#!/usr/bin/env python3
"""Convert the supplied boot image to a bounded RGB565 kernel include.

macOS uses its built-in sips JPEG decoder. Other hosts may use Pillow for
local preparation. BMP parsing and RGB565 encoding below use the stdlib only.
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import sys
import tempfile

def read_bmp(data):
    if len(data) < 54 or data[:2] != b'BM':
        raise ValueError('Not a BMP')
    off = struct.unpack_from('<I', data, 10)[0]
    dib, width, signed_height, planes, bpp, compression = struct.unpack_from('<IiiHHI', data, 14)
    if dib < 40 or dib > len(data) - 14 or planes != 1 or width != 1080 or abs(signed_height) != 2160:
        raise ValueError('Expected a 1080x2160 BMP with one plane')
    if bpp not in (24, 32) or compression not in (0, 3) or (compression == 3 and bpp != 32):
        raise ValueError('Unsupported BMP encoding')
    header_end = 14 + dib
    if compression == 3:
        masks_at = 54
        if masks_at + 12 > len(data) or struct.unpack_from('<III', data, masks_at) != (0xff0000, 0xff00, 0xff):
            raise ValueError('Unsupported BMP channel masks')
        header_end = max(header_end, masks_at + 12)
    height = abs(signed_height)
    stride = ((width * bpp + 31) // 32) * 4
    if off < header_end or off > len(data) or stride * height > len(data) - off:
        raise ValueError('Truncated/overlapping BMP pixels')
    raw = bytearray(width * height * 2)
    for y in range(height):
        row = y if signed_height < 0 else height - 1 - y
        start = off + row * stride
        for x in range(width):
            p = start + x * (bpp // 8)
            b, g, r = data[p:p + 3]
            value = ((r >> 3) << 11) | ((g >> 2) << 5) | (b >> 3)
            struct.pack_into('<H', raw, (y * width + x) * 2, value)
    return width, height, raw

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('image', type=Path)
    ap.add_argument('--output', required=True, type=Path)
    ap.add_argument('--report', required=True, type=Path)
    ap.add_argument('--expected-sha256', required=True)
    args = ap.parse_args()
    image = args.image.read_bytes()
    if hashlib.sha256(image).hexdigest() != args.expected_sha256:
        raise SystemExit('Boot image input hash mismatch')
    with tempfile.TemporaryDirectory() as td:
        bmp = Path(td) / 'splash.bmp'
        if image[:2] == b'BM':
            bmp.write_bytes(image)
            decoder = 'BMP input'
        elif sys.platform == 'darwin':
            subprocess.run(['/usr/bin/sips', '-s', 'format', 'bmp',
                            str(args.image.resolve()), '--out', str(bmp)],
                           check=True, capture_output=True)
            decoder = 'macOS sips'
        else:
            from PIL import Image
            with Image.open(args.image) as im:
                if im.size != (1080, 2160):
                    raise SystemExit('Expected a 1080x2160 source image')
                im.convert('RGB').save(bmp, format='BMP')
            decoder = 'Pillow local conversion'
        width, height, raw = read_bmp(bmp.read_bytes())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('w', newline='\n') as f:
        f.write('/* Generated from supplied boot art; RGB565, top row first. */\n')
        f.write('#define WHYRED_SPLASH_WIDTH 1080U\n#define WHYRED_SPLASH_HEIGHT 2160U\n')
        f.write('static const uint16_t whyred_splash_rgb565[1080U * 2160U] = {\n')
        values = memoryview(raw).cast('H') if sys.byteorder == 'little' else None
        for start in range(0, width * height, 16):
            row = values[start:start + 16] if values is not None else struct.unpack_from('<16H', raw, start * 2)
            f.write(','.join('0x%04x' % value for value in row) + ',\n')
        f.write('};\n')
    report = dict(input_sha256=args.expected_sha256, width=width, height=height,
                  decoded_bytes=len(raw), rgb565_sha256=hashlib.sha256(raw).hexdigest(),
                  header_sha256=hashlib.sha256(args.output.read_bytes()).hexdigest(),
                  decoder=decoder, hold_ms=3000)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2) + '\n')
    print('Boot art ready:', width, 'x', height, len(raw), 'RGB565 bytes')

if __name__ == '__main__':
    main()
