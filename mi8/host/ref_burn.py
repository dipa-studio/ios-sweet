#!/usr/bin/env python3
"""Independent re-implementation of ST's flash_burn command stream (fts_lib/ftsFlash.c) for the host test.
Prints the expected write-only I2C transactions, one per line: "W <len> <first 12 bytes hex> <sum of bytes from index 5>"."""
import struct, sys
f = open(sys.argv[1], 'rb').read()
FLASH_CHUNK, DMA_CHUNK = 32 * 1024, 32
sec0, sec1, sec2, sec3 = struct.unpack_from('<IIII', f, 44)
data = f[64:64 + sec0 + sec1 + sec2 + sec3]
code_pg, panel_pg, cx_pg, cfg_pg = f[280:284]
cfg_addr = ((code_pg + panel_pg + cx_pg) * 4096) // 4
lines = []
def w(b):
    b = bytes(b)
    lines.append("W %d %s %d" % (len(b), b[:12].hex(), sum(b[5:])))
def hw(a, d): w([0xFA, 0x20, 0x00, 0x00, a, d])
hw(0x24, 0x81)                       # 1) system reset
hw(0x24, 0x01)                       # 2) hold M3
hw(0x1B, 0x66); hw(0x68, 0x13)       # 3) uvlo + auto power down
hw(0x25, 0x20); hw(0x6B, 0x00)       # 4) flash unlock
hw(0xDE, 0x03)                       # 5) erase unlock
panel_s = code_pg; panel_e = panel_s + panel_pg - 1 if panel_pg > 1 else panel_s
cx_s = panel_e + 1; cx_e = cx_s + cx_pg - 1 if cx_pg > 1 else cx_s
mask = [0] * 4
for i in list(range(cx_s, cx_e + 1)) + list(range(panel_s, panel_e + 1)):
    mask[i // 8] |= 1 << (i % 8)
w([0xFA, 0x20, 0x00, 0x01, 0x28] + [0xFF & ~m for m in mask])   # 6) page mask
hw(0x6B, 0x00); hw(0x6A, 0xA0)
def fill(address, blob):
    pos, wheel = 0, 0
    while pos < len(blob):
        block, addr = 0, 0x00100000
        while block < FLASH_CHUNK and pos < len(blob):
            n = min(DMA_CHUNK, len(blob) - pos, FLASH_CHUNK - block)
            w([0xFA, addr >> 24, (addr >> 16) & 255, (addr >> 8) & 255, addr & 255] + list(blob[pos:pos + n]))
            addr += n; pos += n; block += n
        words = block // 4 - 1
        a = address + (wheel * FLASH_CHUNK) // 4
        w([0xFA, 0x20, 0, 0, 0x72, 0, 0, a & 255, (a >> 8) & 255, words & 255, (words >> 8) & 255, 0])
        w([0xFA, 0x20, 0, 0, 0x6B, 0, 0x40, 0x42, 0x0F, 0, 0, 0xC0])
        wheel += 1
fill(0, data[:sec0])                 # 7) program
fill(cfg_addr, data[sec0:sec0 + sec1])   # 8) config
hw(0x24, 0x81)                       # 9) system reset
print("\n".join(lines))
