# MT6983 CSF MCU boot probes (2322 / 2323 / 2324 / 2325)

2026-10-31. GPU2321 established actual GPUEB power ownership and Mali soft
reset on matisse. These diagnostics install MCU firmware mappings, power
the first L2 group, enable AS0 and start the MCU. Trials2322,2323 and2325
timed out at MCU start;2324 was rejected by a pre-MCU mask gate. All trials
were fully restored.2325 measured GPU/JOB/MMU masks and passed its revised
gate, but still produced no fresh global-interface IRQ or shared version.
Firmware readiness remains unproven. The original2322 design follows, then
the measured results and successive2323/2324/2325 changes. There is no shader
job, command queue, Vulkan or Metal path yet.

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


## Normal2323 hardware result (2026-10-31)

The specifically authorized normal2323 trial executed once. Runner32766
exited0; fresh marks build2323/count77 replaced2322/count72, and18657-byte
console agrees with gpu2323/sweettrial2323. Platform INIT0/ON1/OFF0, SPM3->7,
GPU_ID0xa8620004 and initial reset completion0x100 repeated successfully;
the single power reference was released. Aggregate failure is the CSF
callback, not the initial reset.

MCU again timed out at stage4/error-53, status1, JOB_RAW0, MMU_RAW0,
L2_READY1, AS status/fault/address0. Configuration readback0x420001c6 and
rootPA0x40076000 matched. sample_flags3 now proves shared sampling occurred:
version before/after0, features0, input0x04002000, output0x04003000,
groups8 and stride0xa0. The same metadata exist in the firmware blob; they
do not prove MCU execution. No fresh global readiness IRQ or version was
published. GPU_RAW0x600, disable_status1/disable_error-53, cleanup_error-53,
reset_raw0x600/reset_completed0. Firmware-ready remains false.

Fastboot enumerated86.57s after normal reboot. The host detected enumeration
without opening the transport and entered the existing restoration path.
One persistent fbraw session verified identity/slot/geometry, restored the
stock20MiB prefix with OKAY and requested Recovery with OKAY. Recovery
restored the full67108864-byte original boot_a; independent identity and
full SHA256 matched
2931647a56039722ea2585990b8ef3b1a2daf4c9b990231879f753049eaf86b1.
No user keys/unplug or host SIGINT was needed. Journal status is
complete-restored-Recovery, restore_pending=false; no active runner remains.
This is host-managed restoration, not autonomous Recovery from XNU.

Evidence stays ignored under shim2323-trials/gpu-normal/ and sibling
gpu-normal-run.txt. No second trial, new image, CI run or source change.
The48-bit/cache change alone did not establish readiness. Further static
work must examine MCU startup prerequisites/internal event delivery and
G710 vendor initialization without claiming a diagnosed root cause.


## Static firmware startup audit and successor2324 (2026-10-31)

The exact pinned258048-byte firmware above has initial MSP0x02040000 and
Thumb reset entry0x010018ed. The code section begins at file0xe94 / MCU
VA0x01000000; reset entry file offset is0x2780. Capstone5.0.7 using
THUMB|MCLASS decodes the Cortex-M system instructions that plain THUMB
stopped on. Ignored startup-detail.txt records the disassembly.

Observed instruction locations in the blob:

- Reset startup0x010018ec, MPU configuration0x01003126 and main startup
  0x01002aec.
- Loop0x01002ee4..0x01002ef2 reads TILER_PWRTRANS at MCU-view
  0x40000214/0x40000210 and TILER_PRESENT at0x40000114/0x40000110, waiting
  until their intersection is zero. It then writes TILER_PWRON at
  0x40000190/0x40000194 (R8 is0x40000010, so operand offsets180/184
  resolve to190/194). These are GPU registers viewed through the MCU
  aperture; do not interpret the loop as waiting on shader transition bits.
- At0x01003012 startup publishes version0x01010000 to shared VA0x04000000.
- At0x0100301c it writes0x80000000 to internal MCU-view0x40001000, issuing
  the initial global-interface interrupt; startup WFI is0x01003032.

An ignored Unicorn2.1.4 Cortex-M7 replay loads ordinary firmware sections
with a simplified synthetic MMIO model. Baseline reaches WFI in986
instructions, publishes0x01010000 and writes the first IRQ. Injecting
present1/transition1 hits a500000-instruction cap in that tiler-transition
loop with version0. Clearing the injected transition after4 reads reaches
WFI in1004 instructions. These results establish a startup dependency in
this synthetic model, not actual GPU execution or the location of2323's
stall. Real2323 tiler present/transition values were not captured.
Optional trace-buffer pointers default0 and startup handles their absence;
this audit does not show that skipped trace/config entries alone prevent
initial version publication. Replay source/results remain ignored under
research/matisse/20261031-gpu/firmware-static/.

Local vendor disassembly kbase_pm_enable_interrupts0x3a748 writes GPU
CLEAR/MASK0x80503, JOB CLEAR/MASK0xffffffff and MMU CLEAR0xffffffff/
MASK0xffff. Linux v6.12 Panthor also enables JOB interrupts before MCU
startup.2323 instead kept all three internal masks zero. GPU_RAW0x600 in
2323 denotes power-change bits, not GPU fault bits by itself. AUTO2 was
already correct. Vendor coherency/default mode31 and all G710 quirks are
not fully reproduced; no speculative quirk-register writes were added.

2324 enables GPU0x80503/JOB0xffffffff/MMU0xffff immediately before MCU AUTO,
clears the selected GPU sources and verifies all three mask readbacks. A
mismatch aborts before MCU start. The earlier AS0/global clears are kept;
CPU DAIF remains masked, GIC routing is untouched and RAW is still polled.
Cleanup restores the saved masks as before. The effect on actual firmware
startup is an untested hardware hypothesis. Translation, memory attributes,
firmware mappings and shader-power handling retain2323 behavior.

The report remains128 bytes. Offset124, reserved-zero in2323, records JOB
INT_MASK readback in2324. Kernel patch0122 bumps the build to2324 and keeps
CSF marks320..335. Decoder supports2321/2322/2323/2324, preserves2323's
reserved-zero validation, and requires2324 JOB mask0xffffffff in addition
to a fresh IRQ, valid interface and verified cleanup for aggregate success.

## Host validation and concrete2324 artifact

29 targeted tests PASS, including sanitizer firmware/memory/boot harnesses,
mask readback rejection before MCU start, restoration of original masks,
128-byte ADT publication and old/new evidence decoder cases. Separate actual
pinned-blob ASan/UBSan memory replay PASS:7 ordinary sections,3 protected
skipped,8 tables,1232896 arena bytes and606208 shared bytes.

Local full incremental kernel build session29800 exited0, no CI run/push.
Kernel16724248B SHA256
fe02cab05b52f75fa08f93098e2093dd9a1e9f3df16aab9c7091da840daa90cf.
Image builder session7673 exited0. Image:
research/matisse/20261031-gpu/shim2324-ready/matisse-shim-gpu2324.img
26710016B SHA256
b8214a7e5166f396db9b6e7ac42331c6c592662473347288b32e6ab5679506f1.
Predicted full boot_a candidate partition hash (candidate prefix plus
unchanged baseline tail):
8d7de4d7f5cac9a6b73f50df7f3e8da23a9bc163e9a0db34bd25bf5bbbf0b8f1.

Independent verification passed source-manifest hashes, embedded payload/
ADT, kernel build source, readonly cmdline, unchanged Linux fallback and
frozen board/UFS/display objects, and the completed2323 restoration journal.
Expanded size80402548B, arena offset483328, BSS end2580608, shim end2650112,
payload offset2650128; these are offsets, not hardware PAs. Linux+32MiB,
ramdisk and signature bytes remain unchanged; signature retained, not
authenticated. rootrw=0/ufsrw=0. Local proprietary inputs stay ignored.

No2324 device trial or reboot has occurred. Latest hardware evidence is
still the2323 timeout and complete full64MiB restoration. The next hardware
step requires specific approval for one Recovery-fallback boot_a write of
this concrete image and full baseline restoration/hash. A normal MCU trial
requires separate approval after that SAME-image fallback passes. Automatic
Recovery from normal XNU remains unreliable; preserve the persistent fbraw
stock-prefix recovery path. No firmware-ready or acceleration claim.


The prepared ignored shim2324-trials/run-once.py pins this exact candidate
hash and predicted full-partition hash. Its readonly preflight exited0:
Recovery identity/slot/root and geometry matched, local candidate/backup
hashes matched, and the live full64MiB boot_a was rehashed to baseline
2931647a56039722ea2585990b8ef3b1a2daf4c9b990231879f753049eaf86b1.
Final29-test rerun PASS (2.563s); git diff --check PASS. Preflight does not
write a partition or reboot. No2324 trial journal or pending restoration.


## Recovery fallback2324 hardware result (2026-10-31)

The specifically approved fallback trial of imageb8214a7e ran once.
Runner83683 exited0. A fresh Recovery boot was observed26.56 seconds after
adb reboot recovery. Full candidate boot_a readback matched prediction
8d7de4d7f5cac9a6b73f50df7f3e8da23a9bc163e9a0db34bd25bf5bbbf0b8f1.
No Fastboot, user USB/key action or host SIGINT was needed. Fresh Recovery
dmesg842253B was captured. Full67108864-byte original boot_a was restored;
an independent read again verified
2931647a56039722ea2585990b8ef3b1a2daf4c9b990231879f753049eaf86b1.
Independent identity/geometry confirmed matisse/slot_a/root Recovery.

Ignored shim2324-trials/recovery-fallback/journal.json is
complete-restored-Recovery, restore_pending=false. No active trial/restore
runner remains. Independent-post-restore.txt and recovery-dmesg.txt are
alongside the captures; recovery-fallback-run.txt is in the parent directory.
Before/after4198400B tails and4096B marks are byte-identical as expected for
bypass. Historical2323 console/marks are not fresh2324 execution evidence.

This verifies2324 Recovery entry/BSS and embedded original Linux fallback
only. Normal MCU execution, firmware readiness, acceleration and automatic
Recovery from normal XNU remain unverified. The next step needs separate
specific approval for ONE normal2324 MCU trial using this same image,
Recovery boot_a write -> normal reboot -> fresh2324 marks320..335/console
-> full64MiB baseline restoration/hash. Keep the tested one-session fbraw
stock-prefix restore available if Fastboot appears. No new build,CI run,
push or source-code modification was needed for this fallback.


## Normal2324 hardware result (2026-10-31)

The specifically approved normal2324 trial ran once; runner21671 exited0.
Fresh build2324/count77 marks replaced2323/count77, and18657-byte console
agrees with gpu2324/sweettrial2324. Platform INIT0/ON1/OFF0,SPM3->7,
GPU_ID0xa8620004 and initial reset completion0x100 repeated successfully;
the acquired power reference was released.

CSF stopped at stage3/address-space,error-52/state, before MCU_CONTROL_AUTO.
The source path and sample_flags1 prove the internal-mask gate was reached
and rejected; JOB mask readback was0xffffffff, so the remaining GPU0x80503
or MMU0xffff comparison failed (or both). Neither GPU/MMU mask readback is
recorded by2324; this result cannot identify which mask was responsible.
L2_READY1,TRANSCFG0x420001c6,rootPA0x40076000 and prestart shared version0
were observed. MCU was NOT started and runtime interface was NOT sampled;
zero runtime fields are unobserved. Thus this trial does not evaluate the
IRQ-enable hypothesis against the earlier2323 MCU timeout. Cleanup verified:
disable status/error0,reset RAW0x100,reset_completed1,cleanup_error0.
Firmware-ready remains false. AS_PRESENT was0xff, not proof of which
interrupt-mask bits the hardware implements.

Normal boot enumerated Fastboot83.56s after reboot. One persistent fbraw
session verified matisse/slot_a/geometry, flashed the known stock20MiB
prefix (OKAY), and requested Recovery (OKAY). Recovery restored the full
67108864-byte original boot_a; independent identity/geometry and full hash
matched2931647a56039722ea2585990b8ef3b1a2daf4c9b990231879f753049eaf86b1.
No user keys/unplug,host SIGINT or blind USB retry was needed. Fresh Recovery
dmesg891397B was saved. Journal is complete-restored-Recovery,
restore_pending=false; no active trial/restore runner remains. This is
host-managed restoration, not automatic Recovery from XNU.

Ignored evidence is under shim2324-trials/gpu-normal/ with sibling
gpu-normal-run.txt. Next static work must audit implemented interrupt-mask
bits and preserve exact GPU/MMU readbacks in a successor before interpreting
another MCU trial. No second trial,new image or device write is authorized.
No new build,CI run,push or source-code modification was needed for this trial.


## Normal2324 result and successor2325 (2026-10-31)

The normal2324 hardware trial reached the CSF address-space stage but
rejected the pre-MCU mask gate with state error-52. Fresh marks establish
sample_flags1, L2_READY1, TRANSCFG0x420001c6, rootPA0x40076000,
AS_PRESENT0xff and JOB_INT_MASK readback0xffffffff. MCU_CONTROL_AUTO was
not issued. 2324 report ABI did not preserve GPU/MMU mask readbacks, so the
exact rejected comparison is unknown; neither one may be guessed. Core
state was not sampled by2324. Cleanup disable and soft reset passed, the
power reference was released, and no firmware-ready claim applies.

Fastboot enumerated83.56 seconds after normal reboot. The preapproved
single-session fbraw restoration flashed the stock20MiB prefix, requested
Recovery and allowed a full67108864B original boot_a restore. Independent
Recovery identity/geometry and full SHA256
2931647a56039722ea2585990b8ef3b1a2daf4c9b990231879f753049eaf86b1
passed. Journal is complete-restored-Recovery with restore_pending=false.
Evidence stays ignored under shim2324-trials/gpu-normal/. This was host-
managed restoration, not automatic Recovery from normal XNU.

2325 retains the full requested pre-start writes GPU_MASK0x80503,
JOB_MASK0xffffffff and MMU_MASK0xffff. It records exact GPU/JOB/MMU mask
readbacks, AS_PRESENT and whether the gate passed. It requires JOB global
interface bit31, GPU fault/protected/reset bits0x103, and every page-fault
mask bit corresponding to a present AS0..15 slot. It does not require
reserved/unimplemented mask bits to read back as ones; the exact values are
still reported. This accommodates a GPU readback such as0x103 when optional
source bits are not implemented, while refusing absent fault/reset sources.
MMU mask requirement follows the measured AS_PRESENT bitmap; simulator tests
cover zero-extended/clamped and missing-required-bit readbacks.

Before MCU start,2325 captures GPU AS_PRESENT and shader/tiler PRESENT,
PWRTRANS and READY registers. After the firmware wait, it captures the same
core state again, along with the existing CSF RAW/shared evidence. The exact
pinned firmware loop at0x01002ee4 reads TILER_PRESENT and TILER_PWRTRANS,
waiting for their intersection to clear before writing TILER_PWRON.
The effective MCU addresses are0x40000190/194: R8 is0x40000010, so the
disassembly operands [r8,#0x180/184] do not target SHADER_PWRON.
2324 did not capture these registers, so no actual cause of its gate rejection
or the earlier2323 firmware timeout is inferred. The endpoint snapshot can
show a current transition, but cannot locate the firmware program counter
or exclude an earlier wait.

Report grows128->192B; kernel records24 CSF qwords at marks320..343. Decoder
retains2321..2324 layouts and verifies mask evidence only for2325. Targeted
30-test suite PASS, including ASan/UBSan loader/state-machine models,
2325 evidence cases and prior ABI regressions. Actual pinned firmware
ASan/UBSan replay PASS:7 ordinary sections,3 protected skipped,8 tables,
1232896 arena bytes,606208 shared bytes.

Local incremental kernel build exited0 without CI/push. Kernel16724248B
SHA256 da73b367cb071992f592485431bc7ac963c3ce200709eee61236774a70459f39.
Image26714112B:
research/matisse/20261031-gpu/shim2325-ready/matisse-shim-gpu2325.img
SHA256 06759c12f2bfb0bd7a7631909e03adb6e7411668dd4f346338797cd31d7e611f.
Predicted full boot_a hash, candidate prefix plus unchanged baseline tail:
5193d19a93bfe4065a5833d0f46e72250810335b452075d9bc3d51730739ba3e.
Independent source-manifest/frozen-object/image/fallback validation passed.
Expanded image80402548B, fallback Linux +32MiB unchanged,rootrw=0,ufsrw=0.
Signature bytes are retained but not authenticated. Proprietary inputs remain
ignored. Recovery-only readonly preflight reverified current boot_a baseline
2931647a56039722ea2585990b8ef3b1a2daf4c9b990231879f753049eaf86b1.

At this build milestone, no2325 hardware trial had occurred. Implementation/
tests/docs were committed as3f29061. The next action then was specific
approval for ONE2325 Recovery-fallback
boot_a trial, Recovery reboot and full baseline restore/hash. A separate approval is required for normal MCU execution after
same-image fallback passes. Normal XNU Recovery remains unreliable; retain
the verified persistent fbraw stock-prefix path. No second2324 trial or
2325 write was authorized by the2324 approval. Both subsequent2325 trials
and full restorations are recorded below.


## Recovery fallback2325 hardware result (2026-10-31)

The specifically approved fallback trial of image06759c12 ran once; runner
43725 exited0. Fresh Recovery was observed26.53 seconds after adb reboot
recovery. Full candidate boot_a readback matched predicted partition hash
5193d19a93bfe4065a5833d0f46e72250810335b452075d9bc3d51730739ba3e.
No Fastboot, user USB/key action or host SIGINT was needed. Fresh Recovery
dmesg863855B was captured. Full67108864-byte original boot_a was restored
and independently rehashed2931647a56039722ea2585990b8ef3b1a2daf4c9b990231879f753049eaf86b1.
Independent identity/geometry confirmed matisse/slot_a/root Recovery.

Ignored shim2325-trials/recovery-fallback/journal.json is
complete-restored-Recovery,restore_pending=false. Independent-post-restore.txt
records the same identity/hash; no active runner or restoration remains.
Before/after4198400B tails and4096B marks are byte-identical, as expected
for bypass. This verifies2325 Recovery entry/BSS and embedded original Linux
fallback only. Normal MCU execution, firmware readiness and acceleration
remain unverified. The next hardware step needs separate specific approval
for one normal2325 MCU trial using this same image, then full restoration.


## Normal2325 hardware result (2026-10-31)

The specifically approved normal2325 trial ran once; runner87765 exited0.
Fresh marks build2325/count85 replace2324/count77;18657B console agrees with
sweettrial2325/gpu2325. Platform INIT0/ON1/OFF0,SPM3->7,GPU_ID0xa8620004,
initial reset completion0x100 repeated and the power reference was released.
Prestart mask readbacks are GPU0x80503,JOB0xffffffff,MMU0xff,AS_PRESENT0xff;
the2325 gate passed and MCU_CONTROL_AUTO was issued. This establishes that
requesting MMU0xffff need not read back0xffff on this device.2324 did not
record its own GPU/MMU readbacks; a specific attribution of its earlier
rejection remains inference, not a measured2324 mask.

MCU start timed out again: stage4/error-53,MCU_STATUS1,JOB_RAW0,MMU_RAW0,
AS status/fault/address0,L2_READY1,TRANSCFG0x420001c6,rootPA0x40076000.
sample_flags15 proves pre/post shared and core captures executed. Shared
version before/after0 and features0; input0x04002000,output0x04003000,groups8,
stride0xa0 remain preloaded blob metadata and are not execution evidence.
No fresh global-interface IRQ or version publication occurred.

Poststart shader PRESENT0x770017,PWRTRANS0,READY0;
tiler PRESENT1,PWRTRANS0,READY1,all high words0. The captured endpoint is
not an outstanding shader/tiler transition. This does not establish which
firmware instructions executed or exclude an earlier transient wait.
GPU_RAW0x600,disable_status1/disable_error-53,reset_raw0x600,
reset_completed0,cleanup_error-53. Internal interrupt enables alone did not
produce the firmware handshake. Firmware-ready and acceleration remain
unproven, and cleanup was not verified by the MCU transaction.

Fastboot enumerated99.82 seconds after normal reboot. The authorized
single persistent fbraw session verified identity/slot/geometry, restored
the stock20MiB prefix with OKAY and requested Recovery with OKAY. Recovery
restored the full67108864-byte original boot_a; independent Recovery
identity/geometry and full SHA256 matched
2931647a56039722ea2585990b8ef3b1a2daf4c9b990231879f753049eaf86b1.
Fresh Recovery dmesg874306B was saved. No user USB/key action,host SIGINT or
blind transport retry was needed. Journal is complete-restored-Recovery,
restore_pending=false,evidence_decoded=true; no active runner remains.
This is host-managed restoration, not automatic Recovery from normal XNU.

Evidence stays ignored under shim2325-trials/gpu-normal/ and sibling
gpu-normal-run.txt. No second trial,new image or device write is authorized.
Further static analysis must compare firmware boot/MMU/coherency prerequisites
and G710 vendor initialization, without claiming the timeout root cause.

## Post2325 vendor initialization audit (2026-10-31)

This bounded audit uses the same extracted KMD hash22b26f30 and the saved
live Recovery DTB hash4fa4d9fe. It does not execute firmware or read new GPU
registers. Full GPU-node properties, rather than a filtered inventory, contain
none of system-coherency, quirks_gpu, quirks_sc, quirks_tiler or quirks_mmu.
These are the exact property names resolved from KMD ELF relocations and
rodata. The live DT is evidence of LK's Recovery configuration; a normal
Android runtime has not been observed.

- kbase_device_coherency_init0x2374c stores default31 at device+0x2dfc.
  kbase_pm_init_hw calls kbase_cache_set_coherency_mode at0x3be0c with that
  field. The setter0x3678c writes GPU+0x304 when feature19 is set. The model
  key for GPU_ID0xa8620004 is0xa0020000 (mask0xf00f0000); its feature array
  at rodata+0x12084 includes19. The current probe neither programs nor
  records COHERENCY_ENABLE, so its actual post-reset value remains unknown.
- In the no-DT-override path, vendor initialization derives values for
  SHADER_CONFIG+0xf04, TILER_CONFIG+0xf08, L2_MMU_CONFIG+0xf0c and
  CSF_CONFIG+0xf00 before writing them at0x3bd84..0x3bdf8. Shader/tiler
  defaults also depend on model/feature/issue bits; do not invent literals.
  kbase_set_mmu_quirks0x4045c has no model-table entry for0xa0020000; its
  default path clears0x0f000000 in the existing L2_MMU_CONFIG value. The
  separate coherency==1 addition does not apply to default31. No actual
  quirk-register readback is available from2325.
- Vendor MMU setup supplies MEMATTR0x00084c8d888d8f88 and mode6. Its default31
  path adds WB/RA walks without outer-shareability or observed INA bits,
  yielding0x42000006. Probe2325 instead measures0x420001c6 and uses its
  own attribute-index assignments. Compare effective PTE attributes and
  table-level semantics, not raw index numbers alone. Different register
  values do not establish that either configuration caused the timeout.

Ignored evidence firmware-static/post2325-vendor-audit.json records source
hashes, property absence, model/features and exact register/function offsets;
vendor-init-audit.txt holds bounded local disassembly extracts. Before a
behavioral successor, finish the MCU fetch/address-space audit and select
one evidence-backed difference. A future probe can record COHERENCY_ENABLE,
CSF_CONFIG, SHADER_CONFIG, TILER_CONFIG, L2_MMU_CONFIG and AS_MEMATTR alongside
existing diagnostics. No speculative register writes, new build or device
action were performed by this audit.

## Offline fetch and access audit (2026-10-31)

`tools/matisse-csf-fetch-audit.py` compiles the actual independent C parser
and memory builder with ASan/UBSan. It constructs the current four-level
48-bit-VA,4KiB arena at measured PA0x40076000, walks those generated tables,
and copies translated arena bytes into a synthetic Cortex-M7 Unicorn run.
It checks each startup instruction fetch and data read/write against page
presence, arena bounds, AF, privilege/AP, RO and PXN/UXN. Unsupported table
descriptor flags fail closed. The CLI accepts only pinned blobde22d2fc,
because the reset/startup addresses and synthetic MMIO assumptions are
specific to that image. No proprietary bytes are included in the tool.

Run from the repository root with a local Unicorn installation:

```sh
python3 tools/matisse-csf-fetch-audit.py \
  --firmware research/matisse/20261031-gpu/extracted/vendor_a-mali_csffw.bin \
  --python-deps research/matisse/20261031-gpu/firmware-static/python-deps
```

Reset vectors read through the generated tables are MSP0x02040000 and
Thumb entry0x010018ed. With otherwise-zero synthetic MMIO and the explicitly
seeded identification/feature registers, startup reaches WFI0x01003032 in
986 instructions, publishes shared version0x01010000, and has no modeled
access violation. It fetches pages0x01001000,0x01002000,0x01003000,
0x0100b000 and0x0100e000. A TILER transition clearing after four reads
reaches the same point in1004 instructions. A permanently asserted
synthetic transition hits the10000-instruction cap in0x01002ee4..0x01002ef2
with version0. Neither transition control measures an actual device state.

As a negative permission control, setting the first shared-page PTE to RO
stops instruction640, PC0x01002fd6, on the write to0x04000018. Version
remains0. Unicorn pages are deliberately mapped RWX so these denials come
from the independent access checker, rather than Unicorn's host mappings.
Eight standalone tests cover page boundaries, missing pages, permissions,
AF, hierarchy flags and out-of-arena pointers without firmware or Unicorn.
The targeted eight-module suite passes39 tests in3.177s.

Source pins for this replay are SHA256:

- `xnu/gpu/mali_csf_memory.c`: b30ea8dc07278f9bc1cfa4d9d37a20bf6659e2cb2385a51ea616227dca5100fc
- `xnu/gpu/mali_csf_firmware.c`: 17520e27cb0a48bf00db23cd26ae7c719c0ef564e82c28fc778ce62eb434991a

The synthetic model does not implement actual Mali MMU hardware, caches,
coherency, DRAM reachability, clocks, interrupts or Cortex-M MPU behavior.
It establishes only that the generated bytes/mappings permit this modeled
startup path. It does not establish real MCU execution or fix the2325
timeout; real shared version/IRQ evidence remains absent.

The effective vendor attributes also remain different. For ordinary cached
sections, vendor convert_mem_flags/entry_set_ate select index0,value0x88,
with no shareability bits. The probe selects index1,value0x9f,SH_IS. For
shared cache-mode3, vendor coherency31 degrades to mode0,index5,value0x4c,
with no SH bits; the probe uses index0,value0x4c,SH_OS. Vendor table creation
at0x47250 sets low bits0x403 and keeps software entry-count bits55..58;
the independent builder uses PA|3. These differences are static observations,
not evidence that an attribute or table bit caused the timeout.

Ignored evidence is firmware-static/fetch-audit-{zero,transition-completes,
transition-stuck,readonly-negative}.json and csf-fetch-audit-tests.txt. No
kernel/image change,CI run or device action occurred. The next diagnostic
should preserve behavior and capture reset/init register values plus early
firmware-owned memory mutations before cleanup. Any future partition write
requires its own concrete image approval under AGENTS.md.

## CSF2326 startup evidence build (2026-10-31)

The build-only successor keeps the transaction behavior unchanged and appends
evidence fields to the report. It records pre/post values of GPU
`COHERENCY_ENABLE` (`0x304`), `CSF_CONFIG` (`0xf00`), `SHADER_CONFIG`
(`0xf04`), `TILER_CONFIG` (`0xf08`), `L2_MMU_CONFIG` (`0xf0c`) and the
programmed `AS_MEMATTR` pair (`0x2408/0x240c`). It also samples four words in
the ordinary firmware arena section and the shared word at VA `0x04000018`
before MCU AUTO and after the startup wait. Sampling is bounded, read-only and
does not substitute for a fresh JOB global IRQ, version publication or valid
runtime interface.

The private addresses are tied to the pinned blob: the arena page backing MCU
VA `0x0202c000` contains the endpoint words at offsets `+0x934`, `+0x93c` and
`+0x22c`; the disassembly writes them near PCs `0x01002bce`,
`0x01002bea/0x01002c16` and `0x01002f14`. The shared allocation word is
`0x04000018`, written near `0x01002fd6`. If the blob's ordinary section does
not cover that page, the probe refuses to run.

The ABI is build `0x2326`: the report is 288 bytes and the kernel records
36 CSF qwords at marks `320..355`. The decoder treats these words as
diagnostic evidence only. It requires all five diagnostic flag bits and the
private page address before considering startup sampling complete, while the
firmware-ready predicate still requires the existing fresh IRQ/version/
interface checks. A diagnostic mutation can show that the modeled endpoint
was reached; an unchanged word cannot prove that it was not.

Validation completed without a device write: local XNU build exited 0; the
build-only image is
`research/matisse/20261031-gpu/shim2326-ready/matisse-shim-gpu2326.img` with
SHA256 `2b55baf18e88a68f4e642ab35bda1cdb95987452710bc1b56a964aa99d544b87`.
The 40-test targeted suite passed in 3.111 seconds. No CI run or push was
performed. A 2326 hardware trial requires separate approval and must use the
same restoration journal/full-boot hash procedure as earlier trials.

## CSF2326 hardware result (2026-10-31)

The specifically approved normal CSF2326 trial ran once and was fully
restored. The candidate image hash was
`2b55baf18e88a68f4e642ab35bda1cdb95987452710bc1b56a964aa99d544b87`; the
temporary full-partition hash was
`b585e5f36c09081670118aec1f0468020e3ca5c62b37e62732579b115986ea91`.
Normal boot reached Fastboot after 93.73 seconds. The single persistent
`fbraw` session flashed the 20 MiB stock prefix with `OKAY`, requested
Recovery with `OKAY`, and the Recovery-side full restore returned boot_a to
67108864 bytes and SHA256
`2931647a56039722ea2585990b8ef3b1a2daf4c9b990231879f753049eaf86b1`.
The journal is `complete-restored-Recovery` with `restore_pending=false`.

The fresh build2326 marks contain97 records and decode as platform
INIT0/ON1/OFF0, SPM3->7, GPU_ID `0xa8620004`, reset `0x100`, AS_PRESENT
`0xff`. CSF mask setup passes with GPU `0x80503`, JOB `0xffffffff`, MMU
`0xff`; L2 is ready and the programmed address-space state remains
TRANSCFG `0x420001c6`, root PA `0x40076000`. The MCU still ends at stage4
with timeout `-53`, MCU status1, raw JOB/MMU0, AS fault/status0, version0 and
no fresh global-interface IRQ. The endpoint snapshot is shader
PRESENT`0x770017`/transition0/ready0 and tiler PRESENT1/transition0/ready1.
Cleanup again times out (`disable_error=-53`, reset raw `0x600`, reset not
completed), so firmware readiness is unproven.

The new read-only startup sample completed (`diag_flags=31`). It observed
coherency features1; `COHERENCY_ENABLE`, `CSF_CONFIG`, `SHADER_CONFIG`,
`TILER_CONFIG` and `L2_MMU_CONFIG` all read0 before and after, while the
programmed AS_MEMATTR pair was `0x4c4c9f4c/0x4c4c4c4c`. The private probe page
was PA `0x400bb000`; the three private marker words stayed0->0. The shared
word at VA `0x04000018` changed0->`0x1d`. This sampled mutation proves only
that the observed memory state changed during the transaction; the probe has
no writer trace and cannot identify a firmware PC or establish complete MCU
execution. No new global IRQ or version publication was observed.

Ignored evidence is under
`research/matisse/20261031-gpu/shim2326-trials/gpu-normal/`. This result
does not authorize another write. Any next test needs a new image and a
separate concrete approval, with the same full restore/hash procedure.


## CSF2327 isolated coherency diagnostic (2026-10-31; not hardware tested)

Fresh read-only Recovery collection confirms matisse, slot_a, root and the
original 67108864-byte boot_a SHA256
`2931647a56039722ea2585990b8ef3b1a2daf4c9b990231879f753049eaf86b1`.
Evidence is `recovery-live-6/raw-state.txt`. The provided official image
package resolves to `/Users/xiaohuasheng/Documents/matisse_images_OS2.0.2.0.ULKCNXM_14.0`;
package hashes and inventory remain in ignored research. Recovery does not
bind Mali/GPUEB/gpufreq and provides no runtime GPU register snapshot.

The vendor quirk comparison is now reconstructed from the pinned local KMD
SHA256 `22b26f30a151e9d6791f959cc1f93d1e3f4d4c564537970dadefb0ec2d742a3b`,
its relocations, feature and production issue tables. GPU_ID `0xa8620004`
masks to model key `0xa0020000`. Production record12 at rodata `0x126e0`
selects revision4's issue list `0x12e1c`: 1,15,19,30,31,32. Issue4 and21
are absent; feature19 is present and24 absent. The module's
`corestack_driver_control` default is BSS0. With the measured zero reset
registers and no DT overrides, the default-derived values for SHADER_CONFIG,
TILER_CONFIG, CSF_CONFIG and L2_MMU_CONFIG are all zero. This is a static
derivation of defaults, not a runtime trace or timeout diagnosis. The
ignored data audit is `firmware-static/vendor-2327-data-audit.json`.

The relevant vendor instructions are `kbase_pm_init_hw` at `0x3c150..0x3c35c`
(CSF/shader/tiler derivation), `kbase_set_mmu_quirks` at `0x4045c..0x405dc`,
`kbase_device_coherency_init` at `0x23764` (default31), and
`kbase_cache_set_coherency_mode` at `0x367ac..0x367d4` (feature19 gates
GPU+0x304). Linux v6.12 `panthor_regs.h` independently names selector31
`GPU_COHERENCY_NONE`. Value31 is a protocol selector, not a mask that must
be present in COHERENCY_FEATURES, whose measured value was1.

2327 changes one behavioral input: the diagnostic shim explicitly requests
protocol NONE through config `noncoherent=1`. The portable transaction
accepts only0/1;0 preserves the old sequence. It snapshots reset state, masks
interrupts, writes GPU+0x304=31 before L2/AS/MCU initialization, and immediately
reads it back. A mismatch rejects before enabling L2 or MCU and proceeds to
reset/cleanup. PTEs, MEMATTR, TRANSCFG and four quirk registers are unchanged.
This is a controlled hypothesis test, not a claimed fix for the2326 timeout.

The report is296 bytes, with requested/readback appended after the2326 ABI,
and kernel patch0125 publishes37 qwords at marks320..356 under build2327.
Flags32/64 mean attempted write/matched readback. The decoder retains all
previous report ABIs and requires protocol readback31, post-start protocol31,
fresh global JOB IRQ, version/interface evidence and successful cleanup
before declaring success. A matched protocol alone cannot establish MCU
readiness.41 targeted tests pass in5.173s, including ASan/UBSan, default-off,
write ordering, rejected readback, timeout and stale/partial evidence cases.
The publication fixture rejects the former288-byte buffer.

Local full XNU build exited0. Kernel is16724248 bytes, SHA256
`3817002e5b249c9cd0efeb55ee42a9d42147422e2ce13f562ebc6f368ac655f9`. The build-only image is26714112 bytes, SHA256
`a624742667410660768dd0349a9622b73439dcfd71975edbd1918832defdd30c`, at
`research/matisse/20261031-gpu/shim2327-ready/matisse-shim-gpu2327.img`.
Independent image validation passed: source pins and frozen objects match,
stock Linux remains byte-identical at+32MiB, ramdisk/signature bytes match,
expanded size80402548, report296 bytes, and rootrw/ufsrw remain0. Retaining
signature bytes does not authenticate the image. The local kernel source
replays exactly with the inherited untracked0093 read-only-console patch
included; this existing difference is recorded explicitly and preserved.
No device boot, partition write, CI run or push occurred.

`shim2327-trials/restoration-plan.json` and a separate pinned trial runner
are prepared; only the runner's read-only preflight ran and passed. No active
trial journal or restoration duty exists. Full backup and stock-prefix hashes
match the previous successful restoration inputs. Predicted temporary full
boot_a hash is `3682d6a6727d4d24157de1524e566ec8da76b6513eee4434851a987aec5afe3d`.
A new concrete approval is required for one normal2327 boot_a trial and the
complete64MiB restore/hash. Host-managed Fastboot/Recovery restoration is
the established recovery path; automatic Recovery from normal XNU remains
unverified. The device remains in root Recovery with the original hash.
