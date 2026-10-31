#!/usr/bin/env python3
"""Compare the real CSF arena with bounded pinned vendor MMU helpers.

Offline only: modules are never loaded as host code. Unicorn executes small
relocation-free AArch64 ranges against synthetic memory. This does not model
Mali translation, memory routing, caches, or physical MCU execution. Keep
proprietary input and detailed generated reports in ignored research/.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import struct
import sys

ROOT = Path(__file__).resolve().parents[1]
KMD_SHA256 = '22b26f30a151e9d6791f959cc1f93d1e3f4d4c564537970dadefb0ec2d742a3b'
MGM_SHA256 = '22113cb61a7b1fab5e552ff028a7e45c8ef40cfe57b2bdd67ea835b017d0f2f9'
VENDOR_MEMATTR = 0x00084C8D888D8F88
PROBE_MEMATTR = 0x4C4C4C4C4C4C9F4C
PA_MASK = 0x0000FFFFFFFFF000
HELPERS = {
    'convert_section_flags': (0x6FBEC, 0x6FC9C),
    'entry_set_ate': (0x471A0, 0x47250),
    'entry_set_pte': (0x47250, 0x472C8),
    'get_as_setup': (0x47994, 0x479C8),
    'mgm_update_gpu_pte': (0x97C, 0x9DC),
}


def elf_section(data, wanted):
    """Read an ELF64 LE section with bounds checks, without extra packages."""
    if len(data) < 64 or data[:7] != b'\x7fELF\x02\x01\x01':
        raise ValueError('expected ELF64 little-endian input')
    offset, = struct.unpack_from('<Q', data, 40)
    stride, count, names_index = struct.unpack_from('<HHH', data, 58)
    if stride != 64 or not count or names_index >= count or offset + stride * count > len(data):
        raise ValueError('invalid ELF section table')
    sections = [struct.unpack_from('<IIQQQQIIQQ', data, offset + stride * i) for i in range(count)]
    names = sections[names_index]
    if names[4] + names[5] > len(data):
        raise ValueError('invalid section-name bounds')
    strings = data[names[4]:names[4] + names[5]]
    for section in sections:
        if section[0] >= len(strings):
            raise ValueError('invalid section name')
        end = strings.find(b'\0', section[0])
        if end < 0:
            raise ValueError('unterminated section name')
        if strings[section[0]:end].decode('ascii') == wanted:
            if section[1] == 8 or section[4] + section[5] > len(data):
                raise ValueError('section is absent or outside file')
            return data[section[4]:section[4] + section[5]]
    raise ValueError('missing ELF section ' + wanted)


def pinned_elf(path, expected, helper_names):
    data = path.read_bytes()
    if hashlib.sha256(data).hexdigest() != expected:
        raise ValueError('unsupported module hash: ' + str(path))
    relocation_section = ('.rela.text.mtk_common_get_kbdev' if expected == KMD_SHA256
                          else '.rela.text.memory_group_manager_probe')
    code, relocations = elf_section(data, '.text'), elf_section(data, relocation_section)
    if len(relocations) % 24:
        raise ValueError('invalid RELA section')
    offsets = [struct.unpack_from('<Q', relocations, pos)[0] for pos in range(0, len(relocations), 24)]
    for name in helper_names:
        start, end = HELPERS[name]
        if end > len(code) or any(start <= off < end for off in offsets):
            raise ValueError('helper is truncated or requires relocation: ' + name)
    return code


def effective_leaf(descriptor, memattr):
    index = (descriptor >> 2) & 7
    return dict(pa=hex(descriptor & PA_MASK), attr_index=index,
                attr_value=hex((memattr >> (index * 8)) & 255),
                shareability=(descriptor >> 8) & 3,
                unprivileged=bool(descriptor & 0x40), readonly=bool(descriptor & 0x80),
                access_flag=bool(descriptor & 0x400), nonglobal=bool(descriptor & 0x800),
                pxn=bool(descriptor & (1 << 53)), uxn=bool(descriptor & (1 << 54)),
                high_bits_59_62=(descriptor >> 59) & 15,
                bit63=bool(descriptor & (1 << 63)))


def differences(left, right):
    return {key: {'probe': left[key], 'vendor': right[key]} for key in left if left[key] != right[key]}


class VendorHelpers:
    CODE, DATA, DATA_BYTES = 0x1000000, 0x2000000, 0x10000

    def __init__(self, kmd, mgm):
        import unicorn
        from unicorn import arm64_const
        self.uc, self.arm = unicorn, arm64_const
        self.kmd_code, self.mgm_code = kmd, mgm
        self.calls = []

    def call(self, name, registers=None, stores=(), reads=()):
        uc, arm = self.uc, self.arm
        code = self.mgm_code if name == 'mgm_update_gpu_pte' else self.kmd_code
        begin, end = HELPERS[name]
        u = uc.Uc(uc.UC_ARCH_ARM64, uc.UC_MODE_ARM)
        u.mem_map(self.CODE, (len(code) + 4095) & ~4095, uc.UC_PROT_READ | uc.UC_PROT_EXEC)
        u.mem_write(self.CODE, code)
        u.mem_map(self.DATA, self.DATA_BYTES, uc.UC_PROT_READ | uc.UC_PROT_WRITE)
        u.reg_write(arm.UC_ARM64_REG_SP, self.DATA + 0xE000)
        u.reg_write(arm.UC_ARM64_REG_X29, self.DATA + 0xF000)
        u.reg_write(arm.UC_ARM64_REG_LR, self.CODE + end)
        for index, value in (registers or {}).items():
            u.reg_write(getattr(arm, 'UC_ARM64_REG_X%d' % index), value)
        for address, data in stores:
            if address < self.DATA or address + len(data) > self.DATA + self.DATA_BYTES:
                raise ValueError('synthetic store outside data slab')
            u.mem_write(address, data)
        count = [0]

        def check_pc(_u, address, _size, _context):
            count[0] += 1
            if not self.CODE + begin <= address < self.CODE + end:
                raise ValueError('helper escaped pinned range')

        u.hook_add(uc.UC_HOOK_CODE, check_pc)
        try:
            u.emu_start(self.CODE + begin, self.CODE + end, count=256)
        except uc.UcError as error:
            pc = u.reg_read(arm.UC_ARM64_REG_PC) - self.CODE
            raise ValueError('%s at text+%#x: %s' % (name, pc, error)) from error
        if u.reg_read(arm.UC_ARM64_REG_PC) != self.CODE + end:
            raise ValueError('bounded helper did not complete: ' + name)
        self.calls.append(dict(helper=name, instructions=count[0]))
        result = {index: u.reg_read(getattr(arm, 'UC_ARM64_REG_X%d' % index)) for index in range(29)}
        return result, [bytes(u.mem_read(address, size)) for address, size in reads]

    def flags(self, flags, coherency=31):
        registers = {19: self.DATA, 12: self.DATA + 0x4000,
                     26: flags, 28: self.DATA + 0x5000}
        result, _ = self.call('convert_section_flags', registers,
                             [(self.DATA + 0x2DFC, struct.pack('<I', coherency))])
        return result[28]

    def ate(self, pa, flags):
        _, output = self.call('entry_set_ate', {0: self.DATA, 1: pa, 2: flags, 3: 3},
                              reads=[(self.DATA, 8)])
        return struct.unpack('<Q', output[0])[0]

    def mgm(self, descriptor, requested_group=0, override=0):
        result, _ = self.call('mgm_update_gpu_pte',
                             {0: self.DATA, 1: requested_group, 2: 3, 3: descriptor},
                             [(self.DATA + 0x28, struct.pack('<Q', self.DATA + 0x1000)),
                              (self.DATA + 0x1210, struct.pack('<i', override))])
        return result[0]

    def table(self, pa, index=10):
        _, output = self.call('entry_set_pte', {0: self.DATA, 1: index, 2: pa},
                              reads=[(self.DATA + index * 8, 8), (self.DATA, 24)])
        return struct.unpack('<Q', output[0])[0], [hex(x) for x in struct.unpack('<3Q', output[1])]

    def setup(self, root):
        _, output = self.call('get_as_setup', {0: self.DATA, 1: self.DATA + 0x1000},
                              [(self.DATA + 0x38, struct.pack('<Q', root))],
                              [(self.DATA + 0x1000, 24)])
        return struct.unpack('<3Q', output[0])


def fetch_module():
    spec = importlib.util.spec_from_file_location('csf_fetch', ROOT / 'tools/matisse-csf-fetch-audit.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def compare(kmd, mgm, firmware, arena_pa):
    fetch = fetch_module()
    firmware_hash = hashlib.sha256(firmware.read_bytes()).hexdigest()
    if firmware_hash != fetch.FIRMWARE_SHA256:
        raise ValueError('unsupported firmware hash')
    helpers = VendorHelpers(kmd, mgm)
    arena, plan = fetch.build_arena(firmware, arena_pa)
    root, memattr, base_transcfg = helpers.setup(plan['root_pa'])
    if root != plan['root_pa'] or memattr != VENDOR_MEMATTR or base_transcfg != 6:
        raise ValueError('unexpected pinned vendor AS setup')
    sections = []
    for section in plan['sections']:
        flags = helpers.flags(section['flags'])
        descriptors = [fetch.translate(arena, plan['root_pa'], va)[1]
                       for va in range(section['va'], section['va'] + section['bytes'], 4096)]
        pa = descriptors[0] & PA_MASK
        bare = helpers.ate(pa, flags)
        tagged = helpers.mgm(bare)
        probe = effective_leaf(descriptors[0], PROBE_MEMATTR)
        vendor = effective_leaf(tagged, memattr)
        for index, descriptor in enumerate(descriptors):
            effective = effective_leaf(descriptor, PROBE_MEMATTR)
            effective['pa'] = probe['pa']
            if effective != probe or descriptor & PA_MASK != pa + index * 4096:
                raise ValueError('nonuniform section attributes or unexpected PA stride')
        sections.append(dict(va=hex(section['va']), bytes=section['bytes'],
                             section_flags=hex(section['flags']), vendor_mem_flags=hex(flags),
                             probe_descriptor=hex(descriptors[0]), vendor_base_descriptor=hex(bare),
                             vendor_mgm_descriptor=hex(tagged), probe=probe, vendor=vendor,
                             differences=differences(probe, vendor), checked_pages=len(descriptors)))
    mgm_cases = [dict(requested_group=group, override=override,
                      result=hex(helpers.mgm(0x40000443, group, override)))
                 for group, override in ((0, 0), (6, 0), (15, 0), (0, 3))]
    table_descriptor, counter_words = helpers.table(arena_pa + 4096)
    return dict(scope='Offline synthetic helper execution; not a device trace or timeout root-cause proof.',
                kmd_sha256=KMD_SHA256, mgm_sha256=MGM_SHA256, firmware_sha256=firmware_hash,
                source_sha256={name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
                               for name in ('tools/matisse-csf-vendor-mmu-audit.py',
                                            'xnu/gpu/mali_csf_memory.c', 'xnu/gpu/mali_csf_firmware.c')},
                arena_sha256=hashlib.sha256(arena).hexdigest(),
                checked_pages=sum(s['checked_pages'] for s in sections),
                setup=dict(root_pa=hex(root), vendor_memattr=hex(memattr),
                           vendor_base_transcfg=hex(base_transcfg),
                           vendor_coherency31_transcfg=hex(base_transcfg | 0x42000000),
                           probe_memattr=hex(PROBE_MEMATTR), probe_transcfg='0x420001c6'),
                table=dict(vendor_descriptor=hex(table_descriptor),
                           probe_descriptor=hex((arena_pa + 4096) | 3),
                           synthetic_counter_words=counter_words),
                mgm_cases=mgm_cases, sections=sections, helper_calls=helpers.calls,
                limitations=['MGM uses a zero-initialized synthetic override; Android runtime override was not measured.',
                             'TRANSCFG WB/RA addition is statically derived, not emulated here.',
                             'No Mali translation, high-bit routing, cache hierarchy, or physical MCU execution is modeled.'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--kmd', required=True, type=Path)
    parser.add_argument('--mgm', required=True, type=Path)
    parser.add_argument('--firmware', required=True, type=Path)
    parser.add_argument('--python-deps', type=Path)
    parser.add_argument('--arena-pa', type=lambda value: int(value, 0), default=0x40076000)
    args = parser.parse_args()
    if args.python_deps:
        sys.path.insert(0, str(args.python_deps.resolve()))
    kmd = pinned_elf(args.kmd, KMD_SHA256, tuple(name for name in HELPERS if not name.startswith('mgm_')))
    mgm = pinned_elf(args.mgm, MGM_SHA256, ('mgm_update_gpu_pte',))
    print(json.dumps(compare(kmd, mgm, args.firmware.resolve(), args.arena_pa), indent=2))
    return 0


if __name__ == '__main__':
    sys.exit(main())
