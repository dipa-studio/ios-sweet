#!/usr/bin/env python3
"""Receive one bounded, checksummed RAM collector frame. No command transmission."""
import argparse
import base64
import binascii
import hashlib
import io
import json
import os
from pathlib import Path
import re
import select
import tarfile
import termios
import time
import tty

LIMIT = 16*1024*1024
HEADER = re.compile(rb'(?:^|\n)MATISSE-COLLECTOR-V1 ([0-9]{1,9}) ([0-9a-f]{64})\r?\n')
END = b'MATISSE-COLLECTOR-END'
FILES = frozenset(('proc-cmdline.txt', 'proc-version.txt', 'proc-iomem.txt',
                   'proc-modules.txt', 'proc-mounts.txt', 'live.dtb', 'pl_lk.bin',
                   'dmesg.txt', 'modules-requested.txt', 'build.json', 'init.log',
                   'udc.txt', 'usb-mode.txt', 'usb-state.txt'))


def decode_frame(data):
    """Return verified payload, or None for an incomplete frame."""
    match = HEADER.search(data)
    if match is None:
        if len(data) > LIMIT:
            raise ValueError('header absent within input bound')
        return None
    size = int(match[1])
    if not 0 < size <= LIMIT:
        raise ValueError('frame size exceeds limit')
    end = data.find(END, match.end())
    if end < 0:
        if len(data)-match.end() > (size+2)//3*4 + size//40 + 1024:
            raise ValueError('encoded frame exceeds size bound')
        return None
    encoded = b''.join(data[match.end():end].split())
    if len(encoded) > (size+2)//3*4:
        raise ValueError('encoded frame exceeds declared size')
    try:
        payload = base64.b64decode(encoded, validate=True)
    except binascii.Error as e:
        raise ValueError('invalid frame base64') from e
    if len(payload) != size or hashlib.sha256(payload).hexdigest().encode() != match[2]:
        raise ValueError('frame length or SHA256 mismatch')
    return payload


def archive_files(payload):
    """Validate all members before exposing any output, never extract paths."""
    files, total = {}, 0
    with tarfile.open(fileobj=io.BytesIO(payload), mode='r:gz') as archive:
        for member in archive:
            name = member.name.rstrip('/')
            parts = name.split('/')
            if member.isdir() and name in ('before-modules', 'after-modules'):
                continue
            if (not member.isfile() or len(parts) != 2 or
                parts[0] not in ('before-modules', 'after-modules') or
                parts[1] not in FILES or name in files):
                raise ValueError('unexpected/unsafe archive member')
            total += member.size
            if member.size < 0 or total > LIMIT:
                raise ValueError('expanded archive exceeds limit')
            content = archive.extractfile(member).read(LIMIT+1)
            if len(content) != member.size:
                raise ValueError('truncated archive member')
            files[name] = content
    for phase in ('before-modules', 'after-modules'):
        for name in ('live.dtb', 'pl_lk.bin', 'proc-mounts.txt', 'dmesg.txt'):
            if phase+'/'+name not in files:
                raise ValueError('required collection member missing')
    return files


def receive(port, timeout):
    if not re.fullmatch(r'/dev/cu\.usbmodem[A-Za-z0-9._-]+', port):
        raise ValueError('use an explicit macOS USB ACM /dev/cu.usbmodem port')
    fd = os.open(port, os.O_RDONLY | os.O_NOCTTY | os.O_NONBLOCK)
    original = termios.tcgetattr(fd)
    try:
        tty.setraw(fd, termios.TCSANOW)
        termios.tcflush(fd, termios.TCIFLUSH)
        deadline, data = time.monotonic()+timeout, bytearray()
        while time.monotonic() < deadline:
            if not select.select([fd], [], [], min(1, max(0,deadline-time.monotonic())))[0]:
                continue
            chunk = os.read(fd, 65536)
            if not chunk:
                raise ValueError('USB serial disconnected')
            data += chunk
            if len(data) > LIMIT*2:
                raise ValueError('serial input exceeds limit')
            payload = decode_frame(data)
            if payload is not None:
                return payload
        raise TimeoutError('no complete collector frame before deadline')
    finally:
        termios.tcsetattr(fd, termios.TCSANOW, original)
        os.close(fd)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    source = ap.add_mutually_exclusive_group(required=True)
    source.add_argument('--port')
    source.add_argument('--input', help='captured text frame for offline verification')
    ap.add_argument('--timeout', type=float, default=120)
    ap.add_argument('--out', required=True, help='new output directory (ignored research recommended)')
    a = ap.parse_args(); out = Path(a.out)
    if out.exists():
        raise ValueError('output directory already exists')
    payload = receive(a.port, a.timeout) if a.port else decode_frame(Path(a.input).read_bytes())
    if payload is None:
        raise ValueError('incomplete input frame')
    files = archive_files(payload)
    out.mkdir(parents=True)
    (out/'collection.tar.gz').write_bytes(payload)
    for name, content in files.items():
        target = out/name; target.parent.mkdir(exist_ok=True); target.write_bytes(content)
    report = dict(sha256=hashlib.sha256(payload).hexdigest(), bytes=len(payload),
                  files={n:dict(bytes=len(v),sha256=hashlib.sha256(v).hexdigest()) for n,v in files.items()})
    (out/'manifest.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(dict(bytes=len(payload), files=len(files), sha256=report['sha256'])))


if __name__ == '__main__':
    main()
