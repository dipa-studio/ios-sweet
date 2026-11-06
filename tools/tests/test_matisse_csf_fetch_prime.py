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
ADT = ROOT / 'research/matisse/20261031-hs/matisse-userland-native-keys-2317.adt'


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

    @unittest.skipUnless(FIRMWARE.exists(), 'requires pinned local firmware')
    def test_2385_moves_only_the_reset_word_and_its_target(self):
        original = FIRMWARE.read_bytes()
        embedded, patch = self.builder.fault_vector_probe(FIRMWARE, SHA, 0x2385)
        config, code = 0x0380, 0x0e94
        allowed = set(range(config + 4, config + 8))
        allowed |= set(range(code + 0xe000, code + 0xe000 + 20))
        expected = self.builder.COLD_BOOT_2385
        allowed |= set(range(code + 0x200, code + 0x200 + len(bytes.fromhex(expected[0]))))
        allowed |= set(range(code + 0x19b0, code + 0x19b0 + 40))
        changed = {i for i, (a, b) in enumerate(zip(original, embedded)) if a != b}
        self.assertTrue(changed)
        self.assertLessEqual(changed, allowed)
        self.assertEqual(int.from_bytes(embedded[config + 4:config + 8], 'little'), 0x0100e001)
        # SP and the five fault vectors must not move with it
        self.assertEqual(embedded[config:config + 4], original[config:config + 4])
        self.assertEqual(embedded[config + 8:config + 0x20], original[config + 8:config + 0x20])
        # The vendor entry program stays: reset never reaches 0x010018ec now.
        self.assertEqual(embedded[code + 0x18ec:code + 0x18ec + 38],
                         original[code + 0x18ec:code + 0x18ec + 38])
        self.assertEqual(patch['reset_vector']['was'], '0x10018ed')
        self.assertEqual(patch['reset_vector']['target'], '0x100e000')
        self.assertEqual(patch['kind'], 'cold-boot-fetch')

    @unittest.skipUnless(FIRMWARE.exists(), 'requires pinned local firmware')
    def test_2385_refuses_a_vector_that_moved_or_a_target_outside_code(self):
        spec = self.builder.TRACE_PROBE[0x2385]
        # a word that is not the vendor reset / a target without the Thumb bit /
        # a target outside the 64 KB code section
        for bad in ((0x010018ec, 0x0100E001), (0x010018ed, 0x0100E000),
                    (0x010018ed, 0x03000001)):
            saved = spec['reset_vector']
            spec['reset_vector'] = bad
            try:
                with self.assertRaises(ValueError):
                    self.builder.fault_vector_probe(FIRMWARE, SHA, 0x2385)
            finally:
                spec['reset_vector'] = saved

    def test_leaf_property_and_shim_macro_read_the_same_list(self):
        """The gate that emits the ADT property and the one that compiles the
        reader drifted apart between 2388 and 2389: 2389 shipped with neither, so
        the capture had no leaves and the decoder refused it. Both now read one
        list, and this test fails if either is written out again."""
        self.assertIn(0x2390, self.builder.LEAF_PROBE_BUILDS)
        self.assertIn(0x2388, self.builder.LEAF_PROBE_BUILDS)
        source = (ROOT / 'tools/matisse-shim-gpu-image.py').read_text()
        self.assertIn('a.build_id in LEAF_PROBE_BUILDS)', source)
        self.assertIn("('1' if a.build_id in LEAF_PROBE_BUILDS else '0')", source)
        self.assertNotIn('a.build_id == 0x2388', source)

    @unittest.skipUnless(ADT.exists(), 'requires the pinned ADT')
    def test_leaf_property_is_32_bytes_and_only_when_asked(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location('adt', ROOT / 'tools/adt.py')
        adt = importlib.util.module_from_spec(spec); spec.loader.exec_module(adt)
        for flag, size in ((True, 32), (False, None)):
            tree = self.builder.diagnostic_adt(ADT.read_bytes(), 0x2390, False, flag)
            root, _ = adt.parse(tree)
            chosen = next(c for c in root.children if c.name == 'chosen')
            prop = chosen.prop('sweet-csf-leaf')
            self.assertEqual(len(prop) if prop is not None else None, size)

    @unittest.skipUnless(FIRMWARE.exists(), 'requires pinned local firmware')
    def test_2391_moves_only_the_word_and_adds_the_third_landing(self):
        original = FIRMWARE.read_bytes()
        embedded_2390, _ = self.builder.fault_vector_probe(FIRMWARE, SHA, 0x2390)
        embedded_2391, patch = self.builder.fault_vector_probe(FIRMWARE, SHA, 0x2391)
        config, code = 0x0380, 0x0e94
        # the word moves, and the block it names becomes the program; 2390's two
        # landings keep their bytes so the three controls stay comparable
        allowed = set(range(config + 4, config + 8))
        allowed |= set(range(code + 0x1A00, code + 0x1A00 + 20))
        changed = {i for i, (a, b) in enumerate(zip(embedded_2390, embedded_2391)) if a != b}
        self.assertTrue(changed)
        self.assertLessEqual(changed, allowed)
        self.assertEqual(int.from_bytes(embedded_2391[config + 4:config + 8], 'little'),
                         0x01001A01)
        self.assertEqual(embedded_2391[code + 0x1A00:code + 0x1A00 + 20],
                         bytes.fromhex(self.builder.COLD_BOOT_2391[1]))
        # 0x1A00 is code in the vendor blob, so the probe has to name it
        self.assertEqual(embedded_2391[code + 0x1A00:code + 0x1A00 + 20][:2],
                         bytes.fromhex('72b6'))
        for landing, program in ((0x18ec, self.builder.COLD_BOOT_2390_ENTRY),
                                 (0x1000, self.builder.COLD_BOOT_2390_PAGE)):
            self.assertEqual(embedded_2391[code + landing:code + landing + 20],
                             bytes.fromhex(program[1]), hex(landing))
        self.assertEqual([item['target'] for item in patch['cold_boot']['landings']],
                         ['0x1001a00', '0x1001000', '0x10018ec'])
        self.assertEqual(patch['cold_boot']['target'], '0x1001a00')
        self.assertNotIn('reset_vector_unchanged', patch['cold_boot'])
        self.assertEqual(patch['leaf_probe']['marks'], '420..423')

    @unittest.skipUnless(FIRMWARE.exists(), 'requires pinned local firmware')
    def test_2390_leaves_the_vendor_word_alone_and_instruments_both_landings(self):
        original = FIRMWARE.read_bytes()
        embedded_2389, _ = self.builder.fault_vector_probe(FIRMWARE, SHA, 0x2389)
        embedded_2390, patch = self.builder.fault_vector_probe(FIRMWARE, SHA, 0x2390)
        config, code = 0x0380, 0x0e94
        # two differences against 2389, both intended: the vendor reset handler at
        # 0x010018ec becomes our program, and the vector 2389 moved is restored to
        # the value the device ships.
        allowed = set(range(code + 0x18ec, code + 0x18ec + 20))
        allowed |= set(range(config + 4, config + 8))
        changed = {i for i, (a, b) in enumerate(zip(embedded_2389, embedded_2390)) if a != b}
        self.assertTrue(changed)
        self.assertLessEqual(changed, allowed)
        # the word the device ships is untouched, which is the whole point
        self.assertEqual(embedded_2390[config + 4:config + 8],
                         original[config + 4:config + 8])
        self.assertEqual(int.from_bytes(embedded_2390[config + 4:config + 8], 'little'),
                         0x010018ed)
        self.assertTrue(patch['reset_vector']['unchanged'])
        self.assertEqual(patch['reset_vector']['now'], '0x10018ed')
        self.assertEqual(embedded_2390[code + 0x18ec:code + 0x18ec + 20],
                         bytes.fromhex(self.builder.COLD_BOOT_2390_ENTRY[1]))
        # both landings carry a marker program, so the capture names the landing
        self.assertEqual(embedded_2390[code + 0x1000:code + 0x1000 + 20],
                         bytes.fromhex(self.builder.COLD_BOOT_2390_PAGE[1]))
        self.assertEqual([landing['target'] for landing in patch['cold_boot']['landings']],
                         ['0x10018ec', '0x1001000'])
        self.assertTrue(patch['cold_boot']['reset_vector_unchanged'])
        self.assertEqual(patch['leaf_probe']['marks'], '420..423')

    @unittest.skipUnless(FIRMWARE.exists(), 'requires pinned local firmware')
    def test_2389_moves_only_the_vector_to_page_one_offset_zero(self):
        original = FIRMWARE.read_bytes()
        embedded_2388, _ = self.builder.fault_vector_probe(FIRMWARE, SHA, 0x2388)
        embedded_2389, patch = self.builder.fault_vector_probe(FIRMWARE, SHA, 0x2389)
        config, code = 0x0380, 0x0e94
        allowed = set(range(config + 4, config + 8))
        allowed |= set(range(code + 0x1000, code + 0x1000 + 20))
        allowed |= set(range(code + 0x1200, code + 0x1200 + 20))
        changed = {i for i, (a, b) in enumerate(zip(embedded_2388, embedded_2389)) if a != b}
        self.assertTrue(changed)
        self.assertLessEqual(changed, allowed)
        self.assertEqual(int.from_bytes(embedded_2389[config + 4:config + 8], 'little'),
                         0x01001001)
        self.assertEqual(embedded_2389[code + 0x1000:code + 0x1000 + 20],
                         bytes.fromhex(self.builder.COLD_BOOT_2389[1]))
        # 2388's block goes back to vendor bytes
        self.assertEqual(embedded_2389[code + 0x1200:code + 0x1200 + 20],
                         original[code + 0x1200:code + 0x1200 + 20])
        self.assertEqual(patch['cold_boot']['target'], '0x1001000')
        self.assertEqual(patch['leaf_probe']['marks'], '420..423')

    @unittest.skipUnless(FIRMWARE.exists(), 'requires pinned local firmware')
    def test_2388_moves_only_the_vector_and_page_1(self):
        original = FIRMWARE.read_bytes()
        embedded_2387, _ = self.builder.fault_vector_probe(FIRMWARE, SHA, 0x2387)
        embedded_2388, patch = self.builder.fault_vector_probe(FIRMWARE, SHA, 0x2388)
        config, code = 0x0380, 0x0e94
        allowed = set(range(config + 4, config + 8))
        allowed |= set(range(code + 0x1200, code + 0x1200 + 20))
        allowed |= set(range(code + 0x600, code + 0x600 + 20))
        changed = {i for i, (a, b) in enumerate(zip(embedded_2387, embedded_2388)) if a != b}
        self.assertTrue(changed)
        self.assertLessEqual(changed, allowed)
        self.assertEqual(int.from_bytes(embedded_2388[config + 4:config + 8], 'little'), 0x01001201)
        self.assertEqual(embedded_2388[code + 0x1200:code + 0x1200 + 20],
                         bytes.fromhex(self.builder.COLD_BOOT_2388[1]))
        # 2387's block goes back to vendor bytes: this build fetches page 1 only
        self.assertEqual(embedded_2388[code + 0x600:code + 0x600 + 20],
                         original[code + 0x600:code + 0x600 + 20])
        self.assertEqual(patch['cold_boot']['target'], '0x1001200')
        self.assertEqual(patch['cold_boot']['marker_value'], '0x1001200')

    @unittest.skipUnless(FIRMWARE.exists(), 'requires pinned local firmware')
    def test_2387_moves_only_the_vector_and_its_block(self):
        original = FIRMWARE.read_bytes()
        embedded_2385, _ = self.builder.fault_vector_probe(FIRMWARE, SHA, 0x2385)
        embedded_2387, patch = self.builder.fault_vector_probe(FIRMWARE, SHA, 0x2387)
        config, code = 0x0380, 0x0e94
        allowed = set(range(config + 4, config + 8))
        allowed |= set(range(code + 0x600, code + 0x600 + 20))
        allowed |= set(range(code + 0xe000, code + 0xe000 + 20))
        changed = {i for i, (a, b) in enumerate(zip(embedded_2385, embedded_2387)) if a != b}
        self.assertTrue(changed)
        self.assertLessEqual(changed, allowed)
        self.assertEqual(int.from_bytes(embedded_2387[config + 4:config + 8], 'little'), 0x01000601)
        self.assertEqual(embedded_2387[code + 0x600:code + 0x600 + 20],
                         bytes.fromhex(self.builder.COLD_BOOT_2387[1]))
        self.assertEqual(embedded_2387[code + 0xe000:code + 0xe000 + 20],
                         original[code + 0xe000:code + 0xe000 + 20])
        # the cursed block keeps 2385's two-byte stub: nothing fetches it here
        self.assertEqual(embedded_2387[code + 0x200:code + 0x204], bytes.fromhex('00bf7047'))
        self.assertEqual(patch['cold_boot']['target'], '0x1000600')

    @unittest.skipUnless(FIRMWARE.exists(), 'requires pinned local firmware')
    def test_2386_is_2385_with_the_vector_pointed_at_the_other_block(self):
        original = FIRMWARE.read_bytes()
        embedded_2385, _ = self.builder.fault_vector_probe(FIRMWARE, SHA, 0x2385)
        embedded_2386, patch = self.builder.fault_vector_probe(FIRMWARE, SHA, 0x2386)
        config, code = 0x0380, 0x0e94
        allowed = set(range(config + 4, config + 8))
        allowed |= set(range(code + 0x200, code + 0x200 + 20))
        allowed |= set(range(code + 0xe000, code + 0xe000 + 20))
        changed = {i for i, (a, b) in enumerate(zip(embedded_2385, embedded_2386)) if a != b}
        self.assertTrue(changed)
        self.assertLessEqual(changed, allowed)
        self.assertEqual(int.from_bytes(embedded_2386[config + 4:config + 8], 'little'), 0x01000201)
        # 2385's block is vendor-original in this image; the program moved here
        self.assertEqual(embedded_2386[code + 0xe000:code + 0xe000 + 20],
                         original[code + 0xe000:code + 0xe000 + 20])
        self.assertEqual(embedded_2386[code + 0x200:code + 0x200 + 20],
                         bytes.fromhex(self.builder.COLD_BOOT_2386[1]))
        self.assertEqual(patch['cold_boot']['target'], '0x1000200')
        self.assertEqual(patch['cold_boot']['marker_value'], '0x1000200')

    def test_cold_boot_assembly_matches_both_pinned_programs(self):
        """2385 and 2386 are the same twenty bytes with one immediate changed."""
        bins = sorted((Path.home() / 'Library/Android/sdk/ndk').glob(
            '*/toolchains/llvm/prebuilt/darwin-x86_64/bin'))
        if not bins:
            self.skipTest('requires ARM linker from Android NDK')
        cases = ((0x2385, 0x0100E000, 'COLD_BOOT_2385', False),
                 (0x2388, 0x01001200, 'COLD_BOOT_2388', False),
                 (0x2386, 0x01000200, 'COLD_BOOT_2386', False),
                 (0x2387, 0x01000600, 'COLD_BOOT_2387', False),
                 (0x2389, 0x01001000, 'COLD_BOOT_2389', False),
                 # 0x010018ec is out of range of add.w's modified immediate and of
                 # addw's twelve bits, so the 2390 entry variant materialises the
                 # word with movw/movt: same twenty bytes, different encoding.
                 (0x2390, 0x010018EC, 'COLD_BOOT_2390_ENTRY', True))
        for build, target, pinned, wide in cases:
            with self.subTest(build=hex(build)), tempfile.TemporaryDirectory() as directory:
                p = Path(directory)
                (p / 'cold.ld').write_text('SECTIONS { '
                    '.text.cold %#x : { *(.text.cold) } }' % target)
                command = [str(bins[-1] / 'clang'), '--target=armv7m-none-eabi',
                    '-mcpu=cortex-m7', '-mthumb', '-nostdlib', '-Wl,--build-id=none',
                    '-Wl,-e,csf_cold_boot', '-Wl,-T,' + str(p / 'cold.ld'),
                    '-DCOLD_TARGET=%#x' % target]
                if wide:
                    command.append('-DCOLD_TARGET_WIDE')
                command += [str(ROOT / 'tools/matisse-csf-coldboot.S'), '-o', str(p / 'cold.elf')]
                subprocess.run(command, check=True, capture_output=True)
                elf = (p / 'cold.elf').read_bytes()
                shoff, = struct.unpack_from('<I', elf, 32)
                size, count, names_index = struct.unpack_from('<HHH', elf, 46)
                sections = [struct.unpack_from('<10I', elf, shoff + i * size) for i in range(count)]
                names_section = sections[names_index]
                names = elf[names_section[4]:names_section[4] + names_section[5]]
                actual = {names[s[0]:].split(b'\0', 1)[0].decode(): elf[s[4]:s[4] + s[5]]
                          for s in sections}
                want, stub = getattr(self.builder, pinned)
                self.assertEqual(actual['.text.cold'], bytes.fromhex(stub))
                self.assertEqual(len(bytes.fromhex(stub)), len(bytes.fromhex(want)))
                self.assertEqual(sections[1][3], target)
                # nothing but the marker store, so no stack and no literal pool
                self.assertEqual(bytes.fromhex(stub)[-4:], bytes.fromhex('00bffee7'))
        # the add.w family differs only in the block's own address: one halfword
        programs = {b: bytes.fromhex(getattr(self.builder, pin)[1])
                    for b, _, pin, wide in cases if not wide}
        self.assertEqual({len(v) for v in programs.values()}, {20})
        for first in programs:
            for second in programs:
                if first >= second:
                    continue
                diff = [i for i in range(20) if programs[first][i] != programs[second][i]]
                self.assertLessEqual(len(diff), 2, (hex(first), hex(second)))
        # the wide variant is the same shape, not the same encoding: cpsid, the
        # absolute target, the store, the park, and nothing else
        wide_bytes = bytes.fromhex(self.builder.COLD_BOOT_2390_ENTRY[1])
        self.assertEqual(len(wide_bytes), 20)
        self.assertEqual(wide_bytes[:2], bytes.fromhex('72b6'))
        self.assertEqual(wide_bytes[-4:], bytes.fromhex('00bffee7'))
        movable = bytes.fromhex(self.builder.COLD_BOOT_2389[1])
        self.assertEqual(wide_bytes[-10:], movable[-10:])

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
