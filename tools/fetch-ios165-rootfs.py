#!/usr/bin/env python3
"""Fetch only root/OS/App images from Apple's iPhone X iOS 16.5 IPSW locally.

Reads the ZIP64 central directory, checks HTTP ranges, resumes stored members,
and verifies each output's ZIP CRC and length. Does not extract files or flash.
Member selection follows HakiOS's sysimage/fetch-from-ipsw.py at commit
88513176b1e96ecf0b764cd62c6f4e6ac71345e3; range/CRC validation is added here.
"""
import hashlib
import json
from pathlib import Path
import struct
import time
import urllib.request
import zlib

URL = ('https://updates.cdn-apple.com/2023SpringFCS/fullrestores/032-85130/'
       '6AB0D10A-8AF9-4F6C-8CF5-A1B315CABE88/iPhone10,3,iPhone10,6_16.5_20F66_Restore.ipsw')
SIZE = 6165698198
MEMBERS = {'096-04088-077.dmg': 'rootfs.dmg', '096-04666-078.dmg': 'cryptex-os.dmg',
           '096-03536-083.dmg': 'cryptex-app.dmg'}
DEST = Path(__file__).resolve().parents[1] / 'out/ios165-20F66-apple'


def fetch(start, end):
    if not 0 <= start <= end < SIZE: raise ValueError('Invalid IPSW byte range')
    r = urllib.request.urlopen(urllib.request.Request(URL, headers={'Range': f'bytes={start}-{end}'}), timeout=120)
    if r.status != 206 or r.headers.get('Content-Range') != f'bytes {start}-{end}/{SIZE}':
        r.close(); raise OSError('Apple CDN returned an unexpected range')
    return r


def small(start, length):
    with fetch(start, start + length - 1) as r:
        data = r.read(length + 1)
    if len(data) != length: raise OSError('Short/oversized IPSW metadata')
    return data


def directory():
    tail = small(SIZE - 65536, 65536)
    at = tail.rfind(b'PK\x06\x06')
    if at < 0 or at + 56 > len(tail): raise ValueError('Missing ZIP64 directory')
    size, offset = struct.unpack_from('<QQ', tail, at + 40)
    if size > 8 * 1024 * 1024: raise ValueError('Unexpected directory size')
    cd = small(offset, size); p = 0; result = {}
    while cd[p:p + 4] == b'PK\x01\x02':
        method = struct.unpack_from('<H', cd, p + 10)[0]
        crc, csize, usize, nl, el, cl = struct.unpack_from('<IIIHHH', cd, p + 16)
        offset = struct.unpack_from('<I', cd, p + 42)[0]
        name = cd[p + 46:p + 46 + nl].decode()
        extra = cd[p + 46 + nl:p + 46 + nl + el]; q = 0
        while q + 4 <= len(extra):
            tag, n = struct.unpack_from('<HH', extra, q)
            if tag == 1:
                values = list(struct.unpack_from('<' + 'Q' * (n // 8), extra, q + 4))
                if usize == 0xffffffff: usize = values.pop(0)
                if csize == 0xffffffff: csize = values.pop(0)
                if offset == 0xffffffff: offset = values.pop(0)
            q += 4 + n
        if name in MEMBERS:
            h = small(offset, 30)
            if h[:4] != b'PK\x03\x04': raise ValueError('Invalid member header')
            hnl, hel = struct.unpack_from('<HH', h, 26)
            result[name] = {'method': method, 'crc32': crc, 'compressed_bytes': csize,
                            'bytes': usize, 'data_offset': offset + 30 + hnl + hel}
        p += 46 + nl + el + cl
    if set(result) != set(MEMBERS): raise ValueError('Required IPSW components missing')
    return result


def digest(path):
    sha = hashlib.sha256(); crc = 0; size = 0
    with path.open('rb') as f:
        while data := f.read(8 * 1024 * 1024):
            sha.update(data); crc = zlib.crc32(data, crc); size += len(data)
    return sha.hexdigest(), crc & 0xffffffff, size


def get(name, info):
    path = DEST / MEMBERS[name]; part = path.with_suffix('.dmg.part')
    if path.is_file():
        sha, crc, size = digest(path)
        if crc != info['crc32'] or size != info['bytes']: raise ValueError(f'Existing {path.name} failed CRC/size')
        print(f'{path.name}: already verified', flush=True); return sha
    if info['method'] not in (0, 8): raise ValueError('Unsupported ZIP compression')
    for attempt in range(1, 6):
        have = part.stat().st_size if part.exists() and info['method'] == 0 else 0
        if have > info['bytes']: raise ValueError('Partial image is too large')
        if have == info['bytes']: break
        print(f'{path.name}: download attempt {attempt}, resume={have}, output={info["bytes"]}', flush=True)
        try:
            decoder = zlib.decompressobj(-15) if info['method'] == 8 else None
            begin = info['data_offset'] + (have if decoder is None else 0)
            end = info['data_offset'] + info['compressed_bytes'] - 1
            progress = have; next_report = have + 128 * 1024 * 1024
            with fetch(begin, end) as stream, part.open('ab' if have else 'wb') as f:
                while chunk := stream.read(1024 * 1024):
                    data = decoder.decompress(chunk, 8 * 1024 * 1024) if decoder else chunk
                    while True:
                        f.write(data); progress += len(data)
                        if progress > info['bytes']: raise ValueError('Inflated image exceeds ZIP size')
                        if not decoder or not decoder.unconsumed_tail: break
                        data = decoder.decompress(decoder.unconsumed_tail, 8 * 1024 * 1024)
                    if progress >= next_report:
                        print(f'{path.name}: {progress}/{info["bytes"]} bytes ({100 * progress // info["bytes"]}%)', flush=True)
                        next_report += 128 * 1024 * 1024
                if decoder:
                    f.write(decoder.flush())
                    if not decoder.eof: raise OSError('Incomplete deflated member')
            break
        except (OSError, zlib.error) as error:
            print(f'{path.name}: {error}', flush=True)
            if attempt == 5: raise
            time.sleep(2)
    sha, crc, size = digest(part)
    if size != info['bytes'] or crc != info['crc32']:
        raise ValueError(f'{path.name}: ZIP CRC/size mismatch ({crc:08x}, {size})')
    part.replace(path)
    print(f'{path.name}: CRC verified, SHA256={sha}', flush=True)
    return sha


def main():
    DEST.mkdir(parents=True, exist_ok=True)
    meta = {'source_url': URL, 'ipsw_bytes': SIZE, 'build': '20F66', 'ios': '16.5',
            'purpose': 'local Apple source images; not a whyred flash image', 'members': directory()}
    (DEST / 'source.json').write_text(json.dumps(meta, indent=2) + '\n')
    for name in MEMBERS:
        meta['members'][name]['sha256'] = get(name, meta['members'][name])
        (DEST / 'source.json').write_text(json.dumps(meta, indent=2) + '\n')
    print('All three Apple source images downloaded and CRC/SHA256 checked; no extraction/phone writes.', flush=True)


if __name__ == '__main__': main()
