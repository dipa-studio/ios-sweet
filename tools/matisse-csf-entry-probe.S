/* Diagnostic overlay for the pinned Cortex-M reset path. No stack use.
 * r0/r1 are scratch until the original reset sequence initializes them.
 * Return with the original first three instructions' state, before its
 * first peripheral store. The separate marker never replaces version.
 */
.syntax unified
.cpu cortex-m7
.thumb
.section .text.csf_entry_jump,"ax",%progbits
.balign 4
.global csf_entry_jump
.type csf_entry_jump,%function
.thumb_func
csf_entry_jump:
#ifdef CSF_INLINE_MARKER
    cpsid i
    ldr r0, 1f
    ldr r1, 2f
    str r1, [r0]
    dsb sy
    b.w csf_entry_probe
.balign 4
1:  .word 0x04000ffc
2:  .word 0x53545542
#else
    b.w csf_entry_probe
    nop
    nop
#endif
.size csf_entry_jump, .-csf_entry_jump
#ifdef CSF_INLINE_MARKER
.thumb_set csf_entry_resume, csf_entry_jump + 24
#else
.thumb_set csf_entry_resume, csf_entry_jump + 8
#endif

.section .text.csf_entry_probe,"ax",%progbits
.balign 4
.global csf_entry_probe
.type csf_entry_probe,%function
.thumb_func
csf_entry_probe:
#ifndef CSF_INLINE_MARKER
    cpsid i
#endif
    ldr r0, 1f
    ldr r1, 2f
    str r1, [r0]
    dsb sy
    ldr r0, 3f
    ldr r0, [r0]
    mov.w r1, #11
#ifdef CSF_INLINE_MARKER
    str r1, [r0]
    ldr r0, 4f
    ldr r0, [r0]
    mov.w r1, #7
    str r1, [r0]
    ldr r0, 5f
    ldr r0, [r0]
    mov.w r1, #0x70000
#endif
    b.w csf_entry_resume
.balign 4
1:  .word 0x04000ffc
2:
#ifdef CSF_INLINE_MARKER
    .word 0x5452414d
#else
    .word 0x53545542
#endif
3:  .word 0x01001988
#ifdef CSF_INLINE_MARKER
4:  .word 0x0100198c
5:  .word 0x01001990
#endif
.size csf_entry_probe, .-csf_entry_probe
