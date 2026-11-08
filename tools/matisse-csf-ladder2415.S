/*
 * 2415: the shape of the wall, measured in one page.
 *
 * 2412 answered "which allocation" and 2414 answered "which SoC glue": neither.
 * What is left is the geometry. Every read so far sampled only +0x000, +0x200
 * and +0x400 of a page, and those three cannot tell "PA bit 9" apart from "the
 * second 512 bytes of every 1 KiB" - a translation preserves the 12-bit offset,
 * so no mapping can separate them. A fourth offset can: +0x600 has bit 9 = 1
 * *and* bit 10 = 1. If it returns while +0x200 stalls, the rule cannot be a
 * 512-byte period and cannot be bit 9 alone either; if it stalls, bit 9 is
 * literal and the 512-byte alternation holds.
 *
 * The order is deliberate - every earlier answer is re-established before the
 * new question is asked, so a surprise is localised by the marker alone:
 *
 *   marker 1  read 0x0100C400  arena leaf,     bit 9 = 0   instrument control
 *   marker 2  read 0x0100D400  past the arena, bit 9 = 0   re-establishes 2412
 *   marker 3  read 0x0100D600  past the arena, bit 9 = 1, bit 10 = 1  the shape
 *   marker 4  read 0x0100D200  past the arena, bit 9 = 1, bit 10 = 0  the wall
 *   marker 5  every access returned
 *
 * marker 1 -> the instrument itself is dead; nothing here is about memory
 * marker 2 -> 2412's control no longer reproduces; this build is not comparable
 * marker 3 -> bit 9 = 1 stalls regardless of bit 10: the 512-byte period holds
 * marker 4 -> +0x600 returned and +0x200 did not: bit 9 alone is not the rule
 * marker 5 -> nothing in this page stalls; the wall is not in the page at all
 *
 * One result slot, shared+0x0c, rewritten after every completed read, so
 * output_va always names the last offset that answered:
 *   0x2415a400 -> +0x400 answered    0x2415a600 -> +0x600 answered
 *   0x2415a200 -> +0x200 answered (only reachable at marker 5)
 * and the shim writes 0x2415a000/200/400/600 at those offsets, so the value
 * identifies the offset without any extra bookkeeping.
 *
 * Every marker and every result has a DSB behind it for the reason 2405 spells
 * out: a posted store can outlive the read that follows it, and then "read N
 * stalled" and "marker N+1 never drained" look identical.
 */
    .syntax unified
    .thumb
    .section .text.ladder, "ax", %progbits
    .global csf_ladder_2415
    .type csf_ladder_2415, %function
csf_ladder_2415:
    movw r2, #0x0000
    movt r2, #0x0400              /* r2 = shared base 0x04000000 */
    movw r6, #0x0000
    movt r6, #0x0100              /* r6 = code base 0x01000000 */
    movw r7, #0xD000
    movt r7, #0x0100              /* r7 = 0x0100D000, the remapped page */

    movs r0, #1
    str  r0, [r2, #8]             /* marker 1 */
    dsb  sy
    movw r8, #0xC400
    ldr.w r0, [r6, r8]            /* 0x0100C400: arena leaf, bit 9 = 0 */
    str  r0, [r2, #12]
    dsb  sy

    movs r0, #2
    str  r0, [r2, #8]             /* marker 2: present <=> read 1 returned */
    dsb  sy
    ldr  r0, [r7, #0x400]         /* 0x0100D400: bit 9 = 0, bit 10 = 1 */
    str  r0, [r2, #12]
    dsb  sy

    movs r0, #3
    str  r0, [r2, #8]             /* marker 3: present <=> read 2 returned */
    dsb  sy
    ldr  r0, [r7, #0x600]         /* 0x0100D600: bit 9 = 1, bit 10 = 1 */
    str  r0, [r2, #12]
    dsb  sy

    movs r0, #4
    str  r0, [r2, #8]             /* marker 4: present <=> read 3 returned */
    dsb  sy
    ldr  r0, [r7, #0x200]         /* 0x0100D200: bit 9 = 1, bit 10 = 0 */
    str  r0, [r2, #12]
    dsb  sy

    movs r0, #5
    str  r0, [r2, #8]             /* marker 5: everything returned */
    dsb  sy
1:  b    1b
    .rept 13
    nop
    .endr
    .balign 4
    .size csf_ladder_2415, . - csf_ladder_2415
