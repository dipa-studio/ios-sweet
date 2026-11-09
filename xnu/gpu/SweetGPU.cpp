/* SPDX-License-Identifier: MIT
 * Resident MT6983 CSF owner. The loader transfers its exclusive power
 * reference and reserved firmware arena; no firmware is loaded from disk. */
#include <pexpert/arm64/board_config.h>
#if defined(SWEET)
#include <IOKit/IOService.h>
#include <IOKit/IOUserClient.h>
#include <IOKit/IOKitKeys.h>
#include <IOKit/IOLib.h>
#include <pexpert/pexpert.h>
#include <pexpert/device_tree.h>
#include <kern/thread.h>
extern "C" {
#include "../../../bsd/dev/sweet_gpu_handoff.h"
#include "../../../bsd/dev/mali_csf_queue.h"
#include "../../../bsd/dev/mali_csf_runtime.h"
vm_offset_t ml_io_map(vm_offset_t, vm_size_t);
int sweet_gpu_log_ready(void);
int sweet_gpu_log_flush(void);
}

static struct sweet_gpu_handoff handoff;
static struct sweet_csf_queue_config queue;
static vm_offset_t gpu_map, arena_map;
static IOLock *gpu_lock;
static uint32_t ready, submits, failures;
static struct sweet_csf_queue_report last_report;

static volatile uint32_t *address(uint64_t pa)
{
    if(pa>=handoff.gpu && pa-handoff.gpu<0x90000)
        return (volatile uint32_t *)(gpu_map+pa-handoff.gpu);
    if(pa>=handoff.arena_pa && pa-handoff.arena_pa<handoff.arena_bytes)
        return (volatile uint32_t *)(arena_map+pa-handoff.arena_pa);
    panic("SweetGPU: unmapped physical access");
}
static uint32_t read_word(void *,uint64_t pa){return *address(pa);}
static void write_word(void *,uint64_t pa,uint32_t v){*address(pa)=v;}
static void barrier(void *){__asm__ volatile("dsb sy" ::: "memory");}
static uint64_t ticks(void *)
{uint64_t t;__asm__ volatile("isb; mrs %0,cntpct_el0":"=r"(t));return t;}
static struct sweet_gpu_io gpu_io;
static uint32_t gpu_trace;
static void gpu_checkpoint(const char *phase,uint64_t a=0,uint64_t b=0)
{
    if(!gpu_trace)return;
    IOLog("SWEET GPU: checkpoint %s a=%llx b=%llx\n",phase,a,b);
    int rc=sweet_gpu_log_flush();
    if(rc)IOLog("SWEET GPU: checkpoint flush failed rc=%d\n",rc);
}
#include "SweetGPUVM.h"

static int submit_compute(struct sweet_csf_queue_report *report=NULL)
{
    IOLockLock(gpu_lock);
    int rc=ready?sweet_csf_queue_probe(&queue,&gpu_io,&last_report):-62;
    submits++;
    if(rc){failures++;ready=0;}
    IOLog("SWEET GPU: resident submit=%u rc=%d stage=%u tag=%08x extract=%u/%u csg=%x cs=%x mmu=%x as=%x stop=%x\n",
        submits,rc,last_report.stage,last_report.after,last_report.extract,
        last_report.insert,last_report.csg_ack,last_report.cs_ack,last_report.mmu_raw,
        last_report.as_fault,last_report.stop_ack);
    if(report)memcpy(report,&last_report,sizeof(*report));
    IOLockUnlock(gpu_lock);
    return rc;
}

class SweetGPU : public IOService {
    OSDeclareDefaultStructors(SweetGPU);
public:
    bool start(IOService *provider) APPLE_KEXT_OVERRIDE;
};
OSDefineMetaClassAndStructors(SweetGPU,IOService);
bool SweetGPU::start(IOService *provider)
{
    if(!IOService::start(provider))return false;
    setName("SweetGPU");setProperty(kIOUserClientClassKey,"SweetGPUUserClient");
    setProperty("CSFVersion",(unsigned long long)1,32);
    registerService();return true;
}
class SweetGPUUserClient : public IOUserClient {
    OSDeclareDefaultStructors(SweetGPUUserClient);
public:
    GPUVM *vm;
    bool start(IOService *) APPLE_KEXT_OVERRIDE;
    void free(void) APPLE_KEXT_OVERRIDE;
    IOReturn clientMemoryForType(UInt32,IOOptionBits *,IOMemoryDescriptor **) APPLE_KEXT_OVERRIDE;
    IOReturn clientClose(void) APPLE_KEXT_OVERRIDE;
    IOReturn externalMethod(uint32_t,IOExternalMethodArguments *,IOExternalMethodDispatch *,OSObject *,void *) APPLE_KEXT_OVERRIDE;
};
OSDefineMetaClassAndStructors(SweetGPUUserClient,IOUserClient);
bool SweetGPUUserClient::start(IOService *provider)
{
    vm=NULL;if(!IOUserClient::start(provider))return false;
    IOLockLock(gpu_lock);if(ready)vm=gpu_vm_create();IOLockUnlock(gpu_lock);
    IOLog("SWEET GPU: user client open AS=%u\n",vm?vm->as_nr:0);
    return vm&&!vm->broken;
}
void SweetGPUUserClient::free(void)
{
    IOLockLock(gpu_lock);gpu_vm_destroy(vm);vm=NULL;IOLockUnlock(gpu_lock);IOUserClient::free();
}
IOReturn SweetGPUUserClient::clientMemoryForType(UInt32 type,IOOptionBits *options,IOMemoryDescriptor **memory)
{
    IOLockLock(gpu_lock);GPUBuffer *b=gpu_bo(vm,type);IOReturn rc=kIOReturnNotFound;
    if(b&&!(b->flags&1)) {*memory=b->memory;(*memory)->retain();*options=kIOMapWriteCombineCache;rc=kIOReturnSuccess;}
    IOLockUnlock(gpu_lock);return rc;
}
IOReturn SweetGPUUserClient::clientClose(void){terminate();return kIOReturnSuccess;}
IOReturn SweetGPUUserClient::externalMethod(uint32_t selector,IOExternalMethodArguments *a,
    IOExternalMethodDispatch *,OSObject *,void *)
{
    if(selector>=SWEET_GPU_INFO&&selector<=SWEET_GPU_SUBMIT) {
        if(!vm||!a||a->scalarInputCount||a->structureInputDescriptor||a->structureOutputDescriptor)
            return kIOReturnBadArgument;
        if(selector==SWEET_GPU_INFO) {
            if(a->structureInputSize||!a->structureOutput||a->structureOutputSize<sizeof(sweet_gpu_info))
                return kIOReturnBadArgument;
            sweet_gpu_info info={};info.version=1;
            const unsigned off[]={0,0x280,0x1c,4,0xc,0x10,0x14,0xac,0xa0,0xa4,0xa8,0x300,
                0xb0,0xb4,0xb8,0xbc,0x18,0,0x100,0x104,0x120,0x124,0x110,0x114,8,0};
            IOLockLock(gpu_lock);
            for(unsigned i=0;i<26;i++)if(i!=17&&i!=25)info.gpu[i]=read_word(NULL,handoff.gpu+off[i]);
            uint32_t cs=read_word(NULL,handoff.shared_pa+0x1040);
            info.cs[0]=SWEET_CSF_GROUPS;info.cs[1]=1;info.cs[2]=(cs&255)+1;
            info.cs[3]=(cs>>8)&255;info.cs[4]=4;
            IOLockUnlock(gpu_lock);
            memcpy(a->structureOutput,&info,sizeof(info));a->structureOutputSize=sizeof(info);return kIOReturnSuccess;
        }
        union {sweet_gpu_bo bo;sweet_gpu_map map;sweet_gpu_group group;sweet_gpu_submit submit;} r;
        size_t size=selector==SWEET_GPU_VM_MAP?sizeof(r.map):selector==SWEET_GPU_SUBMIT?sizeof(r.submit):
            (selector==SWEET_GPU_BO_CREATE?sizeof(r.bo):sizeof(r.group));
        if(!a->structureInput||a->structureInputSize!=size||!a->structureOutput||a->structureOutputSize<size)
            return kIOReturnBadArgument;
        memcpy(&r,a->structureInput,size);IOLockLock(gpu_lock);
        IOReturn rc=kIOReturnUnsupported;
        switch(selector) {
        case SWEET_GPU_BO_CREATE:rc=gpu_bo_create(vm,&r.bo);break;
        case SWEET_GPU_BO_CLOSE:rc=gpu_bo_close(vm,r.group.handle);break;
        case SWEET_GPU_VM_MAP:rc=gpu_vm_map(vm,&r.map);break;
        case SWEET_GPU_GROUP_CREATE:rc=gpu_group_create(vm,&r.group);break;
        case SWEET_GPU_GROUP_CLOSE:rc=gpu_group_close(vm,r.group.handle);break;
        case SWEET_GPU_SUBMIT:rc=gpu_submit(vm,&r.submit);break;
        }
        memcpy(a->structureOutput,&r,size);a->structureOutputSize=size;IOLockUnlock(gpu_lock);return rc;
    }
    if(!a||a->scalarInputCount||a->structureInputSize||a->structureInputDescriptor)
        return kIOReturnBadArgument;
    if(selector==0) {
        if(a->scalarOutputCount<4||!a->scalarOutput)return kIOReturnBadArgument;
        IOLockLock(gpu_lock);
        a->scalarOutput[0]=1;a->scalarOutput[1]=ready;
        a->scalarOutput[2]=submits;a->scalarOutput[3]=failures;
        a->scalarOutputCount=4;IOLockUnlock(gpu_lock);return kIOReturnSuccess;
    }
    if(selector==1) {
        /* The old diagnostic owns AS1 and all scratch memory. Once clients
         * have VMs, it cannot run alongside their persistent groups. */
        return kIOReturnUnsupported;
    }
    return kIOReturnUnsupported;
}

static bool resident_vm_test(void)
{
    /* Real allocated BOs and a root with no firmware mappings. Rebind the
     * SAME VA to another BO halfway through, and wrap the ring twice. */
    gpu_checkpoint("VM test begin");
    GPUVM *v=gpu_vm_create();if(!v||v->broken){gpu_vm_destroy(v);return false;}
    gpu_checkpoint("VM root ready",v->pt[0].pa,v->as_nr);
    sweet_gpu_bo bo[2]={{0x10000,0,0},{0x10000,0,0}};
    sweet_gpu_group group={};bool ok=true;
    for(unsigned i=0;i<2;i++)if(gpu_bo_create(v,&bo[i])!=kIOReturnSuccess)ok=false;
    const uint64_t va=0x10000000;
    sweet_gpu_map map={bo[0].handle,0,0,va,0x10000};
    if(ok&&gpu_vm_map(v,&map)!=kIOReturnSuccess)ok=false;
    gpu_checkpoint("VM BO map",ok);
    if(ok&&gpu_group_create(v,&group)!=kIOReturnSuccess)ok=false;
    unsigned completed=0;
    for(unsigned i=0;i<70&&ok;i++) {
        if(i==35) {
            map.flags=1u<<28;if(gpu_vm_map(v,&map)!=kIOReturnSuccess){ok=false;break;}
            map.flags=0;map.handle=bo[1].handle;
            if(gpu_vm_map(v,&map)!=kIOReturnSuccess){ok=false;break;}
        }
        IOBufferMemoryDescriptor *m=OSDynamicCast(IOBufferMemoryDescriptor,gpu_bo(v,map.handle)->memory);
        volatile uint64_t *p=(volatile uint64_t *)m->getBytesNoCopy();
        uint32_t tag=0x24380000+i;
        p[0x4000/8]=UINT64_C(0x0110c000000000c0)|((va+0x3000)<<8);
        p[0x4008/8]=UINT64_C(0x0110c100000000c0);
        p[0x4010/8]=UINT64_C(0x0110c200000000c0)|((uint64_t)tag<<8);
        p[0x4018/8]=UINT64_C(0x7861420218000040);
        p[0x5000/8]=0x80000018;p[0x5008/8]=va+0x4000;p[0x6000/8]=31ull<<32;
        p[0x3000/8]=0xdeadbeef;
        const uint64_t init[]={
            UINT64_C(0x2200000000000001),UINT64_C(0x1700000000000002),
            UINT64_C(0x0100000000000000),UINT64_C(0x0108000000000000),
            UINT64_C(0x0110000000000000)|(va+0x5000),UINT64_C(0x0118000000000000)|(va+0x6000),
            UINT64_C(0x0220000000000000),UINT64_C(0x0221000000000000),
            UINT64_C(0x0222000000000000),UINT64_C(0x0223000000000000),
            UINT64_C(0x0224000000000000),UINT64_C(0x0225000000000001),
            UINT64_C(0x0226000000000001),UINT64_C(0x0227000000000001),
            UINT64_C(0x0400000000008001),UINT64_C(0x0300000000ff0000),
            UINT64_C(0x2200000000000000)};
        const uint64_t again[]={UINT64_C(0x2200000000000001),UINT64_C(0x0400000000008001),
            UINT64_C(0x0300000000ff0000),UINT64_C(0x2200000000000000)};
        const uint64_t *words=i?again:init;unsigned count=i?4:17;
        for(unsigned k=0;k<count;k++)p[k]=words[k];barrier(NULL);
        sweet_gpu_submit s={group.handle,count*8,va,0};
        ok=gpu_submit(v,&s)==kIOReturnSuccess&&p[0x3000/8]==tag;
        if(ok)completed++;
        else IOLog("SWEET GPU: VM test failed i=%u actual=%llx expected=%x\n",i,p[0x3000/8],tag);
    }
    IOLog("SWEET GPU: VM test completed=%u/70 root=%llx firmware_root=%llx tables=%u remap=%u ring_wraps=%u\n",
        completed,v->pt[0].pa,handoff.root_pa,v->tables,completed>35,completed/32);
    if(group.handle&&gpu_group_close(v,group.handle)!=kIOReturnSuccess)ok=false;
    gpu_vm_destroy(v);return ok;
}

static void resident_worker(void *arg,wait_result_t)
{
    IOService *provider=(IOService *)arg;
    for(unsigned i=0;i<3;i++) {
        if(submit_compute())break;
        IOSleep(20);
    }
    /* Normal boots expose the driver after the proven resident probe.
     * The destructive-to-VM stress test is an explicit diagnostic mode;
     * service discovery must not depend on the persistent-log worker. */
    uint32_t selftest=0;
    PE_parse_boot_argn("sweetgpuvmtest",&selftest,sizeof(selftest));
    if(selftest) {
        while(ready&&!sweet_gpu_log_ready())IOSleep(100);
        gpu_checkpoint("persistent logging ready");
        IOLockLock(gpu_lock);
        gpu_checkpoint("VM lock acquired");
        if(ready&&!resident_vm_test()){ready=0;IOLog("SWEET GPU: VM selftest failed\n");}
        IOLockUnlock(gpu_lock);
    }
    if(ready) {
        SweetGPU *gpu=OSTypeAlloc(SweetGPU);
        if(gpu&&gpu->init()&&gpu->attach(provider)&&gpu->start(provider))
            IOLog("SWEET GPU: resident service ready; MCU retained, three compute submissions passed\n");
        else IOLog("SWEET GPU: service registration failed\n");
        OSSafeReleaseNULL(gpu);
    }
    provider->release();
    for(;;) {
        IOSleep(15000);
        IOLog("SWEET GPU: resident status ready=%u submits=%u failures=%u MCU=%x\n",
            ready,submits,failures,read_word(NULL,handoff.gpu+0x704));
    }
}

extern "C" void SweetGPUStart(IOService *provider)
{
    DTEntry chosen;const void *raw=NULL;unsigned int bytes=0;
    uint32_t enabled=0;PE_parse_boot_argn("sweetgpu",&enabled,sizeof(enabled));
    PE_parse_boot_argn("sweetgputrace",&gpu_trace,sizeof(gpu_trace));
    if(!enabled||SecureDTLookupEntry(NULL,"/chosen",&chosen)!=kSuccess||
       SecureDTGetProperty(chosen,"sweet-gpu-resident",&raw,&bytes)!=kSuccess||
       bytes!=sizeof(handoff))return;
    memcpy(&handoff,raw,sizeof(handoff));
    if(handoff.magic!=SWEET_GPU_HANDOFF_MAGIC||handoff.version!=1||handoff.bytes!=128||
       handoff.flags!=1||handoff.gpu!=0x13000000||handoff.arena_bytes!=(2u<<20)||
       handoff.arena_pa<0x40000000||handoff.arena_pa>0x47e00000||
       handoff.root_pa!=handoff.arena_pa||handoff.shared_pa<handoff.arena_pa||
       handoff.shared_bytes>handoff.arena_bytes||
       handoff.shared_pa-handoff.arena_pa>handoff.arena_bytes-handoff.shared_bytes||
       handoff.memory_bytes!=SWEET_CSF_QUEUE_BYTES||handoff.memory_pa<handoff.arena_pa||
       handoff.memory_pa-handoff.arena_pa>handoff.arena_bytes-handoff.memory_bytes) {
        IOLog("SWEET GPU: invalid resident handoff\n");return;
    }
    gpu_map=ml_io_map(handoff.gpu,0x90000);
    arena_map=ml_io_map(handoff.arena_pa,handoff.arena_bytes);
    gpu_lock=IOLockAlloc();
    if(!gpu_map||!arena_map||!gpu_lock){IOLog("SWEET GPU: mapping failed\n");return;}
    queue.gpu=handoff.gpu;queue.root_pa=handoff.root_pa;queue.shared_pa=handoff.shared_pa;
    queue.memory_pa=handoff.memory_pa;queue.shared_va=handoff.shared_va;
    queue.shared_bytes=handoff.shared_bytes;queue.input_va=handoff.input_va;
    queue.output_va=handoff.output_va;queue.memory_bytes=handoff.memory_bytes;
    queue.timeout_ms=1000;queue.reuse_as1=1;
    gpu_io.context=NULL;gpu_io.read32=read_word;gpu_io.write32=write_word;
    gpu_io.barrier=barrier;gpu_io.ticks=ticks;
    __asm__ volatile("mrs %0,cntfrq_el0":"=r"(gpu_io.frequency));
    ready=read_word(NULL,handoff.gpu+0x704)==1;
    IOLog("SWEET GPU: adopting MCU=%u GPU=%08x reserved arena=%llx\n",ready,
        read_word(NULL,handoff.gpu),handoff.arena_pa);
    if(!ready)return;
    thread_t thread;provider->retain();
    if(kernel_thread_start(resident_worker,provider,&thread)==KERN_SUCCESS)thread_deallocate(thread);
    else {provider->release();ready=0;IOLog("SWEET GPU: worker failed\n");}
}
#endif
