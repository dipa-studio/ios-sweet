#!/usr/bin/env python3
"""Read-only MTK v1 image-component inventory and component-aware comparison.

Does not extract, flash, authenticate certificates or modify input images.
Hash each bounded component separately: certificate lengths can shift every
later file offset even when those payloads are identical. Unknown trailers
are reported as opaque bytes, never searched for guessed image headers.
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct

MAGIC = 0x58881688
EXT_MAGIC = 0x58891689


def hash_range(stream, start, size):
    stream.seek(start)
    digest = hashlib.sha256()
    nonzero = 0
    while size:
        block = stream.read(min(size, 1 << 20))
        if not block:
            raise ValueError('image changed/truncated during hashing')
        digest.update(block)
        nonzero += len(block) - block.count(0)
        size -= len(block)
    return digest.hexdigest(), nonzero


def inspect(path):
    path = Path(path)
    with path.open('rb') as stream:
        before = path.stat()
        size = before.st_size
        offset, components = 0, []
        while offset + 4 <= size:
            stream.seek(offset)
            header = stream.read(80)
            if struct.unpack_from('<I', header)[0] != MAGIC:
                break
            if len(header) != 80:
                raise ValueError('truncated MTK header at %#x' % offset)
            magic, header_bytes, version = struct.unpack_from('<III', header, 48)
            alignment, size_hi = struct.unpack_from('<II', header, 68)
            if magic != EXT_MAGIC or version != 1 or not 80 <= header_bytes <= 4096:
                raise ValueError('unsupported MTK extended header at %#x' % offset)
            if not alignment or alignment & (alignment - 1) or alignment > 4096:
                raise ValueError('invalid MTK alignment at %#x' % offset)
            raw_name = header[8:40]
            nul = raw_name.find(b'\0')
            if nul <= 0 or any(x < 32 or x >= 127 for x in raw_name[:nul]):
                raise ValueError('invalid MTK component name at %#x' % offset)
            name = raw_name[:nul].decode('ascii')
            payload_bytes = struct.unpack_from('<I', header, 4)[0] | size_hi << 32
            payload_offset = offset + header_bytes
            end = payload_offset + payload_bytes
            if not payload_bytes or payload_offset > size or end > size:
                raise ValueError('MTK payload outside file at %#x' % offset)
            digest, _ = hash_range(stream, payload_offset, payload_bytes)
            components.append({'index': len(components), 'name': name,
                               'header_offset': offset, 'header_bytes': header_bytes,
                               'payload_offset': payload_offset, 'payload_bytes': payload_bytes,
                               'alignment': alignment, 'sha256': digest})
            aligned = (end + alignment - 1) & ~(alignment - 1)
            # Last file may end at its exact payload boundary, without padding.
            if end < size < aligned:
                raise ValueError('truncated MTK alignment padding')
            offset = end if end == size else aligned
        if not components:
            raise ValueError('not a supported MTK v1 container')
        tail_hash, tail_nonzero = hash_range(stream, offset, size - offset)
        digest, _ = hash_range(stream, 0, size)
        after = path.stat()
        if (before.st_size, before.st_mtime_ns, before.st_ino) != (after.st_size, after.st_mtime_ns, after.st_ino):
            raise ValueError('image changed during inventory')
    return {'name': path.name, 'bytes': size, 'sha256': digest, 'components': components,
            'trailer': {'offset': offset, 'bytes': size - offset,
                        'nonzero_bytes': tail_nonzero, 'sha256': tail_hash},
            'certificate_authentication_performed': False}


def compare(left, right):
    def keyed(report):
        counts, result = {}, {}
        for c in report['components']:
            name = c['name']
            ordinal = counts.get(name, 0)
            counts[name] = ordinal + 1
            result[name, ordinal] = c
        return result
    a, b = keyed(left), keyed(right)
    rows = []
    for key in dict.fromkeys([*a, *b]):
        x, y = a.get(key), b.get(key)
        rows.append({'name': key[0], 'occurrence': key[1],
                     'left_payload_offset': x['payload_offset'] if x else None,
                     'right_payload_offset': y['payload_offset'] if y else None,
                     'payload_equal': bool(x and y and x['payload_bytes'] == y['payload_bytes']
                                           and x['sha256'] == y['sha256'])})
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('image', type=Path)
    parser.add_argument('--compare', type=Path)
    args = parser.parse_args()
    try:
        report = inspect(args.image)
        if args.compare:
            other = inspect(args.compare)
            report = {'left': report, 'right': other, 'comparison': compare(report, other)}
    except (ValueError, OSError) as exc:
        parser.exit(1, '%s\n' % exc)
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
