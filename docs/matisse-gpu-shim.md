# MT6983 shim GPU power/reset probe

2026-10-31. This independently written probe executes GPUEB INIT_SHARED_MEM,
POWER_ON, verifies both MFG power status registers, reads GPU_ID and performs
one CSF GPU soft reset, then releases its single power reference. It does not
load Arm CSF firmware, install GPU page tables or submit graphics work.

## Source of hardware facts

Actual modified LK payload SHA256 is
5310a43ac8b7aec6de3d1571b7012cb6ba3600958db3e4e9df4372fdc642ee84.
Register facts were cross-checked with extracted OS2.0.2.0 vendor KMD and
xiaomi-rubens commit270b84910b941bf75490fccdb5fb2b3021dd7cbf. No GPL
implementation was copied. Raw dumps and reference source remain ignored.

- LK0x20424..0x20474 polls GPUEB0x13c5fd24 for magic0x55667788.
- LK0x2041c stores the additional20MiB firmware allocation PA>>12 at0x13c5fd34.
- Live DT describes mailbox0x13c5fd80, set0x13c62004, clear0x13c62074,
  send0x13c62000 and recv0x13c62078. GPUFREQ pin1 TX+0x10/RX+0xbc,32B each.
- SPM sleep0x1c001000+0xf3c/+0xf40: MFG0 bit1, MFG1 bit2.
- GPU control base0x13000000: ID+0, AS_PRESENT+0x18, IRQ RAW+0x20,
  CLEAR+0x24, MASK+0x28, COMMAND+0x30. CSF soft reset is0x101, completion bit8.

## Bounds and ownership

Default loader builds do not reference this probe. SHIM_GPU_PROBE enables
it only for an exact normal-mode MT6983 live-FDT geometry. Channel tables
are parsed, not guessed. Shared2MiB and additional20MiB firmware memory
must not overlap the XNU memory window or each other. Conflict aborts before
the first XNU segment copy. No shared region is read or zeroed by this probe.

All polls have250ms and independent iteration limits. A pending response
is rejected, other channel interrupts are untouched. Replies are checked
for command/target/signed error. POWER_ON must return count1; unexpected
ownership prevents reset. Only a definitely acquired reference is released.
Timed-out POWER_ON is not retried and does not trigger a blind POWER_OFF.

GPU control registers are accessed only after valid IPI and both SPM checks.
Only expected v10 architecture is accepted; protected mode is rejected.
IRQ mask is saved/restored. The probe does not alter PMIC/PLL/RPC directly.
Host model tests cannot establish that real firmware booted or GPU powered.

## Existing console and Recovery return

The build reserves128B ADT slots for sweet-gpu-report and each shim firmware
version. Bounded summaries with prefix sweet-shim/gpu2320 are printed by
the existing XNU iBoot-version path, then flushed by established SWEETLOG
to the userdata tail. PE_init_iokit uses FW_VERS_LEN128 and enforces NUL.
The raw report is also available in the ADT. Old2317 logs are not a trial result.

Kernel0118 adds an explicit ADT diagnostic-window option. It stops feeding
the hardware watchdog after60seconds; default behavior remains unchanged.
The shim first validates the exact watchdog/reboot-mode FDT, selects the
volatile Recovery mode scratch and arms31seconds. No misc partition write.
Root is ufsrw=0/rootrw=0; existing0093 permits only persistent console tail
logging despite read-only VFS. Early hangs should also expire the watchdog.

An intact package Linux Image is embedded at shim+32MiB. Recovery/unknown
boot modes bypass shim_main and jump directly to that Linux at EL1 with
MMU/caches off. Normal mode executes the probe and XNU. First validate the
Recovery fallback alone, then test normal mode. LK/vendor_boot/DTBO stay intact.

Build-only tool matisse-shim-gpu-image.py requires SHA256 pins, reuses
frozen2313 board/display/UFS objects, and recompiles start/loader/new GPU
units only. Current unrelated dirty shim.c/build.sh are excluded. Combined
Image must end before measured live DTB. Stock fallback, generic ramdisk
and signature are byte-compared; signature is retained, not authenticated.

Host ASan/UBSan tests cover success, invalid mode/address, memory conflict,
power off, wrong magic, stale/negative/bad replies, bounded waits, stopped
timer, unexpected reference count/model, reset timeout and cleanup failure.
Actual FDT reader/ADT publication have regression tests. Hardware outcomes,
image hashes and restoration duty are recorded in NOTES and a fresh journal.
