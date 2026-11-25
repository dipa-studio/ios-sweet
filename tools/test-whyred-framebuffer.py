#!/usr/bin/env python3
"""Execute the kernel's exact CPU blitter on guarded host buffers."""
import argparse
import ctypes as C
import hashlib
import json
import os
from pathlib import Path
import random
import shutil
import struct
import subprocess
import sys

BGRA, RGBA = 0x42475241, 0x52474241

class Image(C.Structure):
    _fields_ = [('pixels', C.POINTER(C.c_uint8)), ('length', C.c_uint64),
                ('width', C.c_uint32), ('height', C.c_uint32),
                ('row_bytes', C.c_uint32), ('offset', C.c_uint32), ('format', C.c_uint32)]

class Rect(C.Structure):
    _fields_ = [(n, C.c_int32) for n in ('x', 'y', 'w', 'h')]

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('source', type=Path, help='Patched XNU source root')
    ap.add_argument('--output', type=Path, required=True)
    args = ap.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    header = args.source / 'iokit/Kernel/arm/SweetFramebufferBlit.h'
    wrapper = args.output / 'blit-wrapper.c'
    wrapper.write_text('#include "SweetFramebufferBlit.h"\n'
        '#ifdef _WIN32\n__declspec(dllexport)\n#endif\n'
        'uint64_t blit(const struct sweet_fb_image *s, struct sweet_fb_image *d, '
        'uint32_t w, uint32_t h, struct sweet_fb_rect a, struct sweet_fb_rect b) '
        '{ return sweet_fb_blit(s,d,w,h,a,b); }\n', encoding='utf-8')
    cc = os.environ.get('CC') or shutil.which('clang') or 'cc'
    library = args.output / ('blit.dll' if sys.platform == 'win32' else 'blit.so')
    command = [cc, '-std=c11', '-O2', '-ffreestanding', '-fno-stack-protector',
               '-shared', '-I', str(header.parent.resolve()), str(wrapper.resolve()),
               '-o', str(library.resolve())]
    env = os.environ.copy()
    env.pop('SDKROOT', None)
    env.pop('MACOSX_DEPLOYMENT_TARGET', None)
    if sys.platform == 'win32':
        command += ['-nostdlib', '-fuse-ld=lld', '-Wl,/noentry', '-Wl,/nodefaultlib']
    else:
        command += ['-fPIC']
        if sys.platform == 'darwin':
            sdk = subprocess.check_output(['xcrun', '--sdk', 'macosx', '--show-sdk-path'],
                text=True, env=env).strip()
            command += ['-isysroot', sdk]
    subprocess.run(command, check=True, env=env)
    lib = C.CDLL(str(library.resolve()))
    fn = lib.blit
    fn.argtypes = [C.POINTER(Image), C.POINTER(Image), C.c_uint32, C.c_uint32, Rect, Rect]
    fn.restype = C.c_uint64
    checks = []

    def case(name, sw=7, sh=5, pw=7, ph=5, logical=None, sr=None, dr=None,
             fmt=BGRA, short_source=False, short_panel=False, bad_stride=False):
        # Byte offsets and row padding deliberately differ between buffers.
        source_stride, panel_stride, offset = sw*4+12, pw*4+20, 16
        source = bytearray([0xCD]*(offset+source_stride*sh+64))
        for y in range(sh):
            for x in range(sw):
                source[offset+y*source_stride+x*4:offset+y*source_stride+x*4+4] = bytes((x%251, y%251, (x+3*y)%251, 255))
        panel = bytearray([0xA5]*(offset+panel_stride*ph+64))
        expected = panel.copy()
        lw, lh = logical or (pw, ph)
        a = sr or (0, 0, sw, sh)
        b = dr or (0, 0, lw, lh)
        copied = 0
        valid = not(short_source or short_panel or bad_stride) and fmt in (BGRA, RGBA)
        valid &= 0 < a[2] <= 16384 and 0 < a[3] <= 16384 and b[2] > 0 and b[3] > 0
        valid &= 0 < lw <= 16384 and 0 < lh <= 16384
        if valid:
            # Reference visits all physical pixels and maps their centers;
            # it does not use the kernel's clipped destination bounding box.
            for y in range(ph):
                yn = (2*y+1)*lh - b[1]*2*ph
                yd = b[3]*2*ph
                if not 0 <= yn < yd: continue
                sy = a[1] + yn*a[3]//yd
                if not 0 <= sy < sh: continue
                for x in range(pw):
                    xn = (2*x+1)*lw - b[0]*2*pw
                    xd = b[2]*2*pw
                    if not 0 <= xn < xd: continue
                    sx = a[0] + xn*a[2]//xd
                    if not 0 <= sx < sw: continue
                    p = source[offset+sy*source_stride+sx*4:offset+sy*source_stride+sx*4+4]
                    if fmt == RGBA: p = p[2:3]+p[1:2]+p[0:1]+p[3:4]
                    expected[offset+y*panel_stride+x*4:offset+y*panel_stride+x*4+4] = p
                    copied += 1
        sb = (C.c_uint8*len(source)).from_buffer(source)
        db = (C.c_uint8*len(panel)).from_buffer(panel)
        slen = offset+(sh-1)*source_stride+sw*4 - (1 if short_source else 0)
        dlen = offset+(ph-1)*panel_stride+pw*4 - (1 if short_panel else 0)
        si = Image(sb, slen, sw, sh, 1 if bad_stride else source_stride, offset, fmt)
        di = Image(db, dlen, pw, ph, panel_stride, offset, BGRA)
        before = bytes(source)
        result = fn(C.byref(si), C.byref(di), lw, lh, Rect(*a), Rect(*b))
        assert result == copied, (name, 'pixel count', result, copied)
        assert panel == expected, (name, 'pixels or guards changed incorrectly')
        assert bytes(source) == before, (name, 'source modified')
        checks.append(name)

    case('native BGRA with padded rows and nonzero offsets')
    case('RGBA red/blue conversion', fmt=RGBA)
    case('logical full frame scaled to smaller panel', pw=4, ph=3, logical=(11, 9))
    case('upscale', sw=3, sh=2, pw=9, ph=8)
    case('clipped negative destination', dr=(-3, -2, 10, 7))
    case('clipped negative source', sr=(-2, -1, 7, 5))
    case('partially out of source', sr=(4, 3, 7, 5))
    case('offscreen right', dr=(8, 0, 7, 5))
    case('offscreen bottom', dr=(0, 8, 7, 5))
    case('empty source', sr=(0, 0, 0, 5))
    case('empty destination', dr=(0, 0, 7, 0))
    case('reversed destination', dr=(0, 0, -1, 5))
    case('short source mapping', short_source=True)
    case('short panel mapping', short_panel=True)
    case('invalid row stride', bad_stride=True)
    case('unsupported pixel format', fmt=0x34323066)
    case('large signed destination', dr=(-2147483648, -2147483648, 2147483647, 2147483647))
    case('large source span', sr=(0, 0, 2147483647, 5))
    rng = random.Random(75)
    for i in range(256):
        sw, sh, pw, ph = [rng.randint(1, 15) for _ in range(4)]
        case('random geometry %d' % i, sw=sw, sh=sh, pw=pw, ph=ph,
             logical=(rng.randint(1,20),rng.randint(1,20)),
             sr=(rng.randint(-8,8),rng.randint(-8,8),rng.randint(1,20),rng.randint(1,20)),
             dr=(rng.randint(-8,15),rng.randint(-8,15),rng.randint(1,20),rng.randint(1,20)),
             fmt=rng.choice((BGRA,RGBA)))
    case('actual whyred panel receives full iPhone canvas', sw=1125, sh=2436,
         pw=1080, ph=2160, logical=(1125,2436))
    report = dict(checks=len(checks), cases=checks, header_sha256=hashlib.sha256(header.read_bytes()).hexdigest(),
                  actual_kernel_blitter=True, hardware_scanout_tested=False,
                  coreanimation_scene_tested=False)
    (args.output/'report.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print('PASS: %d actual framebuffer pixel/format/clipping/bounds checks' % len(checks))

if __name__ == '__main__':
    main()
