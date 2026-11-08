/*
 * 2410: is PA bit 9 a property of the arena allocation, or of the address?
 *
 * 2409 asked this of the last pages of the framebuffer defaults and got no
 * answer, because those defaults sum to 0xfffff000: the MCU never returned even
 * the bit-9 = 0 control, so the run measured the address it was given, not bit
 * 9. 2410 keeps the access pattern and moves the pages to memory whose backing
 * is not a guess:
 *
 *   0x0100D000 -> near, a page of this shim's own BSS beside the arena
 *   0x0100C000 -> far,  a page inside LK's 20 MiB GPU firmware allocation
 *
 * Both leaves keep the tag the firmware puts on every other leaf (group 6), so
 * bit 9 is the only variable left. The two controls run first: a stall at
 * marker 2 then says the far page was not reachable, not that bit 9 bit.
 *
 *   marker 1  read 0x0100D400  near, bit 9 = 0   control
 *   marker 2  read 0x0100C400  far,  bit 9 = 0   control
 *   marker 3  read 0x0100D200  near, bit 9 = 1   the question, beside the arena
 *   marker 4  read 0x0100C200  far,  bit 9 = 1   the question, in GPU firmware
 *   marker 5  every access returned
 *
 * marker 2 only -> the far page is not reachable; bit 9 untested at distance
 * marker 3 only -> bit 9 stalls on a page the arena does not back, so the wall
 *                  is the address bit and not this allocation
 * marker 4 only -> bit 9 is harmless beside the arena and fatal in the GPU's own
 *                  firmware allocation: the wall follows the allocation
 * marker 5      -> both halves of both pages answered
 *
 * The near page holds 0x2410a400 at +0x400 and 0x2410a200 at +0x200, so the word
 * the MCU returns names the page and the offset by itself; the far page is
 * read-only and is compared against the CPU's own read of the same PA.
 *
 * Every marker and every result has a DSB behind it for the reason 2405 spells
 * out: a posted store can outlive the read that follows it, and then "read N
 * stalled" and "marker N+1 never drained" look identical.
 *
 * Results go to shared+12 (the word the report publishes as output_va) *and*
 * to shared+0x200 + 4*n, so a hang after marker 3 still leaves the earlier
 * words behind. shared+16 and +20 are groups/group_stride and stay untouched.
 */
    .syntax unified
    .thumb
    .section .text.ladder, "ax", %progbits
    .global csf_ladder_2410
    .type csf_ladder_2410, %function
csf_ladder_2410:
    movw r2, #0x0000
    movt r2, #0x0400              /* r2 = shared base 0x04000000 */
    movw r6, #0x0000
    movt r6, #0x0100              /* r6 = code 0x01000000 */

    movs r0, #1
    str  r0, [r2, #8]             /* marker 1 */
    dsb  sy
    movw r8, #0xD400
    ldr.w r0, [r6, r8]            /* 0x0100D400: near, bit 9 = 0 */
    str  r0, [r2, #12]
    str  r0, [r2, #0x200]
    dsb  sy

    movs r0, #2
    str  r0, [r2, #8]             /* marker 2: present <=> read 1 returned */
    dsb  sy
    movw r8, #0xC400
    ldr.w r0, [r6, r8]            /* 0x0100C400: far, bit 9 = 0 */
    str  r0, [r2, #12]
    str  r0, [r2, #0x204]
    dsb  sy

    movs r0, #3
    str  r0, [r2, #8]             /* marker 3: present <=> read 2 returned */
    dsb  sy
    movw r8, #0xD200
    ldr.w r0, [r6, r8]            /* 0x0100D200: near, bit 9 = 1 */
    str  r0, [r2, #12]
    str  r0, [r2, #0x208]
    dsb  sy

    movs r0, #4
    str  r0, [r2, #8]             /* marker 4: present <=> read 3 returned */
    dsb  sy
    movw r8, #0xC200
    ldr.w r0, [r6, r8]            /* 0x0100C200: far, bit 9 = 1 */
    str  r0, [r2, #12]
    str  r0, [r2, #0x20c]
    dsb  sy

    movs r0, #5
    str  r0, [r2, #8]             /* marker 5: everything returned */
    dsb  sy
1:  b    1b
    nop
    nop
    .balign 4
    .size csf_ladder_2410, . - csf_ladder_2410
