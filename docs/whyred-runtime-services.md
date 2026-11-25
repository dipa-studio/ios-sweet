# Whyred runtime services candidate v76

This candidate addresses two observed userspace failures and makes framebuffer
content observable. It does not establish that SpringBoard renders a visible UI.

## Volatile development AppleKeyStore

`whyred_aks_volatile_wrap=1` enables paired selectors 10/11 in DEVELOPMENT/DEBUG
builds for this board. The implementation follows the iOS 16.5 call shapes:
bag handle and key class as two scalars, one returned actual-class scalar for
wrapping, and no returned scalars for unwrapping. A 32-byte key wraps to 40 bytes.

RFC 3394 AES key wrap uses the existing constant-time kernel AES provider.
Each supported numeric class (1..12) has an independent 256-bit KEK, generated
through the port's kernel PRNG before service publication. The KEKs are never
logged or persisted. Entropy quality depends on the existing port's boot seed
and timing inputs; fresh hardware RNG entropy has not been established.
Unwrapping checks integrity before releasing plaintext; malformed input,
unsupported bag/class, insufficient output and short descriptor I/O fail.
Only the existing system bag handle 0 is supported. Keys and scratch buffers
are cleared when their lifetimes end.

This supplies a volatile development format, not Apple's SEP keybag format,
passcode policy, rolled key generations or hardware protection. It is suitable
only for the current disposable RAMFS `/private/var`: wrapped data cannot be
recovered after a kernel reboot. The opt-in is disabled by default.

## Per-process driverkitd memory policy

The observed SIGKILL reason is a fatal per-process physical-footprint limit.
It does not establish global memory exhaustion or reveal the original budget.

`whyred_driverkitd_mem_mb=64` enables a trial floor of 64 MiB for the exact
process name `driverkitd`. Both active and inactive budgets pass through the
same policy at spawn and subsequent memorystatus property updates. Only
smaller finite budgets are raised; unlimited/default-larger budgets, other
processes, fatal attributes and pressure-kill behavior are preserved. Values
0..512 are accepted; 0 disables the floor and invalid values disable it.

`WHYRED driverkitd limits` reports requested/effective budgets, applied budgets
and current footprint. Warning/exceeded diagnostics include the actual task
ledger limit. These measurements are needed to assess the trial value.
The separate privileged legacy Mach API that writes the task ledger directly
retains its upstream behavior.

## Framebuffer content

The first eight presentation attempts and every 300th attempt report visible
source and panel pixel counts, nonzero RGB and alpha counts, and the bounding
box of nonzero RGB. Row padding and allocation tails are excluded. Source
surface identity, geometry and copy rectangles accompany the measurements.
The scan does not modify the image or print raw pixel buffers.

`WHYRED FB: presented` confirms copying to the framebuffer mapping. A full-frame
`rgb=0` measurement establishes black RGB at that observation; two zero sample
pixels alone do not. A nonzero count still does not establish physical scanout
or a correct iOS scene. Full scans are throttled because the display buffer is
mapped with write-combine attributes.

## Validation

The workflow executes the exact key-wrap helper and call boundary using the
same staged AES implementation, public known-answer vectors, integrity failures,
malformed lengths, class separation and guarded buffers. It executes the exact
memory-policy C helpers/macros for target and non-target processes and retains
the upstream kill path. Framebuffer tests cover 275 copy cases and 11 content
cases plus an attempt-budget check, including a nonblack pixel missed by the first and center samples.

Full kernel compilation, binary instruction audits and matched buildtree sources
are required before packaging. A hardware test remains necessary to establish
Keychain progress, the memory policy's effect and visible graphics.
