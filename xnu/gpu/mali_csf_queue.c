/* SPDX-License-Identifier: MIT
 * MT6983 r32p1 CSF interface, cross-checked with panthor_fw.h/panthor_sched.c.
 * Instruction fields follow Mesa25.0.7 genxml/v10.xml. No Linux dependencies.
 */
#include "mali_csf_queue.h"
#include "mali_csf_memory.h"

static uint64_t load64(const uint8_t *p)
{
    uint64_t n=0;for(unsigned i=0;i<8;i++)n|=(uint64_t)p[i]<<(i*8);return n;
}
static void store64(uint8_t *p,uint64_t n)
{
    for(unsigned i=0;i<8;i++)p[i]=(uint8_t)(n>>(i*8));
}
int sweet_csf_queue_memory(void *buffer,size_t capacity,uint64_t pa,
    uint32_t used,uint32_t table_pages,unsigned pa_bits,uint64_t *memory_pa)
{
    uint8_t *arena=buffer,*table=buffer;
    const uint64_t mask=UINT64_C(0x0000fffffffff000);
    if(!buffer||!memory_pa||((uintptr_t)buffer&7)||(pa&4095)||(used&4095)||
       !table_pages||table_pages>used/4096||used>capacity||
       4096+SWEET_CSF_QUEUE_BYTES>capacity-used||pa_bits<32||pa_bits>48||
       pa<0x40000000||pa>=(UINT64_C(1)<<pa_bits)||
       capacity>(UINT64_C(1)<<pa_bits)-pa)return -60;
    /* QUEUE_VA shares existing L0/L1/L2 with firmware. Never follow data
     * memory or overwrite an occupied slot; validate everything first. */
    for(unsigned l=0;l<2;l++) {
        uint64_t d=load64(table+(((uint64_t)SWEET_CSF_QUEUE_VA>>(39-9*l))&511)*8);
        uint64_t next=d&mask;
        if((d&3)!=3||next<pa||next-pa>=(uint64_t)table_pages*4096)return -60;
        table=arena+(next-pa);
    }
    uint8_t *slot=table+((SWEET_CSF_QUEUE_VA>>21)&511)*8;
    if(load64(slot))return -60;
    for(size_t i=used;i<used+4096+SWEET_CSF_QUEUE_BYTES;i++)arena[i]=0;
    uint64_t data=pa+used+4096;
    for(unsigned i=0;i<SWEET_CSF_QUEUE_BYTES/4096;i++)
        store64(arena+used+i*8,(data+i*4096)|UINT64_C(0x60000000000457));
    /* Vendor AP=RW, AF, AttrIdx5(noncacheable), XN; no physical-group tag
     * for application BOs. Firmware mappings retain their existing tags. */
    store64(slot,(pa+used)|3);
    *memory_pa=data;return 0;
}

static uint32_t rd(const struct sweet_gpu_io *io,uint64_t a)
{return io->read32(io->context,a);}
static void wr(const struct sweet_gpu_io *io,uint64_t a,uint32_t n)
{io->write32(io->context,a,n);io->barrier(io->context);}
static void wr64(const struct sweet_gpu_io *io,uint64_t a,uint64_t n)
{wr(io,a,(uint32_t)n);wr(io,a+4,(uint32_t)(n>>32));}
static int poll(const struct sweet_gpu_io *io,uint64_t a,uint32_t mask,uint32_t n,uint64_t budget)
{
    uint64_t start=io->ticks(io->context);
    for(unsigned i=0;i<10000000;i++) {
        if((rd(io,a)&mask)==n)return 0;
        if(io->ticks(io->context)-start>=budget)break;
    }
    return -63;
}
static uint64_t iface(const struct sweet_csf_queue_config *c,uint32_t va)
{
    if((va&4095)||va<c->shared_va+0x2000||va-c->shared_va>c->shared_bytes-4096)return 0;
    return c->shared_pa+(va-c->shared_va);
}
static void doorbell(const struct sweet_csf_queue_config *c,const struct sweet_gpu_io *io,
    uint64_t gi,uint64_t go)
{
    wr(io,gi+8,(rd(io,gi+8)&~1u)|((rd(io,go+8)^1u)&1u));
    wr(io,c->gpu+0x80000,1);
}
int sweet_csf_queue_probe(const struct sweet_csf_queue_config *c,
    const struct sweet_gpu_io *io,struct sweet_csf_queue_report *r)
{
    if(!r)return -60;
    *r=(struct sweet_csf_queue_report){.stage=1};
    if(!c||!io||!io->read32||!io->write32||!io->barrier||!io->ticks||
       !io->frequency||io->frequency>1000000000||c->gpu!=0x13000000||
       c->shared_va!=0x04000000||c->shared_bytes<0x4000||c->shared_bytes>0x1000000||
       c->memory_bytes!=SWEET_CSF_QUEUE_BYTES||(c->memory_pa&4095)||
       c->memory_pa<0x40000000||c->memory_pa>UINT64_MAX-c->memory_bytes||
       (c->root_pa&4095)||c->root_pa<0x40000000||
       !c->timeout_ms||c->timeout_ms>1000){r->error=-60;return r->error;}
    uint64_t budget=(io->frequency*c->timeout_ms+999)/1000;
    uint64_t gi=iface(c,c->input_va),go=iface(c,c->output_va);
    uint64_t ctrl=c->shared_pa+0x1000;
    uint64_t in=iface(c,rd(io,ctrl+4)),out=iface(c,rd(io,ctrl+8));
    r->suspend_bytes=rd(io,ctrl+12);r->streams=rd(io,ctrl+20);
    uint32_t stride=rd(io,ctrl+24);
    uint64_t ci=iface(c,rd(io,ctrl+0x44)),co=iface(c,rd(io,ctrl+0x48));
    uint64_t pages[]={gi,go,in,out,ci,co};
    for(unsigned i=0;i<6;i++) {
        if(!pages[i]){r->error=-61;return r->error;}
        for(unsigned j=0;j<i;j++)if(pages[i]==pages[j]){r->error=-61;return r->error;}
    }
    if(!r->streams||r->streams>32||stride<12||(stride&3)||
       !r->suspend_bytes||r->suspend_bytes>SWEET_CSF_QUEUE_BYTES-0x10000||
       (rd(io,out)&7)||(rd(io,co)&7)||!(rd(io,c->gpu+0x18)&2)) {
        r->error=-61;return r->error;
    }
    r->stage=2;
    /* AS1 belongs exclusively to this transaction. Same owned root as the
     * MCU for now; a resident multi-client driver must use separate roots. */
    uint64_t as=c->gpu+0x2440;
    if((rd(io,as+0x30)&15)>1||rd(io,as)||rd(io,as+4)){r->error=-62;return r->error;}
    if(poll(io,as+0x28,1,0,budget)){r->error=-63;return r->error;}
    wr64(io,as,c->root_pa);
    wr(io,as+8,SWEET_CSF_VENDOR_MEMATTR_LO);wr(io,as+12,SWEET_CSF_VENDOR_MEMATTR_HI);
    wr64(io,as+0x30,0x42000006);wr(io,as+0x18,1);
    if(poll(io,as+0x28,1,0,budget)){r->error=-63;return r->error;}
    r->stage=3;
    /* ring+0, input+0x1000, output+0x2000, completion+0x3000,
     * suspend+0x10000. SYNC_SET32 writes data and an error word. */
    uint64_t mem=c->memory_pa,va=SWEET_CSF_QUEUE_VA;
    wr(io,mem+0x3000,0xdeadbeef);wr(io,mem+0x3004,0);
    r->before=rd(io,mem+0x3000);
    wr64(io,mem,UINT64_C(0x0100000000000000)|(va+0x3000));
    wr64(io,mem+8,UINT64_C(0x0202000000000000)|SWEET_CSF_QUEUE_TAG);
    wr64(io,mem+16,UINT64_C(0x2600000200000000));
    wr64(io,mem+24,UINT64_C(0x0300000000010000));
    r->insert=32;wr64(io,mem+0x1000,r->insert);wr64(io,mem+0x1008,0);
    wr64(io,mem+0x2000,0);
    wr64(io,ci+0x10,va);wr(io,ci+0x18,4096);
    wr64(io,ci+0x30,va+0x1000);wr64(io,ci+0x38,va+0x2000);
    wr(io,ci+4,0x10f);wr(io,ci+12,UINT32_MAX);
    r->cs_req=(rd(io,ci)&~0x517u)|0x511u;wr(io,ci,r->cs_req);
    wr64(io,in+0x20,rd(io,c->gpu+0x100)|(uint64_t)rd(io,c->gpu+0x104)<<32);
    wr64(io,in+0x28,rd(io,c->gpu+0x100)|(uint64_t)rd(io,c->gpu+0x104)<<32);
    wr(io,in+0x30,rd(io,c->gpu+0x110));wr(io,in+0x34,0xf0010101);
    wr64(io,in+0x40,va+0x10000);wr64(io,in+0x48,0);wr(io,in+0x50,1);
    wr(io,in+4,UINT32_MAX);
    wr(io,in+8,(rd(io,in+8)&~1u)|((rd(io,out+8)^1u)&1u));
    r->csg_req=(rd(io,in)&~0x17u)|((rd(io,out)^0x10)&0x10)|1u;
    wr(io,in,r->csg_req);doorbell(c,io,gi,go);r->stage=4;
    uint64_t start=io->ticks(io->context);
    r->error=-63;
    for(unsigned i=0;i<10000000;i++) {
        io->barrier(io->context);r->polls++;
        r->csg_ack=rd(io,out);r->cs_ack=rd(io,co);
        r->extract=rd(io,mem+0x2000);r->after=rd(io,mem+0x3000);
        r->fault=rd(io,co+0x80);r->fatal=rd(io,co+0x84);
        r->mmu_raw=rd(io,c->gpu+0x2000);r->as_fault=rd(io,as+0x1c);
        r->cmd_lo=rd(io,co+0x40);r->cmd_hi=rd(io,co+0x44);
        if(r->fault||r->fatal||r->mmu_raw||rd(io,mem+0x3004)) {r->error=-64;break;}
        if((r->csg_ack&0x17)==(r->csg_req&0x17)&&(r->cs_ack&7)==1&&
           r->after==SWEET_CSF_QUEUE_TAG&&r->before==0xdeadbeef&&
           r->extract==r->insert&&!rd(io,mem+0x2004)){r->error=0;r->stage=5;break;}
        if(io->ticks(io->context)-start>=budget)break;
    }
    /* Terminate before returning; the boot transaction then resets the GPU
     * on both success and error, so no caller can reclaim live DMA memory. */
    wr(io,in,rd(io,in)&~7u);doorbell(c,io,gi,go);
    int stopped=poll(io,out,7,0,budget);r->stop_ack=rd(io,out);
    if(!r->error&&stopped)r->error=stopped;
    if(!r->error)r->stage=7;
    return r->error;
}
