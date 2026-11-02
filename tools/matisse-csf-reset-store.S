/* Offline diagnostic for the pinned matisse Cortex-M reset entry. The host
 * patches these 20 bytes at the entry named by the existing reset vector.
 * No IRQ or valid CSF interface is fabricated; STUB is not an ABI version.
 */
.syntax unified
.cpu cortex-m7
.thumb
.section .text.csf_reset_store,"ax",%progbits
.balign 4
.global csf_reset_store
.type csf_reset_store,%function
.thumb_func
csf_reset_store:
    ldr r0, 1f
    ldr r1, 2f
    str r1, [r0]
    dsb sy
0:  b 0b
.balign 4
1:  .word 0x04000000
2:  .word 0x53545542
.size csf_reset_store, .-csf_reset_store
