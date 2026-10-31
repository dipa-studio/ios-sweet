#!/usr/bin/env python3
"""Inspect/extract a partition from raw or Android sparse super.img, read-only.

Only supports a single physical block device and linear/zero LP extents.
Validates LP geometry, header and table SHA256 checksums before use.
Format: AOSP fs_mgr/liblp/include/liblp/metadata_format.h and libsparse.
"""
import argparse
import bisect
import hashlib
import io
import json
from pathlib import Path
import re
import struct


class SparseImage(io.RawIOBase):
    def __init__(self, path):
        super().__init__()
        self.fh = Path(path).open('rb')
        self.pos, self.runs = 0, []
        self.fh.seek(0, 2)
        physical = self.fh.tell()
        self.fh.seek(0)
        header = self.fh.read(28)
        if len(header) < 4:
            raise ValueError('truncated image')
        if struct.unpack_from('<I', header)[0] != 0xed26ff3a:
            self.size = physical
            self.runs = [(0, physical, 0xcac1, 0)]
        else:
            if len(header) != 28:
                raise ValueError('truncated sparse header')
            _, major, minor, hsize, csize, block, blocks, chunks, checksum = struct.unpack('<I4H4I', header)
            if major != 1 or minor != 0 or hsize < 28 or csize < 12 or not block or block % 4:
                raise ValueError('unsupported sparse header')
            self.size = block * blocks
            off, logical = hsize, 0
            for _ in range(chunks):
                self.fh.seek(off)
                chunk = self.fh.read(csize)
                if len(chunk) != csize:
                    raise ValueError('truncated sparse chunk')
                kind, _, count, total = struct.unpack_from('<2H2I', chunk)
                length = count * block
                payload = total - csize
                if total < csize or off + total > physical or logical + length > self.size:
                    raise ValueError('invalid sparse chunk bounds')
                if kind == 0xcac1 and payload == length:
                    source = off + csize
                elif kind == 0xcac2 and payload == 4:
                    source = self.fh.read(4)
                elif kind == 0xcac3 and payload == 0:
                    source = None
                elif kind == 0xcac4 and payload == 4 and count == 0:
                    off += total
                    continue  # Sparse CRC is not verified; LP checksums are.
                else:
                    raise ValueError('unsupported/invalid sparse chunk')
                if length:
                    self.runs.append((logical, logical + length, kind, source))
                logical += length
                off += total
            if logical != self.size:
                raise ValueError('sparse logical size mismatch')
        self.starts = [r[0] for r in self.runs]

    def readable(self):
        return True

    def seekable(self):
        return True

    def tell(self):
        return self.pos

    def seek(self, offset, whence=0):
        target = offset if whence == 0 else self.pos + offset if whence == 1 else self.size + offset if whence == 2 else -1
        if target < 0:
            raise ValueError('negative/invalid seek')
        self.pos = target
        return target

    def read(self, size=-1):
        left = max(0, self.size - self.pos)
        if size >= 0:
            left = min(size, left)
        parts = []
        while left:
            start, end, kind, source = self.runs[bisect.bisect_right(self.starts, self.pos) - 1]
            offset = self.pos - start
            n = min(left, end - self.pos)
            if kind == 0xcac1:
                self.fh.seek(source + offset)
                data = self.fh.read(n)
                if len(data) != n:
                    raise ValueError('short raw image read')
            elif kind == 0xcac2:
                pad = offset % 4
                data = (source * ((n + pad + 3) // 4))[pad:pad + n]
            else:
                data = bytes(n)
            parts.append(data)
            self.pos += n
            left -= n
        return b''.join(parts)

    def read_at(self, offset, size):
        if offset < 0 or size < 0 or offset + size > self.size:
            raise ValueError('read outside image')
        self.seek(offset)
        data = self.read(size)
        if len(data) != size:
            raise ValueError('short image read')
        return data

    def close(self):
        self.fh.close()
        super().close()


def metadata(image, slot=0):
    geom = image.read_at(4096, 52)
    magic, size = struct.unpack_from('<II', geom)
    if magic != 0x616c4467 or size != 52:
        raise ValueError('unsupported LP geometry')
    if hashlib.sha256(geom[:8] + bytes(32) + geom[40:]).digest() != geom[8:40]:
        raise ValueError('LP geometry checksum mismatch')
    maximum, slots, block_size = struct.unpack_from('<III', geom, 40)
    if slot < 0 or slot >= slots or not maximum or maximum % 512 or maximum > 16 * 1024 * 1024:
        raise ValueError('invalid metadata slot/size')
    raw = image.read_at(12288 + maximum * slot, maximum)
    magic, major, minor, header_size = struct.unpack_from('<IHHI', raw)
    if magic != 0x414c5030 or major != 10 or minor > 2 or header_size not in (128, 256):
        raise ValueError('unsupported LP header')
    if hashlib.sha256(raw[:12] + bytes(32) + raw[44:header_size]).digest() != raw[12:44]:
        raise ValueError('LP header checksum mismatch')
    table_size, = struct.unpack_from('<I', raw, 44)
    if header_size + table_size > len(raw):
        raise ValueError('LP tables exceed metadata')
    tables = raw[header_size:header_size + table_size]
    if hashlib.sha256(tables).digest() != raw[48:80]:
        raise ValueError('LP table checksum mismatch')

    def table(offset, expected):
        start, count, stride = struct.unpack_from('<III', raw, offset)
        if stride != expected or start + count * stride > len(tables):
            raise ValueError('invalid LP table descriptor')
        return [tables[start + i * stride:start + (i + 1) * stride] for i in range(count)]

    devices = table(116, 64)
    if len(devices) != 1:
        raise ValueError('multiple physical devices are not supported')
    first_sector, _, _, device_size = struct.unpack_from('<QIIQ', devices[0])
    if device_size > image.size:
        raise ValueError('LP physical device exceeds image')
    extents = [struct.unpack('<QIQI', e) for e in table(92, 24)]
    for count, kind, sector, source in extents:
        if kind not in (0, 1) or source != 0 or (kind == 1 and sector != 0):
            raise ValueError('unsupported LP extent')
        if kind == 0 and (sector < first_sector or (sector + count) * 512 > device_size):
            raise ValueError('LP extent outside physical data area')
    parts = {}
    for rawpart in table(80, 52):
        name, attrs, first, count, group = struct.unpack('<36s4I', rawpart)
        name = name.rstrip(b'\0').decode('ascii')
        if not re.fullmatch(r'[A-Za-z0-9_]+', name) or name in parts or first + count > len(extents):
            raise ValueError('invalid LP partition')
        runs = extents[first:first + count]
        parts[name] = {'attributes': attrs, 'group': group,
                       'bytes': sum(r[0] * 512 for r in runs), 'extents': runs}
    return {'slot': slot, 'version': [major, minor], 'logical_block_size': block_size,
            'metadata_sha256': hashlib.sha256(raw[:header_size + table_size]).hexdigest(),
            'partitions': parts}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('image', type=Path)
    parser.add_argument('--slot', type=int, default=0)
    parser.add_argument('--partition')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    if bool(args.partition) != bool(args.output):
        parser.error('--partition and --output are required together')
    with SparseImage(args.image) as image:
        info = metadata(image, args.slot)
        if args.partition:
            part = info['partitions'][args.partition]
            digest = hashlib.sha256()
            with args.output.open('xb') as dest:
                for count, kind, sector, source in part['extents']:
                    size, offset = count * 512, sector * 512
                    while size:
                        n = min(size, 4 << 20)
                        data = image.read_at(offset, n) if kind == 0 else bytes(n)
                        dest.write(data)
                        digest.update(data)
                        offset += n
                        size -= n
            info['extracted'] = {'partition': args.partition, 'output': str(args.output),
                                 'bytes': part['bytes'], 'sha256': digest.hexdigest()}
        print(json.dumps(info, indent=2))


if __name__ == '__main__':
    main()
