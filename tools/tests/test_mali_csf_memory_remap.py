"""2409: repointing a leaf outside the arena changes PA and PBHA, nothing else."""
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
HARNESS = r'''
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "mali_csf_memory.h"
static void put(uint8_t *p, uint32_t v) { for (unsigned i = 0; i < 4; i++) p[i] = (uint8_t)(v >> (8*i)); }
static uint64_t u64(const uint8_t *p) { uint64_t v = 0; for (unsigned i = 0; i < 8; i++) v |= (uint64_t)p[i] << (8*i); return v; }
static void section(uint8_t *p, uint32_t flags, uint32_t va, uint32_t end, uint32_t start, uint32_t stop) {
    put(p, 24 << 8); put(p+4, flags); put(p+8, va); put(p+12, end); put(p+16, start); put(p+20, stop);
}
static void fixture(uint8_t *b) {
    memset(b, 0, 256); put(b, 0xc3f13a6e); b[4] = 1; put(b+16, 92);
    section(b+20, 0xd, 0, 4096, 128, 132);
    section(b+44, 0x4000001b, 0x4000000, 0x4002000, 132, 136);
    section(b+68, 0x2b, 0x3000000, 0x3001000, 0, 0);
    b[128] = 0x10; b[129] = 0x20; b[130] = 0x30; b[131] = 0x40;
    b[132] = 1; b[133] = 2; b[134] = 3; b[135] = 4;
}
static const uint64_t PAGE = 0x0000fffffffff000ULL;
static uint64_t leaf_pa(const uint8_t *a, uint64_t root, uint32_t va) {
    const uint8_t *t = a;
    for (unsigned l = 0; l < 3; l++) {
        unsigned shift = 39 - 9*l;
        uint64_t d = u64(t + ((((uint64_t)va) >> shift) & 511)*8);
        assert((d & 3) == 3);
        t = a + ((d & PAGE) - root);
    }
    return u64(t + (((uint64_t)va >> 12) & 511)*8);
}
int main(void) {
    uint8_t b[256]; fixture(b);
    struct sweet_csf_memory m; assert(!sweet_csf_memory_plan(b, sizeof b, &m));
    size_t bytes = m.required_bytes;
    uint8_t *base = aligned_alloc(4096, bytes), *remapped = aligned_alloc(4096, bytes);
    assert(base && remapped);
    uint64_t rb = 0, rr = 0;
    assert(!sweet_csf_memory_build_group(b, sizeof b, &m, base, bytes, 0x40000000, 40, 6, &rb));
    struct sweet_csf_remap r[2] = { {0x0, 0x9c16f000, 0}, {0x4000000, 0x9c16e000, 6} };
    assert(!sweet_csf_memory_build_group(b, sizeof b, &m, remapped, bytes, 0x40000000, 40, 6, &rr));
    assert(!sweet_csf_memory_remap_leaves(remapped, bytes, 0x40000000, 40, r, 2));
    assert(rb == rr);
    const uint64_t KEEP = ~(PAGE | (UINT64_C(15) << 59));
    uint64_t a = leaf_pa(base, rb, 0x0), c = leaf_pa(remapped, rr, 0x0);
    /* PA replaced, PBHA set to the caller's tag, every other bit identical. */
    assert((c & PAGE) == 0x9c16f000 && ((c >> 59) & 15) == 0);
    assert((a & KEEP) == (c & KEEP) && (a & PAGE) != (c & PAGE));
    uint64_t d = leaf_pa(remapped, rr, 0x4000000), e = leaf_pa(base, rb, 0x4000000);
    assert((d & PAGE) == 0x9c16e000 && ((d >> 59) & 15) == 6);
    assert((e & KEEP) == (d & KEEP));
    /* untouched pages keep their original leaves byte for byte */
    assert(leaf_pa(remapped, rr, 0x4001000) == leaf_pa(base, rb, 0x4001000));
    assert(leaf_pa(remapped, rr, 0x1000) == leaf_pa(base, rb, 0x1000));
    /* fail closed on every ambiguous request */
    struct sweet_csf_remap bad[1];
    bad[0] = (struct sweet_csf_remap){0x81, 0x9c000000, 0};       /* unaligned VA */
    assert(sweet_csf_memory_remap_leaves(remapped, bytes, 0x40000000, 40, bad, 1) == SWEET_CSF_MEMORY_ARGUMENT);
    bad[0] = (struct sweet_csf_remap){0x80, 0x9c000001, 0};       /* unaligned PA */
    assert(sweet_csf_memory_remap_leaves(remapped, bytes, 0x40000000, 40, bad, 1) == SWEET_CSF_MEMORY_ARGUMENT);
    bad[0] = (struct sweet_csf_remap){0x80, 0x40000000, 0};       /* inside the arena */
    assert(sweet_csf_memory_remap_leaves(remapped, bytes, 0x40000000, 40, bad, 1) == SWEET_CSF_MEMORY_ARGUMENT);
    bad[0] = (struct sweet_csf_remap){0x80, 0x9c000000, 16};      /* tag out of range */
    assert(sweet_csf_memory_remap_leaves(remapped, bytes, 0x40000000, 40, bad, 1) == SWEET_CSF_MEMORY_ARGUMENT);
    bad[0] = (struct sweet_csf_remap){0x2000000, 0x9c000000, 0};  /* no such leaf */
    assert(sweet_csf_memory_remap_leaves(remapped, bytes, 0x40000000, 40, bad, 1) == SWEET_CSF_MEMORY_ARGUMENT);
    free(base); free(remapped);
    puts("PASS: 2409 leaf remap, nine checks"); return 0;
}
'''
@unittest.skipUnless(shutil.which('cc'), 'requires C compiler')
class RemapTests(unittest.TestCase):
    def _run(self, source, defines):
        with tempfile.TemporaryDirectory() as directory:
            p = Path(directory); (p/'t.c').write_text(source)
            cmd = ['cc', '-std=c11', '-Wall', '-Wextra', '-Werror',
                   '-fsanitize=address,undefined', *defines, '-I', str(ROOT/'xnu/gpu'),
                   str(p/'t.c'), str(ROOT/'xnu/gpu/mali_csf_memory.c'),
                   str(ROOT/'xnu/gpu/mali_csf_firmware.c'), '-o', str(p/'t')]
            subprocess.run(cmd, check=True, capture_output=True)
            out = subprocess.run([str(p/'t')], capture_output=True, text=True)
            self.assertEqual(out.returncode, 0, out.stdout + out.stderr)

    def test_remap_changes_pa_and_tag_only(self):
        self._run(HARNESS, ['-DSWEET_CSF_OUT_OF_ARENA=1'])

if __name__ == '__main__':
    unittest.main()
