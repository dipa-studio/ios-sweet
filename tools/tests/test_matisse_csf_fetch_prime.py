"""Check the linked two-window probe and its unchanged firmware surroundings."""
import importlib.util
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
FIRMWARE = ROOT / 'research/matisse/20261031-gpu/extracted/vendor_a-mali_csffw.bin'
SHA = 'de22d2fc06bc8a859968499a6e609c27fe838be062bf5c97d92ea9f904f7229a'


class FetchPrimeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        sys.path.insert(0, str(ROOT / 'tools'))
        spec = importlib.util.spec_from_file_location('fetch_prime_builder',
                                                     ROOT / 'tools/matisse-shim-gpu-image.py')
        cls.builder = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.builder)

    def test_linked_assembly_matches_both_installed_windows(self):
        bins = sorted((Path.home() / 'Library/Android/sdk/ndk').glob(
            '*/toolchains/llvm/prebuilt/darwin-x86_64/bin'))
        if not bins:
            self.skipTest('requires ARM linker from Android NDK')
        with tempfile.TemporaryDirectory() as directory:
            p = Path(directory)
            (p / 'probe.ld').write_text('SECTIONS { '
                '.text.fresh 0x01000200 : { *(.text.fresh) } '
                '.text.reset 0x010018ec : { *(.text.reset) } }')
            subprocess.run([str(bins[-1] / 'clang'), '--target=armv7m-none-eabi',
                '-mcpu=cortex-m7', '-mthumb', '-nostdlib', '-Wl,--build-id=none',
                '-Wl,-e,csf_fetch_prime_reset', '-Wl,-T,' + str(p / 'probe.ld'),
                str(ROOT / 'tools/matisse-csf-fetch-prime.S'), '-o', str(p / 'probe.elf')],
                check=True, capture_output=True)
            elf = (p / 'probe.elf').read_bytes()
            shoff, = struct.unpack_from('<I', elf, 32)
            size, count, names_index = struct.unpack_from('<HHH', elf, 46)
            sections = [struct.unpack_from('<10I', elf, shoff + i * size) for i in range(count)]
            names_section = sections[names_index]
            names = elf[names_section[4]:names_section[4] + names_section[5]]
            actual = {names[s[0]:].split(b'\0', 1)[0].decode(): elf[s[4]:s[4] + s[5]]
                      for s in sections}
            probe = self.builder.TRACE_PROBE[0x2379]
            self.assertEqual(actual['.text.fresh'], probe['stub'])
            self.assertEqual(actual['.text.reset'], bytes.fromhex(probe['patches'][0x010018ec][1]))
            self.assertEqual(actual['.text.reset'][22:26],
                             self.builder.encode_bl(0x01001902, 0x01000200))
            self.assertFalse(any(s[1] in (4, 9) and s[5] for s in sections))

    @unittest.skipUnless(FIRMWARE.exists(), 'requires pinned local firmware')
    def test_only_two_windows_change_and_fault_handler_stays_original(self):
        original = FIRMWARE.read_bytes()
        embedded, patch = self.builder.fault_vector_probe(FIRMWARE, SHA, 0x2379)
        allowed = set(range(0x0e94 + 0x200, 0x0e94 + 0x204))
        allowed.update(range(0x0e94 + 0x18ec, 0x0e94 + 0x18ec + 38))
        changed = {i for i, (a, b) in enumerate(zip(original, embedded)) if a != b}
        self.assertEqual(len(embedded), len(original))
        self.assertTrue(changed)
        self.assertLessEqual(changed, allowed)
        self.assertEqual(embedded[:0x0e94], original[:0x0e94])
        self.assertEqual(embedded[0x0e94 + 0x19b0:0x0e94 + 0x19d8],
                         original[0x0e94 + 0x19b0:0x0e94 + 0x19d8])
        self.assertEqual(patch['kind'], 'fetch-prime')
        self.assertTrue(patch['fetch_prime']['fault_vectors_unchanged'])
