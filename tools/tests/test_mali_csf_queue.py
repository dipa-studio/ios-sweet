"""Run the actual queue transport against an independent MMIO/CS model."""
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
#include "mali_csf_queue.h"
#define GPU 0x13000000ULL
#define SH 0x90000000ULL
#define MEM 0x91000000ULL
struct model {
 uint32_t gpu[0x90000/4],sh[0x10000/4],mem[SWEET_CSF_QUEUE_BYTES/4];
 uint64_t ticks;unsigned writes,bells,executed;int mode;
};
static uint32_t *address(struct model*m,uint64_t a){
 assert(!(a&3));
 if(a>=GPU&&a<GPU+sizeof(m->gpu))return &m->gpu[(a-GPU)/4];
 if(a>=SH&&a<SH+sizeof(m->sh))return &m->sh[(a-SH)/4];
 if(a>=MEM&&a<MEM+sizeof(m->mem))return &m->mem[(a-MEM)/4];
 assert(0);return NULL;
}
static uint32_t rd(void*p,uint64_t a){return *address(p,a);}
static uint64_t word(struct model*m,uint64_t a){return rd(m,a)|((uint64_t)rd(m,a+4)<<32);}
static void execute(struct model*m){
 uint32_t *gi=m->sh+0x2000/4,*go=m->sh+0x3000/4;
 uint32_t *in=m->sh+0x4000/4,*out=m->sh+0x5000/4;
 uint32_t *ci=m->sh+0x6000/4,*co=m->sh+0x7000/4;
 assert((gi[2]^go[2])&1);go[2]=gi[2];
 if(!(in[0]&7)){if(m->mode!=5)out[0]=in[0];return;}
 assert(in[0]==0x11&&in[0x50/4]==1&&ci[4]==0x06000000&&ci[6]==4096);
 assert(ci[0x30/4]==0x06001000&&ci[0x38/4]==0x06002000);
 assert(in[0x40/4]==0x06010000&&in[0x34/4]==0xf0010101);
 assert(m->gpu[0x2440/4]==0x90000000&&m->gpu[0x2470/4]==0x42000006);
 if(m->mode==1)return;
 out[0]=in[0];co[0]=ci[0];
 if(m->mode==4){co[0x84/4]=0x44;return;}
 if(m->mode==6){m->gpu[0x2000/4]|=2;return;}
 if(m->mode==7){m->gpu[0x245c/4]=0xc1;return;}
 uint32_t regs[96]={0};unsigned waited=0,resources=0;
 unsigned length=m->mem[0x1000/4];
 /* Decode the submitted words, rather than accepting a host-supplied tag. */
 for(unsigned off=0;off<length;off+=8){
  uint64_t ins=word(m,MEM+off);unsigned op=ins>>56,dst=(ins>>48)&255;
  if(op==1){assert(dst+1<96);regs[dst]=ins;regs[dst+1]=(ins>>32)&0xffff;}
  else if(op==2){assert(dst<96);regs[dst]=ins;}
  else if(op==38){
   unsigned addr=(ins>>40)&255,data=(ins>>32)&255;
   assert(addr+1<96&&data<96&&(ins&0xffffffff)==0&&dst==0);
   uint64_t va=regs[addr]|((uint64_t)regs[addr+1]<<32);
   assert(va==(SWEET_CSF_COMPUTE_PROBE?0x06003010:0x06003000));
   if(!SWEET_CSF_COMPUTE_PROBE)assert(m->mem[0x3000/4]==0xdeadbeef);
   m->mem[(va-0x06000000)/4]=regs[data]^(m->mode==2);m->executed++;
  }else if(op==3){assert(((ins>>16)&255)!=0);waited++;}
  else if(op==34){resources=ins&15;}
  else if(op==23){assert((ins&255)==2);}
  else if(op==36){assert((ins&0xffffffff)==0x211&&regs[(ins>>40)&255]==0);}
  else if(op==4){
   assert(SWEET_CSF_COMPUTE_PROBE&&resources==1&&(ins&0xffff)==0x8001);
   assert(regs[0]==0&&regs[8]==0&&regs[16]==0x06005000&&regs[24]==0x06006000);
   assert(regs[33]==0&&regs[37]==1&&regs[38]==1&&regs[39]==1);
   assert(m->mem[0x5000/4]==0x80000018&&m->mem[0x6004/4]==31);
   uint64_t pc=word(m,MEM+0x5008);uint32_t sr[64]={0};
   for(unsigned k=0;k<4;k++){
    uint64_t shader=word(m,MEM+(pc-0x06000000)+k*8);
    if(((shader>>48)&255)==16){
     assert((shader&0xffffc000000000ffULL)==0x0110c000000000c0ULL);
     sr[(shader>>40)&63]=(uint32_t)(shader>>8);
    }else{
     assert(((shader>>48)&255)==0x61&&((shader>>59)&15)==15);
     unsigned ar=shader&63,dr=(shader>>40)&63;assert(ar+1<64);
     uint64_t va=sr[ar]|((uint64_t)sr[ar+1]<<32);assert(va==0x06003000);
     assert(m->mem[0x3000/4]==0xdeadbeef);m->mem[0x3000/4]=sr[dr];
    }
   }
  }
  else assert(0);
 }
 assert(waited==(SWEET_CSF_COMPUTE_PROBE?3:1));
 m->mem[0x2000/4]=m->mode==3?length-8:length;
}
static void wr(void*p,uint64_t a,uint32_t n){
 struct model*m=p;m->writes++;*address(m,a)=n;
 if(a==GPU+0x2458){assert(n==1);m->gpu[0x2000/4]|=0x20000;}
 if(a==GPU+0x80000){assert(n==1);m->bells++;execute(m);}
}
static uint64_t ticks(void*p){return ++((struct model*)p)->ticks;}
static void barrier(void*p){(void)p;}
static void init(struct model*m){
 memset(m,0,sizeof(*m));m->gpu[0x18/4]=3;m->gpu[0x100/4]=0x770017;m->gpu[0x110/4]=1;
 m->sh[0x1004/4]=0x04004000;m->sh[0x1008/4]=0x04005000;
 m->sh[0x100c/4]=0x10000;m->sh[0x1014/4]=8;m->sh[0x1018/4]=12;
 m->sh[0x1044/4]=0x04006000;m->sh[0x1048/4]=0x04007000;
}
static void memory_test(void){
 uint64_t *a=calloc(1,2<<20);assert(a);uint64_t p=0x90000000,mem=0;
 a[0]=(p+4096)|3;a[512]=(p+8192)|3;
 assert(!sweet_csf_queue_memory(a,2<<20,p,0x10000,3,40,&mem));
 assert(mem==p+0x11000&&a[1024+48]==(p+0x10000+3));
 for(unsigned i=0;i<128;i++){
  uint64_t flags=(SWEET_CSF_COMPUTE_PROBE&&i==4)?0x4d7:0x0060000000000457ULL;
  assert(a[0x10000/8+i]==((mem+4096*i)|flags));
 }
 assert(a[0]==((p+4096)|3)&&a[512]==((p+8192)|3));
 uint8_t *copy=malloc(2<<20);assert(copy);memcpy(copy,a,2<<20);
 assert(sweet_csf_queue_memory(a,2<<20,p,0x10000,3,40,&mem)<0);assert(!memcmp(a,copy,2<<20));
 assert(sweet_csf_queue_memory(a,0x11000,p,0x10000,3,40,&mem)<0);assert(!memcmp(a,copy,2<<20));
 a[0]=((p+0x10000)|3);memcpy(copy,a,2<<20);
 assert(sweet_csf_queue_memory(a,2<<20,p,0x10000,3,40,&mem)<0);assert(!memcmp(a,copy,2<<20));
 free(copy);free(a);
}
int main(void){
 struct model*m=malloc(sizeof(*m));assert(m);
 struct sweet_gpu_io io={m,rd,wr,ticks,barrier,1000000};
 struct sweet_csf_queue_config c={.gpu=GPU,.root_pa=SH,.shared_pa=SH,.memory_pa=MEM,
 .shared_va=0x04000000,.shared_bytes=0x10000,.input_va=0x04002000,.output_va=0x04003000,
 .memory_bytes=SWEET_CSF_QUEUE_BYTES,.timeout_ms=1};
 struct sweet_csf_queue_report r;
 for(int i=0;i<8;i++){init(m);m->mode=i;int rc=sweet_csf_queue_probe(&c,&io,&r);
  if(!i)assert(!rc&&r.stage==7&&r.after==(SWEET_CSF_COMPUTE_PROBE?SWEET_CSF_COMPUTE_TAG:SWEET_CSF_QUEUE_TAG)&&
              r.extract==(SWEET_CSF_COMPUTE_PROBE?192:32)&&m->executed==1);
  else assert(rc<0&&r.stage!=7);assert(m->bells==2);
 }
 init(m);m->gpu[0x2470/4]=6;assert(sweet_csf_queue_probe(&c,&io,&r)==-62&&!m->writes);
 init(m);m->sh[0x1044/4]=0x04004000;assert(sweet_csf_queue_probe(&c,&io,&r)==-61&&!m->writes);
 init(m);m->sh[0x100c/4]=0x80000;assert(sweet_csf_queue_probe(&c,&io,&r)==-61&&!m->writes);
 memory_test();free(m);return 0;
}
'''


class QueueTests(unittest.TestCase):
    def test_actual_queue_and_memory_under_sanitizers(self):
        self.run_model(False)

    def test_compute_shader_and_stream_under_sanitizers(self):
        self.run_model(True)

    def run_model(self, compute):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            (d / 'queue.c').write_text(HARNESS)
            subprocess.run(['cc', '-std=c11', '-O1', '-g', '-Wall', '-Wextra', '-Werror',
                '-fsanitize=address,undefined', '-DSWEET_CSF_COMPUTE_PROBE='+str(int(compute)),
                '-I' + str(ROOT / 'xnu/gpu'),
                str(d / 'queue.c'), str(ROOT / 'xnu/gpu/mali_csf_queue.c'),
                '-o', str(d / 'queue')], check=True)
            subprocess.run([str(d / 'queue')], check=True)


if __name__ == '__main__':
    unittest.main()
