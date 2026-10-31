"""Negative checks for offline CSF fetch/access auditing, without firmware blobs."""
import importlib.util
from pathlib import Path
import struct
import unittest

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location('csf_fetch_audit', ROOT / 'tools/matisse-csf-fetch-audit.py')
audit = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(audit)


class FetchAccessTests(unittest.TestCase):
    def setUp(self):
        self.root = 0x40076000
        self.arena = bytearray(6 * audit.PAGE)
        for level in range(3):
            struct.pack_into('<Q', self.arena, level * audit.PAGE,
                             self.root + (level + 1) * audit.PAGE | 3)
        self.put_leaf(0, 0x403)
        self.put_leaf(1, 0x403)

    def put_leaf(self, page, attributes):
        struct.pack_into('<Q', self.arena, 3 * audit.PAGE + page * 8,
                         self.root + (4 + page) * audit.PAGE | attributes)

    def test_walk_and_valid_cross_page_access(self):
        self.assertEqual(audit.translate(self.arena, self.root, 17)[0], 4 * audit.PAGE + 17)
        for op in ('read', 'write', 'fetch'):
            audit.check_access(self.arena, self.root, audit.PAGE - 2, 4, op)

    def test_leaf_group_does_not_alias_physical_address_or_permissions(self):
        self.put_leaf(0, 0x443 | (6 << 59))
        self.assertEqual(audit.translate(self.arena, self.root, 17)[0], 4 * audit.PAGE + 17)
        for op in ('read', 'write', 'fetch'):
            audit.check_access(self.arena, self.root, 0, 4, op, True)
        self.put_leaf(0, 0x4c3 | (6 << 59))
        with self.assertRaisesRegex(audit.MappingError, 'read-only'):
            audit.check_access(self.arena, self.root, 0, 4, 'write')
        self.put_leaf(0, 0x443 | (1 << 54) | (6 << 59))
        with self.assertRaisesRegex(audit.MappingError, 'execute-never'):
            audit.check_access(self.arena, self.root, 0, 2, 'fetch', True)

    def test_missing_next_page_cannot_hide_at_boundary(self):
        struct.pack_into('<Q', self.arena, 3 * audit.PAGE + 8, 0)
        with self.assertRaisesRegex(audit.MappingError, 'missing'):
            audit.check_access(self.arena, self.root, audit.PAGE - 2, 4, 'fetch')

    def test_readonly_page_rejects_write(self):
        self.put_leaf(0, 0x4C3)
        audit.check_access(self.arena, self.root, 0, 4, 'read', True)
        with self.assertRaisesRegex(audit.MappingError, 'read-only'):
            audit.check_access(self.arena, self.root, 0, 4, 'write')

    def test_privileged_and_unprivileged_execute_never_are_distinct(self):
        self.put_leaf(0, 0x443 | (1 << 53))
        with self.assertRaisesRegex(audit.MappingError, 'execute-never'):
            audit.check_access(self.arena, self.root, 0, 2, 'fetch')
        audit.check_access(self.arena, self.root, 0, 2, 'fetch', True)
        self.put_leaf(0, 0x443 | (1 << 54))
        audit.check_access(self.arena, self.root, 0, 2, 'fetch')
        with self.assertRaisesRegex(audit.MappingError, 'execute-never'):
            audit.check_access(self.arena, self.root, 0, 2, 'fetch', True)

    def test_unprivileged_permission_and_access_flag(self):
        with self.assertRaisesRegex(audit.MappingError, 'unprivileged'):
            audit.check_access(self.arena, self.root, 0, 4, 'read', True)
        self.put_leaf(0, 0x43)
        with self.assertRaisesRegex(audit.MappingError, 'access flag'):
            audit.check_access(self.arena, self.root, 0, 4, 'read', True)

    def test_table_and_leaf_cannot_escape_owned_arena(self):
        struct.pack_into('<Q', self.arena, 0, self.root - audit.PAGE | 3)
        with self.assertRaisesRegex(audit.MappingError, 'table outside'):
            audit.translate(self.arena, self.root, 0)
        struct.pack_into('<Q', self.arena, 0, self.root + audit.PAGE | 3)
        self.put_leaf(0, 0x403)
        struct.pack_into('<Q', self.arena, 3 * audit.PAGE, self.root + len(self.arena) | 0x403)
        with self.assertRaisesRegex(audit.MappingError, 'leaf points outside'):
            audit.translate(self.arena, self.root, 0)

    def test_hierarchy_permissions_are_not_silently_ignored(self):
        struct.pack_into('<Q', self.arena, 0, self.root + audit.PAGE | 3 | (1 << 59))
        with self.assertRaisesRegex(audit.MappingError, 'unsupported table descriptor'):
            audit.translate(self.arena, self.root, 0)

    def test_invalid_ranges_and_operations_fail_closed(self):
        for va, size, op in ((-1, 4, 'read'), (1 << 48, 4, 'read'),
                             ((1 << 48) - 1, 2, 'read'), (0, 0, 'read'), (0, 4, 'other')):
            with self.subTest(va=va, size=size, op=op), self.assertRaises(audit.MappingError):
                audit.check_access(self.arena, self.root, va, size, op)


class SyntheticMmioTests(unittest.TestCase):
    def test_raw_words_and_shader_mask_preserve_full_width(self):
        words = audit.synthetic_mmio_words(0xA8620304, 0x1234567800770017, 0x20000000)
        self.assertEqual(words[0x40000010], 0xA8620304)
        self.assertEqual(words[0x40000100], 0x770017)
        self.assertEqual(words[0x40000104], 0x12345678)
        self.assertEqual(words[0x40030004], 0x20000000)
        self.assertEqual(audit.synthetic_mmio_words()[0x40000010], 0xA8620004)

    def test_allocation_expression_uses_highest_shader_bit_not_popcount(self):
        for mask in (0, 1, 0x770017, 1 << 32, 1 << 63):
            for word in (0, 0x300, 0xA8620004, 0xFFFFFFFF):
                with self.subTest(mask=mask, word=word):
                    self.assertEqual(audit.shared_allocation_word(word, mask),
                                     ((word >> 8) & 15) + mask.bit_length() + 3)
        self.assertEqual(audit.shared_allocation_word(0x300, 0x770017), 0x1D)
        self.assertEqual(audit.shared_allocation_word(0, 0x770017), 0x1A)
        self.assertEqual(audit.shared_allocation_word(0, 0), 3)

    def test_synthetic_inputs_reject_width_overflow_and_negative_values(self):
        for args in ((-1, 0, 0), (1 << 32, 0, 0), (0, -1, 0),
                     (0, 1 << 64, 0), (0, 0, -1), (0, 0, 1 << 32)):
            with self.subTest(args=args), self.assertRaisesRegex(ValueError, 'width'):
                audit.synthetic_mmio_words(*args)


if __name__ == '__main__':
    unittest.main()
