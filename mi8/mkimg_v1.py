#!/usr/bin/env python3
"""Pack the shim Image into an Android boot.img (header v1) for the Mi 8's ABL.

The Mi 8 (SDM845, Android 9/10 bootloader) boots a v1 header with the DTB(s)
appended to the kernel; there is no separate dtb section. ABL picks the DTB by
qcom,msm-id / qcom,board-id, so the appended DTB must be the one matching this
board (mi8/fdt/mi8-dipper-mp-v2.1.dtb: msm-id 321/0x20001, board-id 55/0).

Two kernel containers:
  gz    gzip(Image) + DTB. Same layout as the stock ROM boot.img (verified on a
        dump of it: gzip stream, then 24 DTBs back to back). Try this first.
  ucomp "UNCOMPRESSED_IMG" + le32(len(Image)) + Image + DTB, the layout other
        Qualcomm shim ports use for an uncompressed kernel. Fallback.
Header fields mirror the stock dump: base 0, kernel_offset 0x8000,
ramdisk_offset 0x1000000, tags 0x100, page 4096, os_version 0x1a000175.
"""
import argparse, gzip, hashlib, struct

PAGE = 4096


def up(n):
    return (n + PAGE - 1) // PAGE * PAGE


def empty_cpio_gz():
    # ABL dislikes a zero-size ramdisk on some builds: ship an empty newc archive.
    name = b"TRAILER!!!\0"
    fields = [0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, len(name), 0]
    hdr = b"070701" + b"".join(b"%08X" % f for f in fields) + name
    hdr += b"\0" * (-len(hdr) % 4)
    hdr += b"\0" * (-len(hdr) % 512)
    return gzip.compress(hdr, 9, mtime=0)


def build(image, dtb, mode, cmdline, ramdisk=None):
    if mode == "gz":
        kernel = gzip.compress(image, 9, mtime=0) + dtb
    elif mode == "ucomp":
        kernel = b"UNCOMPRESSED_IMG" + struct.pack("<I", len(image)) + image + dtb
    else:
        raise SystemExit("bad mode")
    # A raw payload (the shim reads it from the ramdisk slot) or, by default, an empty cpio so ABL has something.
    ramdisk = ramdisk if ramdisk is not None else empty_cpio_gz()
    sha = hashlib.sha1()
    for blob in (kernel, ramdisk, b""):
        sha.update(blob)
        sha.update(struct.pack("<I", len(blob)))
    sha.update(struct.pack("<I", 0))  # recovery_dtbo (v1): empty
    ident = sha.digest().ljust(32, b"\0")
    hdr = b"ANDROID!"
    hdr += struct.pack("<10I", len(kernel), 0x8000, len(ramdisk), 0x1000000, 0, 0, 0x100,
                       PAGE, 1, 0x1A000175)
    hdr += b"\0" * 16                      # name
    hdr += cmdline[:511].ljust(512, b"\0")
    hdr += ident
    hdr += b"\0" * 1024                    # extra_cmdline
    hdr += struct.pack("<IQI", 0, 0, 1648)  # recovery_dtbo size/offset, header_size
    assert len(hdr) == 1648
    out = hdr.ljust(PAGE, b"\0")
    out += kernel.ljust(up(len(kernel)), b"\0")
    out += ramdisk.ljust(up(len(ramdisk)), b"\0")
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--image", required=True)
    ap.add_argument("--dtb", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--mode", choices=("gz", "ucomp"), default="gz")
    ap.add_argument("--cmdline", default="console=null")
    ap.add_argument("--ramdisk", help="raw shim payload (kernel + ADT) to carry as the ramdisk")
    a = ap.parse_args()
    image = open(a.image, "rb").read()
    dtb = open(a.dtb, "rb").read()
    assert dtb[:4] == b"\xd0\x0d\xfe\xed", "not a DTB"
    assert image[0x38:0x3C] == b"ARMd", "not an arm64 Image"
    rd = open(a.ramdisk, "rb").read() if a.ramdisk else None
    open(a.out, "wb").write(build(image, dtb, a.mode, a.cmdline.encode(), rd))
    print(f"{a.out}: mode={a.mode} image={len(image)} dtb={len(dtb)} ramdisk={len(rd) if rd else 0}")
