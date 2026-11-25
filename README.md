# ios-sweetwhyred

Experimental Apple XNU bring-up on the Xiaomi Redmi Note 5 (whyred, Qualcomm SDM636 / Snapdragon 636). This branch targets whyred; inherited sweet drivers and device claims do not automatically apply to it.

## Current status — 2026-10-31

The handset boots XNU from the iOS 16 generation (xnu-8796), mounts the prepared iOS 16.5 APFS System volume from eMMC, starts Apple launchd and executes backboardd and SpringBoard. A stable graphical interface has not been demonstrated.

Confirmed on the handset:

- Gold CPU handoff, 16 KiB page tables, VM, IOKit, GIC virtual timer and BSD initialization.
- eMMC identification, valid primary GPT CRCs and bounded, read-only partition block devices.
- Read-only APFS root mounting from the existing System partition and execution of Apple userspace.
- launchd early boot completion, framebuffer/IOSurface service access by backboardd, and submitted display transactions.
- A framebuffer console on the 1080×2160 panel.

The current hardware-tested boot is v74 with System v70. Writable runtime state lives in a volatile RAMFS mounted at `/private/var`, with a 128 MiB file-data quota. This avoids embedding a large writable HFS image in the boot payload; contents disappear on reboot. Metadata, extended attributes and page-cache overhead consume additional RAM.

## Graphics candidate v75

Patch [0150](xnu/patches/0150-whyred-framebuffer-presentation.patch) is built and packaged for the next handset test. [Actions run 41227451892](https://github.com/timosid/ios-sweetwhyred/actions/runs/41227451892) succeeded on source commit `db0fa1d4d3b7748f091205e1cec166547a2418ab`.

The candidate:

- Retains queued IOSurface objects until delayed presentation finishes.
- Copies packed BGRA/RGBA pixels on the CPU, with clipping and buffer bounds checks.
- Scales the full logical 1125×2436 canvas to the actual 1080×2160 panel.
- Preserves UART after presentation and hides the framebuffer console only after pixels were copied.

The shipped graphics libraries contain a software-rendering fallback, confirmed by static inspection. That does not establish successful rendering of a complete SpringBoard scene on this handset, and this port has no GPU acceleration.

The [host check](tools/test-whyred-framebuffer.py) executes the actual kernel blitter. Its 275 cases cover pixel formats, scaling, offsets, padded rows, clipping, invalid buffers and the real panel dimensions. The packaged kernel also passed an instruction audit with no executable LSE or PAN instructions.

The next UART markers distinguish stages:

- `WHYRED FB: queued`: a display transaction was accepted.
- `WHYRED FB: no copied layer`: presentation had no supported layer to copy.
- `WHYRED FB: presented`: pixels were copied to the boot framebuffer mapping; counts and samples are included.

A `presented` message establishes a copy, not a correct or visible iOS interface. v75 has not yet been flashed or hardware-tested.

## Boot and storage

The whyred shim transfers execution to the verified Gold core, which enters XNU at EL1. XNU initializes VM, interrupts and platform services, discovers eMMC partitions, mounts APFS System, creates writable RAMFS state and starts `/sbin/launchd`.

Whyred uses the Qualcomm SDHCI MSM v5 controller at `0x0c0c4000`. The eMMC driver rejects media writes; APFS is read-only. The old inherited UFS root path is not used. Mockfs and the project's small diagnostic APFS root remain available for isolated tests. [APFS scope and checks](docs/whyred-apfs.md).

## Build and checks

[GitHub Actions](.github/workflows/xnu.yml) cross-compiles ARM64 on a macOS 15 Intel runner. Whyred patches live in [xnu/patches](xnu/patches/). Artifacts include the kernel, build log, source reports, host-check results and patched build tree.

The required checks cover the kernel build, framebuffer pixel copying, synthetic APFS images, RAMFS atomic writes and directory ABI, and a signed static diagnostic PID 1. CI success does not establish handset boot or graphical output.

## Limitations

This remains a bring-up project, not a usable phone OS. Only one Gold core (MPIDR `0x100`) is enabled. The core supports 16 KiB pages and lacks LSE atomics and PAN; builds avoid those instructions.

Storage currently retains a conservative identification clock after transfer-clock verification fails, so userspace loading can take several minutes. Real touchscreen/button input, GPU acceleration, radios, battery telemetry, suspend and full power management are not validated. Inherited sweet input pollers target different controllers and must not be enabled on whyred unchanged. Several security and platform services are bring-up stand-ins, and some unsupported launchd jobs are disabled.

Keep verified partition backups. Downloaded Apple userland, firmware, raw UART captures and device identifiers are not distributed in this repository or its CI artifacts.

## Credits

Apple's open-source XNU, [blacktop/darwin-xnu-build](https://github.com/blacktop/darwin-xnu-build), [HakiOS](https://github.com/oosexgang/hakios-xnu-kernel) APFS/RAMFS work, and published Qualcomm/Xiaomi kernel sources. Included third-party sources retain their licenses.
