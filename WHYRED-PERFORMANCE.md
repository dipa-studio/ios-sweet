# Whyred boot performance candidate

This development candidate targets the existing read-only eMMC root path.
It has not established a hardware speedup or a rendered SpringBoard scene.

## Storage

- `whyred-emmc-fast=1` keeps the established clock through initialization and
  GPT discovery, then tries the dedicated SDCC1 GCC RCG2 with the existing
  19.2 MHz XO parent. It bypasses the ordinary SDHCI divider, preserves other
  RCG fields and leaves PLLs, voltage rails, card timing and bus width alone.
  Register/update/clock waits are bounded. The original clock configuration
  is saved for rollback.
- Before publishing the device, 32 sectors of the selected root partition
  are compared byte for byte with CMD17 reads in the baseline configuration.
  The clock is retained only after that comparison. Failed recovery or a
  failed baseline comparison prevents block-device publication.
- `whyred-emmc-multi=1` enables batches of up to 32 sectors through eMMC
  CMD23 plus CMD18 only after comparison with the baseline bytes. Both card
  and host get an explicit block count; the reliable-write bit is never set.
  Failed batches are rejected, the read stream is stopped and checked with
  CMD13, the new modes are disabled, and the full batch is reread with CMD17.
  Unrecoverable state causes further I/O to fail.
- `whyred-emmc-perf=1` prints GCC/host snapshots and at most 64 aggregated
  I/O summaries per boot: bytes, requests, CMD17/CMD18 counts, active I/O time,
  elapsed time, errors and fallbacks. The old printed 200 kHz value was a
  divider calculation, not a measured card clock.

FWRITE, block writes and writable-media ioctls remain rejected. No media-write
command, filesystem write support, HS200/HS400 or additional CPU is introduced.

Register references are Xiaomi's exact whyred source branch at commit
`efbbb9cce47475c49f28d227b2a52eca6f0d02a7`: `drivers/clk/qcom/gcc-sdm660.c`,
`drivers/clk/qcom/clk-rcg2.c`, `drivers/mmc/host/sdhci-msm.c` and
`arch/arm/boot/dts/qcom/sdm660_whyred.dtsi`.

## Logs and splash

`whyred-quiet=1` keeps actual daemon execs and AKS errors visible. Repeated
successful AKS calls and xpcproxy execs log the first four observations and
then exponentially spaced samples. Crash diagnostics remain available.

`whyred-splash=1` displays the supplied `assets/meimei.jpg` at the early XNU
framebuffer handoff for three counter-timed seconds, clears it, and resumes
the existing console. It uses the known 1080x2160 framebuffer with no crop.
The JPEG is decoded during the build; a bounded RGB565 array is embedded in
the kernel. The image adds 4,665,600 bytes of pixel data to the kernel and the
intentional pause adds three seconds to startup. The packager must recheck
the accepted ramdisk size limit.

macOS uses its built-in sips decoder and the stdlib BMP converter. The input
JPEG hash is pinned in the workflow. Local development can use Pillow for
conversion. Generated image headers and raw diagnostic captures need not be
committed.

Host checks execute the actual clock, multi-read, recovery and BSD strategy
functions with modeled registers, plus the actual splash renderer and timer
predicate. They exercise failure/rollback, byte order, ranges, residuals and
guarded buffers. They cannot establish SDCC timing, physical scanout, or the
reason for the observed pkd SIGABRT loop; `sweetscan=pkd` remains the targeted
runtime diagnostic for that separate failure.
