/*
 * A51 (Exynos 9611) probe shim entry: arm64 Linux Image header so S-Boot
 * treats us like a kernel. Expected: EL1 (Samsung's uH owns EL2), MMU and
 * D-cache off, x0 = DTB pointer. The probe prints what it really gets.
 */
	.section .text.head, "ax"
	.globl _head
_head:
	b	_start			/* code0 */
	.long	0			/* code1 */
	.quad	0x80000			/* text_offset, like the stock kernel */
	.quad	_end			/* image_size (linked at 0) */
	.quad	0xa			/* flags: LE, 4K pages, place anywhere */
	.quad	0			/* res2 */
	.quad	0			/* res3 */
	.quad	0			/* res4 */
	.ascii	"ARM\x64"		/* magic */
	.long	0			/* res5 (PE offset) */

	.text
	.globl _start
_start:
	msr	daifset, #0xf
	mov	x19, x0			/* DTB pointer from S-Boot */
	mrs	x1, CurrentEL
	cmp	x1, #(2 << 2)
	b.ne	1f
	/* Entered at EL2: run the probe from EL2 with the EL2 vectors. */
	adr	x1, _stack_top
	mov	sp, x1
	adr	x1, vectors
	msr	vbar_el2, x1
	b	2f
1:	msr	spsel, #1
	adr	x1, _stack_top
	mov	sp, x1
	adr	x1, vectors
	msr	vbar_el1, x1
2:	isb
	/* zero .bss */
	adr	x1, _bss_start
	adr	x2, _bss_end
3:	cmp	x1, x2
	b.hs	4f
	str	xzr, [x1], #8
	b	3b
4:	mov	x0, x19
	bl	shim_main
5:	wfe
	b	5b

/*
 * PSCI CPU_ON target. Samsung's PSCI 0.1 firmware need not pass the
 * context id, so the cpu index (0..7) comes from MPIDR: Aff0 + 4 * Aff1.
 * Before touching the stack, record MPIDR and the x0 we were given, so a
 * core that arrives but dies later is still visible.
 */
	.globl secondary_entry
secondary_entry:
	msr	daifset, #0xf
	mrs	x2, mpidr_el1
	and	x3, x2, #0xff
	ubfx	x4, x2, #8, #8
	add	x3, x3, x4, lsl #2
	and	x3, x3, #7
	/* Clean each marker to memory in case this core runs cacheable. */
	adr	x1, sec_marker
	add	x1, x1, x3, lsl #3
	str	x2, [x1]
	dc	civac, x1
	adr	x1, sec_ctx
	add	x1, x1, x3, lsl #3
	str	x0, [x1]
	dc	civac, x1
	dsb	sy
	/*
	 * Paint a green 96x64 block at x = 24 + idx * 128, y = 2300 straight
	 * into the framebuffer (stride 4320), visible whatever else fails.
	 */
	mov	x4, #0xca000000
	mov	x5, #2300
	mov	x6, #4320
	madd	x4, x5, x6, x4
	mov	x5, #128
	mul	x5, x3, x5
	add	x5, x5, #24
	add	x4, x4, x5, lsl #2
	mov	w6, #0xff00ff00
	mov	x10, #4320
	mov	x7, #64			/* rows */
4:	mov	x8, #96			/* pixels per row */
	mov	x9, x4
5:	str	w6, [x9]
	dc	civac, x9
	add	x9, x9, #4
	subs	x8, x8, #1
	b.ne	5b
	add	x4, x4, x10
	subs	x7, x7, #1
	b.ne	4b
	dsb	sy
	mov	x0, x3
	mrs	x1, CurrentEL
	cmp	x1, #(2 << 2)
	b.eq	1f
	msr	spsel, #1
	adr	x1, vectors
	msr	vbar_el1, x1
	b	3f
1:	adr	x1, vectors
	msr	vbar_el2, x1
3:	isb
	adr	x1, _sec_stacks
	add	x1, x1, x0, lsl #12
	add	x1, x1, #0x1000
	mov	sp, x1
	bl	secondary_main
2:	wfe
	b	2b

/*
 * Exception vectors (current EL only matters). Each slot stashes x29/x30,
 * loads its slot number and calls exc_handler(slot, regs), which paints
 * the panic screen and never returns.
 */
.macro vent slot
	.balign	0x80
	stp	x29, x30, [sp, #-16]!
	mov	x29, #\slot
	b	exc_common
.endm

	.balign	0x800
	.globl vectors
vectors:
	vent 0
	vent 1
	vent 2
	vent 3
	vent 4
	vent 5
	vent 6
	vent 7
	vent 8
	vent 9
	vent 10
	vent 11
	vent 12
	vent 13
	vent 14
	vent 15

exc_common:
	sub	sp, sp, #(30 * 8)
	stp	x0, x1, [sp, #0]
	mov	x0, x29
	mov	x1, sp
	bl	exc_handler
6:	wfe
	b	6b
