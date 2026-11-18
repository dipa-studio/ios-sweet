# ios-angelican

**Experimental iOS 16 port for the Xiaomi Redmi 9C NFC.**

This project aims to port Apple's open-source XNU kernel (`xnu-8796`, the iOS 16 generation) to the Xiaomi Redmi 9C NFC (`angelican`, MediaTek MT6765G / Helio G35).

The long-term goal is to run the **unmodified iOS 16.7.16 (20H392) userland of the iPhone X** on the device, including `launchd`, system daemons, `backboardd`, SpringBoard, and stock applications.

The project is currently in its early hardware bring-up stage. A custom ARM64 boot shim successfully executes on the actual device, initializes a framebuffer console, communicates with the MediaTek PMIC, services the hardware watchdog, and transitions execution from EL2 to EL1.

**XNU has not been booted yet. No iOS userland or graphical interface is running.**

> Experimental hardware bring-up. This is not a usable phone OS. The project is under active development, and many hardware components and kernel subsystems still need to be implemented.

## What works

| Area | State |
| --- | --- |
| Boot | Stock Xiaomi bootloader → custom ARM64 boot shim. Successfully boots on the actual device. |
| CPU | ARM64 execution on the primary Cortex-A53 core. Successfully transitioned from EL2 to EL1 using `eret`. |
| Memory | 512 MiB physical RAM confirmed from the stock device tree (`0x40000000–0x60000000`). Memory allocator and MMU not implemented yet. |
| Display | Direct framebuffer console works using the bootloader-provided framebuffer at `0x7EC50000` (720×1600, 32 bpp). |
| Timer | ARM generic timer counter accessible. DTB reports a frequency of 13 MHz. |
| Watchdog | MediaTek TOPRGU watchdog identified and successfully serviced. Periodic refresh prevents watchdog resets. |
| Power button | Physical power-key detection through MT6765 PWRAP and MT6357 PMIC works. Pressing the button triggers a software reset. |
| Device tree | Stock device tree inspected. RAM, reserved-memory declarations, GICv3, timer, watchdog, and PWRAP addresses identified. |
| GIC | GICv3 identified in the device tree. Interrupt controller initialization not implemented yet. |
| Storage | Not implemented. |
| iOS kernel (XNU) | Not booted. |
| iOS userland | Not implemented. |
| Display stack | Only the low-level framebuffer console works. No IOSurface or IOMobileFramebuffer implementation yet. |
| GUI | Not implemented. |
| Touch | Not implemented. |
| Buttons | Power button works as a hardware input to the shim. Volume buttons not implemented. |
| Battery | Not implemented. |
| Device identity | Targeting iPhone X (`iPhone10,3` / `D22AP`). Not implemented yet. |
| Activation | Not implemented yet. |

## What does not work (yet)

- **No XNU boot:** the current boot shim does not load or execute the XNU kernel.
- **No MMU setup:** EL1 currently runs with the MMU disabled. Page tables and memory management still need to be implemented.
- **No secondary cores:** only the primary core is currently used. PSCI-based CPU startup has not been implemented.
- **No GIC initialization:** the GICv3 hardware has been identified, but interrupt handling is not implemented.
- **No storage driver:** UFS support and an iOS root filesystem are not implemented.
- **No iOS userland:** `launchd`, system daemons, SpringBoard, and applications have not been started.
- **No GPU:** graphics acceleration is not implemented.
- **No touchscreen:** the touchscreen controller and input stack have not been brought up.
- **No Wi-Fi, Bluetooth, cellular, audio, camera, sensors, GPS, or SEP / Face ID.**

## How it boots

The current boot flow is:

```text
Xiaomi bootloader
    |
    v
Custom ARM64 boot shim
    |
    +-- Capture bootloader handoff state
    |
    +-- Initialize framebuffer console
    |
    +-- Service MediaTek TOPRGU watchdog
    |
    +-- Access MT6357 PMIC through MT6765 PWRAP
    |
    +-- Detect physical power button
    |
    +-- Configure EL1 stack and exception vectors
    |
    +-- Transition from EL2 to EL1 using eret
    |
    v
EL1 diagnostic loop
```

The next stage is to establish a usable EL1 execution environment, including physical memory management, page tables, MMIO mappings, and interrupt handling.

The intended future boot flow is:

```text
Xiaomi bootloader
    |
    v
ARM64 boot shim
    |
    +-- Initialize CPU and memory
    |
    +-- Set up MMU and exception handling
    |
    +-- Initialize required hardware
    |
    +-- Load XNU kernel and Apple Device Tree
    |
    v
XNU
    |
    +-- Platform initialization
    |
    +-- Memory and CPU management
    |
    +-- Device drivers
    |
    +-- UFS storage
    |
    v
iOS root filesystem
    |
    v
launchd
    |
    v
System daemons
    |
    v
backboardd and SpringBoard
```

This is the intended architecture, not the current implementation.

## Development

### Requirements

The current shim development environment uses:

- Linux or WSL2.
- AArch64 cross-compilation toolchain (`aarch64-linux-gnu-gcc` and binutils).
- Git.
- Device access for testing on the Redmi 9C NFC.
- A working stock Android boot image and device tree for hardware reference.

### Current development milestone

The current milestone is building a reliable ARM64 execution environment for the MT6765 platform.

The following components have already been tested on the physical device:

1. ARM64 boot shim entry point.
2. Bootloader handoff register capture.
3. Direct framebuffer console.
4. TOPRGU watchdog refresh.
5. MT6765 PWRAP communication.
6. MT6357 power-key detection.
7. Software reset through the MediaTek watchdog.
8. EL2-to-EL1 transition.

### Next steps

The planned development order is:

1. **Physical memory management:** establish a safe memory map and reserve memory used by the shim, stack, device tree, and framebuffer.
2. **EL1 MMU:** implement 4 KiB translation tables and identity-map the necessary RAM and MMIO regions.
3. **Exception handling:** establish reliable exception vectors and exception reporting.
4. **GICv3:** initialize the distributor and redistributors and implement interrupt handling.
5. **SMP:** investigate PSCI and bring up the secondary Cortex-A53 cores.
6. **Platform support:** implement the hardware interfaces required by XNU.
7. **XNU boot:** adapt the kernel configuration and boot protocol for the MT6765 platform.
8. **Storage:** implement UFS support and prepare an iOS-compatible root filesystem.
9. **iOS userland:** bring up the iPhone X iOS 16.7.