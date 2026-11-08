/*
 * 2411: is PA bit 9 a property of the arena allocation, or of the address?
 *
 * 2409 asked this of the framebuffer defaults and answered nothing: those
 * defaults sum to 0xfffff000, so the MCU never returned even a bit-9 = 0
 * control and the run measured the address it was handed. 2410 moved the pages
 * to a shim-owned one and to LK's 20 MiB GPU firmware allocation, and the shim
 * died before it could hand the report back - the CPU witness read the firmware
 * allocation, which mtk_gpueb_boot.c warns is never to be dereferenced.
 *
 * 2411 keeps one remapped page and adds the control that was missing.
 * 0x0100C000 keeps the firmware's own leaf into the arena, so its read proves
 * the instrument is alive before anything new is asked; 0x0100D000 is
 * repointed at a page of this shim's BSS immediately past the arena, carrying
 * the same tag 6 as every other leaf.
 *
 *   marker 1  read 0x0100C400  arena leaf,      bit 9 = 0   instrument control
 *   marker 2  read 0x0100D400  page past aren,  bit 9 = 0   is it reachable
 *   marker 3  read 0x0100D200  page past aren,  bit 9 = 1   the question
 *   marker 4  every access returned
 *
 * Nothing here is dereferenced by the CPU except the shim's own page, which it
 * writes and reads back; the far memory that killed 2410 is not in this build.
 *
 * marker 1      -> the MCU never read the arena leaf it has read since 2333:
 *                  the run says nothing, check the entry before anything else
 * marker 2      -> the page past the arena is not reachable even at bit 9 = 0,
 *                  so the wall is about which pages the MCU may read at all
 * marker 3      -> both reads above returned and the bit-9 read stalled: bit 9
 *                  is not this allocation's property, it is the address bit
 * marker 4      -> both halves of a page the arena does not back answered, so
 *                  the wall is a property of the arena allocation
 *
 * Every marker and every result has a DSB behind it for the reason 2405 spells
 * out: a posted store can outlive the read that follows it, and then "read N
 * stalled" and "marker N+1 never drained" look identical.
 *
 * Results go to shared+12 (published as output_va) *and* to shared+0x200+4*n,
 * so a hang after marker 3 still leaves the earlier words behind. shared+16 and
 * +20 are groups/group_stride and stay untouched.
 */
    .syntax unified
    .thumb
    .section .text.ladder, "ax", %progbits
    .global csf_ladder_2411
    .type csf_ladder_2411, %function
csf_ladder_2411:
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
    str  r0, [r2, #0x200]
    dsb  sy

    movs r0, #2
    str  r0, [r2, #8]             /* marker 2: present <=> read 1 returned */
    dsb  sy
    movw r8, #0xD400
    ldr.w r0, [r6, r8]            /* 0x0100D400: past the arena, bit 9 = 0 */
    str  r0, [r2, #12]
    str  r0, [r2, #0x204]
    dsb  sy

    movs r0, #3
    str  r0, [r2, #8]             /* marker 3: present <=> read 2 returned */
    dsb  sy
    movw r8, #0xD200
    ldr.w r0, [r6, r8]            /* 0x0100D200: past the arena, bit 9 = 1 */
    str  r0, [r2, #12]
    str  r0, [r2, #0x208]
    dsb  sy

    movs r0, #4
    str  r0, [r2, #8]             /* marker 4: everything returned */
    dsb  sy
1:  b    1b
    nop
    nop
    /* pad to the 136 bytes the replaced stub occupies, so the replacement
     * covers the same region 2409/2410 did and no stale instruction survives */
    .rept 14
    nop
    .endr
    .balign 4
    .size csf_ladder_2411, . - csf_ladder_2411
