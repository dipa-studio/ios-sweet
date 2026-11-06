/* Builds 2385/2386: does the MCU ever complete the fetch of a block it has
 * never touched - and does that answer depend on which block it is?
 *
 * Every fetch this port has seen complete came from a block that was already
 * resident: the reset target 0x010018ec sits inside 0x01001800, and the only
 * other block ever read (0x01001900, 2375) is in that same block. Everything
 * cold stops: the branch to 0x01000200 (2379/2382/2383) and the firmware's own
 * literal load from 0x01001a00 (2370/2371/2373).
 *
 * The one fetch that cannot be warm is the first one: at reset nothing has run.
 * So these builds move the reset vector itself - the word at VA 0x4, in the
 * config section - onto this program, which is fetched only by the core's very
 * first cycle:
 *
 *   2385  COLD_TARGET 0x0100E000  a block 56 KB into the code section that
 *         nothing else executes, so the block itself cannot be the reason
 *   2386  COLD_TARGET 0x01000200  the block every branch and every data read
 *         has failed to reach; the program replaces the 2379 probe stub there
 *
 * Same twenty bytes in both, only the immediate differs, so the two images are
 * a controlled A/B on the block and nothing else.
 *
 *   shared+8 <- COLD_TARGET   written only if that first fetch completed
 *   park
 *
 * One word, two answers:
 *   present  a cold fetch completes, so the wall is the path a running core
 *            uses, not the block and not the memory path
 *   absent   the first fetch of this block has the same fate as every other
 *            cold one, so the block or its page differs from one that worked
 *
 * No stack, no literal pool, no branch: nothing here can stall except the fetch
 * of these nine halfwords. The bytes are pinned in COLD_BOOT_2385 in
 * tools/matisse-shim-gpu-image.py and compared with this file by
 * tools/tests/test_matisse_csf_fetch_prime.py, which links this file twice with
 * -DCOLD_TARGET=<block>.
 */
#ifndef COLD_TARGET
#define COLD_TARGET 0x0100E000
#endif
.syntax unified
.cpu cortex-m7
.thumb

.section .text.cold,"ax",%progbits
.global csf_cold_boot
.thumb_func
csf_cold_boot:
    cpsid i
#ifdef COLD_TARGET_WIDE
    /* 0x010018ec is out of range of both add.w's modified immediate and addw's
     * 12-bit field, so this variant materialises the whole word instead: 24
     * bytes rather than 20, still no stack, no literal pool, no branch.
     * 2385..2389 keep their pinned add.w bytes untouched. */
    movw r4, #(COLD_TARGET & 0xFFFF)
    movt r4, #((COLD_TARGET >> 16) & 0xFFFF)
#else
    movs r4, #1
    lsls r4, r4, #24              /* r4 = 0x01000000 */
    add.w r4, r4, #(COLD_TARGET & 0xFFFF)   /* r4 = COLD_TARGET, this very block */
#endif
    movs r3, #1
    lsls r3, r3, #26              /* r3 = 0x04000000, the shared page */
    str  r4, [r3, #8]             /* shared+8: the marker */
    nop
1:  b    1b
