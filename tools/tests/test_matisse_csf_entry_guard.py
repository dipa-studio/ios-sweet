"""The pre-AUTO entry walk reads the PTE backing, not the section's first word."""
import hashlib
import importlib.util
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
VENDOR = ROOT / 'research/matisse/20261031-gpu/extracted/vendor_a-mali_csffw.bin'
VENDOR_SHA256 = 'de22d2fc06bc8a859968499a6e609c27fe838be062bf5c97d92ea9f904f7229a'

HARNESS = r'''
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "mali_csf_entry_probe.h"
#include "mali_csf_entry_guard.h"
#define BASE UINT64_C(0x40077000)
static uint8_t arena[2u << 20] __attribute__((aligned(4096)));
static struct sweet_csf_memory plan;
static unsigned reads;
static void put32(uint8_t *p, uint32_t v) {
    for(unsigned i=0;i<4;i++)p[i]=(uint8_t)(v>>(8*i));
}
static void put64(uint8_t *p, uint64_t v) {
    put32(p,(uint32_t)v);put32(p+4,(uint32_t)(v>>32));
}
static uint64_t get64(const uint8_t *p) {
    uint64_t v=0;for(unsigned i=0;i<8;i++)v|=(uint64_t)p[i]<<(i*8);return v;
}
static uint32_t read32(void *ctx,uint64_t pa) {
    (void)ctx;
    assert(pa>=BASE && pa-BASE<=plan.required_bytes-4 && !(pa&3));
    reads++;
    const uint8_t *p=arena+(pa-BASE);
    return (uint32_t)p[0]|(uint32_t)p[1]<<8|(uint32_t)p[2]<<16|(uint32_t)p[3]<<24;
}
static void section(uint8_t *p,uint32_t flags,uint32_t va,uint32_t end,
                    uint32_t first,uint32_t last) {
    put32(p,24u<<8);put32(p+4,flags);put32(p+8,va);put32(p+12,end);
    put32(p+16,first);put32(p+20,last);
}
static uint8_t *synthetic(size_t *size) {
    const uint32_t vector=140,code=vector+8,shared=code+0xf848;
    *size=shared+4096;
    uint8_t *fw=calloc(1,*size);assert(fw);
    put32(fw,0xc3f13a6e);put32(fw+16,140);
    section(fw+20,9,0,0x1000,vector,code);
    section(fw+44,13,0x01000000,0x01010000,code,shared);
    section(fw+68,11,0x02000000,0x02040000,0,0);
    section(fw+92,0xc000001b,0x04000000,0x04001000,shared,*size);
    section(fw+116,11,0x10000000,0x10001000,0,0);
    put32(fw+vector,0x02040000);put32(fw+vector+4,0x010018ed);
    put32(fw+code,0xd00cf8df);
    const uint32_t prefix[]={0x4826b672,0x010bf04f,0x48256001,
                             0x0107f04f,0x48246001,0x21e0f44f};
    memcpy(fw+code+0x18ec,prefix,sizeof(prefix));
    put32(fw+code+0x1988,0x40022000);
    put32(fw+code+0x198c,0x40022004);
    put32(fw+code+0x1990,0xe000ed24);
    return fw;
}
static uint8_t *file(const char *path,size_t *size) {
    FILE *f=fopen(path,"rb");assert(f);
    assert(!fseek(f,0,SEEK_END));long n=ftell(f);assert(n>0);
    assert(!fseek(f,0,SEEK_SET));
    uint8_t *fw=malloc((size_t)n);assert(fw);
    assert(fread(fw,1,(size_t)n,f)==(size_t)n);assert(!fclose(f));
    *size=(size_t)n;return fw;
}
static uint64_t *leaf(void) {
    uint64_t table=0;
    for(unsigned shift=39;shift>=21;shift-=9) {
        uint64_t d=get64(arena+table+(((uint64_t)SWEET_CSF_RESET_ENTRY_VA>>shift)&511u)*8);
        table=(d&SWEET_CSF_ENTRY_PA_MASK)-BASE;
    }
    return (uint64_t *)(void *)(arena+table+((SWEET_CSF_RESET_ENTRY_VA>>12)&511u)*8);
}
static int check(struct sweet_csf_entry_guard_result *e) {
    return sweet_csf_entry_guard(&plan,BASE,BASE,read32,0,
        sweet_csf_inline_jump,sizeof(sweet_csf_inline_jump),e);
}
int main(int argc,char **argv) {
    size_t size=0;uint8_t *fw=argc==2?file(argv[1],&size):synthetic(&size);
    assert(!sweet_csf_memory_plan(fw,size,&plan));
    assert(plan.table_pages==8 && plan.required_bytes<=sizeof(arena));
    uint64_t root=0;
    assert(!sweet_csf_memory_build_group(fw,size,&plan,arena,sizeof(arena),BASE,40,6,&root));
    assert(root==BASE && !sweet_csf_inline_probe_install(arena,sizeof(arena),&plan));
    struct sweet_csf_entry_guard_result e={0};
    assert(check(&e)==0);
    assert(e.leaf_pte==UINT64_C(0x3000000040081cc7));
    assert(e.entry_pa==UINT64_C(0x400818ec));
    assert(e.entry_word==0x4803b672 && e.code_start_word==0xd00cf8df);
    uint32_t good=read32(0,e.entry_pa);
    put32(arena+(e.entry_pa-BASE),0xd00cf8df);
    assert(check(&e)==SWEET_CSF_ENTRY_INSTRUCTION && e.entry_word==0xd00cf8df);
    put32(arena+(e.entry_pa-BASE),good);
    uint32_t last=read32(0,e.entry_pa+20);
    put32(arena+(e.entry_pa-BASE)+20,last^1u);
    assert(check(&e)==SWEET_CSF_ENTRY_INSTRUCTION && e.entry_word==good);
    put32(arena+(e.entry_pa-BASE)+20,last);
    uint64_t *p=leaf(),saved=*p;
    *p=saved^UINT64_C(0x80);
    assert(check(&e)==SWEET_CSF_ENTRY_LEAF && e.leaf_pte==*p);
    *p=(saved&~SWEET_CSF_ENTRY_PA_MASK)|(BASE+0x8000);
    assert(check(&e)==SWEET_CSF_ENTRY_LEAF && e.leaf_pte==*p);
    *p=(saved&~SWEET_CSF_ENTRY_PA_MASK)|UINT64_C(0x50000000);
    assert(check(&e)==SWEET_CSF_ENTRY_BACKING && e.leaf_pte==*p);
    *p=saved;
    uint64_t old=get64(arena);
    put64(arena,UINT64_C(0x50000000)|3);
    assert(check(&e)==SWEET_CSF_ENTRY_TABLE && e.leaf_pte==0);
    put64(arena,old);
    unsigned before=reads;
    assert(sweet_csf_entry_guard(&plan,BASE,BASE+4096,read32,0,
        sweet_csf_inline_jump,sizeof(sweet_csf_inline_jump),&e)==SWEET_CSF_ENTRY_ARGUMENT);
    assert(reads==before && check(&e)==0);
    free(fw);
    return 0;
}
'''


@unittest.skipUnless(shutil.which('cc'), 'requires C compiler')
class EntryGuardTests(unittest.TestCase):
    def run_harness(self, firmware=None):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / 'guard.c'
            binary = Path(directory) / 'guard'
            source.write_text(HARNESS)
            subprocess.run(['cc', '-std=c11', '-Wall', '-Wextra', '-Werror',
                            '-fsanitize=address,undefined', '-I', str(ROOT / 'xnu/gpu'),
                            str(source), str(ROOT / 'xnu/gpu/mali_csf_memory.c'),
                            str(ROOT / 'xnu/gpu/mali_csf_firmware.c'), '-o', str(binary)],
                           check=True, capture_output=True)
            result = subprocess.run([str(binary), *([str(firmware)] if firmware else [])],
                                    capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr.decode())

    def test_synthetic_walk_and_fail_closed_cases(self):
        self.run_harness()

    @unittest.skipUnless(VENDOR.exists(), 'requires ignored vendor firmware')
    def test_pinned_vendor_firmware(self):
        self.assertEqual(hashlib.sha256(VENDOR.read_bytes()).hexdigest(), VENDOR_SHA256)
        self.run_harness(VENDOR)

    @unittest.skipUnless(VENDOR.exists(), 'requires ignored vendor firmware')
    def test_builder_requires_guard_for_distinct_2337_identity(self):
        sys.path.insert(0, str(ROOT / 'tools'))
        spec = importlib.util.spec_from_file_location('gpu_image', ROOT / 'tools/matisse-shim-gpu-image.py')
        builder = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(builder)
        with self.assertRaisesRegex(ValueError, 'requires the entry PTE guard'):
            builder.diagnostic_firmware(VENDOR, VENDOR_SHA256, 0x2337, False, True, True, False)
        with self.assertRaisesRegex(ValueError, 'forbid'):
            builder.diagnostic_firmware(VENDOR, VENDOR_SHA256, 0x2336, False, True, True, True)
        firmware, patch = builder.diagnostic_firmware(VENDOR, VENDOR_SHA256,
                                                      0x2337, False, True, True, True)
        self.assertIsNone(patch)
        self.assertEqual(hashlib.sha256(firmware).hexdigest(), VENDOR_SHA256)


if __name__ == '__main__':
    unittest.main()
