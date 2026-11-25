#!/usr/bin/env python3
"""Check the actual early splash renderer, timer bounds and BMP conversion."""
import argparse
import ctypes as C
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import struct
import subprocess
import sys

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('source', type=Path)
    ap.add_argument('--output', required=True, type=Path)
    args = ap.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    directory = args.source / 'osfmk/arm64'
    header = directory / 'whyred_splash.h'
    image = directory / 'whyred_splash_image.h'
    early = (directory / 'sweet_early.c').read_text()
    # Guard the integration point independently of the renderer's math.
    relocate = early[early.index('sweet_early_relocate(uint64_t base)'):]
    assert relocate.index('early_fb =') < relocate.index('whyred_early_splash();') < relocate.index('sweet_early_mark(9,')
    assert 'PE_parse_boot_argn("whyred-splash"' in early
    assert 'frequency * 3' in header.read_text()
    wrapper = args.output / 'splash-wrapper.c'
    wrapper.write_text('''#include <stdint.h>
#include "whyred_splash.h"
#include "whyred_splash_image.h"
#ifdef _WIN32
#define EX __declspec(dllexport)
#else
#define EX
#endif
EX int draw(uint32_t *fb,uint64_t bytes,uint32_t w,uint32_t h,uint32_t stride,
            const uint16_t *p,uint64_t count) {
    return whyred_splash_draw(fb,bytes,w,h,stride,p,count);
}
EX int image_draw(uint32_t *fb,uint64_t bytes,uint32_t stride) {
    return whyred_splash_draw(fb,bytes,WHYRED_SPLASH_WIDTH,WHYRED_SPLASH_HEIGHT,
        stride,whyred_splash_rgb565,sizeof(whyred_splash_rgb565)/2);
}
EX uint16_t image_pixel(uint32_t index) { return whyred_splash_rgb565[index]; }
EX int waiting(uint64_t start,uint64_t now,uint64_t hz) {
    return whyred_splash_waiting(start,now,hz);
}
''')
    library = args.output / ('splash.dll' if os.name == 'nt' else 'splash.so')
    env = os.environ.copy()
    env.pop('SDKROOT', None)
    cc = env.get('CC') or shutil.which('clang') or 'cc'
    cmd = [cc, '-std=c11', '-Wall', '-Wextra', '-Werror', '-O1', '-ffreestanding',
           '-fno-stack-protector', '-shared', '-I', str(directory.resolve()),
           str(wrapper.resolve()), '-o', str(library.resolve())]
    if os.name == 'nt':
        cmd += ['-nostdlib', '-fuse-ld=lld', '-Wl,/noentry', '-Wl,/nodefaultlib']
    else:
        cmd += ['-fPIC']
        if sys.platform == 'darwin':
            sdk = subprocess.check_output(['xcrun', '--sdk', 'macosx', '--show-sdk-path'], text=True, env=env).strip()
            cmd += ['-isysroot', sdk]
    subprocess.run(cmd, check=True, env=env)
    lib = C.CDLL(str(library.resolve()))
    lib.draw.argtypes = [C.POINTER(C.c_uint32), C.c_uint64, C.c_uint32, C.c_uint32,
                         C.c_uint32, C.POINTER(C.c_uint16), C.c_uint64]
    lib.image_draw.argtypes = [C.POINTER(C.c_uint32), C.c_uint64, C.c_uint32]
    lib.image_pixel.argtypes = [C.c_uint32]
    lib.image_pixel.restype = C.c_uint16
    lib.waiting.argtypes = [C.c_uint64, C.c_uint64, C.c_uint64]
    checks = 0
    def check(condition):
        nonlocal checks
        checks += 1
        if not condition:
            raise SystemExit('Splash host check failed: ' + str(checks))
    def expanded(p):
        r,g,b=(p>>11)&31,(p>>5)&63,p&31
        return 0xff000000|(((r<<3)|(r>>2))<<16)|(((g<<2)|(g>>4))<<8)|((b<<3)|(b>>2))
    values = (C.c_uint16 * 6)(0xf800,0x07e0,0x001f,0xffff,0x0000,0x1234)
    guarded = (C.c_uint32 * 16)(*[0xa5a5a5a5]*16)
    fb = C.cast(C.byref(guarded, 4), C.POINTER(C.c_uint32))
    check(lib.draw(fb, 11*4, 3, 2, 8, values, 6) == 1)
    for y in range(2):
        for x in range(3): check(fb[y*8+x] == expanded(values[y*3+x]))
    check(guarded[0] == guarded[-1] == 0xa5a5a5a5)
    for x in range(3,8): check(fb[x] == 0xa5a5a5a5)
    for byte_count,w,h,stride,count in [(40,3,2,8,6),(44,3,2,2,6),(44,3,2,8,5),
            (44,0,2,8,6),(44,3,0,8,6),(44,0xffffffff,0xffffffff,0xffffffff,0xffffffffffffffff)]:
        before = bytes(guarded)
        check(lib.draw(fb,byte_count,w,h,stride,values,count) == 0)
        check(bytes(guarded) == before)
    check(lib.draw(None,44,3,2,8,values,6) == 0)
    check(lib.draw(fb,44,3,2,8,None,6) == 0)
    for start in (0,100,0xffffffffff000000):
        hz=19200000
        check(lib.waiting(start,start+3*hz-1,hz) == 1)
        check(lib.waiting(start,start+3*hz,hz) == 0)
        check(lib.waiting(start,start+3*hz+1,hz) == 0)
    check(lib.waiting(0,0,0) == 0)
    check(lib.waiting(0,0,1000000001) == 0)
    stride=1084
    full=(C.c_uint32 * (stride*2160+32))(*([0xa5a5a5a5]*(stride*2160+32)))
    check(lib.image_draw(full,stride*2160*4,stride) == 1)
    for y in range(2160):
        for x in (0,17,539,1079): check(full[y*stride+x] == expanded(lib.image_pixel(y*1080+x)))
        check(all(full[y*stride+x] == 0xa5a5a5a5 for x in range(1080,stride)))
    check(all(v == 0xa5a5a5a5 for v in full[stride*2160:]))
    spec=importlib.util.spec_from_file_location('splash_maker',Path(__file__).with_name('make-whyred-splash.py'))
    maker=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(maker)
    width,height=1080,2160
    bmp=bytearray(54+width*height*3)
    struct.pack_into('<2sIHHI',bmp,0,b'BM',len(bmp),0,0,54)
    struct.pack_into('<IiiHHII',bmp,14,40,width,-height,1,24,0,width*height*3)
    bmp[54:57]=b'\x00\x00\xff';bmp[-3:]=b'\xff\x00\x00'
    _,_,raw=maker.read_bmp(bmp)
    check(raw[:2] == b'\x00\xf8' and raw[-2:] == b'\x1f\x00')
    struct.pack_into('<i',bmp,22,height)
    _,_,raw=maker.read_bmp(bmp)
    check(raw[(height-1)*width*2:(height-1)*width*2+2] == b'\x00\xf8')
    for corrupt in ('truncated','overlap','width','bpp','compression'):
        bad=bytearray(bmp)
        if corrupt=='truncated': bad=bad[:-1]
        if corrupt=='overlap': struct.pack_into('<I',bad,10,10)
        if corrupt=='width': struct.pack_into('<i',bad,18,0x7fffffff)
        if corrupt=='bpp': struct.pack_into('<H',bad,28,16)
        if corrupt=='compression': struct.pack_into('<I',bad,30,1)
        try: maker.read_bmp(bad)
        except ValueError: check(True)
        else: check(False)
    report=dict(passed=True,checks=checks,actual_kernel_renderer=True,hardware_tested=False,
                hold_ms=3000,source_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest()
                    for p in (header,image,directory/'sweet_early.c')})
    (args.output/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    print('PASS:',checks,'splash conversion/render/timer checks; hardware display pending')

if __name__ == '__main__': main()
