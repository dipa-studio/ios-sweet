# MT6983 shim GPU power/reset probe

The opening sections describe the original power/reset probe. The latest
CSF2331 diagnostic and its current validation boundary are recorded below.

2026-10-31. This independently written probe executes GPUEB INIT_SHARED_MEM,
POWER_ON, verifies both MFG power status registers, reads GPU_ID and performs
one CSF GPU soft reset, then releases its single power reference. It does not
load Arm CSF firmware, install GPU page tables or submit graphics work.

## Source of hardware facts

Actual modified LK payload SHA256 is
5310a43ac8b7aec6de3d1571b7012cb6ba3600958db3e4e9df4372fdc642ee84.
Register facts were cross-checked with extracted OS2.0.2.0 vendor KMD and
xiaomi-rubens commit270b84910b941bf75490fccdb5fb2b3021dd7cbf. No GPL
implementation was copied. Raw dumps and reference source remain ignored.

- LK0x20424..0x20474 polls GPUEB0x13c5fd24 for magic0x55667788.
- LK0x2041c stores the additional20MiB firmware allocation PA>>12 at0x13c5fd34.
- Live DT describes mailbox0x13c5fd80, set0x13c62004, clear0x13c62074,
  send0x13c62000 and recv0x13c62078. GPUFREQ pin1 TX+0x10/RX+0xbc,32B each.
- SPM sleep0x1c001000+0xf3c/+0xf40: MFG0 bit1, MFG1 bit2.
- GPU control base0x13000000: ID+0, AS_PRESENT+0x18, IRQ RAW+0x20,
  CLEAR+0x24, MASK+0x28, COMMAND+0x30. CSF soft reset is0x101, completion bit8.

## Bounds and ownership

Default loader builds do not reference this probe. SHIM_GPU_PROBE enables
it only for an exact normal-mode MT6983 live-FDT geometry. Channel tables
are parsed, not guessed. Shared2MiB and additional20MiB firmware memory
must not overlap the XNU memory window or each other. Conflict aborts before
the first XNU segment copy. No shared region is read or zeroed by this probe.

All polls have250ms and independent iteration limits. A pending response
is rejected, other channel interrupts are untouched. Replies are checked
for command/target/signed error. POWER_ON must return count1; unexpected
ownership prevents reset. Only a definitely acquired reference is released.
Timed-out POWER_ON is not retried and does not trigger a blind POWER_OFF.

GPU control registers are accessed only after valid IPI and both SPM checks.
Only expected v10 architecture is accepted; protected mode is rejected.
IRQ mask is saved/restored. The probe does not alter PMIC/PLL/RPC directly.
Host model tests cannot establish that real firmware booted or GPU powered.

## Existing console and Recovery return

The build reserves128B ADT slots for sweet-gpu-report and each shim firmware
version. Bounded summaries with prefix sweet-shim/gpu2320 are printed by
the existing XNU iBoot-version path, then flushed by established SWEETLOG
to the userdata tail. PE_init_iokit uses FW_VERS_LEN128 and enforces NUL.
The raw report is also available in the ADT. Old2317 logs are not a trial result.

Kernel0118 adds an explicit ADT diagnostic-window option. It stops feeding
the hardware watchdog after60seconds; default behavior remains unchanged.
The shim first validates the exact watchdog/reboot-mode FDT, selects the
volatile Recovery mode scratch and arms31seconds. No misc partition write.
Root is ufsrw=0/rootrw=0; existing0093 permits only persistent console tail
logging despite read-only VFS. Early hangs should also expire the watchdog.

An intact package Linux Image is embedded at shim+32MiB. Recovery/unknown
boot modes bypass shim_main and jump directly to that Linux at EL1 with
MMU/caches off. Normal mode executes the probe and XNU. First validate the
Recovery fallback alone, then test normal mode. LK/vendor_boot/DTBO stay intact.

Build-only tool matisse-shim-gpu-image.py requires SHA256 pins, reuses
frozen2313 board/display/UFS objects, and recompiles start/loader/new GPU
units only. Current unrelated dirty shim.c/build.sh are excluded. Combined
Image must end before measured live DTB. Stock fallback, generic ramdisk
and signature are byte-compared; signature is retained, not authenticated.

Host ASan/UBSan tests cover success, invalid mode/address, memory conflict,
power off, wrong magic, stale/negative/bad replies, bounded waits, stopped
timer, unexpected reference count/model, reset timeout and cleanup failure.
Actual FDT reader/ADT publication have regression tests. Hardware outcomes,
image hashes and restoration duty are recorded in NOTES and a fresh journal.

## Hardware trial and evidence correction (2026-10-31)

GPU2320 Recovery bypass returned in26.56s, and its normal boot returned to
Recovery automatically in121.41s. Each trial fully restored and SHA256
verified boot_a2931647a. New progress marks reached launchd; however the
console ring stayed byte-identical to old2317. No GPU result can be inferred.

The initial0093 exception only covered sweet_log_start. WRITE(10) still
rejected read-only logging. Patch0119 adds a separately requested diagnostic
write path bounded to the established last1025 blocks; normal VFS writes
still require ufsrw=1. Bounds are tested with the exact C predicate and
ASan/UBSan. A second independent channel copies the72-byte ADT GPU report
into progress marks300..308 at UFS init, each tagged2321. Build ID2321
identifies this kernel. GPU2321 retains the already tested Linux fallback
and the unchanged GPU state machine; only report tags and kernel evidence
collection changed. Root remains read-only. Firmware/ID/reset hardware
success still requires a fresh decoded result.

## Confirmed hardware result: GPU2321

2026-10-31, local commit264c9cf kernel and image32a9768f. Fresh console
sweettrial=2321 and independent SWEETMRK kernel build2321/report300..308
agree exactly. This is measured on the device, not the host model:

| Measurement | Result |
| --- | --- |
| GPUEB firmware ready magic | 0x55667788 |
| Shared2MiB reservation PA | 0x7fa30000 |
| Additional20MiB firmware PA | 0x79a00000 |
| INIT_SHARED_MEM reply | 0 |
| POWER_ON reference count | 1 |
| SPM status before / after | 0x3 / 0x7 (second before0x3) |
| GPU_ID | 0xa8620004 |
| GPU_STATUS / AS_PRESENT | 0x100 / 0xff |
| CSF soft-reset completion RAWSTAT | 0x100 |
| POWER_OFF reference count | 0 |
| Final stage / error | 10 / 0 |

The diagnostic releases its single power reference after reset, leaving no
owned reference. This proves platform power-on, accessible Mali registers,
and completed soft reset. It does NOT prove MCU/CSF firmware boot, GPU MMU,
shader execution, Vulkan or Metal acceleration. The two firmware memory
reservations are below XNU RAM0x100000000..0x22e000000 in this measured boot.

GPU2321 did not automatically return to Recovery. User entered Fastboot;
initial macOS platform-tools transport stalled. After the device re-entered
Fastboot, existing tools/fbraw.py successfully downloaded/flashed the known
20,873,216-byte stock prefix (fe6e8fbf) and reboot-recovery returned OKAY.
Recovery then captured fresh evidence, restored the full67,108,864-byte
baseline, and independently verified SHA256
2931647a56039722ea2585990b8ef3b1a2daf4c9b990231879f753049eaf86b1.
Device is back in root Recovery; restore_pending=false; no active runners.
No further boot test is requested by this record. Do not rely on watchdog
scratch to guarantee Recovery; the tested Recovery bypass alone is valid.

Ignored evidence: research/matisse/20261031-gpu/shim2321-trials/gpu-normal/
{after-console.txt,after-marks.bin,gpu-result.json,journal.json} and
shim2321-trials/restore-fbraw-log.txt. Local build PASS;51 host tests PASS;
no GitHub Actions run was required. The next GPU milestone is CSF MCU
firmware memory/page-table preparation and a bounded firmware-ready check,
using the already parsed device firmware; it has not yet been implemented.

## CSF2331 platform snapshots, built but not booted (2026-10-31)

The independent shim now includes the bounded CSF boot path; the preceding
2321-only next-step description is historical. Trials2322..2330 and their
exact outcomes remain in NOTES.md. In2330 the MCU-ready wait timed out with
MCU_STATUS1,JOB_RAW0,version0,AS0 status/fault0. GPUEB INIT0/ON1/OFF0 and
the initial GPU reset completion were observed. These establish neither
firmware readiness nor the MCU's program counter.

`SWEET_CSF_BOOT_TIMEOUT` is a project enum with value-53, not Linux errno.
The report decoder now resolves the return site: a matching CSF report,
top-level stage8 and the observed initial reset identify powered-probe
failure. A negative GPUEB reply retains its separate firmware namespace,
including when the numeric value is also-53. Missing evidence stays
unclassified rather than being attributed to a mailbox failure.

The package vendor_boot v4 DT table contains the335048B FDT with SHA256
783b7fb871087991e97d0d944932981d7b11e207deef2f74d67e8a20cc12ffae,
byte-equal to the extracted LK DTB. GPU/GPUEB/gpufreq/wrapper properties
also match the recorded Recovery live DT. The GPU compatible strings are
`mediatek,mali` and `arm,mali-valhall`; five IRQ names are GPU/MMU/JOB/EVENT/
PWR, with SPI cells544/545/546/547/548. The node already has no `iommus`,
`dma-coherent`,clocks,power-domains or assigned-clock-parents properties.
The shim polls GPU RAW status and does not use Linux IRQ name matching or
Linux DMA/IOMMU allocation. It must not adopt the pasted example IRQs.
The measured shader-present mask0x770017 contains10 set bits; no damaged
core is identified. Firmware backing/page tables are already below4GiB.
L2_READY is GPU+0x160; GPU+0x140 is SHADER_READY. GPU_STATUS bits0/1 are
activity, so their being clear does not establish that a rail is off.

2331 adds an explicit0/1 `platform_snapshot` option, default off. The shim
enables it only after the existing GPUEB/power/L2/AS/IRQ prerequisites pass.
It samples immediately before MCU AUTO and after the bounded wait, before
cleanup. Each snapshot is16 raw u32 words:

| Fields | Addresses |
| --- | --- |
| GPU_STATUS,MCU_CONTROL | GPU+0x34,+0x700 |
| GPU_FAULT_STATUS,address low/high | GPU+0x3c,+0x40,+0x44 |
| JOB_INT_STAT | GPU+0x100c |
| SPM primary/secondary status | 0x1c001f3c,0x1c001f40 |
| MFG power control0..3 | 0x1c001eb8..0x1c001ec4 |
| MFG/MFGSC PLL_CON1 | 0x13fa000c,0x13fa0c0c |
| TOPCKGEN selection,RPC sleep protection | 0x100001f0,0x13f91048 |

Platform addresses were cross-checked against original DT reg-names and
the pinned MT6983 gpufreq module's register readers. The vendor dump
routine itself is not called because it also writes debug selectors.
No PMIC,PLL,clock,domain,descriptor,firmware,coherency or IRQ programming
change accompanies these reads. A successful synthetic C MMIO-write
comparison proves write-sequence isolation only; extra reads can alter
timing and real hardware has not yet been tested with this diagnostic.
PLL programming words do not prove measured frequency or lock.

The report appends136B to the2330 ABI, total440B, tagged55 qwords320..374.
Flags distinguish the before/after samples; invalid flags/reserved words
and missing,duplicate or stale qwords fail decoding. Valid partial sample
flags prevent a success claim. Existing version/IRQ/interface/cleanup
gates remain mandatory for a success claim. Host tests cover
success,timeout and failure before sampling,invalid option values,ABI
publication and exact write isolation. The completed71-test suite passed
in8.446s with sanitizers; the full local kernel build also passed.

Candidate `research/matisse/20261031-gpu/shim2331-platform-ready/
matisse-shim-gpu2331.img` is26714112B,SHA256
e1920561234a68e4472b91ffa2e724385940c6f7c441fc237b80b1a3b4746ad2.
Independent component/source/frozen-object/PIC/ABI verification passed.
Firmware/memory objects and arena PA0x40076000 remain identical to2330.
No2331 hardware trial is authorized or performed. A read-only Recovery
preflight again confirmed the original full64MiB boot_a SHA2562931647a
through86b1. The prepared one-shot runner requires specific image approval
before its write branch; automatic Recovery remains unverified, and full
original restoration with an independent hash is part of any approved trial.

## CSF2331 measured trial and restoration (2026-10-31)

The user subsequently authorized exactly one normal2331 trial and complete
original restoration. Runner session62578 exited0. The candidate's full
boot_a readback matched predicted SHA256
efa6122218e60edd6b515281be3a2b8319ab3910b329a99c3cabee2b5ec799ff.
The device reached Fastboot after82.54s. One persistent raw USB session
restored the stock prefix and rebooted Recovery; Recovery then restored
all67108864B original boot_a. A separate independent device/slot/root/
Recovery/geometry check confirmed the full original SHA256
2931647a56039722ea2585990b8ef3b1a2daf4c9b990231879f753049eaf86b1.
No restore is pending and the one-trial authorization is consumed.

Fresh marks identify2331 and contain all55 CSF qwords; they match the
captured userdata tail exactly. Before-capture marks/tail equal the previous
2330 after-capture,stale2330 evidence is rejected as2331,and the new console
independently names gpu2331/sweettrial2331. Every common GPU/CSF field
matches2330. Both new snapshots were sampled,with these raw measurements:

| Measurement | Before AUTO | After wait,before cleanup |
| --- | --- | --- |
| GPU_STATUS | 0x100 | 0x101 |
| MCU_CONTROL | 0 | 2 |
| GPU_FAULT_STATUS/address | 0 | 0 |
| JOB_INT_STAT | 0 | 0 |
| SPM status primary/secondary | 0xf / 0xf | 0xf / 0xf |
| MFG power0..3 | c000224d/c0000112/c0000112/1112 | same |
| MFG/MFGSC PLL_CON1 | 82177627/832013b1 | same |
| TOPCKGEN_SEL | ff030000 | same |
| RPC_SLP_PROTECT | fff0fff0 | same |

MCU_STATUS remains1,version0,JOB_RAW0,MMU_RAW0,AS0 status/fault0,L2_READY1.
The CSF stage4 wait returns the local-53 timeout. Disable also times out,
MCU status remains1,and cleanup reset does not complete (RAW0x200). GPUEB
INIT0/ON1/OFF0 and the initial GPU reset0x100 remain independently observed.
The CSF firmware handshake has not succeeded.

Offline comparison verifies gpufreq_mt6983.c/.h against original pinned
commit270b84910b941bf75490fccdb5fb2b3021dd7cbf. Under those definitions,
CLK_CFG30 bits16/17 are both MAIN selections; GPU_STATUS ACTIVE is set and
PROTM is clear. This does not measure actual clock frequency,PLL lock or
MCU instruction fetch. The reference uses PDCv2 and conditionally skips
manual MFG2..18 power-on; it also contains fake SPM power-control APIs.
Thus shader-domain status bits alone are insufficient to diagnose a rail
failure. No PDC CG/ST state or EMI-path state was captured. The next offline
comparison should examine those vendor/binary initialization paths before
selecting another diagnostic. No direct rail/PLL/clock writes are selected.

Evidence stays ignored under `research/matisse/20261031-gpu/
shim2331-platform-trials/gpu-normal/`:fresh marks/tail/console,decoded report,
comparison-2330-2331.json,platform-field-analysis.json,journal.json and
independent-post-restore.txt. No new build,CI run or push occurred for this
trial; implementation8ea682a and build handoff5862456 remain applicable.
