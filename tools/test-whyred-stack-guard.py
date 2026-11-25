#!/usr/bin/env python3
"""Run the extracted kernel stack-check macro in Unicorn (offline ARM64).

The fixture adapts Mach-O page relocations and positional macro syntax to ELF.
Constants match v70's linked exception vector. Dispatch is replaced by stop
markers; this does not emulate the scheduler, MMU, interrupt controller or phone.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import struct
import subprocess


def macro(s, name):
    start = s.index('.macro '+name)
    end = s.index('.endmacro',start)+len('.endmacro')
    return s[start:end]


def fixture(source, header):
    check = macro(source,'CHECK_KERNEL_STACK')
    flavors = macro(header,'INIT_SAVED_STATE_FLAVORS')
    flavors = flavors.replace('.macro INIT_SAVED_STATE_FLAVORS',
        '.macro INIT_SAVED_STATE_FLAVORS state scratch0 scratch1')
    for i,name in enumerate(('state','scratch0','scratch1')):
        flavors = flavors.replace('$'+str(i),'\\'+name)
    check = check.replace('fleh_invalid_stack@pageoff',':lo12:fleh_invalid_stack')
    check = check.replace('fleh_invalid_stack@page','fleh_invalid_stack')
    a = source.index('el1_sp0_synchronous_vector_long:')
    b = source.index('\n\tEL1_SP0_VECTOR',a)
    entry = source[a:b].replace('el1_sp0_synchronous_vector_long:','entry:')
    const = '''#define SWEET 1
#define ESR_EC_MASK 0xfc000000
#define ESR_EC_SHIFT 26
#define ESR_EC_SP_ALIGN 0x26
#define ESR_EC_DABORT_EL1 0x25
#define KERNEL_STACK_SIZE 0x4000
#define INTSTACK_SIZE_NUM 0x4000
#define TH_KSTACKPTR 0x158
#define ACT_CPUDATAP 0x228
#define CPU_INTSTACK_TOP 0x18
#define ARM_CONTEXT_SIZE 0x350
#define SS64_X0 8
#define SS64_X2 0x18
#define SS64_SP 0x100
#define SS_FLAVOR 0
#define NS_FLAVOR 0x130
#define NS_COUNT 0x134
#define ARM_SAVED_STATE64 21
#define ARM_SAVED_STATE64_COUNT 72
#define ARM_NEON_SAVED_STATE64 23
#define ARM_NEON_SAVED_STATE64_COUNT 132
.text
.globl entry
'''
    return const+flavors+'\n'+check+'\n'+entry+'''
normal_dispatch:
    brk #0x111
fleh_dispatch64:
    brk #0x222
fleh_invalid_stack:
    brk #0x333
'''


def elf(path):
    b = path.read_bytes()
    assert b[:6] == b'\x7fELF\x02\x01'
    shoff = struct.unpack_from('<Q',b,0x28)[0]
    stride, n, names = struct.unpack_from('<HHH',b,0x3a)
    sections = [struct.unpack_from('<IIQQQQIIQQ',b,shoff+i*stride) for i in range(n)]
    stringsec = sections[names]
    strings = b[stringsec[4]:stringsec[4]+stringsec[5]]
    def string(data,off):return data[off:data.index(0,off)].decode()
    text = next(s for s in sections if string(strings,s[0]) == '.text')
    symbols = {}
    for s in sections:
        if s[1] != 2:continue
        st = sections[s[6]]
        ns = b[st[4]:st[4]+st[5]]
        for off in range(s[4],s[4]+s[5],s[9]):
            name,_,_,_,value,_ = struct.unpack_from('<IBBHQQ',b,off)
            if name:symbols[string(ns,name)] = value
    return text[3],b[text[4]:text[4]+text[5]],symbols


def run_case(image,sp0,esr):
    from unicorn import Uc,UC_ARCH_ARM64,UC_MODE_ARM,UC_HOOK_CODE
    from unicorn.arm64_const import UC_ARM64_REG_SP,UC_ARM64_REG_SP_EL0,UC_ARM64_REG_SP_EL1,UC_ARM64_REG_PSTATE,UC_ARM64_REG_ESR_EL1,UC_ARM64_REG_ELR_EL1,UC_ARM64_REG_TPIDR_EL1,UC_ARM64_REG_X0,UC_ARM64_REG_X1,UC_ARM64_REG_X2,UC_ARM64_REG_X3
    addr,data,syms = image
    u = Uc(UC_ARCH_ARM64,UC_MODE_ARM)
    u.mem_map(addr&~4095,0x10000);u.mem_write(addr,data)
    for p,size in [(0x500000,4096),(0x600000,4096),(0x700000,0x4000),(0x800000,0x4000),(0x900000,0x4000)]:u.mem_map(p,size)
    u.mem_write(0x500000+0x158,struct.pack('<Q',0x703f40))
    u.mem_write(0x500000+0x228,struct.pack('<Q',0x600000))
    u.mem_write(0x600000+0x18,struct.pack('<Q',0x804000))
    u.reg_write(UC_ARM64_REG_PSTATE,0x3c5)  # EL1h, interrupts masked
    u.reg_write(UC_ARM64_REG_SP_EL1,0x903f00)
    u.reg_write(UC_ARM64_REG_SP,0x903f00)
    u.reg_write(UC_ARM64_REG_SP_EL0,sp0)
    u.reg_write(UC_ARM64_REG_TPIDR_EL1,0x500000)
    u.reg_write(UC_ARM64_REG_ESR_EL1,esr)
    original_pc = 0xfffffe0007b79e00
    u.reg_write(UC_ARM64_REG_ELR_EL1,original_pc)
    regs = [UC_ARM64_REG_X0,UC_ARM64_REG_X1,UC_ARM64_REG_X2,UC_ARM64_REG_X3]
    values = [0x123400+i for i in range(4)]
    for r,v in zip(regs,values):u.reg_write(r,v)
    hit=[]
    def hook(uc,pc,size,user):
        for label in ('normal_dispatch','fleh_dispatch64'):
            if pc == syms[label]:hit.append(label);uc.emu_stop()
    u.hook_add(UC_HOOK_CODE,hook)
    u.emu_start(syms['entry'],addr+len(data),count=1000)
    assert len(hit)==1
    assert u.reg_read(UC_ARM64_REG_ELR_EL1)==original_pc
    assert u.reg_read(UC_ARM64_REG_ESR_EL1)==esr
    assert u.reg_read(UC_ARM64_REG_SP_EL0)==sp0
    if hit[0]=='normal_dispatch':
        assert u.reg_read(UC_ARM64_REG_SP)==0x903f00
        assert [u.reg_read(r) for r in regs]==values
    else:
        frame=u.reg_read(UC_ARM64_REG_X0)
        assert frame==0x903f00-0x350
        assert struct.unpack('<QQ',u.mem_read(frame+8,16))==tuple(values[:2])
        assert struct.unpack('<QQ',u.mem_read(frame+0x18,16))==tuple(values[2:])
        assert struct.unpack('<Q',u.mem_read(frame+0x100,8))[0]==sp0
    return hit[0]


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('baseline',type=Path)
    ap.add_argument('patched',type=Path)
    ap.add_argument('exception_header',type=Path)
    ap.add_argument('output',type=Path)
    ap.add_argument('--clang',default=shutil.which('clang'))
    ap.add_argument('--linker',default=shutil.which('ld.lld'))
    args=ap.parse_args()
    args.output.mkdir(parents=True,exist_ok=True)
    rows=[];images={}
    for name,path in [('baseline',args.baseline),('patched',args.patched)]:
        asm=args.output/f'{name}.S';obj=asm.with_suffix('.o');exe=asm.with_suffix('.elf')
        asm.write_text(fixture(path.read_text(),args.exception_header.read_text()),encoding='utf-8',newline='\n')
        subprocess.run([args.clang,'-target','aarch64-none-elf','-c',str(asm),'-o',str(obj)],check=True)
        subprocess.run([args.linker,'-Ttext=0x100000','-e','entry',str(obj),'-o',str(exe)],check=True)
        images[name]=elf(exe)
    for esr in [0,0x8600000f,0x9600000f,0x9a000000]:
        for sp in [5,0x703000,0x803000]:
            old=run_case(images['baseline'],sp,esr);new=run_case(images['patched'],sp,esr)
            expected='fleh_dispatch64' if sp==5 or esr==0x9a000000 else 'normal_dispatch'
            assert new==expected,(hex(sp),hex(esr),new,expected)
            if sp!=5:assert old==new
            if sp==5 and esr in [0,0x8600000f]:assert old=='normal_dispatch' and new=='fleh_dispatch64'
            rows.append(dict(esr=hex(esr),sp0=hex(sp),baseline=old,patched=new))
    report=dict(checks=len(rows),source_sha256=hashlib.sha256(args.patched.read_bytes()).hexdigest(),
        result='PASS: 12 ARM64 macro cases; original registers/ELR/ESR and safe exception stack preserved',
        cases=rows,hardware_emulated=False,scheduler_emulated=False)
    (args.output/'report.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(report['result'])


if __name__=='__main__':main()
