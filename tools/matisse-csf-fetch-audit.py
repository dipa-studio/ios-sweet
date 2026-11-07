#!/usr/bin/env python3
"""Replay CSF startup against the arena built by the actual C loader.

Offline only. Synthetic MMIO and Unicorn do not model GPU MMU hardware,
cache coherence, clocks, interrupts or physical DRAM reachability. Never use
this report as proof that the real MCU executed or that its timeout is fixed.
The proprietary input, arena and report belong in ignored research/, not git.
"""
import argparse
from collections import Counter, deque
import hashlib
import importlib
import json
from pathlib import Path
import struct
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
PAGE = 4096
PA_MASK = 0x0000FFFFFFFFF000
FIRMWARE_SHA256 = 'de22d2fc06bc8a859968499a6e609c27fe838be062bf5c97d92ea9f904f7229a'
# Assembled from matisse-csf-reset-store.S; the cross-compile test compares
# the object section with this template. These are Thumb/M-class instructions.
RESET_STORE_CODE = bytes.fromhex('024803490160bff34f8ffee7')
RESET_STORE_MARKER = 0x53545542
RESET_ENTRY = 0x010018ED
ENTRY_PROBE_VA = 0x0100F900
ENTRY_MARKER_VA = 0x04000FFC
HOST_BUILDER = r'''
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include "mali_csf_memory.h"
#include "mali_csf_entry_probe.h"
int main(int argc, char **argv) {
    if (argc != 5 && argc != 6) return 2;
    FILE *f = fopen(argv[1], "rb");
    if (!f || fseek(f, 0, SEEK_END)) return 3;
    long n = ftell(f);
    if (n <= 0 || n > 16777216 || fseek(f, 0, SEEK_SET)) return 4;
    uint8_t *fw = malloc((size_t)n);
    if (!fw || fread(fw, 1, (size_t)n, f) != (size_t)n) return 5;
    fclose(f);
    struct sweet_csf_memory m;
    if (sweet_csf_memory_plan(fw, (size_t)n, &m)) return 6;
    uint8_t *arena = aligned_alloc(4096, m.required_bytes);
    uint64_t root = 0, pa = strtoull(argv[3], NULL, 0);
    if (!arena || sweet_csf_memory_build_group(fw, (size_t)n, &m, arena,
        m.required_bytes, pa, 40, (unsigned)strtoul(argv[4], NULL, 0), &root)) return 7;
    if (argc == 6 && sweet_csf_entry_probe_install_mode(arena, m.required_bytes, &m,
        argv[5][0] == 'i')) return 9;
    f = fopen(argv[2], "wb");
    if (!f || fwrite(arena, 1, m.required_bytes, f) != m.required_bytes) return 8;
    fclose(f);
    printf("{\"root_pa\":%llu,\"required_bytes\":%u,\"table_pages\":%u,"
           "\"protected_skipped\":%u,\"shared_va\":%u,\"shared_bytes\":%u,"
           "\"sections\":[", (unsigned long long)root, m.required_bytes,
           m.table_pages, m.protected_skipped, m.shared_va, m.shared_bytes);
    for (unsigned i = 0; i < m.mapping_count; i++) {
        const struct sweet_csf_mapping *p = &m.map[i];
        printf("%s{\"va\":%u,\"bytes\":%u,\"flags\":%u,\"arena_offset\":%u,"
               "\"data_start\":%u,\"data_bytes\":%u}", i ? "," : "",
               p->va, p->bytes, p->flags, p->arena_offset, p->data_start, p->data_bytes);
    }
    puts("]}");
    free(arena); free(fw);
    return 0;
}
'''


class MappingError(ValueError):
    pass


def translate(arena, root_pa, va):
    """Walk four 4 KiB table levels; reject missing/out-of-arena tables."""
    if va < 0 or va >= 1 << 48 or len(arena) < PAGE:
        raise MappingError('VA or arena outside the supported range')
    table = 0
    for level, shift in enumerate((39, 30, 21, 12)):
        pos = table + ((va >> shift) & 511) * 8
        if pos < 0 or pos + 8 > len(arena):
            raise MappingError('table entry outside the arena')
        desc, = struct.unpack_from('<Q', arena, pos)
        if desc & 3 != 3:
            raise MappingError('missing page/table at level%d' % level)
        pa = desc & PA_MASK
        if level == 3:
            offset = pa - root_pa + (va & (PAGE - 1))
            if offset < 0 or offset >= len(arena):
                raise MappingError('leaf points outside the arena')
            return offset, desc
        # The independent loader emits unrestricted table descriptors. Do not
        # silently ignore hierarchy permissions or unsupported descriptor bits.
        if desc & ~(PA_MASK | 3):
            raise MappingError('unsupported table descriptor flags')
        table = pa - root_pa
        if table < 0 or table % PAGE or table + PAGE > len(arena):
            raise MappingError('next table outside the arena')
    raise MappingError('incomplete translation')


def check_access(arena, root_pa, va, size, operation, unprivileged=False):
    if operation not in ('read', 'write', 'fetch') or size < 1 or va < 0 or va + size > 1 << 48:
        raise MappingError('invalid access')
    stop = va + size
    while va < stop:
        offset, desc = translate(arena, root_pa, va)
        end = min(stop, (va | (PAGE - 1)) + 1)
        if offset + end - va > len(arena) or not desc & (1 << 10):
            raise MappingError('arena bounds or access flag')
        if unprivileged and not desc & (1 << 6):
            raise MappingError('unprivileged access denied')
        if operation == 'write' and desc & (1 << 7):
            raise MappingError('read-only page')
        if operation == 'fetch' and desc & (1 << (54 if unprivileged else 53)):
            raise MappingError('execute-never page')
        va = end


def build_arena(firmware, arena_pa, compiler='cc', memory_group=0, entry_probe=False,
                inline_entry=False, relocate_code=False, mirror_code=False, share_code_l3=False,
                vendor=False):
    if not isinstance(memory_group, int) or not 0 <= memory_group <= 15:
        raise ValueError('memory group must fit four bits')
    with tempfile.TemporaryDirectory(prefix='csf-fetch-') as tmp:
        tmp = Path(tmp)
        source, binary, arena_path = tmp / 'loader.c', tmp / 'loader', tmp / 'arena.bin'
        source.write_text(HOST_BUILDER)
        defines = ['-DSWEET_CSF_RELOCATE_CODE=1'] if relocate_code else []
        if mirror_code:
            defines.append('-DSWEET_CSF_MIRROR_CODE_VA=0x03000000u')
        if share_code_l3:
            defines.append('-DSWEET_CSF_SHARE_CODE_L3_VA=0x05000000u')
        if vendor:
            # The shim compiles both of these on for every 2393+ image; a host
            # rebuild without them reports the default AttrIdx 1 / nG / SH
            # descriptor instead of the one the MCU actually walks.
            defines += ['-DSWEET_CSF_VENDOR_LEAVES=1', '-DSWEET_CSF_VENDOR_MEMATTR=1']
        subprocess.run([compiler, '-std=c11', '-Wall', '-Wextra', '-Werror',
                        '-fsanitize=address,undefined', *defines, '-I', str(ROOT / 'xnu/gpu'),
                        str(source), str(ROOT / 'xnu/gpu/mali_csf_firmware.c'),
                        str(ROOT / 'xnu/gpu/mali_csf_memory.c'), '-o', str(binary)],
                       check=True, capture_output=True, text=True)
        command = [str(binary), str(firmware), str(arena_path), hex(arena_pa), str(memory_group)]
        if entry_probe or inline_entry:
            command.append('inline-entry' if inline_entry else 'entry-probe')
        result = subprocess.run(command,
                                check=True, capture_output=True, text=True)
        return arena_path.read_bytes(), json.loads(result.stdout)


def firmware_sections(data):
    """Inventory of the pinned container after the actual C parser validates it."""
    end, = struct.unpack_from('<I', data, 16)
    sections, offset = [], 20
    while offset < end:
        header, = struct.unpack_from('<I', data, offset)
        size = (header >> 8) & 255
        if size < 4 or offset + size > end:
            raise MappingError('invalid section inventory header')
        if header & 255 == 0:
            flags, start, stop, first, last = struct.unpack_from('<5I', data, offset + 4)
            sections.append(dict(flags=flags, va_start=start, va_end=stop,
                data_start=first, data_end=last,
                cache_mode=('none','cached','uncached-coherent','cached-coherent')[(flags >> 3) & 3],
                shared=bool(flags & (1 << 30)), zero_tail=bool(flags & (1 << 31))))
        offset += size
    return sections


def entry_probe_metadata(original, patched, plan, inline_entry=False):
    root = plan['root_pa']
    ranges = []
    for va, size in ((RESET_ENTRY & ~1, 24 if inline_entry else 8),
                     (ENTRY_PROBE_VA, 64 if inline_entry else 36)):
        offset, _ = translate(original, root, va)
        ranges.append((offset, size))
    expected = bytearray(original)
    for offset, size in ranges:
        expected[offset:offset + size] = patched[offset:offset + size]
    if bytes(expected) != patched or original[:plan['table_pages'] * PAGE] != patched[:plan['table_pages'] * PAGE]:
        raise MappingError('entry probe changed bytes outside its two code overlays')
    marker_offset, _ = translate(patched, root, ENTRY_MARKER_VA)
    version_offset, _ = translate(patched, root, plan['shared_va'])
    if patched[marker_offset:marker_offset+4] != bytes(4) or patched[version_offset:version_offset+4] != bytes(4):
        raise MappingError('entry probe prefilled marker or version')
    return dict(reset_entry_va=hex(RESET_ENTRY & ~1), reset_entry_pa=hex(root + ranges[0][0]),
                trampoline_va=hex(ENTRY_PROBE_VA), trampoline_pa=hex(root + ranges[1][0]),
                resume_va='0x1001904' if inline_entry else '0x10018f4',
                inline_marker=inline_entry, trampoline_marker='0x5452414d' if inline_entry else None,
                marker_va=hex(ENTRY_MARKER_VA),
                marker_pa=hex(root + marker_offset), marker=hex(RESET_STORE_MARKER),
                version_va=hex(plan['shared_va']), version_pa=hex(root + version_offset),
                patches=[dict(arena_offset=off, bytes=size, hex=patched[off:off+size].hex()) for off,size in ranges],
                page_tables_unchanged=True, outside_code_overlays_unchanged=True,
                version_and_marker_initially_zero=True)


def synthetic_mmio_words(fw_word10=0xA8620004, shader_present=0, fw_word30004=0x2000000A):
    if (not isinstance(fw_word10, int) or not 0 <= fw_word10 < 1 << 32 or
            not isinstance(shader_present, int) or not 0 <= shader_present < 1 << 64 or
            not isinstance(fw_word30004, int) or not 0 <= fw_word30004 < 1 << 32):
        raise ValueError('synthetic MMIO values exceed register width')
    # Raw firmware-visible addresses: their equivalence to host GPU register
    # offsets has NOT been measured. Legacy defaults are synthetic assumptions.
    return {0x40000010: fw_word10, 0x40000014: 0x2830,
            0x40030004: fw_word30004, 0x40030108: 0xFF,
            0x40000100: shader_present & 0xFFFFFFFF,
            0x40000104: shader_present >> 32}


def shared_allocation_word(fw_word10, shader_present):
    """Arithmetic at pinned firmware01002f96..01002fd6, not a PC trace."""
    synthetic_mmio_words(fw_word10, shader_present)
    return (((fw_word10 >> 8) & 15) + shader_present.bit_length() + 3) & 0xFFFF


def patch_reset_store_stub(arena, plan):
    """Replace only reset-entry bytes in an offline arena; keep all PTEs.

    The vector at VA0 selects the entry, not the first code-section word.
    The pinned shared control header, rather than its input page, holds
    version. This marker deliberately cannot satisfy CSF firmware readiness.
    """
    root, shared = plan['root_pa'], plan['shared_va']
    if shared != 0x04000000 or len(arena) != plan['required_bytes']:
        raise MappingError('unsupported reset-store arena or shared header')
    check_access(arena, root, 0, 8, 'read')
    vector_offset, _ = translate(arena, root, 0)
    stack, entry = struct.unpack_from('<II', arena, vector_offset)
    if entry != RESET_ENTRY or stack != 0x02040000:
        raise MappingError('reset-store requires the pinned reset vectors')
    check_access(arena, root, stack - 4, 4, 'write')
    check_access(arena, root, shared, 4, 'write')
    shared_offset, _ = translate(arena, root, shared)
    if struct.unpack_from('<I', arena, shared_offset)[0]:
        raise MappingError('reset-store requires a zero initial version')
    code = RESET_STORE_CODE + struct.pack('<II', shared, RESET_STORE_MARKER)
    start = entry & ~1
    check_access(arena, root, start, len(code), 'fetch')
    offset, _ = translate(arena, root, start)
    last, _ = translate(arena, root, start + len(code) - 1)
    if last != offset + len(code) - 1 or offset < plan['table_pages'] * PAGE:
        raise MappingError('reset-store entry overlaps tables or is not contiguous')
    patched = bytearray(arena)
    patched[offset:offset + len(code)] = code
    return bytes(patched), {
        'entry_va': hex(start), 'entry_pa': hex(root + offset),
        'patch_bytes': len(code), 'patch_hex': code.hex(),
        'self_loop_va': hex(start + 10), 'marker': hex(RESET_STORE_MARKER),
        'version_va': hex(shared), 'version_pa': hex(root + shared_offset),
        'original_patch_sha256': hashlib.sha256(arena[offset:offset + len(code)]).hexdigest(),
        'page_tables_unchanged': patched[:plan['table_pages'] * PAGE] == arena[:plan['table_pages'] * PAGE],
        'outside_patch_unchanged': patched[:offset] == arena[:offset] and
                                   patched[offset + len(code):] == arena[offset + len(code):],
        'firmware_ready': False,
        'interpretation': 'A real marker would prove reset-entry execution and a shared write. '
                          'No IRQ or valid CSF interface is provided; a missing marker does not localize the stall.',
    }


def reset_store_pass(result, patch):
    return (result['reason'] == 'diagnostic-self-loop' and not result['violations'] and
            result['version'] == patch['marker'] and result['shared_write_count'] == 1 and
            len(result['shared_writes']) == 1 and
            result['shared_writes'][0]['address'] == patch['version_va'] and
            result['shared_writes'][0]['size'] == 4 and
            result['shared_writes'][0]['value'] == patch['marker'] and
            not result['mmio_writes'] and not result['startup_probe_writes'] and
            patch['page_tables_unchanged'] and patch['outside_patch_unchanged'])


def replay(arena, plan, step_limit=500000, tiler_transition_reads=0,
           fw_word10=0xA8620004, shader_present=0, fw_word30004=0x2000000A,
           self_loop_pc=None, entry_checkpoint=False, resume_pc=0x010018F4,
           stop_before_pc=None):
    words = synthetic_mmio_words(fw_word10, shader_present, fw_word30004)
    uc = importlib.import_module('unicorn')
    arm = importlib.import_module('unicorn.arm_const')
    u = uc.Uc(uc.UC_ARCH_ARM, uc.UC_MODE_THUMB | uc.UC_MODE_MCLASS)
    u.ctl_set_cpu_model(arm.UC_CPU_ARM_CORTEX_M7)
    root = plan['root_pa']
    for section in plan['sections']:
        for va in range(section['va'], section['va'] + section['bytes'], PAGE):
            off, _ = translate(arena, root, va)
            if off != section['arena_offset'] + va - section['va']:
                raise MappingError('page table differs from allocation plan')
            # All emulated bytes come through the actual loader's tables.
            u.mem_map(va, PAGE)
            u.mem_write(va, bytes(arena[off:off + PAGE]))
    u.mem_map(0x40000000, 0x40000)
    u.mem_map(0xE0000000, 0x100000)
    for address, value in words.items():
        u.mem_write(address, struct.pack('<I', value))
    if tiler_transition_reads:
        u.mem_write(0x40000110, struct.pack('<I', 1))
        u.mem_write(0x40000210, struct.pack('<I', 1))
    state = {'reason': 'instruction-limit', 'steps': 0, 'violations': [],
             'tiler_transition_read_count': 0, 'shared_write_count': 0}
    accessed = {key: Counter() for key in ('read', 'write', 'fetch')}
    last = deque(maxlen=16)
    mmio_reads, mmio_writes = Counter(), []
    shared_writes = []
    probes = {'private_early': 0x0202C934, 'private_feature': 0x0202C93C,
              'private_late': 0x0202C22C, 'shared_alloc': plan['shared_va'] + 0x18}
    if entry_checkpoint:
        probes['entry_checkpoint'] = ENTRY_MARKER_VA
    probe_before = {name: struct.unpack('<I', u.mem_read(address, 4))[0]
                    for name, address in probes.items()}
    probe_writes = []
    self_loop_hits = 0

    def violation(operation, address, size, message):
        state['reason'] = 'access-violation'
        state['violations'].append({'operation': operation, 'address': hex(address),
                                    'size': size, 'pc': hex(u.reg_read(arm.UC_ARM_REG_PC)),
                                    'message': message})
        u.emu_stop()

    def access(operation, address, size):
        try:
            check_access(arena, root, address, size, operation,
                         bool(u.reg_read(arm.UC_ARM_REG_CONTROL) & 1))
        except MappingError as error:
            violation(operation, address, size, str(error))
            return False
        for page in range(address & -PAGE, ((address + size - 1) & -PAGE) + PAGE, PAGE):
            accessed[operation][page] += 1
        return True

    def code_hook(_u, address, size, _context):
        nonlocal self_loop_hits
        state['steps'] += 1
        last.append(address)
        if not access('fetch', address, size):
            return
        if stop_before_pc is not None and address == stop_before_pc:
            state['reason'] = 'diagnostic-checkpoint'
            u.emu_stop()
        if entry_checkpoint and address == resume_pc:
            state['entry_resume_registers'] = {
                name: hex(u.reg_read(getattr(arm, 'UC_ARM_REG_' + name)))
                for name in ('R0', 'R1', 'MSP', 'PSP', 'PRIMASK', 'CONTROL', 'XPSR')}
        if address == 0x01003032:
            state['reason'] = 'startup-wfi'
            u.emu_stop()
        if address == self_loop_pc:
            self_loop_hits += 1
            if self_loop_hits == 2:
                state['reason'] = 'diagnostic-self-loop'
                u.emu_stop()

    def memory_hook(_u, operation, address, size, value, _context):
        pc = u.reg_read(arm.UC_ARM_REG_PC)
        is_read = operation == uc.UC_MEM_READ
        if (0x40000000 <= address and address + size <= 0x40040000) or (
                0xE0000000 <= address and address + size <= 0xE0100000):
            if is_read:
                mmio_reads[(address, pc)] += 1
                if address == 0x40000210 and tiler_transition_reads:
                    state['tiler_transition_read_count'] += 1
                    if tiler_transition_reads > 0 and state['tiler_transition_read_count'] >= tiler_transition_reads:
                        u.mem_write(address, struct.pack('<I', 0))
            elif len(mmio_writes) < 256:
                mmio_writes.append({'pc': hex(pc), 'address': hex(address), 'value': hex(value), 'size': size})
            return
        if access('read' if is_read else 'write', address, size) and not is_read:
            for name, target in probes.items():
                if address < target + 4 and target < address + size and len(probe_writes) < 64:
                    probe_writes.append({'name': name, 'pc': hex(pc), 'address': hex(address),
                                         'size': size, 'value': hex(value)})
            if plan['shared_va'] <= address < plan['shared_va'] + plan['shared_bytes']:
                state['shared_write_count'] += 1
                if len(shared_writes) < 256:
                    shared_writes.append({'pc': hex(pc), 'address': hex(address), 'size': size, 'value': hex(value)})

    def invalid_hook(_u, operation, address, size, value, _context):
        violation('unmapped-%d' % operation, address, size, 'Unicorn unmapped/protected access')
        return False

    def interrupt_hook(_u, number, _context):
        state['reason'] = 'cpu-exception-%d' % number
        u.emu_stop()

    # Read reset vectors via the generated page table, not blob offsets.
    check_access(arena, root, 0, 8, 'read')
    vector_offset, _ = translate(arena, root, 0)
    stack, entry = struct.unpack_from('<II', arena, vector_offset)
    check_access(arena, root, entry & ~1, 2, 'fetch')
    check_access(arena, root, stack - 4, 4, 'write')
    u.reg_write(arm.UC_ARM_REG_MSP, stack)
    u.reg_write(arm.UC_ARM_REG_SP, stack)
    u.reg_write(arm.UC_ARM_REG_XPSR, 0x01000000)
    u.hook_add(uc.UC_HOOK_CODE, code_hook)
    u.hook_add(uc.UC_HOOK_MEM_READ | uc.UC_HOOK_MEM_WRITE, memory_hook)
    u.hook_add(uc.UC_HOOK_MEM_INVALID, invalid_hook)
    u.hook_add(uc.UC_HOOK_INTR, interrupt_hook)
    try:
        u.emu_start(entry, 0, count=step_limit)
    except uc.UcError as error:
        state['emulator_error'] = str(error)
    state.update({'initial_stack': hex(stack), 'reset_entry': hex(entry),
                  'version': hex(struct.unpack('<I', u.mem_read(plan['shared_va'], 4))[0]),
                  'fetched_pages': [hex(x) for x in sorted(accessed['fetch'])],
                  'accessed_page_counts': {k: len(v) for k, v in accessed.items()},
                  'mmio_reads': [{'address': hex(a), 'pc': hex(pc), 'count': n}
                                 for (a, pc), n in mmio_reads.most_common(40)],
                  'mmio_writes': mmio_writes, 'shared_writes': shared_writes,
                  'startup_probes': {name: {'va': hex(address), 'before': hex(probe_before[name]),
                      'after': hex(struct.unpack('<I', u.mem_read(address, 4))[0])}
                      for name, address in probes.items()},
                  'startup_probe_writes': probe_writes,
                  'synthetic_mmio_words': {hex(a): hex(v) for a, v in words.items()},
                  'shared_allocation_prediction': hex(shared_allocation_word(fw_word10, shader_present)),
                  'synthetic_mmio_note': 'Raw firmware-visible inputs; host-register aliases and '
                      'actual startup values have not been measured. An endpoint match cannot identify the writer or PC.',
                  'last_pcs': [hex(x) for x in last], 'unicorn_version': uc.__version__})
    return state


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--firmware', required=True, type=Path)
    parser.add_argument('--python-deps', type=Path, help='directory containing local Unicorn installation')
    parser.add_argument('--arena-pa', type=lambda value: int(value, 0), default=0x40076000)
    parser.add_argument('--memory-group', type=int, choices=range(16), default=0,
                        help='leaf bits59..62; hardware routing is not modeled')
    parser.add_argument('--reset-store-stub', action='store_true',
                        help='offline only: patch Thumb reset entry to store STUB at the version header and loop')
    parser.add_argument('--entry-probe', action='store_true',
                        help='mark a distinct shared word, restore original reset prefix and continue real firmware')
    parser.add_argument('--inline-entry', action='store_true',
                        help='inline STUB before remote fetch, tail advances to TRAM, then resume original firmware')
    parser.add_argument('--step-limit', type=int, default=500000)
    parser.add_argument('--tiler-transition-reads', type=int, default=0,
                        help='synthetic transition: 0 absent, -1 stuck, N clears after N reads')
    parser.add_argument('--fw-word10', type=lambda value: int(value, 0), default=0xA8620004,
                        help='synthetic raw firmware MMIO40000010; legacy default is not a measured alias')
    parser.add_argument('--shader-present', type=lambda value: int(value, 0), default=0,
                        help='synthetic64-bit firmware MMIO40000100/104; defaults to zero')
    parser.add_argument('--fw-word30004', type=lambda value: int(value, 0), default=0x2000000A,
                        help='synthetic raw firmware MMIO40030004; not measured on the MCU')
    args = parser.parse_args()
    if sum((args.entry_probe, args.inline_entry, args.reset_store_stub)) > 1:
        parser.error('select only one firmware diagnostic')
    if args.step_limit < 1 or args.step_limit > 1000000 or args.tiler_transition_reads < -1:
        parser.error('invalid bounded replay parameters')
    try:
        synthetic_mmio_words(args.fw_word10, args.shader_present, args.fw_word30004)
    except ValueError as error:
        parser.error(str(error))
    if args.python_deps:
        sys.path.insert(0, str(args.python_deps.resolve()))
    firmware_hash = hashlib.sha256(args.firmware.read_bytes()).hexdigest()
    if firmware_hash != FIRMWARE_SHA256:
        parser.error('unsupported firmware hash; startup PC and MMIO model require the pinned matisse blob')
    arena, plan = build_arena(args.firmware.resolve(), args.arena_pa, memory_group=args.memory_group)
    patch = None
    original_arena_hash = hashlib.sha256(arena).hexdigest()
    if args.reset_store_stub:
        arena, patch = patch_reset_store_stub(arena, plan)
    entry_patch = None
    if args.entry_probe or args.inline_entry:
        original = arena
        arena, probe_plan = build_arena(args.firmware.resolve(), args.arena_pa,
                                       memory_group=args.memory_group, entry_probe=True, inline_entry=args.inline_entry)
        if probe_plan != plan:
            parser.error('entry probe changed the canonical mapping plan')
        entry_patch = entry_probe_metadata(original, arena, plan, inline_entry=args.inline_entry)
    result = {'scope': 'Offline synthetic startup; not hardware execution or timeout root-cause proof.',
              'firmware_sha256': firmware_hash,
              'synthetic_parameters': {'step_limit': args.step_limit, 'memory_group': args.memory_group,
                                       'fw_word10': hex(args.fw_word10),
                                       'shader_present': hex(args.shader_present),
                                       'fw_word30004': hex(args.fw_word30004),
                                       'tiler_transition_reads': args.tiler_transition_reads},
              'arena_sha256': hashlib.sha256(arena).hexdigest(),
              'source_sha256': {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
                                for name in ('xnu/gpu/mali_csf_memory.c', 'xnu/gpu/mali_csf_firmware.c')},
              'plan': plan, 'replay': replay(arena, plan, args.step_limit, args.tiler_transition_reads,
                                           args.fw_word10, args.shader_present, args.fw_word30004,
                                           int(patch['self_loop_va'], 0) if patch else None,
                                           entry_checkpoint=args.entry_probe or args.inline_entry,
                                           resume_pc=0x01001904 if args.inline_entry else 0x010018f4)}
    if entry_patch:
        result['entry_probe'] = entry_patch
        result['sections'] = firmware_sections(args.firmware.read_bytes())
        result['original_arena_sha256'] = original_arena_hash
    if patch:
        result['scope'] = 'Offline synthetic reset-store diagnostic; not hardware execution or firmware readiness.'
        for name in ('tools/matisse-csf-reset-store.S', 'tools/matisse-csf-fetch-audit.py'):
            result['source_sha256'][name] = hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
        result['original_arena_sha256'] = original_arena_hash
        result['reset_store_stub'] = patch
        result['diagnostic_pass'] = reset_store_pass(result['replay'], patch)
        result['firmware_ready'] = False
    print(json.dumps(result, indent=2))
    if patch:
        return 0 if result['diagnostic_pass'] else 1
    return 0 if result['replay']['reason'] == 'startup-wfi' and not result['replay']['violations'] else 1


if __name__ == '__main__':
    sys.exit(main())
