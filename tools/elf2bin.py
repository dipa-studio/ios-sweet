#!/usr/bin/env python3
"""objcopy -O binary for a static ELF64 linked at 0: concatenate the PT_LOAD
segments' file bytes at their addresses and pad to the highest p_memsz end
(so .bss and stacks exist as zeroed bytes, like the shim build expects).

  elf2bin.py IN.elf OUT.bin
"""
import struct, sys

d = open(sys.argv[1], 'rb').read()
assert d[:4] == b'\x7fELF' and d[4] == 2 and d[5] == 1, 'need little-endian ELF64'
phoff, = struct.unpack_from('<Q', d, 0x20)
phentsize, phnum = struct.unpack_from('<HH', d, 0x36)
segs = []
for i in range(phnum):
    (ptype, flags, off, vaddr, paddr, filesz, memsz, align) = \
        struct.unpack_from('<IIQQQQQQ', d, phoff + i * phentsize)
    if ptype == 1:
        segs.append((paddr, off, filesz, memsz))
base = min(s[0] for s in segs)
assert base == 0, f'expected an image linked at 0, lowest segment at {base:#x}'
out = bytearray(max(s[0] + s[3] for s in segs))
for paddr, off, filesz, memsz in segs:
    out[paddr:paddr + filesz] = d[off:off + filesz]
open(sys.argv[2], 'wb').write(out)
print(f'{sys.argv[2]}: {len(out)} bytes')
