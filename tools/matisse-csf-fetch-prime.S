/* Build 2379: fetch a fresh code block, return, then read it as data.
 * Link .text.fresh at 0x01000200 and .text.reset at 0x010018ec.
 * No stack access, literal pool, peripheral access or firmware continuation.
 * shared+8 identifies the target; shared+16 starts at the template's 8.
 */
.syntax unified
.cpu cortex-m7
.thumb

.section .text.fresh,"ax",%progbits
.global csf_fetch_prime_fresh
.thumb_func
csf_fetch_prime_fresh:
    nop
    bx lr

.section .text.reset,"ax",%progbits
.global csf_fetch_prime_reset
.thumb_func
csf_fetch_prime_reset:
    cpsid i
    movs r4, #1
    lsls r4, r4, #24
    add.w r4, r4, #0x200
    movs r3, #1
    lsls r3, r3, #26
    str r4, [r3, #8]
    ldr r2, [r3, #16]
    adds r2, #1
    str r2, [r3, #16]             /* 9: about to call the fresh block */
    bl csf_fetch_prime_fresh
    adds r2, #1
    str r2, [r3, #16]             /* 10: call returned */
    ldr r0, [r4, #16]             /* 0x01000210, value deliberately discarded */
    adds r2, #1
    str r2, [r3, #16]             /* 11: data read returned */
1:  b 1b
