/*
 * 2405: 2404's four accesses, with the instrument fixed.
 *
 * 2404 stopped after marker 1 and could not say why. Two defects made its
 * report unreadable:
 *
 *   1. no barrier after a marker store. A marker is a posted write, so if the
 *      read that follows it stalls, the marker can still be sitting in the
 *      store buffer when the core dies. "Read 1 stalled" and "read 2 stalled
 *      with marker 2 undrained" then produce the same report.
 *   2. shared+12 was never seeded. 2402's ladder writes markers only - it has
 *      no store to shared+12 at all - and its flight still read 0x04003000 out
 *      of that slot, so the arena arrives uninitialised and the word says
 *      nothing until something writes it.
 *
 * So this ladder is 2404 with a DSB SY after every marker store and after every
 * result store. The kernel seeds shared+12 with 0xDEADBEEF before MCU_CONTROL,
 * which turns the slot into a real instrument:
 *
 *   sentinel intact      nothing the MCU stored ever landed
 *   sentinel replaced    the last successful read did land, and the word is it
 *
 * The accesses are unchanged, so the two flights stay comparable:
 *
 *   marker 1  read 0x0100E400  bit 9 = 0, warm      word must be 0x0f10f857
 *   marker 2  read 0x0604E400  cold walk, leaf at L3 offset 0x270 -> PA bit 9 = 1
 *   marker 3  store 0x5a5a5a5a -> 0x04000200        first write at bit 9 = 1
 *   marker 4  read 0x04000200                       read-after-write
 *   marker 5  every access returned
 *
 * The DSB after each marker is what makes marker 2 trustworthy: if it is
 * present, read 1 completed, and the mirror read is the one that stopped the
 * core. That is the answer 2404 was built to get and could not report.
 */
    .syntax unified
    .thumb
    .section .text.ladder, "ax", %progbits
    .global csf_ladder_2405
    .type csf_ladder_2405, %function
csf_ladder_2405:
    movw r2, #0x0000
    movt r2, #0x0400              /* r2 = shared base 0x04000000 */
    movw r6, #0x0000
    movt r6, #0x0100              /* r6 = code 0x01000000 */
    movw r7, #0x0000
    movt r7, #0x0604              /* r7 = mirror 0x06040000 */
    movw r8, #0xE400

    movs r0, #1
    str  r0, [r2, #8]             /* marker 1 */
    dsb  sy                       /* marker 1 is in memory before read 1 */
    ldr.w r0, [r6, r8]            /* 0x0100E400, bit 9 = 0, warm */
    str  r0, [r2, #12]            /* shared+12: the word, for a data check */
    dsb  sy                       /* the word lands before marker 2 does */

    movs r0, #2
    str  r0, [r2, #8]             /* marker 2 */
    dsb  sy                       /* present <=> read 1 returned */
    ldr.w r0, [r7, r8]            /* 0x0604E400: cold walk, L3 entry at bit 9 = 1 */
    str  r0, [r2, #12]            /* shared+12 again: shared+16 is groups and
                                   * shared+20 is group_stride, both validated */
    dsb  sy

    movs r0, #3
    str  r0, [r2, #8]             /* marker 3 */
    dsb  sy
    movw r0, #0x5a5a
    movt r0, #0x5a5a              /* r0 = 0x5a5a5a5a */
    str.w r0, [r2, #0x200]        /* 0x04000200, bit 9 = 1, writable */
    dsb  sy                       /* the store must reach AXI before marker 4 */

    movs r0, #4
    str  r0, [r2, #8]             /* marker 4 */
    dsb  sy
    ldr.w r0, [r2, #0x200]        /* read it back: 0x5a5a5a5a means it landed */
    str  r0, [r2, #12]
    dsb  sy

    movs r0, #5
    str  r0, [r2, #8]             /* marker 5: everything returned */
    dsb  sy
1:  b    1b
    nop
    nop
    .size csf_ladder_2405, . - csf_ladder_2405
