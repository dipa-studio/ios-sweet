# matisse GPUEB RAM collector

2026-10-31. One specifically authorized trial is complete; original boot_a is
fully restored and Recovery is online. USB ACM enumerated briefly but the
receiver disconnected before a complete frame. Normal GPUEB runtime addresses
remain unmeasured. A second boot_a write requires fresh specific confirmation.

## Purpose and boundaries

Actual modified LK skips GPUEB loading in Recovery mode 2. The collector must
therefore enter Linux through normal LK boot, with its own initramfs PID 1,
then return to Recovery and restore boot_a. It collects FDT and boot logs,
not GPU registers. A successful host build is not a successful hardware boot.

`tools/matisse-ramcollector.py` reads a Recovery newc archive without extracting
its paths, validates the static AArch64 BusyBox executable, resolves module
symbol dependencies against an explicit allowlist, and builds a new boot-v4
image. The compressed kernel and signature bytes are retained exactly from
the already linked GPUEB entry probe. The retained signature is not re-signed
or authenticated. No Apple artifacts or third-party binaries enter git.

`tools/ramcollector/init` uses `rdinit=/matisse-collector/init` and a matching
`init=` fallback. It never invokes Android init. It mounts proc/sysfs/tmpfs/
configfs only, disables modprobe autoload, loads the explicit supplier list,
and creates a USB ACM gadget. It creates character devices explicitly because
the actual kernel has no devtmpfs. No block device nodes, block mounts, UFS/
MMC/GPU/GPUEB modules, mailbox messages, or GPU MMIO accesses are requested.
USB/clock/PMIC kernel drivers necessarily operate their own hardware.

The 17 allowed modules are watchdog, log_store, nvmem_mtk-devinfo, the two
MT6983 pinctrl modules, clk-mt6983/clk-common, mrdump/aee_aed (clock symbol
dependencies), regmap-spmi, mtk-pmic-wrap, mtk-spmi-pmic, spmi-mtk-pmif,
mt6363/mt6373 regulators, phy-mtk-xsphy and mtu3. The log_store module is needed
for `/proc/pl_lk`; no writes to that proc interface are issued. These are the
same module files already used by this Recovery. Their vendor vermagic string
differs from the running kernel banner; do not mistake host validation for
a fresh insmod test. No module was loaded in the current Recovery self-test.

DT suppliers identify USB0 `11201000.usb0`, PHY0, topckgen and mt6373_vusb.
Reference `xiaomi-rubens@270b84910b941bf75490fccdb5fb2b3021dd7cbf`
`drivers/usb/mtu3/mtu3.h` defines operation mode 3 as peripheral. The collector
uses that sysfs interface rather than loading the charger/Type-C stack.
This minimal closure has not yet been proven at cold normal-mode boot.

## Important ramdisk detail

Actual vendor_boot v4 has a 4-byte platform fragment `02 21 4c 18`, followed
by a separate Recovery-type legacy LZ4 fragment. Appending a gzip collector
to the 4-byte legacy prefix is unsafe: the kernel unlz4 parser would interpret
the gzip header as a compressed block length. The builder therefore emits
**legacy LZ4**, and verifies decompression with the exact 4-byte prefix prepended.
The source kernel `lib/decompress_unlz4.c` explicitly skips repeated legacy
magic. This is tested locally. Normal LK fragment selection is still unmeasured;
unique collector paths avoid clobbering a Recovery `/init` if also included.

## Build and validation

```sh
python3 tools/matisse-ramcollector.py \
  --recovery-cpio research/matisse/20261031-gpu/live-recovery.cpio \
  --template research/matisse/20261031-gpu/gpueb-handoff-probe.img \
  --out research/matisse/20261031-gpu/matisse-gpueb-ramcollector.img
python3 -m unittest discover -s tools/tests -p test_matisse_ramcollector.py -v
```

Artifact: 21,450,752 bytes, SHA256
`50813edab73c4ebcb4554cb41360457f180df1df593d0325ebc76fe64f2dee6d`.
Ramdisk: 1,867,289 bytes, 40 archive entries including 17 modules. Expanded
entry-probe/Linux Image remains 48,945,268 bytes, below the prior measured
`0x7c80000` bound. This is not a measurement of runtime RAM reservation safety.
The source probe has no XNU payload or UFS probe.

9 new host tests pass: bounded cpio/ELF/boot parsing, dependency denylist,
legacy-LZ4 prefix concatenation, immutable kernel/signature, receiver frame
length/hash/base64 limits and archive traversal/link rejection. Existing GPUEB
10 + entryprobe14 + Android readers7 tests also pass.

Recovery self-test only copied helpers to `/tmp/matisse-collector-selftest`
and executed `--snapshot-only`: syntax check PASS, 26 files packed from two
Recovery snapshots, checksummed frame decoded and validated on host. This
did not exercise PID1, module loading, USB role changes or ACM enumeration;
the frame crossed existing ADB, not ACM. It does not establish normal-mode
GPUEB loading, GPU_ID or GPU acceleration.

Ignored evidence: `research/matisse/20261031-gpu/collector-analysis/`, including
`final-verification.json`, `wire-selftest/`, `recovery-selftest.frame`, and build
manifest adjacent to the image. Do not commit these raw dumps or images.

## Reviewable hardware procedure — pending confirmation

Do not execute old trial runners. matisse does not support temporary
`fastboot boot`. The test requires a temporary **boot_a partition flash**:

1. Reconfirm Recovery matisse, active slot a, boot_a size 64 MiB and full
   boot_a SHA256 against the baseline below; revalidate image and backup.
2. Record a fresh dedicated restoration journal before the first write.
   Reboot bootloader; verify product/slot/partition size without recording
   the device serial in git. Never erase or switch slots.
3. Flash only the named collector into boot_a, boot normal once, and receive
   the immutable collection over the newly enumerated `/dev/cu.usbmodem*`.
   `tools/matisse-collector-receive.py --port <exact-port> --out <new-research-dir>`
   only reads serial data and validates it. It does not expose a command shell.
4. Return to bootloader (physical keys if needed), restore the **full original
   64 MiB** boot_a image, then reboot Recovery. Do not restore merely the short
   rebuilt boot prefix. Do not flash LK, vendor_boot, DTBO or userdata.
5. Independently read/hash all of restored boot_a from Recovery; mark the
   journal restored only on exact match. If enumeration fails, preserve the
   restoration duty; do not proceed with unrelated boot experiments.
6. Parse normal `/chosen/atag,boot`, GPUEB shared address/size and all DT
   reservations, check against XNU RAM `0x100000000..0x22e000000`, and inspect
   LK loader results. This must precede any mailbox/power implementation.

Verified full backup:
`backup/recovery-20261021/boot_a-live-20261021.img`, 67,108,864 bytes, SHA256
`2931647a56039722ea2585990b8ef3b1a2daf4c9b990231879f753049eaf86b1`.
A fresh read-only current boot_a hash still matches it. No restore is pending.

## First authorized trial result

User authorized the concrete image, one normal boot, full backup restoration
and return to Recovery, then explicitly requested writing from Recovery. The
initial fastboot getvar preflight timed out before any write; after USB replug,
`fastboot reboot recovery` succeeded. No fastboot flash was performed.

A new dedicated Recovery runner (not a historical run-ui script) hashed the
image in `/tmp`, wrote only its prefix into boot_a with dd+fsync, and hashed
the entire 64 MiB partition. Observed SHA256
`3b5ef7f319e3b9a56373381ae87b77aba47229e4cff74c33cb7aedbd44420c42`
exactly matches the collector plus original partition tail.
Normal reboot began at **2026-10-31 09:35:00 Asia/Shanghai**.

USB ACM appeared within seven seconds; receive failed with ENXIO (device not
configured). No complete collection was saved. This establishes transient
USB enumeration only; it does not establish a panic, watchdog reset, GPUEB
loader success, GPU_ID or acceleration. The original receiver cleanup also
raised ENXIO and masked the read exception; this is fixed with two regression
tests, bringing collector tests to 11 PASS. This host fix does not fix or
explain the device disconnect.

User entered Recovery with physical keys. The runner restored all 67,108,864
bytes of the original backup and verified full partition SHA256
`2931647a56039722ea2585990b8ef3b1a2daf4c9b990231879f753049eaf86b1`
at **09:36:10 Asia/Shanghai**. Independent post-check also matched. Runner
exit0; journal `restore_pending=false`, `collection_received=false`. Recovery
remains online. LK/vendor_boot/DTBO/userdata were not written.

Read-only pstore collection returned a 262132-byte console record with
corrupted text from older Recovery uptime around 863–953 seconds and an
earlier reboot,bootloader. It contains no usable collector trace and cannot
explain this trial. `/proc/last_kmsg` is absent (an exec-out error response is
not a log). Current pl_lk is a fresh mode2 Recovery log, not the normal boot.
Ignored artifacts are under `collector-trial-recovery-20261031/`, including
`journal.json`, `receive.txt` and `post-recovery/`. No restoration is pending.

Next work is local: retain partial receive bytes and arrange durable early
collector diagnostics, then review a new image before requesting another
partition-write authorization. Do not rerun this one-shot trial journal.
