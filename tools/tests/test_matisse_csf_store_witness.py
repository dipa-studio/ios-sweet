"""Execute the new MCU ladder, including stopped-store/read observations."""
import importlib.util
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


class StoreWitnessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        sys.path.insert(0, str(ROOT / 'tools'))
        spec = importlib.util.spec_from_file_location('witness_builder', ROOT / 'tools/matisse-shim-gpu-image.py')
        cls.builder = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.builder)

    def test_assembled_program_is_the_installed_program(self):
        bins = sorted((Path.home() / 'Library/Android/sdk/ndk').glob('*/toolchains/llvm/prebuilt/darwin-x86_64/bin'))
        if not bins:
            self.skipTest('requires NDK')
        with tempfile.TemporaryDirectory() as directory:
            p = Path(directory)
            subprocess.run([str(bins[-1] / 'clang'), '--target=armv7m-none-eabi', '-mthumb',
                            '-c', str(ROOT / 'tools/matisse-csf-ladder2420.S'), '-o', str(p / 'p.o')], check=True)
            subprocess.run([str(bins[-1] / 'llvm-objcopy'), '-O', 'binary', '--only-section=.text.ladder',
                            str(p / 'p.o'), str(p / 'p.bin')], check=True)
            self.assertEqual((p / 'p.bin').read_bytes(), self.builder.TRACE_PROBE[0x2420]['stub'])

    def test_markers_distinguish_store_from_read(self):
        if not importlib.util.find_spec('unicorn'):
            self.skipTest('requires Unicorn')
        from unicorn import Uc, UC_ARCH_ARM, UC_MODE_THUMB, UC_MODE_MCLASS, UC_HOOK_MEM_READ, UC_HOOK_MEM_WRITE
        for stop, expected in (('store', 2), ('read', 3), (None, 4)):
            with self.subTest(stop=stop):
                u = Uc(UC_ARCH_ARM, UC_MODE_THUMB | UC_MODE_MCLASS)
                u.mem_map(0x0100e000, 4096)
                u.mem_write(0x0100e000, self.builder.TRACE_PROBE[0x2420]['stub'])
                u.mem_map(0x04000000, 4096)
                u.mem_write(0x04000200, struct.pack('<I', 0x24205200))
                def hook(uc, access, address, size, value, data):
                    if address == 0x04000200:
                        uc.emu_stop()
                if stop:
                    u.hook_add(UC_HOOK_MEM_WRITE if stop == 'store' else UC_HOOK_MEM_READ, hook)
                u.emu_start(0x0100e001, 0x0100e088, count=100)
                self.assertEqual(struct.unpack('<I', u.mem_read(0x04000008, 4))[0], expected)
                self.assertEqual(struct.unpack('<I', u.mem_read(0x04000400, 4))[0], 0x2420a400)
                if stop != 'store':
                    self.assertEqual(struct.unpack('<I', u.mem_read(0x04000200, 4))[0], 0x2420a200)


if __name__ == '__main__':
    unittest.main()
