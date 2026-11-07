/* Build 2402: the bit-9 matrix, run from the code section itself.
 *
 * 2401 put a marker at 1 (shared 0x04000200) and that read never returned, so
 * the whole series can be read as "bit 9 of the address decides". Every access
 * that ever returned has bit 9 clear; every hang has it set. Bit 9 is inside
 * the 4 KiB page offset, so the two addresses of a pair below are the same VA
 * page and the same PA page: no L2/L3 entry, no leaf, no physical page and no
 * walk can differ between them. Only one address bit does.
 *
 *   marker 1  read shared 0x04000000   bit9=0
 *   marker 2  read stack  0x02000000   bit9=0
 *   marker 3  read code   0x0100E400   bit9=0, the page this program runs from
 *   marker 4  read code   0x0100E200   bit9=1, the same page, 0x200 away
 *   marker 5  read stack  0x02000200   bit9=1
 *   marker 6  read shared 0x04000200   bit9=1 (2401 stalled here)
 *   marker 7  all six reads returned
 *
 * Order matters: a stall ends the run, so the three bit-9=0 reads go first.
 * They must all return for the matrix to mean anything; if they do, marker 4
 * is the decisive one because it is the tightest possible control - same
 * section, same page, same translation as marker 3, one bit apart. It is also
 * the read the 0x01000000 window hypothesis asked for in 2393..2400, which
 * never reached it. Markers 5 and 6 only run if marker 4 returns, i.e. only if
 * bit 9 is not the rule, and then they say whether the rule is per-section.
 *
 * No stack, no literal pool, no branch: every address is materialised in a
 * register, so nothing here can stall except the data read it names. The raw
 * bytes are pinned in COLD_BOOT_2402 in tools/matisse-shim-gpu-image.py and
 * compared with this file by tools/tests/test_matisse_csf_fetch_prime.py.
 * Thumb-2 memory is little-endian: clang/llvm-objdump prints a 32-bit
 * instruction as halfwords (e.g. f8d4 0200), but the bytes it stores are
 * d4 f8 00 02. Pin the section bytes, never the objdump display order.
 */
.syntax unified
.cpu cortex-m7
.thumb

.section .text.ladder,"ax",%progbits
.global csf_ladder_2402
.thumb_func
csf_ladder_2402:
    cpsid i
    movs r4, #1
    lsls r4, r4, #26              /* r4 = 0x04000000, shared */
    movs r5, #2
    lsls r5, r5, #24              /* r5 = 0x02000000, stack */
    movs r6, #1
    lsls r6, r6, #24              /* r6 = 0x01000000, code */
    movw r8, #0xE200
    movw r9, #0xE400
    movs r0, #1
    str  r0, [r4, #8]
    ldr  r0, [r4]                 /* marker 1: 0x04000000, bit 9 = 0 */
    movs r0, #2
    str  r0, [r4, #8]
    ldr  r0, [r5]                 /* marker 2: 0x02000000, bit 9 = 0 */
    movs r0, #3
    str  r0, [r4, #8]
    ldr.w r0, [r6, r9]            /* marker 3: 0x0100E400, bit 9 = 0, our page */
    movs r0, #4
    str  r0, [r4, #8]
    ldr.w r0, [r6, r8]            /* marker 4: 0x0100E200, bit 9 = 1, same page */
    movs r0, #5
    str  r0, [r4, #8]
    ldr.w r0, [r5, #0x200]        /* marker 5: 0x02000200, bit 9 = 1 */
    movs r0, #6
    str  r0, [r4, #8]
    ldr.w r0, [r4, #0x200]        /* marker 6: 0x04000200, bit 9 = 1 */
    movs r0, #7
    str  r0, [r4, #8]
1:  b    1b
    .balign 4
