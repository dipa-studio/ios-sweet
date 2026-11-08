/* Build 2403: does the 0x0100xxxx VA prefix decide, or the leaf/PA?
 *
 * 2402 proved that bit 9 decides inside one 4 KiB page: 0x0100E400 (bit 9 = 0)
 * returned and 0x0100E200 (bit 9 = 1) did not, same L2 entry, same L3 entry,
 * same leaf, same physical page. This build adds an L2 alias - slot 24 gets
 * slot 8's entry verbatim - so 0x0300E200 walks the identical L3 page, the
 * identical leaf descriptor and the identical physical word as 0x0100E200.
 * Only the VA differs. The ladder stays at 0x0100E000, so the first read is
 * the same known-good read 2402 used.
 *
 *   marker 1  read 0x0100E400   bit9 0, the page we execute from
 *             and copy the word to shared+12 as a data check
 *   marker 2  read 0x0300E200   bit9 1, alias of 0x0100E200: same leaf and PA
 *   marker 3  read 0x01001200   bit9 1, the uncached + PBHA 0 page (2x2 corner)
 *   marker 4  read 0x0100E200   bit9 1, the 0x01 VA again - 2402's control
 *   marker 5  all four returned
 *
 * Read 2 is the question: if it returns, the refusal is keyed on the VA above
 * the MMU, because the leaf, the table page and the physical word are the same
 * ones read 4 uses. If it stalls, the VA prefix is not the wall and the stall
 * travels with the page/leaf/bit.
 *
 * Reads 3 and 4 only execute if read 2 returned, i.e. only in the world where
 * the alias works. Then 3 asks whether the missing cell of the attribute matrix
 * (uncached + PBHA 0, the first time both are cleared at once) also works, and
 * 4 repeats 2402's own address in the same boot as its alias.
 *
 * No stack, no literal pool, no branch: every address is materialised in a
 * register, so nothing here can stall except the data read it names. The raw
 * bytes are pinned in COLD_BOOT_2403 in tools/matisse-shim-gpu-image.py and
 * compared with this file by tools/tests/test_matisse_csf_fetch_prime.py.
 * Thumb-2 memory is little-endian: clang/llvm-objdump prints a 32-bit
 * instruction as halfwords (e.g. f8d6 0200), but the bytes it stores are
 * d6 f8 00 02. Pin the section bytes, never the objdump display order.
 */
.syntax unified
.cpu cortex-m7
.thumb

.section .text.ladder,"ax",%progbits
.global csf_ladder_2403
.thumb_func
csf_ladder_2403:
    cpsid i
    movs r4, #1
    lsls r4, r4, #26              /* r4 = 0x04000000, shared */
    movs r6, #1
    lsls r6, r6, #24              /* r6 = 0x01000000, code */
    movs r7, #3
    lsls r7, r7, #24              /* r7 = 0x03000000, alias of the code L3 */
    movw r8, #0xE200
    movw r9, #0xE400
    movw r3, #0x1200
    movs r0, #1
    str  r0, [r4, #8]
    ldr.w r0, [r6, r9]            /* marker 1: 0x0100E400, bit 9 = 0 */
    str  r0, [r4, #12]            /* sampled word -> output_va */
    movs r0, #2
    str  r0, [r4, #8]
    ldr.w r0, [r7, r8]            /* marker 2: 0x0300E200, the alias */
    movs r0, #3
    str  r0, [r4, #8]
    ldr.w r0, [r6, r3]            /* marker 3: 0x01001200, uncached + PBHA 0 */
    movs r0, #4
    str  r0, [r4, #8]
    ldr.w r0, [r6, r8]            /* marker 4: 0x0100E200, 2402's address */
    movs r0, #5
    str  r0, [r4, #8]
1:  b    1b
    .balign 4
