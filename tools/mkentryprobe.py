#!/usr/bin/env python3
"""Wrap a known-good arm64 boot v4 with a same-boot entry/FDT probe.

The prefix records entry registers into the bundled Linux Image's banner,
then runs that Linux kernel at a 2 MiB-aligned address. Read SWEET-ENTRY in
recovery dmesg. It does not need UART, display, UFS, or persistent reset logs.
The source boot image is never modified. Flashing is deliberately separate.
"""
import argparse
import gzip
import hashlib
import json
import os
from pathlib import Path
import shutil
import struct
import subprocess
import tempfile

import mkbootimg
from xnu_breakpoint import early_vector_pa, high_vector_pa, high_vector_sync_va, bootstrap_clean_range, bootstrap_ttbr0_pa

PREFIX_SIZE = 2 << 20
# `sctlr` is SCTLR_EL1 at the shim entry point, i.e. the controls LK handed
# over (the probe clears M/C/I first, so it normally reads 0x30d00980). It is a
# handoff snapshot, NOT the state XNU runs in: by the time a BRK checkpoint in
# the kernel fires, XNU has installed its own SCTLR_EL1 with M/C/I set. Do not
# read this field as evidence about the running kernel's MMU or caches.
FIELDS = ('el', 'midr', 'mpidr', 'freq', 'dtb', 'sctlr', 'stage',
          'fault', 'esr', 'far', 'pc', 'gicd', 'vtimer', 'fb', 'x0',
          'x16', 'spsr')
DISPLAY_RECORD_FIELDS = tuple('0123456789abcdefghijk')
DISPLAY_LEVELS = ('display', 'display-kick', 'xnu')
LEVELS = {'entry': 0, 'board': 1, 'logstore': 2, 'mmu': 3, 'timer': 4, 'irq': 5,
          'display': 6, 'display-kick': 6, 'xnu': 6, 'el1-display': 7,
          'el1-xnu': 7, 'el1-load': 7, 'usb': 1, 'gpueb': 1}
UFS_QUERY_MODES = {'full': 0, 'none': 1, 'read': 2, 'set': 3, 'power': 4}

# For display levels the banner holds (first u32 << 32 | second u32) per
# field. All bases are live-FDT lookups. Field K is the status word:
# (stage << 16) | code. Codes:
#   0 ok, 1 FDT node missing, 2 DSI clock gates report off,
#   3 DSI not in the expected LK command/DSC state, 4 OVL not scanning the
#   boot framebuffer, 5 DSI cmd-mode buffer disabled, 6 no TE pulse,
#   7 frame not completed, 8 some frames missed.
# display-kick overwrites I/J with the refresh result:
#   I = last INTSTA << 32 | completed frames
#   J = TE seen << 32 | status code
DISPLAY_FIELDS = {
    '0': ('dsi0.CON_CTRL', 'dsi0.MODE_CTRL'),
    '1': ('dsi0.START', 'dsi0.INTSTA'),
    '2': ('dsi0.TXRX_CTRL', 'dsi0.PSCTRL'),
    '3': ('dsi0.CMDQ_SIZE', 'dsi0.SIZE_CON'),
    '4': ('dsi0.MEM_CONTI', 'dsi0.BUF_CON0'),
    '5': ('dsi0.BUF_CON1', 'dsi0.TX_BUF_RW_TIMES'),
    '6': ('dsi0.CMD_TYPE1_HS', 'dsi0.DEBUG_SEL'),
    '7': ('dsi0.PHY_LCCON', 'dsi0.PHY_LD0CON'),
    '8': ('mipi.PLL_PWR', 'mipi.PLL_CON0'),
    '9': ('dsi0.VACT_NL', 'dsi0.PHY_TIMECON0'),
    'a': ('dispsys.clk_gate0_status', 'dispsys.clk_gate1_status'),
    'b': ('dispsys.clk_gate2_status', 'disp_mutex0.CFG'),
    'c': ('disp_ovl0_2l.EN', 'disp_ovl0_2l.L0_ADDR'),
    'd': ('disp_ovl0_2l.L0_PITCH', 'disp_ovl0_2l.CON0'),
    'e': ('disp_ovl0_2l.SRC_CON', 'disp_ovl0_2l.SRC_SIZE0'),
    'f': ('disp_mutex0.EN', 'disp_mutex0.SOF'),
    'g': ('disp_mutex0.MOD0', 'disp_mutex0.MOD1'),
    'h': ('disp_mutex0.INTEN', 'disp_mutex0.INTSTA'),
    'i': ('GCE thread 3 CURR_STATUS', 'GCE thread 3 WAIT_TOKEN'),
    'j': ('GCE thread 5 CURR_STATUS', 'GCE thread 5 WAIT_TOKEN'),
    'k': ('status', 'status'),
}

DISPLAY_STATUS_CODES = {
    0: 'ok', 1: 'FDT node missing', 2: 'DSI clock gates off',
    3: 'unexpected DSI state', 4: 'OVL not scanning boot fb',
    5: 'cmd-mode buffer disabled', 6: 'no TE pulse',
    7: 'frame not completed', 8: 'some frames missed',
}

DISPLAY_SECONDARY = {
    'display-kick': {
        'i': ('kick last INTSTA', 'kick completed frames'),
        'j': ('kick TE seen', 'kick status code'),
    },
}

# usb level: read-only MTU3 snapshot at LK handoff, taken after board_probe
# from the live usb0 node (compatible mediatek,mtu3; reg-names mac, ippc).
# Each field holds (first register << 32) | second register; offsets follow
# the vendor mtu3_hw_regs.h with the DT-provided base. Stage is
# (0x60 << 16) | code: 0 ok, 1 no MTU3 node, 2 unusable mac/ippc reg.
# A read fault leaves stage at 0x5f and fills the recorder fields instead.
# PW_CTRL2 DEV_PDN, U3/U2 PORT_PDN|DIS, PW_STS1 PLL/reset status,
# OTG_STS VBUS_VALID and POWER_MANAGEMENT SOFT_CONN answer whether LK left
# the controller powered, clocked and connected; HW_ID/HW_SUB_ID identify
# the IP revision for the XNU driver.
USB_FIELDS = {
    'gicd': ('IPPC.PW_CTRL0', 'IPPC.PW_CTRL1'),
    'vtimer': ('IPPC.PW_CTRL2', 'IPPC.PW_CTRL3'),
    'fb': ('IPPC.PW_STS1', 'IPPC.PW_STS2'),
    'dtb': ('IPPC.OTG_STS', 'IPPC.SPM_CTRL'),
    'sctlr': ('IPPC.U3_CTRL_0P', 'IPPC.U2_CTRL_0P'),
    'esr': ('IPPC.REF_CK_CTRL', 'IPPC.DEV_RST_CTRL'),
    'far': ('IPPC.HW_ID', 'IPPC.HW_SUB_ID'),
    'pc': ('MAC.DEVICE_CONF', 'MAC.MISC_CTRL'),
    'fault': ('MAC.POWER_MANAGEMENT', 'MAC.DEVICE_CONTROL'),
    'x0': ('MAC.USB3_CONFIG', 'MAC.LINK_STATE_MACHINE'),
    'x16': ('MAC.LV1ISR', 'MAC.LV1IER'),
    'spsr': ('MAC.EP0CSR', 'MAC.RXCOUNT0'),
}

USB_STATUS_CODES = {
    0: 'ok', 1: 'no MTU3 node', 2: 'unusable mac/ippc reg',
    3: 'device power domain down, MAC not read',
    0x5f: 'read faulted before completion',
}

GPUEB_FIELDS = {
    'gicd': 'Mali MMIO base from DT (not read)',
    'vtimer': 'Mali MMIO bytes from DT',
    'fb': 'GPUEB runtime memory base from DT',
    'x16': 'GPUEB runtime memory bytes from DT',
    'x0': 'LK atag boot mode (UINT64_MAX if unavailable)',
    'far': 'GPUFREQ status PA (not dereferenced)',
    'pc': 'GPUFREQ debug PA (not dereferenced)',
    'spsr': 'status bytes << 32 | debug bytes',
}
GPUEB_STATUS_CODES = {
    0x9000: 'memory described; reservation/firmware readiness unverified',
    0x9001: 'no GPUEB node',
    0x9002: 'GPUEB disabled',
    0x9003: 'GPUEB support property malformed',
    0x9004: 'runtime memory properties missing/malformed',
    0x9005: 'GPUFREQ region malformed or out of bounds',
}


def decode_display_status(value):
    return {'stage': value >> 16, 'code': value & 0xffff,
            'code_name': DISPLAY_STATUS_CODES.get(value & 0xffff, 'unknown')}


def banner_record(level=None):
    display = level in DISPLAY_LEVELS
    record = bytearray(b'SWTX1' if display else b'SWEET-ENTRY v1')
    offsets = {}
    fields = DISPLAY_RECORD_FIELDS if display else FIELDS
    for name in fields:
        record += (' ' + name + '=').encode()
        offsets[name] = len(record)
        record += b'0' * 16
    record += b'\n\0'
    return bytes(record), offsets


def prepare(template, level=None):
    """Validate all source ranges and placement constraints before building."""
    header = mkbootimg.parse(template)
    if header['header_version'] != 4:
        raise ValueError('entry probe currently requires a boot v4 template')
    ks, rs = header['kernel_size'], header['ramdisk_size']
    rd_off = mkbootimg.PAGE + mkbootimg.pad(ks)
    if ks < 64 or rd_off + rs > len(template):
        raise ValueError('truncated kernel or ramdisk in template')
    compressed = template[mkbootimg.PAGE:mkbootimg.PAGE + ks]
    image = bytearray(gzip.decompress(compressed) if compressed[:2] == b'\x1f\x8b'
                      else compressed)
    if len(image) < 64 or image[56:60] != b'ARM\x64':
        raise ValueError('template kernel is not an arm64 Linux Image')
    text_offset, image_size, flags = struct.unpack_from('<3Q', image, 8)
    if text_offset or not image_size or flags & 1 or not flags & 8:
        raise ValueError('need LE Image with text_offset=0 and anywhere-placement flag')
    record, offsets = banner_record(level)
    # Do not patch the short "Linux version %s (%s)" printf format string.
    candidates = []
    at = 0
    while True:
        at = image.find(b'Linux version ', at)
        if at < 0:
            break
        end = image.find(b'\0', at)
        if end >= 0 and end - at + 1 >= len(record) and b'%' not in image[at:end]:
            candidates.append((at, end + 1))
        at += 1
    if len(candidates) != 1:
        raise ValueError('cannot uniquely locate a Linux banner large enough for probe')
    start, end = candidates[0]
    original_banner = bytes(image[start:end])
    image[start:end] = record + bytes(end - start - len(record))
    return header, image, template[rd_off:rd_off + rs], start, offsets, original_banner


def build(template_path, out_path, toolchain, level, max_image_size=None, payload_path=None,
          xnu_vector_offset=None, xnu_high_vector_offset=None, xnu_clean=False,
          xnu_clean_limit=None, xnu_restore_ttbr0=None, xnu_selective=False,
          xnu_el0_syscall=None, ufs_regs=False, ufs_test=False, ufs_init=False,
          ufs_query='full'):
    template = Path(template_path).read_bytes()
    header, image, ramdisk, banner_at, offsets, old_banner = prepare(template, level)
    image_size = PREFIX_SIZE + max(len(image), struct.unpack_from('<Q', image, 16)[0])
    payload = Path(payload_path).read_bytes() if payload_path else None
    if (level in ('el1-xnu', 'el1-load')) != (payload is not None):
        raise ValueError('el1-xnu/el1-load require --payload; other levels do not accept it')
    if ufs_regs and level not in ('el1-xnu', 'el1-load'):
        raise ValueError('UFS register snapshot requires el1-xnu or el1-load')
    if ufs_test and level != 'el1-load':
        raise ValueError('UFS selftest requires el1-load (it claims the host)')
    if ufs_init and level not in ('el1-xnu', 'el1-load'):
        raise ValueError('UFS pre-init requires el1-xnu or el1-load')
    if ufs_query not in UFS_QUERY_MODES:
        raise ValueError('unknown UFS query mode')
    if ufs_query != 'full' and not ufs_init:
        raise ValueError('UFS query mode requires --ufs-init')
    vector_pa = None
    if xnu_vector_offset is not None:
        if level != 'el1-xnu':
            raise ValueError('early-vector relay requires el1-xnu')
        vector_pa = early_vector_pa(payload, xnu_vector_offset)
    high_pa = None
    if xnu_high_vector_offset is not None:
        if vector_pa is None:
            raise ValueError('high-vector relay requires the early-vector relay')
        high_pa = high_vector_pa(payload, xnu_high_vector_offset)
    clean_range = None
    if xnu_clean:
        if high_pa is None:
            raise ValueError('cache cleanup requires the high-vector relay')
        clean_range = bootstrap_clean_range(payload, xnu_clean_limit)
    elif xnu_clean_limit is not None:
        raise ValueError('cache-clean limit requires --xnu-clean')
    restore_ttbr0 = None
    if xnu_restore_ttbr0 is not None:
        if clean_range is None:
            raise ValueError('TTBR0 restoration requires high vectors and cache cleanup')
        restore_ttbr0 = bootstrap_ttbr0_pa(payload, xnu_restore_ttbr0)
        if not clean_range[0] <= restore_ttbr0 < restore_ttbr0 + 0x4000 <= clean_range[1]:
            raise ValueError('bootstrap TTBR0 page must be inside cache-clean range')
    high_va = None
    if xnu_selective:
        if high_pa is None or clean_range is None or restore_ttbr0 is None:
            raise ValueError('selective vectors require high vectors, cache cleanup and TTBR0 restore')
        high_va = high_vector_sync_va(payload, xnu_high_vector_offset,
                                      el0=xnu_el0_syscall is not None)
    if xnu_el0_syscall is not None:
        if not xnu_selective:
            raise ValueError('EL0 syscall trap requires selective vectors')
        if not 0 <= xnu_el0_syscall <= 0xffff:
            raise ValueError('EL0 syscall number must be 0..0xffff')
    payload_offset = None
    if payload is not None:
        if len(payload) < 0x2a8 or payload[:8] != b'SWEETXNU':
            raise ValueError('invalid SWEETXNU payload')
        payload_offset = (image_size + 4095) & ~4095
        image_size = payload_offset + 16 + len(payload)
    if max_image_size is not None and image_size > max_image_size:
        raise ValueError('wrapped Image exceeds caller-supplied safe load window')
    out_path = Path(out_path).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    repo = Path(__file__).resolve().parent.parent
    cc = str(Path(toolchain) / 'clang') if toolchain else shutil.which('clang')
    objcopy = str(Path(toolchain) / 'llvm-objcopy') if toolchain else shutil.which('llvm-objcopy')
    if not cc or not objcopy:
        raise ValueError('pass --toolchain with clang, ld.lld, and llvm-objcopy')
    with tempfile.TemporaryDirectory(prefix='entryprobe-', dir=out_path.parent) as tmp:
        tmp = Path(tmp)
        config = f'#define ENTRY_LEVEL {LEVELS[level]}\n'
        config += f'#define ENTRY_IMAGE_SIZE {image_size}\n'
        config += f'#define ENTRY_BANNER_OFFSET {banner_at}\n'
        config += f'#define ENTRY_BANNER_SIZE {len(banner_record(level)[0])}\n'
        config += ''.join(f'#define ENTRY_{n.upper()} {o}\n' for n, o in offsets.items())
        if level in DISPLAY_LEVELS:
            # The assembly always stages EL/MIDR/MPIDR/FREQ and a progress
            # marker, and its fault path records ESR/FAR/PC. Map those onto
            # the compact record; C overwrites the data fields afterwards and
            # keeps its last status in K even if a fault occurs later.
            for old, new in (('EL', '0'), ('MIDR', '1'), ('MPIDR', '2'),
                             ('FREQ', '3'), ('DTB', '4'), ('SCTLR', '5'),
                             ('STAGE', 'K'), ('FAULT', 'J'),
                             ('ESR', 'H'), ('FAR', 'I'), ('PC', 'J'),
                             ('GICD', 'A'), ('VTIMER', 'B'), ('FB', 'C')):
                config += f'#define ENTRY_{old} ENTRY_{new}\n'
        if level in ('display-kick', 'xnu'):
            config += '#define ENTRY_DISPLAY_KICK 1\n'
        if level == 'xnu':
            config += '#define ENTRY_XNU 1\n'
        if level in ('el1-display', 'el1-xnu', 'el1-load'):
            config += '#define ENTRY_EL1_DISPLAY 1\n'
        if level in ('el1-xnu', 'el1-load'):
            config += '#define ENTRY_LOADER_PROBE 1\n'
        if vector_pa is not None:
            config += f'#define ENTRY_XNU_VECTOR_PA {vector_pa:#x}ULL\n'
        if high_pa is not None:
            config += f'#define ENTRY_XNU_HIGH_VECTOR_PA {high_pa:#x}ULL\n'
        if clean_range is not None:
            config += f'#define ENTRY_XNU_CLEAN_START {clean_range[0]:#x}\n'
            config += f'#define ENTRY_XNU_CLEAN_END {clean_range[1]:#x}\n'
        if restore_ttbr0 is not None:
            config += f'#define ENTRY_XNU_RESTORE_TTBR0 {restore_ttbr0:#x}\n'
        if xnu_selective:
            config += '#define ENTRY_XNU_SELECTIVE 1\n'
            config += f'#define ENTRY_XNU_HIGH_VECTOR_VA {high_va:#x}ULL\n'
        if xnu_el0_syscall is not None:
            config += f'#define ENTRY_EL0_SYSCALL {xnu_el0_syscall}\n'
        if ufs_regs:
            config += '#define ENTRY_UFS_REGS 1\n'
        if ufs_test:
            config += '#define ENTRY_UFS_TEST 1\n'
        if ufs_init:
            config += '#define ENTRY_UFS_INIT 1\n'
            config += f'#define ENTRY_UFS_QUERY_MODE {UFS_QUERY_MODES[ufs_query]}\n'
        if level == 'usb':
            config += '#define ENTRY_USB_SNAPSHOT 1\n'
        if level == 'gpueb':
            config += '#define ENTRY_GPUEB_SNAPSHOT 1\n'
        (tmp / 'entryprobe_config.h').write_text(config)
        linker = '''ENTRY(_head)
SECTIONS {
 . = 0;
 .text : { *(.text.head) *(.text*) }
 .rodata : { *(.rodata*) }
 .data : { *(.data*) }
 .bss : { *(.bss*) *(COMMON) }
 . = ALIGN(16);
 _end = .;
 ASSERT(. <= 0x200000, "probe exceeds prefix")
 stock_image = 0x200000;
 /DISCARD/ : { *(.comment) *(.note*) *(.eh_frame*) }
}
'''
        if payload_offset is not None:
            linker = linker.replace('_end = .;', f'_end = {payload_offset};')
        if restore_ttbr0 is not None:
            linker += '\nASSERT(probe_mmu_code_end - probe_mmu_vector <= 128, "shared relay overlaps vector 1")\n'
            linker += 'ASSERT(probe_mmu_literals_end - probe_mmu_vector <= 256, "shared literals overlap vector 2")\n'
            linker += 'ASSERT(probe_mmu_vector_end - probe_mmu_vector == 2048, "shared vector table size")\n'
            if xnu_selective:
                linker += 'ASSERT(probe_sel_stub_end - probe_sel_stub <= 128, "selective stub exceeds vector slot")\n'
        elif high_pa is not None:
            linker += '\nASSERT(probe_mmu_vector_end - probe_mmu_vector <= 128, "MMU relay exceeds vector slot")\n'
        (tmp / 'probe.ld').write_text(linker)
        sources = ['entryprobe.S']
        if LEVELS[level]:
            sources += ['entryprobe.c', 'board.c', 'fdt.c', 'str.c', 'logstore.c']
        if level == 'gpueb':
            sources += ['entryprobe_gpueb.c', '../xnu/gpu/mtk_gpueb_protocol.c']
        if 3 <= LEVELS[level] < 6:
            sources += ['mmu.c']
        if 4 <= LEVELS[level] < 6:
            sources += ['entryprobe_timer.c']
        if level in DISPLAY_LEVELS:
            sources += ['entryprobe_display.c']
        if level in ('display-kick', 'xnu', 'el1-display', 'el1-xnu', 'el1-load'):
            sources += ['console.c']
        if level in ('el1-display', 'el1-xnu', 'el1-load'):
            sources += ['display.c']
        if level in ('xnu', 'el1-xnu', 'el1-load'):
            sources += ['loader.c']
        if ufs_test or ufs_init:
            sources += ['ufs.c']
        objects = []
        flags = ['--target=aarch64-none-elf', '-O2', '-ffreestanding', '-nostdlib',
                 '-fno-pic', '-mgeneral-regs-only', '-mstrict-align',
                 '-fno-stack-protector', '-fno-builtin', '-Wall', '-Wextra', '-Werror',
                 '-I' + str(tmp), '-I' + str(repo / 'shim')]
        if payload is not None:
            flags += [f'-DEMBEDDED_XNU_BYTES={len(payload)}']
        if level == 'el1-load':
            flags += ['-DLOADER_NO_JUMP']
        for source in sources:
            obj = tmp / (Path(source).name + '.o')
            subprocess.run([cc, *flags, '-c', str(repo / 'shim' / source), '-o', str(obj)], check=True)
            objects.append(str(obj))
        elf = tmp / 'probe.elf'
        subprocess.run([cc, *flags, '-static', '-fuse-ld=lld', '-Wl,--build-id=none',
                        '-T', str(tmp / 'probe.ld'), *objects, '-o', str(elf)], check=True)
        raw = tmp / 'probe.bin'
        subprocess.run([objcopy, '-O', 'binary', str(elf), str(raw)], check=True)
        prefix = raw.read_bytes()
        if len(prefix) > PREFIX_SIZE:
            raise ValueError('probe larger than prefix')
        wrapped = prefix + bytes(PREFIX_SIZE - len(prefix)) + image
        if payload is not None:
            wrapped += bytes(payload_offset - len(wrapped))
            wrapped += b'SWEETAPP' + struct.pack('<Q', len(payload)) + payload
        wrapped += bytes(image_size - len(wrapped))
        packed = gzip.compress(wrapped, compresslevel=9, mtime=0)
        mkbootimg.build(packed, ramdisk, header['cmdline'].decode(), str(out_path),
                        header_version=4, os_version=header['os_version'],
                        signature_size=header['signature_size'], signature=header['signature'])
        shutil.copyfile(elf, out_path.with_suffix('.elf'))
    manifest = {
        'level': level, 'source_boot_sha256': hashlib.sha256(template).hexdigest(),
        'boot_sha256': hashlib.sha256(out_path.read_bytes()).hexdigest(),
        'boot_bytes': out_path.stat().st_size, 'image_size': image_size,
        'stock_entry_offset': PREFIX_SIZE, 'banner_offset_in_stock_image': banner_at,
        'payload_offset': payload_offset,
        'payload_sha256': hashlib.sha256(payload).hexdigest() if payload else None,
        'xnu_vector_pa': vector_pa,
        'xnu_high_vector_pa': high_pa,
        'xnu_clean_range': clean_range,
        'xnu_restore_ttbr0': restore_ttbr0,
        'xnu_selective': xnu_selective,
        'xnu_high_vector_va': high_va,
        'xnu_el0_syscall': xnu_el0_syscall,
        'ufs_regs': ufs_regs,
        'ufs_test': ufs_test,
        'ufs_init': ufs_init,
        'ufs_query': ufs_query if ufs_init else None,
        'usb_fields': USB_FIELDS if level == 'usb' else None,
        'usb_status_codes': USB_STATUS_CODES if level == 'usb' else None,
        'gpueb_fields': GPUEB_FIELDS if level == 'gpueb' else None,
        'gpueb_status_codes': GPUEB_STATUS_CODES if level == 'gpueb' else None,
        'display_fields': DISPLAY_FIELDS if level in DISPLAY_LEVELS else None,
        'display_secondary': DISPLAY_SECONDARY.get(level),
        'display_status_codes': DISPLAY_STATUS_CODES if level in DISPLAY_LEVELS else None,
        'banner_fields': offsets, 'original_banner': old_banner.rstrip(b'\0').decode(),
    }
    out_path.with_suffix('.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print(json.dumps({k: v for k, v in manifest.items() if k not in ('original_banner', 'banner_fields')}, indent=2))


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--template', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--level', choices=LEVELS, default='entry')
    ap.add_argument('--payload', help='embedded SWEETXNU payload for el1-xnu/el1-load')
    ap.add_argument('--xnu-vector-offset', type=lambda s: int(s, 0),
                    help='diagnostic: relay early XNU vectors at this entry-relative offset; MMU-off only')
    ap.add_argument('--xnu-high-vector-offset', type=lambda s: int(s, 0),
                    help='diagnostic: relay high vectors via an identity alias immediately after MMU enable')
    ap.add_argument('--xnu-clean', action='store_true',
                    help='clean kernel/ADT/boot_args caches before returning from early C; bootstrap map required')
    ap.add_argument('--xnu-clean-limit', type=lambda s: int(s, 0),
                    help='diagnostic: extend cleanup to this page-aligned physical end to cover early VM allocations')
    ap.add_argument('--xnu-restore-ttbr0', type=lambda s: int(s, 0),
                    help='diagnostic: restore this verified bootstrap TTBR0 root on exception; contents and TCR must remain compatible')
    ap.add_argument('--xnu-selective', action='store_true',
                    help='diagnostic: intercept the EL1 synchronous slots and leave all normal XNU vectors intact')
    ap.add_argument('--el0-syscall', type=lambda s: int(s, 0),
                    help='diagnostic: abort at the first EL0 AArch64 SVC with this syscall number')
    ap.add_argument('--ufs-regs', action='store_true',
                    help='read-only UFSHCI snapshot into the board fields before the XNU jump')
    ap.add_argument('--ufs-test', action='store_true',
                    help='run the shim UFS tie-over/TUR/GPT selftest from low memory (el1-load)')
    ap.add_argument('--ufs-init', action='store_true',
                    help='reset host/device and start the UFS link before the XNU jump (el1-xnu/el1-load)')
    ap.add_argument('--ufs-query', choices=UFS_QUERY_MODES, default='full',
                    help='device-init isolation: none, READ_FLAG, SET_FLAG, power-mode repair, or full poll')
    ap.add_argument('--toolchain', default=os.environ.get('LLVM_BIN'))
    ap.add_argument('--max-image-size', type=lambda s: int(s, 0),
                    help='safe load-window size measured from this device; refuse to exceed')
    a = ap.parse_args()
    try:
        build(a.template, a.out, a.toolchain, a.level, a.max_image_size, a.payload,
              a.xnu_vector_offset, a.xnu_high_vector_offset, a.xnu_clean, a.xnu_clean_limit,
              a.xnu_restore_ttbr0, a.xnu_selective, a.el0_syscall, a.ufs_regs,
              a.ufs_test, a.ufs_init, a.ufs_query)
    except (ValueError, OSError) as e:
        ap.error(str(e))


if __name__ == '__main__':
    main()
