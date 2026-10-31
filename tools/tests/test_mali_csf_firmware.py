"""Exercise the real portable CSF parser with sanitizers and hostile containers."""
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
HARNESS = r'''
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "mali_csf_firmware.h"

static unsigned calls;
static void put(uint8_t *p, uint32_t n) {
    p[0]=n; p[1]=n>>8; p[2]=n>>16; p[3]=n>>24;
}
static int count(const struct sweet_csf_section *s, void *ctx) {
    (void)ctx; assert(s->va_end > s->va_start); calls++; return 0;
}
static int fail(const struct sweet_csf_section *s, void *ctx) {
    (void)s; (void)ctx; calls++; return 1;
}
static void section(uint8_t *p, uint32_t flags, uint32_t start, uint32_t end) {
    put(p, 24u<<8); put(p+4,flags); put(p+8,start); put(p+12,end);
    put(p+16,0); put(p+20,0);
}
static void fixture(uint8_t *b) {
    memset(b,0,128); put(b,0xc3f13a6e); b[4]=1; put(b+8,0x01010000);
    put(b+16,68); section(b+20,9,0,4096);
    section(b+44,0xc000001b,0x04000000,0x04008000);
}
static void invalid(const uint8_t *b, size_t n, int expected) {
    struct sweet_csf_layout out, sentinel;
    memset(&out,0xa5,sizeof(out)); sentinel=out; calls=0;
    assert(sweet_csf_parse(b,n,&out,count,NULL)==expected);
    assert(!memcmp(&out,&sentinel,sizeof(out))); assert(calls==0);
}
static void tests(void) {
    uint8_t b[128], original[128]; struct sweet_csf_layout out;
    fixture(b); calls=0;
    assert(!sweet_csf_parse(b,sizeof(b),&out,count,NULL));
    assert(calls==2 && out.entries==2 && out.sections==2);
    assert(out.shared_va==0x04000000 && out.shared_bytes==32768);
    assert(out.non_16k_sections==1 && out.format_minor==1);
    assert(out.format_hash==0x01010000);
    for(size_t n=0;n<20;n++)invalid(b,n,SWEET_CSF_TRUNCATED);
    invalid(b,67,SWEET_CSF_TRUNCATED);
    assert(sweet_csf_parse(NULL,128,&out,NULL,NULL)==SWEET_CSF_BAD_ARGUMENT);
    assert(sweet_csf_parse(b,128,NULL,NULL,NULL)==SWEET_CSF_BAD_ARGUMENT);
    b[0]=0;invalid(b,128,SWEET_CSF_BAD_HEADER); fixture(b);
    b[5]=1;invalid(b,128,SWEET_CSF_BAD_HEADER); fixture(b);
    b[6]=1;invalid(b,128,SWEET_CSF_BAD_HEADER); fixture(b);
    put(b+16,67);invalid(b,128,SWEET_CSF_BAD_HEADER); fixture(b);
    put(b+20,0);invalid(b,128,SWEET_CSF_BAD_ENTRY); fixture(b);
    put(b+20,23u<<8);invalid(b,128,SWEET_CSF_BAD_ENTRY); fixture(b);
    put(b+20,(24u<<8)|0x10000);invalid(b,128,SWEET_CSF_BAD_ENTRY); fixture(b);
    put(b+24,0x40);invalid(b,128,SWEET_CSF_BAD_SECTION); fixture(b);
    put(b+28,1);invalid(b,128,SWEET_CSF_BAD_SECTION); fixture(b);
    put(b+36,120);put(b+40,129);invalid(b,128,SWEET_CSF_BAD_SECTION); fixture(b);
    put(b+36,1);put(b+40,2);invalid(b,128,SWEET_CSF_BAD_SECTION); fixture(b);
    put(b+36,80);put(b+40,79);invalid(b,128,SWEET_CSF_BAD_SECTION); fixture(b);
    put(b+56,0x04000000);invalid(b,128,SWEET_CSF_BAD_SECTION); fixture(b);
    put(b+48,0xc000003b);invalid(b,128,SWEET_CSF_BAD_SECTION); fixture(b);
    put(b+24,0x40000009);invalid(b,128,SWEET_CSF_BAD_SECTION); fixture(b);
    section(b+20,9,0x04000000,0x04001000);
    invalid(b,128,SWEET_CSF_BAD_SECTION); fixture(b);
    section(b+20,9,0x03fff000,0x04001000);
    invalid(b,128,SWEET_CSF_OVERLAPPING_SECTION); fixture(b);
    put(b+16,44);invalid(b,128,SWEET_CSF_NO_SHARED); fixture(b);
    put(b+68,(4u<<8)|99);put(b+16,72);
    invalid(b,128,SWEET_CSF_UNSUPPORTED_ENTRY);
    put(b+68,0x80000463);calls=0;
    assert(!sweet_csf_parse(b,128,&out,count,NULL) && out.entries==3 && calls==2);
    fixture(b);calls=0;memset(&out,0xa5,sizeof(out));
    struct sweet_csf_layout sentinel=out;
    assert(sweet_csf_parse(b,128,&out,fail,NULL)==SWEET_CSF_CALLBACK_FAILED);
    assert(calls==1 && !memcmp(&out,&sentinel,sizeof(out)));
    fixture(original);
    /* Small deterministic mutation corpus exercises bounds under ASan/UBSan. */
    for(unsigned i=0;i<8192;i++) {
        memcpy(b,original,128);
        unsigned at=(i*37u)%128u; b[at]^=(uint8_t)(i*17u+1u);
        calls=0;int rc=sweet_csf_parse(b,i%129,&out,count,NULL);
        if(rc)assert(calls==0);
    }
    puts("PASS: CSF bounds, atomic validation, overlap, callback, 8192 mutations");
}
int main(int argc, char **argv) {
    if(argc==1) { tests(); return 0; }
    assert(argc==2); FILE *f=fopen(argv[1],"rb"); assert(f);
    assert(!fseek(f,0,SEEK_END)); long n=ftell(f); assert(n>=0); rewind(f);
    uint8_t *b=malloc((size_t)n+1);assert(b);
    assert(fread(b,1,(size_t)n,f)==(size_t)n);fclose(f);
    struct sweet_csf_layout o;int rc=sweet_csf_parse(b,(size_t)n,&o,count,NULL);
    if(!rc)printf("{\"entries\":%u,\"sections\":%u,\"protected_sections\":%u,\"non_16k_sections\":%u,\"shared_va\":%u,\"shared_bytes\":%u,\"format_hash\":%u}\n",
        o.entries,o.sections,o.protected_sections,o.non_16k_sections,
        o.shared_va,o.shared_bytes,o.format_hash);
    free(b);return rc?1:0;
}
'''


@unittest.skipUnless(shutil.which('cc'), 'needs C compiler')
class CsfFirmwareTests(unittest.TestCase):
    def test_real_parser_with_sanitizers(self):
        with tempfile.TemporaryDirectory(prefix='mali-csf-') as directory:
            work = Path(directory)
            source = work / 'harness.c'
            source.write_text(HARNESS)
            binary = work / 'csf-test'
            subprocess.run(['cc', '-std=c11', '-Wall', '-Wextra', '-Werror',
                            '-fsanitize=address,undefined', '-I', str(ROOT / 'xnu/gpu'),
                            str(source), str(ROOT / 'xnu/gpu/mali_csf_firmware.c'),
                            '-o', str(binary)], check=True, capture_output=True)
            subprocess.run([str(binary)], check=True, capture_output=True)


if __name__ == '__main__':
    unittest.main()
