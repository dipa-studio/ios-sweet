#!/usr/bin/env python3
"""Generate synthetic APFS and exercise the port's actual C reader on the host."""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import random
import shutil
import struct
import subprocess
import sys

HERE = Path(__file__).resolve().parent
PORT = HERE.parent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=PORT / 'out/patch-0135-work')
    parser.add_argument('--builder', type=Path, default=HERE / 'apfs/mkapfs.py')
    parser.add_argument('--output', type=Path, default=PORT / 'out/whyred-apfs-host-test')
    args = parser.parse_args()
    out = args.output.resolve(); out.mkdir(parents=True, exist_ok=True)
    source = args.source.resolve() / 'bsd/miscfs/apfs'
    fixture = out / 'root'; fixture.mkdir(exist_ok=True)
    (fixture / 'plain.bin').write_bytes(random.Random(42).randbytes(8207))
    (fixture / 'inline.txt').write_bytes(b'whyred APFS inline zlib\n' * 21)
    (fixture / 'packed.bin').write_bytes((b'whyred APFS resource-fork paging\n' * 9000)[:212345])
    manifest = out / 'manifest.txt'
    manifest.write_text('100644\t0\t0\tplain.bin\n100644\t0\t0\tinline.txt\n100644\t0\t0\tpacked.bin\n120777\t0\t0\tlink\tinline.txt\n', newline='\n')
    image = out / 'test.apfs'
    subprocess.run([sys.executable, str(args.builder), '-z', '-o', str(image),
                    f'Test={fixture},manifest={manifest}'], check=True)
    # Compile the same parser/decompressors as the kernel, with host-only APIs.
    compiler = shutil.which('cc') or shutil.which('clang')
    sources = [str(HERE / 'apfs-parser-test.c')] + [str(source / n) for n in ('apfs_lib.c', 'apfs_deflate.c', 'apfs_zbitmap.c')]
    if os.name == 'nt':
        compiler = 'C:/Program Files/Microsoft Visual Studio/2022/Community/VC/Tools/Llvm/bin/clang.exe'
        exe = out / 'apfs-parser-test.exe'
        win = HERE / 'apfs-host-windows'
        command = [compiler, '-target', 'x86_64-pc-windows-msvc', '-O1', '-std=c11', '-D_CRT_SECURE_NO_WARNINGS', '-I' + str(source),
                   '-I' + str(win), '-include', str(win / 'host-time.h'), *sources, '-o', str(exe), '-lbcrypt']
        batch = out / 'compile.cmd'
        batch.write_text('@call "C:\\Program Files\\Microsoft Visual Studio\\2022\\Community\\VC\\Auxiliary\\Build\\vcvars64.bat" >nul\n' + subprocess.list2cmdline(command) + '\n')
        run = subprocess.run(['cmd', '/d', '/c', str(batch)], capture_output=True, text=True)
    else:
        exe = out / 'apfs-parser-test'
        command = [compiler or 'cc', '-O1', '-std=gnu11', '-I' + str(source), *sources, '-o', str(exe), '-lz', '-lcrypto']
        if sys.platform == 'darwin':
            prefix = subprocess.check_output(['brew', '--prefix', 'openssl@3'], text=True).strip()
            command += ['-I' + prefix + '/include', '-L' + prefix + '/lib']
        run = subprocess.run(command, capture_output=True, text=True)
    (out / 'host-compile.log').write_text(run.stdout + run.stderr)
    if run.returncode:
        print((run.stdout + run.stderr)[-6000:]); return run.returncode
    results = []
    def exercise(path, mode):
        r = subprocess.run([str(exe), str(path), str(fixture), mode], capture_output=True, text=True, timeout=30)
        print(path.name + ': ' + (r.stdout + r.stderr).strip())
        results.append({'image': path.name, 'mode': mode, 'returncode': r.returncode, 'output': r.stdout + r.stderr})
    exercise(image, 'good')
    spec = importlib.util.spec_from_file_location('mkapfs_test_builder', args.builder)
    builder = importlib.util.module_from_spec(spec); spec.loader.exec_module(builder)
    raw = image.read_bytes()
    for name, mutate in (
        ('bad-magic', lambda b: b.__setitem__(slice(32, 36), b'BAD!')),
        ('bad-block-size', lambda b: struct.pack_into('<I', b, 36, 3072)),
        ('overflow-block-count', lambda b: struct.pack_into('<Q', b, 40, (1 << 64) - 1)),
        ('unbounded-checkpoints', lambda b: struct.pack_into('<I', b, 104, 0x7fffffff)),
    ):
        b = bytearray(raw); mutate(b); path = out / (name + '.apfs'); path.write_bytes(b); exercise(path, 'bad-open')
    # A checksummed checkpoint can still lie about its geometry. Recompute its
    # Fletcher checksum, so rejection has to come from validation, not CRC alone.
    for name, field, value, fmt in [('checkpoint-overflow', 40, (1 << 64) - 1, '<Q'), ('checkpoint-block-size', 36, 8192, '<I')]:
        b = bytearray(raw)
        for off in range(4096, len(b), 4096):
            if b[off + 32:off + 36] == b'NXSB':
                struct.pack_into(fmt, b, off + field, value)
                struct.pack_into('<Q', b, off, builder.fletcher64(b[off:off + 4096]))
                assert struct.unpack_from('<Q', b, off)[0] == builder.fletcher64(b[off:off + 4096])
        path = out / (name + '.apfs'); path.write_bytes(b); exercise(path, 'bad-open')
    path = out / 'truncated.apfs'; path.write_bytes(raw[:512]); exercise(path, 'bad-open')
    (out / 'report.json').write_text(json.dumps({'tests': results}, indent=2) + '\n')
    return int(any(r['returncode'] for r in results))


if __name__ == '__main__': raise SystemExit(main())
