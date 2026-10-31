"""Offline audit validation without proprietary modules or emulator dependency."""
import hashlib
import importlib.util
from pathlib import Path
import struct
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location('vendor_mmu_audit', ROOT / 'tools/matisse-csf-vendor-mmu-audit.py')
audit = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(audit)


def elf_fixture(relocations=b''):
    names = b'\0.shstrtab\0.text\0.rela.text.memory_group_manager_probe\0'
    sections = [(0, 0, b''), (1, 3, names), (11, 1, bytes(0xA00)), (17, 4, relocations)]
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


if __name__ == '__main__':
    unittest.main()
