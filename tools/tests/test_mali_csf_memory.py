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
RELOC_DUMP = r"""
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
static void alt_fixture(uint8_t *b) {
 /* executable, but not at the code VA; and the code VA is not executable. */
 memset(b,0,256);put(b,0xc3f13a6e);b[4]=1;put(b+16,92);
 section(b+20,0x0b,0x01000000,0x01002000,128,132);
 section(b+44,0x0d,0x02000000,0x02002000,132,136);
 section(b+68,0x4000001b,0x04000000,0x04002000,136,140);
 b[128]=0x10;b[129]=0x20;b[130]=0x30;b[131]=0x40;
 b[132]=1;b[133]=2;b[134]=3;b[135]=4;b[136]=5;b[137]=6;b[138]=7;b[139]=8;
}
static void fixture(uint8_t *b) {
 memset(b,0,256);put(b,0xc3f13a6e);b[4]=1;put(b+16,92);
 /* one executable section at the firmware's code VA, a RW data section and a
  * shared section, so a relocation has exactly one legal target. */
 section(b+20,0x0d,0x01000000,0x01002000,128,132);
 section(b+44,0x0b,0x02000000,0x02002000,132,136);
 section(b+68,0x4000001b,0x04000000,0x04002000,136,140);
 b[128]=0x10;b[129]=0x20;b[130]=0x30;b[131]=0x40;
 b[132]=1;b[133]=2;b[134]=3;b[135]=4;b[136]=5;b[137]=6;b[138]=7;b[139]=8;
}
static uint64_t walk(const uint8_t *a,uint64_t pa,uint32_t va) {
 const uint8_t *t=a;
 for(unsigned l=0;l<3;l++) {unsigned shift=39-9*l;uint64_t d=u64(t+(((uint64_t)va>>shift)&511)*8);if((d&3)!=3)return 0;t=a+((d&0x0000fffffffff000ULL)-pa);}
 return u64(t+((va>>12)&511)*8);
}
int main(int argc,char **argv) {
 uint8_t b[256];(void)argv;
 if(argc==2)alt_fixture(b);else fixture(b);
 struct sweet_csf_memory m;if(sweet_csf_memory_plan(b,sizeof b,&m))return 2;
 uint8_t *a=aligned_alloc(4096,(m.required_bytes+4095)&~4095u);if(!a)return 4;
 uint64_t root=0;if(sweet_csf_memory_build(b,sizeof b,&m,a,m.required_bytes,0x90000000,40,&root))return 3;
 printf("required %u tables %u\n",m.required_bytes,m.table_pages);
 for(unsigned i=0;i<m.mapping_count;i++)
  printf("sec %08x %u %u %u %016llx\n",m.map[i].va,m.map[i].arena_offset,m.map[i].bytes,
         m.map[i].flags,(unsigned long long)walk(a,root,m.map[i].va));
 /* the abandoned slot must be padding, not a second copy of the section. */
 printf("copy %u\n",(unsigned)memcmp(a+m.map[1].arena_offset,b+m.map[1].data_start,m.map[1].data_bytes)==0);
 return 0;
}
"""
ALIAS_DUMP = r"""
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
/* code at 0x01000000, RW stack at 0x02000000, shared at 0x04000000: the alias
 * target is a different section, so a correct alias changes the PA only. */
static void fixture(uint8_t *b) {
 memset(b,0,256);put(b,0xc3f13a6e);b[4]=1;put(b+16,92);
 section(b+20,0x0d,0x01000000,0x01002000,128,132);
 section(b+44,0x0b,0x02000000,0x02002000,132,136);
 section(b+68,0x4000001b,0x04000000,0x04002000,136,140);
 b[128]=0x10;b[129]=0x20;b[130]=0x30;b[131]=0x40;
 b[132]=1;b[133]=2;b[134]=3;b[135]=4;b[136]=5;b[137]=6;b[138]=7;b[139]=8;
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
 memset(a,0xa5,m.required_bytes);
 uint64_t root=0;
 int rc=sweet_csf_memory_build_group(b,sizeof b,&m,a,m.required_bytes,0x90000000,40,6,&root);
 printf("rc %d\n",rc);
 if(rc)return 0;
 printf("required %u\n",m.required_bytes);
 for(unsigned i=0;i<m.mapping_count;i++)
  for(unsigned off=0;off<m.map[i].bytes;off+=4096)
   printf("%08x %016llx\n",m.map[i].va+off,(unsigned long long)walk(a,root,m.map[i].va+off));
 return 0;
}
"""
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

    def test_page_uncached_changes_only_that_leaf(self):
        """2400: one page takes AS_MEMATTR index 5, the section keeps the rest."""
        def dump(define):
            with tempfile.TemporaryDirectory() as directory:
                p=Path(directory);(p/'d.c').write_text(ALIAS_DUMP)
                cmd=['cc','-std=c11','-Wall','-Wextra','-Werror','-I',str(ROOT/'xnu/gpu')]
                if define:cmd.append(define)
                cmd+=[str(p/'d.c'),str(ROOT/'xnu/gpu/mali_csf_firmware.c'),
                      str(ROOT/'xnu/gpu/mali_csf_memory.c'),'-o',str(p/'dump')]
                subprocess.run(cmd,check=True,capture_output=True)
                out=subprocess.run([str(p/'dump')],check=True,capture_output=True,text=True).stdout
                rows={}
                for line in out.splitlines():
                    head=line.split()
                    if len(head)!=2:continue
                    try:rows[int(head[0],16)]=int(head[1],16)
                    except ValueError:continue
                return rows
        base=dump(None);uncached=dump('-DSWEET_CSF_UNCACHED_VA=0x01000000u')
        self.assertEqual(set(base),set(uncached))
        self.assertIn(0x01000000,base);self.assertIn(0x01001000,base)
        for va,desc in base.items():
            new=uncached[va]
            if va!=0x01000000:
                self.assertEqual(desc,new,'leaf 0x%x must not move'%va)
                continue
            self.assertEqual((new>>2)&7,5,'the named page must take AttrIdx 5')
            self.assertEqual((new>>8)&3,0,'a non-cacheable leaf must carry no SH bits')
            self.assertEqual(desc&~0x31c,new&~0x31c,
                             'only AttrIdx and SH may move on the named page')
        # The entry page keeps its cached leaf, which is what lets the start
        # stay at 2394's.
        self.assertEqual(uncached[0x01001000],base[0x01001000])

    def test_alias_repoints_one_leaf_and_keeps_its_bits(self):
        """2399: one page takes another section's PA, its attributes stay."""
        def dump(from_va,to_va):
            with tempfile.TemporaryDirectory() as directory:
                p=Path(directory);(p/'d.c').write_text(ALIAS_DUMP)
                cmd=['cc','-std=c11','-Wall','-Wextra','-Werror','-I',str(ROOT/'xnu/gpu'),
                     '-DSWEET_CSF_ALIAS_VA=%s'%from_va,'-DSWEET_CSF_ALIAS_TO_VA=%s'%to_va,
                     str(p/'d.c'),str(ROOT/'xnu/gpu/mali_csf_firmware.c'),
                     str(ROOT/'xnu/gpu/mali_csf_memory.c'),'-o',str(p/'dump')]
                subprocess.run(cmd,check=True,capture_output=True)
                out=subprocess.run([str(p/'dump')],check=True,capture_output=True,text=True).stdout
                rc=None;rows={}
                for line in out.splitlines():
                    head=line.split()
                    if head[0]=='rc':rc=int(head[1])
                    elif head[0]!='required':rows[int(head[0],16)]=int(head[1],16)
                return rc,rows
        rc,base=dump('0','0')
        self.assertEqual(rc,0)
        self.assertIn(0x01000000,base);self.assertIn(0x02000000,base)
        rc,aliased=dump('0x01000000u','0x02000000u')
        self.assertEqual(rc,0)
        self.assertEqual(set(base),set(aliased))
        code,stack=base[0x01000000],base[0x02000000]
        page=0x0000fffffffff000
        self.assertEqual(aliased[0x01000000]&page,stack&page,'the page must take the stack PA')
        self.assertEqual(aliased[0x01000000]&~page,code&~page,
                         'the aliased leaf must keep every non-address bit')
        self.assertEqual(aliased[0x02000000],stack,'the source leaf must not move')
        moved=[va for va in base if base[va]!=aliased[va]]
        self.assertEqual(moved,[0x01000000],'the alias must touch exactly one leaf')
        # A target that the plan never mapped, and a misaligned address, fail
        # closed: no leaf may be written and the build must report -40.
        for from_va,to_va in (('0x01000000u','0x03000000u'),('0x01000100u','0x02000000u')):
            rc,rows=dump(from_va,to_va)
            self.assertEqual(rc,-40,'%s -> %s must be refused'%(from_va,to_va))

    def test_relocated_code_moves_only_that_section(self):
        """2382: the plan moves the R-X section and nothing else."""
        def dump(define):
            with tempfile.TemporaryDirectory() as directory:
                p=Path(directory);(p/'d.c').write_text(RELOC_DUMP)
                cmd=['cc','-std=c11','-Wall','-Wextra','-Werror','-I',str(ROOT/'xnu/gpu')]
                if define:cmd.append(define)
                cmd+=[str(p/'d.c'),str(ROOT/'xnu/gpu/mali_csf_firmware.c'),
                      str(ROOT/'xnu/gpu/mali_csf_memory.c'),'-o',str(p/'dump')]
                subprocess.run(cmd,check=True,capture_output=True)
                out=subprocess.run([str(p/'dump')],check=True,capture_output=True,text=True).stdout
                required=tables=None;rows=[];copy=None
                for line in out.splitlines():
                    head=line.split()
                    if head[0]=='required':required,tables=int(head[1]),int(head[3])
                    elif head[0]=='sec':rows.append((int(head[1],16),int(head[2]),int(head[3]),
                                                     int(head[4]),int(head[5],16)))
                    elif head[0]=='copy':copy=int(head[1])
                return required,tables,rows,copy
        base_required,base_tables,base,base_copy=dump(None)
        moved_required,moved_tables,moved,moved_copy=dump('-DSWEET_CSF_RELOCATE_CODE=1')
        self.assertEqual(base_tables,moved_tables)
        self.assertEqual(len(base),3);self.assertEqual(len(moved),3)
        code=[row for row in base if row[0]==0x01000000 and row[3]&4]
        self.assertEqual(len(code),1)
        code_va,code_offset,code_bytes,code_flags,code_leaf=code[0]
        # every other section keeps offset, size, flags and leaf descriptor.
        for before,after in zip(base,moved):
            if before[0]==code_va:continue
            self.assertEqual(before,after,'section0x%x moved'%before[0])
        moved_code=next(row for row in moved if row[0]==code_va)
        self.assertEqual(moved_code[1],base_required)
        self.assertEqual(moved_required,base_required+code_bytes)
        self.assertEqual(moved_copy,1,'the abandoned slot must not hold a copy')
        # the only leaf bits that may differ are the physical address field.
        self.assertEqual(code_leaf&~0x0000fffffffff000,moved_code[4]&~0x0000fffffffff000)
        # the shift is everything the default plan placed after the section.
        self.assertEqual((code_leaf&0x0000fffffffff000)+(base_required-code_offset),
                         moved_code[4]&0x0000fffffffff000)

    def test_relocation_needs_both_the_va_and_the_execute_bit(self):
        """No section matches: an executable page elsewhere, a code VA that is RW."""
        def dump(define):
            with tempfile.TemporaryDirectory() as directory:
                p=Path(directory);(p/'d.c').write_text(RELOC_DUMP)
                cmd=['cc','-std=c11','-Wall','-Wextra','-Werror','-I',str(ROOT/'xnu/gpu')]
                if define:cmd.append(define)
                cmd+=[str(p/'d.c'),str(ROOT/'xnu/gpu/mali_csf_firmware.c'),
                      str(ROOT/'xnu/gpu/mali_csf_memory.c'),'-o',str(p/'dump')]
                subprocess.run(cmd,check=True,capture_output=True)
                return subprocess.run([str(p/'dump'),'alt'],check=True,capture_output=True,
                                      text=True).stdout
        base=dump(None);moved=dump('-DSWEET_CSF_RELOCATE_CODE=1')
        self.assertEqual(base,moved,'the flag must be inert when no section qualifies')

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
