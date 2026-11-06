#!/usr/bin/env python3
"""Build-only MT6983 GPU shim diagnostic with an intact Recovery fallback.

Never flashes or imports historical trial runners. Requires pinned inputs.
"""
import argparse
import gzip
import hashlib
import importlib.util
import json
from pathlib import Path
import struct
import subprocess
import tempfile

import adt
import embed_payload
import mkbootimg
import mkpayload

ROOT = Path(__file__).resolve().parents[1]
FALLBACK_OFFSET = 0x2000000
FLAGS = ['--target=aarch64-none-elf', '-O2', '-ffreestanding', '-nostdlib',
         '-fno-pic', '-mgeneral-regs-only', '-mstrict-align',
         '-fno-stack-protector', '-fno-builtin', '-Wall', '-Wextra', '-Werror']

def digest(data):
    return hashlib.sha256(data).hexdigest()

def pinned(path, expected):
    data = Path(path).read_bytes()
    if digest(data) != expected:
        raise ValueError('SHA256 mismatch: ' + str(path))
    return data

# The real reset handler at0x010018ec touches the MCU peripheral window before
# it touches anything else: it stores0xb to0x40022000, stores7 to0x40022004,
# and then loads0x40003034. Every one of those constants occurs exactly once in
# the pinned container, so each is the load literal of exactly one instruction.
# A variant repoints them at words inside the shared page, which leaves the
# instructions themselves untouched while (a) bypassing the peripheral accesses
# that may be stalling the bus and (b) leaving an observable trace.
MCU_ACCESS_REDIRECTS = {
    0x2339: (
        dict(kind='store', literal_va=0x01001988, original=0x40022000,
             insn_va=0x010018f4, insn=b'\x01\x60', target=0x04000ffc, value=0xb),
        dict(kind='store', literal_va=0x0100198c, original=0x40022004,
             insn_va=0x010018fc, insn=b'\x01\x60', target=0x04000ffc, value=0x7),
    ),
    0x2340: (
        # First store goes to the global-interface version word, which is the
        # one location2334 proved writable from this same entry. That splits
        # "the code never ran" from "shared+0xffc specifically does not take
        # the write", which2336 and2339 could not distinguish.
        dict(kind='store', literal_va=0x01001988, original=0x40022000,
             insn_va=0x010018f4, insn=b'\x01\x60', target=0x04000000, value=0xb),
        dict(kind='store', literal_va=0x0100198c, original=0x40022004,
             insn_va=0x010018fc, insn=b'\x01\x60', target=0x04000ffc, value=0x7),
        # The load itself cannot fault the way a store can, but a peripheral
        # read that never answers stalls exactly the same way. Point it at a
        # zero word so r4 becomes0 and the guarded0x03800000 copy is skipped.
        dict(kind='load', literal_va=0x01001998, original=0x40003034,
             insn_va=0x01001918, insn=b'\x1f\x48', target=0x04000ff8, value=None),
    ),
    0x2341: (
        # 2340 proved the first store executes: version read0xb, the value it
        # writes, on a byte-identical shim. Its second store, aimed at the same
        # shared+0xffc that2335/2336/2339 also used, still did not land. So ask
        # the narrow question: does the rest of that first page take writes, or
        # is0xffc alone broken? The second store now targets shared+4, one word
        # further in, and features is already decoded, so nothing in the report
        # ABI moves.
        dict(kind='store', literal_va=0x01001988, original=0x40022000,
             insn_va=0x010018f4, insn=b'\x01\x60', target=0x04000000, value=0xb),
        dict(kind='store', literal_va=0x0100198c, original=0x40022004,
             insn_va=0x010018fc, insn=b'\x01\x60', target=0x04000004, value=0x7),
        dict(kind='load', literal_va=0x01001998, original=0x40003034,
             insn_va=0x01001918, insn=b'\x1f\x48', target=0x04000ff8, value=None),
    ),
    0x2342: (
        # 2341 proved both stores run and that the whole first shared page takes
        # writes except0xffc. It left one variable untested: whether the REAL
        # peripheral at0x40022000 accepts its store. So keep that store exactly
        # as the vendor wrote it, keep the peripheral load real too (bit7 must
        # be0 because0x0302bc78 and0x03800000 are in no section, so the vendor
        # firmware itself could not survive a set bit), and move only the second
        # store to shared+4. features0x7 therefore means the real peripheral
        # write completed and execution reached the next instruction.
        dict(kind='store', literal_va=0x0100198c, original=0x40022004,
             insn_va=0x010018fc, insn=b'\x01\x60', target=0x04000004, value=0x7),
    ),
}


def redirect_mcu_accesses(path, expected, build_id):
    firmware = pinned(path, expected)
    if expected != 'de22d2fc06bc8a859968499a6e609c27fe838be062bf5c97d92ea9f904f7229a':
        raise ValueError('MCU access redirect requires the measured device firmware')
    sites = MCU_ACCESS_REDIRECTS.get(build_id)
    if not sites:
        raise ValueError('build %#x has no MCU access redirect' % build_id)
    spec = importlib.util.spec_from_file_location('csf_fetch', ROOT / 'tools/matisse-csf-fetch-audit.py')
    fetch = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(fetch)
    _, plan = fetch.build_arena(Path(path), 0x40077000, memory_group=6)
    section = next(s for s in plan['sections'] if s['va'] == 0x01000000)

    def offset(va):
        if not (section['va'] <= va and va + 4 <= section['va'] + section['data_bytes']):
            raise ValueError('redirect site %#x is outside the code section' % va)
        return section['data_start'] + va - section['va']

    edits = []
    for site in sites:
        insn = offset(site['insn_va'])
        if firmware[insn:insn + 2] != site['insn']:
            raise ValueError('instruction at %#x is %s, expected %s' %
                             (site['insn_va'], firmware[insn:insn + 2].hex(), site['insn'].hex()))
        literal = offset(site['literal_va'])
        have = int.from_bytes(firmware[literal:literal + 4], 'little')
        if have != site['original']:
            raise ValueError('literal %#x is %#x, expected %#x' %
                             (site['literal_va'], have, site['original']))
        if firmware.count(site['original'].to_bytes(4, 'little')) != 1:
            raise ValueError('constant %#x is not unique in the container' % site['original'])
        if site['target'] & 3:
            raise ValueError('redirect target %#x is not aligned' % site['target'])
        edits.append((literal, site['original'], site['target']))

    embedded = bytearray(firmware)
    for literal, _, target in edits:
        embedded[literal:literal + 4] = target.to_bytes(4, 'little')
    embedded = bytes(embedded)
    if len(embedded) != len(firmware):
        raise ValueError('redirect changed the container size')
    changed = [i for i in range(len(firmware)) if firmware[i] != embedded[i]]
    if not changed or any(
            not any(literal <= i < literal + 4 for literal, _, _ in edits) for i in changed):
        raise ValueError('redirect touched bytes outside the redirected literals')
    for literal, _, _ in edits:
        if firmware[literal:literal + 4] == embedded[literal:literal + 4]:
            raise ValueError('literal at container offset %#x was not changed' % literal)
    with tempfile.TemporaryDirectory(prefix='csf-access-redirect-') as directory:
        candidate = Path(directory) / 'diagnostic.bin'
        candidate.write_bytes(embedded)
        _, rebuilt_plan = fetch.build_arena(candidate, 0x40077000, memory_group=6)
    if rebuilt_plan != plan:
        raise ValueError('access redirect changed firmware mappings')
    patch = dict(diagnostic_only=True,
                 sites=[dict(kind=site['kind'], literal_va='%#x' % site['literal_va'],
                             original='%#x' % site['original'], target='%#x' % site['target'],
                             written_value=site['value'],
                             insn_va='%#x' % site['insn_va'],
                             container_offset='%#x' % literal)
                        for site, (literal, _, _) in zip(sites, edits)],
                 original_container_sha256=digest(firmware),
                 embedded_container_sha256=digest(embedded))
    return embedded, patch


def redirect_mcu_stores(path, expected):
    return redirect_mcu_accesses(path, expected, 0x2339)


# Every Cortex-M fault vector in this container points at0x010019b1, so a single
# storm-free stub answers the one question static analysis cannot: does the MCU
# fault, and at which instruction. The stub reads the stacked PC out of the
# exception frame on PSP (the entry switches to PSP at0x01001910) and parks it
# in a shared word the shim already decodes. The periphals and the rest of the
# entry stay exactly as the vendor shipped them.
FAULT_VECTOR_PROBE = {
    0x2343: dict(
        stub_va=0x010019b0,
        # mrs r0,psp / ldr r1,[r0,#0x18] / ldr r2,[pc,#8] / str r1,[r2] /
        # b . / nop / nop / .word0x04000010
        stub=bytes.fromhex('eff309808169' '024a1160' 'fee7' '00bf' '00bf' '10000004'),
        marker_va=0x04000010,
    ),
}


# Build2344 keeps the same single fault entry but makes it resumable. The
# handler ORs one bit per trap site into shared+0xffc and returns to the
# instruction after the udf, so one boot reports how far the MCU actually got
# instead of only the first trap. Each site is a four-byte barrier (dsb/isb):
# skipping a barrier is the one edit that cannot corrupt the code around it, and
# the udf immediate is the mask itself, so the handler needs no table.
TRACE_PROBE = {
    0x2344: dict(
        stub_va=0x010019b0,
        # mrs r0,psp / ldr r3,[r0,#0x18] / ldrb r1,[r3,#3] / ldr r2,[pc,#0xc]
        # ldr r4,[r2] / orrs r4,r1 / str r4,[r2] / adds r3,#4
        # str r3,[r0,#0x18] / bx lr / nop / .word0x04000ffc
        stub=bytes.fromhex('eff30980' '8369' '1978' '034a' '1468' '0c43' '1460'
                           '0433' '8361' '7047' '00bf' 'fc0f0004'),
        marker_va=0x04000ffc,
        # (site, bit) in execution order. The first five are the reset path up to
        # the state dispatch, the last two the end of init and the idle loop.
        markers=((0x010019e2, 0x01), (0x010019fc, 0x02), (0x01001a2c, 0x04),
                 (0x01002aec, 0x08), (0x01002b26, 0x10), (0x01002b32, 0x20),
                 (0x01003018, 0x40), (0x01003036, 0x80)),
    ),
    # 2344 read back 0 everywhere, but 2341 had already shown that shared+0xffc
    # never takes a write; the word was dead, so that result says nothing about
    # the MCU. 2345 moves the same bitmap to shared+4, which is the word 2342
    # proved writable (features=7), and spends one bit on the barrier right after
    # the PSP switch so "stopped before the 0x40003034 load" is distinguishable
    # from "the channel is still wrong".
    0x2345: dict(
        stub_va=0x010019b0,
        stub=bytes.fromhex('eff30980' '8369' '1978' '034a' '1468' '0c43' '1460'
                           '0433' '8361' '7047' '00bf' '04000004'),
        marker_va=0x04000004,
        markers=((0x01001914, 0x01), (0x010019e2, 0x02), (0x01001a2c, 0x04),
                 (0x01002aec, 0x08), (0x01002b26, 0x10), (0x01002b32, 0x20),
                 (0x01003018, 0x40), (0x01003036, 0x80)),
    ),
    # 2345 proved the channel works but no marker fired, including the one that
    # sits on the isb right after the PSP switch. The reset entry's first store
    # targets the real 0x40022000; a posted write there can let the following
    # instructions retire and only stall at the first synchronisation event.
    # 2346 repoints that one literal at shared+0 (the same redirect 2340 used,
    # where 0xb landed) and fixes the mask byte, which 2345 read as [r3] instead
    # of [r3,#2] - it would have set 0xf0 for any hit, so the zero bitmap still
    # meant "no marker executed".
    0x2346: dict(
        stub_va=0x010019b0,
        stub=bytes.fromhex('eff30980' '8369' '9978' '034a' '1468' '0c43' '1460'
                           '0433' '8361' '7047' '00bf' '04000004'),
        marker_va=0x04000004,
        markers=((0x01001914, 0x01), (0x010019e2, 0x02), (0x01001a2c, 0x04),
                 (0x01002aec, 0x08), (0x01002b26, 0x10), (0x01002b32, 0x20),
                 (0x01003018, 0x40), (0x01003036, 0x80)),
        literals={0x281c: 0x04000000},
    ),
    # 2346 landed the redirected first store (version=0xb) and still fired no
    # marker, so the outstanding device write that stalls the barrier must be the
    # SECOND store, which still went to the real 0x40022004. 2347 sends both
    # stores to the shared page, leaving no device write before the isb, and the
    # first two bits then split "barrier passed" from "0x40003034 load passed".
    0x2347: dict(
        stub_va=0x010019b0,
        stub=bytes.fromhex('eff30980' '8369' '9978' '034a' '1468' '0c43' '1460'
                           '0433' '8361' '7047' '00bf' '04000004'),
        marker_va=0x04000004,
        markers=((0x01001914, 0x01), (0x010019e2, 0x02), (0x01001a2c, 0x04),
                 (0x01002aec, 0x08), (0x01002b26, 0x10), (0x01002b32, 0x20),
                 (0x01003018, 0x40), (0x01003036, 0x80)),
        literals={0x281c: 0x04000000, 0x2820: 0x04000008},
    ),
    # 2347 landed BOTH redirected stores (version=0xb, input_va=7) and still
    # fired no marker, so no device write is outstanding at the isb. The only
    # instruction left between the second store and the barrier that can fault
    # is the SHCSR write at 0x01001904 (r0 = 0xe000ed24). Every earlier probe
    # read the frame through PSP only, but that write happens BEFORE 0x01001908
    # sets PSP, so a fault there is taken on MSP and none of the stubs could
    # ever record it. 2348 restores the vendor's own MSP/PSP selection, records
    # the stacked PC into shared+0x08 (the word 2347 proved takes a write) and
    # stops there: one boot then separates "faulted at X" from "reached the
    # barrier", with the two redirected stores still proving the path.
    0x2348: dict(
        stub_va=0x010019b0,
        # tst.w lr,#4 / ite eq / mrseq r0,msp / mrsne r0,psp
        # ldr r3,[r0,#0x18] / ldr r2,[pc,#4] / str r3,[r2] / b .
        # .word 0x04000008
        stub=bytes.fromhex('1ef0040f' '0cbf' 'eff30880' 'eff30980' '8369'
                           '014a' '1360' 'fee7' '00bf' '08000004'),
        marker_va=0x04000008,
        markers=((0x01001914, 0x01),),
        literals={0x281c: 0x04000000, 0x2820: 0x04000004},
    ),
    # 2348 gave the handler the vendor's MSP/PSP selection and recorded nothing:
    # version=0xb and features=7 still landed, so both stores ran, but no fault
    # was taken anywhere between them and the barrier and the barrier marker
    # never fired either. The one memory access left in that window is the SCS
    # write at 0x01001904 (r0 = 0xe000ed24, r1 = 0x70000). Either it stalls the
    # core or it is discarded; 2349 repoints that literal at shared+0x0c so the
    # store cannot stall, and output_va then proves the instruction ran.
    0x2349: dict(
        stub_va=0x010019b0,
        stub=bytes.fromhex('1ef0040f' '0cbf' 'eff30880' 'eff30980' '8369'
                           '014a' '1360' 'fee7' '00bf' '08000004'),
        marker_va=0x04000008,
        markers=((0x01001914, 0x01),),
        literals={0x281c: 0x04000000, 0x2820: 0x04000004, 0x2824: 0x0400000c},
    ),
    # 2349 proved the SCS store itself executes (output_va=0x70000) and that no
    # fault is taken afterwards, yet the barrier at 0x01001914 is still never
    # reached and the udf that replaced it never traps. Either the core does not
    # take the 32-bit udf, or the vectors do not lead to 0x010019b0. 2350 stops
    # relying on exceptions altogether: the barrier becomes `bl 0x010019b0` and
    # the stub ORs bit 0 into shared+0x08 with ordinary instructions, then
    # returns with bx lr. The stub starts with mov r0,lr / lsrs r0,#28 / cbnz so
    # an exception that somehow does land here parks instead of faking a hit.
    0x2350: dict(
        stub_va=0x010019b0,
        # mov r0,lr / lsrs r0,r0,#28 / cbnz r0,park
        # ldr r3,[pc,#16] / ldr r2,[r3] / movs r1,#1 / orrs r2,r1 / str r2,[r3]
        # bx lr / nop / park: b . / nop / .word 0x04000008
        stub=bytes.fromhex('7046' '000f' '30b9' '044b' '1a68' '0121' '0a43'
                           '1a60' '7047' '00bf' 'fee7' '00bf' '08000004'),
        marker_va=0x04000008,
        calls={0x01001914: 0x010019b0},
        literals={0x281c: 0x04000000, 0x2820: 0x04000004, 0x2824: 0x0400000c},
    ),
    # 2350 proved the barrier at 0x01001914 IS reached (input_va=0x04002001) and
    # that bx lr resumes cleanly, so the 32-bit udf never trapped and every
    # earlier "no marker" reading was blind. 2351 turns the same trick into a
    # progress ladder: nine barriers along the reset path each become
    # `bl 0x010019b0`, and the stub stores the *site address* in shared+0x08 and
    # returns. The last site written is how far the MCU actually got.
    0x2351: dict(
        stub_va=0x010019b0,
        # push {r0,r1,lr} / mov r1,lr / lsrs r1,#28 / cbnz r1,park
        # mov r0,lr / subs r0,#5 (drop the Thumb bit and the four-byte call)
        # ldr r3,=shared+0x08 / str r0,[r3] / pop {r0,r1,pc} / park: b .
        stub=bytes.fromhex('03b5' '7146' '090f' '21b9' '7046' '0538' '024b'
                           '1860' '03bd' 'fee7' '00bf' '00bf' '08000004'),
        marker_va=0x04000008,
        calls={va: 0x010019b0 for va in (
            0x01001914, 0x010019e2, 0x010019fc, 0x01001a2c, 0x01002aec,
            0x01002b26, 0x01002b32, 0x01003018, 0x01003036)},
        literals={0x281c: 0x04000000, 0x2820: 0x04000004, 0x2824: 0x0400000c},
    ),
    # 2351 stopped at the very first rung: the MCU reaches the barrier at
    # 0x01001914 and never calls the helper at 0x010019e2. Between them sits the
    # first real device access of the whole run, `ldr r4,[0x40003034]` at
    # 0x0100191a, because 2351 already sends all three stores to the shared page.
    # 2352 repoints that read at shared+0x14 (group_stride, 0xa0, so bit 7 stays
    # set and the branch after the cache calls is unchanged) and leaves the
    # ladder in place: if the rungs advance, the read is the wall.
    0x2352: dict(
        stub_va=0x010019b0,
        stub=bytes.fromhex('03b5' '7146' '090f' '21b9' '7046' '0538' '024b'
                           '1860' '03bd' 'fee7' '00bf' '00bf' '08000004'),
        marker_va=0x04000008,
        calls={va: 0x010019b0 for va in (
            0x01001914, 0x010019e2, 0x010019fc, 0x01001a2c, 0x01002aec,
            0x01002b26, 0x01002b32, 0x01003018, 0x01003036)},
        literals={0x281c: 0x04000000, 0x2820: 0x04000004, 0x2824: 0x0400000c,
                  0x282c: 0x04000014},
    ),
    # 2352 changed nothing: the 0x40003034 load is not the wall. The only other
    # work between the barrier and the first rung is `bl 0x01003126`, and that
    # function is pure MPU programming: it writes RBAR/RASR at 0xe000ed9c for a
    # dozen regions and then, at 0x01003282, does `movs r0,#3 ; str r0,[r1,#-8]`
    # i.e. MPU_CTRL = ENABLE|PRIVDEFENA. The very next fetch runs under the new
    # map, so 2353 nops exactly that store (`41 f8 08 0c` -> two nops) and leaves
    # everything else, including the region writes, alone.
    0x2353: dict(
        stub_va=0x010019b0,
        stub=bytes.fromhex('03b5' '7146' '090f' '21b9' '7046' '0538' '024b'
                           '1860' '03bd' 'fee7' '00bf' '00bf' '08000004'),
        marker_va=0x04000008,
        calls={va: 0x010019b0 for va in (
            0x01001914, 0x010019e2, 0x010019fc, 0x01001a2c, 0x01002aec,
            0x01002b26, 0x01002b32, 0x01003018, 0x01003036)},
        patches={0x01003282: ('41f8080c', '00bf00bf')},
        literals={0x281c: 0x04000000, 0x2820: 0x04000004, 0x2824: 0x0400000c,
                  0x282c: 0x04000014},
    ),
    # 2352 and 2353 both left the ladder word at 0x01001914, whether the first
    # peripheral read or the MPU enable was neutralised. A core that resets and
    # re-enters the reset path would rewrite that same word every pass, so 2354
    # does not change any firmware behaviour at all: it only makes the stub count
    # its own entries in shared+0x10 (the groups word, reported verbatim) with
    # r2 now saved across the call. One pass means the core stopped; a large
    # count means it is looping back to the reset vector.
    0x2354: dict(
        stub_va=0x010019b0,
        # push {r0,r1,r2,lr} / mov r0,lr / subs r0,#5
        # ldr r3,=shared+0x08 / str r0,[r3]
        # ldr r2,=shared+0x10 / ldr r3,[r2] / adds r3,#1 / str r3,[r2]
        # pop {r0,r1,r2,pc}
        stub=bytes.fromhex('07b5' '7046' '0538' '034b' '1860' '034a' '1368'
                           '0133' '1360' '07bd' '08000004' '10000004'),
        marker_va=0x04000008,
        counter_va=0x04000010,
        calls={va: 0x010019b0 for va in (
            0x01001914, 0x010019e2, 0x010019fc, 0x01001a2c, 0x01002aec,
            0x01002b26, 0x01002b32, 0x01003018, 0x01003036)},
        literals={0x281c: 0x04000000, 0x2820: 0x04000004, 0x2824: 0x0400000c,
                  0x282c: 0x04000014},
    ),
    # 2354 counted exactly one rung entry, so the core really does stop inside
    # this window and does not reset. The window holds two calls that touch the
    # PPB and nothing else: `bl 0x01003126` (MPU region programming, no barrier
    # inside) and `bl 0x10019d8` (one store to 0xe000ed84). 2355 removes the
    # MPU call only, as two nops, so the next thing executed is the single SCS
    # store and then the rung at 0x010019e2. Rung 2 appearing means the MPU call
    # was the wall; staying at rung 1 means the 0xe000ed84 store was.
    0x2355: dict(
        stub_va=0x010019b0,
        stub=bytes.fromhex('07b5' '7046' '0538' '034b' '1860' '034a' '1368'
                           '0133' '1360' '07bd' '08000004' '10000004'),
        marker_va=0x04000008,
        counter_va=0x04000010,
        calls={va: 0x010019b0 for va in (
            0x01001914, 0x010019e2, 0x010019fc, 0x01001a2c, 0x01002aec,
            0x01002b26, 0x01002b32, 0x01003018, 0x01003036)},
        patches={0x01001922: ('01f000fc', '00bf00bf')},
        literals={0x281c: 0x04000000, 0x2820: 0x04000004, 0x2824: 0x0400000c,
                  0x282c: 0x04000014},
    ),
    # 2355 removed the MPU call and still stopped at rung 0x01001914, so the only
    # device access left between rung 1 and rung 2 is the helper at 0x010019d8:
    # `mov.w r1,#0 ; ldr r0,=0xe000ed84 ; str r1,[r0] ; bx lr`. 0xe000ed84 is
    # CSSELR on a Cortex-M7, i.e. a cache-size selection write. 2356 nops the
    # load and the store (`79 48 01 60` -> two nops) on top of 2355, leaving the
    # window with NO device access at all. If rung 2 appears the CSSELR write is
    # the wall; if it still does not, the ladder cannot span that gap and the
    # return path itself has to be questioned.
    0x2356: dict(
        stub_va=0x010019b0,
        stub=bytes.fromhex('07b5' '7046' '0538' '034b' '1860' '034a' '1368'
                           '0133' '1360' '07bd' '08000004' '10000004'),
        marker_va=0x04000008,
        counter_va=0x04000010,
        calls={va: 0x010019b0 for va in (
            0x01001914, 0x010019e2, 0x010019fc, 0x01001a2c, 0x01002aec,
            0x01002b26, 0x01002b32, 0x01003018, 0x01003036)},
        patches={0x01001922: ('01f000fc', '00bf00bf'),
                 0x10019dc: ('79480160', '00bf00bf')},
        literals={0x281c: 0x04000000, 0x2820: 0x04000004, 0x2824: 0x0400000c,
                  0x282c: 0x04000014},
    ),
    # 2356 removed every device access between rung 1 and rung 2 and the ladder
    # STILL stopped at 0x01001914 with exactly one entry. That can only mean the
    # ladder itself cannot carry execution past rung 1, so 2357 stops chasing the
    # firmware and tests the instrument instead: the stub keeps recording the
    # site and the count, but instead of returning to lr it overwrites the
    # stacked return address with 0x0100192a - the call site of the helper whose
    # first instruction is rung 2. Every entry now bounces back there, so a
    # working return shows site 0x010019e2 with a huge count, while site
    # 0x01001914 with count 9 means execution never leaves the stub at all.
    0x2357: dict(
        stub_va=0x010019b0,
        # push {r0,r1,r2,lr} / mov r0,lr / subs r0,#5 / ldr r3,=shared+0x08
        # str r0,[r3] / ldr r2,=shared+0x10 / ldr r3,[r2] / adds r3,#1
        # str r3,[r2] / ldr r2,=0x0100192a / str r2,[sp,#0xc] / pop {r0,r1,r2,pc}
        stub=bytes.fromhex('07b5' '7046' '0538' '044b' '1860' '044a' '1368'
                           '0133' '1360' '034a' '0392' '07bd'
                           '08000004' '10000004' '2a190001'),
        marker_va=0x04000008,
        counter_va=0x04000010,
        bounce_va=0x0100192a,
        calls={va: 0x010019b0 for va in (
            0x01001914, 0x010019e2, 0x010019fc, 0x01001a2c, 0x01002aec,
            0x01002b26, 0x01002b32, 0x01003018, 0x01003036)},
        patches={0x01001922: ('01f000fc', '00bf00bf'),
                 0x10019dc: ('79480160', '00bf00bf')},
        literals={0x281c: 0x04000000, 0x2820: 0x04000004, 0x2824: 0x0400000c,
                  0x282c: 0x04000014},
    ),
    # 2357 forced the return target to 0x0100192a and the rung-2 helper still
    # never ran, so the stub itself is now the prime suspect. The 2351-2357
    # stub pushes, stores the site, and pops {r0,r1,r2,pc}; if PSP is not
    # backed by real writable RAM at 0x0203f000 the push "succeeds" into a
    # write-ignore region and the pop loads garbage into pc, which kills the
    # core at exactly the first entry no matter what the firmware does. 2358
    # therefore removes the stack completely: the return address never leaves
    # lr, the stub only touches r3 and r12 (both already clobbered by every
    # earlier stub) and keeps APSR intact by using the S-less 32-bit forms.
    # If the ladder now advances past rung 1 the earlier verdicts were an
    # artefact of the stack; if site 0x01001914 still shows one entry with a
    # stack-free return, the barrier itself cannot be replaced by a call.
    0x2358: dict(
        stub_va=0x010019b0,
        # mov r12,lr / sub.w r12,r12,#5 / ldr r3,=shared+0x08 / str r12,[r3]
        # ldr r3,=shared+0x10 / ldr r12,[r3] / add.w r12,r12,#1 / str r12,[r3]
        # bx lr
        stub=bytes.fromhex('f446' 'acf1050c' '054b' 'c3f800c0' '044b' 'd3f800c0'
                           '0cf1010c' 'c3f800c0' '7047' '08000004' '10000004'),
        marker_va=0x04000008,
        counter_va=0x04000010,
        calls={va: 0x010019b0 for va in (
            0x01001914, 0x010019e2, 0x010019fc, 0x01001a2c, 0x01002aec,
            0x01002b26, 0x01002b32, 0x01003018, 0x01003036)},
        patches={0x01001922: ('01f000fc', '00bf00bf'),
                 0x10019dc: ('79480160', '00bf00bf')},
        literals={0x281c: 0x04000000, 0x2820: 0x04000004, 0x2824: 0x0400000c,
                  0x282c: 0x04000014},
    ),
    # 2358 proved the stack was the wall: the stack-free stub returns, rung 2
    # (0x010019e2) is recorded and the count reached 2. The next stop is the
    # cache-enable helper itself, whose body is exactly three device accesses:
    # `str r1,[0xe000ef50]` (ICIALLU), `ldr r1,[0xe000ed14]` (CCR) then
    # `str r1,[r0]` with bit 0x20000 set (CCR.IC = 1). On M-profile a read of
    # CCR is always safe, so 2359 nops only the two stores and keeps the read:
    # rung 3 appearing means one of those two writes takes the core down, and
    # the firmware can then be brought up with caches off.
    0x2359: dict(
        stub_va=0x010019b0,
        stub=bytes.fromhex('f446' 'acf1050c' '054b' 'c3f800c0' '044b' 'd3f800c0'
                           '0cf1010c' 'c3f800c0' '7047' '08000004' '10000004'),
        marker_va=0x04000008,
        counter_va=0x04000010,
        calls={va: 0x010019b0 for va in (
            0x01001914, 0x010019e2, 0x010019fc, 0x01001a2c, 0x01002aec,
            0x01002b26, 0x01002b32, 0x01003018, 0x01003036)},
        patches={0x01001922: ('01f000fc', '00bf00bf'),
                 0x10019dc: ('79480160', '00bf00bf'),
                 0x010019f0: ('0160', '00bf'),      # ICIALLU write
                 0x010019fa: ('0160', '00bf')},     # CCR.IC write
        literals={0x281c: 0x04000000, 0x2820: 0x04000004, 0x2824: 0x0400000c,
                  0x282c: 0x04000014},
    ),
    # 2359 nop'd both cache writes and the core still died at rung 2, so the
    # only device access left in that helper is the CCR read at 0x010019f4.
    # Rather than spend a boot on a yes/no, 2360 splits the window in three by
    # turning two more four-byte instructions into call sites: the `isb` at
    # 0x010019e6 and the `orr r1,r1,#0x20000` at 0x010019f6 (whose only
    # consumer, the store, is already a nop). Site 0x010019e6 with three hits
    # means the kill is between the isb and the orr, i.e. the CCR read; site
    # 0x010019f6 with four means the read survives and rung 3 itself fails;
    # site 0x010019fc means the helper is clear and the wall moved on.
    0x2360: dict(
        stub_va=0x010019b0,
        stub=bytes.fromhex('f446' 'acf1050c' '054b' 'c3f800c0' '044b' 'd3f800c0'
                           '0cf1010c' 'c3f800c0' '7047' '08000004' '10000004'),
        marker_va=0x04000008,
        counter_va=0x04000010,
        calls={**{va: 0x010019b0 for va in (
                    0x01001914, 0x010019e2, 0x010019fc, 0x01001a2c, 0x01002aec,
                    0x01002b26, 0x01002b32, 0x01003018, 0x01003036)},
               # explicit words: neither of these is a barrier any more
               0x010019e6: (0x010019b0, 'bff36f8f'),     # isb sy
               0x010019f6: (0x010019b0, '41f40031')},    # orr r1,r1,#0x20000
        patches={0x01001922: ('01f000fc', '00bf00bf'),
                 0x10019dc: ('79480160', '00bf00bf'),
                 0x010019f0: ('0160', '00bf'),
                 0x010019fa: ('0160', '00bf')},
        literals={0x281c: 0x04000000, 0x2820: 0x04000004, 0x2824: 0x0400000c,
                  0x282c: 0x04000014},
    ),
    # 2360 named the CCR read as the wall, which is impossible on a working
    # M-profile core: 0xe000ed14 is internal to the core and privileged code
    # cannot fault on it. The answer is in the reset prologue. Its first three
    # stores were redirected to RAM since 2339 - 0x40022000 <- 0xb,
    # 0x40022004 <- 0x7 and, crucially, 0xe000ed24 (SHCSR) <- 0x70000 - so the
    # MCU has been running with its own vendor bring-up writes silently
    # swallowed, and every real bus access since has killed it. 2361 puts those
    # three literals back to the vendor values and leaves only the 0x40003034
    # read redirected, so the ladder can say whether the prologue is what makes
    # the peripheral/PPB space reachable.
    0x2361: dict(
        stub_va=0x010019b0,
        stub=bytes.fromhex('f446' 'acf1050c' '054b' 'c3f800c0' '044b' 'd3f800c0'
                           '0cf1010c' 'c3f800c0' '7047' '08000004' '10000004'),
        marker_va=0x04000008,
        counter_va=0x04000010,
        calls={**{va: 0x010019b0 for va in (
                    0x01001914, 0x010019e2, 0x010019fc, 0x01001a2c, 0x01002aec,
                    0x01002b26, 0x01002b32, 0x01003018, 0x01003036)},
               0x010019e6: (0x010019b0, 'bff36f8f'),
               0x010019f6: (0x010019b0, '41f40031')},
        patches={0x01001922: ('01f000fc', '00bf00bf'),
                 0x10019dc: ('79480160', '00bf00bf'),
                 0x010019f0: ('0160', '00bf'),
                 0x010019fa: ('0160', '00bf')},
        # vendor values: the two MCU configuration stores and SHCSR
        literals={0x281c: 0x40022000, 0x2820: 0x40022004, 0x2824: 0xE000ED24,
                  0x282c: 0x04000014},
    ),
    # 2361 put the vendor prologue back and the ladder LOST one rung: site
    # 0x010019e2 with two entries, where 2360 reached 0x010019e6 with three,
    # while every hardware word stayed identical. So those three real stores do
    # not unlock the peripheral space; they make the stall come sooner. 2362
    # returns to 2360's redirects exactly and changes one instruction: the CCR
    # read (`ldr r1,[r0]` at 0x010019f4) becomes a nop, which is the last device
    # access left in the cache helper. If the ladder now passes the orr rung the
    # firmware runs with no SCB reads, and the next stop is the first NVIC use.
    0x2362: dict(
        stub_va=0x010019b0,
        stub=bytes.fromhex('f446' 'acf1050c' '054b' 'c3f800c0' '044b' 'd3f800c0'
                           '0cf1010c' 'c3f800c0' '7047' '08000004' '10000004'),
        marker_va=0x04000008,
        counter_va=0x04000010,
        calls={**{va: 0x010019b0 for va in (
                    0x01001914, 0x010019e2, 0x010019fc, 0x01001a2c, 0x01002aec,
                    0x01002b26, 0x01002b32, 0x01003018, 0x01003036)},
               0x010019e6: (0x010019b0, 'bff36f8f'),
               0x010019f6: (0x010019b0, '41f40031')},
        patches={0x01001922: ('01f000fc', '00bf00bf'),
                 0x10019dc: ('79480160', '00bf00bf'),
                 0x010019f0: ('0160', '00bf'),
                 0x010019f4: ('0168', '00bf'),      # the CCR read itself
                 0x010019fa: ('0160', '00bf')},
        literals={0x281c: 0x04000000, 0x2820: 0x04000004, 0x2824: 0x0400000c,
                  0x282c: 0x04000014},
    ),
    # 2362 left no device access at all between the isb rung and the orr rung
    # and the core still stopped there, and the shared page is only sampled
    # after the poll loop gives up a full second later. Twenty instructions in
    # one second is not a running core, so 2363 stops probing the firmware and
    # tests the core itself: the reset vector is redirected at the entry, and
    # 0x010018ec becomes `ldr r3,=shared+0x10 / ldr r2,[r3] / adds r2,#1 /
    # str r2,[r3] / b .-8`. Nothing else runs. groups then reads 8 if the loop
    # never executed, a small offset if the core took a few steps and stalled,
    # and an arbitrary wrapped value if the core free-runs for the whole second.
    0x2363: dict(
        stub_va=0x010019b0,
        stub=bytes.fromhex('f446' 'acf1050c' '054b' 'c3f800c0' '044b' 'd3f800c0'
                           '0cf1010c' 'c3f800c0' '7047' '08000004' '10000004'),
        marker_va=0x04000008,
        counter_va=0x04000010,
        calls={},
        patches={0x010018ec: ('72b626484ff00b01016025484ff00701',
                              '024b1a6801321a60fce700bf10000004')},
        literals={},
    ),
    # 2362 nop'd every device access in the cache helper and the core still
    # stopped at the isb rung, which forced 2363. 2363 ran no firmware at all
    # and the same stub counter climbed to 406,670,326 inside the one-second
    # poll window: the core free-runs, so its clock, its fetch path and the
    # shared page all work, and every earlier stall is real control flow.
    #
    # The stop is between 0x010019e6 (isb rung) and 0x010019f6 (orr rung), and
    # that window holds only `mov.w r1,#0`, two 16-bit literal loads and two
    # nops - every one of them dead here, because the stores they feed are
    # already nop'd. 2364 turns all three 4-byte windows into rungs as well, so
    # one boot reports the exact 4 bytes where the core dies:
    #   site 0x010019e6 -> never re-entered after the isb rung
    #   site 0x010019ea -> died inside the first new rung
    #   site 0x010019ee -> died inside the second
    #   site 0x010019f2 -> died inside the third
    #   site 0x010019f6 -> the window is clear and the orr rung is the wall
    0x2364: dict(
        stub_va=0x010019b0,
        stub=bytes.fromhex('f446' 'acf1050c' '054b' 'c3f800c0' '044b' 'd3f800c0'
                           '0cf1010c' 'c3f800c0' '7047' '08000004' '10000004'),
        marker_va=0x04000008,
        counter_va=0x04000010,
        calls={**{va: 0x010019b0 for va in (
                    0x01001914, 0x010019e2, 0x010019fc, 0x01001a2c, 0x01002aec,
                    0x01002b26, 0x01002b32, 0x01003018, 0x01003036)},
               # the whole cache helper, in execution order
               0x010019e6: (0x010019b0, 'bff36f8f'),     # isb sy
               0x010019ea: (0x010019b0, '4ff00001'),     # mov.w r1,#0
               0x010019ee: (0x010019b0, '76480160'),     # ldr r0,[pc] / str r1,[r0]
               0x010019f2: (0x010019b0, '76480168'),     # ldr r0,[pc] / ldr r1,[r0]
               0x010019f6: (0x010019b0, '41f40031')},    # orr r1,r1,#0x20000
        # 0x010019f0 and 0x010019f4 are gone: both now sit inside rungs.
        patches={0x01001922: ('01f000fc', '00bf00bf'),
                 0x10019dc: ('79480160', '00bf00bf'),
                 0x010019fa: ('0160', '00bf')},
        literals={0x281c: 0x04000000, 0x2820: 0x04000004, 0x2824: 0x0400000c,
                  0x282c: 0x04000014},
    ),
    # 2364 answered, and not the way the address theory predicted: the rung at
    # 0x010019ea was entered AND returned (counter 12 = 8 + four entries), and
    # the core then died before the next rung at 0x010019ee. Adding four bytes
    # of rungs moved the stop forward by four bytes, so the stop is not pinned
    # to an address in that window. 2365 asks the narrower question: is the
    # instruction at 0x010019ee itself unsurvivable, or is it the `bl` we put
    # there? The ladder still runs to rung 4, then 0x010019ee becomes a plain
    # counter loop on shared+0x14 (group_stride, seeded 0xa0, +4 per turn) with
    # its literal at 0x010019fc. If group_stride climbs, the core executes
    # happily at that exact address and the wall is the call/return, not the
    # place; if it stays 0xa0, the address really is unreachable after the
    # ladder and the next question is what the ladder left behind.
    0x2365: dict(
        stub_va=0x010019b0,
        stub=bytes.fromhex('f446' 'acf1050c' '054b' 'c3f800c0' '044b' 'd3f800c0'
                           '0cf1010c' 'c3f800c0' '7047' '08000004' '10000004'),
        marker_va=0x04000008,
        counter_va=0x04000010,
        calls={**{va: 0x010019b0 for va in (
                    0x01001914, 0x010019e2, 0x01001a2c, 0x01002aec,
                    0x01002b26, 0x01002b32, 0x01003018, 0x01003036)},
               0x010019e6: (0x010019b0, 'bff36f8f'),     # isb sy
               0x010019ea: (0x010019b0, '4ff00001')},    # mov.w r1,#0
        # 0x010019ee .. 0x010019ff: ldr.w r3,=shared+0x14 / ldr r2,[r3] /
        # adds r2,#4 / str r2,[r3] / b .-8 / nop / .word 0x04000014
        patches={0x01001922: ('01f000fc', '00bf00bf'),
                 0x10019dc: ('79480160', '00bf00bf'),
                 0x010019ee: ('764801607648016841f400310160bff34f8f',
                              'dff80c301a6804321a60fce700bf14000004')},
        literals={0x281c: 0x04000000, 0x2820: 0x04000004, 0x2824: 0x0400000c,
                  0x282c: 0x04000014},
    ),
    # 2365 answered with one turn of the loop and nothing more: group_stride
    # went 0xa0 -> 0xa4 and stopped. That is not a free-run and not a dead
    # address, so the next step is the controlled A/B against 2363: the very
    # same counter loop byte for byte (ldr / ldr / adds / str / b, counter in
    # register r2, one store per turn) but placed at 0x010019ee instead of
    # 0x010018ec, reached by a direct branch from the reset vector with no
    # ladder and no prologue in between. If groups climbs here, the address is
    # fine on its own and the ladder is what leaves the core unable to
    # continue; if groups stays 8, that address cannot host a loop at all.
    0x2366: dict(
        stub_va=0x010019b0,
        stub=bytes.fromhex('f446' 'acf1050c' '054b' 'c3f800c0' '044b' 'd3f800c0'
                           '0cf1010c' 'c3f800c0' '7047' '08000004' '10000004'),
        marker_va=0x04000008,
        counter_va=0x04000010,
        calls={},
        patches={0x010018ec: ('72b626484ff00b01016025484ff00701',
                              '7fe000bf00bf00bf00bf00bf00bf00bf'),
                 # 0x010019ee: ldr r3,=shared+0x10 / ldr r2,[r3] / adds r2,#1 /
                 # str r2,[r3] / b .-8 / .word 0x04000010, literal at 0x010019f8
                 0x010019ee: ('764801607648016841f400310160',
                              '024b1a6801321a60fce710000004')},
        literals={},
    ),
    # 2366 put the 2363 loop at 0x010019ee, entered by a single branch from
    # the reset vector, and it turned exactly ONCE - while the same bytes at
    # 0x010018ec turned 406 million times in 2363. 2367 therefore drops
    # branching entirely and asks a simpler question: how far can the core
    # execute at all? The reset entry becomes a straight line of 128
    # `adds r2,#1 / str r2,[r3]` pairs, one store every four bytes, from
    # 0x010018ec to 0x01001af0, then `b .`. groups-8 is the number of stores
    # that landed, so the frontier is 0x010018ec + 4*(groups-8) with 4-byte
    # resolution, and no branch is involved anywhere before the park.
    0x2367: dict(
        stub_va=0x01001d00,
        stub=bytes.fromhex('f446' 'acf1050c' '054b' 'c3f800c0' '044b' 'd3f800c0'
                           '0cf1010c' 'c3f800c0' '7047' '08000004' '10000004'),
        marker_va=0x04000008,
        counter_va=0x04000010,
        calls={},
        patches={
            0x010018ec: (
            '72b626484ff00b01016025484ff0070101602448',
            '824b1a6801321a6001321a6001321a6001321a60'),
            0x01001900: (
            '4ff4e0210160234880f309884ff0020080f31488bff36f8f1f48046804f08004'
            '204601f000fc00f057f800f05af800f07cf834b31948017819b3194819491a4a'
            'f0e80234e1e80234f0e80234e1e80234f0e80234e1e80234f0e80234e1e80234'
            '9142edd9114a4ff000004ff00003e1e80203e1e80203e1e80203e1e802039142'
            'f5d901f0b3b800bf002002400420024024ed00e000f003023430004078bc0203'
            '000080030000000210c2020244c902021ef0040f0cbfeff30880eff309802de9'
            'f04f6946eff3058200f0f0fb08b000bd4ff0ff30704700004ff0000179480160'
            '7047bff34f8fbff36f8f4ff00001764801607648016841f400310160bff34f8f'
            'bff36f8f7047bff34f8fbff36f8f6f48016821f4003101604ff000016a480160'
            'bff34f8fbff36f8f704710b4bff34f8f674868490968c1f34e32c1f3c9034fea'
            '421463f39f740460013bfad5013af4d5bff34f8f5d48016841f480310160bff3'
            '4f8fbff36f8f10bc704710b4bff34f8f5648016821f480310160574855490968'
            'c1f34e32c1f3c9034fea421463f39f740460013bfad5013af4d5bff34f8fbff3'
            '6f8f10bc704710b4bff34f8f4b4849490968c1f34e32c1f3c9034fea421463f3'
            '9f740460013bfad5013af4d5bff34f8fbff36f8f10bc704710b4bff34f8f3c48'
            '3c490968c1f34e32c1f3c9034fea421463f39f740460013bfad5013a',
            '01321a6001321a6001321a6001321a6001321a6001321a6001321a6001321a60'
            '01321a6001321a6001321a6001321a6001321a6001321a6001321a6001321a60'
            '01321a6001321a6001321a6001321a6001321a6001321a6001321a6001321a60'
            '01321a6001321a6001321a6001321a6001321a6001321a6001321a6001321a60'
            '01321a6001321a6001321a6001321a6001321a6001321a6001321a6001321a60'
            '01321a6001321a6001321a6001321a6001321a6001321a6001321a6001321a60'
            '01321a6001321a6001321a6001321a6001321a6001321a6001321a6001321a60'
            '01321a6001321a6001321a6001321a6001321a6001321a6001321a6001321a60'
            '01321a6001321a6001321a6001321a6001321a6001321a6001321a6001321a60'
            '01321a6001321a6001321a6001321a6001321a6001321a6001321a6001321a60'
            '01321a6001321a6001321a6001321a6001321a6001321a6001321a6001321a60'
            '01321a6001321a6001321a6001321a6001321a6001321a6001321a6001321a60'
            '01321a6001321a6001321a6001321a6001321a6001321a6001321a6001321a60'
            '01321a6001321a6001321a6001321a6001321a6001321a6001321a6001321a60'
            '01321a6001321a6001321a6001321a6001321a6001321a6001321a6001321a60'
            '01321a6001321a6001321a6001321a60fee700bf00bf00bf10000004')},
        literals={},
    ),
    # 2367 showed that a 128-store straight line starting at the reset vector
    # never landed a single store, while 2363's fourteen-byte loop at the very
    # same address turned 406 million times. The only difference in the first
    # four instructions is the literal: 2363 loads it from 0x010018f8, twelve
    # bytes past the load, and 2367 from 0x01001af8, 520 bytes away. The vendor
    # code at 0x010019ee does exactly the same thing with `ldr r0,[pc,#0x1d8]`,
    # and every ladder build died in that window, so 2368 repeats 2363 byte for
    # byte and moves ONLY the literal to the far slot at 0x01001af8.
    #   groups-8 == 0        -> a distant data read from the code region hangs
    #                           the core, which would explain the whole ladder
    #   groups-8 large       -> distance is harmless and 2367 failed for
    #                           another reason (the 528-byte overwrite)
    0x2368: dict(
        stub_va=0x010019b0,
        stub=bytes.fromhex('f446' 'acf1050c' '054b' 'c3f800c0' '044b' 'd3f800c0'
                           '0cf1010c' 'c3f800c0' '7047' '08000004' '10000004'),
        marker_va=0x04000008,
        counter_va=0x04000010,
        calls={},
        patches={0x010018ec: ('72b626484ff00b010160',
                              '824b1a6801321a60fce7'),
                 # ldr r3,=0x04000010 placed 520 bytes away from the loader
                 0x01001af8: ('fad5013a', '10000004')},
        literals={},
    ),
    # 2368 turned that hypothesis into a single-variable result: same loop, same
    # address, literal 520 bytes away instead of 12, and the count went from
    # 406 million to zero with no fault recorded. What is still open is whether
    # the far read hangs the core or merely returns a wrong value. 2369 answers
    # it by removing the far read from the data path that matters: the counter
    # pointer is built with movs/lsls/adds instead of a literal, and the far
    # slot is read once, before the loop, into r0 and thrown away.
    #   groups-8 == 0     -> the far read itself stops the core
    #   groups-8 large    -> the far read returns garbage but does not stall,
    #                        so 2368's zero was a wrong pointer, not a hang
    0x2369: dict(
        stub_va=0x010019b0,
        stub=bytes.fromhex('f446' 'acf1050c' '054b' 'c3f800c0' '044b' 'd3f800c0'
                           '0cf1010c' 'c3f800c0' '7047' '08000004' '10000004'),
        marker_va=0x04000008,
        counter_va=0x04000010,
        calls={},
        patches={0x010018ec: ('72b626484ff00b01016025484ff00701',
                              '01239b0610331a68804801321a60fce7'),
                 # the far slot, read once into r0 and discarded
                 0x01001af8: ('fad5013a', '10000004')},
        literals={},
    ),
    # 2369 removed every other explanation: the counter pointer came from
    # immediates and the far read's result went into r0, which nothing reads
    # again, yet the count stayed at 8. So the read itself stops the core -
    # but 0x01001af8 and 0x010018ec are in the SAME 4 KiB page with the same
    # descriptor, so this cannot be a mapping difference. 2370 therefore sweeps
    # the address space instead of guessing: the loop probes 0x01001900,
    # 0x01001a00, 0x01001b00, ... one 0x100 step per turn, incrementing the
    # counter after each successful read. groups-8 is how many probes completed,
    # so the first address that hangs the core is 0x01001900 + 0x100*(groups-8)
    # and a change in the site word means the probe faulted instead of hanging.
    0x2370: dict(
        stub_va=0x010019b0,
        stub=bytes.fromhex('f446' 'acf1050c' '054b' 'c3f800c0' '044b' 'd3f800c0'
                           '0cf1010c' 'c3f800c0' '7047' '08000004' '10000004'),
        marker_va=0x04000008,
        counter_va=0x04000010,
        calls={},
        patches={0x010018ec: ('72b626484ff00b01016025484ff00701016024484ff4e02101602348',
                              '0124240604f5c85401239b0610331a68206804f5807401321a60f9e7')},
        literals={},
    ),
    # 2370 found the edge at 0x01001a00: the probe at 0x01001900 returned (it
    # sits inside this loop's own code, i.e. bytes the core had already fetched)
    # and the very next probe hung the core. Same 4 KiB page, same descriptor, so
    # the difference has to be whether the core has fetched those bytes. 2371
    # narrows the same sweep to 0x10 steps from 0x01001900 to 0x01001a00:
    #   one probe  -> the window ends right after the loop's own last byte,
    #                 which is what "only fetched bytes are readable" predicts
    #   many probes-> 0x01001900..0x010019ff is readable without being fetched,
    #                 so the limit is a region size, not the fetch stream
    0x2371: dict(
        stub_va=0x010019b0,
        stub=bytes.fromhex('f446' 'acf1050c' '054b' 'c3f800c0' '044b' 'd3f800c0'
                           '0cf1010c' 'c3f800c0' '7047' '08000004' '10000004'),
        marker_va=0x04000008,
        counter_va=0x04000010,
        calls={},
        patches={0x010018ec: ('72b626484ff00b01016025484ff00701016024484ff4e02101602348',
                              '0124240604f5c85401239b0610331a68206804f1100401321a60f9e7')},
        literals={},
    ),
    # 2371 answered, and not the way the build was designed to: sixteen 0x10-step
    # probes returned (0x01001900..0x010019f0) and 0x01001a00 hung. That kills
    # both readings it was meant to choose between - "only fetched bytes" would
    # have stopped after one or two probes, and 0x010019f0 with 0x01001a00 share
    # a 4 KiB page, a leaf and a backing page. What fits 2363/2365/2368/2369 is a
    # 512-byte aligned fetch window at 0x01001800..0x010019ff, which 2366 does
    # not fit. 2372 stops guessing at one address and maps the whole 64 KiB code
    # section instead, in the same 0x100 steps, from 0x01000000 to 0x01010000:
    #   a readable prefix ending at 0x1a00        -> a region limit
    #   only the blocks that hold executed bytes  -> a fetch-derived window
    #   all 256 blocks readable                  -> the 2371 hang was not the read
    # The loop stores 0x01000000 into shared+0x08 before the first probe, so a
    # core that dies on probe 0 still reports input_va=0x01000000 instead of the
    # host placeholder 0x04002000, and is not mistaken for one that never ran.
    0x2372: dict(
        stub_va=0x010019b0,
        stub=bytes.fromhex('f446' 'acf1050c' '054b' 'c3f800c0' '044b' 'd3f800c0'
                           '0cf1010c' 'c3f800c0' '7047' '08000004' '10000004'),
        marker_va=0x04000008,
        counter_va=0x04000010,
        calls={},
        # 2372 replaces32 bytes, not28: the marker store and the block counter
        # need the room. The window ends two bytes into the msr at0x0100190a,
        # which the park never reaches.
        patches={0x010018ec: ('72b626484ff00b01016025484ff00701016024484ff4e0210160234880f30988',
                              '0124240601239b069c601a6901263602206804f5807401321a61013ef8d1fee7')},
        literals={},
    ),
    # 2372 ran the same map with the vendor ENABLE|AUTO start value(3) and the MCU
    # never left MCU_STATUS0, so the map itself was never executed and the result
    # could not say anything about reads. 2373 repeats the map unchanged with the
    # measured-good AUTO-alone value(2). The container bytes are identical to2372;
    # only the shim's start word differs, which the container cannot show.
    0x2373: dict(
        stub_va=0x010019b0,
        stub=bytes.fromhex('f446' 'acf1050c' '054b' 'c3f800c0' '044b' 'd3f800c0'
                           '0cf1010c' 'c3f800c0' '7047' '08000004' '10000004'),
        marker_va=0x04000008,
        counter_va=0x04000010,
        calls={},
        patches={0x010018ec: ('72b626484ff00b01016025484ff00701016024484ff4e0210160234880f30988',
                              '0124240601239b069c601a6901263602206804f5807401321a61013ef8d1fee7')},
        literals={},
    ),
    # 2374 is the 2373 map unchanged. The only difference is that the CSF page
    # table now follows the section ABI for shareability: a section that does
    # not declare CSF_FIRMWARE_ENTRY_SHARED gets no share bits, which is what
    # mali_kbase_mmu_mode_aarch64.c get_mmu_flags() does with
    # KBASE_REG_SHARE_BOTH. 2373 mapped every cached section inner+outer
    # shareable and completed two probes.
    0x2374: dict(
        stub_va=0x010019b0,
        stub=bytes.fromhex('f446' 'acf1050c' '054b' 'c3f800c0' '044b' 'd3f800c0'
                           '0cf1010c' 'c3f800c0' '7047' '08000004' '10000004'),
        marker_va=0x04000008,
        counter_va=0x04000010,
        calls={},
        patches={0x010018ec: ('72b626484ff00b01016025484ff00701016024484ff4e0210160234880f30988',
                              '0124240601239b069c601a6901263602206804f5807401321a61013ef8d1fee7')},
        literals={},
    ),
    # 2375 stops asking about the code section. 2374 held shareability constant and
    # changed nothing, so the wall is not a code-section attribute; 2358 could not
    # write the stack either. This probe reads one address per section in one boot,
    # each read followed by its own counter increment, so the first hang names the
    # section instead of the address: code 0x01001900 (known good, control), stack
    # 0x02000000, read-only 0x02800000, heap 0x03000000, shared 0x04000000.
    # If the control returns and the stack does not, every 2371-2374 experiment was
    # measuring the wrong object.
    0x2375: dict(
        stub_va=0x010019b0,
        stub=bytes.fromhex('f446' 'acf1050c' '054b' 'c3f800c0' '044b' 'd3f800c0'
                           '0cf1010c' 'c3f800c0' '7047' '08000004' '10000004'),
        marker_va=0x04000008,
        counter_va=0x04000010,
        calls={},
        patches={0x010018ec: ('72b626484ff00b01016025484ff00701016024484ff4e0210160234880f309884ff0020080f31488bff36f8f1f48046804f08004204601f000fc00f0', '0124240601239b069c601a6904f5c854206801321a6101246406206801321a6104f50004206801321a6103242406206801321a61186801321a61fee7')},
        literals={},
    ),
    # 2377 tests writes, because the vector table says the firmware dies on one. The
    # config section at VA0 holds SP=0x02040000, so the reset prologue's first push
    # lands in 0x0203f000..0x0203ffff: the page 2358 could not write to. A store that
    # never completes raises no fault, which is exactly what 2376 saw - MCU enabled,
    # no fault, never ready.
    #
    # Two pages, each written with a pattern, drained with DSB, read back and
    # restored. The counter encodes how far it got:
    #    8  the bottom page 0x02000000 hung (2375 only proved it *reads*)
    #    9  bottom ok, the 0x0203f000 read hung
    #   10  that read ok, the write there hung
    #   11  both pages held a write and returned it
    #   24  bottom returned a wrong value (the write did not stick)
    #   26  top returned a wrong value
    # Because an unmapped page faults at once (2375, error -54) and a page that
    # cannot complete a store hangs, the counter separates the two mechanisms.
    0x2377: dict(
        stub_va=0x010019b0,
        stub=bytes.fromhex('f446' 'acf1050c' '054b' 'c3f800c0' '044b' 'd3f800c0'
                           '0cf1010c' 'c3f800c0' '7047' '08000004' '10000004'),
        marker_va=0x04000008,
        counter_va=0x04000010,
        calls={},
        patches={0x010018ec: ('72b626484ff00b01016025484ff00701016024484ff4e0210160234880f309884ff0020080f31488bff36f8f1f48046804f08004204601f000fc00f057f800f05af800f07cf834b31948017819b3',
                              '0124640601239b069c601a6901273f06773720682760bff34f8f21682060b94212d101321a610124640604f57c34206801321a612760bff34f8f21682060b94202d101321a6101e010321a61fee7')},
        literals={},
    ),
    # 2378 made the code and stack leaves identical without making firmware
    # ready. Ask whether instruction fetch makes a fresh code block readable.
    # Assembled from matisse-csf-fetch-prime.S: no stack or literal loads.
    # Only these two windows change; the fault handler stays vendor-original.
    # Counter 9: call did not return; 10: call returned, data read did not;
    # 11: the data read returned. Faults must be interpreted separately.
    0x2379: dict(
        kind='fetch-prime',
        stub_va=0x01000200,
        stub_original=bytes.fromhex('01340a2c'),
        stub=bytes.fromhex('00bf7047'),  # nop / bx lr
        marker_va=0x04000008,
        counter_va=0x04000010,
        calls={},
        patches={0x010018ec: (
            '72b626484ff00b01016025484ff00701016024484ff4e0210160234880f309884ff0020080f3',
            '72b60124240604f5007401239b069c601a6901321a61fef77dfc01321a61206901321a61fee7')},
        literals={},
    ),
}
# 2382 reuses the2379 fetch-prime patch byte for byte. The container, the patch
# sites and the counter semantics are therefore identical by construction, and
# the only difference between the two images is where the memory plan puts the
# code section. Declared after the literal so the two can never drift apart.
TRACE_PROBE[0x2382] = TRACE_PROBE[0x2379]

# 2383 is 2382 plus the vendor fault entry. 2382 could not tell a fetch that
# never completes from a fault that entered 0x010019b1 and parked there, because
# an MCU-side fault does not set AS_FAULT. The stub reads the exception frame
# from the stack EXC_RETURN selects, parks the stacked PC in shared+12, the CFSR
# in shared+20 and 20 in shared+16, then parks. 20 cannot collide with the
# probe's 9/10/11, so one counter value answers the mechanism question.
# Hand-assembled from tools/matisse-csf-fault-entry.S and checked against the
# pinned container by tools/tests/test_matisse_csf_fetch_prime.py.
FAULT_ENTRY_2383 = (
    '1ef0040f0cbfeff30880eff309802de9f04f6946eff3058200f0f0fb08b000bd4ff0ff3070470000',
    '734613f0040f0cbfeff30880eff30980816901229206d16002490868506114211161fee728ed00e0')
TRACE_PROBE[0x2383] = dict(TRACE_PROBE[0x2379])
TRACE_PROBE[0x2383]['patches'] = dict(TRACE_PROBE[0x2379]['patches'])
TRACE_PROBE[0x2383]['patches'][0x010019b0] = FAULT_ENTRY_2383
TRACE_PROBE[0x2383]['fault_entry_va'] = 0x010019b0
BARRIERS = (0x8F4FF3BF, 0x8F6FF3BF)   # dsb sy / isb sy, first halfword in the low bytes


def encode_bl(src, dst):
    """Thumb-2 BL from src to dst, as the four bytes the core will fetch."""
    off = dst - (src + 4)
    if off & 1:
        raise ValueError('bl target %#x is not halfword aligned' % dst)
    if not -(1 << 24) <= off < (1 << 24):
        raise ValueError('bl target %#x is out of range of %#x' % (dst, src))
    sign = 1 if off < 0 else 0
    off &= 0x1FFFFFF
    i1 = (off >> 23) & 1
    i2 = (off >> 22) & 1
    j1 = (1 ^ i1) ^ sign
    j2 = (1 ^ i2) ^ sign
    hw1 = 0xF000 | (sign << 10) | ((off >> 12) & 0x3FF)
    hw2 = 0xD000 | (j1 << 13) | (j2 << 11) | ((off >> 1) & 0x7FF)
    return hw1.to_bytes(2, 'little') + hw2.to_bytes(2, 'little')


def fault_vector_probe(path, expected, build_id):
    firmware = pinned(path, expected)
    if expected != 'de22d2fc06bc8a859968499a6e609c27fe838be062bf5c97d92ea9f904f7229a':
        raise ValueError('fault vector probe requires the measured device firmware')
    spec = TRACE_PROBE.get(build_id) or FAULT_VECTOR_PROBE.get(build_id)
    if not spec:
        raise ValueError('build %#x has no fault vector probe' % build_id)
    fetch = importlib.util.module_from_spec(
        importlib.util.spec_from_file_location('csf_fetch', ROOT / 'tools/matisse-csf-fetch-audit.py'))
    importlib.util.spec_from_file_location('csf_fetch', ROOT / 'tools/matisse-csf-fetch-audit.py').loader.exec_module(fetch)
    _, plan = fetch.build_arena(Path(path), 0x40077000, memory_group=6)
    section = next(s for s in plan['sections'] if s['va'] == 0x01000000)

    def offset(va):
        if not (section['va'] <= va and va + 4 <= section['va'] + section['data_bytes']):
            raise ValueError('probe site %#x is outside the code section' % va)
        return section['data_start'] + va - section['va']

    # The vector table lives in the VA-zero config section, not at file offset0.
    config = next(s for s in plan['sections'] if s['va'] == 0)
    # SP at0x0 and Reset at0x4 are not fault vectors.
    for entry in (0x08, 0x0c, 0x10, 0x14, 0x18):
        at = config['data_start'] + entry
        word = int.from_bytes(firmware[at:at + 4], 'little')
        if word != 0x010019b1:
            raise ValueError('vector %#x is %#x, expected0x010019b1' % (entry, word))

    stub_at = offset(spec['stub_va'])
    stub = spec['stub']
    if ('stub_original' in spec and
            firmware[stub_at:stub_at + len(stub)] != spec['stub_original']):
        raise ValueError('probe stub original bytes mismatch')
    if len(stub) % 4:
        raise ValueError('stub must keep four-byte alignment')
    sites = list(spec.get('markers', ()))
    masks = [mask for _, mask in sites]
    if len(set(masks)) != len(masks) or any(not 0 < mask < 0x100 for mask in masks):
        raise ValueError('trace masks must be distinct nonzero bytes')
    site_at = {}
    for va, mask in sites:
        at = offset(va)
        word = int.from_bytes(firmware[at:at + 4], 'little')
        if word not in BARRIERS:
            raise ValueError('trace site %#x is %#x, expected dsb/isb' % (va, word))
        site_at[at] = (va, mask)
    call_at = {}
    for src, dst in spec.get('calls', {}).items():
        at = offset(src)
        word = int.from_bytes(firmware[at:at + 4], 'little')
        if isinstance(dst, tuple):
            # A site whose original instruction is not a barrier: the caller
            # must state the exact four bytes it expects, so the probe can
            # split a straight-line window between two rungs.
            target, want_hex = dst
            if firmware[at:at + 4] != bytes.fromhex(want_hex):
                raise ValueError('call site %#x is %s, expected %s'
                                 % (src, firmware[at:at + 4].hex(), want_hex))
        else:
            target = dst
            if word not in BARRIERS:
                raise ValueError('call site %#x is %#x, expected dsb/isb' % (src, word))
        call_at[at] = (src, target)
    literal_at = {}
    for off, value in spec.get('literals', {}).items():
        literal_at[off] = value
    patch_at = {}
    for va, (want_hex, new_hex) in spec.get('patches', {}).items():
        at = offset(va)
        want, new = bytes.fromhex(want_hex), bytes.fromhex(new_hex)
        if not want or len(want) != len(new):
            raise ValueError('patch %#x must keep its length' % va)
        if firmware[at:at + len(want)] != want:
            raise ValueError('patch site %#x is %s, expected %s'
                             % (va, firmware[at:at + len(want)].hex(), want_hex))
        patch_at[at] = new
    embedded = bytearray(firmware)
    replaced = bytes(embedded[stub_at:stub_at + len(stub)])
    embedded[stub_at:stub_at + len(stub)] = stub
    for at, (va, mask) in site_at.items():
        embedded[at:at + 4] = b'\xf0\xf7' + (0xA000 | mask).to_bytes(2, 'little')
    for at, (src, dst) in call_at.items():
        embedded[at:at + 4] = encode_bl(src, dst)
    for off, value in literal_at.items():
        embedded[off:off + 4] = value.to_bytes(4, 'little')
    for at, new in patch_at.items():
        embedded[at:at + len(new)] = new
    embedded = bytes(embedded)
    if len(embedded) != len(firmware):
        raise ValueError('fault probe changed the container size')
    changed = sorted(i for i in range(len(firmware)) if firmware[i] != embedded[i])
    if any(not (stub_at <= i < stub_at + len(stub)) and
           not any(at <= i < at + 4 for at in site_at) and
           not any(at <= i < at + 4 for at in call_at) and
           not any(at <= i < at + len(new) for at, new in patch_at.items()) and
           not any(off <= i < off + 4 for off in literal_at) for i in changed):
        raise ValueError('fault probe touched bytes outside the stub, markers, calls, patches and literals')
    with tempfile.TemporaryDirectory(prefix='csf-fault-probe-') as directory:
        candidate = Path(directory) / 'diagnostic.bin'
        candidate.write_bytes(embedded)
        _, rebuilt = fetch.build_arena(candidate, 0x40077000, memory_group=6)
    if rebuilt != plan:
        raise ValueError('fault probe changed firmware mappings')
    patch = dict(diagnostic_only=True,
                 kind=spec.get('kind', 'branch-probe' if call_at else
                               'trace-resume' if sites else 'fault-vector'),
                 stub_va='%#x' % spec['stub_va'], stub_bytes=stub.hex(),
                 replaced_bytes=replaced.hex(), marker_va='%#x' % spec['marker_va'],
                 markers=[dict(va='%#x' % va, mask=mask, bit='%#x' % mask)
                          for va, mask in sites],
                 calls=[dict(va='%#x' % src, target='%#x' % dst, bytes=encode_bl(src, dst).hex())
                        for src, dst in call_at.values()],
                 patches=[dict(va='%#x' % (at - section['data_start'] + section['va']),
                               bytes=new.hex()) for at, new in patch_at.items()],
                 literals={('%#x' % off): ('%#x' % value) for off, value in literal_at.items()},
                 container_bytes_changed=len(changed),
                 original_container_sha256=digest(firmware),
                 embedded_container_sha256=digest(embedded))
    if build_id in (0x2379, 0x2382, 0x2383):
        patch['fetch_prime'] = dict(
            entry_va='0x10018ec', call_va='0x1001902', return_va='0x1001906',
            fetch_va='0x1000200', read_insn_va='0x100190a', read_va='0x1000210',
            marker_value='0x1000200', counter_va='0x4000010', counter_seed=8,
            counter_meanings={'9': 'fresh-block call did not return',
                              '10': 'call returned; data read did not return',
                              '11': 'data read returned'},
            fault_vectors_unchanged=True, block_size_hypothesis=512)
        if build_id == 0x2383:
            patch['fetch_prime']['fault_entry'] = dict(
                entry_va='0x10019b0', counter_value=20,
                stacked_pc_field='output_va', cfsr_field='group_stride',
                cfsr_address='0xe000ed28', stack_selected_by='EXC_RETURN bit2',
                counter_meanings={'9': 'no fault taken: the fetch itself never completes',
                                  '20': 'a fault was taken; read output_va and group_stride'})
        if build_id == 0x2382:
            # Same probe, same target VA; only the section's PA differs, so a
            # counter of9 here against 2379's9 says the hang does not follow the
            # physical pages this build moved it to.
            patch['fetch_prime']['code_section_relocated'] = True
    return embedded, patch


def relocation_evidence(firmware):
    """2382: prove at build time that the plan moves exactly one section.

    Builds the same container twice, once with the shipping plan and once with
    SWEET_CSF_RELOCATE_CODE, and refuses to hand out an image unless the only
    difference is the executable section's offset. Returns arena-relative
    numbers; the caller adds the linked arena base.
    """
    spec = importlib.util.spec_from_file_location('csf_fetch', ROOT / 'tools/matisse-csf-fetch-audit.py')
    fetch = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(fetch)
    with tempfile.TemporaryDirectory(prefix='csf-relocate-') as directory:
        path = Path(directory) / 'patched.bin'
        path.write_bytes(firmware)
        _, default = fetch.build_arena(path, 0x40077000, memory_group=6)
        _, moved = fetch.build_arena(path, 0x40077000, memory_group=6, relocate_code=True)
    if len(default['sections']) != len(moved['sections']):
        raise ValueError('relocation changed the section count')
    index = [i for i, section in enumerate(default['sections'])
             if section['va'] == 0x01000000 and section['flags'] & 4]
    if len(index) != 1:
        raise ValueError('expected exactly one executable section')
    index = index[0]
    for i, (before, after) in enumerate(zip(default['sections'], moved['sections'])):
        if i != index and before != after:
            raise ValueError('relocation moved section %#x' % before['va'])
    code, relocated = default['sections'][index], moved['sections'][index]
    if relocated['arena_offset'] < default['required_bytes']:
        raise ValueError('the code section was not appended after the whole layout')
    return dict(code_va='%#x' % code['va'], code_bytes=code['bytes'],
                default_offset=code['arena_offset'],
                relocated_offset=relocated['arena_offset'],
                pa_delta_bytes=relocated['arena_offset'] - code['arena_offset'],
                default_required_bytes=default['required_bytes'],
                relocated_required_bytes=moved['required_bytes'],
                sections_unchanged=moved['required_bytes'] - default['required_bytes'] == code['bytes'])


def diagnostic_firmware(path, expected, build_id, reset_store_stub, entry_probe=False,
                        inline_entry=False, entry_pte_guard=False, mcu_store_redirect=False):
    firmware = pinned(path, expected)
    if expected != 'de22d2fc06bc8a859968499a6e609c27fe838be062bf5c97d92ea9f904f7229a':
        raise ValueError('CSF probe requires the measured device firmware')
    if build_id in MCU_ACCESS_REDIRECTS:
        if not mcu_store_redirect or entry_probe or inline_entry or entry_pte_guard or reset_store_stub:
            raise ValueError('build%x requires only the MCU access redirect' % build_id)
        return redirect_mcu_accesses(path, expected, build_id)
    if mcu_store_redirect:
        raise ValueError('only the redirect builds may repoint MCU access literals')
    if inline_entry and (not entry_probe or build_id not in (0x2336,0x2337,0x2338)):
        raise ValueError('inline entry requires build2336/2337/2338 and entry probe')
    if entry_pte_guard != (build_id in (0x2337,0x2338)):
        raise ValueError('build2337 requires the entry PTE guard (build2338 does too); other builds forbid it')
    if entry_probe:
        if (build_id not in ((0x2336,0x2337,0x2338) if inline_entry else (0x2335,)) or
                reset_store_stub):
            raise ValueError('entry probe requires build2335/2336/2337/2338 and original firmware')
        return firmware, None
    if build_id in (0x2335,0x2336,0x2337,0x2338):
        raise ValueError('build2335/2336/2337/2338 requires the entry probe')
    if (build_id == 0x2334) != reset_store_stub:
        raise ValueError('build2334 requires the reset-store stub; other builds must retain stock firmware')
    if not reset_store_stub:
        return firmware, None
    spec = importlib.util.spec_from_file_location('csf_fetch', ROOT / 'tools/matisse-csf-fetch-audit.py')
    fetch = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(fetch)
    arena, plan = fetch.build_arena(Path(path), 0x40077000, memory_group=6)
    patched_arena, patch = fetch.patch_reset_store_stub(arena, plan)
    entry = int(patch['entry_va'], 0)
    code = bytes.fromhex(patch['patch_hex'])
    section = next(s for s in plan['sections'] if s['flags'] & 4 and
                   s['va'] <= entry and entry + len(code) <= s['va'] + s['data_bytes'])
    offset = section['data_start'] + entry - section['va']
    embedded = firmware[:offset] + code + firmware[offset + len(code):]
    with tempfile.TemporaryDirectory(prefix='csf-reset-store-') as directory:
        candidate = Path(directory) / 'diagnostic.bin'
        candidate.write_bytes(embedded)
        rebuilt, rebuilt_plan = fetch.build_arena(candidate, 0x40077000, memory_group=6)
    if rebuilt != patched_arena or rebuilt_plan != plan or len(embedded) != len(firmware):
        raise ValueError('container patch differs from the verified reset-store arena')
    patch.update(container_patch_offset=offset, original_container_sha256=digest(firmware),
                 embedded_container_sha256=digest(embedded), diagnostic_only=True)
    return embedded, patch

def diagnostic_adt(data, build_id=0x2333, global_property=False):
    root, end = adt.parse(data)
    if end != len(data):
        raise ValueError('trailing ADT bytes')
    chosen = next(c for c in root.children if c.name == 'chosen')
    keys = ['sweet-gpu-report', 'sweet-csf-report', 'sweet-gpu-autorecovery-seconds']
    if global_property:
        keys.append('sweet-csf-global')
    for key in keys:
        if chosen.prop(key) is not None:
            raise ValueError('already a GPU diagnostic ADT')
    chosen.props = [(n, f, ('sweet-shim/gpu%x' % build_id).encode().ljust(128, b'\0')
                     if n in ('firmware-version', 'system-firmware-version') else v)
                    for n, f, v in chosen.props]
    chosen.props += [('sweet-gpu-report', 0, bytes(128)),
                     ('sweet-csf-report', 0, bytes(696)),
                     ('sweet-gpu-autorecovery-seconds', 0, struct.pack('<I', 60))]
    if global_property:
        #2381: fixed96-byte global-interface evidence, separate from the696-byte ABI.
        chosen.props.append(('sweet-csf-global', 0, bytes(96)))
    return adt.serialize(root)

def build(a):
    out = Path(a.out).resolve()
    out.relative_to(ROOT / 'research')
    if out.exists():
        raise ValueError('refuse existing output directory')
    kernel = pinned(a.kernel, a.kernel_sha256)
    if a.build_id == 0x2379 and (not a.trace_probe or not a.ro_as_rw or a.mcu_control != '2'):
        raise ValueError('build2379 requires --trace-probe --ro-as-rw --mcu-control 2')
    if a.build_id == 0x2338 and not (a.entry_probe and a.inline_entry and a.entry_pte_guard):
        raise ValueError('build2338 must preserve the2337 CSF probe configuration')
    #2380 is a clean single-variable boot: vendor MemAttr only, no probe, no
    # writable-RO leaves, no global stage. 2381 adds the global interface.
    if a.build_id == 0x2380:
        if not a.vendor_memattr:
            raise ValueError('build2380 requires --vendor-memattr')
        if a.ro_as_rw or a.trace_probe or a.fault_probe or a.global_init or a.entry_probe or a.reset_store_stub:
            raise ValueError('build2380 must be a clean boot: no probe, no RO-as-RW, no global init')
    if a.build_id == 0x2381 and not (a.vendor_memattr and a.global_init):
        raise ValueError('build2381 requires --vendor-memattr --global-init')
    #2382 is the2379 container patch on a plan that puts the R-X section after
    # the whole layout. Everything else - leaf encoding, probe, RO-as-RW, start
    # word - is held at2379's values so the PA is the only moved number.
    if a.build_id in (0x2382, 0x2383):
        if not (a.trace_probe and a.ro_as_rw and a.relocate_code):
            raise ValueError('build%x requires --trace-probe --ro-as-rw --relocate-code' % a.build_id)
        if (a.vendor_memattr or a.global_init or a.fault_probe or a.entry_probe or
                a.reset_store_stub or a.mcu_control != '2'):
            raise ValueError('build%x may change only the code section PA' % a.build_id)
    elif a.relocate_code:
        raise ValueError('--relocate-code is only defined for build2382/2383')
    if a.fault_probe or a.trace_probe:
        if a.redirect_mcu_stores or a.entry_probe or a.inline_entry or a.entry_pte_guard or a.reset_store_stub:
            raise ValueError('the fault vector probe replaces the handler and takes no other patch')
        firmware, reset_patch = fault_vector_probe(a.firmware, a.firmware_sha256, a.build_id)
    else:
        firmware, reset_patch = diagnostic_firmware(a.firmware, a.firmware_sha256,
                                                   a.build_id, a.reset_store_stub, a.entry_probe,
                                                   a.inline_entry, a.entry_pte_guard,
                                                   a.redirect_mcu_stores)
    template = pinned(a.template, a.template_sha256)
    original_adt = pinned(a.adt, a.adt_sha256)
    stock = pinned(a.stock, a.stock_sha256)
    frozen = Path(a.frozen).resolve()
    for name in ('loader.c', 'start.S', 'fdt.c', 'str.c'):
        previous = subprocess.check_output(['git', 'show', '8dc3bce:shim/' + name], cwd=ROOT)
        if (frozen / name).read_bytes() != previous:
            raise ValueError('frozen source pin mismatch: ' + name)
    command = Path(a.cmdline).read_text().strip()
    if 'sweettrial=2317' not in command:
        raise ValueError('expected known-good2317 command line')
    label = 'gpu%x' % a.build_id
    command = command.replace('sweettrial=2317', 'sweettrial=%x' % a.build_id)
    command = command.replace('rootrw=1', 'rootrw=0').replace('ufsrw=1', 'ufsrw=0')
    tree = diagnostic_adt(original_adt, a.build_id, a.global_init)
    out.mkdir(parents=True)
    (out / (label + '.adt')).write_bytes(tree)
    payload, _ = mkpayload.build(Path(a.kernel), out / (label + '.adt'), command,
                                 allow_matisse_root_write=False)
    (out / (label + '.payload')).write_bytes(payload)
    ndk = Path(a.ndk)
    if a.dvfs_commit == 'off':
        dvfs = ['-DSWEET_GPU_DVFS_COMMIT=0']
    elif a.dvfs_commit == 'current':
        dvfs = ['-DSWEET_GPU_DVFS_COMMIT=1', '-DSWEET_GPU_DVFS_COMMIT_OPP=-1']
    else:
        index = int(a.dvfs_commit, 0)
        if not 0 <= index < 64:
            raise ValueError('dvfs-commit index out of range')
        dvfs = ['-DSWEET_GPU_DVFS_COMMIT=1', '-DSWEET_GPU_DVFS_COMMIT_OPP=%d' % index]
    definitions = ['-DSHIM_GPU_PROBE', '-DSHIM_CSF_PROBE', '-DSHIM_RECOVERY_FALLBACK',
                   '-DSHIM_RECOVERY_OFFSET=' + str(FALLBACK_OFFSET),
                   '-DSWEET_SHIM_BUILD_LABEL="%x"' % a.build_id,
                   '-DSWEET_CSF_MCU_CONTROL=' + str(a.mcu_control),
                   '-DSWEET_CSF_RO_LEAVES_WRITABLE=' + ('1' if a.ro_as_rw else '0'),
                   '-DSWEET_CSF_VENDOR_MEMATTR=' + ('1' if a.vendor_memattr else '0'),
                   '-DSWEET_CSF_GLOBAL_INIT=' + ('1' if a.global_init else '0'),
                   '-DSWEET_CSF_RELOCATE_CODE=' + ('1' if a.relocate_code else '0'),
                   *dvfs,
                   '-DEMBEDDED_XNU_BYTES=' + str(len(payload))]
    if a.entry_probe:
        definitions.append('-DSHIM_CSF_ENTRY_PROBE')
    if a.inline_entry:
        definitions.append('-DSHIM_CSF_INLINE_ENTRY_PROBE')
    if a.entry_pte_guard:
        definitions.append('-DSHIM_CSF_ENTRY_PTE_GUARD')
    if a.build_id in MCU_ACCESS_REDIRECTS or a.build_id in TRACE_PROBE:
        # Sample shared+0xffc without installing any entry overlay: the marker
        # is now written by the original reset handler itself.
        definitions.append('-DSHIM_CSF_ENTRY_CHECKPOINT')
    source = {'start': ROOT / 'shim/start.S', 'loader': ROOT / 'shim/loader.c',
              'gpu': ROOT / 'shim/gpu.c', 'gpueb_boot': ROOT / 'xnu/gpu/mtk_gpueb_boot.c',
              'gpueb_protocol': ROOT / 'xnu/gpu/mtk_gpueb_protocol.c',
              'gpufreq': ROOT / 'xnu/gpu/mtk_gpufreq.c',
              'csf': ROOT / 'shim/csf.c', 'csf_memory': ROOT / 'xnu/gpu/mali_csf_memory.c',
              'csf_firmware': ROOT / 'xnu/gpu/mali_csf_firmware.c', 'csf_boot': ROOT / 'xnu/gpu/mali_csf_boot.c'}
    for name, path in source.items():
        subprocess.run([str(ndk / 'clang'), *FLAGS, *definitions, '-c', str(path),
                        '-o', str(out / (name + '.o'))], check=True)
        relocs = subprocess.check_output([str(ndk / 'llvm-readelf'), '-r', str(out / (name + '.o'))], text=True)
        if name != 'start' and 'R_AARCH64_ABS64' in relocs:
            raise ValueError('absolute pointer in position-independent shim: ' + name)
    (out / 'csf.bin').write_bytes(firmware)
    assembly = '.section .rodata.csf,"a"\n.balign 8\n.global sweet_csf_blob_start\nsweet_csf_blob_start:\n.incbin "' + str(out / 'csf.bin') + '"\n.global sweet_csf_blob_end\nsweet_csf_blob_end:\n'
    (out / 'csf_blob.S').write_text(assembly)
    subprocess.run([str(ndk / 'clang'), *FLAGS, '-c', str(out / 'csf_blob.S'), '-o', str(out / 'csf_blob.o')],check=True)
    names = ['start' ,'shim','console','display','diag','mmu','fdt','board','loader',
             'ufs','str','logstore','gpu','gpueb_boot','gpueb_protocol','gpufreq','csf','csf_memory','csf_firmware','csf_boot','csf_blob']
    objects = [out / (n + '.o') if n in source or n == 'csf_blob' else frozen / 'out' / (n + '.o') for n in names]
    subprocess.run([str(ndk / 'clang'), *FLAGS, '-static', '-T', str(frozen / 'shim.ld'),
                    '-fuse-ld=lld', '-Wl,--build-id=none', *map(str, objects),
                    '-o', str(out / 'shim.elf')], check=True)
    subprocess.run([str(ndk / 'llvm-objcopy'), '-O', 'binary', str(out / 'shim.elf'),
                    str(out / 'Image-bare')], check=True)
    symbols = subprocess.check_output([str(ndk / 'llvm-nm'), str(out / 'shim.elf')], text=True)
    symbol = {line.split()[-1]:int(line.split()[0],16) for line in symbols.splitlines()
              if len(line.split()) == 3 and line.split()[0] != 'U'}
    end = symbol['_end']
    arena = symbol['arena']
    if arena & 4095 or arena < symbol['_bss_start'] or arena + (2 << 20) > symbol['_bss_end']:
        raise ValueError('CSF arena is outside the aligned shim BSS')
    bare = (out / 'Image-bare').read_bytes()
    if len(bare) > end:
        raise ValueError('shim exceeds linker end')
    bare += bytes(end - len(bare))
    raw = embed_payload.embed(bare, payload, 0x7c80000)
    stock_header = mkbootimg.parse(stock)
    stock_linux = gzip.decompress(stock[4096:4096 + stock_header['kernel_size']])
    text_offset, image_bytes, flags = struct.unpack_from('<3Q', stock_linux, 8)
    if stock_linux[56:60] != b'ARM\x64' or text_offset or flags & 8 == 0 or image_bytes > len(stock_linux):
        raise ValueError('stock Linux placement contract not satisfied')
    if len(raw) > FALLBACK_OFFSET:
        raise ValueError('payload overlaps stock fallback')
    raw += bytes(FALLBACK_OFFSET - len(raw)) + stock_linux
    if len(raw) > 0x7c80000:
        raise ValueError('combined Image overlaps measured live DTB')
    raw = bytearray(raw)
    struct.pack_into('<Q', raw, 16, len(raw))
    (out / 'Image').write_bytes(raw)
    header = mkbootimg.parse(template)
    if header['header_version'] != 4:
        raise ValueError('requires boot v4')
    rd_offset = 4096 + mkbootimg.pad(header['kernel_size'])
    ramdisk = template[rd_offset:rd_offset + header['ramdisk_size']]
    image = out / ('matisse-shim-' + label + '.img')
    mkbootimg.build(gzip.compress(raw, compresslevel=9, mtime=0), ramdisk,
                    header['cmdline'].decode(), image, 4, header['os_version'],
                    header['signature_size'], header['signature'])
    result = image.read_bytes()
    h = mkbootimg.parse(result)
    expanded = gzip.decompress(result[4096:4096 + h['kernel_size']])
    rd = 4096 + mkbootimg.pad(h['kernel_size'])
    if (expanded[FALLBACK_OFFSET:] != stock_linux or expanded != raw or
            result[rd:rd + h['ramdisk_size']] != ramdisk or h['signature'] != header['signature']):
        raise ValueError('image readback/component mismatch')
    info = dict(trial=hex(a.build_id), image_bytes=len(result), image_sha256=digest(result),
                kernel_sha256=digest(kernel), adt_sha256=digest(tree), payload_sha256=digest(payload),
                expanded_bytes=len(raw), fallback_offset=FALLBACK_OFFSET,
                fallback_linux_sha256=digest(stock_linux), stock_sha256=digest(stock),
                ramdisk_sha256=digest(ramdisk), signature_sha256=digest(header['signature']),
                signature_authenticated=False, cmdline=command,
                frozen_objects={p.name:digest(p.read_bytes()) for p in objects if p.parent == frozen / 'out'},
                sources={str(p.relative_to(ROOT)):digest(p.read_bytes()) for p in source.values()},
                autorecovery_seconds=60, automatic_recovery_verified=False,
                gpu_csf_firmware_embedded_sha256=digest(firmware), gpu_csf_boot_hardware_verified=False)
    info['csf_leaf_memory_group'] = 6
    info['gpu_boot_report_bytes'] = 112
    info['gpufreq_dvfs'] = dict(commit=a.dvfs_commit, definitions=dvfs,
                                report_abi='2338', hardware_verified=False)
    #2372: the start word is a build input, so record which one this image
    # carries. Without it a trial result cannot be tied back to its value.
    info['csf_mcu_control'] = dict(value=a.mcu_control, vendor_form=a.mcu_control == '3',
                                   report_field='platform_reserved')
    info['csf_readonly_leaves_writable'] = bool(a.ro_as_rw)
    info['csf_vendor_memattr'] = bool(a.vendor_memattr)
    # The shim publishes the96-byte block, but sweet_ufs.c does not forward it
    # into SWEETMRK yet, so2381 evidence is console-only until that lands.
    info['csf_global_init'] = (dict(enabled=True, report_bytes=96, kernel_marks_wired=False)
                               if a.global_init else False)
    info['csf_mapping_metadata_hardware_readback'] = False
    info['csf_arena'] = dict(shim_offset=arena, bytes=2 << 20,
                             bss_end=symbol['_bss_end'], shim_end=end,
                             payload_offset=end + 16, cpu_cache_policy='MMU/cache off')
    if reset_patch and a.build_id == 0x2334:
        if arena != 0x77000:
            raise ValueError('reset-store trial must preserve the measured2333 arena placement')
        info['reset_store_stub'] = reset_patch
        info['reset_store_stub']['source_sha256'] = {
            name: digest((ROOT / name).read_bytes()) for name in
            ('tools/matisse-csf-reset-store.S', 'tools/matisse-csf-fetch-audit.py',
             'tools/matisse-shim-gpu-image.py')}
    if a.build_id in MCU_ACCESS_REDIRECTS:
        if reset_patch is None:
            raise ValueError('build%x requires the MCU access redirect' % a.build_id)
        # No entry-probe translation unit is compiled in, so the shim text
        # shrinks by the same page the2338 probe added and the anchor returns
        # to the2334 measurement. Pin it rather than dropping the check.
        if arena != 0x77000:
            raise ValueError('redirect builds must keep the measured pre-probe arena placement '
                             '(expected 0x77000, got %#x)' % arena)
        info['mcu_store_redirect'] = reset_patch
        info['mcu_store_redirect']['source_sha256'] = {
            name: digest((ROOT / name).read_bytes()) for name in
            ('xnu/gpu/mali_csf_boot.c', 'tools/matisse-csf-fetch-audit.py',
             'tools/matisse-shim-gpu-image.py')}
    if a.build_id in FAULT_VECTOR_PROBE or a.build_id in TRACE_PROBE:
        if reset_patch is None:
            raise ValueError('build%x requires the fault vector probe' % a.build_id)
        if arena != 0x77000:
            raise ValueError('fault probe builds must keep the measured pre-probe arena placement '
                             '(expected 0x77000, got %#x)' % arena)
        info['fault_vector_probe'] = reset_patch
        info['fault_vector_probe']['source_sha256'] = {
            name: digest((ROOT / name).read_bytes()) for name in
            ('tools/matisse-csf-fetch-audit.py', 'tools/matisse-shim-gpu-image.py')}
        if a.build_id in TRACE_PROBE:
            info['trace_probe'] = info.pop('fault_vector_probe')
            if a.build_id in (0x2379, 0x2382, 0x2383):
                name = 'tools/matisse-csf-fetch-prime.S'
                info['trace_probe']['source_sha256'][name] = digest((ROOT / name).read_bytes())
    if a.relocate_code:
        moved = relocation_evidence(firmware)
        base = 0x40000000 + arena
        if moved['relocated_required_bytes'] > (2 << 20):
            raise ValueError('relocated plan no longer fits the shim arena')
        moved.update(arena_pa=base, default_pa=base + moved['default_offset'],
                     relocated_pa=base + moved['relocated_offset'])
        info['csf_relocated_code'] = moved
    if a.entry_probe:
        # The gpufreq layer adds one page of shim text, so from2338 the arena
        # anchor moves by exactly0x1000. Pinning it per build keeps the drift
        # check meaningful instead of dropping it.
        expected_arena = 0x78000 if a.build_id >= 0x2338 else 0x77000
        if arena != expected_arena:
            raise ValueError('entry trial must preserve the measured arena placement '
                             'for build %#x (expected %#x, got %#x)' % (a.build_id, expected_arena, arena))
        spec = importlib.util.spec_from_file_location('entry_fetch', ROOT / 'tools/matisse-csf-fetch-audit.py')
        fetch = importlib.util.module_from_spec(spec); spec.loader.exec_module(fetch)
        original, plan = fetch.build_arena(Path(a.firmware), 0x40000000 + arena, memory_group=6)
        patched, probe_plan = fetch.build_arena(Path(a.firmware), 0x40000000 + arena,
                                               memory_group=6, entry_probe=True, inline_entry=a.inline_entry)
        if plan != probe_plan:
            raise ValueError('entry probe changed firmware mappings')
        info['entry_probe'] = fetch.entry_probe_metadata(original, patched, plan, inline_entry=a.inline_entry)
        info['entry_probe']['arena_sha256'] = digest(patched)
        info['entry_probe']['original_arena_sha256'] = digest(original)
        info['entry_probe']['source_sha256'] = {name: digest((ROOT / name).read_bytes()) for name in
            ('tools/matisse-csf-entry-probe.S', 'tools/matisse-csf-fetch-audit.py',
             'xnu/gpu/mali_csf_entry_probe.h', 'xnu/gpu/mali_csf_boot.h', 'tools/matisse-shim-gpu-image.py')}
        if a.entry_pte_guard:
            info['entry_pte_guard'] = dict(pre_auto=True, reset_entry_va='0x10018ec',
                expected_entry_word='0x4803b672',
                source_sha256=digest((ROOT / 'xnu/gpu/mali_csf_entry_guard.h').read_bytes()))
        info['firmware_sections'] = fetch.firmware_sections(firmware)
    (out / 'manifest.json').write_text(json.dumps(info, indent=2) + '\n')
    print(json.dumps(info, indent=2))

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--build-id', type=lambda s:int(s,0), choices=(0x2333,0x2334,0x2335,0x2336,0x2337,0x2338,0x2339,0x2340,0x2341,0x2342,0x2343,0x2344,0x2345,0x2346,0x2347,0x2348,0x2349,0x2350,0x2351,0x2352,0x2353,0x2354,0x2355,0x2356,0x2357,0x2358,0x2359,0x2360,0x2361,0x2362,0x2363,0x2364,0x2365,0x2366,0x2367,0x2368,0x2369,0x2370,0x2371,0x2372,0x2373,0x2374,0x2375,0x2376,0x2377,0x2378,0x2379,0x2380,0x2381,0x2382,0x2383), default=0x2333)
    p.add_argument('--reset-store-stub', action='store_true',
                   help='build2334 only: replace20 Thumb reset-entry bytes; no firmware-readiness claim')
    p.add_argument('--entry-probe', action='store_true',
                   help='build2335 only: mark a separate word and continue the original reset path')
    p.add_argument('--inline-entry', action='store_true',
                   help='build2336/2337: inline STUB before remote fetch, then TRAM in tail')
    p.add_argument('--entry-pte-guard', action='store_true',
                   help='build2337/2338 only: reject PTE/backing mismatch before MCU_CONTROL')
    p.add_argument('--fault-probe', action='store_true',
                   help='build2343 only: replace the shared fault vector entry with a stub that '
                        'records the stacked PC in shared+0x10, leaving the entry untouched')
    p.add_argument('--trace-probe', action='store_true',
                   help='install the selected build\'s diagnostic probe; build2379 fetches a '
                        'fresh block before reading it as data, with the fault handler untouched')
    p.add_argument('--redirect-mcu-stores', action='store_true',
                   help='build2339/2340 only: repoint the reset handler\'s MCU peripheral access '
                        'literals at shared words, leaving the original code intact')
    p.add_argument('--dvfs-commit', default='off', metavar='{off,current,<oppidx>}',
                   help='send CMD_COMMIT after POWER_ON: off (default), current (the '
                        'index GPUEB already reports, no frequency change), or an index')
    p.add_argument('--ro-as-rw', action='store_true',
                   help='map sections the firmware declares read-only as writable. Diagnostic '
                        'only:2375/2377 showed RW leaves complete reads and writes while a data '
                        'read of an R-X leaf hangs until its line is resident, so this isolates '
                        'whether the read-only bit is what refuses the fill')
    p.add_argument('--vendor-memattr', action='store_true',
                   help='2380: map firmware sections with the vendor MemAttr indexes/share bits')
    p.add_argument('--relocate-code', action='store_true',
                   help='2382: put the R-X section after the whole arena layout so its PA moves')
    p.add_argument('--global-init', action='store_true',
                   help='2381: program the CSF global interface after boot')
    p.add_argument('--mcu-control', default='2', choices=('2', '3'),
                   help='value written to MCU_CONTROL to start the MCU: 2 is AUTO alone and '
                        'the measured-good value on this SoC (default), 3 is the vendor '
                        'ENABLE|AUTO form, which 2372 measured as leaving MCU_STATUS at0')
    for key in ('firmware','firmware-sha256','kernel','kernel-sha256','template','template-sha256','adt','adt-sha256',
                'stock','stock-sha256','frozen','cmdline','ndk','out'):
        p.add_argument('--' + key, required=True)
    build(p.parse_args())

if __name__ == '__main__':
    main()
