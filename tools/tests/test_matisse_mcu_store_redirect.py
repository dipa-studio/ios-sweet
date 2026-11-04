import importlib.util
import struct
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TOOLS = ROOT / 'tools'
FIRMWARE = ROOT / 'research/matisse/20261031-gpu/extracted/vendor_a-mali_csffw.bin'
SHA = 'de22d2fc06bc8a859968499a6e609c27fe838be062bf5c97d92ea9f904f7229a'

STORE_SITES = (0x010018f4, 0x010018fc)
LITERALS = ((0x281c, 0x40022000), (0x2820, 0x40022004))
SCRATCH = 0x04000ffc


def load_builder():
    if str(TOOLS) not in sys.path:
        sys.path.insert(0, str(TOOLS))
    spec = importlib.util.spec_from_file_location(
        'shim_gpu_image', TOOLS / 'matisse-shim-gpu-image.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@unittest.skipUnless(FIRMWARE.exists(), 'pinned vendor CSF container is not present')
class McuStoreRedirectTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_builder()
        cls.original = FIRMWARE.read_bytes()

    def test_redirect_only_repoints_the_two_literals(self):
        embedded, patch = self.module.redirect_mcu_stores(FIRMWARE, SHA)
        self.assertEqual(len(embedded), len(self.original))
        changed = [i for i in range(len(self.original)) if self.original[i] != embedded[i]]
        allowed = {offset + i for offset, _ in LITERALS for i in range(4)}
        self.assertTrue(changed)
        self.assertTrue(set(changed) <= allowed, [hex(i) for i in set(changed) - allowed])
        for offset, original in LITERALS:
            self.assertEqual(struct.unpack_from('<I', self.original, offset)[0], original)
            self.assertEqual(struct.unpack_from('<I', embedded, offset)[0], SCRATCH)
        # The reset handler instructions themselves must be untouched.
        for va in STORE_SITES:
            offset = 0x0e94 + va - 0x01000000
            self.assertEqual(self.original[offset:offset + 2], b'\x01\x60')
            self.assertEqual(embedded[offset:offset + 2], b'\x01\x60')
        self.assertTrue(patch['diagnostic_only'])
        self.assertEqual([site['target'] for site in patch['sites']], ['0x4000ffc'] * 2)
        self.assertEqual([site['written_value'] for site in patch['sites']], [0xb, 0x7])
        self.assertEqual(patch['original_container_sha256'], SHA)

    def test_redirect_is_deterministic(self):
        first, _ = self.module.redirect_mcu_stores(FIRMWARE, SHA)
        second, _ = self.module.redirect_mcu_stores(FIRMWARE, SHA)
        self.assertEqual(first, second)

    def test_rejects_a_changed_container(self):
        import tempfile
        with tempfile.TemporaryDirectory() as directory:
            other = Path(directory) / 'other.bin'
            data = bytearray(self.original)
            data[0] ^= 0xff
            other.write_bytes(bytes(data))
            with self.assertRaises(ValueError):
                self.module.redirect_mcu_stores(other, SHA)

    def test_rejects_a_shifted_literal(self):
        import tempfile
        with tempfile.TemporaryDirectory() as directory:
            other = Path(directory) / 'shifted.bin'
            data = bytearray(self.original)
            struct.pack_into('<I', data, 0x281c, 0x40022010)
            other.write_bytes(bytes(data))
            digest = __import__('hashlib').sha256(bytes(data)).hexdigest()
            with self.assertRaises(ValueError):
                self.module.redirect_mcu_stores(other, digest)

    def test_build2340_also_redirects_the_peripheral_load(self):
        embedded, patch = self.module.redirect_mcu_accesses(FIRMWARE, SHA, 0x2340)
        self.assertEqual(len(embedded), len(self.original))
        kinds = [site['kind'] for site in patch['sites']]
        self.assertEqual(kinds, ['store', 'store', 'load'])
        targets = [site['target'] for site in patch['sites']]
        # The first store goes to the version word, the one location2334
        # proved writable from this entry; the second still uses the marker word.
        self.assertEqual(targets, ['0x4000000', '0x4000ffc', '0x4000ff8'])
        # The load literal only shares one byte with its replacement.
        off = 0x282c
        self.assertEqual(struct.unpack_from('<I', self.original, off)[0], 0x40003034)
        self.assertEqual(struct.unpack_from('<I', embedded, off)[0], 0x04000ff8)
        changed = {i for i in range(len(self.original)) if self.original[i] != embedded[i]}
        self.assertTrue(changed <= {off, off + 1, off + 2, off + 3} | {0x281c, 0x281d, 0x281e, 0x281f, 0x2820, 0x2821, 0x2822, 0x2823})

    def test_build2341_checks_the_rest_of_the_first_shared_page(self):
        # 2340 proved the first store lands at shared+0 while a second store to
        # shared+0xffc still does not. 2341 moves only that second store, one
        # word in, so a set features word proves the page takes writes and
        # isolates 0xffc.
        embedded, patch = self.module.redirect_mcu_accesses(FIRMWARE, SHA, 0x2341)
        self.assertEqual(len(embedded), len(self.original))
        targets = [(site['kind'], site['target'], site['written_value'])
                   for site in patch['sites']]
        self.assertEqual(targets, [('store', '0x4000000', 0xb),
                                   ('store', '0x4000004', 0x7),
                                   ('load', '0x4000ff8', None)])
        changed = {i for i in range(len(self.original)) if self.original[i] != embedded[i]}
        allowed = {0x281d, 0x281e, 0x281f, 0x2821, 0x2822, 0x2823,
                   0x282c, 0x282d, 0x282f}
        self.assertEqual(changed, allowed)
        self.assertEqual(struct.unpack_from('<I', embedded, 0x2820)[0], 0x04000004)

    def test_build2342_keeps_the_real_peripheral_store(self):
        # 2341 showed both stores execute and every shared word but 0xffc takes
        # a write. 2342 leaves the 0x40022000 store and the 0x40003034 load
        # exactly as the vendor wrote them and moves only the second store, so a
        # set features word proves the REAL peripheral write completed.
        embedded, patch = self.module.redirect_mcu_accesses(FIRMWARE, SHA, 0x2342)
        self.assertEqual(len(embedded), len(self.original))
        self.assertEqual([(site['kind'], site['literal_va'], site['target'])
                          for site in patch['sites']],
                         [('store', '0x100198c', '0x4000004')])
        changed = {i for i in range(len(self.original)) if self.original[i] != embedded[i]}
        self.assertEqual(changed, {0x2821, 0x2822, 0x2823})
        # The vendor's first peripheral store and the peripheral load survive.
        self.assertEqual(struct.unpack_from('<I', embedded, 0x281c)[0], 0x40022000)
        self.assertEqual(struct.unpack_from('<I', embedded, 0x282c)[0], 0x40003034)

    def test_only_redirect_builds_may_redirect(self):
        for build in (0x2334, 0x2335, 0x2337, 0x2338):
            with self.assertRaises(ValueError):
                self.module.diagnostic_firmware(
                    FIRMWARE, SHA, build, build == 0x2334,
                    entry_probe=build in (0x2335, 0x2336, 0x2337, 0x2338),
                    inline_entry=build in (0x2336, 0x2337, 0x2338),
                    entry_pte_guard=build in (0x2337, 0x2338),
                    mcu_store_redirect=True)
        with self.assertRaises(ValueError):
            self.module.diagnostic_firmware(FIRMWARE, SHA, 0x2339, False)


if __name__ == '__main__':
    unittest.main()
