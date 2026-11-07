/* Build 2401: separate an AXI read-channel hang from a Cortex-M7 fault.
 *
 * Build 2383 replaced the vendor fault handler with a stub that writes the
 * stacked PC and CFSR and parks. That is already enough to tell a fault from a
 * hang, but only if the reader knows to look at groups == 20. This variant
 * puts the answer in input_va, the field every capture is read for:
 *
 *   shared+8  = 0xE3   (a value no ladder marker and no probe ever writes)
 *   shared+12 = stacked PC   (the instruction that faulted)
 *   shared+20 = CFSR         (IACCVIOL, IBUSERR, PRECISERR, IMPRECISERR...)
 *
 * It no longer writes shared+16 = 20: input_va carries the signal now, and the
 * four bytes pay for the extra store. The slot at 0x010019b0 is exactly forty
 * bytes of vendor handler, and the patch engine refuses a length change, so
 * this file must stay forty bytes and keep its four-byte alignment.
 *
 * LR holds EXC_RETURN on entry; bit 2 is the SPSEL the exception used, so the
 * frame is read from MSP or PSP accordingly. No other register or memory is
 * touched, and the stub parks exactly like the code it replaces.
 *
 * Assembled bytes are pinned in FAULT_ENTRY_2401 in tools/matisse-shim-gpu-image.py
 * and compared with this file by tools/tests/test_matisse_csf_fetch_prime.py.
 */
.syntax unified
.cpu cortex-m7
.thumb

.section .text.fault,"ax",%progbits
.global csf_fault_entry_2401
.thumb_func
csf_fault_entry_2401:
    movs r2, #1
    lsls r2, r2, #26              /* 0x04000000, the shared page */
    movs r0, #0xE3
    str  r0, [r2, #8]             /* shared+8: fault taken */
    tst  lr, #4
    ite  eq
    mrseq r0, msp
    mrsne r0, psp
    ldr  r1, [r0, #0x18]          /* stacked PC */
    str  r1, [r2, #12]            /* shared+12 */
    ldr  r1, =0xE000ED28          /* SCB->CFSR */
    ldr  r0, [r1]
    str  r0, [r2, #20]            /* shared+20 */
1:  b    1b
    nop
