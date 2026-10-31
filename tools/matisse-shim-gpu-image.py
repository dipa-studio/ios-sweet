#!/usr/bin/env python3
"""Build-only MT6983 GPU shim diagnostic with an intact Recovery fallback.

Never flashes or imports historical trial runners. Requires pinned inputs.
"""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import struct
import subprocess

import adt
import embed_payload
import mkbootimg
import mkpayload

ROOT = Path(__file__).resolve().parents[1]
FALLBACK_OFFSET = 0x2000000
FLAGS = ['--target=aarch64-none-elf', '-O2', '-ffreestanding', '-nostdlib',
         '-fno-pic', '-mgeneral-regs-only', '-mstrict-align',
         '-fno-stack-protector', '-fno-builtin', '-Wall', '-Wextra', '-Werror']

def digest(data):
    return hashlib.sha256(data).hexdigest()

def pinned(path, expected):
    data = Path(path).read_bytes()
    if digest(data) != expected:
        raise ValueError('SHA256 mismatch: ' + str(path))
    return data

def diagnostic_adt(data):
    root, end = adt.parse(data)
    if end != len(data):
        raise ValueError('trailing ADT bytes')
    chosen = next(c for c in root.children if c.name == 'chosen')
    for key in ('sweet-gpu-report', 'sweet-gpu-autorecovery-seconds'):
        if chosen.prop(key) is not None:
            raise ValueError('already a GPU diagnostic ADT')
    chosen.props = [(n, f, b'sweet-shim/gpu2320'.ljust(128, b'\0')
                     if n in ('firmware-version', 'system-firmware-version') else v)
                    for n, f, v in chosen.props]
    chosen.props += [('sweet-gpu-report', 0, bytes(128)),
                     ('sweet-gpu-autorecovery-seconds', 0, struct.pack('<I', 60))]
    return adt.serialize(root)

def build(a):
    out = Path(a.out).resolve()
    out.relative_to(ROOT / 'research')
    if out.exists():
        raise ValueError('refuse existing output directory')
    kernel = pinned(a.kernel, a.kernel_sha256)
    template = pinned(a.template, a.template_sha256)
    original_adt = pinned(a.adt, a.adt_sha256)
    stock = pinned(a.stock, a.stock_sha256)
    frozen = Path(a.frozen).resolve()
    for name in ('loader.c', 'start.S', 'fdt.c', 'str.c'):
        previous = subprocess.check_output(['git', 'show', '8dc3bce:shim/' + name], cwd=ROOT)
        if (frozen / name).read_bytes() != previous:
            raise ValueError('frozen source pin mismatch: ' + name)
    command = Path(a.cmdline).read_text().strip()
    if 'sweettrial=2317' not in command:
        raise ValueError('expected known-good2317 command line')
    command = command.replace('sweettrial=2317', 'sweettrial=2320')
    command = command.replace('rootrw=1', 'rootrw=0').replace('ufsrw=1', 'ufsrw=0')
    tree = diagnostic_adt(original_adt)
    out.mkdir(parents=True)
    (out / 'gpu2320.adt').write_bytes(tree)
    payload, _ = mkpayload.build(Path(a.kernel), out / 'gpu2320.adt', command,
                                 allow_matisse_root_write=False)
    (out / 'gpu2320.payload').write_bytes(payload)
    ndk = Path(a.ndk)
    definitions = ['-DSHIM_GPU_PROBE', '-DSHIM_RECOVERY_FALLBACK',
                   '-DSHIM_RECOVERY_OFFSET=' + str(FALLBACK_OFFSET),
                   '-DEMBEDDED_XNU_BYTES=' + str(len(payload))]
    source = {'start': ROOT / 'shim/start.S', 'loader': ROOT / 'shim/loader.c',
              'gpu': ROOT / 'shim/gpu.c', 'gpueb_boot': ROOT / 'xnu/gpu/mtk_gpueb_boot.c',
              'gpueb_protocol': ROOT / 'xnu/gpu/mtk_gpueb_protocol.c'}
    for name, path in source.items():
        subprocess.run([str(ndk / 'clang'), *FLAGS, *definitions, '-c', str(path),
                        '-o', str(out / (name + '.o'))], check=True)
        relocs = subprocess.check_output([str(ndk / 'llvm-readelf'), '-r', str(out / (name + '.o'))], text=True)
        if name != 'start' and 'R_AARCH64_ABS64' in relocs:
            raise ValueError('absolute pointer in position-independent shim: ' + name)
    names = ['start','shim','console','display','diag','mmu','fdt','board','loader',
             'ufs','str','logstore','gpu','gpueb_boot','gpueb_protocol']
    objects = [out / (n + '.o') if n in source else frozen / 'out' / (n + '.o') for n in names]
    subprocess.run([str(ndk / 'clang'), *FLAGS, '-static', '-T', str(frozen / 'shim.ld'),
                    '-fuse-ld=lld', '-Wl,--build-id=none', *map(str, objects),
                    '-o', str(out / 'shim.elf')], check=True)
    subprocess.run([str(ndk / 'llvm-objcopy'), '-O', 'binary', str(out / 'shim.elf'),
                    str(out / 'Image-bare')], check=True)
    symbols = subprocess.check_output([str(ndk / 'llvm-nm'), str(out / 'shim.elf')], text=True)
    end = int(next(l.split()[0] for l in symbols.splitlines() if l.endswith(' _end')), 16)
    bare = (out / 'Image-bare').read_bytes()
    if len(bare) > end:
        raise ValueError('shim exceeds linker end')
    bare += bytes(end - len(bare))
    raw = embed_payload.embed(bare, payload, 0x7c80000)
    stock_header = mkbootimg.parse(stock)
    stock_linux = gzip.decompress(stock[4096:4096 + stock_header['kernel_size']])
    text_offset, image_bytes, flags = struct.unpack_from('<3Q', stock_linux, 8)
    if stock_linux[56:60] != b'ARM\x64' or text_offset or flags & 8 == 0 or image_bytes > len(stock_linux):
        raise ValueError('stock Linux placement contract not satisfied')
    if len(raw) > FALLBACK_OFFSET:
        raise ValueError('payload overlaps stock fallback')
    raw += bytes(FALLBACK_OFFSET - len(raw)) + stock_linux
    if len(raw) > 0x7c80000:
        raise ValueError('combined Image overlaps measured live DTB')
    raw = bytearray(raw)
    struct.pack_into('<Q', raw, 16, len(raw))
    (out / 'Image').write_bytes(raw)
    header = mkbootimg.parse(template)
    if header['header_version'] != 4:
        raise ValueError('requires boot v4')
    rd_offset = 4096 + mkbootimg.pad(header['kernel_size'])
    ramdisk = template[rd_offset:rd_offset + header['ramdisk_size']]
    image = out / 'matisse-shim-gpu2320.img'
    mkbootimg.build(gzip.compress(raw, compresslevel=9, mtime=0), ramdisk,
                    header['cmdline'].decode(), image, 4, header['os_version'],
                    header['signature_size'], header['signature'])
    result = image.read_bytes()
    h = mkbootimg.parse(result)
    expanded = gzip.decompress(result[4096:4096 + h['kernel_size']])
    rd = 4096 + mkbootimg.pad(h['kernel_size'])
    if (expanded[FALLBACK_OFFSET:] != stock_linux or expanded != raw or
            result[rd:rd + h['ramdisk_size']] != ramdisk or h['signature'] != header['signature']):
        raise ValueError('image readback/component mismatch')
    info = dict(trial='0x2320', image_bytes=len(result), image_sha256=digest(result),
                kernel_sha256=digest(kernel), adt_sha256=digest(tree), payload_sha256=digest(payload),
                expanded_bytes=len(raw), fallback_offset=FALLBACK_OFFSET,
                fallback_linux_sha256=digest(stock_linux), stock_sha256=digest(stock),
                ramdisk_sha256=digest(ramdisk), signature_sha256=digest(header['signature']),
                signature_authenticated=False, cmdline=command,
                frozen_objects={p.name:digest(p.read_bytes()) for p in objects if p.parent == frozen / 'out'},
                sources={str(p.relative_to(ROOT)):digest(p.read_bytes()) for p in source.values()},
                autorecovery_seconds=60, gpu_csf_firmware_loaded=False)
    (out / 'manifest.json').write_text(json.dumps(info, indent=2) + '\n')
    print(json.dumps(info, indent=2))

def main():
    p = argparse.ArgumentParser(description=__doc__)
    for key in ('kernel','kernel-sha256','template','template-sha256','adt','adt-sha256',
                'stock','stock-sha256','frozen','cmdline','ndk','out'):
        p.add_argument('--' + key, required=True)
    build(p.parse_args())

if __name__ == '__main__':
    main()
