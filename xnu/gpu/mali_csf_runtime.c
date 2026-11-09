/* SPDX-License-Identifier: MIT
 * Persistent v10/CSF queues. Register layout: pinned r32p1/Panthor; CALL
 * envelope follows Panthor queue_run_job. Completion is GPU-written memory,
 * never a successful ioctl or mere firmware START acknowledgment. */
#include "mali_csf_runtime.h"
#include "mali_csf_memory.h"
static uint32_t read32(const struct sweet_gpu_io *io,uint64_t a)
{return io->read32(io->context,a);}
static uint64_t read64(const struct sweet_gpu_io *io,uint64_t a)
{return read32(io,a)|((uint64_t)read32(io,a+4)<<32);}
static void write32(const struct sweet_gpu_io *io,uint64_t a,uint32_t v)
{io->write32(io->context,a,v);io->barrier(io->context);}
static void write64(const struct sweet_gpu_io *io,uint64_t a,uint64_t v)
{write32(io,a,(uint32_t)v);write32(io,a+4,(uint32_t)(v>>32));}
static int wait_bits(const struct sweet_csf_queue_config *c,const struct sweet_gpu_io *io,
    uint64_t a,uint32_t mask,uint32_t v)
{
    uint64_t start=io->ticks(io->context),budget=io->frequency*c->timeout_ms/1000;
    for(unsigned i=0;i<10000000;i++) {
        if((read32(io,a)&mask)==v)return 0;
        if(io->ticks(io->context)-start>=budget)break;
    }
    return -63;
}
static int valid(const struct sweet_csf_queue_config *c,const struct sweet_gpu_io *io)
{
    return c&&io&&io->read32&&io->write32&&io->barrier&&io->ticks&&io->frequency&&
        io->frequency<=1000000000&&c->timeout_ms&&c->timeout_ms<=1000&&
        c->gpu==0x13000000&&c->shared_va==0x04000000&&c->shared_bytes>=0x4000&&
        c->shared_bytes<=0x1000000&&c->memory_bytes==SWEET_CSF_QUEUE_BYTES;
}
static uint64_t iface(const struct sweet_csf_queue_config *c,uint32_t va)
{
    if((va&4095)||va<c->shared_va+0x2000||va-c->shared_va>c->shared_bytes-4096)return 0;
    return c->shared_pa+va-c->shared_va;
}
static int as_cmd(const struct sweet_csf_queue_config *c,const struct sweet_gpu_io *io,
    unsigned nr,uint32_t cmd)
{
    uint64_t as=c->gpu+0x2400+nr*64;
    if(wait_bits(c,io,as+0x28,1,0))return -63;
    write32(io,as+0x18,cmd);
    return wait_bits(c,io,as+0x28,1,0);
}
int sweet_csf_runtime_bind(const struct sweet_csf_queue_config *c,
    const struct sweet_gpu_io *io,unsigned nr,uint64_t root)
{
    if(!valid(c,io)||!nr||nr>=16||(root&4095)||root>=(UINT64_C(1)<<40)||
       !(read32(io,c->gpu+0x18)&(1u<<nr)))return -60;
    uint64_t as=c->gpu+0x2400+nr*64;
    if(wait_bits(c,io,as+0x28,1,0))return -63;
    write64(io,as,root);write32(io,as+8,SWEET_CSF_VENDOR_MEMATTR_LO);
    write32(io,as+12,SWEET_CSF_VENDOR_MEMATTR_HI);
    write64(io,as+0x30,root?UINT64_C(0x42000006):1);
    return as_cmd(c,io,nr,1);
}
int sweet_csf_runtime_invalidate(const struct sweet_csf_queue_config *c,
    const struct sweet_gpu_io *io,unsigned nr)
{
    if(!valid(c,io)||!nr||nr>=16)return -60;
    /* All callers serialize with completed GPU work; lock/invalidate the
     * full 48-bit VA space before reusing or releasing physical pages. */
    write64(io,c->gpu+0x2410+nr*64,47);
    if(as_cmd(c,io,nr,2)||as_cmd(c,io,nr,4)||as_cmd(c,io,nr,3))return -63;
    return 0;
}
static void ring_group(const struct sweet_csf_queue_config *c,const struct sweet_gpu_io *io,
    struct sweet_csf_runtime_group *g)
{
    uint64_t gi=iface(c,c->input_va),go=iface(c,c->output_va);
    uint32_t bit=1u<<g->slot;
    write32(io,gi+8,(read32(io,gi+8)&~bit)|((read32(io,go+8)^bit)&bit));
    write32(io,c->gpu+0x80000,1);
}
static void ring(const struct sweet_csf_queue_config *c,const struct sweet_gpu_io *io,
    struct sweet_csf_runtime_group *g)
{
    write32(io,g->input+8,(read32(io,g->input+8)&~1u)|((read32(io,g->output+8)^1u)&1u));
    ring_group(c,io,g);
}
int sweet_csf_runtime_start(const struct sweet_csf_queue_config *c,const struct sweet_gpu_io *io,
    struct sweet_csf_runtime_group *g,unsigned slot,unsigned nr)
{
    if(!g||!valid(c,io)||slot>=SWEET_CSF_GROUPS||!nr||nr>=16||
       !iface(c,c->input_va)||!iface(c,c->output_va))return -60;
    if(g->active||g->failed)return -62;
    uint32_t groups=read32(io,c->shared_pa+16),stride=read32(io,c->shared_pa+20);
    if(slot>=groups||stride<0x50||stride>512||(stride&3))return -61;
    uint64_t ctrl=c->shared_pa+0x1000+slot*stride;
    uint64_t in=iface(c,read32(io,ctrl+4)),out=iface(c,read32(io,ctrl+8));
    uint64_t ci=iface(c,read32(io,ctrl+0x44)),co=iface(c,read32(io,ctrl+0x48));
    if(!in||!out||!ci||!co||read32(io,ctrl+12)>0x8000||
       !read32(io,ctrl+12)||(read32(io,out)&7))return -61;
    *g=(struct sweet_csf_runtime_group){.input=in,.output=out,.cs_input=ci,.cs_output=co,
        .memory_pa=c->memory_pa+slot*SWEET_CSF_GROUP_BYTES,
        .memory_va=SWEET_CSF_QUEUE_VA+slot*SWEET_CSF_GROUP_BYTES,.slot=slot,.as_nr=nr};
    uint64_t mem=g->memory_pa,va=g->memory_va;
    for(unsigned i=0;i<SWEET_CSF_GROUP_BYTES;i+=4)write32(io,mem+i,0);
    write64(io,ci+0x10,va);write32(io,ci+0x18,4096);
    write64(io,ci+0x30,va+0x1000);write64(io,ci+0x38,va+0x2000);
    write32(io,ci+4,((slot+1)<<8)|15u);write32(io,ci+12,UINT32_MAX);
    write32(io,ci,(read32(io,ci)&~0x517u)|0x511u);
    uint64_t cores=read64(io,c->gpu+0x100);unsigned count=0;
    for(uint64_t n=cores;n;n>>=1)count+=n&1;
    write64(io,in+0x20,cores);write64(io,in+0x28,cores);
    write32(io,in+0x30,read32(io,c->gpu+0x110));
    write32(io,in+0x34,0xf0010000|(count<<8)|count);
    write64(io,in+0x40,va+0x8000);write64(io,in+0x48,0);
    write32(io,in+0x50,nr);write32(io,in+4,UINT32_MAX);
    uint32_t req=(read32(io,in)&~0x17u)|((read32(io,out)^0x10)&0x10)|1u;
    write32(io,in,req);g->active=1;ring(c,io,g);
    if(wait_bits(c,io,out,0x17,req&0x17)||wait_bits(c,io,co,7,1)) {
        g->failed=1;return -63;
    }
    return 0;
}
int sweet_csf_runtime_submit(const struct sweet_csf_queue_config *c,const struct sweet_gpu_io *io,
    struct sweet_csf_runtime_group *g,uint64_t stream,uint32_t bytes,struct sweet_csf_queue_report *r)
{
    if(!r)return -60;
    *r=(struct sweet_csf_queue_report){.stage=1};
    if(!valid(c,io)||!g||!g->active||g->failed||!bytes||(bytes&7)||
       bytes>(16u<<20)||(stream&7)||stream>=(UINT64_C(1)<<48)-bytes||
       g->sequence==UINT32_MAX){r->error=-60;return -60;}
    if(read64(io,g->memory_pa+0x2000)!=g->insert){r->error=-62;return -62;}
    uint32_t seq=++g->sequence;
    uint64_t commands[16]={
        UINT64_C(0x025e000000000000),UINT64_C(0x24005e0000000233),
        UINT64_C(0x0300000000010000),UINT64_C(0x015c000000000000)|stream,
        UINT64_C(0x025e000000000000)|bytes,UINT64_C(0x20005c5e00000000),
        UINT64_C(0x0300000000ff0000),UINT64_C(0x025e000000000000),
        UINT64_C(0x24005e0000000211),UINT64_C(0x0300000000010000),
        UINT64_C(0x015c000000000000)|(g->memory_va+0x3000),
        UINT64_C(0x025e000000000000)|seq,UINT64_C(0x26005c5e00000000),
        UINT64_C(0x0300000000010000),0,0};
    r->before=read32(io,g->memory_pa+0x3000);
    uint64_t pos=g->insert&4095;
    for(unsigned i=0;i<16;i++)write64(io,g->memory_pa+pos+i*8,commands[i]);
    g->insert+=sizeof(commands);r->insert=(uint32_t)g->insert;
    write64(io,g->memory_pa+0x1000,g->insert);
    /* The global doorbell processes interface requests. New ring contents
     * need the user doorbell selected in CS_CONFIG, as in Panthor's
     * queue_submit: an unchanged CS_REQ does not wake an idle stream. */
    write32(io,c->gpu+0x80000+(uint64_t)(g->slot+1)*0x10000,1);
    r->stage=4;
    uint64_t start=io->ticks(io->context),budget=io->frequency*c->timeout_ms/1000;
    r->error=-63;
    for(unsigned i=0;i<10000000;i++) {
        io->barrier(io->context);r->polls++;
        r->csg_req=read32(io,g->input);r->csg_ack=read32(io,g->output);
        r->cs_req=read32(io,g->cs_input);r->cs_ack=read32(io,g->cs_output);
        uint64_t extract=read64(io,g->memory_pa+0x2000);
        r->extract=(uint32_t)extract;
        r->after=read32(io,g->memory_pa+0x3000);
        r->fault=read32(io,g->cs_output+0x80);r->fatal=read32(io,g->cs_output+0x84);
        r->mmu_raw=read32(io,c->gpu+0x2000);r->as_fault=read32(io,c->gpu+0x241c+g->as_nr*64);
        r->cmd_lo=read32(io,g->cs_output+0x40);r->cmd_hi=read32(io,g->cs_output+0x44);
        if(r->fault||r->fatal||(r->mmu_raw&0xffff)||r->as_fault||read32(io,g->memory_pa+0x3004)) {
            r->error=-64;break;
        }
        if(r->after==seq&&extract==g->insert) {
            r->stage=7;r->error=0;break;
        }
        if(io->ticks(io->context)-start>=budget)break;
    }
    if(r->error)g->failed=1;
    return r->error;
}
int sweet_csf_runtime_stop(const struct sweet_csf_queue_config *c,const struct sweet_gpu_io *io,
    struct sweet_csf_runtime_group *g)
{
    if(!valid(c,io)||!g)return -60;
    if(!g->active)return 0;
    /* Terminate the group first, as Panthor does. A standalone CS STOP
     * can wait on resources retained by another live group. CSG TERMINATE
     * is the lifetime barrier for its queue memory; reset the CS request
     * only after that acknowledgement, with no separate CS wait. Its old
     * ACK may survive until the next CSG START. */
    write32(io,g->input,read32(io,g->input)&~7u);ring_group(c,io,g);
    if(wait_bits(c,io,g->output,7,0)){g->failed=1;return -63;}
    write32(io,g->cs_input,read32(io,g->cs_input)&~7u);
    g->active=0;return 0;
}
