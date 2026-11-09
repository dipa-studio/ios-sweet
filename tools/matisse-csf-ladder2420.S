/* 2420: distinguish MCU store retirement from CPU-visible data.
 * Shared is mapped non-cacheable (vendor AttrIdx 5). The CPU seeds and samples
 * +0x200/+0x400 before AUTO and after the bounded wait, BEFORE reset/disable.
 * 1: control store/read, 2: odd-slot store/DSB, 3: odd-slot read, 4: all done.
 * No stack or literal pool; the odd store cannot hide its own checkpoint.
 */
.syntax unified
.cpu cortex-m7
.thumb
.section .text.ladder,"ax",%progbits
.global csf_ladder_2420
.thumb_func
csf_ladder_2420:
    cpsid i
    movw r4, #0
    movt r4, #0x0400
    movs r0, #1
    str r0, [r4, #8]
    dsb sy
    movw r1, #0xa400
    movt r1, #0x2420
    str.w r1, [r4, #0x400]
    dsb sy
    ldr.w r0, [r4, #0x400]
    str r0, [r4, #12]
    movs r0, #2
    str r0, [r4, #8]
    dsb sy
    movw r1, #0xa200
    movt r1, #0x2420
    str.w r1, [r4, #0x200]
    dsb sy
    movs r0, #3
    str r0, [r4, #8]
    dsb sy
    ldr.w r0, [r4, #0x200]
    str r0, [r4, #12]
    dsb sy
    movs r0, #4
    str r0, [r4, #8]
    dsb sy
1:  b 1b
    .balign 4
    .space 136 - (. - csf_ladder_2420), 0
