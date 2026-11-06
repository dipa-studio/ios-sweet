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

    def test_fault_entry_assembly_matches_the_2383_patch(self):
        """2383's stub is the linked bytes, not a remembered hex string."""
        bins = sorted((Path.home() / 'Library/Android/sdk/ndk').glob(
            '*/toolchains/llvm/prebuilt/darwin-x86_64/bin'))
        if not bins:
            self.skipTest('requires ARM linker from Android NDK')
        with tempfile.TemporaryDirectory() as directory:
            p = Path(directory)
            (p / 'fault.ld').write_text('SECTIONS { '
                '.text.fault 0x010019b0 : { *(.text.fault) } }')
            subprocess.run([str(bins[-1] / 'clang'), '--target=armv7m-none-eabi',
                '-mcpu=cortex-m7', '-mthumb', '-nostdlib', '-Wl,--build-id=none',
                '-Wl,-e,csf_fault_entry', '-Wl,-T,' + str(p / 'fault.ld'),
                str(ROOT / 'tools/matisse-csf-fault-entry.S'), '-o', str(p / 'fault.elf')],
                check=True, capture_output=True)
            elf = (p / 'fault.elf').read_bytes()
            shoff, = struct.unpack_from('<I', elf, 32)
            size, count, names_index = struct.unpack_from('<HHH', elf, 46)
            sections = [struct.unpack_from('<10I', elf, shoff + i * size) for i in range(count)]
            names_section = sections[names_index]
            names = elf[names_section[4]:names_section[4] + names_section[5]]
            actual = {names[s[0]:].split(b'\0', 1)[0].decode(): elf[s[4]:s[4] + s[5]]
                      for s in sections}
        want, stub = self.builder.FAULT_ENTRY_2383
        self.assertEqual(actual['.text.fault'], bytes.fromhex(stub))
        self.assertEqual(len(bytes.fromhex(want)), len(bytes.fromhex(stub)))
        self.assertEqual(sections[1][3], 0x010019b0)

    @unittest.skipUnless(FIRMWARE.exists(), 'requires pinned local firmware')
    def test_2383_changes_only_the_fault_entry_on_top_of_2382(self):
        """One more window than 2382, and the two probe windows unchanged."""
        original = FIRMWARE.read_bytes()
        embedded_2382, _ = self.builder.fault_vector_probe(FIRMWARE, SHA, 0x2382)
        embedded_2383, patch = self.builder.fault_vector_probe(FIRMWARE, SHA, 0x2383)
        base = 0x0e94
        window = set(range(base + 0x19b0, base + 0x19b0 + 40))
        changed = {i for i, (a, b) in enumerate(zip(embedded_2382, embedded_2383)) if a != b}
        self.assertEqual(len(embedded_2383), len(original))
        self.assertTrue(changed)
        self.assertLessEqual(changed, window)
        # everything outside the three probe windows is the vendor's own bytes
        self.assertEqual(embedded_2383[:base + 0x200], original[:base + 0x200])
        self.assertEqual(embedded_2383[base + 0x204:base + 0x18ec],
                         original[base + 0x204:base + 0x18ec])
        self.assertEqual(embedded_2383[base + 0x18ec + 38:base + 0x19b0],
                         original[base + 0x18ec + 38:base + 0x19b0])
        self.assertEqual(embedded_2383[base + 0x19b0 + 40:], original[base + 0x19b0 + 40:])
        # the 2379 windows must survive untouched
        self.assertEqual(embedded_2383[base + 0x200:base + 0x204], bytes.fromhex('00bf7047'))
        self.assertEqual(embedded_2383[base + 0x18ec:base + 0x18ec + 38],
                         embedded_2382[base + 0x18ec:base + 0x18ec + 38])
        self.assertEqual(patch['kind'], 'fetch-prime')
        self.assertEqual(patch['fetch_prime']['fault_entry']['counter_value'], 20)

    def test_control_entry_assembly_matches_the_2384_patch(self):
        """2384's positive control is the linked bytes too."""
        bins = sorted((Path.home() / 'Library/Android/sdk/ndk').glob(
            '*/toolchains/llvm/prebuilt/darwin-x86_64/bin'))
        if not bins:
            self.skipTest('requires ARM linker from Android NDK')
        with tempfile.TemporaryDirectory() as directory:
            p = Path(directory)
            (p / 'control.ld').write_text('SECTIONS { '
                '.text.control 0x010018ec : { *(.text.control) } }')
            subprocess.run([str(bins[-1] / 'clang'), '--target=armv7m-none-eabi',
                '-mcpu=cortex-m7', '-mthumb', '-nostdlib', '-Wl,--build-id=none',
                '-Wl,-e,csf_fault_control', '-Wl,-T,' + str(p / 'control.ld'),
                str(ROOT / 'tools/matisse-csf-fault-control.S'), '-o', str(p / 'control.elf')],
                check=True, capture_output=True)
            elf = (p / 'control.elf').read_bytes()
            shoff, = struct.unpack_from('<I', elf, 32)
            size, count, names_index = struct.unpack_from('<HHH', elf, 46)
            sections = [struct.unpack_from('<10I', elf, shoff + i * size) for i in range(count)]
            names_section = sections[names_index]
            names = elf[names_section[4]:names_section[4] + names_section[5]]
            actual = {names[s[0]:].split(b'\0', 1)[0].decode(): elf[s[4]:s[4] + s[5]]
                      for s in sections}
        want, stub = self.builder.FAULT_CONTROL_2384
        self.assertEqual(actual['.text.control'], bytes.fromhex(stub))
        self.assertEqual(len(bytes.fromhex(stub)) % 4, 0)
        self.assertLessEqual(len(bytes.fromhex(stub)), 38)
        self.assertEqual(len(bytes.fromhex(want)), len(bytes.fromhex(stub)))
        self.assertEqual(sections[1][3], 0x010018ec)

    @unittest.skipUnless(FIRMWARE.exists(), 'requires pinned local firmware')
    def test_2384_is_2383_with_only_the_control_entry(self):
        original = FIRMWARE.read_bytes()
        embedded_2383, _ = self.builder.fault_vector_probe(FIRMWARE, SHA, 0x2383)
        embedded_2384, patch = self.builder.fault_vector_probe(FIRMWARE, SHA, 0x2384)
        base = 0x0e94
        window = set(range(base + 0x18ec, base + 0x18ec + 38))
        changed = {i for i, (a, b) in enumerate(zip(embedded_2383, embedded_2384)) if a != b}
        self.assertTrue(changed)
        self.assertLessEqual(changed, window)
        # the 2383 fault entry must be byte-identical in both
        self.assertEqual(embedded_2384[base + 0x19b0:base + 0x19b0 + 40],
                         embedded_2383[base + 0x19b0:base + 0x19b0 + 40])
        self.assertEqual(patch['kind'], 'positive-control')
        self.assertEqual(patch['positive_control']['unmapped_va'], '0x3000000')

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
