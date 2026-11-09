/* SPDX-License-Identifier: MIT
 * Mesa Panthor ABI over SweetGPU's Darwin IOUserClient. Hardware submission
 * is synchronous; timeline values become signalled only after its GPU-written
 * fence completes. No JM ioctls, software renderer or fabricated completion. */
#include <IOKit/IOKitLib.h>
#include <pthread.h>
#include <sys/mman.h>
#include <errno.h>
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <time.h>
#include "xf86drm.h"
#include "drm-uapi/panthor_drm.h"
#include "sweet_gpu_user.h"

#define OBJECTS 4096u
#define HEAPS 64u
static pthread_mutex_t lock=PTHREAD_MUTEX_INITIALIZER;
static pthread_cond_t changed=PTHREAD_COND_INITIALIZER;
static io_connect_t connection;
static int device=-1,failed;
static struct sweet_gpu_info info;
_Static_assert(sizeof(info.gpu)==sizeof(struct drm_panthor_gpu_info),"GPU info ABI");
_Static_assert(sizeof(info.cs)==sizeof(struct drm_panthor_csif_info),"CSIF info ABI");
static struct {uint64_t point;unsigned used,signalled;} syncs[OBJECTS];
static struct {mach_vm_address_t address;mach_vm_size_t size;unsigned refs;} maps[OBJECTS];
static struct {unsigned count;uint32_t bo[65];} heaps[HEAPS];
static uint64_t heap_va=UINT64_C(1)<<47;
static unsigned vm_alive;
static int error(int e){errno=e;return -1;}
static int call(unsigned selector,void *r,size_t size)
{
    size_t returned=size;
    kern_return_t rc=IOConnectCallStructMethod(connection,selector,r,size,r,&returned);
    if(!rc&&returned==size)return 0;
    int e=rc==kIOReturnNoMemory?ENOMEM:rc==kIOReturnBadArgument?EINVAL:
        rc==kIOReturnNotFound?ENOENT:rc==kIOReturnTimeout?ETIMEDOUT:
        rc==kIOReturnBusy?EBUSY:rc==kIOReturnUnsupported?ENOTSUP:EIO;
    fprintf(stderr,"SweetGPU call=%u rc=%x\n",selector,rc);return error(e);
}
int drmOpenWithType(const char *name,const char *busid,int type)
{
    (void)busid;(void)type;
    if(strcmp(name,"panthor")&&strcmp(name,"panfrost"))return error(ENODEV);
    pthread_mutex_lock(&lock);
    if(device<0) {
        io_service_t service=IOServiceGetMatchingService(0,IOServiceMatching("SweetGPU"));
        if(!service){pthread_mutex_unlock(&lock);return error(ENODEV);}
        kern_return_t rc=IOServiceOpen(service,mach_task_self(),0,&connection);IOObjectRelease(service);
        size_t size=sizeof(info);
        if(!rc)rc=IOConnectCallStructMethod(connection,SWEET_GPU_INFO,NULL,0,&info,&size);
        if(rc||size!=sizeof(info)||info.version!=1||info.gpu[0]>>28!=10) {
            if(connection)IOServiceClose(connection);connection=0;
            pthread_mutex_unlock(&lock);return error(ENODEV);
        }
        device=open("/dev/null",O_RDWR|O_CLOEXEC);
        fprintf(stderr,"SweetGPU Panthor: GPU=%08x regs=%u scoreboards=%u\n",info.gpu[0],info.cs[2],info.cs[3]);
    }
    int fd=device>=0?dup(device):-1;pthread_mutex_unlock(&lock);return fd;
}
drmVersionPtr drmGetVersion(int fd)
{
    (void)fd;drmVersionPtr v=calloc(1,sizeof(*v));if(!v)return NULL;
    v->version_major=1;v->name=strdup("panthor");v->name_len=7;return v;
}
void drmFreeVersion(drmVersionPtr v){if(v){free(v->name);free(v->date);free(v->desc);free(v);}}
int drmGetCap(int fd,uint64_t cap,uint64_t *value)
{(void)fd;*value=cap==DRM_CAP_SYNCOBJ||cap==DRM_CAP_SYNCOBJ_TIMELINE;return 0;}
static int signalled(uint32_t handle,uint64_t point)
{return handle&&handle<OBJECTS&&syncs[handle].used&&syncs[handle].signalled&&syncs[handle].point>=point;}
static int sync_ops(struct drm_panthor_obj_array a,int signal)
{
    if(a.count&&!a.array)return error(EINVAL);
    if(a.count>OBJECTS||(a.count&&a.stride!=sizeof(struct drm_panthor_sync_op)))return error(EINVAL);
    for(unsigned i=0;i<a.count;i++) {
        const struct drm_panthor_sync_op *s=(const void *)(uintptr_t)(a.array+(uint64_t)a.stride*i);
        if(((s->flags>>31)!=0)!=signal)continue;
        if(!s->handle||s->handle>=OBJECTS||!syncs[s->handle].used||(s->flags&0x7ffffffeu))return error(EINVAL);
        uint64_t point=(s->flags&1)?s->timeline_value:0;
        if(signal){if(point>syncs[s->handle].point)syncs[s->handle].point=point;syncs[s->handle].signalled=1;}
        else if(!signalled(s->handle,point))return error(ETIME);
    }
    if(signal)pthread_cond_broadcast(&changed);return 0;
}
static void *map_bo(uint32_t handle,uint64_t bytes)
{
    if(!handle||handle>=OBJECTS)return MAP_FAILED;
    if(maps[handle].address){maps[handle].refs++;return (void *)(uintptr_t)maps[handle].address;}
    mach_vm_address_t address=0;mach_vm_size_t size=bytes;
    kern_return_t rc=IOConnectMapMemory64(connection,handle,mach_task_self(),&address,&size,kIOMapAnywhere);
    if(rc||size<bytes)return MAP_FAILED;
    maps[handle].address=address;maps[handle].size=size;maps[handle].refs=1;return (void *)(uintptr_t)address;
}
static void unmap_bo(uint32_t handle)
{
    if(handle&&handle<OBJECTS&&maps[handle].address&&!--maps[handle].refs) {
        IOConnectUnmapMemory64(connection,handle,mach_task_self(),maps[handle].address);
        memset(&maps[handle],0,sizeof(maps[handle]));
    }
}
static int close_bo(uint32_t handle)
{struct sweet_gpu_group r={handle,0};return call(SWEET_GPU_BO_CLOSE,&r,sizeof(r));}
static int heap_buffer(unsigned h,uint64_t size,uint64_t *va,uint64_t next)
{
    struct sweet_gpu_bo bo={size,0,0};
    if(call(SWEET_GPU_BO_CREATE,&bo,sizeof(bo)))return -1;
    struct sweet_gpu_map map={bo.handle,2,0,heap_va,bo.size};
    heap_va+=bo.size;
    if(call(SWEET_GPU_VM_MAP,&map,sizeof(map))){close_bo(bo.handle);return -1;}
    uint64_t *cpu=map_bo(bo.handle,bo.size);
    if(cpu==MAP_FAILED){close_bo(bo.handle);return error(ENOMEM);}
    cpu[0]=next;__sync_synchronize();unmap_bo(bo.handle);
    heaps[h].bo[heaps[h].count++]=bo.handle;*va=map.va;return 0;
}
static void destroy_heap(unsigned h)
{
    for(unsigned i=0;i<heaps[h].count;i++)close_bo(heaps[h].bo[i]);
    memset(&heaps[h],0,sizeof(heaps[h]));
}
static int ioctl_locked(unsigned long request,void *arg)
{
    if(!connection)return error(ENODEV);
    if(request==DRM_IOCTL_PANTHOR_DEV_QUERY) {
        struct drm_panthor_dev_query *q=arg;void *src=NULL;size_t bytes=0;
        if(q->type==DRM_PANTHOR_DEV_QUERY_GPU_INFO){src=info.gpu;bytes=sizeof(info.gpu);}
        else if(q->type==DRM_PANTHOR_DEV_QUERY_CSIF_INFO){src=info.cs;bytes=sizeof(info.cs);}
        else return error(EINVAL);
        if(q->pointer){if(q->size<bytes)bytes=q->size;memcpy((void *)(uintptr_t)q->pointer,src,bytes);}
        q->size=bytes;return 0;
    }
    if(request==DRM_IOCTL_PANTHOR_VM_CREATE) {
        struct drm_panthor_vm_create *r=arg;
        if(r->flags||vm_alive)return error(EBUSY);
        r->id=1;if(!r->user_va_range)r->user_va_range=UINT64_C(1)<<47;
        if(r->user_va_range>(UINT64_C(1)<<47))return error(EINVAL);
        vm_alive=1;return 0;
    }
    if(request==DRM_IOCTL_PANTHOR_VM_DESTROY){vm_alive=0;return 0;}
    if(request==DRM_IOCTL_PANTHOR_VM_GET_STATE) {
        ((struct drm_panthor_vm_get_state *)arg)->state=failed?DRM_PANTHOR_VM_STATE_UNUSABLE:DRM_PANTHOR_VM_STATE_USABLE;return 0;
    }
    if(request==DRM_IOCTL_PANTHOR_BO_CREATE) {
        struct drm_panthor_bo_create *r=arg;struct sweet_gpu_bo b={r->size,0,r->flags};
        if(r->exclusive_vm_id>1)return error(EINVAL);
        if(call(SWEET_GPU_BO_CREATE,&b,sizeof(b)))return -1;
        r->size=b.size;r->handle=b.handle;return 0;
    }
    if(request==DRM_IOCTL_PANTHOR_BO_MMAP_OFFSET) {
        struct drm_panthor_bo_mmap_offset *r=arg;r->offset=(uint64_t)r->handle<<16;return 0;
    }
    if(request==DRM_IOCTL_GEM_CLOSE)return close_bo(((struct drm_gem_close *)arg)->handle);
    if(request==DRM_IOCTL_PANTHOR_VM_BIND) {
        struct drm_panthor_vm_bind *r=arg;
        if(r->vm_id!=1||r->flags>1||r->ops.stride!=sizeof(struct drm_panthor_vm_bind_op)||r->ops.count>4096)return error(EINVAL);
        for(unsigned i=0;i<r->ops.count;i++) {
            struct drm_panthor_vm_bind_op *o=(void *)(uintptr_t)(r->ops.array+(uint64_t)i*r->ops.stride);
            if(sync_ops(o->syncs,0))return -1;
            if((o->flags>>28)!=2) {
                struct sweet_gpu_map m={o->bo_handle,o->flags,o->bo_offset,o->va,o->size};
                if(call(SWEET_GPU_VM_MAP,&m,sizeof(m)))return -1;
            }
            if(sync_ops(o->syncs,1))return -1;
        }
        return 0;
    }
    if(request==DRM_IOCTL_PANTHOR_GROUP_CREATE) {
        struct drm_panthor_group_create *r=arg;struct sweet_gpu_group g={0};
        if(r->vm_id!=1||r->queues.count!=1)return error(ENOTSUP);
        if(call(SWEET_GPU_GROUP_CREATE,&g,sizeof(g)))return -1;
        r->group_handle=g.handle;return 0;
    }
    if(request==DRM_IOCTL_PANTHOR_GROUP_DESTROY) {
        struct drm_panthor_group_destroy *r=arg;struct sweet_gpu_group g={r->group_handle,0};
        return call(SWEET_GPU_GROUP_CLOSE,&g,sizeof(g));
    }
    if(request==DRM_IOCTL_PANTHOR_GROUP_GET_STATE) {
        struct drm_panthor_group_get_state *r=arg;r->state=failed?DRM_PANTHOR_GROUP_STATE_FATAL_FAULT:0;r->fatal_queues=failed?1:0;return 0;
    }
    if(request==DRM_IOCTL_PANTHOR_GROUP_SUBMIT) {
        struct drm_panthor_group_submit *r=arg;
        if(r->queue_submits.stride!=sizeof(struct drm_panthor_queue_submit)||r->queue_submits.count>1024)return error(EINVAL);
        for(unsigned i=0;i<r->queue_submits.count;i++) {
            struct drm_panthor_queue_submit *q=(void *)(uintptr_t)(r->queue_submits.array+(uint64_t)i*r->queue_submits.stride);
            if(q->queue_index||sync_ops(q->syncs,0))return error(EINVAL);
            struct sweet_gpu_submit s={r->group_handle,q->stream_size,q->stream_addr,0};
            if(q->stream_size&&call(SWEET_GPU_SUBMIT,&s,sizeof(s))){failed=1;return -1;}
            if(sync_ops(q->syncs,1))return -1;
        }
        return 0;
    }
    if(request==DRM_IOCTL_PANTHOR_TILER_HEAP_CREATE) {
        struct drm_panthor_tiler_heap_create *r=arg;
        if(r->vm_id!=1||!r->initial_chunk_count||r->initial_chunk_count>64||r->max_chunks<r->initial_chunk_count||
           r->chunk_size<131072||r->chunk_size>8*1024*1024||(r->chunk_size&4095))return error(EINVAL);
        unsigned h=1;while(h<HEAPS&&heaps[h].count)h++;if(h==HEAPS)return error(ENOMEM);
        uint64_t first=0;
        for(unsigned i=0;i<r->initial_chunk_count;i++) {
            uint64_t next=first?(first|(r->chunk_size>>12)):0;
            if(heap_buffer(h,r->chunk_size,&first,next)){destroy_heap(h);return -1;}
        }
        if(heap_buffer(h,16384,&r->tiler_heap_ctx_gpu_va,0)){destroy_heap(h);return -1;}
        r->first_heap_chunk_gpu_va=first;r->handle=h;return 0;
    }
    if(request==DRM_IOCTL_PANTHOR_TILER_HEAP_DESTROY) {
        unsigned h=((struct drm_panthor_tiler_heap_destroy *)arg)->handle;
        if(!h||h>=HEAPS)return error(EINVAL);destroy_heap(h);return 0;
    }
    fprintf(stderr,"SweetGPU unsupported DRM request=%lx\n",request);return error(ENOTSUP);
}
int drmIoctl(int fd,unsigned long request,void *arg)
{(void)fd;pthread_mutex_lock(&lock);int rc=ioctl_locked(request,arg);pthread_mutex_unlock(&lock);return rc;}
int drmCommandWrite(int fd,unsigned long index,const void *data,unsigned long size)
{(void)fd;(void)index;(void)data;(void)size;return error(ENOTSUP);}
int drmCommandWriteRead(int fd,unsigned long index,void *data,unsigned long size)
{return drmCommandWrite(fd,index,data,size);}
void *redwood_drm_map(int fd,uint32_t handle,uint64_t size)
{(void)fd;pthread_mutex_lock(&lock);void *p=map_bo(handle,size);pthread_mutex_unlock(&lock);return p;}
void redwood_drm_unmap(int fd,uint32_t handle,void *p)
{(void)fd;(void)p;pthread_mutex_lock(&lock);unmap_bo(handle);pthread_mutex_unlock(&lock);}
int drmCloseBufferHandle(int fd,uint32_t handle)
{struct drm_gem_close c={handle,0};return drmIoctl(fd,DRM_IOCTL_GEM_CLOSE,&c);}
int drmSyncobjCreate(int fd,uint32_t flags,uint32_t *handle)
{
    (void)fd;pthread_mutex_lock(&lock);unsigned i=1;while(i<OBJECTS&&syncs[i].used)i++;
    if(i==OBJECTS){pthread_mutex_unlock(&lock);return error(ENOMEM);}
    syncs[i].used=1;syncs[i].signalled=!!(flags&DRM_SYNCOBJ_CREATE_SIGNALED);syncs[i].point=0;
    *handle=i;pthread_mutex_unlock(&lock);return 0;
}
int drmSyncobjDestroy(int fd,uint32_t h)
{
    (void)fd;pthread_mutex_lock(&lock);if(!h||h>=OBJECTS){pthread_mutex_unlock(&lock);return error(EINVAL);}
    memset(&syncs[h],0,sizeof(syncs[h]));pthread_mutex_unlock(&lock);return 0;
}
int drmSyncobjReset(int fd,const uint32_t *h,uint32_t n)
{
    (void)fd;pthread_mutex_lock(&lock);
    for(unsigned i=0;i<n;i++)if(!h[i]||h[i]>=OBJECTS||!syncs[h[i]].used){pthread_mutex_unlock(&lock);return error(EINVAL);}
    for(unsigned i=0;i<n;i++){syncs[h[i]].signalled=0;syncs[h[i]].point=0;}
    pthread_mutex_unlock(&lock);return 0;
}
int drmSyncobjTimelineWait(int fd,uint32_t *h,uint64_t *points,unsigned n,int64_t timeout,unsigned flags,uint32_t *first)
{
    (void)fd;if(!n)return error(EINVAL);pthread_mutex_lock(&lock);
    for(;;) {
        unsigned done=0;
        for(unsigned i=0;i<n;i++)if(signalled(h[i],points?points[i]:0)) {
            done++;if(!(flags&DRM_SYNCOBJ_WAIT_FLAGS_WAIT_ALL)){if(first)*first=i;break;}
        }
        if(done&&(!(flags&DRM_SYNCOBJ_WAIT_FLAGS_WAIT_ALL)||done==n)){pthread_mutex_unlock(&lock);return 0;}
        struct timespec now;clock_gettime(CLOCK_MONOTONIC,&now);
        int64_t ns=(int64_t)now.tv_sec*1000000000+now.tv_nsec;
        if(timeout<=ns){pthread_mutex_unlock(&lock);return error(ETIME);}
        int64_t remaining=timeout-ns;if(remaining>1000000000)remaining=1000000000;
        struct timespec rel={remaining/1000000000,remaining%1000000000};
        pthread_cond_timedwait_relative_np(&changed,&lock,&rel);
    }
}
int drmSyncobjWait(int fd,uint32_t *h,unsigned n,int64_t timeout,unsigned flags,uint32_t *first)
{return drmSyncobjTimelineWait(fd,h,NULL,n,timeout,flags,first);}
int drmSyncobjTransfer(int fd,uint32_t dst,uint64_t dp,uint32_t src,uint64_t sp,uint32_t flags)
{
    (void)fd;(void)flags;pthread_mutex_lock(&lock);
    if(!signalled(src,sp)||!dst||dst>=OBJECTS||!syncs[dst].used){pthread_mutex_unlock(&lock);return error(EINVAL);}
    if(dp>syncs[dst].point)syncs[dst].point=dp;syncs[dst].signalled=1;
    pthread_cond_broadcast(&changed);pthread_mutex_unlock(&lock);return 0;
}
/* Shared IOSurface and cross-process fences are a separate transport; never
 * report success for a resource that hasn't been imported or synchronized. */
int drmPrimeHandleToFD(int fd,uint32_t h,uint32_t flags,int *out)
{(void)fd;(void)h;(void)flags;(void)out;return error(ENOTSUP);}
int drmPrimeFDToHandle(int fd,int surface,uint32_t *out)
{(void)fd;(void)surface;(void)out;return error(ENOTSUP);}
int redwood_drm_surface(int fd,struct redwood_drm_surface *s)
{(void)fd;(void)s;return error(ENOTSUP);}
int drmSyncobjFDToHandle(int fd,int object,uint32_t *h)
{(void)fd;(void)object;(void)h;return error(ENOTSUP);}
int drmSyncobjHandleToFD(int fd,uint32_t h,int *object)
{(void)fd;(void)h;(void)object;return error(ENOTSUP);}
int drmSyncobjImportSyncFile(int fd,uint32_t h,int file)
{(void)fd;(void)h;(void)file;return error(ENOTSUP);}
int drmSyncobjExportSyncFile(int fd,uint32_t h,int *file)
{(void)fd;(void)h;(void)file;return error(ENOTSUP);}
