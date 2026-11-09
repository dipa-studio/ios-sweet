"""Exercise the persistent transport's real C with a CS instruction model."""
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
HARNESS = r'''
#include <assert.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include "mali_csf_runtime.h"
#define GPU 0x13000000ull
#define SH 0x90000000ull
#define MEM 0x91000000ull
struct model {
 uint32_t gpu[0x90000/4],sh[0x10000/4],mem[SWEET_CSF_QUEUE_BYTES/4],reg[96];
 uint64_t ticks,user[4];unsigned writes,calls,mode;
};
static uint32_t *addr(struct model*m,uint64_t a){
 assert(!(a&3));
 if(a>=GPU&&a<GPU+sizeof(m->gpu))return m->gpu+(a-GPU)/4;
 if(a>=SH&&a<SH+sizeof(m->sh))return m->sh+(a-SH)/4;
 if(a>=MEM&&a<MEM+sizeof(m->mem))return m->mem+(a-MEM)/4;
 assert(0);return NULL;
}
static uint32_t rd(void*p,uint64_t a){return *addr(p,a);}
static uint64_t word(struct model*m,uint64_t a){return rd(m,a)|((uint64_t)rd(m,a+4)<<32);}
static void instruction(struct model*m,uint64_t ins,unsigned depth){
 unsigned op=ins>>56,dst=(ins>>48)&255,ar=(ins>>40)&255,vr=(ins>>32)&255;
 if(!op)return;
 if(op==1){assert(dst+1<96);m->reg[dst]=ins;m->reg[dst+1]=(ins>>32)&0xffff;}
 else if(op==2){assert(dst<96);m->reg[dst]=ins;}
 else if(op==3){assert((ins>>16)&255);}
 else if(op==36){assert(ar<96&&m->reg[ar]==0);assert((ins&0xffffffff)==0x233||(ins&0xffffffff)==0x211);}
 else if(op==32){
  assert(!depth&&ar==92&&vr==94&&m->reg[92]==0x10000000&&m->reg[93]==0);
  assert(m->reg[vr]&&m->reg[vr]<=sizeof(m->user));m->calls++;
  for(unsigned i=0;i<m->reg[vr]/8;i++)instruction(m,m->user[i],depth+1);
 }else if(op==38){
  assert(!depth&&ar==92&&vr==94&&m->reg[92]==SWEET_CSF_QUEUE_VA+0x3000);
  if(m->mode!=2)m->mem[0x3000/4]=m->reg[vr];
 }else assert(0);
}
static void doorbell(struct model*m){
 uint32_t *gi=m->sh+0x2000/4,*go=m->sh+0x3000/4,*in=m->sh+0x4000/4,*out=m->sh+0x5000/4;
 uint32_t *ci=m->sh+0x6000/4,*co=m->sh+0x7000/4;
 assert((gi[2]^go[2])&1);go[2]=gi[2];out[2]=in[2];
 if(!(in[0]&7)){if(m->mode!=4)out[0]=in[0];return;}
 if(!(ci[0]&7)){co[0]=ci[0];return;}
 out[0]=in[0];co[0]=ci[0];
 if(m->mode==1)return;
 if(m->mode==3){co[0x80/4]=0x44;return;}
 uint64_t insert=word(m,MEM+0x1000),extract=word(m,MEM+0x2000);
 assert(insert>=extract&&insert-extract<=4096);
 for(uint64_t n=extract;n<insert;n+=8)instruction(m,word(m,MEM+(n&4095)),0);
 m->mem[0x2000/4]=insert;m->mem[0x2004/4]=insert>>32;
}
static void wr(void*p,uint64_t a,uint32_t n){
 struct model*m=p;m->writes++;*addr(m,a)=n;
 if(a==GPU+0x80000)doorbell(m);
 if(a==GPU+0x2458)m->gpu[0x2000/4]|=0x20000;
}
static uint64_t tick(void*p){return ++((struct model*)p)->ticks;}
static void barrier(void*p){(void)p;}
static void init(struct model*m){
 memset(m,0,sizeof(*m));m->gpu[0x18/4]=3;m->gpu[0x100/4]=0x7ff;m->gpu[0x110/4]=1;
 m->sh[4]=8;m->sh[5]=160;
 m->sh[0x1004/4]=0x04004000;m->sh[0x1008/4]=0x04005000;
 m->sh[0x100c/4]=26112;m->sh[0x1044/4]=0x04006000;m->sh[0x1048/4]=0x04007000;
}
int main(void){
 struct model*m=calloc(1,sizeof(*m));assert(m);
 struct sweet_gpu_io io={m,rd,wr,tick,barrier,1000000};
 struct sweet_csf_queue_config c={.gpu=GPU,.root_pa=SH,.shared_pa=SH,.memory_pa=MEM,
  .shared_va=0x04000000,.shared_bytes=0x10000,.input_va=0x04002000,.output_va=0x04003000,
  .memory_bytes=SWEET_CSF_QUEUE_BYTES,.timeout_ms=1};
 struct sweet_csf_runtime_group g={0};struct sweet_csf_queue_report r;
 init(m);assert(sweet_csf_runtime_bind(&c,&io,0,0x80000000)==-60&&!m->writes);
 assert(!sweet_csf_runtime_bind(&c,&io,1,0x80000000));
 assert(word(m,GPU+0x2440)==0x80000000&&word(m,GPU+0x2470)==0x42000006);
 assert(!sweet_csf_runtime_invalidate(&c,&io,1)&&word(m,GPU+0x2450)==47);
 assert(!sweet_csf_runtime_start(&c,&io,&g,0,1));
 assert(m->sh[0x4050/4]==1&&m->sh[0x4034/4]==0xf0010b0b);
 for(unsigned i=0;i<100;i++){
  m->user[0]=i?0:0x025000002438cafeull;
  assert(!sweet_csf_runtime_submit(&c,&io,&g,0x10000000,8,&r));
  assert(r.stage==7&&r.after==i+1&&r.extract==(i+1)*128&&r.error==0);
  assert(m->reg[80]==0x2438cafe&&m->calls==i+1);
 }
 unsigned writes=m->writes;
 assert(sweet_csf_runtime_submit(&c,&io,&g,0x10000001,8,&r)==-60&&m->writes==writes);
 assert(sweet_csf_runtime_start(&c,&io,&g,0,1)==-62&&m->writes==writes);
 assert(!sweet_csf_runtime_stop(&c,&io,&g)&&!g.active);
 assert(!sweet_csf_runtime_bind(&c,&io,1,0)&&word(m,GPU+0x2470)==1);
 for(unsigned mode=1;mode<=3;mode++) {
  init(m);memset(&g,0,sizeof(g));assert(!sweet_csf_runtime_start(&c,&io,&g,0,1));
  m->mode=mode;
  assert(sweet_csf_runtime_submit(&c,&io,&g,0x10000000,8,&r)<0&&g.failed);
  writes=m->writes;assert(sweet_csf_runtime_submit(&c,&io,&g,0x10000000,8,&r)<0&&m->writes==writes);
  assert(!sweet_csf_runtime_stop(&c,&io,&g));
 }
 init(m);memset(&g,0,sizeof(g));assert(!sweet_csf_runtime_start(&c,&io,&g,0,1));
 m->mode=4;assert(sweet_csf_runtime_stop(&c,&io,&g)<0&&g.active&&g.failed);
 free(m);return 0;
}
'''


class RuntimeTests(unittest.TestCase):
    def test_persistent_ring_vm_and_failure_paths(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)
            (p / 'test.c').write_text(HARNESS)
            subprocess.run(['clang', '-std=c11', '-O1', '-g', '-Wall', '-Wextra',
                            '-Werror', '-fsanitize=address,undefined',
                            '-I', str(ROOT / 'xnu/gpu'), str(p / 'test.c'),
                            str(ROOT / 'xnu/gpu/mali_csf_runtime.c'),
                            '-o', str(p / 'test')], check=True)
            subprocess.run([str(p / 'test')], check=True)


if __name__ == '__main__':
    unittest.main()
