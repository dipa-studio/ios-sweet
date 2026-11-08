/*
 * 2404: does the GPU MMU survive a page-table read at PA bit 9 = 1?
 *
 * The ladder runs from 0x0100E000, whose own translation is warm. The mirror
 * section is mapped at 0x06040000, so:
 *
 *   0x0604E000 -> L2[48] at table offset 0x180 (bit 9 = 0)
 *              -> a fresh L3 page, index 0x4E at offset 0x270 (bit 9 = 1)
 *              -> the very same physical page as 0x0100E000
 *
 * Reading 0x0604E400 therefore needs a cold walk whose last descriptor fetch
 * lands on PA bit 9 = 1, while the access itself is at VA bit 9 = 0 and hits a
 * PA whose bit 9 is 0. Nothing else about the access differs from read 1 except
 * where the page table entry happens to sit.
 *
 * The leaf is valid on purpose. An invalid one would fault as soon as the walk
 * succeeds and end the run, which would throw away reads 3 and 4 - and those
 * are the only measurements of the store direction anyone has.
 *
 *   marker 1  read 0x0100E400  bit9 0, warm       word must be 0x0f10f857
 *   marker 2  read 0x0604E400  bit9 1 page entry  the same word, cold walk
 *   marker 3  store 0x5a5a5a5a -> 0x04000200      first bit9 = 1 access the MCU
 *                                                 issues; DSB makes it complete
 *   marker 4  read 0x04000200  bit9 1             read-after-write, and the last
 *                                                 untested attribute cell
 *   marker 5  every access returned
 *
 * The store and read 4 sit on the shared page, which is writable (its leaf has
 * no 0x80 bit), uncached (AttrIdx 5) and PBHA 0 - so the store tests the bus,
 * not the MMU permission bits.
 */
    .syntax unified
    .thumb
    .section .text.ladder, "ax", %progbits
    .global csf_ladder_2404
    .type csf_ladder_2404, %function
csf_ladder_2404:
    movw r2, #0x0000
    movt r2, #0x0400              /* r2 = shared base 0x04000000 */
    movw r6, #0x0000
    movt r6, #0x0100              /* r6 = code 0x01000000 */
    movw r7, #0x0000
    movt r7, #0x0604              /* r7 = mirror 0x06040000 */
    movw r8, #0xE400

    movs r0, #1
    str  r0, [r2, #8]             /* marker 1 */
    ldr.w r0, [r6, r8]            /* 0x0100E400, bit 9 = 0, warm */
    str  r0, [r2, #12]            /* shared+12: the word, for a data check */

    movs r0, #2
    str  r0, [r2, #8]             /* marker 2 */
    ldr.w r0, [r7, r8]            /* 0x0604E400: cold walk, L3 entry at bit 9 = 1 */
    str  r0, [r2, #12]            /* shared+12 again: the same physical word, and
                                   * shared+16 is the groups counter, not a slot */

    movs r0, #3
    str  r0, [r2, #8]             /* marker 3 */
    movw r0, #0x5a5a
    movt r0, #0x5a5a              /* r0 = 0x5a5a5a5a */
    str.w r0, [r2, #0x200]        /* 0x04000200, bit 9 = 1, writable */
    dsb  sy                       /* the store must reach AXI before marker 4 */

    movs r0, #4
    str  r0, [r2, #8]             /* marker 4 */
    ldr.w r0, [r2, #0x200]        /* read it back: 0x5a5a5a5a means it landed */
    str  r0, [r2, #12]            /* shared+12: group_stride is checked as a
                                   * length, so a 0x5a5a5a5a word there would make
                                   * the decoder reject a perfectly good run */

    movs r0, #5
    str  r0, [r2, #8]             /* marker 5: everything returned */
1:  b    1b
    nop
    nop
    .size csf_ladder_2404, . - csf_ladder_2404
