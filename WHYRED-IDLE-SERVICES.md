# Idle interrupt-stack repair and service diagnostics

The v82 UART panic is `preemption count not 0`, count 1, in kernel_task tid 102.
Its kernel UUID matches the installed v82 binary. Symbolication places the check
in the ARM64 user-return path, rather than inside a daemon. Thread creation order
identifies tid 102 as the boot CPU idle thread; idle deliberately holds one
preemption-disable reference. The panic text alone does not identify the original
instruction or prove which saved state was corrupted.

Patch 0120 introduced an unsafe combination: `Idle_context` switches to
CPU_ISTACKPTR, then the proximate-timer wait unmasks IRQs there. An IRQ allocates
its saved state below the interrupted SP, but SWITCH_TO_INT_STACK resets the
handler SP to that same interrupt-stack top. Handler calls can overwrite both
the live idle frames and the exception saved state. This is a concrete stack
ownership defect consistent with the observed idle-thread user-return assertion.

Patch 0163 replaces only that SWEET timer wait with a pending-interrupt loop
using DSB SY and WFI while preserving DAIF. WFI can wake for a signaled pending
IRQ without taking its handler while PSTATE.I is set. GIC priority/group enables
stay unchanged. The pending interrupt is handled after Idle_load_context restores
the thread stack. Spurious WFI returns are rechecked. The ordinary thread-stack
unmasked WFE recommendation path remains valid. The preemption assertion is kept.
See the [Linux ARM64 idle sequence](https://github.com/torvalds/linux/blob/v6.1/arch/arm64/kernel/idle.c)
for the same masked-WFI approach and its interrupt-controller priority caveat.
Physical wakeup and absence of the reported panic still require a device run.

The supplied full UART contains repeated `exec bluetoothd` and `exec fairplayd.H2`
without their exit causes; a later tail adds repeated suggestd. Those exec lines
precede completion. The full capture first exhausts the 8192-page RAMFS quota
before its first pkd attempt, while bluetoothd/fairplayd repeats already occur
before quota exhaustion. The separate lsd SIGSEGV is a userspace crash. These
observations do not establish a common daemon failure cause.

Patch 0164 adds default-off `whyred-service-trace=1` for exactly bluetoothd,
fairplayd.H2, suggestd, lsd and pkd. `WHYRED SERVICE` prints ticks, fixed target
name, PID, event, sequence, errno, detail, raw wait status and OS reason namespace/
64-bit code. Exec/spawn detail means image activation completed; it does not
prove userspace initialization. Exit detail means internal posix_spawn failure.
Decode exit status with Darwin wait macros: e.g. 0x100 is normal exit 1; 0xb is
signal 11. Exit reporting runs once in proc_exit, after unlocking and before
reference cleanup, including direct task-termination paths.

Each target/event has a saturating atomic 64-record budget: at most 960 records
across both translation units. There are no allocations, user-memory reads,
path lookups or reason-buffer parsing. The hooks keep live process references
and print outside proc locks. Jobs, KeepAlive policies and return values are
unchanged. Errors occurring before a target process name is assigned are outside
this diagnostic's coverage. This patch diagnoses the daemon loops; it does not
claim to repair their unknown exit causes.

`tools/test-whyred-idle-services.py` runs the actual wait and reporting helpers
with modeled interrupts/kernel services. It covers already-pending interrupts,
16 spurious wakeups, mask/barrier ordering, disabled and malformed configuration,
exact target selection, event fields, 64-bit reason codes, saturation and 8000
concurrent report attempts. Assembly and hook-placement contracts are checked.
Local UBSan passes 799 checks; all three changed ARM64 units compile with zero
LSE/PAN instructions. Restoring the unmasked timer call or weakening the output
budget fails a negative control. Host tests do not emulate real GIC wakeup or
kernel stack execution. Full CI41329547329 subsequently passed all27 steps, including799 ASan+UBSan
checks, retained USB614/RAMFS1120134 and the complete ARM64 build. Downloaded
artifacts match provenance, digest, length and CRC. Packaged linked cpu_idle
contains the pending-IRQ/DSB/WFI wait with no DAIFClr; runtime sources match the
reviewed files. V85 was flashed and booted; v87 now retains this repair. The
supplied later trace does not establish long-term idle stability.

V85 lifecycle output records successful image activation followed by normal
exit0 for fairplayd.H2 and bluetoothd. Suggestd exits2 without an OS reason or
signal. Pkd receives SIGABRT with the previous container-related stack, while
lsd still receives SIGSEGV in the Objective-C class-metadata retain path.
Neither the suggestd status alone nor the other clean exits identifies a cause.

Read-only analysis of the authenticated bluetoothd binary finds an early branch
that checks /dev/uart.bluetooth, then marconi-bt and bluetooth IOKit matches.
If none exists, that branch terminates through errx with status0. This is a
specific explanation consistent with the trace, not confirmation that the
device took that branch. Hardware transport support remains unverified. No
dummy service, forced successful initialization or KeepAlive change was added.
