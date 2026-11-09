"""Execute the real surface-import routine with descriptor/lifetime mocks."""
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


class SurfaceImportTests(unittest.TestCase):
    def test_owned_uncached_backing_and_handle_lifetime(self):
        source = (ROOT / 'xnu/gpu/SweetGPUVM.h').read_text()
        function = source[source.index('static IOReturn gpu_surface('):source.index('static IOReturn gpu_vm_map(')]
        prelude = r'''
#include <cassert>
#include <cstdint>
#include <cstdio>
#include "sweet_gpu_user.h"
using IOReturn = int;
enum { kIOReturnSuccess, kIOReturnNotReady, kIOReturnBadArgument,
       kIOReturnNotFound, kIOReturnUnsupported, kIOReturnNoResources };
#define GPU_MAX_BO 4
#define kIOMapWriteCombineCache 2
#define IOLog(...) ((void)0)
#define OSDynamicCast(T,p) dynamic_cast<T *>(p)
struct IOMemoryDescriptor {
    int refs=1; uint64_t length=262144;
    virtual ~IOMemoryDescriptor()=default;
    uint64_t getLength(){return length;}
    void retain(){refs++;} void release(){assert(refs>0);refs--;}
};
struct IOBufferMemoryDescriptor: IOMemoryDescriptor {};
struct SweetSurface {
    int refs=1; uint32_t id=99,width=256,height=256,bytesPerRow=1024,
        offset=0,pixelFormat='BGRA',planeCount=0,bytesPerElement=4,mapCache=2;
    bool memoryReadOnly=false; IOMemoryDescriptor *memory;
    void retain(){refs++;} void release(){assert(refs>0);refs--;}
};
static IOBufferMemoryDescriptor backing;
static IOMemoryDescriptor borrowed;
static SweetSurface surface;
static SweetSurface *sweet_surface_copy(uint32_t id) {
    if(id!=surface.id)return nullptr;surface.retain();return &surface;
}
struct GPUBuffer { IOMemoryDescriptor *memory; SweetSurface *surface;uint64_t size; };
struct GPUVM {bool broken;GPUBuffer bo[GPU_MAX_BO];};
'''
        checks = r'''
int main() {
    surface.memory=&backing;GPUVM vm={};
    sweet_gpu_surface r={99,0};assert(gpu_surface(&vm,&r)==0&&r.handle==0&&r.size==262144);
    assert(surface.refs==1&&backing.refs==1&&!vm.bo[0].memory);
    r={99,UINT32_MAX};assert(!gpu_surface(&vm,&r)&&r.handle==1);
    assert(surface.refs==2&&backing.refs==2&&vm.bo[0].surface==&surface);
    r={99,UINT32_MAX};assert(!gpu_surface(&vm,&r)&&r.handle==1&&surface.refs==2);
    auto reject=[&](int status){r={99,UINT32_MAX};assert(gpu_surface(&vm,&r)==status);assert(surface.refs==2);};
    surface.mapCache=0;reject(kIOReturnUnsupported);surface.mapCache=2;
    surface.memory=&borrowed;reject(kIOReturnUnsupported);surface.memory=&backing;
    surface.memoryReadOnly=true;reject(kIOReturnUnsupported);surface.memoryReadOnly=false;
    surface.offset=64;reject(kIOReturnUnsupported);surface.offset=0;
    surface.bytesPerRow=1000;reject(kIOReturnUnsupported);surface.bytesPerRow=1024;
    surface.pixelFormat=0;reject(kIOReturnUnsupported);surface.pixelFormat='BGRA';
    surface.planeCount=1;reject(kIOReturnUnsupported);surface.planeCount=0;
    backing.length=262143;reject(kIOReturnUnsupported);backing.length=262144;
    vm.broken=true;reject(kIOReturnNotReady);vm.broken=false;
    r={100,UINT32_MAX};assert(gpu_surface(&vm,&r)==kIOReturnNotFound);
    r={99,1};assert(gpu_surface(&vm,&r)==kIOReturnBadArgument);
    vm.bo[0].memory->release();vm.bo[0].surface->release();vm.bo[0]={};
    assert(surface.refs==1&&backing.refs==1);
    r={99,UINT32_MAX};assert(!gpu_surface(&vm,&r)&&r.handle==1);
    vm.bo[0].memory->release();vm.bo[0].surface->release();
    assert(surface.refs==1&&backing.refs==1);
}
'''
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)
            (p / 'test.cpp').write_text(prelude + function + checks)
            subprocess.run(['clang++', '-std=c++14', '-O1', '-g',
                            '-fsanitize=address,undefined', '-I', str(ROOT / 'xnu/gpu'),
                            str(p / 'test.cpp'), '-o', str(p / 'test')], check=True)
            subprocess.run([str(p / 'test')], check=True)


if __name__ == '__main__':
    unittest.main()
