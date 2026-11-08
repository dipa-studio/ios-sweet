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

    def test_fault_entry_2401_writes_the_e3_marker_and_keeps_the_frame(self):
        """2401's fault stub is the linked bytes, and still forty of them."""
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
                '-Wl,-e,csf_fault_entry_2401', '-Wl,-T,' + str(p / 'fault.ld'),
                str(ROOT / 'tools/matisse-csf-fault-entry-e3.S'), '-o', str(p / 'fault.elf')],
                check=True, capture_output=True)
            elf = (p / 'fault.elf').read_bytes()
            shoff, = struct.unpack_from('<I', elf, 32)
            size, count, names_index = struct.unpack_from('<HHH', elf, 46)
            sections = [struct.unpack_from('<10I', elf, shoff + i * size) for i in range(count)]
            names_section = sections[names_index]
            names = elf[names_section[4]:names_section[4] + names_section[5]]
            actual = {names[s[0]:].split(b'\0', 1)[0].decode(): elf[s[4]:s[4] + s[5]]
                      for s in sections}
        want, stub = self.builder.FAULT_ENTRY_2401
        self.assertEqual(actual['.text.fault'], bytes.fromhex(stub))
        # The patch engine keeps the replaced region's length, and 0x010019b0
        # holds exactly the vendor's forty bytes.
        self.assertEqual(len(bytes.fromhex(stub)), 40)
        self.assertEqual(len(bytes.fromhex(want)), 40)
        self.assertEqual(len(bytes.fromhex(stub)) % 4, 0)
        self.assertEqual(sections[1][3], 0x010019b0)
        # shared+8 = 0xE3, then the stacked PC at +12 and CFSR at +20.
        self.assertEqual(bytes.fromhex(stub)[:8], bytes.fromhex('01229206e3209060'))
        self.assertEqual(bytes.fromhex(stub)[22:26], bytes.fromhex('8169d160'))
        self.assertEqual(bytes.fromhex(stub)[32:36], bytes.fromhex('fee700bf'))
        self.assertEqual(bytes.fromhex(stub)[36:], bytes.fromhex('28ed00e0'))
        # 2383's stub must stay untouched: 2383..2400 keep their pinned bytes.
        self.assertNotEqual(self.builder.FAULT_ENTRY_2383[1], stub)

    def test_ladder_2402_assembly_matches_the_pinned_bytes(self):
        """2402's six-read matrix is the linked bytes, and 72 of them."""
        bins = sorted((Path.home() / 'Library/Android/sdk/ndk').glob(
            '*/toolchains/llvm/prebuilt/darwin-x86_64/bin'))
        if not bins:
            self.skipTest('requires ARM linker from Android NDK')
        with tempfile.TemporaryDirectory() as directory:
            p = Path(directory)
            (p / 'ladder.ld').write_text('SECTIONS { '
                '.text.ladder 0x0100E000 : { *(.text.ladder) } }')
            subprocess.run([str(bins[-1] / 'clang'), '--target=armv7m-none-eabi',
                '-mcpu=cortex-m7', '-mthumb', '-nostdlib', '-Wl,--build-id=none',
                '-Wl,-e,csf_ladder_2402', '-Wl,-T,' + str(p / 'ladder.ld'),
                str(ROOT / 'tools/matisse-csf-ladder2402.S'), '-o', str(p / 'ladder.elf')],
                check=True, capture_output=True)
            elf = (p / 'ladder.elf').read_bytes()
            shoff, = struct.unpack_from('<I', elf, 32)
            size, count, names_index = struct.unpack_from('<HHH', elf, 46)
            sections = [struct.unpack_from('<10I', elf, shoff + i * size) for i in range(count)]
            names_section = sections[names_index]
            names = elf[names_section[4]:names_section[4] + names_section[5]]
            actual = {names[s[0]:].split(b'\0', 1)[0].decode(): elf[s[4]:s[4] + s[5]]
                      for s in sections}
        want = bytes.fromhex(self.builder.COLD_BOOT_2402[1])
        self.assertEqual(actual['.text.ladder'], want)
        self.assertEqual(len(want), 72)
        self.assertEqual(len(want), len(bytes.fromhex(self.builder.COLD_BOOT_2402[0])))
        self.assertEqual(sections[1][3], 0x0100E000)
        # The three bit-9 = 0 reads come first and must be ordinary loads; the
        # first two use offset 0 (16-bit form), the third r9 = 0xE400.
        self.assertEqual(want[0x0e:0x12], bytes.fromhex('4ef20028'))
        self.assertEqual(want[0x12:0x16], bytes.fromhex('4ef20049'))
        self.assertEqual(want[0x1a:0x1c], bytes.fromhex('2068'))
        self.assertEqual(want[0x20:0x22], bytes.fromhex('2868'))
        self.assertEqual(want[0x26:0x2a], bytes.fromhex('56f80900'))
        # Then the decisive pair: 0x0100E200 stalls or returns against a word in
        # its own page, and 0x0100E200 must come after 0x0100E400.
        self.assertEqual(want[0x2e:0x32], bytes.fromhex('56f80800'))
        self.assertLess(want.index(bytes.fromhex('56f80900')),
                        want.index(bytes.fromhex('56f80800')))
        self.assertEqual(want[0x36:0x3a], bytes.fromhex('d5f80002'))
        self.assertEqual(want[0x3e:0x42], bytes.fromhex('d4f80002'))
        # No branch before the terminal loop: every access is a plain read.
        self.assertEqual(want[-2:], bytes.fromhex('fee7'))

    def test_ladder_2404_assembly_matches_the_pinned_bytes(self):
        """2404: three reads, one store, and a DSB that makes the store count."""
        bins = sorted((Path.home() / 'Library/Android/sdk/ndk').glob(
            '*/toolchains/llvm/prebuilt/darwin-x86_64/bin'))
        if not bins:
            self.skipTest('requires ARM linker from Android NDK')
        with tempfile.TemporaryDirectory() as directory:
            p = Path(directory)
            (p / 'ladder.ld').write_text('SECTIONS { '
                '.text.ladder 0x0100E000 : { *(.text.ladder) } }')
            subprocess.run([str(bins[-1] / 'clang'), '--target=armv7m-none-eabi',
                '-mcpu=cortex-m7', '-mthumb', '-nostdlib', '-Wl,--build-id=none',
                '-Wl,-e,csf_ladder_2404', '-Wl,-T,' + str(p / 'ladder.ld'),
                str(ROOT / 'tools/matisse-csf-ladder2404.S'), '-o', str(p / 'ladder.elf')],
                check=True, capture_output=True)
            elf = (p / 'ladder.elf').read_bytes()
            shoff, = struct.unpack_from('<I', elf, 32)
            size, count, names_index = struct.unpack_from('<HHH', elf, 46)
            sections = [struct.unpack_from('<10I', elf, shoff + i * size) for i in range(count)]
            names_section = sections[names_index]
            names = elf[names_section[4]:names_section[4] + names_section[5]]
            actual = {names[s[0]:].split(b'\0', 1)[0].decode(): elf[s[4]:s[4] + s[5]]
                      for s in sections}
        want = bytes.fromhex(self.builder.COLD_BOOT_2404[1])
        self.assertEqual(actual['.text.ladder'], want)
        self.assertEqual(len(want), 88)
        self.assertEqual(len(want), len(bytes.fromhex(self.builder.COLD_BOOT_2404[0])))
        self.assertEqual(sections[1][3], 0x0100E000)
        # read 1 goes through r6 = 0x01000000, read 2 through r7 = 0x06040000,
        # both at r8 = 0xE400 and both storing to shared+12.
        self.assertEqual(want[0x20:0x24], bytes.fromhex('56f80800'))
        self.assertEqual(want[0x2a:0x2e], bytes.fromhex('57f80800'))
        self.assertEqual(want[0x24:0x26], bytes.fromhex('d060'))
        self.assertEqual(want[0x2e:0x30], bytes.fromhex('d060'))
        # store 0x5a5a5a5a to 0x04000200, then DSB SY, then the read back.
        self.assertEqual(want[0x3c:0x40], bytes.fromhex('c2f80002'))
        self.assertEqual(want[0x40:0x44], bytes.fromhex('bff34f8f'))
        self.assertEqual(want[0x48:0x4c], bytes.fromhex('d2f80002'))
        self.assertLess(want.index(bytes.fromhex('c2f80002')),
                        want.index(bytes.fromhex('bff34f8f')))
        self.assertLess(want.index(bytes.fromhex('bff34f8f')),
                        want.index(bytes.fromhex('d2f80002')))
        self.assertEqual(want[0x52:0x54], bytes.fromhex('fee7'))
        self.assertEqual(want[0x54:], bytes.fromhex('00bf00bf'))

    def test_ladder_2405_barriers_every_marker(self):
        """2405: 2404's accesses, with a DSB after every store in the ladder."""
        bins = sorted((Path.home() / 'Library/Android/sdk/ndk').glob(
            '*/toolchains/llvm/prebuilt/darwin-x86_64/bin'))
        if not bins:
            self.skipTest('requires ARM linker from Android NDK')
        with tempfile.TemporaryDirectory() as directory:
            p = Path(directory)
            (p / 'ladder.ld').write_text('SECTIONS { '
                '.text.ladder 0x0100E000 : { *(.text.ladder) } }')
            subprocess.run([str(bins[-1] / 'clang'), '--target=armv7m-none-eabi',
                '-mcpu=cortex-m7', '-mthumb', '-nostdlib', '-Wl,--build-id=none',
                '-Wl,-e,csf_ladder_2405', '-Wl,-T,' + str(p / 'ladder.ld'),
                str(ROOT / 'tools/matisse-csf-ladder2405.S'), '-o', str(p / 'ladder.elf')],
                check=True, capture_output=True)
            elf = (p / 'ladder.elf').read_bytes()
            shoff, = struct.unpack_from('<I', elf, 32)
            size, count, names_index = struct.unpack_from('<HHH', elf, 46)
            sections = [struct.unpack_from('<10I', elf, shoff + i * size) for i in range(count)]
            names_section = sections[names_index]
            names = elf[names_section[4]:names_section[4] + names_section[5]]
            actual = {names[s[0]:].split(b'\0', 1)[0].decode(): elf[s[4]:s[4] + s[5]]
                      for s in sections}
        want = bytes.fromhex(self.builder.COLD_BOOT_2405[1])
        self.assertEqual(actual['.text.ladder'], want)
        self.assertEqual(len(want), 120)
        self.assertEqual(len(want), len(bytes.fromhex(self.builder.COLD_BOOT_2405[0])))
        self.assertEqual(sections[1][3], 0x0100E000)
        # The accesses are 2404's, byte for byte.
        self.assertEqual(want[0x24:0x28], bytes.fromhex('56f80800'))
        self.assertEqual(want[0x36:0x3a], bytes.fromhex('57f80800'))
        self.assertEqual(want[0x50:0x54], bytes.fromhex('c2f80002'))
        self.assertEqual(want[0x60:0x64], bytes.fromhex('d2f80002'))
        # Every marker store is followed by a DSB: 0x1e, 0x30, 0x42, 0x5a, 0x6c.
        dsb = bytes.fromhex('bff34f8f')
        self.assertEqual(want.count(dsb), 9)
        for store in (0x1e, 0x30, 0x42, 0x5a, 0x6c):
            self.assertEqual(want[store + 2:store + 6], dsb, hex(store))
        # The result store is barriered before the next marker is written.
        self.assertEqual(want[0x28:0x2a], bytes.fromhex('d060'))
        self.assertEqual(want[0x2a:0x2e], dsb)
        self.assertEqual(want[0x72:0x74], bytes.fromhex('fee7'))
        self.assertEqual(want[0x74:], bytes.fromhex('00bf00bf'))

    def test_mirror_definitions_follow_the_spec_not_a_build_id(self):
        """2405 shipped the mirror at 0x03000000 while its ladder read 0x0604E400."""
        leaves_2404 = '{0x0100e000u,0x0604e000u,0x01001000u,0x02000000u}'
        for build in (0x2404, 0x2405, 0x2406):
            self.assertEqual(self.builder.chip_definitions(build, True),
                             ('0x06040000u', leaves_2404), hex(build))
        self.assertEqual(self.builder.chip_definitions(0x2401, True),
                         ('0x03000000u',
                          '{0x03000000u,0x03001000u,0x05001000u,0x01001000u}'))
        self.assertEqual(self.builder.chip_definitions(0x2403, False),
                         ('0', '{0x0100e000u,0x0300e000u,0x01001000u,0x02000000u}'))
        self.assertEqual(self.builder.chip_definitions(0x2402, False),
                         ('0', '{0x01000000u,0x01001000u,0x0100e000u,0x0100f000u}'))
        # The shim and the page-table plan may not disagree about the mirror.
        with self.assertRaises(ValueError):
            self.builder.chip_definitions(0x2406, False)

    def test_manifest_records_the_effective_mirror_and_leaves(self):
        """The manifest used to claim 0x03000000 for every --mirror-code build."""
        self.assertEqual(self.builder.chip_spec(0x2406, True),
                         (0x06040000, (0x0100E000, 0x0604E000, 0x01001000, 0x02000000)))
        self.assertEqual(self.builder.chip_spec(0x2404, True)[0], 0x06040000)
        self.assertEqual(self.builder.chip_spec(0x2401, True),
                         (0x03000000, (0x03000000, 0x03001000, 0x05001000, 0x01001000)))
        self.assertEqual(self.builder.chip_spec(0x2402, False)[0], 0)

    @unittest.skipUnless(FIRMWARE.exists(), 'requires pinned local firmware')
    def test_2405_keeps_2404s_mapping_and_moves_only_the_entry(self):
        embedded_2404, patch_2404 = self.builder.fault_vector_probe(FIRMWARE, SHA, 0x2404)
        embedded_2405, patch_2405 = self.builder.fault_vector_probe(FIRMWARE, SHA, 0x2405)
        config, code = 0x0380, 0x0e94
        # Same layout inputs, so every table offset and PA must agree: only the
        # entry program (88 -> 120 bytes) and the vector word may differ.
        self.assertEqual(patch_2405['mirror_code']['arena_offset'],
                         patch_2404['mirror_code']['arena_offset'])
        self.assertEqual(patch_2405['mirror_code']['entry_offset'],
                         patch_2404['mirror_code']['entry_offset'])
        allowed = set(range(config + 4, config + 8))
        allowed |= set(range(code + 0xE000, code + 0xE000 + 120))
        changed = {i for i, (a, b) in enumerate(zip(embedded_2404, embedded_2405)) if a != b}
        self.assertTrue(changed)
        self.assertLessEqual(changed, allowed)
        self.assertEqual(int.from_bytes(embedded_2405[config + 4:config + 8], 'little'),
                         0x0100E001)

    @unittest.skipUnless(FIRMWARE.exists(), 'requires pinned local firmware')
    def test_2404_mirrors_at_0x06040000_and_leaves_the_rest_alone(self):
        embedded_2403, _ = self.builder.fault_vector_probe(FIRMWARE, SHA, 0x2403)
        embedded_2404, patch = self.builder.fault_vector_probe(FIRMWARE, SHA, 0x2404)
        config, code = 0x0380, 0x0e94
        stub = bytes.fromhex(self.builder.COLD_BOOT_2404[1])
        # Only the vector word and the entry program move: the fault entry and the
        # 0x01000200 patch are 2403's, and 2404's ladder is longer than 2403's.
        allowed = set(range(config + 4, config + 8))
        allowed |= set(range(code + 0xE000, code + 0xE000 + 88))
        changed = {i for i, (a, b) in enumerate(zip(embedded_2403, embedded_2404))
                   if a != b}
        self.assertTrue(changed)
        self.assertLessEqual(changed, allowed)
        self.assertEqual(int.from_bytes(embedded_2404[config + 4:config + 8], 'little'),
                         0x0100E001)
        mirror = patch['mirror_code']
        self.assertEqual(mirror['va'], '0x6040000')
        self.assertTrue(mirror['fresh_l3_page'])
        cold = patch['cold_boot']
        self.assertEqual(cold['target'], '0x100e000')
        self.assertEqual(cold['mirror_va'], '0x6040000')
        self.assertEqual(cold['mirror_l3_index'], '0x4e')
        self.assertEqual(cold['mirror_l3_offset'], '0x270')
        self.assertEqual(cold['store']['value'], '0x5a5a5a5a')
        self.assertEqual(patch['leaf_probe']['va'],
                         ['0x100e000', '0x604e000', '0x1001000', '0x2000000'])

    def test_ladder_2403_assembly_matches_the_pinned_bytes(self):
        """2403's four-read ladder with the alias and the value sample."""
        bins = sorted((Path.home() / 'Library/Android/sdk/ndk').glob(
            '*/toolchains/llvm/prebuilt/darwin-x86_64/bin'))
        if not bins:
            self.skipTest('requires ARM linker from Android NDK')
        with tempfile.TemporaryDirectory() as directory:
            p = Path(directory)
            (p / 'ladder.ld').write_text('SECTIONS { '
                '.text.ladder 0x0100E000 : { *(.text.ladder) } }')
            subprocess.run([str(bins[-1] / 'clang'), '--target=armv7m-none-eabi',
                '-mcpu=cortex-m7', '-mthumb', '-nostdlib', '-Wl,--build-id=none',
                '-Wl,-e,csf_ladder_2403', '-Wl,-T,' + str(p / 'ladder.ld'),
                str(ROOT / 'tools/matisse-csf-ladder2403.S'), '-o', str(p / 'ladder.elf')],
                check=True, capture_output=True)
            elf = (p / 'ladder.elf').read_bytes()
            shoff, = struct.unpack_from('<I', elf, 32)
            size, count, names_index = struct.unpack_from('<HHH', elf, 46)
            sections = [struct.unpack_from('<10I', elf, shoff + i * size) for i in range(count)]
            names_section = sections[names_index]
            names = elf[names_section[4]:names_section[4] + names_section[5]]
            actual = {names[s[0]:].split(b'\0', 1)[0].decode(): elf[s[4]:s[4] + s[5]]
                      for s in sections}
        want = bytes.fromhex(self.builder.COLD_BOOT_2403[1])
        self.assertEqual(actual['.text.ladder'], want)
        self.assertEqual(len(want), 68)
        self.assertEqual(len(want), len(bytes.fromhex(self.builder.COLD_BOOT_2403[0])))
        self.assertEqual(sections[1][3], 0x0100E000)
        # read 1 is 0x0100E400 through r9, and its word goes to shared+12.
        self.assertEqual(want[0x1e:0x22], bytes.fromhex('56f80900'))
        self.assertEqual(want[0x22:0x24], bytes.fromhex('e060'))
        # read 2 goes through r7 = 0x03000000, read 4 through r6 = 0x01000000,
        # both with r8 = 0xE200: the same offset, the same leaf, a different VA.
        self.assertEqual(want[0x28:0x2c], bytes.fromhex('57f80800'))
        self.assertEqual(want[0x38:0x3c], bytes.fromhex('56f80800'))
        # read 3 is the uncached page window 0x01001200 through r3.
        self.assertEqual(want[0x30:0x34], bytes.fromhex('56f80300'))
        self.assertEqual(want[-4:-2], bytes.fromhex('fee7'))
        self.assertEqual(want[-2:], bytes.fromhex('00bf'))

    @unittest.skipUnless(FIRMWARE.exists(), 'requires pinned local firmware')
    def test_2403_aliases_the_code_l3_without_moving_the_page(self):
        embedded_2402, _ = self.builder.fault_vector_probe(FIRMWARE, SHA, 0x2402)
        embedded_2403, patch = self.builder.fault_vector_probe(FIRMWARE, SHA, 0x2403)
        config, code = 0x0380, 0x0e94
        stub = bytes.fromhex(self.builder.COLD_BOOT_2403[1])
        # Only the entry program moves: the vector word, the fault entry and the
        # 0x01000200 patch are 2402's. 2402's ladder was 72 bytes and this one
        # is 68, so the tail of that window differs too.
        allowed = set(range(code + 0xE000, code + 0xE000 + 72))
        changed = {i for i, (a, b) in enumerate(zip(embedded_2402, embedded_2403))
                   if a != b}
        self.assertTrue(changed)
        self.assertLessEqual(changed, allowed)
        self.assertEqual(int.from_bytes(embedded_2403[config + 4:config + 8], 'little'),
                         0x0100E001)
        alias = patch['alias_check']
        self.assertEqual(alias['va'], '0x3000000')
        self.assertTrue(alias['same_leaf'])
        self.assertTrue(alias['same_pa'])
        self.assertEqual(alias['code_leaf_attributes'], '0x4c3')
        self.assertEqual(alias['uncached_leaf_attributes'], '0x4d7')
        cold = patch['cold_boot']
        self.assertEqual(cold['target'], '0x100e000')
        self.assertEqual([step['read_va'] for step in cold['ladder']],
                         ['0x0100E400', '0x0300E200', '0x01001200', '0x0100E200', None])
        self.assertEqual(cold['sampled_word']['expected'], 0x0f10f857)
        self.assertEqual(patch['leaf_probe']['va'],
                         ['0x100e000', '0x300e000', '0x1001000', '0x2000000'])

    @unittest.skipUnless(FIRMWARE.exists(), 'requires pinned local firmware')
    def test_2402_moves_only_the_vector_and_the_ladder(self):
        embedded_2400, _ = self.builder.fault_vector_probe(FIRMWARE, SHA, 0x2400)
        embedded_2402, patch = self.builder.fault_vector_probe(FIRMWARE, SHA, 0x2402)
        config, code = 0x0380, 0x0e94
        stub = bytes.fromhex(self.builder.COLD_BOOT_2402[1])
        allowed = set(range(config + 4, config + 8))
        allowed |= set(range(code + 0xE000, code + 0xE000 + len(stub)))
        allowed |= set(range(code + 0x19b0, code + 0x19b0 + 40))
        changed = {i for i, (a, b) in enumerate(zip(embedded_2400, embedded_2402))
                   if a != b}
        self.assertTrue(changed)
        self.assertLessEqual(changed, allowed)
        self.assertEqual(embedded_2402[code + 0xE000:code + 0xE000 + len(stub)], stub)
        self.assertEqual(int.from_bytes(embedded_2402[config + 4:config + 8], 'little'),
                         0x0100E001)
        cold = patch['cold_boot']
        self.assertEqual(cold['target'], '0x100e000')
        self.assertEqual(cold['marker_value'], '0x1..0x7')
        self.assertEqual(cold['fault_marker'], 0xE3)
        self.assertEqual([(step['read_va'], step.get('bit9')) for step in cold['ladder']],
                         [('0x04000000', 0), ('0x02000000', 0), ('0x0100E400', 0),
                          ('0x0100E200', 1), ('0x02000200', 1), ('0x04000200', 1),
                          (None, None)])
        # Every bit-9 = 1 read must come after every bit-9 = 0 read: the first
        # stall ends the run, so an early bit-9 = 1 read would hide the controls.
        bits = [step['bit9'] for step in cold['ladder'] if step['read_va']]
        self.assertEqual(bits, [0, 0, 0, 1, 1, 1])
        # No mirror and no shared-L3 window: this build is 2400's layout.
        self.assertNotIn('mirror_va', cold)
        self.assertNotIn('share_code_l3', cold)
        self.assertEqual(patch['leaf_probe']['va'],
                         ['0x1000000', '0x1001000', '0x100e000', '0x100f000'])

    def test_ladder_2401_assembly_matches_the_pinned_bytes(self):
        """2401's seven-step ladder is the linked bytes, not objdump's display."""
        bins = sorted((Path.home() / 'Library/Android/sdk/ndk').glob(
            '*/toolchains/llvm/prebuilt/darwin-x86_64/bin'))
        if not bins:
            self.skipTest('requires ARM linker from Android NDK')
        with tempfile.TemporaryDirectory() as directory:
            p = Path(directory)
            (p / 'ladder.ld').write_text('SECTIONS { '
                '.text.ladder 0x0300E000 : { *(.text.ladder) } }')
            subprocess.run([str(bins[-1] / 'clang'), '--target=armv7m-none-eabi',
                '-mcpu=cortex-m7', '-mthumb', '-nostdlib', '-Wl,--build-id=none',
                '-Wl,-e,csf_ladder_2401', '-Wl,-T,' + str(p / 'ladder.ld'),
                str(ROOT / 'tools/matisse-csf-ladder2401.S'), '-o', str(p / 'ladder.elf')],
                check=True, capture_output=True)
            elf = (p / 'ladder.elf').read_bytes()
            shoff, = struct.unpack_from('<I', elf, 32)
            size, count, names_index = struct.unpack_from('<HHH', elf, 46)
            sections = [struct.unpack_from('<10I', elf, shoff + i * size) for i in range(count)]
            names_section = sections[names_index]
            names = elf[names_section[4]:names_section[4] + names_section[5]]
            actual = {names[s[0]:].split(b'\0', 1)[0].decode(): elf[s[4]:s[4] + s[5]]
                      for s in sections}
        want = bytes.fromhex(self.builder.COLD_BOOT_2401[1])
        self.assertEqual(actual['.text.ladder'], want)
        self.assertEqual(len(want), 84)
        self.assertEqual(len(want), len(bytes.fromhex(self.builder.COLD_BOOT_2401[0])))
        self.assertEqual(sections[1][3], 0x0300E000)
        # The two control reads must be the real ldr.w bytes (d4 f8 ...), not
        # the halfword-swapped form that made 2396..2400 execute a branch.
        self.assertEqual(want[0x22:0x26], bytes.fromhex('d4f80002'))
        self.assertEqual(want[0x2a:0x2e], bytes.fromhex('d5f80002'))
        # Read 3 is the same page the program is fetched from: register offset
        # r8 = 0xE200, not the 0x1200 window the other reads use.
        self.assertEqual(want[0x32:0x36], bytes.fromhex('57f80800'))

    @unittest.skipUnless(FIRMWARE.exists(), 'requires pinned local firmware')
    def test_2401_moves_only_the_vector_and_the_mirror_program(self):
        embedded_2400, _ = self.builder.fault_vector_probe(FIRMWARE, SHA, 0x2400)
        embedded_2401, patch = self.builder.fault_vector_probe(FIRMWARE, SHA, 0x2401)
        config, code = 0x0380, 0x0e94
        stub = bytes.fromhex(self.builder.COLD_BOOT_2401[1])
        allowed = set(range(config + 4, config + 8))
        allowed |= set(range(code + 0xE000, code + 0xE000 + len(stub)))
        # 2401 is the first build whose fault entry puts 0xE3 in input_va.
        allowed |= set(range(code + 0x19b0, code + 0x19b0 + 40))
        changed = {i for i, (a, b) in enumerate(zip(embedded_2400, embedded_2401))
                   if a != b}
        self.assertTrue(changed)
        self.assertLessEqual(changed, allowed)
        self.assertEqual(embedded_2401[code + 0x19b0:code + 0x19b0 + 40],
                         bytes.fromhex(self.builder.FAULT_ENTRY_2401[1]))
        self.assertEqual(int.from_bytes(embedded_2401[config + 4:config + 8], 'little'),
                         0x0300E001)
        self.assertEqual(embedded_2401[code + 0xE000:code + 0xE000 + len(stub)], stub)
        cold = patch['cold_boot']
        self.assertEqual(cold['target'], '0x300e000')
        self.assertEqual(cold['mirror_va'], '0x3000000')
        self.assertEqual(cold['share_code_l3'], '0x5000000')
        self.assertTrue(cold['fresh_l3_page'])
        self.assertEqual([step['read_va'] for step in cold['ladder']],
                         ['0x04000200', '0x02000200', '0x0300E200', '0x03001200',
                          '0x05001200', '0x01001200', None])
        self.assertEqual(cold['fault_marker'], 0xE3)
        self.assertEqual(cold['marker_value'], '0x1..0x7')
        mirror = patch['mirror_code']
        self.assertTrue(mirror['fresh_l3_page'])
        self.assertEqual(mirror['va'], '0x3000000')
        self.assertEqual(mirror['share_va'], '0x5000000')
        # Attribute bits only: vendor AltIdx 0, RO, no nG, no SH, group 6. The
        # physical field is resolved in build() against the linked arena.
        self.assertEqual(mirror['shared_leaf_attributes'], '0x30000000000004c3')
        self.assertNotIn('shared_leaf', mirror)
        # The mirror copy sits one whole 64 KiB section below the relocated code,
        # so 0x0300E000 and 0x0100E000 are 0x10000 apart in physical addresses.
        self.assertEqual(mirror['original_entry_offset'] - mirror['entry_offset'], 0x10000)
        # 2399/2401 shipped a manifest whose mirror PAs were 0x1000 below the
        # image because mirror_check() added its stand-in base. Nothing here may
        # be an absolute address: build() resolves these against the arena symbol
        # it just pinned.
        self.assertEqual(mirror['entry_offset'], mirror['arena_offset'] + 0xE000)
        self.assertNotIn('entry_pa', mirror)
        self.assertNotIn('shared_pa', mirror)
        self.assertNotIn('original_entry_pa', mirror)
        source = (ROOT / 'tools/matisse-shim-gpu-image.py').read_text()
        self.assertIn('base = 0x40000000 + arena', source)
        self.assertIn("mirror_md[pa_key] = '%#x' % (base + mirror_md[off_key])", source)
        self.assertEqual(patch['leaf_probe']['va'],
                         ['0x3000000', '0x3001000', '0x5001000', '0x1001000'])

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
        self.assertIn(0x2393, self.builder.LEAF_PROBE_BUILDS)
        self.assertIn(0x2394, self.builder.LEAF_PROBE_BUILDS)
        self.assertIn(0x2397, self.builder.LEAF_PROBE_BUILDS)
        self.assertIn(0x2398, self.builder.LEAF_PROBE_BUILDS)
        self.assertIn(0x2388, self.builder.LEAF_PROBE_BUILDS)
        source = (ROOT / 'tools/matisse-shim-gpu-image.py').read_text()
        self.assertIn('a.build_id in LEAF_PROBE_BUILDS,', source)
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
    def test_2393_repeats_the_512_target_with_vendor_page_attributes(self):
        original = FIRMWARE.read_bytes()
        embedded_2391, _ = self.builder.fault_vector_probe(FIRMWARE, SHA, 0x2391)
        embedded_2393, patch = self.builder.fault_vector_probe(FIRMWARE, SHA, 0x2393)
        config, code = 0x0380, 0x0e94
        allowed = set(range(config + 4, config + 8))
        allowed |= set(range(code + 0x1A00, code + 0x1A00 + 20))
        allowed |= set(range(code + 0xEA00, code + 0xEA00 + 20))
        changed = {i for i, (a, b) in enumerate(zip(embedded_2391, embedded_2393)) if a != b}
        self.assertTrue(changed)
        self.assertLessEqual(changed, allowed)
        self.assertEqual(int.from_bytes(embedded_2393[config + 4:config + 8], 'little'),
                         0x0100EA01)
        # 2391's program at 0x1A00 goes back to vendor bytes; 0xEA00 takes it
        self.assertEqual(embedded_2393[code + 0x1A00:code + 0x1A00 + 20],
                         original[code + 0x1A00:code + 0x1A00 + 20])
        self.assertEqual(embedded_2393[code + 0xEA00:code + 0xEA00 + 20],
                         bytes.fromhex(self.builder.COLD_BOOT_2393[1]))
        for landing, program in ((0x18ec, self.builder.COLD_BOOT_2390_ENTRY),
                                 (0x1000, self.builder.COLD_BOOT_2390_PAGE)):
            self.assertEqual(embedded_2393[code + landing:code + landing + 20],
                             bytes.fromhex(program[1]), hex(landing))
        self.assertEqual([item['target'] for item in patch['cold_boot']['landings']],
                         ['0x100ea00', '0x1001000', '0x10018ec'])
        self.assertEqual(patch['cold_boot']['target'], '0x100ea00')
        self.assertNotIn('reset_vector_unchanged', patch['cold_boot'])
        self.assertEqual(patch['leaf_probe']['marks'], '420..423')

    @unittest.skipUnless(FIRMWARE.exists(), 'requires pinned local firmware')
    def test_2396_ladder_reads_bit_nine_in_three_sections(self):
        embedded_2394, _ = self.builder.fault_vector_probe(FIRMWARE, SHA, 0x2394)
        embedded_2396, patch = self.builder.fault_vector_probe(FIRMWARE, SHA, 0x2396)
        config, code = 0x0380, 0x0e94
        stub = bytes.fromhex(self.builder.COLD_BOOT_2396[1])
        self.assertEqual(len(stub), 48)
        # Same vector, same fault entry, same 0x200 stub: only the program at
        # 0xE000 grows from twenty bytes to the ladder.
        changed = {i for i, (a, b) in enumerate(zip(embedded_2394, embedded_2396)) if a != b}
        self.assertTrue(changed)
        self.assertLessEqual(changed, set(range(code + 0xE000, code + 0xE000 + 48)))
        self.assertEqual(int.from_bytes(embedded_2396[config + 4:config + 8], 'little'),
                         0x0100E001)
        self.assertEqual(embedded_2396[code + 0xE000:code + 0xE000 + 48], stub)
        # Marker N is written before read N, and the reads sit in three sections.
        self.assertIn(0x04000200, (0x04000200,))
        read_vas = [step['read_va'] for step in patch['cold_boot']['ladder']]
        self.assertEqual(read_vas, ['0x04000200', '0x02000200', '0x01001200', None])
        self.assertEqual([step['marker'] for step in patch['cold_boot']['ladder']],
                         ['0x1', '0x2', '0x3', '0x4'])
        for va in (0x04000200, 0x02000200, 0x01001200):
            self.assertEqual((va >> 9) & 1, 1, hex(va))
        self.assertEqual(patch['cold_boot']['target'], '0x100e000')

    @unittest.skipUnless(FIRMWARE.exists(), 'requires pinned local firmware')
    def test_2397_keeps_2396_container_and_moves_one_page_permission(self):
        embedded_2396, patch_2396 = self.builder.fault_vector_probe(FIRMWARE, SHA, 0x2396)
        embedded_2397, patch_2397 = self.builder.fault_vector_probe(FIRMWARE, SHA, 0x2397)
        # The whole point of 2397: nothing in the container moves. XN lives in
        # the page tables the shim builds, not in the firmware bytes.
        self.assertEqual(embedded_2396, embedded_2397)
        self.assertEqual(patch_2397['cold_boot']['xn_page'], '0x1001000')
        self.assertEqual(patch_2397['cold_boot']['target'], '0x100e000')
        self.assertEqual([step['read_va'] for step in patch_2397['cold_boot']['ladder']],
                         ['0x04000200', '0x02000200', '0x01001200', None])
        self.assertIn('forced non-executable',
                      patch_2397['cold_boot']['ladder'][2]['section'])
        self.assertNotIn('xn_page', patch_2396['cold_boot'])
        self.assertEqual(self.builder.TRACE_PROBE[0x2397]['xn_page'], 0x01001000)

    @unittest.skipUnless(FIRMWARE.exists(), 'requires pinned local firmware')
    def test_2398_keeps_the_container_and_clears_the_group_tag(self):
        embedded_2396, _ = self.builder.fault_vector_probe(FIRMWARE, SHA, 0x2396)
        embedded_2398, patch = self.builder.fault_vector_probe(FIRMWARE, SHA, 0x2398)
        # Only a page-table bit moves: the image bytes are 2396's.
        self.assertEqual(embedded_2396, embedded_2398)
        self.assertEqual(patch['cold_boot']['leaf_group'], 0)
        self.assertEqual(patch['cold_boot']['target'], '0x100e000')
        self.assertEqual(self.builder.TRACE_PROBE[0x2398]['leaf_group'], 0)
        source = (ROOT / 'shim/csf.c').read_text()
        self.assertIn('SWEET_CSF_LEAF_GROUP', source)
        self.assertIn('(mmu>>8)&255,SWEET_CSF_LEAF_GROUP,&root', source)
        self.assertIn('.pte_group_requested=SWEET_CSF_LEAF_GROUP', source)

    @unittest.skipUnless(FIRMWARE.exists(), 'requires pinned local firmware')
    def test_2394_is_the_2385_control_under_vendor_attributes(self):
        embedded_2385, _ = self.builder.fault_vector_probe(FIRMWARE, SHA, 0x2385)
        embedded_2394, patch = self.builder.fault_vector_probe(FIRMWARE, SHA, 0x2394)
        # The probe only patches the container; the attribute change is in the
        # shim compile flags, so 2394's container must equal 2385's byte for byte.
        self.assertEqual(embedded_2394, embedded_2385)
        self.assertEqual(patch['cold_boot']['target'], '0x100e000')
        self.assertEqual(patch['leaf_probe']['marks'], '420..423')
        self.assertNotIn('landings', patch['cold_boot'])

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
                 (0x2390, 0x010018EC, 'COLD_BOOT_2390_ENTRY', True),
                 # 2393 repeats 2391's class of address (512-aligned, not a
                 # page base) with vendor page attributes; same twenty bytes.
                 (0x2393, 0x0100EA00, 'COLD_BOOT_2393', False),
                 # 2394 is 2385's positive control under the vendor encoding:
                 # same container, different shim compile flags.
                 (0x2394, 0x0100E000, 'COLD_BOOT_2385', False),
                 # 2395 keeps 2393's container byte for byte and moves only the
                 # code section's leaf attribute.
                 (0x2395, 0x0100EA00, 'COLD_BOOT_2393', False))
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
