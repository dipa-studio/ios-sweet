/*
 * 2412: the page past the arena, asked properly this time.
 *
 * 2411 proved two things and then stopped: the arena control read returned the
 * firmware's own word at 0x0100C400 (0xb001500c), and the result store to
 * shared+0x0c landed - but the next instruction, the same word written to
 * shared+0x200, never completed. shared+0x0c has bit 9 = 0 and shared+0x200 has
 * bit 9 = 1, in the same page, through the same mapping, with the same tag. So a
 * write at bit 9 = 1 stalls exactly like a read, and 2411 never reached the page
 * it was built to ask about. 2405's ladder had the same store in it; no earlier
 * build ever got that far, so this is the first time it was exercised.
 *
 * 2412 keeps one result word, at shared+0x0c, and no other slot: every extra
 * slot is another chance to hang the core between two markers for a reason that
 * is not the question.
 *
 *   marker 1  read 0x0100C400  arena leaf,     bit 9 = 0   instrument control
 *   marker 2  read 0x0100D400  past the arena, bit 9 = 0   is it reachable
 *   marker 3  read 0x0100D200  past the arena, bit 9 = 1   the question
 *   marker 4  every access returned
 *
 * marker 1 -> the instrument itself is dead; nothing here is about memory
 * marker 2 -> the page past the arena is not reachable even at bit 9 = 0
 * marker 3 -> bit 9 is the address bit, not this allocation
 * marker 4 -> the wall is a property of the arena allocation
 *
 * Every marker and every result has a DSB behind it for the reason 2405 spells
 * out: a posted store can outlive the read that follows it, and then "read N
 * stalled" and "marker N+1 never drained" look identical.
 */
    .syntax unified
    .thumb
    .section .text.ladder, "ax", %progbits
    .global csf_ladder_2412
    .type csf_ladder_2412, %function
csf_ladder_2412:
    movw r2, #0x0000
    movt r2, #0x0400              /* r2 = shared base 0x04000000 */
    movw r6, #0x0000
    movt r6, #0x0100              /* r6 = code 0x01000000 */

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
    movw r8, #0xD400
    ldr.w r0, [r6, r8]            /* 0x0100D400: past the arena, bit 9 = 0 */
    str  r0, [r2, #12]
    dsb  sy

    movs r0, #3
    str  r0, [r2, #8]             /* marker 3: present <=> read 2 returned */
    dsb  sy
    movw r8, #0xD200
    ldr.w r0, [r6, r8]            /* 0x0100D200: past the arena, bit 9 = 1 */
    str  r0, [r2, #12]
    dsb  sy

    movs r0, #4
    str  r0, [r2, #8]             /* marker 4: everything returned */
    dsb  sy
1:  b    1b
    nop
    nop
    .rept 20
    nop
    .endr
    .balign 4
    .size csf_ladder_2412, . - csf_ladder_2412
