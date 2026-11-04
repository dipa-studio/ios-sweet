#!/usr/bin/env python3
"""Build-only MT6983 GPU shim diagnostic with an intact Recovery fallback.

Never flashes or imports historical trial runners. Requires pinned inputs.
"""
import argparse
import gzip
import hashlib
import importlib.util
import json
from pathlib import Path
import struct
import subprocess
import tempfile

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

# The real reset handler at0x010018ec touches the MCU peripheral window before
# it touches anything else: it stores0xb to0x40022000, stores7 to0x40022004,
# and then loads0x40003034. Every one of those constants occurs exactly once in
# the pinned container, so each is the load literal of exactly one instruction.
# A variant repoints them at words inside the shared page, which leaves the
# instructions themselves untouched while (a) bypassing the peripheral accesses
# that may be stalling the bus and (b) leaving an observable trace.
MCU_ACCESS_REDIRECTS = {
    0x2339: (
        dict(kind='store', literal_va=0x01001988, original=0x40022000,
             insn_va=0x010018f4, insn=b'\x01\x60', target=0x04000ffc, value=0xb),
        dict(kind='store', literal_va=0x0100198c, original=0x40022004,
             insn_va=0x010018fc, insn=b'\x01\x60', target=0x04000ffc, value=0x7),
    ),
    0x2340: (
        # First store goes to the global-interface version word, which is the
        # one location2334 proved writable from this same entry. That splits
        # "the code never ran" from "shared+0xffc specifically does not take
        # the write", which2336 and2339 could not distinguish.
        dict(kind='store', literal_va=0x01001988, original=0x40022000,
             insn_va=0x010018f4, insn=b'\x01\x60', target=0x04000000, value=0xb),
        dict(kind='store', literal_va=0x0100198c, original=0x40022004,
             insn_va=0x010018fc, insn=b'\x01\x60', target=0x04000ffc, value=0x7),
        # The load itself cannot fault the way a store can, but a peripheral
        # read that never answers stalls exactly the same way. Point it at a
        # zero word so r4 becomes0 and the guarded0x03800000 copy is skipped.
        dict(kind='load', literal_va=0x01001998, original=0x40003034,
             insn_va=0x01001918, insn=b'\x1f\x48', target=0x04000ff8, value=None),
    ),
    0x2341: (
        # 2340 proved the first store executes: version read0xb, the value it
        # writes, on a byte-identical shim. Its second store, aimed at the same
        # shared+0xffc that2335/2336/2339 also used, still did not land. So ask
        # the narrow question: does the rest of that first page take writes, or
        # is0xffc alone broken? The second store now targets shared+4, one word
        # further in, and features is already decoded, so nothing in the report
        # ABI moves.
        dict(kind='store', literal_va=0x01001988, original=0x40022000,
             insn_va=0x010018f4, insn=b'\x01\x60', target=0x04000000, value=0xb),
        dict(kind='store', literal_va=0x0100198c, original=0x40022004,
             insn_va=0x010018fc, insn=b'\x01\x60', target=0x04000004, value=0x7),
        dict(kind='load', literal_va=0x01001998, original=0x40003034,
             insn_va=0x01001918, insn=b'\x1f\x48', target=0x04000ff8, value=None),
    ),
    0x2342: (
        # 2341 proved both stores run and that the whole first shared page takes
        # writes except0xffc. It left one variable untested: whether the REAL
        # peripheral at0x40022000 accepts its store. So keep that store exactly
        # as the vendor wrote it, keep the peripheral load real too (bit7 must
        # be0 because0x0302bc78 and0x03800000 are in no section, so the vendor
        # firmware itself could not survive a set bit), and move only the second
        # store to shared+4. features0x7 therefore means the real peripheral
        # write completed and execution reached the next instruction.
        dict(kind='store', literal_va=0x0100198c, original=0x40022004,
             insn_va=0x010018fc, insn=b'\x01\x60', target=0x04000004, value=0x7),
    ),
}


def redirect_mcu_accesses(path, expected, build_id):
    firmware = pinned(path, expected)
    if expected != 'de22d2fc06bc8a859968499a6e609c27fe838be062bf5c97d92ea9f904f7229a':
        raise ValueError('MCU access redirect requires the measured device firmware')
    sites = MCU_ACCESS_REDIRECTS.get(build_id)
    if not sites:
        raise ValueError('build %#x has no MCU access redirect' % build_id)
    spec = importlib.util.spec_from_file_location('csf_fetch', ROOT / 'tools/matisse-csf-fetch-audit.py')
    fetch = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(fetch)
    _, plan = fetch.build_arena(Path(path), 0x40077000, memory_group=6)
    section = next(s for s in plan['sections'] if s['va'] == 0x01000000)

    def offset(va):
        if not (section['va'] <= va and va + 4 <= section['va'] + section['data_bytes']):
            raise ValueError('redirect site %#x is outside the code section' % va)
        return section['data_start'] + va - section['va']

    edits = []
    for site in sites:
        insn = offset(site['insn_va'])
        if firmware[insn:insn + 2] != site['insn']:
            raise ValueError('instruction at %#x is %s, expected %s' %
                             (site['insn_va'], firmware[insn:insn + 2].hex(), site['insn'].hex()))
        literal = offset(site['literal_va'])
        have = int.from_bytes(firmware[literal:literal + 4], 'little')
        if have != site['original']:
            raise ValueError('literal %#x is %#x, expected %#x' %
                             (site['literal_va'], have, site['original']))
        if firmware.count(site['original'].to_bytes(4, 'little')) != 1:
            raise ValueError('constant %#x is not unique in the container' % site['original'])
        if site['target'] & 3:
            raise ValueError('redirect target %#x is not aligned' % site['target'])
        edits.append((literal, site['original'], site['target']))

    embedded = bytearray(firmware)
    for literal, _, target in edits:
        embedded[literal:literal + 4] = target.to_bytes(4, 'little')
    embedded = bytes(embedded)
    if len(embedded) != len(firmware):
        raise ValueError('redirect changed the container size')
    changed = [i for i in range(len(firmware)) if firmware[i] != embedded[i]]
    if not changed or any(
            not any(literal <= i < literal + 4 for literal, _, _ in edits) for i in changed):
        raise ValueError('redirect touched bytes outside the redirected literals')
    for literal, _, _ in edits:
        if firmware[literal:literal + 4] == embedded[literal:literal + 4]:
            raise ValueError('literal at container offset %#x was not changed' % literal)
    with tempfile.TemporaryDirectory(prefix='csf-access-redirect-') as directory:
        candidate = Path(directory) / 'diagnostic.bin'
        candidate.write_bytes(embedded)
        _, rebuilt_plan = fetch.build_arena(candidate, 0x40077000, memory_group=6)
    if rebuilt_plan != plan:
        raise ValueError('access redirect changed firmware mappings')
    patch = dict(diagnostic_only=True,
                 sites=[dict(kind=site['kind'], literal_va='%#x' % site['literal_va'],
                             original='%#x' % site['original'], target='%#x' % site['target'],
                             written_value=site['value'],
                             insn_va='%#x' % site['insn_va'],
                             container_offset='%#x' % literal)
                        for site, (literal, _, _) in zip(sites, edits)],
                 original_container_sha256=digest(firmware),
                 embedded_container_sha256=digest(embedded))
    return embedded, patch


def redirect_mcu_stores(path, expected):
    return redirect_mcu_accesses(path, expected, 0x2339)


# Every Cortex-M fault vector in this container points at0x010019b1, so a single
# storm-free stub answers the one question static analysis cannot: does the MCU
# fault, and at which instruction. The stub reads the stacked PC out of the
# exception frame on PSP (the entry switches to PSP at0x01001910) and parks it
# in a shared word the shim already decodes. The periphals and the rest of the
# entry stay exactly as the vendor shipped them.
FAULT_VECTOR_PROBE = {
    0x2343: dict(
        stub_va=0x010019b0,
        # mrs r0,psp / ldr r1,[r0,#0x18] / ldr r2,[pc,#8] / str r1,[r2] /
        # b . / nop / nop / .word0x04000010
        stub=bytes.fromhex('eff309808169' '024a1160' 'fee7' '00bf' '00bf' '10000004'),
        marker_va=0x04000010,
    ),
}


def fault_vector_probe(path, expected, build_id):
    firmware = pinned(path, expected)
    if expected != 'de22d2fc06bc8a859968499a6e609c27fe838be062bf5c97d92ea9f904f7229a':
        raise ValueError('fault vector probe requires the measured device firmware')
    spec = FAULT_VECTOR_PROBE.get(build_id)
    if not spec:
        raise ValueError('build %#x has no fault vector probe' % build_id)
    fetch = importlib.util.module_from_spec(
        importlib.util.spec_from_file_location('csf_fetch', ROOT / 'tools/matisse-csf-fetch-audit.py'))
    importlib.util.spec_from_file_location('csf_fetch', ROOT / 'tools/matisse-csf-fetch-audit.py').loader.exec_module(fetch)
    _, plan = fetch.build_arena(Path(path), 0x40077000, memory_group=6)
    section = next(s for s in plan['sections'] if s['va'] == 0x01000000)

    def offset(va):
        if not (section['va'] <= va and va + 4 <= section['va'] + section['data_bytes']):
            raise ValueError('probe site %#x is outside the code section' % va)
        return section['data_start'] + va - section['va']

    # The vector table lives in the VA-zero config section, not at file offset0.
    config = next(s for s in plan['sections'] if s['va'] == 0)
    # SP at0x0 and Reset at0x4 are not fault vectors.
    for entry in (0x08, 0x0c, 0x10, 0x14, 0x18):
        at = config['data_start'] + entry
        word = int.from_bytes(firmware[at:at + 4], 'little')
        if word != 0x010019b1:
            raise ValueError('vector %#x is %#x, expected0x010019b1' % (entry, word))

    stub_at = offset(spec['stub_va'])
    stub = spec['stub']
    if len(stub) % 4:
        raise ValueError('stub must keep four-byte alignment')
    embedded = bytearray(firmware)
    replaced = bytes(embedded[stub_at:stub_at + len(stub)])
    embedded[stub_at:stub_at + len(stub)] = stub
    embedded = bytes(embedded)
    if len(embedded) != len(firmware):
        raise ValueError('fault probe changed the container size')
    changed = sorted(i for i in range(len(firmware)) if firmware[i] != embedded[i])
    if any(not (stub_at <= i < stub_at + len(stub)) for i in changed):
        raise ValueError('fault probe touched bytes outside the stub')
    with tempfile.TemporaryDirectory(prefix='csf-fault-probe-') as directory:
        candidate = Path(directory) / 'diagnostic.bin'
        candidate.write_bytes(embedded)
        _, rebuilt = fetch.build_arena(candidate, 0x40077000, memory_group=6)
    if rebuilt != plan:
        raise ValueError('fault probe changed firmware mappings')
    patch = dict(diagnostic_only=True, kind='fault-vector',
                 stub_va='%#x' % spec['stub_va'], stub_bytes=stub.hex(),
                 replaced_bytes=replaced.hex(), marker_va='%#x' % spec['marker_va'],
                 container_bytes_changed=len(changed),
                 original_container_sha256=digest(firmware),
                 embedded_container_sha256=digest(embedded))
    return embedded, patch


def diagnostic_firmware(path, expected, build_id, reset_store_stub, entry_probe=False,
                        inline_entry=False, entry_pte_guard=False, mcu_store_redirect=False):
    firmware = pinned(path, expected)
    if expected != 'de22d2fc06bc8a859968499a6e609c27fe838be062bf5c97d92ea9f904f7229a':
        raise ValueError('CSF probe requires the measured device firmware')
    if build_id in MCU_ACCESS_REDIRECTS:
        if not mcu_store_redirect or entry_probe or inline_entry or entry_pte_guard or reset_store_stub:
            raise ValueError('build%x requires only the MCU access redirect' % build_id)
        return redirect_mcu_accesses(path, expected, build_id)
    if mcu_store_redirect:
        raise ValueError('only the redirect builds may repoint MCU access literals')
    if inline_entry and (not entry_probe or build_id not in (0x2336,0x2337,0x2338)):
        raise ValueError('inline entry requires build2336/2337/2338 and entry probe')
    if entry_pte_guard != (build_id in (0x2337,0x2338)):
        raise ValueError('build2337 requires the entry PTE guard (build2338 does too); other builds forbid it')
    if entry_probe:
        if (build_id not in ((0x2336,0x2337,0x2338) if inline_entry else (0x2335,)) or
                reset_store_stub):
            raise ValueError('entry probe requires build2335/2336/2337/2338 and original firmware')
        return firmware, None
    if build_id in (0x2335,0x2336,0x2337,0x2338):
        raise ValueError('build2335/2336/2337/2338 requires the entry probe')
    if (build_id == 0x2334) != reset_store_stub:
        raise ValueError('build2334 requires the reset-store stub; other builds must retain stock firmware')
    if not reset_store_stub:
        return firmware, None
    spec = importlib.util.spec_from_file_location('csf_fetch', ROOT / 'tools/matisse-csf-fetch-audit.py')
    fetch = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(fetch)
    arena, plan = fetch.build_arena(Path(path), 0x40077000, memory_group=6)
    patched_arena, patch = fetch.patch_reset_store_stub(arena, plan)
    entry = int(patch['entry_va'], 0)
    code = bytes.fromhex(patch['patch_hex'])
    section = next(s for s in plan['sections'] if s['flags'] & 4 and
                   s['va'] <= entry and entry + len(code) <= s['va'] + s['data_bytes'])
    offset = section['data_start'] + entry - section['va']
    embedded = firmware[:offset] + code + firmware[offset + len(code):]
    with tempfile.TemporaryDirectory(prefix='csf-reset-store-') as directory:
        candidate = Path(directory) / 'diagnostic.bin'
        candidate.write_bytes(embedded)
        rebuilt, rebuilt_plan = fetch.build_arena(candidate, 0x40077000, memory_group=6)
    if rebuilt != patched_arena or rebuilt_plan != plan or len(embedded) != len(firmware):
        raise ValueError('container patch differs from the verified reset-store arena')
    patch.update(container_patch_offset=offset, original_container_sha256=digest(firmware),
                 embedded_container_sha256=digest(embedded), diagnostic_only=True)
    return embedded, patch

def diagnostic_adt(data, build_id=0x2333):
    root, end = adt.parse(data)
    if end != len(data):
        raise ValueError('trailing ADT bytes')
    chosen = next(c for c in root.children if c.name == 'chosen')
    for key in ('sweet-gpu-report', 'sweet-csf-report', 'sweet-gpu-autorecovery-seconds'):
        if chosen.prop(key) is not None:
            raise ValueError('already a GPU diagnostic ADT')
    chosen.props = [(n, f, ('sweet-shim/gpu%x' % build_id).encode().ljust(128, b'\0')
                     if n in ('firmware-version', 'system-firmware-version') else v)
                    for n, f, v in chosen.props]
    chosen.props += [('sweet-gpu-report', 0, bytes(128)),
                     ('sweet-csf-report', 0, bytes(696)),
                     ('sweet-gpu-autorecovery-seconds', 0, struct.pack('<I', 60))]
    return adt.serialize(root)

def build(a):
    out = Path(a.out).resolve()
    out.relative_to(ROOT / 'research')
    if out.exists():
        raise ValueError('refuse existing output directory')
    kernel = pinned(a.kernel, a.kernel_sha256)
    if a.build_id == 0x2338 and not (a.entry_probe and a.inline_entry and a.entry_pte_guard):
        raise ValueError('build2338 must preserve the2337 CSF probe configuration')
    if a.fault_probe:
        if a.redirect_mcu_stores or a.entry_probe or a.inline_entry or a.entry_pte_guard or a.reset_store_stub:
            raise ValueError('the fault vector probe replaces the handler and takes no other patch')
        firmware, reset_patch = fault_vector_probe(a.firmware, a.firmware_sha256, a.build_id)
    else:
        firmware, reset_patch = diagnostic_firmware(a.firmware, a.firmware_sha256,
                                                   a.build_id, a.reset_store_stub, a.entry_probe,
                                                   a.inline_entry, a.entry_pte_guard,
                                                   a.redirect_mcu_stores)
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
    label = 'gpu%x' % a.build_id
    command = command.replace('sweettrial=2317', 'sweettrial=%x' % a.build_id)
    command = command.replace('rootrw=1', 'rootrw=0').replace('ufsrw=1', 'ufsrw=0')
    tree = diagnostic_adt(original_adt, a.build_id)
    out.mkdir(parents=True)
    (out / (label + '.adt')).write_bytes(tree)
    payload, _ = mkpayload.build(Path(a.kernel), out / (label + '.adt'), command,
                                 allow_matisse_root_write=False)
    (out / (label + '.payload')).write_bytes(payload)
    ndk = Path(a.ndk)
    if a.dvfs_commit == 'off':
        dvfs = ['-DSWEET_GPU_DVFS_COMMIT=0']
    elif a.dvfs_commit == 'current':
        dvfs = ['-DSWEET_GPU_DVFS_COMMIT=1', '-DSWEET_GPU_DVFS_COMMIT_OPP=-1']
    else:
        index = int(a.dvfs_commit, 0)
        if not 0 <= index < 64:
            raise ValueError('dvfs-commit index out of range')
        dvfs = ['-DSWEET_GPU_DVFS_COMMIT=1', '-DSWEET_GPU_DVFS_COMMIT_OPP=%d' % index]
    definitions = ['-DSHIM_GPU_PROBE', '-DSHIM_CSF_PROBE', '-DSHIM_RECOVERY_FALLBACK',
                   '-DSHIM_RECOVERY_OFFSET=' + str(FALLBACK_OFFSET),
                   '-DSWEET_SHIM_BUILD_LABEL="%x"' % a.build_id,
                   *dvfs,
                   '-DEMBEDDED_XNU_BYTES=' + str(len(payload))]
    if a.entry_probe:
        definitions.append('-DSHIM_CSF_ENTRY_PROBE')
    if a.inline_entry:
        definitions.append('-DSHIM_CSF_INLINE_ENTRY_PROBE')
    if a.entry_pte_guard:
        definitions.append('-DSHIM_CSF_ENTRY_PTE_GUARD')
    if a.build_id in MCU_ACCESS_REDIRECTS:
        # Sample shared+0xffc without installing any entry overlay: the marker
        # is now written by the original reset handler itself.
        definitions.append('-DSHIM_CSF_ENTRY_CHECKPOINT')
    source = {'start': ROOT / 'shim/start.S', 'loader': ROOT / 'shim/loader.c',
              'gpu': ROOT / 'shim/gpu.c', 'gpueb_boot': ROOT / 'xnu/gpu/mtk_gpueb_boot.c',
              'gpueb_protocol': ROOT / 'xnu/gpu/mtk_gpueb_protocol.c',
              'gpufreq': ROOT / 'xnu/gpu/mtk_gpufreq.c',
              'csf': ROOT / 'shim/csf.c', 'csf_memory': ROOT / 'xnu/gpu/mali_csf_memory.c',
              'csf_firmware': ROOT / 'xnu/gpu/mali_csf_firmware.c', 'csf_boot': ROOT / 'xnu/gpu/mali_csf_boot.c'}
    for name, path in source.items():
        subprocess.run([str(ndk / 'clang'), *FLAGS, *definitions, '-c', str(path),
                        '-o', str(out / (name + '.o'))], check=True)
        relocs = subprocess.check_output([str(ndk / 'llvm-readelf'), '-r', str(out / (name + '.o'))], text=True)
        if name != 'start' and 'R_AARCH64_ABS64' in relocs:
            raise ValueError('absolute pointer in position-independent shim: ' + name)
    (out / 'csf.bin').write_bytes(firmware)
    assembly = '.section .rodata.csf,"a"\n.balign 8\n.global sweet_csf_blob_start\nsweet_csf_blob_start:\n.incbin "' + str(out / 'csf.bin') + '"\n.global sweet_csf_blob_end\nsweet_csf_blob_end:\n'
    (out / 'csf_blob.S').write_text(assembly)
    subprocess.run([str(ndk / 'clang'), *FLAGS, '-c', str(out / 'csf_blob.S'), '-o', str(out / 'csf_blob.o')],check=True)
    names = ['start' ,'shim','console','display','diag','mmu','fdt','board','loader',
             'ufs','str','logstore','gpu','gpueb_boot','gpueb_protocol','gpufreq','csf','csf_memory','csf_firmware','csf_boot','csf_blob']
    objects = [out / (n + '.o') if n in source or n == 'csf_blob' else frozen / 'out' / (n + '.o') for n in names]
    subprocess.run([str(ndk / 'clang'), *FLAGS, '-static', '-T', str(frozen / 'shim.ld'),
                    '-fuse-ld=lld', '-Wl,--build-id=none', *map(str, objects),
                    '-o', str(out / 'shim.elf')], check=True)
    subprocess.run([str(ndk / 'llvm-objcopy'), '-O', 'binary', str(out / 'shim.elf'),
                    str(out / 'Image-bare')], check=True)
    symbols = subprocess.check_output([str(ndk / 'llvm-nm'), str(out / 'shim.elf')], text=True)
    symbol = {line.split()[-1]:int(line.split()[0],16) for line in symbols.splitlines()
              if len(line.split()) == 3 and line.split()[0] != 'U'}
    end = symbol['_end']
    arena = symbol['arena']
    if arena & 4095 or arena < symbol['_bss_start'] or arena + (2 << 20) > symbol['_bss_end']:
        raise ValueError('CSF arena is outside the aligned shim BSS')
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
    image = out / ('matisse-shim-' + label + '.img')
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
    info = dict(trial=hex(a.build_id), image_bytes=len(result), image_sha256=digest(result),
                kernel_sha256=digest(kernel), adt_sha256=digest(tree), payload_sha256=digest(payload),
                expanded_bytes=len(raw), fallback_offset=FALLBACK_OFFSET,
                fallback_linux_sha256=digest(stock_linux), stock_sha256=digest(stock),
                ramdisk_sha256=digest(ramdisk), signature_sha256=digest(header['signature']),
                signature_authenticated=False, cmdline=command,
                frozen_objects={p.name:digest(p.read_bytes()) for p in objects if p.parent == frozen / 'out'},
                sources={str(p.relative_to(ROOT)):digest(p.read_bytes()) for p in source.values()},
                autorecovery_seconds=60, automatic_recovery_verified=False,
                gpu_csf_firmware_embedded_sha256=digest(firmware), gpu_csf_boot_hardware_verified=False)
    info['csf_leaf_memory_group'] = 6
    info['gpu_boot_report_bytes'] = 112
    info['gpufreq_dvfs'] = dict(commit=a.dvfs_commit, definitions=dvfs,
                                report_abi='2338', hardware_verified=False)
    info['csf_mapping_metadata_hardware_readback'] = False
    info['csf_arena'] = dict(shim_offset=arena, bytes=2 << 20,
                             bss_end=symbol['_bss_end'], shim_end=end,
                             payload_offset=end + 16, cpu_cache_policy='MMU/cache off')
    if reset_patch and a.build_id == 0x2334:
        if arena != 0x77000:
            raise ValueError('reset-store trial must preserve the measured2333 arena placement')
        info['reset_store_stub'] = reset_patch
        info['reset_store_stub']['source_sha256'] = {
            name: digest((ROOT / name).read_bytes()) for name in
            ('tools/matisse-csf-reset-store.S', 'tools/matisse-csf-fetch-audit.py',
             'tools/matisse-shim-gpu-image.py')}
    if a.build_id in MCU_ACCESS_REDIRECTS:
        if reset_patch is None:
            raise ValueError('build%x requires the MCU access redirect' % a.build_id)
        # No entry-probe translation unit is compiled in, so the shim text
        # shrinks by the same page the2338 probe added and the anchor returns
        # to the2334 measurement. Pin it rather than dropping the check.
        if arena != 0x77000:
            raise ValueError('redirect builds must keep the measured pre-probe arena placement '
                             '(expected 0x77000, got %#x)' % arena)
        info['mcu_store_redirect'] = reset_patch
        info['mcu_store_redirect']['source_sha256'] = {
            name: digest((ROOT / name).read_bytes()) for name in
            ('xnu/gpu/mali_csf_boot.c', 'tools/matisse-csf-fetch-audit.py',
             'tools/matisse-shim-gpu-image.py')}
    if a.build_id in FAULT_VECTOR_PROBE:
        if reset_patch is None:
            raise ValueError('build%x requires the fault vector probe' % a.build_id)
        if arena != 0x77000:
            raise ValueError('fault probe builds must keep the measured pre-probe arena placement '
                             '(expected 0x77000, got %#x)' % arena)
        info['fault_vector_probe'] = reset_patch
        info['fault_vector_probe']['source_sha256'] = {
            name: digest((ROOT / name).read_bytes()) for name in
            ('tools/matisse-csf-fetch-audit.py', 'tools/matisse-shim-gpu-image.py')}
    if a.entry_probe:
        # The gpufreq layer adds one page of shim text, so from2338 the arena
        # anchor moves by exactly0x1000. Pinning it per build keeps the drift
        # check meaningful instead of dropping it.
        expected_arena = 0x78000 if a.build_id >= 0x2338 else 0x77000
        if arena != expected_arena:
            raise ValueError('entry trial must preserve the measured arena placement '
                             'for build %#x (expected %#x, got %#x)' % (a.build_id, expected_arena, arena))
        spec = importlib.util.spec_from_file_location('entry_fetch', ROOT / 'tools/matisse-csf-fetch-audit.py')
        fetch = importlib.util.module_from_spec(spec); spec.loader.exec_module(fetch)
        original, plan = fetch.build_arena(Path(a.firmware), 0x40000000 + arena, memory_group=6)
        patched, probe_plan = fetch.build_arena(Path(a.firmware), 0x40000000 + arena,
                                               memory_group=6, entry_probe=True, inline_entry=a.inline_entry)
        if plan != probe_plan:
            raise ValueError('entry probe changed firmware mappings')
        info['entry_probe'] = fetch.entry_probe_metadata(original, patched, plan, inline_entry=a.inline_entry)
        info['entry_probe']['arena_sha256'] = digest(patched)
        info['entry_probe']['original_arena_sha256'] = digest(original)
        info['entry_probe']['source_sha256'] = {name: digest((ROOT / name).read_bytes()) for name in
            ('tools/matisse-csf-entry-probe.S', 'tools/matisse-csf-fetch-audit.py',
             'xnu/gpu/mali_csf_entry_probe.h', 'xnu/gpu/mali_csf_boot.h', 'tools/matisse-shim-gpu-image.py')}
        if a.entry_pte_guard:
            info['entry_pte_guard'] = dict(pre_auto=True, reset_entry_va='0x10018ec',
                expected_entry_word='0x4803b672',
                source_sha256=digest((ROOT / 'xnu/gpu/mali_csf_entry_guard.h').read_bytes()))
        info['firmware_sections'] = fetch.firmware_sections(firmware)
    (out / 'manifest.json').write_text(json.dumps(info, indent=2) + '\n')
    print(json.dumps(info, indent=2))

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--build-id', type=lambda s:int(s,0), choices=(0x2333,0x2334,0x2335,0x2336,0x2337,0x2338,0x2339,0x2340,0x2341,0x2342,0x2343), default=0x2333)
    p.add_argument('--reset-store-stub', action='store_true',
                   help='build2334 only: replace20 Thumb reset-entry bytes; no firmware-readiness claim')
    p.add_argument('--entry-probe', action='store_true',
                   help='build2335 only: mark a separate word and continue the original reset path')
    p.add_argument('--inline-entry', action='store_true',
                   help='build2336/2337: inline STUB before remote fetch, then TRAM in tail')
    p.add_argument('--entry-pte-guard', action='store_true',
                   help='build2337/2338 only: reject PTE/backing mismatch before MCU_CONTROL')
    p.add_argument('--fault-probe', action='store_true',
                   help='build2343 only: replace the shared fault vector entry with a stub that '
                        'records the stacked PC in shared+0x10, leaving the entry untouched')
    p.add_argument('--redirect-mcu-stores', action='store_true',
                   help='build2339/2340 only: repoint the reset handler\'s MCU peripheral access '
                        'literals at shared words, leaving the original code intact')
    p.add_argument('--dvfs-commit', default='off', metavar='{off,current,<oppidx>}',
                   help='send CMD_COMMIT after POWER_ON: off (default), current (the '
                        'index GPUEB already reports, no frequency change), or an index')
    for key in ('firmware','firmware-sha256','kernel','kernel-sha256','template','template-sha256','adt','adt-sha256',
                'stock','stock-sha256','frozen','cmdline','ndk','out'):
        p.add_argument('--' + key, required=True)
    build(p.parse_args())

if __name__ == '__main__':
    main()
