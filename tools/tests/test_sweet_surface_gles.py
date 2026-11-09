"""Execute patched IOSurface geometry and pinning with host sanitizers."""
from pathlib import Path
import re
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
REL = 'iokit/Kernel/arm/SweetSurface.cpp'


def source():
    with tempfile.TemporaryDirectory() as d:
        for n in ('0046-sweet-iosurface-iomfb.patch', '0068-sweet-surface-lookup-cached.patch',
                  '0206-sweet-gles-iosurface-layout-and-wrapping.patch'):
            subprocess.run(['git', 'apply', '--include=' + REL, '-'], cwd=d, check=True,
                           input=(ROOT / 'xnu/patches' / n).read_text(), text=True, capture_output=True)
        return (Path(d) / REL).read_text()


def function(text, name):
    m = re.search(r'static [^\n]+\n' + name + r'\(', text)
    assert m, name
    return text[m.start():text.index('\n}', m.end()) + 2]


class SurfaceTests(unittest.TestCase):
    def test_real_layout_result_and_pin(self):
        src = source()
        helpers = '\n'.join(function(src, n) for n in ('sweet_dict_u32', 'sweet_div_up',
            'sweet_row_bytes', 'sweet_surface_layout', 'put32', 'put64',
            'sweet_surface_fill_result', 'sweet_surface_pin'))
        code = r'''
#include <cassert>
#include <cstdint>
#include <cstring>
#include <map>
#include <string>
#include <vector>
using IOReturn=int; using task_t=int;
enum {kIOReturnSuccess=0,kIOReturnBadArgument=1,kIOReturnUnsupported=2,
 kIOReturnNoMemory=3,kIOReturnVMError=4,kIODirectionInOut=5,kIODirectionOut=6,kIOMapDefaultCache=0};
#define SWEET_SURFACE_MAX_DIM 16384
#define SWEET_SURFACE_MAX_PLANES 20
#define SWEET_SURFACE_MAX_ALLOC (256u<<20)
#define SWEET_SURFACE_ROW_ALIGN 64
#define SWEET_SURFACE_RESULT_SIZE 0xa68
#define SWEET_SURFACE_TIMESTAMPS 0x800
#define round_page(x) (((x)+16383)&~16383ULL)
#define OSDynamicCast(T,v) dynamic_cast<T*>(v)
struct OSObject {virtual ~OSObject() {}};
struct OSNumber: OSObject {uint64_t n;OSNumber(uint64_t x):n(x){} uint32_t unsigned32BitValue(){return n;}};
struct OSDictionary: OSObject {std::map<std::string,OSObject*> v;OSObject*getObject(const char*k){return v[k];}};
struct OSArray: OSObject {std::vector<OSObject*> v;unsigned getCount(){return v.size();}OSObject*getObject(unsigned i){return v[i];}};
struct Mapping {uint64_t address;uint64_t getAddress(){return address;}};
static unsigned pins,releases,fail_pins;
struct IOMemoryDescriptor {
 static IOMemoryDescriptor*withAddressRange(uint64_t address,uint32_t size,int direction,int task){
  assert(address==0x100001 && size==40 && task==7);
  assert(direction==(pins==0?kIODirectionInOut:kIODirectionOut));return new IOMemoryDescriptor;
 }
 int prepare(){return ++pins<=fail_pins?kIOReturnVMError:kIOReturnSuccess;}
 void release(){++releases;delete this;}
};
struct sweet_surface_plane {uint32_t width,height,bytesPerRow,offset,size;uint16_t bytesPerElement;uint8_t elementWidth,elementHeight;};
struct SweetSurface {
 uint32_t id,width,height,bytesPerRow,offset,pixelFormat,allocSize;
 uint16_t bytesPerElement;uint8_t elementWidth,elementHeight;uint32_t cacheMode,planeCount,parentID;
 sweet_surface_plane planes[20];bool memoryPrepared,memoryReadOnly;IOMemoryDescriptor*memory;int mapCache;
};
struct SweetSurfaceRef {Mapping*data,*state;};
static uint32_t sweet_surface_gles;
''' + helpers + r'''
int main(){
 OSNumber w(1440),h(3200),fmt('b3a8'),bpe(4),row(5760),alloc(23150592);
 OSDictionary props;props.v={{"IOSurfaceWidth",&w},{"IOSurfaceHeight",&h},{"IOSurfacePixelFormat",&fmt},
  {"IOSurfaceBytesPerElement",&bpe},{"IOSurfaceBytesPerRow",&row},{"IOSurfaceAllocSize",&alloc}};
 OSDictionary plane0,plane1;OSArray planes;planes.v={&plane0,&plane1};props.v["IOSurfacePlaneInfo"]=&planes;
 SweetSurface s={};assert(sweet_surface_layout(&s,&props)==0 && s.pixelFormat=='b3a8' && s.planeCount==2);
 sweet_surface_gles=1;s={};assert(sweet_surface_layout(&s,&props)==0);
 assert(s.pixelFormat=='BGRA' && s.planeCount==0 && s.width==1440 && s.height==3200);
 assert(s.bytesPerRow==5760 && s.bytesPerElement==4 && s.allocSize==18432000);
 Mapping data{0x1234000},state{0x5678000};SweetSurfaceRef ref{&data,&state};uint8_t out[0xa68];
 sweet_surface_fill_result(&s,&ref,out);uint32_t n;
 memcpy(&n,out+0x30,4);assert(n=='BGRA');memcpy(&n,out+0x38,4);assert(n==0);
 memcpy(&n,out+0x68+0x10,4);assert(n==5760);memcpy(&n,out+0x68,4);assert(n==1440);
 s.planeCount=2;s.planes[1]={10,20,128,4096,2560,4,1,1};sweet_surface_fill_result(&s,&ref,out);
 memcpy(&n,out+0x68+0x80+0x10,4);assert(n==128);memcpy(&n,out+0x68+0x80+0x0c,4);assert(n==4096);
 row.n=5759;assert(sweet_surface_layout(&s,&props)==kIOReturnBadArgument);row.n=5760;
 OSNumber address(0x100001);props.v["IOSurfaceAddress"]=&address;s={};
 assert(sweet_surface_layout(&s,&props)==0 && s.pixelFormat=='b3a8' && s.planeCount==2);
 props.v.erase("IOSurfacePlaneInfo");fmt.n='BGRA';w.n=5;h.n=2;row.n=20;alloc.n=40;s={};
 assert(sweet_surface_layout(&s,&props)==0 && s.allocSize==40);
 alloc.n=39;assert(sweet_surface_layout(&s,&props)==kIOReturnBadArgument);alloc.n=40;
 props.v["IOSurfaceAddressRanges"]=&planes;assert(sweet_surface_layout(&s,&props)==kIOReturnUnsupported);
 for(unsigned fail=0;fail<3;fail++){
  s={};s.allocSize=40;pins=releases=0;fail_pins=fail;int result=sweet_surface_pin(&s,0x100001,7);
  if(fail<2){assert(result==0 && s.memoryPrepared && s.memoryReadOnly==(fail==1));s.memory->release();}
  else {assert(result==kIOReturnVMError && !s.memoryPrepared && s.memory==nullptr);}
  assert(pins==releases);
 }
 pins=0;s.allocSize=40;assert(sweet_surface_pin(&s,0,7)==kIOReturnBadArgument);
 assert(sweet_surface_pin(&s,UINT64_MAX-1,7)==kIOReturnBadArgument && pins==0);
}
'''
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'test.cpp'; p.write_text(code); binary = p.with_suffix('')
            result = subprocess.run(['c++', '-std=c++17', '-Wall', '-Wextra', '-Werror',
                '-Wno-multichar', '-fsanitize=address,undefined', str(p), '-o', str(binary)],
                text=True, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            result = subprocess.run([str(binary)], text=True, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == '__main__':
    unittest.main()
