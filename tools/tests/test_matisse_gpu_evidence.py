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

if __name__ == '__main__':
    unittest.main()
