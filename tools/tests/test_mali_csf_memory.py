"""Replay actual independent CSF load planning/page tables with sanitizers."""
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
HARNESS = r'''
#include <assert.h>
#include <stdint.h>
#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include "mali_csf_memory.h"
static void put(uint8_t *p,uint32_t v) {for(unsigned i=0;i<4;i++)p[i]=v>>(8*i);}
static uint64_t u64(const uint8_t *p) {uint64_t v=0;for(unsigned i=0;i<8;i++)v|=(uint64_t)p[i]<<(8*i);return v;}
static void section(uint8_t *p,uint32_t flags,uint32_t va,uint32_t end,uint32_t start,uint32_t stop) {
 put(p,24<<8);put(p+4,flags);put(p+8,va);put(p+12,end);put(p+16,start);put(p+20,stop);
}
static void fixture(uint8_t *b) {
 memset(b,0,256);put(b,0xc3f13a6e);b[4]=1;put(b+16,92);
 section(b+20,0xd,0,4096,128,132);
 section(b+44,0x4000001b,0x4000000,0x4002000,132,136);
 section(b+68,0x2b,0x3000000,0x3001000,0,0);
 b[128]=0x10;b[129]=0x20;b[130]=0x30;b[131]=0x40;
 b[132]=1;b[133]=2;b[134]=3;b[135]=4;
}
static uint64_t walk(const uint8_t *a,uint64_t pa,uint32_t va) {
 const uint8_t *t=a;
 for(unsigned l=0;l<3;l++) {unsigned shift=39-9*l;uint64_t d=u64(t+(((uint64_t)va>>shift)&511)*8);if((d&3)!=3)return 0;assert((d&0x0000fffffffff000ULL)>=pa);t=a+((d&0x0000fffffffff000ULL)-pa);}
 return u64(t+((va>>12)&511)*8);
}
static void group_checks(const uint8_t *fw,size_t size,const struct sweet_csf_memory *m) {
 uint8_t *baseline=aligned_alloc(4096,m->required_bytes);
 uint8_t *grouped=aligned_alloc(4096,m->required_bytes);
 uint8_t *expected=malloc(m->required_bytes);assert(baseline&&grouped&&expected);
 uint64_t root=0;assert(!sweet_csf_memory_build(fw,size,m,baseline,m->required_bytes,0x90000000,40,&root));
 for(unsigned group=0;group<16;group+=group?9:6) {
  memcpy(expected,baseline,m->required_bytes);
  assert(!sweet_csf_memory_build_group(fw,size,m,grouped,m->required_bytes,root,40,group,&root));
  for(unsigned i=0;i<m->mapping_count;i++)for(unsigned off=0;off<m->map[i].bytes;off+=4096) {
   uint32_t va=m->map[i].va+off;uint8_t *t=expected;
   for(unsigned l=0;l<3;l++) {unsigned shift=39-9*l;uint64_t d=u64(t+(((uint64_t)va>>shift)&511)*8);assert((d&3)==3);t=expected+((d&0x0000fffffffff000ULL)-root);}
   uint8_t *leaf=t+((va>>12)&511)*8;uint64_t value=u64(leaf)|((uint64_t)group<<59);
   for(unsigned k=0;k<8;k++)leaf[k]=(uint8_t)(value>>(8*k));
   assert(walk(grouped,root,va)==(walk(baseline,root,va)|((uint64_t)group<<59)));
  }
  /* Compare every byte: no table/data/cache/permission changes can hide. */
  assert(!memcmp(grouped,expected,m->required_bytes));
 }
 memset(grouped,0xa5,m->required_bytes);root=0xabcdef;
 assert(sweet_csf_memory_build_group(fw,size,m,grouped,m->required_bytes,0x90000000,40,16,&root)==-40);
 for(unsigned i=0;i<m->required_bytes;i++)assert(grouped[i]==0xa5);
 assert(root==0xabcdef);free(expected);free(grouped);free(baseline);
}
static void checks(const uint8_t *fw,size_t size) {
 struct sweet_csf_memory m;assert(!sweet_csf_memory_plan(fw,size,&m));
 assert(m.mapping_count>0 && m.shared_va==0x4000000 && m.shared_bytes);
 uint8_t *a=aligned_alloc(4096,(m.required_bytes+4095)&~4095u);assert(a);
 memset(a,0xa5,m.required_bytes);uint64_t root=0;
 assert(!sweet_csf_memory_build(fw,size,&m,a,m.required_bytes,0x90000000,40,&root));
 assert(root==0x90000000);
 for(unsigned i=0;i<m.mapping_count;i++) {
  struct sweet_csf_mapping *p=&m.map[i];assert(!(p->flags&32));
  assert(!memcmp(a+p->arena_offset,fw+p->data_start,p->data_bytes));
  for(unsigned k=p->data_bytes;k<p->bytes;k++)assert(a[p->arena_offset+k]==0);
  for(unsigned off=0;off<p->bytes;off+=4096) {
   uint64_t d=walk(a,root,p->va+off);assert((d&3)==3);
   assert((d&0x0000fffffffff000ULL)==root+p->arena_offset+off);
   assert(!!(d&0x80)==!(p->flags&2));assert(!!(d&(3ULL<<53))==!(p->flags&4));
   unsigned want=(p->flags&24)==8?4:0;if(p->flags&(1u<<30))want|=0x300;
#if SWEET_CSF_VENDOR_MEMATTR
   /*2380: cached->index0, everything else->index5, no SH bits anywhere. */
   want=(unsigned)((p->flags&24)==8?0u:5u)<<2;
#endif
   assert((d&0x31c)==want);
   /* The selected AS_MEMATTR byte must still be0x88 cached /0x4c other. */
#if SWEET_CSF_VENDOR_MEMATTR
   static const unsigned char tbl[8]={0x88,0x8f,0x8d,0x88,0x8d,0x4c,0x08,0x00};
#else
   static const unsigned char tbl[8]={0x4c,0x88,0x4c,0x4c,0x4c,0x4c,0x4c,0x4c};
#endif
   assert(tbl[(d>>2)&7]==((p->flags&24)==8?0x88:0x4c));
  }
 }
 assert(!walk(a,root,0x3000000));
 group_checks(fw,size,&m);
 memset(a,0xa5,m.required_bytes);root=0xabcdef;
 assert(sweet_csf_memory_build(fw,size,&m,a,m.required_bytes-1,0x90000000,40,&root)==-41);
 assert(a[0]==0xa5 && root==0xabcdef);
 assert(sweet_csf_memory_build(fw,size,&m,a,m.required_bytes,0x90000001,40,&root)==-42);
 assert(sweet_csf_memory_build(fw,size,&m,a,m.required_bytes,(1ULL<<40)-4096,40,&root)==-42);
 assert(sweet_csf_memory_build(fw,size,&m,(void*)fw,m.required_bytes,0x90000000,40,&root)==-40);
 m.map[0].arena_offset+=4096;
 assert(sweet_csf_memory_build(fw,size,&m,a,m.required_bytes,0x90000000,40,&root)==-40);
 assert(a[0]==0xa5 && root==0xabcdef);
 free(a);
 printf("sections=%u protected_skipped=%u tables=%u arena=%u shared=%u\n",m.mapping_count,m.protected_skipped,m.table_pages,m.required_bytes,m.shared_bytes);
}
int main(int argc,char **argv) {
 uint8_t b[256];fixture(b);checks(b,sizeof(b));
 struct sweet_csf_memory m;assert(!sweet_csf_memory_plan(b,sizeof(b),&m));assert(m.mapping_count==2 && m.protected_skipped==1 && m.table_pages==5);
 memset(&m,0xa5,sizeof(m));struct sweet_csf_memory keep=m;b[0]=0;
 assert(sweet_csf_memory_plan(b,sizeof(b),&m));assert(!memcmp(&m,&keep,sizeof(m)));
 if(argc==2) {FILE*f=fopen(argv[1],"rb");assert(f);fseek(f,0,SEEK_END);long n=ftell(f);rewind(f);uint8_t *fw=malloc(n);assert(fread(fw,1,n,f)==(size_t)n);fclose(f);checks(fw,n);free(fw);}
 return 0;
}
'''
DUMP = r'''
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "mali_csf_memory.h"
static void put(uint8_t *p,uint32_t v) {for(unsigned i=0;i<4;i++)p[i]=v>>(8*i);}
static uint64_t u64(const uint8_t *p) {uint64_t v=0;for(unsigned i=0;i<8;i++)v|=(uint64_t)p[i]<<(8*i);return v;}
static void section(uint8_t *p,uint32_t flags,uint32_t va,uint32_t end,uint32_t start,uint32_t stop) {
 put(p,24<<8);put(p+4,flags);put(p+8,va);put(p+12,end);put(p+16,start);put(p+20,stop);
}
static void fixture(uint8_t *b) {
 memset(b,0,256);put(b,0xc3f13a6e);b[4]=1;put(b+16,92);
 section(b+20,0xd,0,4096,128,132);
 section(b+44,0x4000001b,0x4000000,0x4002000,132,136);
 section(b+68,0x2b,0x3000000,0x3001000,0,0);
 b[128]=0x10;b[129]=0x20;b[130]=0x30;b[131]=0x40;
 b[132]=1;b[133]=2;b[134]=3;b[135]=4;
}
static uint64_t walk(const uint8_t *a,uint64_t pa,uint32_t va) {
 const uint8_t *t=a;
 for(unsigned l=0;l<3;l++) {unsigned shift=39-9*l;uint64_t d=u64(t+(((uint64_t)va>>shift)&511)*8);if((d&3)!=3)return 0;t=a+((d&0x0000fffffffff000ULL)-pa);}
 return u64(t+((va>>12)&511)*8);
}
int main(void) {
 uint8_t b[256];fixture(b);
 struct sweet_csf_memory m;if(sweet_csf_memory_plan(b,sizeof b,&m))return 2;
 uint8_t *a=aligned_alloc(4096,(m.required_bytes+4095)&~4095u);if(!a)return 4;
 uint64_t root=0;if(sweet_csf_memory_build(b,sizeof b,&m,a,m.required_bytes,0x90000000,40,&root))return 3;
 for(unsigned i=0;i<m.mapping_count;i++)
  for(unsigned off=0;off<m.map[i].bytes;off+=4096)
   printf("%08x %016llx %u\n",m.map[i].va+off,(unsigned long long)walk(a,root,m.map[i].va+off),m.map[i].flags);
 return 0;
}
'''
@unittest.skipUnless(shutil.which('cc'),'requires C compiler')
class CsfMemoryTests(unittest.TestCase):
    def test_real_memory_builder(self):
        with tempfile.TemporaryDirectory() as directory:
            p=Path(directory);(p/'h.c').write_text(HARNESS)
            subprocess.run(['cc','-std=c11','-Wall','-Wextra','-Werror','-fsanitize=address,undefined',
                '-I',str(ROOT/'xnu/gpu'),str(p/'h.c'),str(ROOT/'xnu/gpu/mali_csf_firmware.c'),
                str(ROOT/'xnu/gpu/mali_csf_memory.c'),'-o',str(p/'test')],check=True,capture_output=True)
            subprocess.run([str(p/'test')],check=True,capture_output=True)

    def test_vendor_memattr_builder(self):
        """2380 pairing: same harness, vendor leaf encode, still self-consistent."""
        with tempfile.TemporaryDirectory() as directory:
            p=Path(directory);(p/'h.c').write_text(HARNESS)
            subprocess.run(['cc','-std=c11','-Wall','-Wextra','-Werror','-fsanitize=address,undefined',
                '-DSWEET_CSF_VENDOR_MEMATTR=1','-I',str(ROOT/'xnu/gpu'),str(p/'h.c'),
                str(ROOT/'xnu/gpu/mali_csf_firmware.c'),str(ROOT/'xnu/gpu/mali_csf_memory.c'),
                '-o',str(p/'test')],check=True,capture_output=True)
            subprocess.run([str(p/'test')],check=True,capture_output=True)

    def test_vendor_pairing_changes_only_attr_index_and_share(self):
        """Diff the two encodings leaf by leaf: only bits0x31c may move."""
        def dump(define):
            with tempfile.TemporaryDirectory() as directory:
                p=Path(directory);(p/'d.c').write_text(DUMP)
                cmd=['cc','-std=c11','-Wall','-Wextra','-Werror','-I',str(ROOT/'xnu/gpu')]
                if define:cmd.append(define)
                cmd+=[str(p/'d.c'),str(ROOT/'xnu/gpu/mali_csf_firmware.c'),
                      str(ROOT/'xnu/gpu/mali_csf_memory.c'),'-o',str(p/'dump')]
                subprocess.run(cmd,check=True,capture_output=True)
                out=subprocess.run([str(p/'dump')],check=True,capture_output=True,text=True).stdout
                rows={}
                for line in out.splitlines():
                    va,desc,flags=line.split()
                    rows[int(va,16)]=(int(desc,16),int(flags))
                return rows
        legacy=dump(None);vendor=dump('-DSWEET_CSF_VENDOR_MEMATTR=1')
        self.assertEqual(set(legacy),set(vendor))
        self.assertTrue(legacy)
        for va,(old,flags) in legacy.items():
            new=vendor[va][0]
            self.assertEqual(old&~0x31c,new&~0x31c,'leaf 0x%x changed outside AttrIndx/SH'%va)
            cached=(flags&24)==8
            self.assertEqual((new>>2)&7,0 if cached else 5)
            self.assertEqual((new>>8)&3,0)
            self.assertEqual((old>>2)&7,1 if cached else 0)
            if flags&(1<<30):self.assertEqual((old>>8)&3,3)
            self.assertEqual(new&0x40,0x40,'AP[2] must stay read-only')

if __name__=='__main__':unittest.main()
