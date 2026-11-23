# Galaxy S8 SM-G950F: initial bring-up assessment

## Status

This checkout supports only the Redmi Note 10 Pro (`sweet`, Qualcomm SM7150). The Galaxy S8 SM-G950F is a separate, unimplemented target. The reported model number identifies the Exynos 8895 variant, not the Qualcomm board used by SWEET.

The user reports the Odin firmware/build string `G950FXXUCDUD1` and installed custom ROM label `hadesRom_Q_OneUI_v3.0-FUK2`. The Hades ROM settings report `SM-N960N`, which may be spoofed. These details have not been independently verified against a stock firmware package; the custom-ROM label is not sufficient to identify the stock firmware/CSC.

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

- The CSC/region and matching stock firmware package for this handset are unknown, so there is no Samsung boot image or DTB to inspect yet.
- The Windows environment currently has Python and Git, but no `aarch64-linux-gnu-gcc`, `gh`, `adb`, or `fastboot`. No target kernel build or phone communication was attempted.
- The SWEET target conditionals are spread over 51 XNU patches. A G950F target needs a separate 4 KiB-page, Cortex-A53/Mongoose, GIC-400, Samsung S-Boot/boot-image and Exynos UFS bring-up; aliasing it to SWEET would use incompatible hardware assumptions.

## First engineering milestone

Before writing G950F register values or attempting a boot, collect and inspect the exact stock firmware for this handset, without modifying the phone:

1. Establish the installed software/build and bootloader unlock state from device information. Do not initiate an unlock; it can erase user data.
2. Obtain the matching stock boot-chain artifacts and extract the kernel, DTB/DTBO, memory map, CPU topology, interrupt controller, timer, and reserved regions.
3. Determine whether the bootloader accepts a temporary test image, and what image format and signing constraints apply. Do not use Odin or flash any partition as an exploratory step.
4. Only then design a separate Exynos target and a minimal diagnostic boot. Keep SWEET's known-good path unchanged and use read-only/reversible tests first.

After minimal kernel entry and diagnostics work, the port would still need board-specific storage, display, touch, power, and other drivers before the existing iOS userland could be evaluated. A bootable iOS system is not yet demonstrated or promised.
