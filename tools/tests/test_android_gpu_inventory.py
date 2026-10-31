"""Validate static sparse/LP/FDT readers against independent binary fixtures."""
import hashlib
import importlib.util
import io
from pathlib import Path
import struct
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


super_image = load('super_image', 'tools/android-super.py')
inventory = load('inventory', 'tools/matisse-gpu-inventory.py')


def fdt():
    def begin(name):
        b = name.encode() + b'\0'
        return struct.pack('>I', 1) + b + bytes(-len(b) % 4)
    def prop(off, value):
        return struct.pack('>3I', 3, len(value), off) + value + bytes(-len(value) % 4)
    strings = b'compatible\0reg\0'
    tokens = begin('') + begin('soc') + begin('mali@13000000')
    tokens += prop(0, b'mediatek,mali\0arm,mali-valhall\0')
    tokens += prop(11, struct.pack('>4I', 0, 0x13000000, 0, 0x480000))
    tokens += struct.pack('>4I', 2, 2, 2, 9)
    header = struct.pack('>10I', 0xd00dfeed, 56 + len(tokens) + len(strings),
                         56, 56 + len(tokens), 40, 17, 16, 0, len(strings), len(tokens))
    return header + bytes(16) + tokens + strings


def lp_image():
    size = 65536
    data = bytearray(size)
    geometry = bytearray(struct.pack('<II32sIII', 0x616c4467, 52, bytes(32), 4096, 2, 4096))
    geometry[8:40] = hashlib.sha256(geometry).digest()
    data[4096:4148] = geometry
    partition = struct.pack('<36s4I', b'vendor_a', 1, 0, 1, 0)
    extent = struct.pack('<QIQI', 8, 0, 64, 0)
    group = struct.pack('<36sIQ', b'default', 0, 0)
    device = struct.pack('<QIIQ36sI', 64, 4096, 0, size, b'super', 0)
    tables = partition + extent + group + device
    header = bytearray(128)
    struct.pack_into('<IHHI', header, 0, 0x414c5030, 10, 0, 128)
    struct.pack_into('<I', header, 44, len(tables))
    header[48:80] = hashlib.sha256(tables).digest()
    offset = 0
    for pos, table in zip((80, 92, 104, 116), (partition, extent, group, device)):
        struct.pack_into('<III', header, pos, offset, 1, len(table))
        offset += len(table)
    header[12:44] = hashlib.sha256(header).digest()
    data[12288:12288 + len(header) + len(tables)] = header + tables
    data[32768:36864] = b'V' * 4096
    return data


class StaticImageTests(unittest.TestCase):
    def test_sparse_raw_fill_hole_and_unaligned_reads(self):
        raw = b'ABCD' * 1024
        fill = b'1234'
        header = struct.pack('<I4H4I', 0xed26ff3a, 1, 0, 28, 12, 4096, 3, 3, 0)
        blob = header + struct.pack('<HHII', 0xcac1, 0, 1, 4108) + raw
        blob += struct.pack('<HHII', 0xcac2, 0, 1, 16) + fill
        blob += struct.pack('<HHII', 0xcac3, 0, 1, 12)
        expected = raw + fill * 1024 + bytes(4096)
        with tempfile.TemporaryDirectory() as temp:
            p = Path(temp) / 'sparse.img'
            p.write_bytes(blob)
            with super_image.SparseImage(p) as image:
                self.assertEqual(image.read(), expected)
                for start, length in ((4093, 9), (8190, 13), (4101, 5), (0, 0)):
                    self.assertEqual(image.read_at(start, length), expected[start:start + length])
                with self.assertRaises(ValueError):
                    image.read_at(12280, 9)
            p.write_bytes(blob[:-1])
            with self.assertRaises(ValueError):
                super_image.SparseImage(p)

    def test_lp_checksums_and_physical_extent_bounds(self):
        with tempfile.TemporaryDirectory() as temp:
            p = Path(temp) / 'super.img'
            data = lp_image()
            p.write_bytes(data)
            with super_image.SparseImage(p) as image:
                meta = super_image.metadata(image)
                self.assertEqual(meta['partitions']['vendor_a']['bytes'], 4096)
                self.assertEqual(image.read_at(32768, 4), b'VVVV')
                with self.assertRaises(ValueError):
                    super_image.metadata(image, -1)
                with self.assertRaises(ValueError):
                    super_image.metadata(image, 2)
            for off in (4096 + 40, 12288 + 12, 12288 + 128):
                mutated = data.copy()
                mutated[off] ^= 1
                p.write_bytes(mutated)
                with super_image.SparseImage(p) as image:
                    with self.assertRaises(ValueError):
                        super_image.metadata(image)
            # Valid checksums but malicious physical address must still fail.
            mutated = data.copy()
            struct.pack_into('<Q', mutated, 12288 + 128 + 52 + 12, 100000)
            table_len = 52 + 24 + 48 + 64
            mutated[12288 + 48:12288 + 80] = hashlib.sha256(mutated[12416:12416 + table_len]).digest()
            mutated[12300:12332] = bytes(32)
            mutated[12300:12332] = hashlib.sha256(mutated[12288:12416]).digest()
            p.write_bytes(mutated)
            with super_image.SparseImage(p) as image:
                with self.assertRaises(ValueError):
                    super_image.metadata(image)

    def test_fdt_bounds_and_numeric_zero(self):
        blob = fdt()
        nodes = inventory.parse_fdt(blob)
        self.assertEqual(nodes['/soc/mali@13000000']['reg'], struct.pack('>4I', 0, 0x13000000, 0, 0x480000))
        report = inventory.gpu_nodes(nodes)
        self.assertEqual(report['/soc/mali@13000000']['compatible']['strings'], ['mediatek,mali', 'arm,mali-valhall'])
        self.assertEqual(inventory.property_value(bytes(4), 'gpueb-support'), {'cells': ['0x0']})
        for broken in (b'', blob[:-1], bytes(40)):
            with self.assertRaises(ValueError):
                inventory.parse_fdt(broken)
        broken = bytearray(blob)
        struct.pack_into('>I', broken, 56, 3)
        with self.assertRaises(ValueError):
            inventory.parse_fdt(broken)

    def test_dtbo_entry_bounds_and_overlay(self):
        blob = fdt()
        header = struct.pack('>8I', 0xd7b7ab1e, 64 + len(blob), 32, 32, 1, 32, 4096, 0)
        entry = struct.pack('>8I', len(blob), 64, 0, 0, 0, 0, 0, 0)
        with tempfile.TemporaryDirectory() as temp:
            p = Path(temp) / 'dtbo.img'
            p.write_bytes(header + entry + blob)
            result = inventory.inspect_image(p)
            self.assertEqual(len(result['overlays']), 1)
            self.assertIn('/soc/mali@13000000', result['overlays'][0]['gpu_nodes'])
            bad_entry = struct.pack('>8I', len(blob) + 1, 64, 0, 0, 0, 0, 0, 0)
            p.write_bytes(header + bad_entry + blob)
            with self.assertRaises(ValueError):
                inventory.inspect_image(p)


if __name__ == '__main__':
    unittest.main()
