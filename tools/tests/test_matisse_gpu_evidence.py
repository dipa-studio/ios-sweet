"""Compile the exact bounds predicate delivered in the kernel patch."""
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
PATCH = ROOT / 'xnu/patches/0119-matisse-gpu-persistent-evidence.patch'

class DiagnosticBoundsTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which('cc'), 'requires C compiler')
    def test_real_patch_bounds_with_sanitizers(self):
        patch = PATCH.read_text()
        added = '\n'.join(line[1:] for line in patch.splitlines()
                          if line.startswith('+') and not line.startswith('+++'))
        begin = added.index('static bool\nsweet_ufs_write_allowed(')
        end = added.index('\nstatic int\nufs_write_blocks_checked', begin)
        predicate = added[begin:end]
        source = '#include <stdint.h>\n#include <stdbool.h>\n#include <assert.h>\n' + predicate + r'''
int main(void) {
    /* first=100, blocks=5000 => diagnostic tail begins at4075. */
    assert(sweet_ufs_write_allowed(false,true,100,5000,4075,1,256));
    assert(sweet_ufs_write_allowed(false,true,100,5000,5099,1,256));
    assert(!sweet_ufs_write_allowed(false,true,100,5000,4074,1,256));
    assert(!sweet_ufs_write_allowed(false,false,100,5000,4075,1,256));
    assert(sweet_ufs_write_allowed(true,false,100,5000,100,256,256));
    assert(!sweet_ufs_write_allowed(false,true,100,2049,2148,1,256));
    assert(!sweet_ufs_write_allowed(false,true,100,5000,5099,2,256));
    assert(!sweet_ufs_write_allowed(true,false,100,5000,99,1,256));
    assert(!sweet_ufs_write_allowed(true,false,100,5000,5100,1,256));
    assert(!sweet_ufs_write_allowed(true,false,100,5000,100,0,256));
    assert(!sweet_ufs_write_allowed(true,false,100,5000,100,257,256));
    assert(!sweet_ufs_write_allowed(true,false,0,UINT64_MAX,UINT64_MAX-1,4,256));
    assert(!sweet_ufs_write_allowed(true,false,0,UINT64_MAX,UINT32_MAX,2,256));
    assert(sweet_ufs_write_allowed(true,false,0,UINT64_MAX,UINT32_MAX,1,256));
    assert(!sweet_ufs_write_allowed(true,false,UINT64_MAX,1,0,1,256));
    return 0;
}
'''
        with tempfile.TemporaryDirectory() as directory:
            p = Path(directory)
            (p/'bounds.c').write_text(source)
            subprocess.run(['cc','-std=c11','-Wall','-Wextra','-Werror',
                            '-fsanitize=address,undefined',str(p/'bounds.c'),
                            '-o',str(p/'bounds')],check=True,capture_output=True)
            subprocess.run([str(p/'bounds')],check=True,capture_output=True)
        self.assertIn('ufs_write_blocks_checked(base + 1 + blk, n, true)', patch)
        self.assertIn('ufs_write_blocks_checked(base, 1, true)', patch)
        self.assertIn('ufs_write_blocks_checked(lba, count, false)', patch)


class ReportDecodeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import importlib.util
        spec=importlib.util.spec_from_file_location('gpu_report',ROOT/'tools/matisse-gpu-report.py')
        cls.module=importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.module)

    def marks(self, error=0, omit=None, build=0x2321, reset=0x100, init=0, spm=6):
        import struct
        raw=struct.pack('<I4i8I4xQ2I',10,error,init,1,0,2,spm,2,0x55667788,
                        0xa0020001,0,reset,0xff,0x250000000,0,1)
        records=[(99,0,build,0)]
        records += [(300+i,0,struct.unpack_from('<Q',raw,i*8)[0],build)
                    for i in range(9) if i!=omit]
        block=bytearray(4096)
        struct.pack_into('<8sII',block,0,b'SWEETMRK',1,len(records))
        for i,record in enumerate(records):
            struct.pack_into('<IIQQ',block,16+i*24,*record)
        return block

    def test_complete_verified_report(self):
        result=self.module.decode(self.marks())
        self.assertTrue(result['power_reset_verified'])
        self.assertFalse(result['csf_firmware_boot_verified'])
        self.assertEqual(result['firmware_memory'],0x250000000)

    def test_failure_is_not_success(self):
        self.assertFalse(self.module.decode(self.marks(error=-23))['power_reset_verified'])
        self.assertFalse(self.module.decode(self.marks(reset=0))['power_reset_verified'])
        self.assertFalse(self.module.decode(self.marks(init=-1))['power_reset_verified'])
        self.assertFalse(self.module.decode(self.marks(spm=2))['power_reset_verified'])

    def test_stale_partial_wrong_build_and_duplicate_rejected(self):
        import struct
        for data in [bytes(4096),self.marks(omit=4),self.marks(build=0x2316),bytes(40)]:
            with self.assertRaises(ValueError):self.module.decode(data)
        data=self.marks()
        count=struct.unpack_from('<I',data,12)[0]
        struct.pack_into('<I',data,12,count+1)
        struct.pack_into('<IIQQ',data,16+24*count,300,0,0,0x2321)
        with self.assertRaises(ValueError):self.module.decode(data)

if __name__ == '__main__':
    unittest.main()
