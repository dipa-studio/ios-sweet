/* Build 2385: does the MCU ever complete the fetch of a block it has never
 * touched?
 *
 * Every fetch this port has seen complete came from a block that was already
 * resident: the reset target 0x010018ec sits inside 0x01001800, and the only
 * other block ever read (0x01001900, 2375) is in that same block. Everything
 * cold stops: the branch to 0x01000200 (2379/2382/2383) and the firmware's own
 * literal load from 0x01001a00 (2370/2371/2373).
 *
 * The one fetch that cannot be warm is the first one: at reset nothing has run.
 * So this build moves the reset vector itself - the word at VA 0x4, in the
 * config section - from 0x010018ed to 0x0100E001, and puts this program at
 * 0x0100E000. That block is 56 KB into the code section, is executed by nothing
 * else, and is fetched only by the core's very first cycle.
 *
 *   shared+8 <- 0x0100E000   written only if that first fetch completed
 *   park
 *
 * One word, two answers:
 *   present  the core fetched a never-touched block at boot, so a cold fetch is
 *            possible and the wall is the path a running core uses to fetch
 *   absent   the first fetch has the same fate as every other cold one, so the
 *            memory path only ever serves lines something else already filled -
 *            and 0x01001800 worked because the container's write left it
 *            resident, not because reset is special
 *
 * No stack, no literal pool, no branch: nothing here can stall except the fetch
 * of these nine halfwords. The bytes are pinned in COLD_BOOT_2385 in
 * tools/matisse-shim-gpu-image.py and compared with this file by
 * tools/tests/test_matisse_csf_fetch_prime.py.
 */
.syntax unified
.cpu cortex-m7
.thumb

.section .text.cold,"ax",%progbits
.global csf_cold_boot
.thumb_func
csf_cold_boot:
    cpsid i
    movs r4, #1
    lsls r4, r4, #24              /* r4 = 0x01000000 */
    add.w r4, r4, #0xE000         /* r4 = 0x0100E000, this very block */
    movs r3, #1
    lsls r3, r3, #26              /* r3 = 0x04000000, the shared page */
    str  r4, [r3, #8]             /* shared+8: the marker */
    nop
1:  b    1b
