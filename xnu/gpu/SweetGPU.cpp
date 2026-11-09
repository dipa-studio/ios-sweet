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
vm_offset_t ml_io_map(vm_offset_t, vm_size_t);
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
    IOReturn clientClose(void) APPLE_KEXT_OVERRIDE;
    IOReturn externalMethod(uint32_t,IOExternalMethodArguments *,IOExternalMethodDispatch *,OSObject *,void *) APPLE_KEXT_OVERRIDE;
};
OSDefineMetaClassAndStructors(SweetGPUUserClient,IOUserClient);
IOReturn SweetGPUUserClient::clientClose(void){terminate();return kIOReturnSuccess;}
IOReturn SweetGPUUserClient::externalMethod(uint32_t selector,IOExternalMethodArguments *a,
    IOExternalMethodDispatch *,OSObject *,void *)
{
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
        if(!a->structureOutput||a->structureOutputSize<sizeof(last_report))return kIOReturnBadArgument;
        int rc=submit_compute((struct sweet_csf_queue_report *)a->structureOutput);
        a->structureOutputSize=sizeof(last_report);
        return rc?kIOReturnIOError:kIOReturnSuccess;
    }
    return kIOReturnUnsupported;
}

static void resident_worker(void *arg,wait_result_t)
{
    IOService *provider=(IOService *)arg;
    for(unsigned i=0;i<3;i++) {
        if(submit_compute())break;
        IOSleep(20);
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
