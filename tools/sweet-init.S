/*
 * First userspace program for SWEET bring-up: mockfs serves the RAM disk
 * itself as /sbin/launchd, so this static binary is PID 1. It proves that
 * exec, the user/kernel boundary, devfs and the console all work, then
 * stays alive (init exiting panics the kernel).
 *
 * tools/mkinit.py wraps the assembled __text into a static Mach-O, so this
 * must stay position independent with no relocations and no writable data:
 * every reference is adr (PC-relative), the PID digit lives on the stack.
 *
 * Raw XNU syscalls: number in x16, svc #0x80, carry set on error.
 */
#define SYS_write	4
#define SYS_open	5
#define SYS_getpid	20
#define SYS_select	93
#define O_RDWR		2

	.text
	.globl	_start
	.p2align 2
_start:
	/*
	 * The kernel enters a static binary with sp at argc, aligned only to
	 * what the argument/apple strings happened to need. Using a misaligned
	 * sp as a base register raises an SP alignment fault (SIGBUS) on real
	 * hardware (QEMU does not check), so align it like crt0/dyld do.
	 */
	mov	x9, sp
	and	x9, x9, #~15
	mov	sp, x9

	adr	x0, path
	mov	x1, #O_RDWR
	mov	x2, #0
	mov	x16, #SYS_open
	svc	#0x80
	b.cs	hang			/* no console: nothing to report to */
	mov	x19, x0

	adr	x1, hello
	adr	x2, hello_tail
	sub	x2, x2, x1
	bl	write_console

	mov	x16, #SYS_getpid
	svc	#0x80
	add	w0, w0, #'0'		/* PID 1 expected: one digit */
	sub	sp, sp, #16
	strb	w0, [sp]
	mov	x1, sp
	mov	x2, #1
	bl	write_console
	add	sp, sp, #16

	adr	x1, hello_tail
	adr	x2, hello_tail_end
	sub	x2, x2, x1
	bl	write_console

one_shot:
	/* One timeout-only select: isolate return status and avoid log interleaving. */
	adr	x1, before_select
	adr	x2, before_select_end
	sub	x2, x2, x1
	bl	write_console
	b.cs	hang
	mov	x0, #0
	mov	x1, #0
	mov	x2, #0
	mov	x3, #0
	adr	x4, five_sec
	mov	x16, #SYS_select
	svc	#0x80
	b.cs	select_failed

	adr	x1, select_returned
	adr	x2, select_returned_end
	sub	x2, x2, x1
	bl	write_console
	b.cs	hang
	adr	x1, diagnostic_done
	adr	x2, diagnostic_done_end
	sub	x2, x2, x1
	bl	write_console
	b	wait_forever

/* Keep PID 1 blocked after the one-shot probe so the CPU can idle. */
wait_forever:
	mov	x0, #0
	mov	x1, #0
	mov	x2, #0
	mov	x3, #0
	mov	x4, #0		/* NULL timeout: wait indefinitely */
	mov	x16, #SYS_select
	svc	#0x80
	b	wait_forever

select_failed:
	mov	x20, x0			/* Darwin errno from select */
	adr	x1, select_failed_message
	adr	x2, select_failed_end
	sub	x2, x2, x1
	bl	write_console
	b.cs	hang
	and	w21, w20, #0xf0
	lsr	w21, w21, #4
	adr	x22, hex_digits
	ldrb	w21, [x22, w21, uxtw]
	sub	sp, sp, #16
	strb	w21, [sp]
	and	w21, w20, #0x0f
	ldrb	w21, [x22, w21, uxtw]
	strb	w21, [sp, #1]
	mov	x1, sp
	mov	x2, #2
	bl	write_console
	add	sp, sp, #16
	b	hang

/* write(x19, x1, x2) */
write_console:
	mov	x0, x19
	mov	x16, #SYS_write
	svc	#0x80
	ret

hang:
	b	hang

	.p2align 3
five_sec:
	.quad	5			/* tv_sec */
	.quad	0			/* tv_usec (int32 + padding) */
path:
	.asciz	"/dev/console"
hello:
	.ascii	"\n*** SWEET userspace: init running as PID "
hello_tail:
	.ascii	" ***\n"
hello_tail_end:
before_select:
	.ascii	"SWEET init: one-shot select(5s) begin\n"
before_select_end:
select_returned:
	.ascii	"SWEET init: one-shot select returned OK\n"
select_returned_end:
select_failed_message:
	.ascii	"SWEET init: one-shot select errno=0x"
select_failed_end:
diagnostic_done:
	.ascii	"SWEET init: one-shot diagnostic complete\n"
diagnostic_done_end:
hex_digits:
	.ascii	"0123456789abcdef"

