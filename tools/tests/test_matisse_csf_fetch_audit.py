"""Negative checks for offline CSF fetch/access auditing, without firmware blobs."""
import importlib.util
from pathlib import Path
import shutil
import struct
import subprocess
import tempfile
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


@unittest.skipUnless(shutil.which('cc'), 'requires C compiler')
class ResetStoreStubTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Public synthetic container: same reset vector/VA contract, no vendor
        # bytes. Use the actual C loader so tests also exercise section layout.
        data = bytearray(136 + 0x2000 + 0x2000)
        struct.pack_into('<I', data, 0, 0xC3F13A6E)
        struct.pack_into('<I', data, 16, 116)
        sections = [(9, 0, 0x1000, 128, 136),
                    (13, 0x01000000, 0x01002000, 136, 136 + 0x2000),
                    (11, 0x02000000, 0x02040000, 0, 0),
                    (0x4000001B, 0x04000000, 0x04004000,
                     136 + 0x2000, len(data))]
        for i, fields in enumerate(sections):
            struct.pack_into('<6I', data, 20 + i * 24, 24 << 8, *fields)
        struct.pack_into('<II', data, 128, 0x02040000, audit.RESET_ENTRY)
        data[136 + 0x18EC:136 + 0x18EE] = bytes.fromhex('fee7')
        with tempfile.TemporaryDirectory() as directory:
            firmware = Path(directory) / 'synthetic.bin'
            firmware.write_bytes(data)
            cls.arena, cls.plan = audit.build_arena(firmware, 0x40077000, memory_group=6)

    def leaf_offset(self, arena, va):
        table = 0
        for shift in (39, 30, 21):
            desc, = struct.unpack_from('<Q', arena, table + ((va >> shift) & 511) * 8)
            table = (desc & audit.PA_MASK) - self.plan['root_pa']
        return table + ((va >> 12) & 511) * 8

    def set_leaf_bits(self, arena, va, bits):
        pos = self.leaf_offset(arena, va)
        desc, = struct.unpack_from('<Q', arena, pos)
        struct.pack_into('<Q', arena, pos, desc | bits)

    def test_changes_only_reset_entry_and_leaves_version_zero(self):
        patched, patch = audit.patch_reset_store_stub(self.arena, self.plan)
        offset, _ = audit.translate(self.arena, self.plan['root_pa'], audit.RESET_ENTRY & ~1)
        self.assertEqual(patch['patch_bytes'], 20)
        self.assertEqual(patched[:offset], self.arena[:offset])
        self.assertEqual(patched[offset + 20:], self.arena[offset + 20:])
        self.assertTrue(patch['page_tables_unchanged'])
        self.assertTrue(patch['outside_patch_unchanged'])
        self.assertFalse(patch['firmware_ready'])
        version_offset, _ = audit.translate(patched, self.plan['root_pa'], 0x04000000)
        self.assertEqual(patched[version_offset:version_offset + 4], bytes(4))
        self.assertEqual(struct.unpack_from('<II', patched, offset + 12),
                         (0x04000000, audit.RESET_STORE_MARKER))

    def test_rejects_input_page_as_version_and_changed_vectors(self):
        with self.assertRaisesRegex(audit.MappingError, 'shared header'):
            audit.patch_reset_store_stub(self.arena, dict(self.plan, shared_va=0x04002000))
        arena = bytearray(self.arena)
        offset, _ = audit.translate(arena, self.plan['root_pa'], 0)
        struct.pack_into('<I', arena, offset + 4, 0x01000001)
        with self.assertRaisesRegex(audit.MappingError, 'reset vectors'):
            audit.patch_reset_store_stub(arena, self.plan)

    def test_rejects_existing_version(self):
        arena = bytearray(self.arena)
        offset, _ = audit.translate(arena, self.plan['root_pa'], 0x04000000)
        struct.pack_into('<I', arena, offset, audit.RESET_STORE_MARKER)
        with self.assertRaisesRegex(audit.MappingError, 'zero initial version'):
            audit.patch_reset_store_stub(arena, self.plan)

    def test_rejects_readonly_shared_or_stack_and_nonexecutable_entry(self):
        for va, bit, message in ((0x04000000, 1 << 7, 'read-only'),
                                  (0x0203FFFC, 1 << 7, 'read-only'),
                                  (audit.RESET_ENTRY & ~1, 1 << 53, 'execute-never')):
            arena = bytearray(self.arena)
            self.set_leaf_bits(arena, va, bit)
            with self.subTest(va=hex(va)), self.assertRaisesRegex(audit.MappingError, message):
                audit.patch_reset_store_stub(arena, self.plan)

    @unittest.skipUnless(shutil.which('clang'), 'requires ARM-capable clang')
    def test_thumb_assembly_matches_template_without_relocations(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / 'stub.o'
            subprocess.run(['clang', '-target', 'armv7m-none-eabi', '-mcpu=cortex-m7', '-mthumb',
                            '-c', str(ROOT / 'tools/matisse-csf-reset-store.S'), '-o', str(target)],
                           check=True, capture_output=True)
            obj = target.read_bytes()
        self.assertEqual(obj[:6], b'\x7fELF\x01\x01')
        shoff, = struct.unpack_from('<I', obj, 32)
        entsize, count, names_index = struct.unpack_from('<HHH', obj, 46)
        sections = [struct.unpack_from('<10I', obj, shoff + i * entsize) for i in range(count)]
        names = obj[sections[names_index][4]:sections[names_index][4] + sections[names_index][5]]
        index, section = next((i, s) for i, s in enumerate(sections)
                              if names[s[0]:].split(b'\0', 1)[0] == b'.text.csf_reset_store')
        self.assertEqual(obj[section[4]:section[4] + section[5]],
                         audit.RESET_STORE_CODE + struct.pack('<II', 0x04000000, audit.RESET_STORE_MARKER))
        self.assertFalse(any(s[1] in (4, 9) and s[7] == index and s[5] for s in sections))

    @unittest.skipUnless(importlib.util.find_spec('unicorn'), 'requires Unicorn')
    def test_emulated_store_and_permission_negative_control(self):
        arena, patch = audit.patch_reset_store_stub(self.arena, self.plan)
        result = audit.replay(arena, self.plan, step_limit=32,
                              self_loop_pc=int(patch['self_loop_va'], 0))
        self.assertTrue(audit.reset_store_pass(result, patch), result)
        readonly = bytearray(arena)
        self.set_leaf_bits(readonly, 0x04000000, 1 << 7)
        negative = audit.replay(readonly, self.plan, step_limit=32,
                                self_loop_pc=int(patch['self_loop_va'], 0))
        self.assertEqual(negative['reason'], 'access-violation')
        self.assertFalse(audit.reset_store_pass(negative, patch))

    @unittest.skipUnless(importlib.util.find_spec('unicorn'), 'requires Unicorn')
    def test_prefilled_marker_without_execution_is_not_a_pass(self):
        _, patch = audit.patch_reset_store_stub(self.arena, self.plan)
        arena = bytearray(self.arena)  # Original synthetic reset just loops.
        offset, _ = audit.translate(arena, self.plan['root_pa'], 0x04000000)
        struct.pack_into('<I', arena, offset, audit.RESET_STORE_MARKER)
        result = audit.replay(arena, self.plan, step_limit=32,
                              self_loop_pc=int(patch['self_loop_va'], 0))
        self.assertEqual(result['version'], patch['marker'])
        self.assertEqual(result['shared_write_count'], 0)
        self.assertFalse(audit.reset_store_pass(result, patch))


if __name__ == '__main__':
    unittest.main()
