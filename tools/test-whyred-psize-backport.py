#!/usr/bin/env python3
"""Refusal/bounds tests for the boot103 layout-preserving backport packager."""
import importlib.util
from pathlib import Path
import struct
import unittest

p = Path(__file__).with_name('prepare-whyred-psize-backport.py')
spec = importlib.util.spec_from_file_location('backport', p)
b = importlib.util.module_from_spec(spec)
spec.loader.exec_module(b)


class BackportTests(unittest.TestCase):
    def test_mappings_are_unique_and_bounded(self):
        self.assertEqual(b.mapped([(0x1000, 16, 64)], 0x100c, 4), 76)
        for rows, address, size in [([], 0x1000, 4), ([(0x1000, 16, 64)], 0x100d, 4),
                                    ([(0x1000, 16, 64), (0x1000, 16, 80)], 0x1000, 4)]:
            with self.assertRaises(ValueError): b.mapped(rows, address, size)

    def test_only_result_instruction_changes(self):
        data = b'prefix!!' + b.OLD + b'suffix!!'
        self.assertEqual(b.replace_word(data, 8), b'prefix!!' + b.NEW + b'suffix!!')
        for wrong in [b'', b'prefix!!' + b.NEW, b'prefix!!' + b'1234']:
            with self.assertRaises(ValueError): b.replace_word(wrong, 8)

    def test_boot_rejects_version_size_and_trailing_changes(self):
        data = bytearray(4096)
        data[:8] = b'ANDROID!'
        struct.pack_into('<10I', data, 8, 0, 0, 0, 0, 0, 0, 0, 4096, 0, 0)
        self.assertEqual(b.boot_parts(data), [('kernel', 4096, 0), ('ramdisk', 4096, 0), ('second', 4096, 0)])
        for offset, value in [(36, 2048), (40, 2), (8, 4096)]:
            wrong = bytearray(data); struct.pack_into('<I', wrong, offset, value)
            with self.assertRaises(ValueError): b.boot_parts(wrong)
        with self.assertRaises(ValueError): b.boot_parts(data + b'\0')

    def test_unpinned_images_never_prepare(self):
        for kernel, boot in [(b'', b''), (bytes(4096), b'ANDROID!' + bytes(4088))]:
            with self.assertRaises(ValueError): b.prepare(kernel, boot)


if __name__ == '__main__':
    unittest.main()
