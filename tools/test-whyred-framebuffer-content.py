#!/usr/bin/env python3
"""Execute the exact framebuffer content scanner on guarded visible images."""
import argparse
import ctypes as C
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

BGRA, RGBA = 0x42475241, 0x52474241

class Image(C.Structure):
    _fields_ = [('pixels',C.POINTER(C.c_uint8)),('length',C.c_uint64),
                ('width',C.c_uint32),('height',C.c_uint32),('row_bytes',C.c_uint32),
                ('offset',C.c_uint32),('format',C.c_uint32)]

class Content(C.Structure):
    _fields_ = [(x,C.c_uint64) for x in ('pixels','rgb_pixels','alpha_pixels')]+[
                (x,C.c_uint32) for x in ('min_x','min_y','max_x','max_y')]

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('source',type=Path)
    ap.add_argument('--output',required=True,type=Path)
    args=ap.parse_args()
    args.output.mkdir(parents=True,exist_ok=True)
    header=args.source/'iokit/Kernel/arm/SweetFramebufferBlit.h'
    wrapper=args.output/'content-wrapper.c'
    wrapper.write_text('#include "SweetFramebufferBlit.h"\n'
        '#ifdef _WIN32\n__declspec(dllexport)\n#endif\n'
        'void measure(const struct sweet_fb_image *i, struct sweet_fb_content *o) '
        '{ *o = sweet_fb_measure(i); }\n'
        '#ifdef _WIN32\n__declspec(dllexport)\n#endif\n'
        'int inspect(uint64_t n) { return sweet_fb_should_inspect(n); }\n'
        '#ifdef _WIN32\n__declspec(dllexport)\n#endif\n'
        'int mute_console(int inspected, uint64_t rgb) '
        '{ return sweet_fb_should_mute_console(inspected, rgb); }\n',encoding='utf8')
    library=args.output/('content.dll' if sys.platform=='win32' else 'content.so')
    cc=os.environ.get('CC') or shutil.which('clang') or 'cc'
    command=[cc,'-std=c11','-O2','-ffreestanding','-fno-stack-protector','-shared',
             '-I',str(header.parent.resolve()),str(wrapper.resolve()),'-o',str(library.resolve())]
    env=os.environ.copy()
    env.pop('SDKROOT',None)
    env.pop('MACOSX_DEPLOYMENT_TARGET',None)
    if sys.platform=='win32':
        command+=['-nostdlib','-fuse-ld=lld','-Wl,/noentry','-Wl,/nodefaultlib']
    else:
        command+=['-fPIC']
        if sys.platform=='darwin':
            sdk=subprocess.check_output(['xcrun','--sdk','macosx','--show-sdk-path'],text=True,env=env).strip()
            command+=['-isysroot',sdk]
    subprocess.run(command,check=True,env=env)
    lib=C.CDLL(str(library.resolve()))
    measure=lib.measure
    measure.argtypes=[C.POINTER(Image),C.POINTER(Content)]
    measure.restype=None
    names=[]

    def check(name,points=(),fmt=BGRA,short=False,stride_bad=False,null=False,width=7):
        w,h,stride,offset=width,5,40,16
        data=bytearray([0xA5]*(offset+stride*h+64))
        for y in range(h):
            data[offset+y*stride:offset+y*stride+w*4]=bytes(w*4)
        for x,y,pixel in points:
            data[offset+y*stride+x*4:offset+y*stride+x*4+4]=bytes(pixel)
        original=bytes(data)
        backing=(C.c_uint8*len(data)).from_buffer(data)
        length=offset+(h-1)*stride+w*4-(1 if short else 0)
        image=Image(C.POINTER(C.c_uint8)() if null else backing,length,w,h,
                    1 if stride_bad else stride,offset,fmt)
        result=Content()
        measure(C.byref(image),C.byref(result))
        actual=tuple(getattr(result,key) for key,_ in Content._fields_)
        valid=not(short or stride_bad or null) and fmt in (BGRA,RGBA) and w>0
        if valid:
            rgb=[(x,y) for x,y,p in points if any(p[:3])]
            alpha=sum(p[3]!=0 for _,_,p in points)
            bbox=(min(x for x,y in rgb),min(y for x,y in rgb),
                  max(x for x,y in rgb)+1,max(y for x,y in rgb)+1) if rgb else (0,0,0,0)
            expected=(w*h,len(rgb),alpha,*bbox)
        else:
            expected=(0,)*7
        assert actual==expected,(name,actual,expected)
        assert bytes(data)==original,(name,'source/guard modified')
        names.append(name)

    check('zero visible image ignores nonzero padding and allocation tails')
    check('black RGB with opaque alpha',points=[(x,y,(0,0,0,255)) for y in range(5) for x in range(7)])
    check('content missed by first and center samples',points=[(1,1,(19,0,0,255))])
    check('RGB count, alpha count and exclusive bounding box',points=[(6,4,(0,4,0,0)),(0,2,(0,0,8,255)),(5,1,(0,0,0,123))])
    check('RGBA geometry and nonzero offset',points=[(2,3,(33,22,11,255))],fmt=RGBA)
    check('zero alpha does not hide nonblack RGB',points=[(3,2,(10,0,0,0))])
    check('short mapping rejected',short=True)
    check('invalid row stride rejected',stride_bad=True)
    check('unsupported planar format rejected',fmt=0x34323066)
    check('null mapping rejected',null=True)
    check('empty image rejected',width=0)
    lib.inspect.argtypes=[C.c_uint64]
    lib.inspect.restype=C.c_int
    actual=[n for n in range(1001) if lib.inspect(n)]
    assert actual==list(range(1,9))+[300,600,900],actual
    assert lib.inspect(2**64-1)==0
    lib.mute_console.argtypes=[C.c_int,C.c_uint64]
    lib.mute_console.restype=C.c_int
    mute_cases=[(0,0,0),(0,12,0),(1,0,0),(1,1,1),(1,2332800,1)]
    for inspected,rgb,want in mute_cases:
        assert lib.mute_console(inspected,rgb)==want,(inspected,rgb,want)
    names.append('console waits for nonblack source content')
    glue=(args.source/'iokit/Kernel/arm/SweetFramebuffer.cpp').read_text()
    assert 'sweet_fb_should_inspect(++fPresentAttempts)' in glue
    assert 'fPresentAttempts = 0;' in glue
    assert glue.index('sweet_fb_should_inspect(++fPresentAttempts)') < glue.index('if (pixels == 0)')
    assert 'sweet_fb_should_mute_console(inspect, source_rgb_pixels)' in glue
    assert glue.index('sweet_fb_should_mute_console(inspect, source_rgb_pixels)') > glue.index('source_rgb_pixels += content.rgb_pixels;')
    names.append('failed presentations consume the diagnostic budget')
    report={'checks':len(names),'cases':names,'actual_kernel_scanner':True,
            'header_sha256':hashlib.sha256(header.read_bytes()).hexdigest(),
            'hardware_scene_tested':False}
    (args.output/'report.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf8')
    print('PASS: %d guarded framebuffer-content checks'%len(names))

if __name__=='__main__':
    main()
