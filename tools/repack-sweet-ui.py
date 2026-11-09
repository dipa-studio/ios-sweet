#!/usr/bin/env python3
"""Repack a proven embedded-XNU UI boot with a new kernel/command line.

The loader checks a compile-time payload length. Rebuild it for the new
payload and first reproduce the original shim byte-for-byte from the frozen
sources/objects, so a different driver or linker cannot slip into the trial.
This creates local artifacts only; it never accesses a device.
"""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import embed_payload
import mkbootimg
import mkpayload

OBJECTS = ('start', 'shim', 'console', 'display', 'diag', 'mmu', 'fdt',
           'board', 'loader', 'ufs', 'str', 'logstore')
FLAGS = ('--target=aarch64-none-elf', '-O2', '-ffreestanding', '-nostdlib',
         '-fno-pic', '-mgeneral-regs-only', '-mstrict-align',
         '-fno-stack-protector', '-fno-builtin', '-Wall', '-Wextra')


def sha(data):
    return hashlib.sha256(data).hexdigest()


def split_embedded(image):
    """Ignore marker strings in code: accept only the final valid payload."""
    found = []
    pos = 0
    while True:
        at = image.find(embed_payload.MARKER, pos)
        if at < 0:
            break
        pos = at + 1
        if at + 16 + embed_payload.MIN_PAYLOAD_HEADER > len(image):
            continue
        length = struct.unpack_from('<Q', image, at + 8)[0]
        if (at % 4096 == 0 and at + 16 + length == len(image) and
                length >= embed_payload.MIN_PAYLOAD_HEADER and
                image[at + 16:at + 24] == embed_payload.PAYLOAD_MAGIC):
            found.append((at, image[at + 16:]))
    if len(found) != 1:
        raise ValueError('base must contain exactly one valid final SWEETAPP payload')
    return found[0]


def build_shim(source, toolchain, work, payload):
    work.mkdir()
    cc = toolchain / 'clang'
    subprocess.run([str(cc), '-DEMBEDDED_XNU_BYTES=' + str(len(payload)), *FLAGS,
                    '-c', str(source / 'loader.c'), '-o', str(work / 'loader.o')], check=True)
    objects = [work / 'loader.o' if n == 'loader' else source / 'out' / (n + '.o')
               for n in OBJECTS]
    subprocess.run([str(cc), *FLAGS, '-static', '-T', str(source / 'shim.ld'),
                    '-fuse-ld=lld', '-Wl,--build-id=none', *map(str, objects),
                    '-o', str(work / 'shim.elf')], check=True)
    subprocess.run([str(toolchain / 'llvm-objcopy'), '-O', 'binary',
                    str(work / 'shim.elf'), str(work / 'Image-bare')], check=True)
    symbols = subprocess.check_output([str(toolchain / 'llvm-nm'), str(work / 'shim.elf')], text=True)
    ends = [int(line.split()[0], 16) for line in symbols.splitlines() if line.endswith(' _end')]
    if len(ends) != 1:
        raise ValueError('shim must have one _end symbol')
    bare = (work / 'Image-bare').read_bytes()
    if len(bare) > ends[0]:
        raise ValueError('shim exceeds _end')
    bare += bytes(ends[0] - len(bare))
    result = embed_payload.embed(bare, payload, 0x7c80000)
    (work / 'Image').write_bytes(result)
    return result


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    for name in ('base-boot', 'kernel', 'adt', 'shim-dir', 'toolchain', 'cmdline-file', 'output'):
        ap.add_argument('--' + name, type=Path, required=True)
    ap.add_argument('--allow-matisse-root-write', action='store_true')
    a = ap.parse_args()
    source, tc = a.shim_dir.resolve(), a.toolchain.resolve()
    out = a.output.resolve()
    work = out.with_suffix('.build')
    if out.exists() or work.exists():
        ap.error('output and build directory must not exist')
    original = a.base_boot.read_bytes()
    meta = mkbootimg.parse(original)
    if meta['header_version'] != 4:
        ap.error('this recipe requires the proven Android v4 UI boot')
    raw = gzip.decompress(original[4096:4096 + meta['kernel_size']])
    _, old_payload = split_embedded(raw)
    work.mkdir(parents=True)
    reproduced = build_shim(source, tc, work / 'baseline', old_payload)
    if reproduced != raw:
        ap.error('frozen shim/compiler did not reproduce the base Image exactly')
    payload, info = mkpayload.build(a.kernel, a.adt, a.cmdline_file.read_text().strip(),
                                   allow_matisse_root_write=a.allow_matisse_root_write)
    new = build_shim(source, tc, work / 'candidate', payload)
    offset = 4096 + mkbootimg.pad(meta['kernel_size'])
    ramdisk = original[offset:offset + meta['ramdisk_size']]
    mkbootimg.build(gzip.compress(new, mtime=0), ramdisk, meta['cmdline'].decode(), out,
                   header_version=4, os_version=meta['os_version'],
                   signature_size=meta['signature_size'], signature=meta['signature'])
    packed = out.read_bytes()
    check = mkbootimg.parse(packed)
    assert gzip.decompress(packed[4096:4096 + check['kernel_size']]) == new
    assert split_embedded(new)[1] == payload
    assert check['signature'] == meta['signature'] and check['cmdline'] == meta['cmdline']
    offset = 4096 + mkbootimg.pad(check['kernel_size'])
    assert packed[offset:offset + check['ramdisk_size']] == ramdisk
    out.with_suffix('.payload').write_bytes(payload)
    result = dict(image_sha256=sha(packed), image_size=len(packed),
                  kernel_sha256=sha(a.kernel.read_bytes()), payload_sha256=sha(payload),
                  payload_bytes=len(payload), previous_payload_bytes=len(old_payload),
                  base_boot_sha256=sha(original), baseline_shim_reproduced=True,
                  loader_recompiled=True, cmdline=info['cmdline'], device_writes=False)
    out.with_suffix('.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
