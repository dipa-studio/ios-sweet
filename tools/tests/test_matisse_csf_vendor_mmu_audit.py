"""Offline audit validation without proprietary modules or emulator dependency."""
import hashlib
import copy
import importlib.util
from pathlib import Path
import struct
import shutil
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location('vendor_mmu_audit', ROOT / 'tools/matisse-csf-vendor-mmu-audit.py')
audit = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(audit)


def elf_fixture(relocations=b'', text_bytes=0xA00):
    names = b'\0.shstrtab\0.text\0.rela.text.memory_group_manager_probe\0'
    sections = [(0, 0, b''), (1, 3, names), (11, 1, bytes(text_bytes)), (17, 4, relocations)]
    data = bytearray(64 + 64 * len(sections))
    data[:7] = b'\x7fELF\x02\x01\x01'
    struct.pack_into('<Q', data, 40, 64)
    struct.pack_into('<HHH', data, 58, 64, len(sections), 1)
    for index, (name, kind, content) in enumerate(sections):
        struct.pack_into('<IIQQQQIIQQ', data, 64 + index * 64,
                         name, kind, 0, 0, len(data), len(content), 0, 2 if kind == 4 else 0, 1, 24 if kind == 4 else 0)
        data.extend(content)
    return data


class ElfBoundsTests(unittest.TestCase):
    def test_extract_and_missing_section(self):
        fixture = elf_fixture()
        self.assertEqual(audit.elf_section(fixture, '.text'), bytes(0xA00))
        with self.assertRaisesRegex(ValueError, 'missing'):
            audit.elf_section(fixture, '.absent')

    def test_truncated_and_invalid_section_table(self):
        fixture = elf_fixture()
        for data in (b'', fixture[:63], fixture[:128]):
            with self.subTest(size=len(data)), self.assertRaises(ValueError):
                audit.elf_section(data, '.text')
        struct.pack_into('<H', fixture, 58, 32)
        with self.assertRaisesRegex(ValueError, 'table'):
            audit.elf_section(fixture, '.text')

    def test_section_name_and_data_bounds(self):
        for field, value in ((0, 0xFFFFFFFF), (24, 0xFFFFFFFFFFFFFFF0), (32, 0xFFFFFFFFFFFFFFF0)):
            fixture = elf_fixture()
            fmt = '<I' if field == 0 else '<Q'
            struct.pack_into(fmt, fixture, 64 + 2 * 64 + field, value)
            with self.subTest(field=field), self.assertRaises(ValueError):
                audit.elf_section(fixture, '.text')
        fixture = elf_fixture()
        struct.pack_into('<I', fixture, 64 + 2 * 64 + 4, 8)
        with self.assertRaisesRegex(ValueError, 'absent'):
            audit.elf_section(fixture, '.text')

    def test_module_hash_and_helper_relocation_fail_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'synthetic.elf'
            data = elf_fixture()
            path.write_bytes(data)
            expected = hashlib.sha256(data).hexdigest()
            self.assertEqual(len(audit.pinned_elf(path, expected, ('mgm_update_gpu_pte',))), 0xA00)
            with self.assertRaisesRegex(ValueError, 'hash'):
                audit.pinned_elf(path, '0' * 64, ('mgm_update_gpu_pte',))
            data = elf_fixture(struct.pack('<QQq', 0x990, 0, 0))
            path.write_bytes(data)
            with self.assertRaisesRegex(ValueError, 'relocation'):
                audit.pinned_elf(path, hashlib.sha256(data).hexdigest(), ('mgm_update_gpu_pte',))
            data = elf_fixture(b'bad')
            path.write_bytes(data)
            with self.assertRaisesRegex(ValueError, 'RELA'):
                audit.pinned_elf(path, hashlib.sha256(data).hexdigest(), ('mgm_update_gpu_pte',))

    def test_group_bits_are_separate_from_pa_and_effective_permissions(self):
        baseline = 0x6000004007EFC7
        plain = audit.effective_leaf(baseline, audit.PROBE_MEMATTR)
        tagged = audit.effective_leaf(baseline | (6 << 59), audit.PROBE_MEMATTR)
        self.assertEqual(audit.differences(plain, tagged),
                         {'high_bits_59_62': {'probe': 0, 'vendor': 6}})
        self.assertEqual(tagged['pa'], hex(baseline & audit.PA_MASK))

    def test_register_slices_reject_relocations_at_both_boundaries(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'synthetic.elf'
            for name in ('as_config_registers', 'as_update_command',
                         'mcu_initial_start', 'mcu_reload_start'):
                begin, end = audit.HELPERS[name]
                for offset in (begin, end - 4):
                    data = elf_fixture(struct.pack('<QQq', offset, 0, 0), 0x71000)
                    path.write_bytes(data)
                    with self.subTest(name=name, offset=offset), self.assertRaisesRegex(ValueError, 'relocation'):
                        audit.pinned_elf(path, hashlib.sha256(data).hexdigest(), (name,))
                data = elf_fixture(struct.pack('<QQq', end, 0, 0), 0x71000)
                path.write_bytes(data)
                audit.pinned_elf(path, hashlib.sha256(data).hexdigest(), (name,))

    def test_bad_synthetic_as_inputs_fail_before_emulation(self):
        helpers = object.__new__(audit.VendorHelpers)
        for slot in (-1, 16):
            with self.subTest(slot=slot), self.assertRaisesRegex(ValueError, 'AS'):
                helpers.configure(0x40076000, as_nr=slot)
            with self.subTest(slot=slot), self.assertRaisesRegex(ValueError, 'AS'):
                helpers.update(slot)
        for mode in (-1, 32):
            with self.subTest(mode=mode), self.assertRaisesRegex(ValueError, 'coherency'):
                helpers.configure(0x40076000, coherency=mode)


class PairingControlTests(unittest.TestCase):
    def cases(self):
        cases = []
        for protocol in (31, 0, 1):
            for mode in range(4):
                index, byte, sh = ((6, '0x8', 2) if protocol != 31 and mode >= 2 else
                                   (0, '0x88', 0) if mode == 1 else (5, '0x4c', 0))
                cases.append(dict(protocol=protocol, cache_mode=mode,
                                  attr_index=index, byte=byte, sh=sh))
        return cases

    def test_require_complete_controls_and_raw_pairing(self):
        audit.validate_pairing_controls(self.cases())
        for field, wrong in (('sh', 3), ('byte', '0x9f'), ('attr_index', 1)):
            cases = self.cases();cases[1][field] = wrong
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, 'pairing'):
                audit.validate_pairing_controls(cases)
        with self.assertRaisesRegex(ValueError, 'incomplete'):
            audit.validate_pairing_controls(self.cases()[:-1])

    def test_bad_flag_inputs_reject_before_emulator(self):
        helpers = object.__new__(audit.VendorHelpers)
        for flags, mode in ((-1, 31), (1 << 32, 31), (0xb, 2)):
            with self.subTest(flags=flags, mode=mode), self.assertRaises(ValueError):
                helpers.flags(flags, mode)


class MemattrIndexTests(unittest.TestCase):
    def fixture(self):
        # Four actual-format table levels plus separate cached/shared pages.
        arena = bytearray(6 * 4096)
        root = 0x40076000
        for page in range(3):
            struct.pack_into('<Q', arena, page * 4096, root + (page + 1) * 4096 | 3)
        struct.pack_into('<2Q', arena, 3 * 4096, root + 4 * 4096 | 0xfc7,
                         root + 5 * 4096 | 0xe43)
        sections = [dict(va=0, bytes=4096, flags=0xd, arena_offset=4 * 4096),
                    dict(va=4096, bytes=4096, flags=0x1b, arena_offset=5 * 4096)]
        return arena, dict(root_pa=root, sections=sections)

    def test_vendor_literal_changes_wrong_indices_and_candidate_preserves_shared(self):
        arena, plan = self.fixture()
        report = audit.memattr_index_audit(arena, plan)
        self.assertEqual(report['memattr_words']['cached_byte_only'], '0x4c4c4c4c4c4c884c')
        self.assertEqual(report['register_xor'], '0x1700')
        self.assertEqual(report['byte_matched_pages'],
                         dict(current=1, vendor_literal_only=0, cached_byte_only=2))
        self.assertEqual((report['cached_pages'], report['shared_pages']), (1, 1))
        cached, shared = report['sections']
        self.assertEqual(cached['selected_bytes'],
                         dict(current='0x9f', vendor_literal_only='0x8f', cached_byte_only='0x88'))
        self.assertEqual(shared['selected_bytes'],
                         dict(current='0x4c', vendor_literal_only='0x88', cached_byte_only='0x4c'))

    def test_reject_wrong_leaf_index_allocation_and_page_span(self):
        for mutation in ('index', 'allocation', 'span'):
            arena, plan = self.fixture()
            if mutation == 'index':
                struct.pack_into('<Q', arena, 3 * 4096, plan['root_pa'] + 4 * 4096 | 0xfc3)
            elif mutation == 'allocation':
                plan['sections'][0]['arena_offset'] += 4096
            else:
                plan['sections'][0]['bytes'] = 4097
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                audit.memattr_index_audit(arena, plan)


class RegisterTraceTests(unittest.TestCase):
    def test_access_snapshot_adds_no_actual_c_writes(self):
        self.assertEqual(audit.probe_boot_trace(1,1,1,0), audit.probe_boot_trace(1,1,1,1))
        for args in ((1,1,1,2),(1,1,0,1)):
            with self.assertRaises(ValueError):audit.probe_boot_trace(*args)

    def test_platform_snapshot_adds_no_actual_c_writes(self):
        baseline = audit.probe_boot_trace(1, 1, 0)
        observed = audit.probe_boot_trace(1, 1, 1)
        self.assertEqual(baseline, observed)
        with self.assertRaises(ValueError):
            audit.probe_boot_trace(1, 1, 2)

    def setUp(self):
        self.root, self.memattr = 0x5A40076000, audit.VENDOR_MEMATTR
        self.cases = []
        write = lambda offset, value: dict(offset=hex(offset), value=hex(value), size=4)
        for mode, slot in ((31, 0), (0, 0), (1, 0), (31, 7)):
            shift = slot * 64
            values = ((0x2430, 0x42000006 if mode == 31 else 0x62000006), (0x2434, 0),
                      (0x2400, 0x40076000), (0x2404, 0x5A),
                      (0x2408, 0x888D8F88), (0x240C, 0x84C8D))
            self.cases.append(dict(coherency=mode, as_nr=slot,
                writes=[write(offset + shift, value) for offset, value in values],
                update_writes=[write(0x2418 + shift, 1)]))
        self.starts = {name: [write(0x700, 2)] for name in ('initial', 'reload')}

    def validate(self, cases=None, starts=None):
        audit.validate_register_slices(self.cases if cases is None else cases,
                                      self.starts if starts is None else starts,
                                      self.root, self.memattr)

    def test_complete_trace_including_high_root_and_as_stride(self):
        self.validate()
        with self.assertRaisesRegex(ValueError, 'incomplete'):
            self.validate(cases=self.cases[:3])

    def test_missing_reordered_and_wrong_width_writes_are_rejected(self):
        for mutation in ('missing', 'reordered', 'width', 'root-high', 'transcfg'):
            cases = copy.deepcopy(self.cases)
            writes = cases[0]['writes']
            if mutation == 'missing':
                writes.pop()
            elif mutation == 'reordered':
                writes[0], writes[2] = writes[2], writes[0]
            elif mutation == 'width':
                writes[0]['size'] = 8
            elif mutation == 'root-high':
                writes[3]['value'] = '0x0'
            else:
                writes[0]['value'] = '0x420001c6'
            with self.subTest(mutation=mutation), self.assertRaisesRegex(ValueError, 'register'):
                self.validate(cases=cases)

    def test_update_and_mcu_controls_require_exact_single_writes(self):
        cases = copy.deepcopy(self.cases)
        cases[3]['update_writes'][0]['offset'] = '0x2418'
        with self.assertRaisesRegex(ValueError, 'UPDATE'):
            self.validate(cases=cases)
        for value in (0, 1, 3):
            starts = copy.deepcopy(self.starts)
            starts['initial'][0]['value'] = hex(value)
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, 'AUTO'):
                self.validate(starts=starts)
        with self.assertRaisesRegex(ValueError, 'incomplete'):
            self.validate(starts={})

    @unittest.skipUnless(shutil.which('cc'), 'requires C compiler')
    def test_actual_probe_trace_keeps_mask_gate_and_cleanup(self):
        trace = audit.probe_boot_trace()
        registers = trace['registers_before_auto']
        self.assertEqual(registers['0x2430'], '0x420001c6')
        self.assertEqual(registers['0x2408'], '0x4c4c9f4c')
        self.assertEqual(registers['0x240c'], '0x4c4c4c4c')
        self.assertEqual(registers['0x304'], '0x1f')
        self.assertEqual(registers['0x1008'], '0xffffffff')
        self.assertEqual(registers['0x2008'], '0xffff')
        self.assertEqual(registers['0x28'], '0x80503')
        self.assertEqual([item['value'] for item in trace['writes'] if item['offset'] == '0x700'],
                         ['0x2', '0x0'])
        self.assertEqual([trace['return_code'], trace['stage'], trace['reset_completed']], [-53, 4, 1])

    @unittest.skipUnless(shutil.which('cc'), 'requires C compiler')
    def test_unblocked_platform_path_keeps_actual_c_writes_identical(self):
        original=audit.probe_boot_trace(1,1,1,1,0)
        candidate=audit.probe_boot_trace(1,1,1,1,1)
        self.assertEqual(original,candidate)
        for args in ((1,1,1,1,2),(1,1,1,0,1)):
            with self.assertRaisesRegex(ValueError,'platform path'):
                audit.probe_boot_trace(*args)

    @unittest.skipUnless(shutil.which('cc'), 'requires C compiler')
    def test_ina_diagnostic_changes_exactly_one_actual_c_write(self):
        original, candidate = audit.probe_boot_trace(), audit.probe_boot_trace(1)
        self.assertEqual(len(original['writes']), len(candidate['writes']))
        changes = [(a, b) for a, b in zip(original['writes'], candidate['writes']) if a != b]
        self.assertEqual(changes, [(dict(offset='0x2430', size=4, value='0x420001c6'),
                                    dict(offset='0x2430', size=4, value='0x42000006'))])
        self.assertEqual(original['return_code'], candidate['return_code'])
        self.assertEqual(original['stage'], candidate['stage'])
        self.assertEqual(original['reset_completed'], candidate['reset_completed'])
        with self.assertRaisesRegex(ValueError, 'INA'):
            audit.probe_boot_trace(2)

    @unittest.skipUnless(shutil.which('cc'), 'requires C compiler')
    def test_cached_byte_changes_exactly_one_actual_c_write(self):
        original, candidate = audit.probe_boot_trace(1), audit.probe_boot_trace(1, 1)
        self.assertEqual(len(original['writes']), len(candidate['writes']))
        self.assertEqual([(a, b) for a, b in zip(original['writes'], candidate['writes']) if a != b],
                         [(dict(offset='0x2408', size=4, value='0x4c4c9f4c'),
                           dict(offset='0x2408', size=4, value='0x4c4c884c'))])
        for name in ('return_code', 'stage', 'reset_completed'):
            self.assertEqual(original[name], candidate[name])
        self.assertEqual(candidate['registers_before_auto']['0x240c'], '0x4c4c4c4c')
        self.assertEqual(candidate['registers_before_auto']['0x2430'], '0x42000006')
        with self.assertRaisesRegex(ValueError, 'MEMATTR'):
            audit.probe_boot_trace(1, 2)


if __name__ == '__main__':
    unittest.main()
