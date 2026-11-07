/* Build 2401: the code section is mirrored at 0x03000000 and the reset vector
 * names this program at 0x0300E000. The ladder writes marker N before read N,
 * so the highest marker in shared+8 names the read that stopped the core:
 *
 *   marker 1  read shared    0x04000200   (control: RW, coherent)
 *   marker 2  read stack     0x02000200   (control: RW, cached, NX)
 *   marker 3  read same page 0x0300E200   (the page this program is fetched from)
 *   marker 4  read mirror    0x03001200   (fresh L3 page, fresh data page)
 *   marker 5  read alias     0x05001200   (same L3 page and leaf as read 6)
 *   marker 6  read code      0x01001200   (original window)
 *   marker 7  all reads returned
 *
 * Read 3 is the one that separates the two remaining readings: its translation
 * must already be resident (the core fetches from that very page), so a stall
 * there cannot be a cold walk. A stall at 4 with 3 returned says the walk or
 * the leaf is the problem; a stall at 5 says the original L3 page frame is;
 * a stall at 6 with 5 returned says the 0x0100xxxx VA itself is.
 *
 * No stack, no literal pool, no branch: every address is materialised in a
 * register, so nothing here can stall except the data read it names. The raw
 * bytes are pinned in COLD_BOOT_2401 in tools/matisse-shim-gpu-image.py and
 * compared with this file by tools/tests/test_matisse_csf_fetch_prime.py.
 * Thumb-2 memory is little-endian: clang/llvm-objdump prints a 32-bit
 * instruction as halfwords (e.g. f8d4 0200), but the bytes it stores are
 * d4 f8 00 02. Pin the section bytes, never the objdump display order.
 */
.syntax unified
.cpu cortex-m7
.thumb

.section .text.ladder,"ax",%progbits
.global csf_ladder_2401
.thumb_func
csf_ladder_2401:
    cpsid i
    movs r4, #1
    lsls r4, r4, #26              /* r4 = 0x04000000, shared */
    movs r5, #2
    lsls r5, r5, #24              /* r5 = 0x02000000, stack */
    movs r6, #1
    lsls r6, r6, #24              /* r6 = 0x01000000, code */
    movs r7, #3
    lsls r7, r7, #24              /* r7 = 0x03000000, mirror */
    movs r3, #5
    lsls r3, r3, #24              /* r3 = 0x05000000, shared code L3 */
    movw r9, #0x1200
    movw r8, #0xE200
    movs r0, #1
    str  r0, [r4, #8]
    ldr.w r0, [r4, #0x200]        /* marker 1: 0x04000200 */
    movs r0, #2
    str  r0, [r4, #8]
    ldr.w r0, [r5, #0x200]        /* marker 2: 0x02000200 */
    movs r0, #3
    str  r0, [r4, #8]
    ldr.w r0, [r7, r8]            /* marker 3: 0x0300E200, our own page */
    movs r0, #4
    str  r0, [r4, #8]
    ldr.w r0, [r7, r9]            /* marker 4: 0x03001200 */
    movs r0, #5
    str  r0, [r4, #8]
    ldr.w r0, [r3, r9]            /* marker 5: 0x05001200 */
    movs r0, #6
    str  r0, [r4, #8]
    ldr.w r0, [r6, r9]            /* marker 6: 0x01001200 */
    movs r0, #7
    str  r0, [r4, #8]
1:  b    1b
    .balign 4
