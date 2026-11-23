# Galaxy S8 SM-G950F: initial bring-up assessment

## Status

This checkout supports only the Redmi Note 10 Pro (`sweet`, Qualcomm SM7150). The user confirmed `PRODUCT NAME: SM-G950F` in Download Mode, establishing the handset as a separate, unimplemented Exynos 8895 target—not the Qualcomm board used by SWEET.

The installed custom ROM label is reported as `hadesRom_Q_OneUI_v3.0-FUK2`. Hades settings report model strings `SM-N960N` and `SAOMC_SM-N960F_OXM_BTU_QQ_0027`, with `BTU/BTU/BTU`; these are ROM-provided values and conflict with the confirmed hardware. TWRP ADB reports device `dreamlte`, model Galaxy S8, bootloader `G950FXXUCDVG4`, carrier BTU, and verified-boot state `orange`. The user had earlier reported `G950FXXUCDUD1` from Odin, but that differs from the current TWRP bootloader value. A separate device identifier was included in chat and intentionally not recorded. No stock firmware package has been inspected.

No G950F firmware package has been inspected, no target code or image has been produced, and no commands have been run against the phone. Do not boot or flash the existing SWEET image on the S8.

## Existing public project

The separate [Floppikrob/ios-galaxy-s8 project](https://github.com/Floppikrob/ios-galaxy-s8) targets the same SM-G950F. Its [README](https://github.com/Floppikrob/ios-galaxy-s8/blob/main/README.md) reports an iOS lock-screen boot; its [progress log](https://github.com/Floppikrob/ios-galaxy-s8/blob/main/DREAMLTE_PROGRESS.md) records device observations and boot results, and the latest listed main commit claims additional UI milestones. These are the project's own reports, not independently verified here. A [GitHub Actions run](https://github.com/Floppikrob/ios-galaxy-s8/actions/runs/39506439642) succeeded, which verifies a build job, not a physical-device boot.

Its [installation guide](https://github.com/Floppikrob/ios-galaxy-s8/blob/main/docs/s8-install.md) requires an unlocked bootloader and TWRP, writes the BOOT partition, and erases USERDATA. It is not a safe temporary-boot path and should not be followed without backups and explicit acceptance of those consequences. The repository root listing did not include a LICENSE file; do not copy its S8-specific code into this checkout unless the author provides permission or an applicable license.

Separately, [MakrSas/LinuxS8](https://github.com/MakrSas/LinuxS8) documents a GPL-licensed Linux bring-up for `dreamlte` using uniLoader and mainline Linux. Its project documentation reports a real-device mainline-kernel boot, which is useful boot-chain/hardware prior art but is not an iOS port. Treat its device-write steps as destructive; this assessment does not run them.

## Why the existing image cannot be reused

- `tools/mkadt.py` encodes SWEET physical-memory ranges, interrupt-controller and timer addresses, Qualcomm CPU identifiers/topology, framebuffer placement, and the Qualcomm UFS controller.
- The XNU build adds a `SWEET` machine configuration and SWEET-specific platform, CPU, display, touch, and storage support.
- `shim/build.sh` expects the SWEET stock DTB and packages a boot image for the project's existing boot path.
- The README's temporary `fastboot boot` workflow is documented for the Xiaomi device. The S8 uses Samsung Download Mode; a compatible, non-destructive way to load an experimental image has not been established.

These are platform dependencies, not settings that can safely be changed by substituting a model name or device tree.

## Current development blockers

- The product name and current BOOT partition are confirmed, but no install image is available. Web lookups of the earlier reported firmware string on SamFW were blocked (HTTP 403); search engines did not provide verifiable results, and no firmware package was downloaded.
- The user has explicitly authorized replacing BOOT and erasing USERDATA, but not unlocking the bootloader. No phone partitions have been modified.
- TWRP ADB is reachable with Google Platform Tools 37.0.3 staged at `F:\AndroidTools\platform-tools`.
- Read-only partition map on this handset: BOOT is `/dev/block/platform/11120000.ufs/by-name/BOOT` -> `sda7` (40 MiB); USERDATA is `/dev/block/platform/11120000.ufs/by-name/USERDATA` -> `sda26` (55,249,448,960 bytes). The third-party install guide's `sda24` USERDATA path is wrong for this device. A validated 40 MiB copy of the current BOOT partition is kept locally at `F:\iOS Galaxy\backup\G950F-BOOT-before-ios.img` (ignored by Git).
- This workstation lacks `aarch64-linux-gnu-gcc`, `gh`, `fastboot`, and a WSL distribution. There is no G950F install image or iOS root image in this checkout. No target build or phone write operation has been attempted.
- The SWEET target conditionals are spread over 51 XNU patches. A G950F target needs a separate 4 KiB-page, Cortex-A53/Mongoose, GIC-400, Samsung S-Boot/boot-image and Exynos UFS bring-up; aliasing it to SWEET would use incompatible hardware assumptions.

## First engineering milestone

Before writing G950F register values or attempting a boot, collect and inspect the exact stock firmware for this handset, without modifying the phone:

1. Obtain the stock firmware package matching the confirmed SM-G950F and reported `G950FXXUCDUD1` build; verify model/region before use.
2. Extract its boot-chain artifacts and inspect the kernel, DTB/DTBO, memory map, CPU topology, interrupt controller, timer, and reserved regions.
3. Determine whether the bootloader accepts a temporary test image, and what image format and signing constraints apply. Do not use Odin or flash any partition as an exploratory step.
4. Only then design a separate Exynos target and a minimal diagnostic boot. Keep SWEET's known-good path unchanged and use read-only/reversible tests first.

After minimal kernel entry and diagnostics work, the port would still need board-specific storage, display, touch, power, and other drivers before the existing iOS userland could be evaluated. A bootable iOS system is not yet demonstrated or promised.
