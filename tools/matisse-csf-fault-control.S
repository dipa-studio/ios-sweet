/* Build 2384: positive control for the 2383 fault entry.
 *
 * 2383 read counter 9 and concluded "no fault was taken". That conclusion is
 * only as good as the instrument: the fault-entry stub at 0x010019b0 has never
 * been observed to fire. This program replaces the entry window with a
 * deliberate fault so the instrument can be seen working.
 *
 * Order matters: the marker is written first, so a run that stalls at the fault
 * is still distinguishable from a run that never started.
 *
 *   shared+8  <- 0x01000200   the probe marker, as 2379/2382/2383 wrote it
 *   read 0x03000000           the protected section, deliberately unmapped
 *   shared+16 <- 30           only reached if that read completes
 *
 * Three outcomes, three answers:
 *   20  the 2383 stub fired -> the instrument works and 2383's 9 is final
 *   30  the unmapped read completed without faulting -> the address space is
 *       larger than the built tables, and 2383's 9 needs re-reading
 *   0   the marker is present but the read neither faulted nor completed ->
 *       unmapped accesses stall exactly like the cold fetch, so "no exception"
 *       is not evidence of anything
 *
 * Nothing else changes: 2384 keeps 2383's relocation and fault-entry patch.
 * Bytes are pinned in FAULT_CONTROL_2384 in tools/matisse-shim-gpu-image.py and
 * compared with this file by tools/tests/test_matisse_csf_fetch_prime.py.
 */
.syntax unified
.cpu cortex-m7
.thumb

.section .text.control,"ax",%progbits
.global csf_fault_control
.thumb_func
csf_fault_control:
    cpsid i
    movs r4, #1
    lsls r4, r4, #24
    add.w r4, r4, #0x200          /* r4 = 0x01000200 */
    movs r3, #1
    lsls r3, r3, #26              /* r3 = 0x04000000, the shared page */
    str  r4, [r3, #8]             /* shared+8: the marker */
    movs r0, #3
    lsls r0, r0, #24              /* r0 = 0x03000000, unmapped on purpose */
    ldr  r1, [r0]                 /* the deliberate fault */
    movs r1, #30
    str  r1, [r3, #16]            /* 30: the read completed */
1:  b    1b
