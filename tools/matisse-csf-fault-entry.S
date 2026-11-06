/* Build 2383: answer "fault or hang" at the vendor fault entry.
 *
 * The vendor vector table sends every Cortex-M fault to 0x010019b1, i.e. the
 * halfword at 0x010019b0, and that handler parks without leaving a trace. An
 * MCU-side fault does not set AS_FAULT either, so a counter of 9 after the
 * fetch-prime call cannot say whether the fetch never completed or faulted.
 *
 * This stub replaces the handler entry and:
 *   shared+12 = stacked PC   (the instruction that faulted)
 *   shared+20 = CFSR         (which fault: IACCVIOL, IBUSERR, PRECISERR...)
 *   shared+16 = 20           (a value the 9/10/11 probe never writes)
 *
 * LR holds EXC_RETURN on entry; bit 2 is the SPSEL the exception used, so the
 * frame is read from MSP or PSP accordingly. No other register or memory is
 * touched, and the stub parks exactly like the code it replaces.
 *
 * Assembled bytes are pinned in FAULT_ENTRY_2383 in tools/matisse-shim-gpu-image.py
 * and compared with this file by tools/tests/test_matisse_csf_fetch_prime.py.
 */
.syntax unified
.cpu cortex-m7
.thumb

.section .text.fault,"ax",%progbits
.global csf_fault_entry
.thumb_func
csf_fault_entry:
    mov  r3, lr
    tst  r3, #4
    ite  eq
    mrseq r0, msp
    mrsne r0, psp
    ldr  r1, [r0, #0x18]          /* stacked PC */
    movs r2, #1
    lsls r2, r2, #26              /* 0x04000000, the shared page */
    str  r1, [r2, #12]            /* shared+12 */
    ldr  r1, =0xE000ED28          /* SCB->CFSR */
    ldr  r0, [r1]
    str  r0, [r2, #20]            /* shared+20 */
    movs r1, #20
    str  r1, [r2, #16]            /* shared+16: fault taken */
1:  b    1b
