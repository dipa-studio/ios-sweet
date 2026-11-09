/* SPDX-License-Identifier: MIT. Included by the built-in SweetGPU owner. */
#ifndef SWEET_GPU_VM_H
#define SWEET_GPU_VM_H
#include <IOKit/IOBufferMemoryDescriptor.h>
#include <mach/vm_param.h>
#include "SweetSurface.h"
#include "../../../bsd/dev/sweet_gpu_user.h"
#define GPU_MAX_BO 4096u
#define GPU_MAX_PT 1024u
struct GPUBuffer {
    IOMemoryDescriptor *memory;
    SweetSurface *surface;
    uint64_t size, va, mapped, offset;
    uint32_t flags;
};
struct GPUPageTable { IOBufferMemoryDescriptor *memory; uint64_t pa; volatile uint64_t *cpu; };
struct GPUVM {
    GPUBuffer *bo;
    GPUPageTable *pt;
    unsigned tables, as_nr;
    uint64_t allocated;
    bool broken;
    struct sweet_csf_runtime_group groups[SWEET_CSF_GROUPS];
};
static uint32_t gpu_as_used=1,gpu_group_used;
static IOBufferMemoryDescriptor *gpu_buffer_alloc(uint64_t size)
{
    gpu_checkpoint("buffer allocation begin",size);
    IOBufferMemoryDescriptor *m=IOBufferMemoryDescriptor::inTaskWithOptions(kernel_task,
        kIODirectionInOut|kIOMemoryKernelUserShared|kIOMapWriteCombineCache|kIOMemoryMapperNone,size,PAGE_SIZE);
    gpu_checkpoint("buffer allocation returned",size,m!=NULL);
    if(m)bzero(m->getBytesNoCopy(),size);
    gpu_checkpoint("buffer zeroed",size);
    return m;
}
static GPUPageTable *gpu_new_table(GPUVM *v)
{
    if(v->tables>=GPU_MAX_PT)return NULL;
    GPUPageTable *t=&v->pt[v->tables];
    t->memory=gpu_buffer_alloc(PAGE_SIZE);
    if(!t->memory)return NULL;
    gpu_checkpoint("table physical query",v->tables);
    IOByteCount len=0;t->pa=t->memory->getPhysicalSegment(0,&len,kIOMemoryMapperNone);
    gpu_checkpoint("table physical returned",t->pa,len);
    if(!t->pa||(t->pa&4095)||len<4096||t->pa>=(1ull<<40)) {
        OSSafeReleaseNULL(t->memory);return NULL;
    }
    t->cpu=(volatile uint64_t *)t->memory->getBytesNoCopy();v->tables++;return t;
}
static volatile uint64_t *gpu_pte(GPUVM *v,uint64_t va,bool create)
{
    GPUPageTable *table=&v->pt[0];
    for(unsigned level=0;level<3;level++) {
        volatile uint64_t *entry=&table->cpu[(va>>(39-level*9))&511];
        uint64_t descriptor=*entry;
        if(!descriptor) {
            if(!create)return NULL;
            GPUPageTable *next=gpu_new_table(v);if(!next)return NULL;
            barrier(NULL);*entry=next->pa|3;barrier(NULL);table=next;
        } else {
            if((descriptor&3)!=3)return NULL;
            uint64_t pa=descriptor&0x0000fffffffff000ull;
            table=NULL;
            for(unsigned i=1;i<v->tables;i++)if(v->pt[i].pa==pa){table=&v->pt[i];break;}
            if(!table)return NULL;
        }
    }
    return &table->cpu[(va>>12)&511];
}
static bool gpu_map_page(GPUVM *v,uint64_t va,uint64_t pa,uint32_t flags)
{
    if((va&4095)||(pa&4095)||va>=(1ull<<48)||!pa||pa>=(1ull<<40))return false;
    volatile uint64_t *pte=gpu_pte(v,va,true);if(!pte||*pte)return false;
    /* Vendor AttrIdx5 = noncacheable, AF, AP=RW. Execute and RO are explicit. */
    *pte=pa|0x457ull|((flags&1)?0x80:0)|((flags&2)?0x0060000000000000ull:0);
    barrier(NULL);return true;
}
static bool gpu_unmap_pages(GPUVM *v,uint64_t va,uint64_t size)
{
    for(uint64_t n=0;n<size;n+=4096) {
        volatile uint64_t *pte=gpu_pte(v,va+n,false);if(pte)*pte=0;
    }
    barrier(NULL);
    if(sweet_csf_runtime_invalidate(&queue,&gpu_io,v->as_nr)){v->broken=true;return false;}
    return true;
}
static GPUVM *gpu_vm_create(void)
{
    unsigned nr=1;uint32_t present=read_word(NULL,handoff.gpu+0x18);
    while(nr<16&&(!(present&(1u<<nr))||(gpu_as_used&(1u<<nr))))nr++;
    if(nr==16)return NULL;
    gpu_checkpoint("VM metadata allocation begin",nr);
    GPUVM *v=IONewZero(GPUVM,1);if(!v)return NULL;
    gpu_checkpoint("VM object allocated",sizeof(*v));
    v->pt=IONewZero(GPUPageTable,GPU_MAX_PT);v->bo=IONewZero(GPUBuffer,GPU_MAX_BO);
    gpu_checkpoint("VM metadata allocated",v->pt!=NULL,v->bo!=NULL);
    if(!v->pt||!v->bo||!gpu_new_table(v)) {
        if(v->pt)IODelete(v->pt,GPUPageTable,GPU_MAX_PT);
        if(v->bo)IODelete(v->bo,GPUBuffer,GPU_MAX_BO);IODelete(v,GPUVM,1);return NULL;
    }
    v->as_nr=nr;gpu_as_used|=1u<<nr;
    gpu_checkpoint("MMU root bind begin",nr,v->pt[0].pa);
    if(sweet_csf_runtime_bind(&queue,&gpu_io,nr,v->pt[0].pa))v->broken=true;
    gpu_checkpoint("MMU root bind returned",nr,v->broken);
    return v;
}
static GPUBuffer *gpu_bo(GPUVM *v,uint32_t handle)
{return v&&handle&&handle<=GPU_MAX_BO&&v->bo[handle-1].memory?&v->bo[handle-1]:NULL;}
static IOReturn gpu_bo_create(GPUVM *v,struct sweet_gpu_bo *r)
{
    if(v->broken)return kIOReturnNotReady;
    if(!r->size||r->size>(256ull<<20)||r->flags>1)return kIOReturnBadArgument;
    uint64_t size=(r->size+PAGE_SIZE-1)&~(uint64_t)(PAGE_SIZE-1);
    if(size>(1ull<<30)-v->allocated)return kIOReturnNoMemory;
    unsigned i=0;while(i<GPU_MAX_BO&&v->bo[i].memory)i++;
    if(i==GPU_MAX_BO)return kIOReturnNoResources;
    IOBufferMemoryDescriptor *m=gpu_buffer_alloc(size);if(!m)return kIOReturnNoMemory;
    v->bo[i].memory=m;v->bo[i].size=size;v->bo[i].flags=r->flags;v->allocated+=size;
    r->handle=i+1;r->size=size;return kIOReturnSuccess;
}
/* Metadata queries do not create a BO. UINT32_MAX imports the owned,
 * uncached IOSurface backing; repeat imports return the same live handle.
 * Borrowed/cacheable memory stays on the explicit texture upload path. */
static IOReturn gpu_surface(GPUVM *v,struct sweet_gpu_surface *r)
{
    if(v->broken)return kIOReturnNotReady;
    if(!r->surface||(r->handle&&r->handle!=UINT32_MAX))return kIOReturnBadArgument;
    bool import=r->handle==UINT32_MAX;
    SweetSurface *s=sweet_surface_copy(r->surface);
    if(!s)return kIOReturnNotFound;
    uint64_t size=s->memory?s->memory->getLength():0;
    if(!OSDynamicCast(IOBufferMemoryDescriptor,s->memory)||s->memoryReadOnly||
       s->mapCache!=kIOMapWriteCombineCache||s->pixelFormat!='BGRA'||s->planeCount||
       s->bytesPerElement!=4||!s->width||!s->height||s->width>UINT32_MAX/4||
       s->bytesPerRow<s->width*4||(s->bytesPerRow&63)||(s->offset&63)||
       !size||(size&4095)||size>(256ull<<20)||
       s->offset+(uint64_t)s->bytesPerRow*s->height>size) {
        s->release();return kIOReturnUnsupported;
    }
    r->handle=0;r->size=size;r->offset=s->offset;r->row_bytes=s->bytesPerRow;
    r->width=s->width;r->height=s->height;r->pixel_format=s->pixelFormat;r->planes=0;
    if(import) {
        unsigned slot=GPU_MAX_BO;
        for(unsigned i=0;i<GPU_MAX_BO;i++) {
            if(v->bo[i].surface==s){r->handle=i+1;break;}
            if(slot==GPU_MAX_BO&&!v->bo[i].memory)slot=i;
        }
        if(!r->handle) {
            if(slot==GPU_MAX_BO){s->release();return kIOReturnNoResources;}
            GPUBuffer *b=&v->bo[slot];b->memory=s->memory;b->memory->retain();
            b->surface=s;s->retain();b->size=size;r->handle=slot+1;
            static unsigned logged;
            if(logged++<24)IOLog("SWEET GPU: surface import id=%u bo=%u %ux%u stride=%u bytes=%llu NC\n",
                s->id,r->handle,r->width,r->height,r->row_bytes,size);
        }
    }
    s->release();return kIOReturnSuccess;
}
static IOReturn gpu_vm_map(GPUVM *v,struct sweet_gpu_map *r)
{
    if(v->broken)return kIOReturnNotReady;
    if(!r->size||((r->va|r->size|r->offset)&4095)||r->size>(256ull<<20)||
       r->va>=(1ull<<48)-r->size||r->va<0x08000000)return kIOReturnBadArgument;
    if(r->flags==(1u<<28)) {
        for(unsigned i=0;i<GPU_MAX_BO;i++) {
            GPUBuffer *b=&v->bo[i];
            if(b->memory&&b->mapped&&b->va==r->va&&b->mapped==r->size) {
                if(!gpu_unmap_pages(v,b->va,b->mapped))return kIOReturnIOError;
                b->mapped=0;return kIOReturnSuccess;
            }
        }
        return kIOReturnNotFound;
    }
    GPUBuffer *b=gpu_bo(v,r->handle);
    if(!b||(r->flags&~7u)||b->mapped||r->offset>b->size||r->size>b->size-r->offset)
        return kIOReturnBadArgument;
    for(uint64_t n=0;n<r->size;n+=4096) {
        volatile uint64_t *p=gpu_pte(v,r->va+n,false);if(p&&*p)return kIOReturnBusy;
    }
    uint64_t done=0;
    for(;done<r->size;done+=4096) {
        IOByteCount len=0;
        uint64_t pa=b->memory->getPhysicalSegment(r->offset+done,&len,kIOMemoryMapperNone);
        if(len<4096||!gpu_map_page(v,r->va+done,pa,r->flags))break;
    }
    if(done!=r->size){gpu_unmap_pages(v,r->va,done);return kIOReturnNoMemory;}
    b->va=r->va;b->offset=r->offset;b->mapped=r->size;
    if(sweet_csf_runtime_invalidate(&queue,&gpu_io,v->as_nr)){v->broken=true;return kIOReturnIOError;}
    return kIOReturnSuccess;
}
static IOReturn gpu_bo_close(GPUVM *v,uint32_t handle)
{
    GPUBuffer *b=gpu_bo(v,handle);if(!b)return kIOReturnNotFound;
    if(v->broken)return kIOReturnNotReady;
    if(b->mapped&&!gpu_unmap_pages(v,b->va,b->mapped))return kIOReturnIOError;
    if(!b->surface)v->allocated-=b->size;
    OSSafeReleaseNULL(b->memory);OSSafeReleaseNULL(b->surface);bzero(b,sizeof(*b));return kIOReturnSuccess;
}
static IOReturn gpu_group_create(GPUVM *v,struct sweet_gpu_group *r)
{
    if(v->broken)return kIOReturnNotReady;
    unsigned slot=0;while(slot<SWEET_CSF_GROUPS&&(gpu_group_used&(1u<<slot)))slot++;
    if(slot==SWEET_CSF_GROUPS)return kIOReturnNoResources;
    uint64_t va=SWEET_CSF_QUEUE_VA+slot*SWEET_CSF_GROUP_BYTES;
    for(unsigned n=0;n<SWEET_CSF_GROUP_BYTES;n+=4096) {
        if(!gpu_map_page(v,va+n,handoff.memory_pa+slot*SWEET_CSF_GROUP_BYTES+n,2)) {
            gpu_unmap_pages(v,va,n);return kIOReturnNoMemory;
        }
    }
    gpu_group_used|=1u<<slot;
    if(sweet_csf_runtime_invalidate(&queue,&gpu_io,v->as_nr)||
       sweet_csf_runtime_start(&queue,&gpu_io,&v->groups[slot],slot,v->as_nr)) {
        v->broken=true;return kIOReturnIOError;
    }
    r->handle=slot+1;return kIOReturnSuccess;
}
static IOReturn gpu_group_close(GPUVM *v,uint32_t handle)
{
    if(!handle||handle>SWEET_CSF_GROUPS||!v->groups[handle-1].active)return kIOReturnNotFound;
    unsigned slot=handle-1;
    int rc=sweet_csf_runtime_stop(&queue,&gpu_io,&v->groups[slot]);
    IOLog("SWEET GPU: group close as=%u group=%u rc=%d csg=%x/%x cs=%x/%x\n",
        v->as_nr,handle,rc,read_word(NULL,v->groups[slot].input),
        read_word(NULL,v->groups[slot].output),read_word(NULL,v->groups[slot].cs_input),
        read_word(NULL,v->groups[slot].cs_output));
    if(rc){v->broken=true;return kIOReturnIOError;}
    if(!gpu_unmap_pages(v,SWEET_CSF_QUEUE_VA+slot*SWEET_CSF_GROUP_BYTES,SWEET_CSF_GROUP_BYTES))
        return kIOReturnIOError;
    bzero(&v->groups[slot],sizeof(v->groups[slot]));gpu_group_used&=~(1u<<slot);return kIOReturnSuccess;
}
static IOReturn gpu_submit(GPUVM *v,struct sweet_gpu_submit *r)
{
    if(v->broken||!r->group||r->group>SWEET_CSF_GROUPS)return kIOReturnNotReady;
    bool found=false;
    for(unsigned i=0;i<GPU_MAX_BO;i++) {
        GPUBuffer *b=&v->bo[i];
        if(b->memory&&r->stream>=b->va&&r->bytes<=b->mapped&&
           r->stream-b->va<=b->mapped-r->bytes){found=true;break;}
    }
    if(!found)return kIOReturnBadArgument;
    int rc=sweet_csf_runtime_submit(&queue,&gpu_io,&v->groups[r->group-1],r->stream,r->bytes,&last_report);
    submits++;
    if(rc){v->broken=true;failures++;}
    r->sequence=v->groups[r->group-1].sequence;
    if(rc||r->sequence<=3||(r->sequence%100)==0)
        IOLog("SWEET GPU: CSF submit as=%u group=%u seq=%llu rc=%d extract=%u/%u fault=%x fatal=%x mmu=%x addr=%x:%x csg=%x/%x cs=%x/%x asfault=%x fence=%x/%x\n",
            v->as_nr,r->group,r->sequence,rc,last_report.extract,last_report.insert,
            last_report.fault,last_report.fatal,last_report.mmu_raw,last_report.cmd_hi,last_report.cmd_lo,
            last_report.csg_req,last_report.csg_ack,last_report.cs_req,last_report.cs_ack,
            last_report.as_fault,last_report.before,last_report.after);
    return rc?kIOReturnIOError:kIOReturnSuccess;
}
static void gpu_vm_destroy(GPUVM *v)
{
    if(!v)return;
    for(unsigned i=0;i<SWEET_CSF_GROUPS;i++)if(v->groups[i].active) {
        if(gpu_group_close(v,i+1)!=kIOReturnSuccess) {
            /* Timed-out hardware can still DMA. Retain its backing until
             * an implemented reset/recovery path can prove it stopped. */
            IOLog("SWEET GPU: retaining failed VM AS%u until reboot\n",v->as_nr);return;
        }
    }
    if(sweet_csf_runtime_bind(&queue,&gpu_io,v->as_nr,0))return;
    for(unsigned i=0;i<GPU_MAX_BO;i++) {
        OSSafeReleaseNULL(v->bo[i].memory);OSSafeReleaseNULL(v->bo[i].surface);
    }
    for(unsigned i=0;i<v->tables;i++)OSSafeReleaseNULL(v->pt[i].memory);
    gpu_as_used&=~(1u<<v->as_nr);
    IODelete(v->pt,GPUPageTable,GPU_MAX_PT);IODelete(v->bo,GPUBuffer,GPU_MAX_BO);IODelete(v,GPUVM,1);
}
#endif
