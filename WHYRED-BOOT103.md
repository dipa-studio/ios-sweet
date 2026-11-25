# Boot103: block-byte units and quiet GUI logging

This candidate supports the current whyred UI bring-up with System102 retained.
It has not been installed or proven to fix intermittent UI presentation.

The current System102 boot eventually displayed a real, partial lock screen:
wallpaper, camera control and home indicator. User photos show a large pale upper
rectangle and red/orange banner; the image flashes and returns to black with the
backlight on. This supersedes the earlier observation of only the Apple logo.
The layout is incomplete and stable interaction/touch remain unproved.

A fresh earlier sample showed SpringBoard waiting for LaunchServices and lsd
waiting in a MobileGestalt Wi-Fi lookup. Later UI progress occurred without a
MobileGestalt cache edit. That sample establishes a slow path, not a permanent
wait or proof that factory Wi-Fi metadata will fix all UI issues.

## Source correction

XNU8796 `specfs:set_blocksize` uses `bdevsw.d_psize` as bytes per device block.
The whyred callback returned partition sector count. For a32MiB persist partition,
that sets65536-byte vnode blocks; `spec_read` rejects this above the16KiB page
size. Small partitions also receive incorrect units. Patch0178 returns512 for a
valid partition and retains-1 for invalid devices. Capacity remains separately
reported by `DKIOCGETBLOCKCOUNT`; write opens and write strategy stay denied.

The host contract test extracts the actual driver and specfs functions, reproduces
the old read rejection, checks512-byte units across four capacities, keeps capacity
and read-only assertions, and passes29 checks plus3 retained HFS checks. The old
driver fails the new unit check. No hardware behavior is emulated by that test.

## Layout-preserving candidate

The pinned packager accepts only the authenticated boot99 kernel and boot image.
It changes the result instruction in `whyred_emmc_psize` from capacity selection
to `mov w0,#512`, preserving the invalid-device return, all code/data addresses,
shim, ADT, and all other kernel bytes. It appends the supported `sweetnull=-`
argument and recomputes Android's image ID. All prior boot arguments are retained.

The layout UUID intentionally remains99's UUID so System102's existing matched
renderer and diagnostic ABI continue to work. This is a MODIFIED kernel, identified
by its new SHA256; a matching UUID does not prove an unchanged kernel. The artifact
is a bounded backport of the source correction, not a newly compiled full kernel.
It does not include the separate unflashed0177 touch implementation.

Exact candidate image22347776 bytes, SHA256
`69422ec4e548fe51391829559bba76a38024f92a7359f5f8b0c3ad7109fb72c1`.
Modified kernel SHA256
`7809054ed5e0965d2950086d7dc317b510958bcb7d5995e881b9b02b54545a52`.
The independent verifier checks every unchanged kernel byte, unchanged shim/ADT,
original command-line prefix, the added argument, loaded code agreement, the
expected ARM64 instruction and both invalid/valid returns, and the Android ID.
The guarded installer rehashes the candidate and boot99 rollback and authenticates
the existing complete System102 installation before allowing a boot-only write.

## Debug-output policy

Patch0048 defaults to teeing backboardd and SpringBoard writes to `/dev/null`
synchronously into the console/UART. At UI startup, the current boot produces
repeated `IOServiceMatchingfailed for: AppleM2ScalerCSCDriver` messages. The existing
`sweetnull=-` option makes `/dev/null` consume those writes normally. Kernel crash,
storage, USB, RAMFS and other diagnostics remain enabled. This removes debug-output
work; CPU starvation and framebuffer overwrite remain hypotheses until measured.

## Factory read helper

`tools/whyred-persist-read.c` permits only a pinned physical whyred kernel UUID,
root, the fixed persist device,512-byte blocks,65536 sectors and read-only media.
It queries geometry with GET ioctls and exports either16KiB or exactly32MiB after
checking the ext superblock magic. It never opens for write, issues SET/media-write
commands, edits metadata or prints identifiers. Raw exports belong in private
host files outside git. Factory Wi-Fi values must come from validated real data.

An earlier diagnostic attempted a fixed-block-size SET ioctl through an O_RDONLY
fd. XNU's vnode layer explicitly rejects that command from user space: EPERM,
zero exported bytes. That attempt established the policy boundary; it was not
bypassed. The final helper omits SET entirely and requires the corrected callback.
Its local native self-test and physical-target refusal pass; its locally linked
ARM64 iOS binary is signed/ISA checked. No new full iPhoneOS-SDK CI or successful
factory export is claimed yet.

## Next device check

Keep the complete boot99 rollback and System102 unchanged. A concrete boot-only
install requires fresh user Fastboot readiness. After boot, verify USB/SSH,
`sweetnull=-` in actual boot arguments, the bounded factory-read contract, and
continued automatic frames. Inspect the compositor and physical panel to distinguish
incomplete scene rendering from frame replacement and sleep. Real factory metadata
and GPIO/touch work remain separate from suppressing noisy debug output.
