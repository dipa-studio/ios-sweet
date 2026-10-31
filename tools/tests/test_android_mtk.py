"""Independent MTK header fixtures exercise component shifts and hostile sizes."""
import importlib.util
from pathlib import Path
import struct
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location('mtk', ROOT / 'tools/android-mtk.py')
mtk = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(mtk)


def component(name, payload):
    header = bytearray(512)
    struct.pack_into('<II32sII', header, 0, 0x58881688, len(payload), name.encode(), 0xffffffff, 0xffffffff)
    struct.pack_into('<8I', header, 48, 0x58891689, 512, 1, 0, 0, 16, 0, 0)
    return header + payload + bytes(-len(payload) % 16)


class MtkImageTests(unittest.TestCase):
    def test_certificate_size_shift_preserves_later_components(self):
        a = component('lk', b'code') + component('cert2', b'A' * 17) + component('dtb', b'DTB')
        b = component('lk', b'edit') + component('cert2', b'B' * 47) + component('dtb', b'DTB')
        with tempfile.TemporaryDirectory() as directory:
            left, right = Path(directory) / 'a.img', Path(directory) / 'b.img'
            left.write_bytes(a)
            right.write_bytes(b + bytes(4096))
            x, y = mtk.inspect(left), mtk.inspect(right)
        rows = mtk.compare(x, y)
        self.assertEqual([r['payload_equal'] for r in rows], [False, False, True])
        self.assertNotEqual(rows[2]['left_payload_offset'], rows[2]['right_payload_offset'])
        self.assertEqual(y['trailer']['nonzero_bytes'], 0)
        self.assertEqual(y['trailer']['bytes'], 4096)
        self.assertFalse(y['certificate_authentication_performed'])

    def test_opaque_trailer_and_duplicate_certificates(self):
        blob = component('fw', b'firmware') + component('cert1', b'A') + component('cert1', b'B')
        trailer = b'AVB' + struct.pack('<I', 0x58881688) + bytes(128)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'image'
            path.write_bytes(blob + trailer)
            result = mtk.inspect(path)
        self.assertEqual(len(result['components']), 3)
        self.assertEqual(result['trailer']['bytes'], len(trailer))
        self.assertEqual([r['occurrence'] for r in mtk.compare(result, result)], [0, 0, 1])

    def test_bounds_versions_and_alignment(self):
        valid = component('gpueb', b'x' * 17)
        cases = [b'', bytes(80), valid[:79], valid[:512], valid[:-1]]
        for offset, value in [(4, 0xffffffff), (48, 0), (52, 79), (52, 4097),
                              (56, 2), (68, 3), (68, 0), (72, 1)]:
            bad = bytearray(valid)
            struct.pack_into('<I', bad, offset, value)
            cases.append(bad)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'image'
            for blob in cases:
                path.write_bytes(blob)
                with self.subTest(size=len(blob)), self.assertRaises(ValueError):
                    mtk.inspect(path)
            # Exact final payload end without padding is also legitimate.
            path.write_bytes(valid[:529])
            self.assertEqual(mtk.inspect(path)['components'][0]['payload_bytes'], 17)


if __name__ == '__main__':
    unittest.main()
