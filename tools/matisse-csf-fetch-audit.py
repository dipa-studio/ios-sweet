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
HOST_BUILDER = r'''
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include "mali_csf_memory.h"
int main(int argc, char **argv) {
    if (argc != 4) return 2;
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
    if (!arena || sweet_csf_memory_build(fw, (size_t)n, &m, arena,
        m.required_bytes, pa, 40, &root)) return 7;
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


def build_arena(firmware, arena_pa, compiler='cc'):
    with tempfile.TemporaryDirectory(prefix='csf-fetch-') as tmp:
        tmp = Path(tmp)
        source, binary, arena_path = tmp / 'loader.c', tmp / 'loader', tmp / 'arena.bin'
        source.write_text(HOST_BUILDER)
        subprocess.run([compiler, '-std=c11', '-Wall', '-Wextra', '-Werror',
                        '-fsanitize=address,undefined', '-I', str(ROOT / 'xnu/gpu'),
                        str(source), str(ROOT / 'xnu/gpu/mali_csf_firmware.c'),
                        str(ROOT / 'xnu/gpu/mali_csf_memory.c'), '-o', str(binary)],
                       check=True, capture_output=True, text=True)
        result = subprocess.run([str(binary), str(firmware), str(arena_path), hex(arena_pa)],
                                check=True, capture_output=True, text=True)
        return arena_path.read_bytes(), json.loads(result.stdout)


def replay(arena, plan, step_limit=500000, tiler_transition_reads=0):
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
    for address, value in ((0x40000010, 0xA8620004), (0x40000014, 0x2830),
                           (0x40030004, 0x2000000A), (0x40030108, 0xFF)):
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
    probe_before = {name: struct.unpack('<I', u.mem_read(address, 4))[0]
                    for name, address in probes.items()}
    probe_writes = []

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
        state['steps'] += 1
        last.append(address)
        if not access('fetch', address, size):
            return
        if address == 0x01003032:
            state['reason'] = 'startup-wfi'
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
                  'last_pcs': [hex(x) for x in last], 'unicorn_version': uc.__version__})
    return state


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--firmware', required=True, type=Path)
    parser.add_argument('--python-deps', type=Path, help='directory containing local Unicorn installation')
    parser.add_argument('--arena-pa', type=lambda value: int(value, 0), default=0x40076000)
    parser.add_argument('--step-limit', type=int, default=500000)
    parser.add_argument('--tiler-transition-reads', type=int, default=0,
                        help='synthetic transition: 0 absent, -1 stuck, N clears after N reads')
    args = parser.parse_args()
    if args.step_limit < 1 or args.step_limit > 1000000 or args.tiler_transition_reads < -1:
        parser.error('invalid bounded replay parameters')
    if args.python_deps:
        sys.path.insert(0, str(args.python_deps.resolve()))
    firmware_hash = hashlib.sha256(args.firmware.read_bytes()).hexdigest()
    if firmware_hash != FIRMWARE_SHA256:
        parser.error('unsupported firmware hash; startup PC and MMIO model require the pinned matisse blob')
    arena, plan = build_arena(args.firmware.resolve(), args.arena_pa)
    result = {'scope': 'Offline synthetic startup; not hardware execution or timeout root-cause proof.',
              'firmware_sha256': firmware_hash,
              'synthetic_parameters': {'step_limit': args.step_limit,
                                       'tiler_transition_reads': args.tiler_transition_reads},
              'arena_sha256': hashlib.sha256(arena).hexdigest(),
              'source_sha256': {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
                                for name in ('xnu/gpu/mali_csf_memory.c', 'xnu/gpu/mali_csf_firmware.c')},
              'plan': plan, 'replay': replay(arena, plan, args.step_limit, args.tiler_transition_reads)}
    print(json.dumps(result, indent=2))
    return 0 if result['replay']['reason'] == 'startup-wfi' and not result['replay']['violations'] else 1


if __name__ == '__main__':
    sys.exit(main())
