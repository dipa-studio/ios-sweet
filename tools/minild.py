#!/usr/bin/env python3
"""Minimal static linker for the boot shims when no ld.lld / aarch64 binutils
is installed (macOS with only Apple clang). Links little-endian AArch64
ELF64 relocatable objects at address 0 with the layout of shim/shim.ld and
writes the flat image directly (what objcopy -O binary would give, padded
to _end so .bss and the stacks exist as zeroed bytes).

  minild.py OUT.bin [--map OUT.map] OBJ...   (the first object provides .text.head)

Supported relocations: ABS64, ADR_PREL_LO21, ADR_PREL_PG_HI21,
ADD_ABS_LO12_NC, LDST{8,16,32,64,128}_ABS_LO12_NC, TSTBR14, CONDBR19,
JUMP26, CALL26, PREL32. Anything else is an error.
"""
import argparse, struct, sys

R = dict(ABS64=257, PREL32=261, ADR_PREL_LO21=274, ADR_PREL_PG_HI21=275, ADD_ABS_LO12_NC=277,
         LDST8=278, TSTBR14=279, CONDBR19=280, JUMP26=282, CALL26=283, LDST16=284,
         LDST32=285, LDST64=286, LDST128=299)
LDST_SHIFT = {R['LDST8']: 0, R['LDST16']: 1, R['LDST32']: 2, R['LDST64']: 3, R['LDST128']: 4}
SHN_UNDEF, SHN_ABS, SHN_COMMON = 0, 0xfff1, 0xfff2

ap = argparse.ArgumentParser()
ap.add_argument('out')
ap.add_argument('--map')
ap.add_argument('objs', nargs='+')
a = ap.parse_args()


class Obj:
    def __init__(self, path):
        self.path = path
        d = self.d = open(path, 'rb').read()
        assert d[:4] == b'\x7fELF' and d[4] == 2 and d[5] == 1, f'{path}: not ELF64 LE'
        assert struct.unpack_from('<HH', d, 16) == (1, 183), f'{path}: not an AArch64 .o'
        shoff, = struct.unpack_from('<Q', d, 0x28)
        shentsize, shnum, shstrndx = struct.unpack_from('<HHH', d, 0x3a)
        self.secs = [struct.unpack_from('<IIQQQQIIQQ', d, shoff + i * shentsize) for i in range(shnum)]
        sh = self.secs[shstrndx]
        self.names = [d[sh[4] + s[0]:d.index(b'\0', sh[4] + s[0])].decode() for s in self.secs]
        self.base = {}		# section index -> output address
        symtab = [s for s in self.secs if s[1] == 2]
        self.syms = []
        if symtab:
            st = symtab[0]
            strtab = self.secs[st[6]]
            for j in range(st[5] // 24):
                name, info, other, shndx, value, size = struct.unpack_from('<IBBHQQ', d, st[4] + j * 24)
                n = d[strtab[4] + name:d.index(b'\0', strtab[4] + name)].decode()
                self.syms.append((n, info >> 4, info & 0xf, shndx, value))


objs = [Obj(p) for p in a.objs]


def kind(name):
    for k in ('.text', '.rodata', '.data', '.bss'):
        if name == k or name.startswith(k + '.'):
            return k
    return None


# Layout (shim.ld): .text.head first, .text*, .rodata*, .data*, .bss + COMMON.
out = bytearray()
addr = 0
placed = []
def place(o, i):
    global addr
    s = o.secs[i]
    al = max(s[8], 1)
    addr = (addr + al - 1) // al * al
    o.base[i] = addr
    placed.append((addr, s[5], o.path, o.names[i]))
    if s[1] != 8:	# not NOBITS
        out.extend(b'\0' * (addr - len(out)))
        out.extend(o.d[s[4]:s[4] + s[5]])
    addr += s[5]

def alloc_secs(o):
    return [i for i, s in enumerate(o.secs) if s[2] & 2 and s[5]]	# SHF_ALLOC

for o in objs:
    for i in alloc_secs(o):
        if o.names[i] == '.text.head':
            place(o, i)
for k in ('.text', '.rodata', '.data'):
    for o in objs:
        for i in alloc_secs(o):
            if i not in o.base and kind(o.names[i]) == k:
                place(o, i)
sym = {}
addr = (addr + 15) // 16 * 16
sym['_bss_start'] = addr
for o in objs:
    for i in alloc_secs(o):
        if i not in o.base and kind(o.names[i]) == '.bss':
            place(o, i)
for o in objs:
    left = [o.names[i] for i in alloc_secs(o) if i not in o.base]
    assert not left, f'{o.path}: unplaced sections {left}'
addr = (addr + 15) // 16 * 16
sym['_bss_end'] = addr
addr += 0x8000
addr = (addr + 15) // 16 * 16
sym['_stack_top'] = addr
addr = (addr + 4095) // 4096 * 4096
sym['_sec_stacks'] = addr
addr += 8 * 0x1000
sym['_end'] = addr

# Global symbols.
for o in objs:
    for n, bind, typ, shndx, value in o.syms:
        if bind in (1, 2) and shndx not in (SHN_UNDEF,):	# GLOBAL / WEAK, defined
            assert shndx != SHN_COMMON, f'{o.path}: COMMON symbol {n} (build with -fno-common)'
            v = value if shndx == SHN_ABS else o.base[shndx] + value
            if n in sym and bind == 1:
                sys.exit(f'duplicate symbol {n}')
            sym.setdefault(n, v)


def resolve(o, idx):
    n, bind, typ, shndx, value = o.syms[idx]
    if shndx == SHN_UNDEF:
        if n not in sym:
            sys.exit(f'{o.path}: undefined symbol {n}')
        return sym[n]
    if shndx == SHN_ABS:
        return value
    return o.base[shndx] + value


def fits(v, bits):
    return -(1 << (bits - 1)) <= v < (1 << (bits - 1))


out.extend(b'\0' * (sym['_end'] - len(out)))
for o in objs:
    for s in o.secs:
        if s[1] != 4 or s[7] not in o.base:	# SHT_RELA for a placed section
            continue
        tbase = o.base[s[7]]
        for j in range(s[5] // 24):
            off, info, add = struct.unpack_from('<QQq', o.d, s[4] + j * 24)
            t = info & 0xffffffff
            S = resolve(o, info >> 32)
            P = tbase + off
            X = S + add
            where = f'{o.path}+{off:#x} type {t}'
            if t == R['ABS64']:
                struct.pack_into('<Q', out, P, X)
                continue
            if t == R['PREL32']:
                assert fits(X - P, 32), where
                struct.pack_into('<i', out, P, X - P)
                continue
            ins, = struct.unpack_from('<I', out, P)
            if t in (R['ADR_PREL_LO21'], R['ADR_PREL_PG_HI21']):
                v = X - P if t == R['ADR_PREL_LO21'] else (X >> 12) - (P >> 12)
                assert fits(v, 21), where
                v &= (1 << 21) - 1
                ins = (ins & ~((3 << 29) | (0x7ffff << 5))) | ((v & 3) << 29) | ((v >> 2) << 5)
            elif t == R['ADD_ABS_LO12_NC']:
                ins = (ins & ~(0xfff << 10)) | ((X & 0xfff) << 10)
            elif t in LDST_SHIFT:
                sh = LDST_SHIFT[t]
                assert X & ((1 << sh) - 1) == 0, f'{where}: misaligned lo12'
                ins = (ins & ~(0xfff << 10)) | (((X & 0xfff) >> sh) << 10)
            elif t in (R['JUMP26'], R['CALL26']):
                v = X - P
                assert v & 3 == 0 and fits(v, 28), where
                ins = (ins & ~0x3ffffff) | ((v >> 2) & 0x3ffffff)
            elif t == R['CONDBR19']:
                v = X - P
                assert v & 3 == 0 and fits(v, 21), where
                ins = (ins & ~(0x7ffff << 5)) | (((v >> 2) & 0x7ffff) << 5)
            elif t == R['TSTBR14']:
                v = X - P
                assert v & 3 == 0 and fits(v, 16), where
                ins = (ins & ~(0x3fff << 5)) | (((v >> 2) & 0x3fff) << 5)
            else:
                sys.exit(f'{where}: unsupported relocation')
            struct.pack_into('<I', out, P, ins)

open(a.out, 'wb').write(out)
if a.map:
    with open(a.map, 'w') as f:
        for ad, size, path, name in placed:
            f.write(f'{ad:08x} {size:8x} {path} {name}\n')
        for n, v in sorted(sym.items(), key=lambda kv: kv[1]):
            f.write(f'{v:08x} {n}\n')
print(f'{a.out}: {len(out)} bytes, _end {sym["_end"]:#x}')
