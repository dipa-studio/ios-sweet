"""Compile the actual Darwin transport against a deterministic IOKit endpoint.

The pinned Mesa header tree is an external fixture, as for compiler ISA tests.
"""
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
MESA = ROOT / 'research/matisse/20261109-panfrost/mesa-25.0.7'
MOCK = r'''
#include <stdint.h>
#include <stddef.h>
typedef uint32_t io_connect_t,io_service_t,kern_return_t;
typedef uint64_t mach_vm_address_t,mach_vm_size_t;
#define kIOReturnNoMemory 1
#define kIOReturnBadArgument 2
#define kIOReturnNotFound 3
#define kIOReturnTimeout 4
#define kIOReturnBusy 5
#define kIOReturnUnsupported 6
#define kIOMapAnywhere 1
void *IOServiceMatching(const char *);
io_service_t IOServiceGetMatchingService(unsigned,void *);
kern_return_t IOServiceOpen(io_service_t,unsigned,unsigned,io_connect_t *);
kern_return_t IOObjectRelease(unsigned);
kern_return_t IOServiceClose(unsigned);
unsigned mach_task_self(void);
kern_return_t IOConnectCallStructMethod(unsigned,unsigned,const void *,size_t,void *,size_t *);
kern_return_t IOConnectMapMemory64(unsigned,unsigned,unsigned,mach_vm_address_t *,mach_vm_size_t *,unsigned);
kern_return_t IOConnectUnmapMemory64(unsigned,unsigned,unsigned,mach_vm_address_t);
'''
HARNESS = r'''
#include <assert.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>
#include <IOKit/IOKitLib.h>
#include "xf86drm.h"
#include "drm-uapi/panthor_drm.h"
#include "sweet_gpu_user.h"
static unsigned submitted,fail_submit,created,nextbo=1;
void *IOServiceMatching(const char *n){assert(!strcmp(n,"SweetGPU"));return (void *)1;}
io_service_t IOServiceGetMatchingService(unsigned a,void*b){(void)a;(void)b;return 1;}
kern_return_t IOServiceOpen(io_service_t a,unsigned b,unsigned c,io_connect_t *out){(void)a;(void)b;(void)c;*out=1;return 0;}
kern_return_t IOObjectRelease(unsigned a){(void)a;return 0;}
kern_return_t IOServiceClose(unsigned a){(void)a;return 0;}
unsigned mach_task_self(void){return 1;}
kern_return_t IOConnectCallStructMethod(unsigned c,unsigned s,const void *in,size_t n,void *out,size_t *size){
 (void)c;
 if(s==SWEET_GPU_INFO){assert(!in&&!n&&*size==sizeof(struct sweet_gpu_info));struct sweet_gpu_info *r=out;
  memset(r,0,*size);r->version=1;r->gpu[0]=0xa8620004;r->cs[2]=96;r->cs[3]=8;return 0;}
 assert(in&&out&&n==*size);
 if(s==SWEET_GPU_BO_CREATE){struct sweet_gpu_bo*r=out;r->handle=nextbo++;r->size=(r->size+16383)&~16383ull;created++;}
 else if(s==SWEET_GPU_GROUP_CREATE)((struct sweet_gpu_group*)out)->handle=1;
 else if(s==SWEET_GPU_SUBMIT){submitted++;if(fail_submit)return 7;((struct sweet_gpu_submit*)out)->sequence=submitted;}
 return 0;
}
kern_return_t IOConnectMapMemory64(unsigned a,unsigned b,unsigned c,mach_vm_address_t *p,mach_vm_size_t*s,unsigned f){
 (void)a;(void)b;(void)c;(void)f;*p=(uintptr_t)calloc(1,*s);return *p?0:1;}
kern_return_t IOConnectUnmapMemory64(unsigned a,unsigned b,unsigned c,mach_vm_address_t p){(void)a;(void)b;(void)c;free((void*)(uintptr_t)p);return 0;}
int main(void){
 int fd=drmOpenWithType("panthor",NULL,2);assert(fd>=0);
 drmVersionPtr v=drmGetVersion(fd);assert(!strcmp(v->name,"panthor")&&v->version_major==1);drmFreeVersion(v);
 struct drm_panthor_gpu_info gpu={0};struct drm_panthor_dev_query q={.type=0,.size=sizeof(gpu),.pointer=(uintptr_t)&gpu};
 assert(!drmIoctl(fd,DRM_IOCTL_PANTHOR_DEV_QUERY,&q)&&gpu.gpu_id==0xa8620004);
 uint32_t fence;assert(!drmSyncobjCreate(fd,0,&fence));
 assert(drmSyncobjWait(fd,&fence,1,0,0,NULL)<0&&errno==ETIME);
 struct drm_panthor_sync_op op={.flags=DRM_PANTHOR_SYNC_OP_SIGNAL|DRM_PANTHOR_SYNC_OP_HANDLE_TYPE_TIMELINE_SYNCOBJ,.handle=fence,.timeline_value=7};
 struct drm_panthor_queue_submit queue={.stream_addr=0x10000000,.stream_size=32,.syncs=DRM_PANTHOR_OBJ_ARRAY(1,&op)};
 struct drm_panthor_group_submit group={.group_handle=1,.queue_submits=DRM_PANTHOR_OBJ_ARRAY(1,&queue)};
 assert(!drmIoctl(fd,DRM_IOCTL_PANTHOR_GROUP_SUBMIT,&group)&&submitted==1);
 uint64_t point=7;assert(!drmSyncobjTimelineWait(fd,&fence,&point,1,0,0,NULL));
 point=8;assert(drmSyncobjTimelineWait(fd,&fence,&point,1,0,0,NULL)<0);
 fail_submit=1;op.timeline_value=8;assert(drmIoctl(fd,DRM_IOCTL_PANTHOR_GROUP_SUBMIT,&group)<0);
 assert(submitted==2&&drmSyncobjTimelineWait(fd,&fence,&point,1,0,0,NULL)<0);
 assert(!drmSyncobjReset(fd,&fence,1)&&drmSyncobjWait(fd,&fence,1,0,0,NULL)<0);
 op.flags=DRM_PANTHOR_SYNC_OP_HANDLE_TYPE_TIMELINE_SYNCOBJ;
 assert(drmIoctl(fd,DRM_IOCTL_PANTHOR_GROUP_SUBMIT,&group)<0&&submitted==2);
 struct drm_panthor_bo_create bo={.size=1};assert(!drmIoctl(fd,DRM_IOCTL_PANTHOR_BO_CREATE,&bo)&&bo.size==16384&&bo.handle==1);
 void*p=redwood_drm_map(fd,bo.handle,bo.size);assert(p&&p!=(void*)-1);assert(redwood_drm_map(fd,bo.handle,bo.size)==p);
 redwood_drm_unmap(fd,bo.handle,p);redwood_drm_unmap(fd,bo.handle,p);assert(!drmCloseBufferHandle(fd,bo.handle));
 struct drm_panthor_tiler_heap_create heap={.vm_id=1,.initial_chunk_count=2,.max_chunks=2,.chunk_size=131072};
 assert(!drmIoctl(fd,DRM_IOCTL_PANTHOR_TILER_HEAP_CREATE,&heap)&&heap.handle&&created==4);
 assert(heap.tiler_heap_ctx_gpu_va>heap.first_heap_chunk_gpu_va);
 struct drm_panthor_tiler_heap_destroy destroy={.handle=heap.handle};assert(!drmIoctl(fd,DRM_IOCTL_PANTHOR_TILER_HEAP_DESTROY,&destroy));
 return 0;
}
'''


class PanthorTransportTests(unittest.TestCase):
    @unittest.skipUnless(MESA.exists(), 'requires pinned Mesa header fixture')
    def test_fences_follow_hardware_and_buffers_use_iokit(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d);(p / 'IOKit').mkdir()
            (p / 'IOKit/IOKitLib.h').write_text(MOCK)
            (p / 'test.c').write_text(HARNESS)
            subprocess.run(['clang', '-std=c11', '-O1', '-g', '-fsanitize=address,undefined',
                            '-I', str(p), '-I', str(MESA / 'src/redwood-drm'),
                            '-I', str(MESA / 'include'), '-I', str(ROOT / 'xnu/gpu'),
                            str(p / 'test.c'), str(ROOT / 'userland/sweet-panthor-drm.c'),
                            '-o', str(p / 'test')], check=True)
            subprocess.run([str(p / 'test')], check=True)


if __name__ == '__main__':
    unittest.main()
