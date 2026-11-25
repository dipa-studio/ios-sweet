#!/usr/bin/env python3
"""Build a small APFS diagnostic root containing the project's static test PID 1."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import sys
import tempfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--init', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    init = args.init.read_bytes()
    if len(init) < 32 or struct.unpack_from('<II', init) != (0xfeedfacf, 0x0100000c):
        raise SystemExit('Expected the project arm64 Mach-O PID 1')
    output = args.output.resolve(); output.parent.mkdir(parents=True, exist_ok=True)
    root = Path(tempfile.mkdtemp(prefix='apfs-root-', dir=output.parent))
    for name in ('sbin', 'dev', 'etc', 'private/var', 'tmp'):
        (root / name).mkdir(parents=True, exist_ok=True)
    (root / 'sbin/launchd').write_bytes(init)
    (root / 'etc/whyred-apfs.txt').write_text('whyred APFS diagnostic root; project test PID 1, no Apple iOS userland\n')
    manifest = root.with_suffix('.manifest')
    manifest.write_text('100755\t0\t0\tsbin/launchd\n100644\t0\t0\tetc/whyred-apfs.txt\n', newline='\n')
    builder = Path(__file__).resolve().parent / 'apfs/mkapfs.py'
    subprocess.run([sys.executable, str(builder), '-o', str(output),
                    f'WhyredTest={root},manifest={manifest}'], check=True)
    report = {'kind': 'diagnostic APFS root', 'contains_apple_ios_userland': False,
              'init_sha256': hashlib.sha256(init).hexdigest(),
              'root_sha256': hashlib.sha256(output.read_bytes()).hexdigest(),
              'root_bytes': output.stat().st_size, 'hardware_boot_validated': False,
              'boot_args_needed': ['rd=md0', 'whyred-apfs-root=1'],
              'expected_runtime': 'APFS mount, then existing SWEET test PID 1 on /dev/console'}
    output.with_suffix('.json').write_text(json.dumps(report, indent=2) + '\n')
    print(f'APFS test root built: {output} ({output.stat().st_size} bytes)')


if __name__ == '__main__': main()
