# ios-unsweet: Galaxy A5 2016 (SM-A510F, Exynos 7580) port

This branch is the start of porting ios-sweet to the **Samsung Galaxy A5 2016**
(`SM-A510F`, codename `a5xelte`, Exynos 7580, 8× Cortex-A53, 2 GB RAM).

Nothing here boots iOS yet. Step one is a **feasibility probe**: a tiny 64-bit
program packed as a Samsung recovery image. It runs on the phone, checks the
hardware facts that decide whether the port can work, and shows the answers as
rows of bits on the screen.

## What is already known

| Question | Answer | Source |
|---|---|---|
| Can S-Boot start 64-bit code? | Very likely yes. LineageOS ships an arm64 kernel for a5xelte | LineageOS wiki, `Exynos7580/android_device_samsung_exynos7580-common` |
| Interrupt controller | GIC-400 (GICv2) at `0x10C00000`. sweet has GICv3 only | `exynos7580.dtsi` |
| Display | DECON at `0x14830000`, S6E3FA3 1080×1920 AMOLED, MIPI **command** mode | `exynos7580*.dtsi` |
| Firmware calls | PSCI over `smc` (CPU_ON `0xC4000003`) | `exynos7580.dtsi` |
| RAM | 2 GB at `0x40000000` | `exynos7580-reserve-2000MB-Ax.dtsi` |
| Storage | eMMC (sweet has a UFS driver only) | |
| **16 KB pages** | **Not supported by Cortex-A53** (4 KB and 64 KB only). XNU/iOS on arm64 uses 16 KB pages | ARM Cortex-A53 TRM. Probe row 6 confirms |
| **LSE atomics** (ARMv8.1) | **Not on Cortex-A53**. iOS 16 code built for A11 may use them | Probe row 5 confirms |

The last two are the big open risks. They are not dead ends, because XNU has
4 KB page-table support (used for Rosetta) and atomics can be emulated, but
they make this port much harder than sweet's.

## Getting the probe

The build runs on GitHub Actions (`.github/workflows/a510f-probe.yml`) for every
push to the `a510f` branch. Open **Actions → a510f-probe → latest run →
Artifacts → a510f-probe**. The zip contains `a510f-probe-recovery.tar`.

## Flashing (Windows, Odin)

The probe goes into the **recovery** partition, so Android keeps working.
Flashing any unofficial image **permanently trips Knox** (Samsung Pay and
Secure Folder stop working, warranty void).

1. Settings → About phone → Software info → tap *Build number* 7×.
   Developer options → turn on **OEM unlock**.
2. Install Samsung USB drivers and Odin (3.13 or similar).
3. Power off. Hold **Vol Down + Home + Power**, then press Vol Up to confirm
   download mode. Connect USB.
4. In Odin: **Options → untick Auto Reboot**. Put `a510f-probe-recovery.tar`
   in **AP**. Press Start and wait for `PASS`.
5. **Unplug the USB cable** (with the charger in, power-off may not cut power).
6. Leave download mode: hold **Vol Down + Power** until the screen goes black,
   then *immediately* switch to **Vol Up + Home + Power** and hold until
   the Samsung logo shows. This boots recovery, which is now the probe.
   If Android boots instead, stock Android will put back the stock recovery
   and you need to flash again.

To undo: flash TWRP or the stock firmware the same way.

## Reading the result

After about a second the screen should show **13 rows**. Each row has a coloured
label on the left and 32 cells (bit 31 first, grouped in fours): white = 1,
dark = 0. **Take a photo and send it over.** Rows, top to bottom:

| # | Label | Value | What we hope to see |
|---|---|---|---|
| 0 | green | all ones | all white: the probe runs in 64-bit mode |
| 1 | red | exception level | `1` (EL1) or `2` (EL2) |
| 2 | orange | PSCI version | `0x00010000` (1.0) or `0x00000002` (0.2); `0xEEEE…` = SMC faulted |
| 3 | yellow | CPU_ON result | `0` = second core started |
| 4 | lime | watchdog core report | `0xC0DE000x` |
| 5 | cyan | `ID_AA64ISAR0_EL1` | bits 23:20 = atomics (A53: 0) |
| 6 | light blue | `ID_AA64MMFR0_EL1` | bits 23:20 = 16 KB pages (A53: 0) |
| 7 | blue | `MIDR_EL1` | `0x410FD03x` (Cortex-A53) |
| 8 | purple | exceptions | count<<24, class<<16, vector |
| 9 | magenta | load address | where S-Boot put us |
| 10 | pink | DTB address | x0 at entry |
| 11 | grey | framebuffer address | DECON window buffer |
| 12 | white | display state | window<<28, pixel format<<20, TRIGCON |

**The phone then powers itself off.** How long that takes is the backup signal
if the screen shows nothing:

| What happens | Meaning |
|---|---|
| Rows appear, off after ~60 s | Full success |
| Logo stays, off after ~15 s | 64-bit code ran, but no framebuffer was found |
| Logo stays, off after ~75 s | Code ran and the second core started, but the main core hung (likely on the display registers) |
| Logo stays forever | The probe did not run, or hung before starting the second core. Hold Vol Down + Power for 7 s to reboot |

## Layout

- `probe/`: probe source (`start.S` entry and exception vectors, `probe.c`).
- `tools/dtbhtool/`: Samsung `dt.img` and boot image packer from LineageOS
  `android_hardware_samsung` (lineage-15.1, Apache-2.0), plus the Exynos 7580
  `samsung_dtbh.h` from `Exynos7580/android_device_samsung_exynos7580-common`.
- `build.sh`: fetches the a5xelte device trees (LineageOS
  `android_kernel_samsung_exynos7580-common`, pinned commit), builds
  everything and packs `recovery.img` and the Odin tar.
