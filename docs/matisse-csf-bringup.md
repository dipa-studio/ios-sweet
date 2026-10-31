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


## CSF2327 hardware result (2026-10-31; full restoration complete)

The user explicitly approved one normal2327 boot_a trial and complete
original restoration. The pinned image SHA256
`a624742667410660768dd0349a9622b73439dcfd71975edbd1918832defdd30c` was written once; full-partition readback matched predicted
`3682d6a6727d4d24157de1524e566ec8da76b6513eee4434851a987aec5afe3d`. Normal boot reached Fastboot after180.34s. A single
persistent raw USB session returned OKAY for the known stock-prefix
download, flash and reboot-recovery. Root Recovery then restored all
67108864 bytes of the original boot_a. A separate read-only check confirmed
matisse, slot_a, recovery, uid0, correct geometry and SHA256
`2931647a56039722ea2585990b8ef3b1a2daf4c9b990231879f753049eaf86b1`. The journal reports `complete-restored-Recovery` and
`restore_pending=false`; the runner exited0. No user USB/key intervention,
new build, CI run or push occurred.

Fresh build2327 marks contain98 records, including all37 CSF qwords at
320..356, and match the final4096 bytes of the captured diagnostic tail.
The previous capture was2326/count97. The18657-byte console independently
names gpu2327/sweettrial2327. Initial power/reset observations remain
INIT0/ON1/OFF0,SPM3->7,GPU_IDa8620004,reset100,AS_PRESENTff.

The intended change is measured: coherency features1, reset protocol0,
requested31, immediate readback31, post-MCU-wait31. Diagnostic flags are127
and `noncoherent_protocol_verified=true`. Nevertheless MCU ends at stage4
with timeout-53,MCU_STATUS1,JOB_RAW0,MMU_RAW0,version0,AS fault/status0,
and no fresh global-interface IRQ. L2_READY1, rootPA40076000,
TRANSCFG420001c6 and MEMATTR4c4c9f4c/4c4c4c4c match2326. IRQ gate passes
with GPU80503/JOBffffffff/MMUff. Shader endpoint is PRESENT770017,
transition0,ready0; tiler endpoint PRESENT1,transition0,ready1. The four
configuration registers remain0; private markers remain0 and shared
VA04000018 changes0->1d. Cleanup still reports disable timeout-53/status1,
reset_raw600,reset_completed0,cleanup_error-53. Firmware-ready is false.

Every common CSF field matches2326 except flags31->127 and
coherency_after0->31; the newly appended requested/readback words are31.
This shows protocol NONE alone is insufficient for handshake in the tested
configuration. It does not locate the firmware PC, identify the timeout
cause, or prove that no firmware instructions executed. The longer USB
return time is measured but cannot be attributed to coherency from one run.
GPU acceleration remains unverified.

Evidence stays ignored under `shim2327-trials/gpu-normal/`: journal,
decoded report, before/after marks and tail, console, Recovery dmesg,
`comparison-2326-2327.json` and `independent-post-restore.txt`. Recovery
dmesg is869052 bytes. The approved trial is consumed; any new partition
write needs a new concrete image confirmation. Next work is offline
vendor address-space/PTE/cache and MCU-startup comparison. Do not rerun
this image expecting a different handshake result.

## Post2327 vendor memory-group audit and CSF2328 candidate (2026-10-31)

The vendor comparison now includes the actual platform memory-group manager,
not only kbase's base descriptor. The saved live Recovery DT links GPU
physical-memory-group-manager to phandle0x59, which resolves to /mgm with
compatible arm,physical-memory-group-manager. This is binding evidence;
Recovery does not provide an observed Android runtime mapping trace.

The extracted mali_mgm module SHA256 is
22113cb61a7b1fab5e552ff028a7e45c8ef40cfe57b2bdd67ea835b017d0f2f9.
Its example_mgm_update_gpu_pte at text0x97c..0x9dc reads a debug override at
private+0x210, substitutes6 when that word is0, and ORs the selected group
into descriptor bits59..62. The requested group argument does not choose
the result in this helper. A synthetic override3 produces3 instead of6;
no Android runtime override was measured. The probe's prior descriptors
have these four bits0. This omitted platform transformation is an observed
binary difference, not a diagnosed timeout cause or proof of its physical
routing effect.

New tools/matisse-csf-vendor-mmu-audit.py requires the pinned kbase, MGM and
firmware hashes. It checks ELF section bounds and rejects relocations in
selected helper ranges, then executes those original AArch64 instructions
in bounded Unicorn instances with synthetic inputs. It exercises the
firmware-section flag conversion block0x6fbec..0x6fc9c, entry_set_ate,
entry_set_pte, kbase_mmu_get_as_setup and example_mgm_update_gpu_pte. It
compares all293 ordinary mapped pages built by the actual independent C
loader. No proprietary bytes are stored in the tool or tracked tests.

The replay confirms the earlier cache/SH/nG/PXN differences: ordinary cached
sections resolve to vendor AttrIdx0/value88/SH0; shared resolves to
AttrIdx5/value4c/SH0 under coherency31. Their MGM-transformed leaves also
carry group6. Base table descriptors use PA|403 rather than PA|3; the
software entry count is stored separately in bits55..58 of the table's
first three words. Those existing differences remain separate hypotheses.
The vendor AS helper supplies MEMATTR00084c8d888d8f88 and base TRANSCFG6;
the coherency31 WB/RA addition42000000 is still statically derived from
kbase_mmu_hw_configure, not emulated by this helper audit.

CSF2328 isolates just the leaf group tag relative to2327. The new explicit
sweet_csf_memory_build_group accepts0..15; its group0 wrapper preserves
existing behavior. The shim requests6 and retains every2327 low descriptor
bit, table descriptor, firmware byte, MEMATTR, TRANSCFG, coherency31 write,
IRQ setup and MCU sequence. Group tags do not enter physical-address masks.
ASan/UBSan checks on synthetic and real pinned firmware compare every arena
byte: exactly293 bytes change, one high byte per mapped leaf, with XOR30 in
that byte. No firmware/table/data/permission/cache bytes change. This is a
candidate diagnostic, not a proven fix.

The report appends software group/count words to304 bytes,38 qwords at
marks320..357. These fields explicitly describe builder inputs and293 leaf
pages; they are not hardware translation readback. The decoder retains
fresh IRQ, version, valid interface and successful disable/reset requirements,
so configured group6 alone never establishes firmware readiness. Patch0126
bumps the persistent kernel build marker to2328 and transports the new ABI.

48 targeted tests pass in3.219s, including malformed ELF/hash/relocation
rejection, descriptor group isolation, real C ASan/UBSan models, previous
report ABIs, new metadata negative cases and contextual patch application.
Separate real-firmware ASan/UBSan checks pass. Group0/group6 synthetic MCU
replays are identical:986 instructions to WFI, version01010000, no modeled
access violation. The emulator does not implement high-bit memory routing,
GPU caches/MMU, clocks or real MCU execution; this cannot predict hardware
success.

Local complete kernel build exits0:16724248 bytes, SHA256
e0d046e63aa909626dfa771fa3ebaf377e11c3530437936cd5faf8653c1aaf4f.
Build-only candidate26714112 bytes, SHA256
a880c8465cbc02deaa287a4925e54a911722e938fde1685fecf0410d733959a6,
at research/matisse/20261031-gpu/shim2328-ready/matisse-shim-gpu2328.img.
Independent verification checks expanded80402548 bytes, intact stock Linux
at+32MiB, ramdisk/signature byte equality, pinned source/frozen objects,
report ABI, rootrw0/ufsrw0 and no absolute pointer relocations. Signature
bytes are retained, not authenticated; automatic Recovery remains unverified.
Kernel source contextual replay matches only with the inherited untracked
0093 console patch, hash54f0aaa5a0390bc0678eca60e55bc192d3ebea315daab808a3c456a1ce65365b,
which remains uncommitted and preserved.

Detailed evidence stays ignored in firmware-static/vendor-mmu2328-audit.json,
group6-isolation2328.json,fetch-audit-group6-2328.json and the2328 build/test
logs. A separately pinned shim2328-trials-run-once.py and restoration plan
are prepared. Only its read-only preflight has run; no journal or device
write/reboot exists. Fresh root Recovery identity and all64MiB original
boot_a SHA2562931647a56039722ea2585990b8ef3b1a2daf4c9b990231879f753049eaf86b1
are verified. No CI run or push occurred.

Implementation commit5ba6301 contains the17 reviewed2328 source/test/patch
files. Source whitespace checks pass;0126 retains required contextual patch
whitespace and its contextual replay passes. Unrelated working-tree edits
and inherited untracked0093 remain intact.

Next requires specific confirmation of ONE normal2328 trial of imagea880c846:
write only boot_a, verify full predicted partition hash1987a83a69676c290dca9a80c8aa95aa4502dd39982df192df6d8cd3e9cf3176,
collect fresh2328 evidence, restore the stock prefix through one persistent
Fastboot session if needed, then restore and independently hash the full
original64MiB in Recovery. The latest 可以 authorized offline continuation;
it did not name or approve this newly created image.

## CSF2328 approved hardware trial and full restoration (2026-10-31)

After the specific image-and-restoration prompt, the user replied 可以.
Exactly one normal2328 trial ran in runner session89703, exit0. The
26714112-byte image SHA256a880c8465cbc02deaa287a4925e54a911722e938fde1685fecf0410d733959a6
was written to boot_a; full partition readback matched predicted
1987a83a69676c290dca9a80c8aa95aa4502dd39982df192df6d8cd3e9cf3176.
The device reached Fastboot after83.54 seconds. A single persistent raw
USB session returned OKAY for stock-prefix download013e8000,flash:boot_a
and reboot-recovery. Root Recovery then restored the complete67108864-byte
original boot_a. A separate identity/geometry/hash check confirmed
matisse,_a,recovery,uid0 and SHA256
2931647a56039722ea2585990b8ef3b1a2daf4c9b990231879f753049eaf86b1.
No manual USB/key intervention was needed. Journal status is
complete-restored-Recovery,restore_pending=false,evidence_decoded=true;
there is no running trial or pending restoration. Recovery dmesg is890576B.

Fresh marks identify build2328,count99,with all38 CSF qwords320..357.
The4198400-byte tail ends in the identical marks block. Before marks identify
2327,count98 and exactly match the prior trial; the2328 decoder rejects
them. The18657-byte after-console independently names gpu2328 and
sweettrial=2328. These checks distinguish the new capture from stale data.

The new fields show requested group6 and293 built leaf pages, as expected.
They are software builder metadata, not hardware translation or routing
readback. Every common decoded GPU and CSF field is unchanged from2327.
Platform power/init/reset evidence, coherency31 write/readback, IRQ mask gate
and L2 readiness remain present. MCU is still stage4/error-53,MCU_STATUS1,
JOB_RAW0,MMU_RAW0,version0,AS fault/status0. TRANSCFG420001c6,rootPA40076000
and MEMATTR4c4c9f4c/4c4c4c4c are unchanged. Private marker words remain0;
shared04000018 changes0->1d. Disable still times out-53,cleanup reset_raw600
with reset_completed0 and cleanup_error-53. Firmware readiness remains false.

Thus adding group6 alone did not establish the firmware handshake under
this configuration. This does not show whether hardware consumed that tag,
identify firmware PC or diagnose the timeout. The83.54-second Fastboot return
versus2327's180.34 seconds is an observed single-run difference with no
causal attribution. No GPU acceleration or firmware-ready result is claimed.

Ignored evidence under shim2328-trials/gpu-normal includes journal.json,
gpu-result.json,comparison-2327-2328.json,independent-post-restore.txt,
before/after marks and tails,after-console.txt and recovery-dmesg.txt;
gpu-normal-run.txt records transport/restoration output. The restoration
plan records the consumed single-trial authorization and verified restore.
Implementation5ba6301 and build handoff4b4c524 are unchanged; prior48 tests
and complete kernel/image checks remain applicable. No new build,CI run or
push occurred. Next is offline pinned vendor cache/AS/PTE and MCU sequence
comparison; repeating2328 is not justified by this result. Any further
candidate device write requires a new specific confirmation.

## Post2328 executable register audit and explicit MCU inputs (2026-10-31)

Audit commit3f33f13 extends the pinned vendor-helper tool with relocation-free
instruction slices AS config0x45e80..0x45fd4,UPDATE0x4605c..0x46084,initial
MCU start0x70008..0x7002c and reload0x6e3c8..0x6e3e8. Synthetic device/AS
structures and a dedicated MMIO slab capture each write with its original
text PC. Full Linux initialization, surrounding AS polling and hardware are
not executed. The tool rejects helper relocations and out-of-range control
flow, validates exact write order/value/width and executes all293 vendor
leaf descriptors against the independently C-built group6 arena.

For protocol31, the vendor slice writes TRANSCFG42000006/0,root40076000/0,
MEMATTR888d8f88/0084c8d, then a separately replayed UPDATE1. Protocol0/1
controls yield62000006; AS7 adds the expected7*64 register stride and a
synthetic high root5a40076000 retains high word5a. Both MCU start slices
write AUTO2, matching the current probe. An ASan/UBSan-built harness captures
the actual independent C boot writes rather than a handwritten write list.
Its pre-AUTO differences remain TRANSCFG and both MEMATTR words; cache,
shareability,nG/PXN and table403-versus3 differences remain separate. These
are observed offline differences, not a diagnosed cause of the real timeout.

The earlier Cortex-M replay seeded raw firmware-visible40000010=a8620004,
40000014=2830 and40030004=2000000a. Those were synthetic assumptions, not
measurements of MCU-visible registers or their equivalence to host offsets.
New explicit CLI inputs and report words make that limitation visible.
Pinned startup01002f96..01002fd6 calculates shared04000018 as
3+bits11:8(word40000010)+bit_length(shader mask40000100/104). Synthetic
shader770017 gives1a with old word10 and1d with hypothetical word10=300.
The latter matches the observed shared value but cannot identify the writer,
firmware PC or real raw-word value. Changing hypothetical40030004 to0 leaves
private early/feature markers0 while the modeled startup still reaches WFI;
private-late remains50c0,unlike real0. Every sensitivity run still publishes
version01010000. Thus neither the observed zero markers nor a single matching
shared word supplies a hardware instruction trace.

Evidence stays ignored in firmware-static/post2328-vendor-register-audit.json,
post2328-input-sensitivity.json and post2328-replay-hypothetical-inputs.json.
The initial offline suite passed57 tests3.476s. No GPU register writes or
device reboot were performed.

## CSF2329 INA-only candidate and verified build (2026-10-31)

Implementation commitb6bb9e1 adds explicit vendor_ina0=0/1. Zero retains
the2328 sequence; the shim selects1. Only the final AS_TRANSCFG write changes
420001c6->42000006,XOR1c0,matching the executed vendor protocol31 slice.
All four-level table allocation and group6 leaves are unchanged, as are
firmware bytes,PA/permissions/cache/MEMATTR,coherency31,IRQ masks and
MCU AUTO/disable/reset. An exact actual-C write comparison changes one write
only; the reconstructed group6 arena remains SHA256
e6cba8456388fe7fc2ba49aee64814478ebdc3491ba5480290b01f9ebe1c91dd.
Built csf_memory.o,csf_firmware.o,csf_blob.o and the blob match2328 bytewise.

The report remains304 bytes,38 qwords320..357. Contextual patch0127 only
bumps the persistent build to2329. Existing transcfg_lo is the hardware
readback; wrong value rejects before MCU start. The decoder requires
42000006 for2329,retains old build expectations and all fresh IRQ/version/
interface/cleanup gates. Matching INA alone never establishes readiness.
Option2 rejects before IO; tests cover the old-valued readback,missing/stale
records,timeout and reset failure. All59 targeted tests pass3.730s. Actual
2326/2327/2328 captures decode to their unchanged saved JSON results.
Freestanding ARM64 cross-compiles and no-ABS64 pointer checks pass.

Full local kernel build exits0,16724248 bytes,SHA256
9ea37e6018022e8a87eb6ed622d19cd18849fc58e33144dc74cf57acda371877.
Candidate research/matisse/20261031-gpu/shim2329-ready/matisse-shim-gpu2329.img
is26714112 bytes,SHA256
83c635bbd15a08bb3333105bc949fd2c9fa21caaad05920844d751875601fe25.
Independent verification checks expanded80402548 bytes,intact stock Linux
at+32MiB,ramdisk/signature byte equality,source/frozen-object pins,report ABI,
rootrw0/ufsrw0 and PIC relocations. Signature is retained,not authenticated;
automatic Recovery remains unverified. Kernel contextual source replay
matches the built tree with inherited untracked0093 hash
54f0aaa5a0390bc0678eca60e55bc192d3ebea315daab808a3c456a1ce65365b,
which remains uncommitted and preserved. No CI or push occurred.

Only the separately pinned2329 runner's read-only preflight ran. It verified
root matisse/_a/Recovery,67108864-byte boot_a and full original SHA256
2931647a56039722ea2585990b8ef3b1a2daf4c9b990231879f753049eaf86b1.
Its runner SHA256 is284b22279b00352be32bf902fc586005438ee3e00aee33bd596d449451602def.
Restoration plan is prepared-unapproved,authorization null,trial_count_executed0,
restore_pending=false with no journal. Predicted full candidate partition
hash isb9626544096d47c370d2bfc3653966e51e237483ee6913127725433041a00fe1.
No device write or reboot occurred. Next requires specific approval for one
normal2329 trial of image83c635bb,full readback/fresh evidence collection,
and complete64MiB original boot_a restoration with independent hash.

## CSF2329 INA-only hardware trial and full restoration (2026-10-31)

The user explicitly approved ONE normal2329 trial of image83c635bb and
complete original restoration. The pinned runner284b2227 executed once,
session77144 exited0. The26714112-byte candidate hash remained
83c635bbd15a08bb3333105bc949fd2c9fa21caaad05920844d751875601fe25.
Full temporary boot_a readback matched the predicted partition SHA256
b9626544096d47c370d2bfc3653966e51e237483ee6913127725433041a00fe1.
Normal boot reached Fastboot after99.87s. A single persistent raw USB session
received OKAY for the stock-prefix download013e8000,flash:boot_a and
reboot-recovery. Recovery then restored the entire67108864-byte original
boot_a. An independent subsequent read verified root matisse/_a/Recovery,
partition geometry and full original SHA256
2931647a56039722ea2585990b8ef3b1a2daf4c9b990231879f753049eaf86b1.
Journal is complete-restored-Recovery,restore_pending=false,evidence_decoded=true.
The restoration plan records one consumed authorization,one executed trial
and independent full restoration. No active runner or restoration remains.

Fresh build2329 marks contain99 records with38 complete CSF qwords320..357;
their4096-byte block matches the last block of the4198400-byte tail. Before
marks and tail exactly match the preceding2328 after capture. The decoder
rejects those old marks when expecting2329. The18657-byte console separately
names gpu2329 and sweettrial=2329. Fresh Recovery dmesg is841950 bytes.

Every common CSF field matches2328 except TRANSCFG420001c6->42000006; the
new vendor_ina_readback_matches is true. All common GPU fields also match.
Thus the intended INA register value persisted through the sampled MCU wait.
Coherency remains requested/read back/after31,software group6/293 leaves,
L2_READY1 and the IRQ-mask gate still pass. MCU remains stage4/error-53,
MCU_STATUS1,JOB_RAW0,MMU_RAW0,version0 and AS fault/status0. Private marker
words stay0; shared04000018 changes0->1d. Disable still times out-53;
cleanup reset_raw600/reset_completed0 and cleanup_error-53. Firmware-ready
remains false. Vendor-matching INA alone did not establish the handshake in
this configuration and does not identify the timeout cause or MCU PC.
99.87s versus2328's83.54s is only a single-run timing observation.

Evidence stays ignored in shim2329-trials/gpu-normal/{journal.json,
gpu-result.json,comparison-2328-2329.json,independent-post-restore.txt,
before/after-marks.bin,before/after-tail.bin,after-console.txt,recovery-dmesg.txt}
and shim2329-trials/gpu-normal-run.txt. Freshness,complete report alignment,
exact common-field comparison and independent restoration checks PASS.
Implementation b6bb9e1 and verified build handoff50f3bf3 remain applicable;
no new build,CI run,push or repeated test suite was needed. Next is offline
vendor MEMATTR/cache/descriptor/table and MCU startup comparison. This
one-trial authorization is consumed; another image/write needs confirmation.

## Post2329 attribute-index audit and CSF2330 cached-byte candidate (2026-10-31)

Offline continuation was authorized after full2329 restoration. Implementation
ad073cf adds a page-by-page raw MEMATTR/index audit over the actual C arena.
All293 vendor leaves still execute through pinned helper slices.145 cached
pages use independent index1/byte9f versus vendor index0/byte88;148 shared
pages use independent index0/byte4c versus vendor index5/byte4c. Directly
copying vendor MEMATTR00084c8d888d8f88 into the independent tables would
instead select8f for cached and88 for shared. Therefore an isolated cached
byte diagnostic retains all PTEs and changes only independent byte1 to88.
Raw byte equality is not a model of effective cache behavior,physical memory
routing or the real timeout cause. SH/nG/PXN/table differences remain.

The vendor table helper47250..472c8 was separately disassembled from the
pinned module. It forces low403 in the stored next-table descriptor and
separately updates packed counter nibbles in the first three table words.
This observation does not establish their hardware meaning; no table change
is selected for2330. Detailed proprietary disassembly remains ignored.

New vendor_cached_memattr accepts0/1;0 retains2329,1 writes MEMATTR low
4c4c884c instead of4c4c9f4c,XOR1700,while high4c4c4c4c remains unchanged.
The shim selects1. Option2 rejects before IO. Wrong low or high readback
rejects before MCU AUTO. Actual C ASan/UBSan write traces differ in exactly
one write,with all remaining writes/order/cleanup equal under identical
synthetic prerequisites. Firmware,PTE/index/SH/nG/PXN/table allocation,
group6,coherency31,INA0,IRQ and MCU startup/disable/reset are unchanged.
The unchanged arena SHA256 is
e6cba8456388fe7fc2ba49aee64814478ebdc3491ba5480290b01f9ebe1c91dd.
Built csf_memory.o,csf_firmware.o,csf_blob.o and csf.bin match2329 bytewise;
linked arena PA remains40076000. This mixes vendor cached byte88 with the
independent descriptor settings deliberately as one diagnostic hypothesis.

Report stays304 bytes/38 qwords320..357. Decoder requires2330 MEMATTR values
and preserves fresh IRQ/version/interface/cleanup readiness gates. A matching
byte alone cannot prove firmware-ready. Patch0128 contextually bumps only
the persistent build2329->2330.63 targeted tests pass4.011s,including invalid
config/readback negatives,old and new ABI,sanitizers and exact write isolation.
Actual2326/2327/2328/2329 captures decode identically to their saved JSON.
Three changed files cross-compile freestanding ARM64 without ABS64 pointers.

The full local CLT kernel build exits0,16724248 bytes,SHA256
7b5519f0c5ef4e7c5474dd2cc92921469306c9b189f3ef5b1db17f0e5054b40a.
An initial Xcode-only wrapper rejected absent Xcode before compilation; the
existing tools/build-xnu-clt.sh then completed. No CI run or push occurred.
Candidate shim2330-ready/matisse-shim-gpu2330.img is26714112 bytes,SHA256
2acb401446915ff72a7b3d8ee5c9d9dcd89cd04b89062ab388a9ea275519a06f.
Independent verification passes expanded80402548 bytes,intact stock Linux
at+32MiB,ramdisk/signature bytes,source/frozen pins,304B ABI,rootrw0/ufsrw0
and relocation checks. Retained signature is not authenticated; automatic
Recovery remains unverified.127-patch contextual source replay matches
local source SHA256cbe6a5dad1bcf5f1f57d5123ca4eace14bac41578d8316961c5e2bd92c3dbccc,
including inherited untracked0093 hash54f0aaa5a0390bc0678eca60e55bc192d3ebea315daab808a3c456a1ce65365b.

A separate runnerd49058813b781860acc928db62d51702df2fbf070db59a122b4a22521eb58ade
was prepared;only read-only preflight ran. Root matisse/_a/Recovery and full
67108864-byte original boot_a hash2931647a56039722ea2585990b8ef3b1a2daf4c9b990231879f753049eaf86b1
pass. Plan is prepared-unapproved,authorization null,trial_count_executed0,
restore_pending=false,no journal. Predicted full candidate partition hash is
42768433ce974e59d1b0c55c1d191a36e283fd2b76dcf594026ed29c35b970cf.
No device write or reboot occurred. Evidence stays ignored under
firmware-static/{post2329-memattr-index-audit,post2329-table-helper,
memattr2330-isolation,vendor-register2330-audit,kernel2330-source-replay}.json,
shim2330-ready/{manifest,independent-verification}.json and build/test logs.
Next requires specific approval for ONE normal2330 image2acb4014 boot_a trial,
full readback/fresh evidence and complete original64MiB restoration with an
independent hash. This offline continuation does not authorize that write.
