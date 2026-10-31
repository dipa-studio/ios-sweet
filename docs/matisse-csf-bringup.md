# MT6983 CSF MCU boot probes (2322 / 2323)

2026-10-31. GPU2321 established actual GPUEB power ownership and Mali soft
reset on matisse. This next diagnostic installs MCU firmware mappings, powers
the first L2 group, enables AS0 and starts the MCU. The2322 hardware trial
timed out at MCU start;2323 is built but hardware-unverified. The original
2322 design follows; the final section describes its2323 successor. There
is no shader job, command queue, Vulkan or Metal path yet.

## Reference facts and firmware

The independently written portable code uses register/ABI facts from Linux
tag v6.12: drivers/gpu/drm/panthor/panthor_regs.h, panthor_fw.h, panthor_fw.c,
panthor_mmu.c and panthor_gpu.c; drivers/iommu/io-pgtable-arm.c was consulted
for AArch64 stage1 descriptor fields. These are source references, not code
copied into XNU. Panthor files declare GPL-2.0 OR MIT. The vendor register
headers were cross-checked against xiaomi-rubens commit
270b84910b941bf75490fccdb5fb2b3021dd7cbf and extracted device firmware.
Local reference copies stay under ignored research/.

Only the measured vendor_a mali_csffw.bin is accepted by the image builder:
258048 bytes, SHA256
de22d2fc06bc8a859968499a6e609c27fe838be062bf5c97d92ea9f904f7229a.
The proprietary blob is embedded in the local image and never committed.
Its header describes 7 ordinary and 3 protected sections. Protected sections
are skipped, so this probe cannot enter protected mode. The shared region
starts at MCU VA 0x04000000 and spans 0x94000 bytes.

## Memory ownership and translation

The shim owns a static 2 MiB, 4096-aligned BSS arena; it is not a GPUEB
reservation. The loader revalidates the firmware and canonical allocation
plan before writing. It creates 7 page-table pages and ordinary firmware
sections using 1228800 bytes total. Remaining arena bytes are not mappings.
It rejects overlap with firmware input, metadata, XNU RAM, live GPUEB shared
2 MiB and live extra firmware 20 MiB allocations, and rejects PA overflow.
GPUEB addresses are read each boot, not taken from the prior measurement.

The MCU uses independent 4 KiB AArch64 stage1 tables for a 32-bit VA space
(level1 root, level2 and level3 tables). CPU 16 KiB tables are not reused.
PTEs carry AF/nG/unprivileged access; write and execute permissions follow
firmware flags. All data mappings use memory attribute index0, NC policy
0x4c, and outer shareability. AS_TRANSCFG is 0x010005c6: 4 KiB mode6,
INA=55-32, NC page walks. The hardware's MMU_FEATURES must support these
VA/PA sizes. This deliberate 32-bit diagnostic configuration differs from
Panthor's usual full hardware VA width and remains hardware-unverified.
The measured LK enters with CPU MMU/caches disabled. A DSB publishes arena
writes before the MCU starts. The arena remains allocated through reset
and POWER_OFF; it is never reused for XNU.

The 2 MiB BSS exceeds ADR's +/-1 MiB reach. Boot/secondary stack and BSS
addresses therefore use ADRP+ADD, compatible with measured page-aligned LK
placement. The builder validates arena bounds, payload separation, original
Linux at +32 MiB, and the measured live-DTB load-window limit.

## Transaction and readiness

The optional platform callback runs only after the GPU2321 reset path has
acquired exactly one power reference. It requires both SPM MFG bits, exact
GPU_ID 0xa8620004, AS0 availability, MCU disabled and no protected mode.
AS0 must have no table and mode0 (legacy reset state) or mode1 (unmapped);
active/identity/unknown address modes are refused. It explicitly establishes
unmapped mode before installing a new table.

The transaction saves/masks GPU/JOB/MMU IRQ masks without touching the GIC,
powers L2 bit0 and polls readiness. Before updating AS0 it programs a locked
4 GiB VA region (LOCKADDR=31), issues LOCK, then FLUSH_MEM, and polls each
command's completion. It writes TRANSTAB/MEMATTR/TRANSCFG and UPDATE, clears
old AS0/global interrupt state, then writes MCU_CONTROL_AUTO=2. All waits
have a hardware-counter deadline of at most 1 second each and an independent
iteration cap, including a stopped-counter case. Total probe time is bounded
by the sum of these waits, not a single 1-second transaction deadline.

Firmware readiness requires a **fresh JOB global-interface raw IRQ bit31**
after MCU start, MCU status1, no GPU/MMU fault, and a valid runtime global
interface. A nonzero version already present in the blob is insufficient.
MMU upper16 request-completion bits are preserved, not classified as faults.
Input/output pages must fit the measured shared region; group count must be
1..31 and group stride/bounds must be valid. No global configuration or
doorbell request is sent in this first probe.

All paths after mask changes attempt MCU disable and CSF soft-reset0x101,
check fresh reset completion bit8, restore masks, then let GPUEB release its
single reference. Firmware-ready and reset/POWER_OFF outcomes are reported
separately. A failed reset is never reported as a successful full trial.

## Independent evidence

Kernel patch0120 identifies build2322. The shim reserves a128-byte ADT slot
for its88-byte CSF report (22 words). XNU records it as SWEETMRK320..330,
tagged2322; platform72-byte report remains300..308, also tagged2322.
Decode a fresh Recovery capture with:

```sh
python3 tools/matisse-gpu-report.py /absolute/path/after-marks.bin --build 0x2322
```

The decoder rejects missing, duplicate and mismatched records. It reports
firmware_ready_observed independently of cleanup_verified and requires
platform success, valid readiness and cleanup for csf_firmware_boot_verified.
Build2321 decoding remains supported and cannot report CSF boot success.

## Host validation and concrete artifact

38 targeted tests pass, including ASan/UBSan runs of the real portable
firmware loader, MMIO boot transaction, GPUEB transport and diagnostic-write
bounds. Separate sanitizer replay of the actual pinned blob confirms
7 sections/3 skipped/7 tables/1228800 bytes. A full local incremental XNU
build passed; no CI run was dispatched for this diagnostic. Initial image
link failed on ADR range, was corrected with ADRP+ADD, then the image passed
freestanding compilation, linking and component readback checks.

Kernel SHA256 f8a78e1868f75103352167290105814444ec685987e3faf248c5dbeec996fa47.
Image research/matisse/20261031-gpu/shim2322-final/matisse-shim-gpu2322.img,
26710016 bytes, SHA256
5ade1013c6cae1119d04af74db5a446c6e7401e682da6b74010bc4b4ad189e64.
Full expanded Image remains80402548 bytes, Linux fallback +33554432.
Manifest records shim arena offset483328, BSS end2580576, shim end2650112
and payload offset2650128. These are offsets, not observed runtime PAs.

## Device trial and recovery

At the2322 build handoff, no partition write or boot had happened. The
full64 MiB boot_a baseline was independently rehashed as
2931647a56039722ea2585990b8ef3b1a2daf4c9b990231879f753049eaf86b1.
Each concrete trial needs the specific boot_a-write confirmation required
by AGENTS.md. Completed trial results follow.
LK/vendor_boot/recovery/modem/persist/DTBO/GPT stay untouched.
Root uses ufsrw=0/rootrw=0; only established userdata-tail diagnostics write.

Automatic Recovery failed in2321 and remains unreliable. The embedded Linux
fallback only helps when LK actually selects Recovery. A trial must keep a
restoration journal, capture fresh logs, restore the full64 MiB original and
verify its hash. If Fastboot is reached, use tools/fbraw.py with one persistent
USB session to flash only the known20 MiB stock prefix and request Recovery;
then restore the full backup in Recovery. Do not use the official fastboot
client or repeatedly reopen a hung LK transport. Never finish with pending
restoration.

## Recovery fallback hardware result (2026-10-31)

The specifically authorized fallback trial of the final image5ade1013
completed. Recovery was newly observed26.53 seconds after reboot recovery.
Full boot_a readback after candidate write matched predicted partition hash
15f5c01989f8023b0e84219a2dafb036fce26b580fd744e66c4ceac060b189cd.
The original67108864-byte boot_a was restored and independently rehashed to
2931647a56039722ea2585990b8ef3b1a2daf4c9b990231879f753049eaf86b1.
Device remained matisse/slot_a/root Recovery. No Fastboot transport used.
Journal shim2322-trials/recovery-fallback/journal.json is complete with
restore_pending=false. Before/after persistent tail and marks are identical.

This verifies this image's Recovery entry, changed stack/BSS addressing and
embedded stock Linux bypass only. It does not execute the normal GPU/MCU
probe and does not establish automatic Recovery from an XNU boot. The normal
CSF trial was still pending at that milestone; its later result follows.


## Normal CSF2322 hardware result (2026-10-31)

The specifically authorized normal trial ran once. Fresh build0x2322 marks
contain72 records (previous capture build0x2321,count61); the console agrees
with sweettrial2322/gpu2322. Platform INIT0 and POWER_ON1 succeeded; SPM
changed3->7, GPU_ID was0xa8620004 and initial reset completion was0x100.
POWER_OFF returned0 and the single acquired reference was released.

CSF stopped at stage4/MCU with timeout-53. MMU_FEATURES was0x2830 (VA48/PA40),
L2_PRESENT/L2_READY were1, MCU_STATUS was1, JOB_RAW was0, MMU_RAW was0 and
AS fault status/address were0. No fresh global-interface interrupt was seen.
The timeout path did not sample shared runtime-interface fields, so their
zero report words are unobserved, not measured zero contents. Cleanup also
timed out (-53), reset raw was0x600 and reset_completed was0. Firmware-ready
and acceleration remain unproven. Aggregate platform stage8/error-53 reflects
the callback failure, not a failure of the earlier platform reset.

Normal boot enumerated Fastboot after approximately126 seconds. Host SIGINT
only entered the waiting runner's existing finally restoration; its journal
KeyboardInterrupt is not a device panic. One persistent fbraw session verified
matisse/slot_a/geometry, flashed the known20MiB stock prefix (OKAY) and issued
reboot-recovery (OKAY at03:08:13Z). Recovery restored the full67108864-byte
original boot_a; an independent read verified SHA256
2931647a56039722ea2585990b8ef3b1a2daf4c9b990231879f753049eaf86b1.
No user USB/key action was required. Runner63108 exited0, journal status is
complete-restored-Recovery and restore_pending=false. Device is root Recovery;
there is no pending runner/restoration. No second trial has run.

Evidence stays ignored under shim2322-trials/gpu-normal/: after-console.txt,
after-marks.bin, gpu-result.json, journal.json, recovery-dmesg.txt and
independent-post-restore.txt; gpu-normal-run.txt is alongside that directory.
Next work is static comparison of MCU translation, firmware permissions/cache,
IRQ behavior and cleanup with the actual vendor KMD. Discrepancies are
hypotheses until tested. Any successor hardware write needs its own specific
confirmation after a concrete image is built.

## Static audit and successor2323 (2026-10-31)

These are source/disassembly observations, not a demonstrated cause of the
2322 timeout. Actual vendor KMD SHA256
22b26f30a151e9d6791f959cc1f93d1e3f4d4c564537970dadefb0ec2d742a3b
was disassembled with NDK28.2 llvm-objdump; copies stay ignored.

- kbase_mmu_get_as_setup at0x47994 supplies MEMATTR0x00084c8d888d8f88,
  TRANSCFG6 and a masked table PA. kbase_mmu_hw_configure at0x45e50 adds
  WB/read-allocate walks0x42000000 and conditional outer-shareability.
  No INA bits were observed in that setup. This suggests a full-width root;
  it does not establish that reduced-width translation is unsupported.
- kbase_csf_firmware_init writes MCU_CONTROL2 at0x70020; trigger_reload
  does likewise at0x6e3dc. AUTO2 in2322 was therefore already correct.
- kbase_pm_enable_interrupts writes JOB mask0xffffffff at0x3a818. Panthor
  v6.12 also unmasks JOB before starting MCU;2322/2323 poll RAW with GPU,
  JOB and MMU masks0 and CPU DAIF masked. The effect of this difference on
  firmware remains untested. No GIC routing was changed.
- Panthor v6.12 uses hardware VA width (48 on this device), WB/RA walks,
  and honors cached firmware sections.2322 instead chose VA32/all-NC.
  The reference has a G610 model entry, not this G710, so it does not prove
  complete hardware support.

2323 removes those deliberate VA/cache deviations while retaining polled
RAW readiness. Independent4KiB stage1 tables now have a level0 root/VA48,
still mapping only ordinary32-bit firmware section addresses. Full48-bit
lock encodes47. TRANSCFG is0x420001c6 (INA7,mode6,WB/RA), not a verbatim
copy of vendor6. Cached mode1 sections use AttrIdx1/WB0x9f and SH_IS; other
modes use index0/NC0x4c and SH_OS, as in the Panthor mapping policy. CPU
caches remain disabled. Root/config readbacks must match before MCU start.
Pinned blob needs8 table pages/1232896B within the owned2MiB arena;7 ordinary
sections/3 protected skipped are unchanged. These changes are untested on
hardware and must not be described as a proven fix.

The report expands88->128 bytes, appending to the original22 words: sample
flags, GPU RAW, AS status, TRANSCFG, root PA, MCU disable status/error and
pre-start shared version. Post-start shared fields are sampled even on
timeout, before reset. Only a fresh global RAW interrupt and valid interface
can assert readiness; a preloaded version remains insufficient. MCU disable
failure remains a cleanup failure even if the next reset succeeds. No new
hard reset, queue or doorbell was added.

Kernel patch0121 changes build2323 and records16 CSF marks320..335. Decoder
accepts2321/2322/2323, exposes initial_power_reset_observed independently of
aggregate power_reset_verified, and labels whether the runtime interface
was sampled. Old2322 timeout zeros remain unobserved.

32 targeted tests PASS, including ASan/UBSan firmware/memory/boot harnesses,
full128-byte ADT publication and old/new evidence decoder regressions. Real
pinned blob sanitizer replay PASS:7 sections/3 protected/8 tables/1232896B.
Local kernel build exited0 (no CI run/push); kernel16724248B SHA256
77c7248c13d55fe4d2db365bc9cf2d728849e51eb371abfbc5b8c4304a5442f8.
Freestanding compile/link, source-manifest equality and image component
readback passed. Image:
research/matisse/20261031-gpu/shim2323-ready/matisse-shim-gpu2323.img
26710016B SHA256
23b2c8dc56f9a7b72a585efa9ebcf889d2979e1dca6fb58fe53dbf81eafb3137.
Expanded80402548B; stock Linux+32MiB, ramdisk/signature bytes and frozen2313
display/UFS/board objects retain2322 component hashes. Signature bytes are
preserved, not authenticated by this builder.

At the2323 build handoff, no hardware write/reboot had occurred. Recovery identity matisse/_a/root
was read again without writes. Readonly runner preflight also verified the
complete64MiB baseline SHA2562931647a56039722ea2585990b8ef3b1a2daf4c9b990231879f753049eaf86b1.
Prepared ignored shim2323-trials/run-once.py has run only preflight.
First specific confirmation must cover one
2323 Recovery-fallback trial and full baseline restore/hash. Only after it
passes should a separately confirmed normal MCU trial run. Automatic Recovery
from normal XNU remains unreliable; retain the tested persistent fbraw restore.


## Recovery fallback2323 hardware result (2026-10-31)

The specifically authorized fallback trial of image23b2c8dc ran once.
Runner85408 exited0; a new Recovery boot was observed26.53s after adb reboot
recovery. Full candidate partition readback matched predicted SHA256
bf7caf4432b7717002cd7dc9168914662820327b30f499454cdc6acc58c7bac7
(candidate prefix plus unchanged original tail). No Fastboot or user USB/key
action was needed. Recovery dmesg889488B was saved.

The full67108864-byte original boot_a was restored, then independently
read and verified SHA256
2931647a56039722ea2585990b8ef3b1a2daf4c9b990231879f753049eaf86b1.
Independent identity/geometry confirmed matisse/slot_a/root Recovery.
Journal shim2323-trials/recovery-fallback/journal.json is
complete-restored-Recovery, restore_pending=false. No runner/restoration
remains active. Evidence stays ignored in that directory and the sibling
recovery-fallback-run.txt. Before/after4198400B diagnostic tails and4096B
marks are byte-identical, as expected for bypass; old console/marks must not
be mistaken for fresh2323 MCU execution.

This verifies Recovery entry/BSS and embedded stock Linux fallback only.
The next normal2323 trial needs separate specific approval for the same
image: write boot_a from Recovery, boot normal, capture fresh2323 CSF marks
320..335 and console, then restore the full baseline/hash. Automatic Recovery
from normal XNU remains unreliable. No firmware-ready or acceleration claim.
No build, CI run or source-code modification was needed for this fallback.
