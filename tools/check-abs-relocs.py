#!/usr/bin/env python3
"""Fail if any ELF64 relocatable object has R_AARCH64_ABS64 relocations.
The shims run wherever the bootloader loads them without a relocation pass,
so code and data must only use PC-relative references.

  check-abs-relocs.py OBJ...
"""
import struct, sys

R_AARCH64_ABS64 = 257
bad = 0
for f in sys.argv[1:]:
    d = open(f, 'rb').read()
    shoff, = struct.unpack_from('<Q', d, 0x28)
    shentsize, shnum, shstrndx = struct.unpack_from('<HHH', d, 0x3a)
    secs = [struct.unpack_from('<IIQQQQIIQQ', d, shoff + i * shentsize) for i in range(shnum)]
    shstr = secs[shstrndx]
    name = lambda o: d[shstr[4] + o:d.index(b'\0', shstr[4] + o)].decode()
    for s in secs:
        if s[1] != 4:	# SHT_RELA
            continue
        for j in range(s[5] // 24):
            off, info, _ = struct.unpack_from('<QQq', d, s[4] + j * 24)
            if info & 0xffffffff == R_AARCH64_ABS64:
                print(f'{f}: ABS64 in {name(s[0])} at {off:#x}', file=sys.stderr)
                bad += 1
sys.exit(1 if bad else 0)
