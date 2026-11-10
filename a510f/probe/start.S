/*
 * SM-A510F (a5xelte, Exynos 7580) feasibility probe: entry and vectors.
 *
 * Carries an arm64 Linux Image header so Samsung S-Boot loads it the way it
 * loads the LineageOS arm64 kernel. Expected entry state (arm64 boot
 * protocol): EL2 or EL1, MMU and D-cache off, x0 = DTB pointer.
 * Everything here is PC-relative; the image runs wherever S-Boot puts it.
 */
	.section .text.head, "ax"
	.globl _head
_head:
	b	_start			/* code0 */
	.long	0			/* code1 */
	.quad	0x80000			/* text_offset (3.10-era arm64 value) */
	.quad	_end			/* image_size (linked at 0) */
	.quad	0xa			/* flags: LE, 4K pages, place anywhere */
	.quad	0			/* res2 */
	.quad	0			/* res3 */
	.quad	0			/* res4 */
	.ascii	"ARM\x64"		/* magic */
	.long	0			/* res5 */

	.text
	.globl _start
_start:
	msr	daifset, #0xf
	mov	x19, x0			/* DTB pointer from S-Boot */
	adr	x20, _head		/* where we were loaded */
	adr	x1, _stack0_top
	mov	sp, x1
	bl	install_vectors
	/* zero .bss */
	adr	x1, _bss_start
	adr	x2, _bss_end
1:	cmp	x1, x2
	b.hs	2f
	str	xzr, [x1], #8
	b	1b
2:	mov	x0, x19
	mov	x1, x20
	bl	probe_main
3:	wfe
	b	3b

/* PSCI CPU_ON target for the watchdog core. Does not touch .bss. */
	.globl secondary_entry
secondary_entry:
	msr	daifset, #0xf
	adr	x1, _stack1_top
	mov	sp, x1
	bl	install_vectors
	bl	secondary_main
4:	wfe
	b	4b

/* Point VBAR at our table for whichever EL we are running in. */
install_vectors:
	adr	x0, vectors
	mrs	x1, CurrentEL
	cmp	x1, #(2 << 2)
	b.eq	5f
	msr	vbar_el1, x0
	isb
	ret
5:	msr	vbar_el2, x0
	isb
	ret

/*
 * Exception vectors. Any exception (e.g. an SMC with no handler behind it,
 * or an undefined system register) is recorded in exc_record and execution
 * resumes at the next instruction for synchronous ones, so one failing test
 * does not kill the probe.
 */
	.macro	vent idx
	.balign	0x80
	stp	x16, x17, [sp, #-16]!
	mov	x17, #\idx
	b	exc_common
	.endm

	.balign	2048
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
	stp	x0, x1, [sp, #-16]!
	mrs	x16, CurrentEL
	cmp	x16, #(2 << 2)
	b.eq	6f
	mrs	x0, esr_el1
	mrs	x1, elr_el1
	b	7f
6:	mrs	x0, esr_el2
	mrs	x1, elr_el2
7:	adr	x16, exc_record
	str	x0, [x16, #8]		/* last ESR */
	str	x1, [x16, #16]		/* last ELR */
	str	x17, [x16, #24]		/* last vector slot */
	ldr	x0, [x16]
	add	x0, x0, #1
	str	x0, [x16]		/* count */
	dsb	sy
	/* synchronous slots are 0, 4, 8, 12: skip the faulting instruction */
	tst	x17, #3
	b.ne	9f
	add	x1, x1, #4
	mrs	x16, CurrentEL
	cmp	x16, #(2 << 2)
	b.eq	8f
	msr	elr_el1, x1
	b	9f
8:	msr	elr_el2, x1
9:	ldp	x0, x1, [sp], #16
	ldp	x16, x17, [sp], #16
	eret

	.data
	.balign	8
	.globl exc_record
exc_record:
	.quad	0, 0, 0, 0		/* count, esr, elr, slot */
