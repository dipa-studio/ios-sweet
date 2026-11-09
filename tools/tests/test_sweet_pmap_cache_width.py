"""A physical cache operation must not wrap high DRAM into peripheral space."""
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


class CacheAddressTests(unittest.TestCase):
    def test_real_page_to_byte_expression_above_four_gib(self):
        patch = (ROOT / 'xnu/patches/0211-sweet-pmap-cache-physical-width.patch').read_text()
        line, = [s[1:].strip() for s in patch.splitlines() if s.startswith('+\tflush_dcache(')]
        source = r'''
#include <assert.h>
#include <stdint.h>
typedef uint32_t ppnum_t;
typedef uint64_t vm_address_t;
#define PAGE_SHIFT 14
#define PAGE_SIZE (1u << PAGE_SHIFT)
#define TRUE 1
#define ptoa(x) ((vm_address_t)(x) << PAGE_SHIFT)
static uint64_t actual;
static void flush_dcache(uint64_t address,unsigned size,int phys) {
    assert(size==PAGE_SIZE && phys); actual=address;
}
static void sync_page(ppnum_t pp) { STATEMENT }
int main(void) {
    const uint64_t addresses[]={0x80000000ull,0xffffc000ull,0x100000000ull,
        0x104f0c000ull,0x17fffc000ull,0x23fffc000ull};
    for(unsigned i=0;i<sizeof(addresses)/sizeof(addresses[0]);i++) {
        sync_page((ppnum_t)(addresses[i]>>PAGE_SHIFT));
        assert(actual==addresses[i]);
    }
    return 0;
}
'''.replace('STATEMENT', line)
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)
            (p / 'test.c').write_text(source)
            subprocess.run(['clang', '-std=c11', '-Wall', '-Wextra', '-Werror',
                            '-fsanitize=address,undefined', str(p / 'test.c'),
                            '-o', str(p / 'test')], check=True)
            subprocess.run([str(p / 'test')], check=True)


if __name__ == '__main__':
    unittest.main()
