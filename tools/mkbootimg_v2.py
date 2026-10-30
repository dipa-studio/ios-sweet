#!/usr/bin/env python3
"""Pack an Android boot image header v2, copying every header field we do not
replace (addresses, page size, os_version, name) from a template boot.img.

  mkbootimg_v2.py TEMPLATE_BOOT.img OUT.img --kernel K [--ramdisk R] [--dtb D] [--cmdline S]

Without --ramdisk an empty gzip'd newc cpio is used; without --dtb the
template's dtb section is kept. The second stage and recovery DTBO are
dropped. No AVB footer or signature is added.
"""
import argparse, gzip, hashlib, struct

p = argparse.ArgumentParser()
p.add_argument('template')
p.add_argument('out')
p.add_argument('--kernel', required=True)
p.add_argument('--ramdisk')
p.add_argument('--dtb')
p.add_argument('--cmdline')
a = p.parse_args()

t = open(a.template, 'rb').read()
assert t[:8] == b'ANDROID!', 'template is not an Android boot image'
(ks, ka, rs, ra, ss, sa, ta, ps, ver, osv) = struct.unpack_from('<10I', t, 8)
assert ver == 2, f'template header version {ver}, need 2'
rnd = lambda n: (n + ps - 1) // ps * ps

def section(off, size):
    return t[off:off + size]

# Template layout, to fetch its dtb.
rds, _, hs = struct.unpack_from('<IQI', t, 1632)
ds, da = struct.unpack_from('<IQ', t, 1648)
off_dtb = ps + rnd(ks) + rnd(rs) + rnd(ss) + rnd(rds)

kernel = open(a.kernel, 'rb').read()
if a.ramdisk:
    ramdisk = open(a.ramdisk, 'rb').read()
else:
    # newc trailer only
    name = b'TRAILER!!!\0'
    hdr = b'070701' + b''.join(b'%08X' % v for v in
                               (0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, len(name), 0))
    rec = hdr + name
    rec += b'\0' * (-len(rec) % 4)
    ramdisk = gzip.compress(rec + b'\0' * (-len(rec) % 512), mtime=0)
dtb = open(a.dtb, 'rb').read() if a.dtb else section(off_dtb, ds)

h = bytearray(t[:ps])
struct.pack_into('<I', h, 8, len(kernel))
struct.pack_into('<I', h, 16, len(ramdisk))
struct.pack_into('<I', h, 24, 0)			# second_size
if a.cmdline is not None:
    c = a.cmdline.encode()
    assert len(c) < 512 + 1024
    h[64:64 + 512] = c[:511].ljust(512, b'\0')
    h[608:608 + 1024] = c[511:].ljust(1024, b'\0')
struct.pack_into('<IQ', h, 1632, 0, 0)		# recovery_dtbo size/offset
struct.pack_into('<I', h, 1648, len(dtb))
# id = SHA-1 over each section followed by its size, as AOSP mkbootimg does
sha = hashlib.sha1()
for blob in (kernel, ramdisk, b'', b'', dtb):
    sha.update(blob)
    sha.update(struct.pack('<I', len(blob)))
h[576:576 + 32] = sha.digest().ljust(32, b'\0')
h[hs:] = b'\0' * (ps - hs)

pad = lambda b: b + b'\0' * (rnd(len(b)) - len(b))
img = bytes(h) + pad(kernel) + pad(ramdisk) + pad(dtb)
open(a.out, 'wb').write(img)
print(f'{a.out}: {len(img)} bytes, page {ps}, kernel {len(kernel)}, ramdisk {len(ramdisk)}, dtb {len(dtb)}')
