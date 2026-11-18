
.section .text.head, "ax"
.global _head
.global _start

_head:
    b _start
    .long 0
    .quad 0x80000
    .quad _end - _head
    .quad 0xA
    .quad 0
    .quad 0
    .quad 0
    .ascii "ARM\x64"
    .long 0

    .org 0x800

_start:
    // Preserve the incoming boot arguments before using registers.
    adrp x9, boot_state
    add  x9, x9, :lo12:boot_state

    stp x0, x1, [x9, #0]
    stp x2, x3, [x9, #16]

    mov x10, sp
    mrs x11, CurrentEL
    mrs x12, DAIF

    stp x10, x11, [x9, #32]
    str x12, [x9, #48]

    // Select the current exception level's SP_ELx.
    msr spsel, #1

    // Install our own stack.
    adrp x9, _stack_top
    add  x9, x9, :lo12:_stack_top
    mov sp, x9

    bl minimal_main

1:
    wfe
    b 1b
