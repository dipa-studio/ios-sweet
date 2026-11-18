#!/usr/bin/env python3
"""Write a synthetic FTM5 .ftb for the host test (same container layout as ST's parseBinFile expects)."""
import random, struct, sys
out = sys.argv[1]
random.seed(51)
sec0, sec1, sec2, sec3 = 70000, 2656, 0, 0
data = bytearray(random.randrange(256) for _ in range(sec0 + sec1))
# organisation bytes live at file offset 280 = data offset 216: code pages, panel pages, cx pages, config pages
data[216:220] = bytes([24, 2, 3, 1])
hdr = bytearray(64)
struct.pack_into('<I', hdr, 0, 0xAA55AA55)
struct.pack_into('<I', hdr, 4, 1)
hdr[8:10] = bytes([0x36, 0x39])
struct.pack_into('<I', hdr, 12, 0x1647)       # svn
struct.pack_into('<I', hdr, 16, 0x0051)       # fw version
struct.pack_into('<I', hdr, 20, 0x0000)
struct.pack_into('<I', hdr, 24, 0x0021)       # config version
hdr[36:44] = bytes(range(1, 9))               # external release
struct.pack_into('<IIII', hdr, 44, sec0, sec1, sec2, sec3)
blob = bytes(hdr) + bytes(data) + b'\x00\x00\x00\x00'   # trailing crc word
open(out, 'wb').write(blob)
print(out, len(blob))
