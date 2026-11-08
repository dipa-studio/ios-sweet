/*
 * 2409: is PA bit 9 a property of the arena, or of the address space?
 *
 * Every access that has ever killed the MCU lies inside the 2 MiB arena
 * [0x40078000, 0x40278000). No bit-9 = 1 access has ever been made outside it,
 * so "bit 9 has no responder" and "this allocation's second 512-byte half has
 * no responder" still fit every measurement. This ladder separates them by
 * reading the same two 512-byte offsets of a page the arena does not back.
 *
 * Two leaves of the R-X section are repointed at the top of the bootloader's
 * splash reservation (see shim/gpu.c):
 *
 *   0x0100C000 -> ooa + 0x1000, leaf tag group 6 (the firmware's own tag)
 *   0x0100D000 -> ooa + 0x0000, leaf tag group 0 (no tag at all)
 *
 * The group tag is the confound this build has to control: the firmware tags
 * every leaf group 6 and the shim never proved that group 6's policy covers
 * anything but the arena. So the two control reads come first, one per tag,
 * before any bit-9 read is attempted.
 *
 *   marker 1  read 0x0100D400  g0, bit 9 = 0   control: does ooa respond at all
 *   marker 2  read 0x0100C400  g6, bit 9 = 0   control: does the tag change that
 *   marker 3  read 0x0100D200  g0, bit 9 = 1   the question, untagged
 *   marker 4  read 0x0100C200  g6, bit 9 = 1   the question, firmware tag
 *   marker 5  every access returned
 *
 * marker 1 only -> nothing outside the arena responds, even untagged
 * marker 2 only -> ooa responds untagged; the group-6 leaf does not
 * marker 3 only -> both controls returned and bit 9 stalls with no tag at all
 * marker 4      -> both halves answered; the wall is arena-shaped
 *
 * Every marker and every result has a DSB behind it for the reason 2405 spells
 * out: a posted store can outlive the read that follows it, and then "read N
 * stalled" and "marker N+1 never drained" look identical.
 *
 * Results go to shared+12 (the word the report publishes as output_va) *and*
 * to shared+0x200 + 4*n, so a hang after marker 3 still leaves the control
 * word behind. shared+16 and +20 are groups/group_stride and stay untouched.
 */
    .syntax unified
    .thumb
    .section .text.ladder, "ax", %progbits
    .global csf_ladder_2409
    .type csf_ladder_2409, %function
csf_ladder_2409:
    movw r2, #0x0000
    movt r2, #0x0400              /* r2 = shared base 0x04000000 */
    movw r6, #0x0000
    movt r6, #0x0100              /* r6 = code 0x01000000 */

    movs r0, #1
    str  r0, [r2, #8]             /* marker 1 */
    dsb  sy
    movw r8, #0xD400
    ldr.w r0, [r6, r8]            /* 0x0100D400: ooa, bit 9 = 0, untagged */
    str  r0, [r2, #12]
    str  r0, [r2, #0x200]
    dsb  sy

    movs r0, #2
    str  r0, [r2, #8]             /* marker 2: present <=> read 1 returned */
    dsb  sy
    movw r8, #0xC400
    ldr.w r0, [r6, r8]            /* 0x0100C400: ooa, bit 9 = 0, group 6 */
    str  r0, [r2, #12]
    str  r0, [r2, #0x204]
    dsb  sy

    movs r0, #3
    str  r0, [r2, #8]             /* marker 3: present <=> read 2 returned */
    dsb  sy
    movw r8, #0xD200
    ldr.w r0, [r6, r8]            /* 0x0100D200: ooa, bit 9 = 1, untagged */
    str  r0, [r2, #12]
    str  r0, [r2, #0x208]
    dsb  sy

    movs r0, #4
    str  r0, [r2, #8]             /* marker 4: present <=> read 3 returned */
    dsb  sy
    movw r8, #0xC200
    ldr.w r0, [r6, r8]            /* 0x0100C200: ooa, bit 9 = 1, group 6 */
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
    .size csf_ladder_2409, . - csf_ladder_2409
