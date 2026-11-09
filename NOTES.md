# iOS 16 on sweet (Redmi Note 10 Pro, SM7150) - working notes
## >>> ACTIVE 2026-11-09: 2442 GPU SERVICE + INTERACTIVE UI VERIFIED <<<

2442 fresh trial/kernel2442, changed log tail, three native compute shaders
rc0/stage7/witness2436c5f1, service registered and nine status samples with
ready1/submits3/failures0/MCU1. User saw UI and working swipe updates. This is
resident GPU coexisting with normal UI; UI is NOT yet hardware rendered.
Fastboot170.07s. Full64MiB boot_a restored; independent Recovery SHA256
2931647a56039722ea2585990b8ef3b1a2daf4c9b990231879f753049eaf86b1.
No restore pending. Evidence:20261109-resident-gpu/resident2442-verified.json
and observation2442.json.0211/0212 restore normal startup and fix high-DRAM
cache-address overflow (direct causality of that fix remains unproven).

0213 now enables sweetgles=2 through exec/AMFI90/IOSurface gates; previously
only1 was recognized. Both modes1/2 and unsupported3 tested under ASan/UBSan.
Full local2443 kernel build exit0, no boot yet. Hardware Mesa rebuild and
read-only current-root snapshot underway under20261109-panfrost. No library
installation yet. Need deploy additive /usr/local/sweet-gpu and hardware probe,
verify GPU pixel checks, then backboardd sweetgles=2 with glcopy=1. This keeps
GPU shader/raster work; glcopy is IOSurface presentation copy, not softpipe.
Hardware profile refuses software fallback. Do not claim hardware UI until
renderer, actual CSF submits and completed frames are verified together.

Completed source commits:9f6c6cb (startup/pmap/mode2), b8b99be (hardware Mesa
transport/probe).9f6c6cb pushed to fork. gh xnu.yml dispatch HTTP422 Actions
disabled, no new CI ID.2443 local full kernel4545b48c2232e824f1c6adbd372b5569fca12d80fc265ee357a3274c5709ee2e;
image62af52351380094ae4c2d6afaa5fb31881fa19b2ddf6ab95de44f62a65aacac7,
26734592B. Image uses launchdsuffix=panfrost-probe and sweetgles=2,
sweetgputrace=1, root writable for journal replay. Preflight passed.
Current16GiB root snapshot verified against device128MiB chunk hashes;
local HFS clone has additive GPU libraries/probe and replacement opt-in loader.
fsck_hfs -fn PASS. Block delta preparation in progress, no device root writes
as of this checkpoint.2443 runner not started yet; inspect its journal first.
UPDATE:95/95 device delta preimages matched and all95 writes readback verified,
16834560 bytes. No root write pending. New root expected SHA256e932dddd7b8dec5be4d3b609e7cd26b6aa21559fcab417e9dba1db24d165d2d4.
2443 hardware probe runner NOW STARTED; follow its journal to full boot_a
restoration before device actions. Canonical builder also aligns Mesa's VA
range to the kernel128MiB minimum; rebuilt output installed. Seven host tests
PASS. Kernel/image exact hashes above; no2443 hardware result yet.

## >>> PREVIOUS 2026-11-09: 2442 NORMAL GPU SERVICE + UI BOOT TRIAL <<<

2440 and2441 completed with fresh console and fully restored boot_a.2441
returned Fastboot97.87s despite180s window; user observed XNU console. No
VM checkpoint survived; this is NOT proof that GPU was absent.2437 had
three real compute successes and service registration;2440/2441 registered
only after the later VM/logging wait. Both diagnostic roots were read-only.
2442 gates VM stress behind sweetgpuvmtest=1 (off normally), restores service
registration after three resident submissions and the normal writable UI root.
Kernel67569933106d2ee62da6d96df075b48a54d630d8b332962968db36e160c732fa,
image0bd13233af24aef9bff5eb93f46475e66c4cdbb0fc8a29bc15e163afd9c83be3,
26734592B. Existing full local build passed; canonical driver equals built
source,0211/0212 reverse-check pass. Four ASan/UBSan/runtime/transport tests
PASS.0211 fixes a verified32-bit physical-page shift overflow; its effect on
the observed boot stall is still unproven. No Mesa deployment/root edit yet.
2442 runner started; inspect shim2442-ui/gpu-normal/journal.json before any
device action. Full boot_a restore required. Preflight independently verified
2931647a56039722ea2585990b8ef3b1a2daf4c9b990231879f753049eaf86b1.
Artifacts:research/matisse/20261109-resident-gpu/. Hardware UI NOT verified.

## >>> PREVIOUS 2026-11-09: 2439 REACHES XNU; 2440 DURABLE VM CHECKPOINTS <<<

2439 consumed and fully restored, independent Recovery boot_a SHA256
2931647a56039722ea2585990b8ef3b1a2daf4c9b990231879f753049eaf86b1 verified.
Fresh kernel/trial2439, changed tail, three native GPU compute successes,
launchd starts. Exactly one persistent flush, no VM-stage message survived.
Thus XNU DOES boot; precise VM regression is still unknown (not shim failure).
Evidence:20261109-resident-gpu/vm2439-verified.json and shim2439-vm/gpu-normal.
2440 adds synchronous UFS-backed allocation/MMU checkpoints gated by
sweetgputrace=1, replacing unproven sleep-based flushing. Actual flush code
passes ASan/UBSan bounds/ring-wrap/write-failure/cache-sync-failure tests;
existing runtime/transport tests pass. Full local kernel build exit0,
0210 reverse application verified. GitHub Actions dispatch again422 disabled;
no new CI run. Image cf4e76ab82827239b92a3e81372240e98d39d0c4f2d918f7afa8ab22e42a5ddc,
kernel30ad8c8f8ddaa9f7d7d17053c52e700ebf9b88c2b0182bad1b4d326481a90dbd.
2440 runner prepared; inspect its journal before device actions. No root edits.
Hardware Mesa remains built/not installed; existing userland changes retained.

## >>> PREVIOUS 2026-11-09: 2438 STALE CAPTURE; 2439 DIAGNOSTIC BUILD <<<

2438 returned Fastboot138.50s, but before/after tail hashes are IDENTICAL and
kernel marks still2437. No fresh XNU evidence:2438 VM test is NOT verified;
do not infer which VM operation failed. Full64MiB boot_a restored and independently
verified2931647a...86b1. Runner consumed; Recovery/no restoration pending.
2439 built/preflight next: delay allocating VM/BOs until the persistent log has actually
flushed once, log allocation/map stages, and explicitly opt out of a system
IOMMU mapper (the GPU owns its translation). Local2438 build was valid; the
failure point is not yet observed. No root modifications.
Hardware Mesa v10+Darwin Panthor transport now cross-built/codesigned under
20261109-panfrost/out; hardware REQUIRED, no softpipe fallback. Actual transport
ASan/UBSan test verifies unsignalled/future fences, failed submit does not signal,
IOKit BO mapping and heap creation. It is NOT tested on phone yet.
2439 imagec7280d252a0bf0cad5687755047046a1ceccdea61c14e36418038f92bbc2c48d,26734592B. Kernel8ae33a1a6c2d8a817f1e74975a3f620c922f69296534ada9e108caac3e546d5e,
16768616B. Full local build exit0,0209 patch replay pass. New one-shot2439
runner prepared/not run yet. User observes shim starts but XNU does not; this
corroborates the absent fresh persistent evidence, not a precise crash site.
Uncommitted build tool/transport test/source pending final review/commit.

## >>> PREVIOUS 2026-11-09: 2438 BO/VM/PERSISTENT CSF TEST READY <<<

2437 resident ownership is verified below.2438 now adds per-client AS/root,
IOBuffer BOs, GPU mappings, persistent CSF groups and synchronous CALL/fence
submissions. Native selftest makes70 shader submissions, remaps the same VA
from BO1 to BO2 at35, and wraps the4KiB ring twice. No Mesa hardware result yet.
Local full kernel build-v2 exit0; kernel2eafef5757ed6db22e822ed47b091d7d56645b04b301ee192945c1923bf2e706,
16768544B; actual runtime_submit symbol checked. Image4a5003dea27ae084ab6a3c4f8440d9e94fd2d79127fb21a810de7b023f134e11,26734592B.
6 targeted tests PASS including actual runtime C with100 interpreted submissions,
register persistence, ring wraps, timeout/fault paths under ASan/UBSan.
0208 reverse/replay checked. New shim2438-vm-run-once.py prepared, not run yet.
Check its gpu-normal/journal.json before device actions. Device Recovery,2437
fully restored; no root changes. Mesa hardware build in progress separately:
tools/build-sweet-panfrost.py + userland/sweet-panthor-drm.c, hardware required;
not built/tested yet. Uses G710 v10, not HakiOS's v7/JM transport.

## >>> PREVIOUS 2026-11-09: 2437 RESIDENT XNU GPU VERIFIED <<<

Source1960662.2437 normal boot retained MCU/power successfully. Native XNU
SweetGPU submitted THREE real compute shaders: all rc0/stage7,
shader witness2436c5f1, insert=extract192, AS fault0. IOService registered;
periodic status twice confirmed ready1/submits3/failures0/MCU1.
Fresh trial/kernel2437, changed persistent console verified. Hardware execution
now works inside XNU, not only in the shim. UI is still NOT GPU accelerated.
Resident evidence:20261109-resident-gpu/resident2437-verified.json.
Fastboot81.31s; runner consumed, full64MiB boot_a restored and independently
rehashed2931647a56039722ea2585990b8ef3b1a2daf4c9b990231879f753049eaf86b1.
Device Recovery; no restore pending/no active runner/root edit.
Next implement isolated application VM/BO and persistent CSF queue, expose
Panfrost/Panthor transport and build hardware Mesa v10; then GLES triangle/UI.
Origin push denied403; fork push1960662 succeeded. gh workflow dispatch on
Jinsens/ios-sweet returned422 Actions disabled; no CI run ID. Local full build
and actual native symbols verified as detailed below. Legacy GPU report does
not accept2437; resident evidence validates raw SWEETMRK identity and console.

## >>> PREVIOUS 2026-11-09: 2437 RESIDENT GPU BUILT; HARDWARE TEST NEXT <<<

User requires GPU-accelerated system UI; no softpipe optimization. Resident
shim handoff retains proven MCU, firmware arena and power. Native SweetGPU
IOService runs three compute submissions after XNU starts. This is the next
transport milestone, NOT hardware-rendered UI yet. No BO/VM/Mesa bridge yet.
0207 installs canonical native driver/queue headers, marks kernel2437.
Local full build exit0; actual SweetGPUStart/sweet_csf_queue_probe symbols
verified. Kernel 2f429784a83dd0bb052c462be5e5d11c61357c5eef2c4b8fc2985947593bdd0d, 16749976B.
Image daf358ccebab22680e4f42063d03a483a6e0f4f16336fd56c03837b3617daab8, 26726400B.
126 host tests passed (4 skipped), including repeated submissions and power/
runtime retention;12-file patch reverse/replay and canonical source parity pass.
Build log build2437-native-v3.log is valid; earlier build2437.log/native.log
were unchanged old builds, native-v2 failed on an include now corrected.
Artifacts: research/matisse/20261109-resident-gpu/.
New one-shot shim2437-resident-run-once.py prepared, not yet run. Device Recovery;
no restoration pending. Check shim2437-resident/gpu-normal/journal.json before
any device action. Test requires normal boot and sweetgpu=1. Full boot_a
backup must be restored/verified; old GPU report reset predicate is inapplicable.
Native selector1 copies report under the submit lock to avoid cross-call races.
CI workflow state active as of this turn; dispatch still to be attempted.

## >>> PREVIOUS 2026-11-09: G710 CSF QUEUE AND COMPUTE SHADER VERIFIED <<<

User explicitly requires direct G710 hardware integration, not softpipe tuning.
GLES frontend/system rendering already works;2432 slowness was glDrawElements.
No low-resolution or software optimization changes were made. Next layers are
resident XNU KMD/BO/VM/queues/fences and Mesa v10 transport. Shader execution
is now verified; do not restart MCU bring-up or softpipe optimization.

2435 SUCCESS: fresh trial2435/kernel2431. CSG_REQ0x11/ACK0x10000011,
CS_REQ0x511/ACK0x11, insert=extract=32, witness deadbeef ->2433c5f1,
10 polls, fault/fatal/AS fault0, MMU_RAW0x20000(request completion only).
Group terminated, MCU disabled0, reset completed, cleanup_error0. This is
hardware COMMAND execution, not shader rendering or accelerated UI.
Source560f3d0; image30decd7848f0c465a153e73454dfae6ff2a0c59faa09d601e82010f98f21cfc1.
Fastboot79.30s; full boot_a restored and independently verified to
2931647a56039722ea2585990b8ef3b1a2daf4c9b990231879f753049eaf86b1.
All2433-2436 trials completed. Device Recovery; no runner active and no restore pending.
Raw evidence20261109-gpu/shim2435-queue/gpu-normal/.

Earlier2433 aborted on MMU bit17 wrongly treated as fault (fixed2e5c0eb).
2434 then showed real AS0 fault bit0, CSG_ACK0x11/CS_ACK0/extract0.
Moving queue IO from08000000 to06000000 fixed that in2435. Panthor MCU shared
window is[04000000,08000000). AS0 fault-address relay added for later errors.
2433/2434 also fully restored. Raw logs under shim2433-queue/shim2434-queue.

2436 SUCCESS: fresh trial2436/kernel2431. Compute-only CS stream192B, real four-instruction Valhall shader
writes2436c5f1 into a separate witness; final SYNC_SET writes another location.
Witness deadbeef ->2436c5f1, insert=extract=192 in18 polls; CS fault/fatal and AS fault0,
MMU0x20000 completion only. CSG/CS ACKs match, terminated, MCU disabled,
reset completed, cleanup_error0. Hardware compute_shader_verified=true.
One executable read-only shader page; other data pages remain XN. Word encoding
matches Mesa25.0.7 valhall/asm.py.103 tests PASS incl actual C ASan/UBSan,
command/shader interpreter and rejecting queue-only completion as shader proof.
Local shim build exit0. Imaged5468945fe4eb1df16d7682a474308cdbd6213b10c957662a0e198afbaf0d435,
26718208B; output20261109-gpu/shim2436-compute-ready/manifest.json.
Kernel2431 unchanged20a6a410...19146d, mark2431. No kernel rebuild/new CI.
Source8faebd9. Runner shim2436-compute-run-once.py completed and consumed;
Fastboot83.45s, full boot_a restored and independently rehashed2931647a...86b1.
Fresh console/changed tail/image/mark independently checked for ALL4 trials.
Evidence20261109-gpu/queue-compute-verified.json and per-trial directories. Do not rerun consumed trial runners. No pending root filesystem edit.

Existing sweet_csf_boot resets and sweet_gpu_boot releases power on return;
these shim probes are not a resident driver. Queue module is portable, with
shared root for AS0/AS1 only in this exclusive test. Separate application VM
and persistent XNU ownership still required. Mesa25 pan_csf.c supports v10;
HakiOS Darwin patch is v7/JM and cannot substitute for the needed CSF transport.
Execution details and the concrete remaining driver work: docs/matisse-csf-execution.md.

## >>> PREVIOUS 2026-11-09: 2431 SYSTEM GLES VERIFIED; INVESTIGATING LATENCY <<<

2431 completed with fresh console/trial/kernel identity. One bridge/context,
37 frame records, 26 with draws into known IOSurface targets; zero recorded
shader/link/dispatch/GL errors and no observed backboardd crash. User saw
a normal lock screen and advancing clock, but swipes and keys had no visible
response. This verifies software GLES UI rendering, NOT GPU acceleration.
55 touch and 26 key records reached HID; display off/on requests also occurred.
Frame-duration median178745us, max19365239us; these are wall intervals from
first draw to flush and do not alone prove all time was spent in GL.
Copy-out takes only a few milliseconds in the long frames. Existing HakiOS
boot option glslow=US can time individual calls without installing new files.
Touch logs use normalized1080x2400 coordinates; patch0111 explicitly maps
them to the panel/logical dimensions, so the log scale alone is not a bug.

Fastboot observed201.15s; runner completed full boot_a restoration and
Recovery independently rehashed it again this turn:
2931647a56039722ea2585990b8ef3b1a2daf4c9b990231879f753049eaf86b1.
No runner active and no restoration pending. Source milestone7591fa4;
local kernel20a6a41098a02309b15ec8dc1a36ef137b0b5a4feb038096501e4af93719146d,
image02319ad5146e1ec83051f1b4afd16ff60a80f4dd042fbacdbf34912b3652615f.
No new CI run; prior dispatch rejected because Actions is disabled.
Raw evidence: research/matisse/20261109-gles-inject/result2431.json,
observation2431.json and gles2431-run/gpu-normal/.
Next: prepare2432 using the same kernel/root and glslow diagnostics,
verify image/preflight, then run and recover logs/full boot_a as before.
2432 image built/preflight passed: b94772799dc3d4fee67e50bbfb89938891cd69b1f553efc4e60ac7cbdb1cadca, 7073792B. Same2431 kernel/root; adds glslow=100000 touch_lat=1. Baseline shim reproduced byte-for-byte. Starting runner run-gles2432.py next; inspect gles2432-run/gpu-normal/journal.json before any device action. Full boot_a restoration required after trial. No kernel rebuild or CI run.

## >>> PREVIOUS 2026-11-09: 2431 IOSURFACE FIX BUILT; PREFLIGHT NEXT <<<

0206 negotiates new XR/b3a8 targets as BGRA when sweetgles=1, refuses
unsupported wrap shortcuts6/7, pins IOSurfaceAddress backing with read-only
fallback and balanced complete(), fixes plane rowBytes to+0x10. No root edit.
2430 crash was symbolicated to IOSurfaceClientGetBulkAttachments (NULL shared
page after fake selector6 success). HakiOS does the same XR negotiation and
refusal;20H392 disassembly confirms plane row ABI.
15 targeted tests pass including actual patched C++ ASan/UBSan geometry,
read-only pin fallback/failure, exact borrowed length, ABI and stale captures.
Local full kernel build exit0: kernel20a6a410...19146d, mark2431; image
02319ad5146e1ec83051f1b4afd16ff60a80f4dd042fbacdbf34912b3652615f.
Baseline shim reproduced byte-for-byte; loader rebuilt for16727184B.
No2431 boot yet.2430 full boot_a restored/verified. No restoration pending.

## >>> PREVIOUS 2026-11-09: 2430 INJECTION WORKS; B3A8 TARGET REJECTED <<<

2430 captured FRESH trial2430/kernel mark2429;270850 console bytes/flush111.
Exec injection8, AMFI90 successes16, loader/8 EAGL methods installed8;
7 ES3.1 softpipe contexts. First native1440x3200 display IOSurface is b3a8,
2 planes, and HakiOS my_attachImage rejects it (only BGRA/0, nonplanar).
Each first draw gets GL_INVALID_FRAMEBUFFER_OPERATION0x506 then backboardd
SIGSEGV at FAR0x30. Seven observed crashes; no completed GLES frame.
User saw continuously scrolling console and entered Fastboot at341.74s.
Full boot_a restored; independent Recovery SHA matches2931647a...86b1.
No runner active/restore pending. Packaging6ee5272 worked; no new kernel/CI.
Next: symbolicate the first backboardd crash, inspect actual b3a8 planes and
format negotiation; implement the smallest correct surface/GLES adaptation.
Do not reinterpret b3a8 as linear BGRA without proving its layout.
Evidence: research/matisse/20261109-gles-inject/result2430.json and
 gles2430-run/gpu-normal/after-console.txt. Offline evidence tool now rejects
unchanged console, wrong trial/build, and missing display draws (7 tests pass).

## >>> PREVIOUS 2026-11-09: 2429 INVALID TRIAL RESTORED; REBUILD LOADER FOR2430 <<<

2429 user saw REDMI only. Before/after persistent tail hashes IDENTICAL
817744f3...f4aa; marks still2316, bootargs still2428. These are stale logs,
NOT new-kernel evidence. Packing bug identified: compiled shim loader expects
16726016B, new payload16726912B (+896); embedded_payload rejects mismatch.
Do not conclude AMFI/GLES failed. 188.78s to Fastboot; runner restored full
boot_a and verified2931647a...86b1, pending=false. No runner active.

Fix: rebuild loader.o against actual payload length using frozen2313 shim
objects, link; first regenerate the old loader/prefix byte-identical to2428.
2430 will use the SAME2429 kernel e1c94338...44f8ba (mark2429), new trial arg.
No root change. 0205 source7a65b31 and seven tests already pass, full local
build exit0. CI disabled HTTP422; no CI run. Next image/preflight/boot,
verify fresh identity BEFORE interpreting any backboardd output, restore.

## >>> PREVIOUS 2026-11-09: 2428 RESTORED; DYLD INJECTION GAP IDENTIFIED <<<

2428 completed: user observed lock/home screen. 169.12s to Fastboot; full
boot_a restored by runner, independently rehashed in Recovery to
2931647a56039722ea2585990b8ef3b1a2daf4c9b990231879f753049eaf86b1.
restore_pending=false, no runner active. Fresh console290916B/flush85,
bootargs identify2428; backboardd+SpringBoard surfaces/input worked. No
SWEET GLES or redwood-gl messages: UI is NOT evidence of new GLES backend.
2427 standalone softpipe triangle/EAGL pixel results remain passed.

Two concrete source findings: current sweet_amfi.c registers "SWEET AMFI"
without mpo_policy_syscall, but 20H392 dyld calls "AMFI" request90, with
{uint64 input, user_addr_t output}; errors zero its permissions. HakiOS
kern_minimac.c implements that ABI; its exec patch also explicitly states
launchd filters DYLD_* from job dictionaries and injects at exec instead.
Root2428 job/cache and loader were present (offline hashes checked).

Preparing0205 patch: sweetgles=1 adds fixed loader env to64-bit backboardd
at exec and permits only dyld path/print vars (0x12) for that process.
2429 image3b9192790db4128708daa89ae6a53d1c6b1572b393ea8b8417dc86f6427a57b8
7073792B, kernele1c94338...44f8ba, source7a65b31. Local full build exit0,
image audit/preflight pass; seven targeted ASan/UBSan tests PASS.
Actions dispatch rejected HTTP422 (repository disabled); local CLT full
build passed, log build2429.log. No new CI run. Repository validator: Python syntax passes; existing0085 numbering gap
and six shell CRLF syntax failures remain (unmodified files).
2429 runner STARTED: run2429.log, gles2429-run/gpu-normal/journal.json.
Do not rerun; follow full boot_a restoration to completion. Libraries/root
unchanged. Read journal for actual pending state before any device action.
Raw evidence and local preimages: research/matisse/20261109-gles-inject/.

## >>> PREVIOUS 2026-11-09: GLES2427 PASSED; BACKBOARDD2428 BOOT RUNNING <<<

2427 unambiguously passed: Mesa softpipe / OpenGL ES3.1 Mesa25.0.7,
2 GLSL shaders,4 draws,8 triangle/background/blend pixels plus EAGL macro
pixel64,128,191,255/error0 (9 checks).4 IOSurface swaps at1440x3200.
User directly observed blue background with red/green triangle. Fresh kernel
FBIMG captures3 frames after copying; renderer readback times13766,7590,10345,
7527us at256x256 (NOT full-resolution performance). No GPU acceleration.
8/8 EAGL methods installed; API3 context and macro table verified on20H392.
This is newly exercised Mesa userspace rendering, separate from old CA::OGL::SW.

Fastboot observed125.91s; full boot_a restored and hash verified
2931647a56039722ea2585990b8ef3b1a2daf4c9b990231879f753049eaf86b1.
No restore pending/no runner active. Probe image0f1a4f89...dd3fc/kernel2316
unchanged; no CI. result2427.json and complete logs in20261109-hakios/.
Source milestone7aebab2; retained full root before/after and delta preimages.

2428 prepared: userland/gles-loader.c only enables EAGL when sweetgles=1.
Backboardd launchd job/cache gain DYLD_INSERT_LIBRARIES pointing to the tiny
loader. Offline HFS fsck passes, UI delta16 runs/892928B, preimagecb39abd0...d4751,
postimage56f45505...8553. Applied root-delta-ui2:16/16 reads matched,16/16 writes readback verified,
no pending root writes, final root SHA05ec8ccdf3568e1e260439dff95d16b5c6b4bfb78ab933b65d087fef255c338a.
2428 runner started, restore pending in gles2428-run/gpu-normal/journal.json.
Do not rerun; wait full boot_a restore verification.
2428 image1b3de2800f914d2e55369dd8df2789dc423930545c567b67fc6051eb05fa0f18,
known2316 kernel,2317 native/touch/keys settings plus sweetgles/glcopy/glwait.
run-gles2428.py NOW CONSUMED; do not rerun. Default boot leaves bridge off.
457 GL exported dispatch stubs checked against20H392; offsets normalized to
context slot(+0x20) all match HakiOS, raw audit saved locally.

Next: boot-arg-gated GLES loader in backboardd, EnvironmentVariables in its
launchd job, test actual CoreAnimation UI. Keep ordinary software UI available.
G710 hardware still needs resident CSF KMD/BO/VM/queues/fences; do not describe
softpipe as GPU acceleration. Current MCU/global2426 remains verified below.

## >>> PREVIOUS 2026-11-09: GLES2427 BOOT RUNNING; ROOT DELTA VERIFIED <<<

GLES userspace buildf52013f plus EAGL API3 test completed. Mesa25.0.7 softpipe,
HakiOS common mtk620c775...7740, device84b0252...02f4; source manifest under
research/matisse/20261109-hakios/. Selected native GLES as first path; PanVK
is a later Vulkan path. G52/v7/JM hardware code cannot be used for G710/CSF.
Probe executes2 shaders/4 draws/8 pixel checks/4 IOSurface swaps and then
EAGL API3 macro-table readback (9th pixel check). No hardware claim.
Both iOS dylibs and probe cross-compiled/codesigned; display ASan/UBSan test
passed. No new kernel/CI. Kernel2316 e25c06b0...857269 reused.

Live16GiB root exported SHA132a4cbe0f654073208dd2a9c46638b02643d1e53f57119b1f75716d582eab01.
APFS clone native HFS journal replay +3 new files, no existing file content
edits. Offline fsck_hfs -fn exit0, volume OK. Edited image SHA
cb39abd0b0f1b78d627cc845056617406d472bf066fc575dffa7536bec3d4751.
Delta184 coalesced runs/86568960B, includes verified unchanged gaps and native
journal/metadata updates. Complete preimages retained in root-delta-gles-packed/.
184/184 delta runs applied and every readback matched. Root write_pending=false.
2427 runner started: run2427.log and gles2427-run/gpu-normal/journal.json.
BOOT_A RESTORATION PENDING until that journal verifies full original hash.

2427 image0f1a4f89709354ab2f9310eca2165bfff4d7df750d3b95751cc9fee7865dd3fc,
7073792B; launchdsuffix=gles-probe selects newly added
/usr/appleinternal/sbin/launchd.gles-probe. rootrw=0/ufsrw=1: VFS read-only,
persistent tail log writable. Device Recovery, full boot_a preflight verified
2931647a56039722ea2585990b8ef3b1a2daf4c9b990231879f753049eaf86b1.
Runner run-gles2427.py NOW CONSUMED; do not rerun; boot recovery mode (UI kernel,
no CSF probe). Always restore full boot_a; follow journal, never blindly rerun.
Next: apply verified additive delta, run2427, inspect pixels/FBIMG/EAGL ABI,
then integrate opt-in EAGL into backboardd. MCU/global2426 remains verified.

## >>> PREVIOUS 2026-11-09: MCU/GLOBAL COMPLETE; USER REQUESTS HAKIOS USERSPACE RENDERING <<<

User now requests github.com/oosexgang/hakios-mt6768 rendering approach,
advance to userspace rendering and hardware acceleration if possible.
Next: inspect/pin that reference and the current userland/display baseline.

MCU baseline2426 PASSED: unmodified firmware de22d2fc...7229a, fresh JOB_IRQ
0x80000000, GLB_VERSION0x01010000, input0x04002000/output0x04003000,
groups8/stride160. Global REQ0x40e ACK0 ->0x40e in10 polls; flags7/error0.
CSF stage7/error0, cleanup_error0/reset_completed1; strict firmware and global
verification true. Image3f9e3f8f3948e71ec65242362fde544d656622ee5c2da6db13ff5b9381414792.
Source0dc9811; c01dcbea...d5ea kernel reused with persistent mark0x2407; no CI.

Seven hardware boots this work session:2422 still failed after far relocation;
2423 passed twice;2424 retained original PDC reads and passed;2425 stock fw
booted;2426 global handshake passed; exact original2420 reverse control again
failed at marker2 with odd store absent/cleanup timeout (fastboot84.40s).
Thus successful new path is repeatable and reverse control rejects simple
persistent warm-state explanation. Minimal EMI read set vs timing still open.
129 combined tests passed. Details: docs/matisse-gpu-20261109.md.

ALL trials restored full boot_a. Independent final Recovery check (root,
matisse,_a,recovery) verified
2931647a56039722ea2585990b8ef3b1a2daf4c9b990231879f753049eaf86b1.
No restore pending/no runner active. Raw logs/images under ignored
research/matisse/20261109-gpu/; final-recovery-verification.json has no serial.
Current GPU path is a bounded shim probe; scheduler/rendering not yet implemented.

## >>> PREVIOUS 2026-11-09: 2426 GLOBAL HANDSHAKE TRIAL <<<

2425 firmware boot is verified (details below).2426 enables global-init and
relays20 actual handshake words into the existing784-byte report; no kernel
build needed. Firmware remains byte-identical de22d2fc...7229a; EMI reads kept.
Image3f9e3f8f3948e71ec65242362fde544d656622ee5c2da6db13ff5b9381414792,
77 relevant tests pass including ACK mismatch/timeout and firmware-not-ready.
Recovery preflight passed. Trial journal shim2426-global/gpu-normal/journal.json,
log research/matisse/20261109-gpu/run2426.log. Restore full boot_a after boot.
No rendering/scheduler implemented yet. Do not claim global ACK until captured.

## >>> PREVIOUS 2026-11-09: 2425 REAL VENDOR FIRMWARE BOOT VERIFIED <<<

2425 a1fa8065544fa2b5c1f7bbc06288670a2a98ddb09ca60c960fb2f47b9f07c58f
booted UNMODIFIED firmware de22d2fc...7229a. Fresh JOB IRQ0x80000000,
GLB_VERSION0x01010000, input0x04002000/output0x04003000, groups8/stride160,
MMU_RAW0/AS_FAULT0. CSF stage7/error0/firmware_ready1, cleanup_error0 and
reset_completed1. Platform stage10/error0; strict decoder verifies firmware
boot. This is beyond the diagnostic MCU program. Full boot_a restored and
verified; no restoration pending. Fastboot80.22s. Raw run2425.log and
shim2425-stock-fw-emi/gpu-normal. Source83fd385 (+ comment/doc corrections).
127 combined tests pass. No CI/new kernel, same c01dcbea...d5ea mark0x2407.

Next2426: enable existing global-init REQ/ACK protocol and relay its evidence
in the existing784-byte report so persistent logs contain actual handshake
values. Keep unmodified firmware and eight EMI reads. Minimal EMI read set
and timing-vs-read cause are still open. GPU rendering is not implemented.

## >>> PREVIOUS 2026-11-09: 2423 BREAKTHROUGH — ODD STORE AND READ COMPLETE <<<

2423 image c43e902e027a3e4f8eee17d1773eefae0a4969831f175f6266336d356b330e1a
ran. MCU marker4, CPU control0x2420a400 and odd0x2420a200: first controlled
store/read witness success. It changes only eight PDC/SLC read addresses to
vendor EMI/GALS/idle diagnostic reads; MCU bytecode, low arena, page attrs
and power protocol unchanged. No firmware-ready claim: diagnostic loop only.
Four GALS words all0x01007514 before/after; nth/sth idle_en1=0x10000618,
idle_en0=0xc40000e8 before/after. Full boot_a restored/verified, no pending
restore. Fastboot96.66s. New raw evidence in shim2423-emi/gpu-normal.
Next: repeat2423, then isolate added reads versus removed PDC reads and timing;
do not add clock writes now that this read-only change passed.
Kernel c01dcbea...d5ea unchanged; no CI. 74 decoder tests plus MMIO-model pass.
2422 code checkpoint3590109. Update docs and commit2423 milestone next.

## >>> PREVIOUS 2026-11-09: 2422 RESTORED — FAR ARENA HAS SAME STORE STALL <<<

2422 ran image d11fbb7ba449601d4eb476e3ea2cf57d68b3e070b70655f457f4c2a378c38d49.
AS root readback0x45000000, firmware PA0x4512d000, shared target0x45099200.
Marker2; CPU +0x400 became0x2420a400; +0x200 retained0x24205200;
MCU_STATUS1 and AS_FAULT0. Whole arena relocation did not fix the stall.
Fastboot113.28s; fresh captures; full boot_a restored/verified to
2931647a56039722ea2585990b8ef3b1a2daf4c9b990231879f753049eaf86b1.
No restore pending. 122 tests pass including assembled/Unicorn ladder,
boot-model and evidence tests. Kernel unchanged c01dcbea...d5ea; no CI run.

2421 also completed/restored: L2_CONFIG0x07130000 ->0x08130000 verified,
same marker2 and CPU store observations. See docs/matisse-gpu-20261109.md.
Do not repeat the old claim that soft reset never completes:2408's pre-MCU
soft reset completed, only post-stall cleanup reset times out.
Next: read vendor EMI/GALS diagnostic words before/after MCU, retain the
CPU store witness. This is new evidence below the MFG top dispatch block;
we do not yet know which interconnect component stalls the request.
Raw images/runners/captures: research/matisse/20261109-gpu/.

## >>> PREVIOUS 2026-11-09: 2421 L2 HASH TEST RUNNING <<<

2421 image 8e31785b853a18e736d5898af06063042abac4600b0083aa381b7adeb9a6dc9f
passed build, 12 sanitizer boot-model tests, two assembled/Unicorn ladder tests
and Recovery preflight. It keeps 2420's MCU program and shared samples, changes
L2_CONFIG bits31:24 to 8 before L2 power-on and requires readback. The two seed
label slots now carry L2_CONFIG before/after (decoder labels it separately).
Trial running; see research/matisse/20261109-gpu/run2421.log and
shim2421-l2hash8/gpu-normal/journal.json. Restore full boot_a before stopping.

## >>> PREVIOUS 2026-11-09: 2420 RAN — ODD STORE NOT CPU-VISIBLE, DSB DOES NOT COMPLETE <<<

2420 completed and restored full boot_a; independent Recovery SHA256 matches
2931647a56039722ea2585990b8ef3b1a2daf4c9b990231879f753049eaf86b1.
No restoration pending. Fastboot arrived at 82.26 s. Fresh marks changed from
the previous capture. marker=2, output=0x2420a400, MCU_STATUS=1, AS_FAULT=0.
CPU before/after: +0x400 0x24205400 -> 0x2420a400 (control works);
+0x200 0x24205200 -> 0x24205200 (odd store absent). The MCU never reached
marker3 after the odd store's DSB. This contradicts the old claim that only
read responses are broken; both directions now fail under controlled testing.
The result does NOT identify an address hole or a hardware defect.

Next: test a supported vendor L2 hash override (8, leaving size unchanged),
before L2 power-on, with readback and the same 2420 witness. Original L2_CONFIG
is 0x07130000, not a zero config. r32p1 mali_kbase_gpuprops.c explicitly allows
user-defined hash selectors 8..15; mali_kbase_pm_driver.c programs bits31:24
before L2 power-on. No such test has run. Earlier panthor ASN_HASH reasoning
applies to arch>=11 and cannot exclude arch10 L2_CONFIG's hash selector.

## >>> PREVIOUS 2026-11-09: 2420 CPU WITNESS TRIAL <<<

The user explicitly authorized continued GPU hardware trials in this session.
2420 image e47c27d83f11bc4e32e1568759b7b6af8e781a85c3448f9eee3affa3501b7d39
was built and the read-only Recovery preflight passed. The runner has written
and verified the candidate and started the boot; restoration is pending until
the journal confirms otherwise. Runner/log/artifacts:
research/matisse/20261109-gpu/shim2420-store-witness-run-once.py, run2420.log,
shim2420-store-witness/gpu-normal/journal.json.

The CPU seeds and reads shared+0x200/+0x400 before AUTO and after the wait,
BEFORE disable/reset. MCU markers: 1 control store/read, 2 odd store/DSB,
3 odd read, 4 completed. CPU absence alone does not prove an address hole.
784-byte ABI unchanged; kernel c01dcbea...d5ea / mark 0x2407 reused (shim-only,
no CI run). 11 boot-model tests and 35 fetch tests pass; arena 0x40078000.

References pinned today: Linux 7475ea8b58616b33c04afb976cf0fbaad9dd63fb;
Xiaomi 270b84910b941bf75490fccdb5fb2b3021dd7cbf; OnePlus branch
oneplus/mt6983_t_13.0_oneplus_ace_2v at ff51a39c66a87f91d870bfff1611e2b36371c8a4.
Eight selected vendor files match byte-for-byte. Their hashes/paths are in
research/matisse/20261109-gpu-sources/sources.json.

Corrections: AS_COMMAND is GPU+0x2418, AS_STATUS is +0x2428 (implementation
already correct). 0x855 is documented as R_dispatch_mode, not an eight-slot
port map; earlier inference cannot exclude the entire MFG/interconnect.
2402/2404 did not prove odd stores completed (see wall report section 55).

## >>> PREVIOUS 2026-11-08 17:25: 2419 RAN - THE WRITE LANDS, THE FIELD IS STILL NOT THE WALL <<<

Four in-words read `0xFFC855` before and `0x00000800` after - all four, exactly the
word written, upper 20 bits cleared too. `diag_flags` `0x387F` (bit11 ran, bit12
already `0x855`, bit13 all read back `0x800`, bit14 clear). **Writes to
`0x13FBF000` land from this context** - so 2413/2414/2418 were writing a live
register, their conclusions stand on evidence now, and 2413's flaw is closed one
level down.

Wall unchanged: marker 3, `output_va` `0x2412a400`, `mcu_status` 1, `as_fault` 0,
610 MHz / 65 mV, identical to 2412. The bit-9 = 0 rungs answering after a
full-width zeroing also says the write did not disturb the in path.

Three codes have now held in the read dispatch mode without moving anything:
`0x855` (vendor), `0xAAA` (2414), `0x800` (pattern `0x00`, bit 11 kept). As
nibbles that is mode 5 / A / 0 on both halves plus bit 11. Mode 0 would have sent
every slot to port 0 and did not. **The MFG top page and the AXI 1-to-2 bridge are
excluded as levers, with the write proven.** Everything `gpufreq_mt6983.c` touches
in that page - AXCOHERENCE, the eight dispatch words, the SLC group table, the GPM
protector - has now been read, written, or both, and none of it moves the wall.

Restated because it constrains what is left: a **store** to a bit-9 = 1 slot
completes (2402/2404) while the **read back hangs**. So the next question is not
which register - it is whether that store's *data* ever reaches DRAM. If it does,
the odd 512-byte slots are real memory with a broken read return path. If it does
not, they are a hole in the GPU's address map and "the write completed" only means
a posted write needs no response.

Next (not built): the ladder stores a magic to `shared+0x200` (bit 9 = 1), the MCU
stalls on the read as always, and the **CPU reads `shared+0x200` afterwards** and
puts it in a report slot. Magic present -> hole ruled out, read path only. Magic
absent -> the odd slots are a hole and the whole shape is decode, not return.

## >>> PREVIOUS 2026-11-08 17:20: 2419 BUILT - WRITE `0x800`, THEN READ THE WORDS BACK <<<

2418's two readings: `0x000` was never the minimal "all to one port" value (it
zeroed the 512-byte pattern *and* bit 11), or nothing has ever reached
`0x13FBF000` from this context. 2419 separates them in one boot.

`0x055` = `0101 0101` is an 8-slot port map, one bit per 512-byte slot - the exact
alternation 2415 measured - and the read path carries one extra bit
(`0x855 = 0x800 | 0x055`). So 2419 writes `0x800`: pattern `0x00`, bit 11 kept,
the smallest delta from the vendor literal. Then it **reads the same four words
back**, the control 2413/2414/2418 never ran.

Same 40-byte block, same offsets, ten labels under `SWEET_CSF_DISPATCH_READBACK`:
four pre-words, four post-words, `0x900/0x928` read but never written.
`gpu_regs_flags == 1`; `diag_flags` bit 11 ran, bit 12 already `0x855`, bit 13 all
four read back `0x800`, bit 14 all four unchanged (inert). Everything else is
2418 byte for byte, so marker 3 = wall stayed, marker 4 = pattern was the wall.

Static: four reads (`+0x8e0`, `orr #8`, `add #0x30`, `add #0x38`), then `+0x20`
and `+0x48`; exactly four stores with `w2 = 0x800`; then the same four reads
again; `cmp #0x855` / `cmp #0x800` / pre-compare gate the bits.

Image `2f8f3789...eda8`, payload `fb0a2b7c...08c2`, kernel `c01dcbea...d5ea`,
308 tests / 3 skipped, 2418 rebuilt byte-identical from the changed sources
first. Runner `shim2419-disp-readback-run-once.py`, partition hash
`cd212200...1e6a`, preflight passed, `boot_a` `2931647a...86b1`, device in
Recovery. **Not flown.**

## >>> PREVIOUS 2026-11-08 17:01: 2418 RAN - THE ZERO DID NOT MOVE THE WALL; `0x055` SPELLS ITS SHAPE AND NO WRITE HAS EVER BEEN READ BACK <<<

2418 flew (`555c10e7...aef7`), restored `2931647a...86b1` in the same run, fastboot
96.93 s, marks fresh. `diag_flags` `0x183F` = bit 11 (block ran) + bit 12 (in-words
already `0x855`). **Marker 3**: `0xC400` answered, `0xD400` answered, `0xD200`
stalled - the wall did not move. The bit-9 = 0 rungs still answering *after* the
write also says `0x000` did not disable the in path.

Two new facts, one of them large:

1. The eight words read `0xFFC855` (in x4) / `0xFFC055` (out x4) - bits 31:12 are
   `0xFFC000`, not zero. The vendor does `val |= 0x855` on a just-read value and
   never reads back, so those twenty bits have never been observed.
2. `0x055` = `0101 0101` is an **8-slot port map, alternating every 512 bytes** -
   exactly the geometry 2415 measured by hand (`+0x000`/`+0x400` answer,
   `+0x200`/`+0x600` stall). The odd-slot port is the one with no responder. The
   read path carries one extra bit (`0x855 = 0x800 | 0x055`), the write path none.

So `0x000` was not the minimal "all to one port" value: it asked for pattern `0x00`
*and* cleared bit 11. The untested value is `0x800`. But the deeper hole is that
**2413, 2414 and 2418 all wrote and never read back** - if writes to `0x13FBF000`
are ignored from the AP, all three measured nothing. `+0x748` does read
`0x06002006`, the vendor's own literal, so some write to that page survived into
this boot - possibly LK's, not the vendor kernel's.

Next (not built): write `0x800` and read the four words back in the same block.
Readback `0x800` + wall gone -> the field is the wall; readback `0x800` + wall
stays -> writable, not a read selector; readback `0xFFC855` -> writes inert and
2413/2414/2418 are void.

## >>> PREVIOUS 2026-11-08 16:56: 2418 BUILT - ASK THE 1-TO-2 BRIDGE TO ROUTE EVERYTHING TO ONE PORT <<<

2413 applied the vendor's dispatch values (a no-op if already there) and 2414 wrote
`0xAAA` (arbitrary). Neither asked the bridge for the setting that would *remove* a
per-address split, and bit-9 = 0 accesses prove one port works. 2418 asks for that.

It records the eight dispatch words first, **full 32 bits** - the vendor only ever
ORs `0x855`/`0x055` into bits 11:0 and never reads them back, so bits 31:12 have
never been seen and an enable/bypass would live there - then writes `0x000` to the
four in-direction words (`0x8E0/0x8E8/0x910/0x918`) and leaves the out-direction at
the vendor `0x055`, so a read-only fix is separable from a bidirectional one.

Everything else is 2412 byte for byte: container, arena `0x40078000`, code
`0x401a5000`, both leaves, sentinels and the three-read ladder, so marker 3 means
the zero did not move the wall and marker 4 means it did. ABI unchanged: same
40-byte block, ten labels (`SWEET_CSF_DISPATCH_SURVEY`), `gpu_regs_flags == 1`
(pre-write samples), `diag_flags` bit 11 = block ran, bit 12 = the in-words already
read `0x855` (a no-op, reported rather than silent).

Static: `csf_boot.o` reads `0x13FBF8E0` then `orr #0x8`, `add #0x30`, `add #0x38`
and `add #0x20`, `#0x28`, `#0x40`, `#0x48`; exactly four stores carry `w2 = wzr`
and all four go to the in-word addresses.

Image `555c10e7...aef7`, payload `93b27ab6...2e21`, kernel `c01dcbea...d5ea`,
307 tests / 3 skipped, 2412-2417 all rebuild byte-identical. Runner
`shim2418-disp-trials-run-once.py`, partition hash `33f1c7c3...a367`, preflight
passed, `boot_a` `2931647a...86b1`, device in Recovery. **Not flown.**

## >>> PREVIOUS 2026-11-08 16:50: 2417 RAN - THE GROUP TABLE IS NOT TEN WINDOWS; THE LAST REGISTER LEAD CLOSES <<<

2417 flew (`cc0f601c...12bf`), restored `2931647a...86b1` in the same run, fastboot
93.71 s, marks fresh. Control intact: `input_va` 3, `output_va` `0x2412a400`,
`mcu_status` 1, `as_fault` 0, `diag_flags` `0x807F` (bit15 set, no glue bits).

Ten base words collapse to **four distinct values**:

| group | value |
|---|---|
| 0 | `0x00000000` |
| 1, 7 | `0x00000014` |
| 2, 3, 4, 5, 8, 9 | `0x113F0F95` |
| 6 | `0x113F0F81` |

Group 6's word is byte-identical to 2416's `0x740`, group 7's to 2416's `0x74C`.

**It is not a window table.** `0x113F0F95 ^ 0x113F0F81` = `0x14`, exactly what
groups 1 and 7 hold alone (bits 2 and 4, no address above them). Six identical
values plus a seventh differing by precisely the flag bits two others consist of
is a shared descriptor plus flags, not ten bounds. So it cannot be the 512-byte
wall, and it is not an access filter either - group-6-tagged leaves read memory far
outside `0x113F0000` every run.

**Leading explanation now**: the 2415 shape (bit 9 decides, bit 10 irrelevant,
hangs rather than faults) is what an address-bit 1-to-2 split with no responder on
the second port looks like. 2414 already showed the dispatch words arrive at
vendor values and that overwriting them changes nothing.

**Correction forced by this run**: §65's "rungs at 0x010019xx, every one at bit 9
= 1" is wrong - `0x1b0`/`0x1e2`/`0x1f6`, `0x010018ec` and `0x0100E000` all have bit
9 = 0. The data-side conclusion survives on `0x01000200` (bit 9 = 1, patched to
`nop; bx lr` every run and followed by a working ladder), which is a stronger
witness: same page, opposite side of the boundary.

**Last stone**: read the 1-to-2 cluster `0x13FBF800..0x13FBF9FC` read-only for an
enable/bypass word. If there is none, the upper 512 bytes of every 1 KiB have no
responder on this board and no GPU register fixes it - then the decision is to
document the wall as physical and stop chasing the real firmware on this device.

`boot_a` `2931647a...86b1`, device in Recovery. Docs §75. **Nothing pending.**

## >>> PREVIOUS 2026-11-08 16:42: 2417 BUILT - READ THE WHOLE GROUP TABLE, ONCE AFTER THE MCU START <<<

2416 answered a narrower question than it was built for: group7's base at `0x74C`
already reads `0x14`, not the vendor's `0xFFFFFFFF`, so "only group 6 was
special-cased" was false before the build existed. 2417 spends its 40 bytes on
breadth: the base word of **groups 0..9**, sampled once, after the MCU start.

The vendor layout from `__gpufreq_slc_control()` is not uniform - group 0 is a
single word at `0x700` (`// group0: default`), groups 1..15 are triplets from
`0x704` with a 12-byte stride - so the ten addresses are `0x700`, then
`0x704/0x710/0x71C/0x728/0x734/0x740/0x74C/0x758/0x764`, spelled out rather than
computed because an off-by-one group index is what this build must be able to
catch.

ABI unchanged: the same 40-byte block, ten labels (`SWEET_CSF_SLC_GROUPS`),
`gpu_regs_flags == 2` (after only) and `diag_flags` bit15 for "no before pass".
The decoder accepts `flags == 2` only for this build - verified by forcing a 2416
capture through it, which is now refused with `invalid CSF GPU register sample
flags/reserved word`. The policy at `0x748` is still sampled before and after by
`platform_path()`, so the page keeps a live control.

Everything else is 2412: container, arena `0x40078000`, code `0x401a5000`, both
leaves, sentinels and the 2412 ladder, so the wall must reproduce underneath.

The new test encodes the address into the model's return value
(`0xB0000000 | (addr - 0x13fbf700)`) and asserts all ten report fields, so a wrong
stride or a shifted view fails by name - the same class of bug 2416 hit one layer
up.

Read it: every base `0xFFFFFFFF` except group0 -> no per-group window exists and
the words cannot be the wall; group 6 the only mismatch -> the value is an LK
question (already unlikely); several mismatches -> an ordinary descriptor table
whose encoding is undocumented in the three trees.

Image `cc0f601c...12bf`, payload `641c5862...d556`, kernel `c01dcbea...d5ea`,
306 tests / 3 skipped, 2412-2416 all still rebuild byte for byte. Runner
`shim2417-groups-trials-run-once.py`, partition hash `3cf69452...6e48`, preflight
passed, `boot_a` `2931647a...86b1`, device in Recovery. **Not flown.**

## >>> PREVIOUS 2026-11-08 16:32: 2416 RAN - THE GROUP WINDOW IS NOT THE VENDOR VALUE, AND NOT A WINDOW <<<

2416 flew (`4cd9c920...c5a2`), restored `2931647a...86b1` in the same run, fastboot
86.52 s. `input_va` 3, `output_va` `0x2412a400`, `mcu_status` 1, `as_fault` 0 - the
wall reproduced, which is the control the register read needed.

Five words, before and after identical:

| offset | value |
|---|---|
| `0x13FBF700` | `0x00000000` (group 0 default - matches the vendor) |
| `0x13FBF740` | `0x113F0F81` |
| `0x13FBF744` | `0x107F3F81` |
| `0x13FBF748` | `0x06002006` (group 6 policy - matches since 2407) |
| `0x13FBF74C` | `0x00000014` |

Two words match known constants, so the page and offsets are right; the other two
are **not** the vendor's `0xFFFFFFFF`. Read as base/limit the pair is inverted; read
in the other order it is a 12 MiB window `[0x107F3000,0x113F0000]` that does not
contain the arena at `0x40078000` - and group-6-tagged leaves into that arena
translate and read every run. So either the low 12 bits are attributes and the
order is reversed, or these are not a base/limit pair at all. No source of truth in
the three trees: the only other use of `0x740/0x744` is the vendor's write, the
`MMU_AS13` hit in the DDK regmap is a different block, and SLC has no Linux driver
in this kernel (GPUEB owns it).

Established anyway: the window is not the vendor's full range; it is stable across
the MCU start (configuration, not activity); the page is live (two known constants
reproduce); and a window that excludes the arena cannot be what gates arena
access, so this pair cannot be the 512-byte wall either.

**Decoder bug caught on the reading side**: the 2416 branch labelled the ten words
in a different order than the struct declares (`base, limit, ctl, group0, group7`),
so the first decode printed the group 0 word as the base. Fixed; values above are
corrected. Second time in three builds that the instrument, not the device, needed
fixing.

Next, cheap: read the base word of groups 0..9 in one pass (`0x700/0x704/0x710/
0x71C/0x728/0x734/0x740/0x74C/0x758/0x764`). All-groups-descriptors means the
encoding is a table and group 6 is ordinary; group-6-only-non-FFFFFF means the boot
chain special-cased it and the meaning is an LK question, not a flight question.

`boot_a` `2931647a...86b1`, device in Recovery. Docs §73.

## >>> PREVIOUS 2026-11-08 16:28: 2416 BUILT - READ THE SLC GROUP WINDOW, CHANGE NOTHING ELSE <<<

2415 closed the shape, so the last unread SoC-side object is the SLC group
*window*: group 6's base and limit at `0x13FBF740/0x744`. The shim has sampled the
policy at `0x748` since 2407 and never those two. Vendor layout from
`__gpufreq_slc_control()`: group 6 is `0x740/0x744/0x748`, group 7 starts at
`0x74C`, so `0x74C` is group 7's base and not a fourth group-6 word.

2416 reads five words before the MCU start and the same five after - `0x700`
(group 0 default), `0x740`, `0x744`, `0x748`, `0x74C` - and writes nothing in that
page, so before and after must agree; a difference would be the finding. The
784-byte report's 40-byte register block is reused with different labels via
`SWEET_CSF_SLC_WINDOW`, so the ABI does not move (the size assert still holds) and
the decoder picks the view by kernel build id. Everything else is 2412: ladder,
both leaves, arena control, sentinels, arena `0x40078000`, code `0x401a5000`.

Likely reading: base and limit both `0xffffffff` (what the vendor writes for every
group), which would kill the last register-level explanation of a 512-byte
boundary and leave the interconnect. Anything else makes the window's extent the
thing to compare with the arena's physical span.

**Also fixed a decoder regression this build exposed**: adding 2415's branch left a
bare `else` hanging off the 2413/2414 sub-chain, so decoding 2412/2413/2414
silently returned `no-marker`. Images were unaffected, only the reading. The four
older captures now decode to their own conclusions again - 2412
`bit9-not-arena-shaped`, 2413 `glue-changed-nothing`, 2414
`axi-dispatch-not-the-wall`, 2415 `bit9-512-period-confirmed` - and that
re-run is now part of the build recipe.

Static: `csf_boot.o` reads `0x13fbf700` then `orr #0x40/#0x44/#0x48/#0x4c`.
2412/2413/2414/2415 still rebuild byte for byte. Image `4cd9c920...c5a2`, payload
`78cfc9e9...d8de`, partition hash `1bae2362...462e`, 305 tests / 3 skipped,
preflight passed, `boot_a` `2931647a...86b1`, device in Recovery. **Not flown.**

## >>> PREVIOUS 2026-11-08 16:22: 2415 RAN - THE WALL IS 512 BYTES WIDE, AND BIT 9 IS ALL OF IT <<<

2415 flew (`4eebf393...78bf`) and restored to `2931647a...86b1` in the same run -
no rescue needed, Recovery came up on the first reboot. Marks differ
(`a09099...` -> `c0a654...`), fastboot 121.04 s, the normal timeout path.
`input_va` 3, `output_va` `0x2415a400`, `mcu_status` 1, `as_fault` 0,
`diag_flags` `0x7F`.

Marker 3 = stopped at `0x0100D600` (bit 9 = 1, bit 10 = 1). Read 2 returned
`0x2415a400`, which only this shim plants at `+0x400`, so the four-sentinel
scheme worked and the offset named itself.

Shape: `+0x200` stalls, `+0x400` answers, `+0x600` stalls. Bit 10 is irrelevant;
the offset's bit 9 decides. A 512-byte alternation, and no field of a 4 KiB leaf
can carry a 512-byte granule - so the wall is not a page-table property, now as a
measured shape instead of an inference. It also kills "the second half of every
1 KiB" (`+0x400` answers) and "a 1 KiB structure" (`+0x600` stalls with bit 10
set).

**What is left, and it is one register pair.** The shim has sampled the SLC group
policy `0x13FBF748` since 2407 but never its window: `0x13FBF740/0x744` (base and
limit). If that window is programmed in 512-byte units, or covers only the even
sectors of the arena's span, it is the first SoC-side mechanism that produces a
512-byte boundary without contradicting a single earlier measurement. The next
build is read-only: sample those three words before and after the MCU start,
compare with the arena PA span, no new ladder, no new mapping.

Recorded because it is visible: fastboot arrival drifted 81.4 -> 83.4 -> 89.6 ->
121.0 s over the last four runs. Nothing in 2415 changes a timeout and the run was
normal (report published, no crash, both restores verified), so it is
environmental until proven otherwise.

`boot_a` `2931647a...86b1`, device in Recovery. Docs §71. **Nothing built or
pending.**

## >>> PREVIOUS 2026-11-08 16:18: 2415 BUILT - THE SHAPE OF THE WALL, FOUR OFFSETS IN ONE PAGE <<<

2412-2414 closed every "which" question, so 2415 asked "what shape". The series
had only ever read +0x000, +0x200 and +0x400 of a page, and those three cannot
separate "PA bit 9" from "the second 512 bytes of each 1 KiB" - a translation
preserves the 12-bit offset, so no mapping can. +0x600 has bit 9 = 1 and bit 10 =
1, and that is the one offset that can.

It kept 2412's container, arena (`0x40078000`), code (`0x401a5000`), both leaves
and the single result slot, and moved exactly two things: four sentinels
(`0x2415a000/a200/a400/a600` at `+0x000/+0x200/+0x400/+0x600`, so the returned
word names the offset) and a four-read ladder (`tools/matisse-csf-ladder2415.S`,
still exactly 136 bytes) reading `0xC400`, `0xD400`, `0xD600`, `0xD200` with
markers 1..4 and marker 5 = all returned. `+0x200` was asked last so the one
known-stalling access could not hide the new question.

Gated by `SWEET_CSF_OOA_SHAPE`, so 2412/2413/2414 kept their bytes; the runner
also gained the fastboot full-restore rescue that 2414 had to be done by hand.

## >>> PREVIOUS 2026-11-08 16:05: 2414 RAN - THE GLUE WAS ALREADY PROGRAMMED, AND PERTURBING IT CHANGES NOTHING <<<

2414 flew (`42385e94...938f`, fastboot 89.57 s) and the measurement is complete.
The run was interrupted during the restore, so the first pass only wrote the
20.87 MiB trim prefix and the device came up in fastboot; once it was in
Recovery, `restore-only` captured the after evidence and wrote the full 64 MiB
back, verified `2931647a...86b1`.

Reading is 2412's exactly: `input_va` 3, `output_va` `0x2412a400`, stage 4
`timeout`, `mcu_status` 1, `as_fault` 0.

Two facts, and they point opposite ways from the hypothesis:

* `diag_flags` `0x787F` = bit 11 + 12/13/14: the in-dispatch words were already
  `0x855`, out-dispatch already `0x055`, group 6 already `0x06002006` **before**
  the write. So the boot chain programs the MFG top page, and 2413's writes were
  genuine no-ops.
* The desk audit's proof of the opposite ("`0x13FBF748` reads `0x06000006`") was
  never measured anywhere. 2407's own `gpu-result.json`, 2412, 2413 and 2414 all
  report `path_before.slc_group6 = 0x06002006`.

Perturbing the four in-dispatch words outright to `0xAAA` moved nothing, so the
AXI 1-to-2 read dispatch is not the wall and that lead is closed. Residual, on
the record: the 784-byte ABI carries no after-value for those words, so "0xAAA
landed" is inferred from the write path - but the premise is dead either way,
because the block arrives programmed and the wall survives it.

**What is left.** (1) Shape: one ladder reading `+0x000`, `+0x400`, `+0x600`,
`+0x200` in that order - `+0x400` already returned, so "upper half of each 1 KiB"
is dead, and `+0x600` splits "PA bit 9" from any 512-byte-period story. (2) The
group table LK builds before handoff: the DT `mgm` node is empty and the table is
in none of the three trees, and the shim has never read `0x740/0x744`.

Image `42385e94...938f`, payload `43c75828...99de`, kernel `c01dcbea...d5ea`,
305 tests / 3 skipped. `boot_a` `2931647a...86b1`, device in Recovery.
`docs/matisse-gpu-mcu-wall.md` §69; the audit's §10.3/§10.4 are corrected in
place. **Nothing is currently built or pending.**

## >>> PREVIOUS 2026-11-08 15:53: 2413 RAN - THE VENDOR GLUE DID NOT MOVE THE WALL, AND THE TREATMENT WAS UNVERIFIED <<<

2413 flew and restored. `input_va` 3, `output_va` `0x2412a400`, `mcu_status` 1,
`diag_flags` `0x87F` (bit 11 set, so the eleven writes ran), fastboot at 83.37 s.
**The reading is 2412's, exactly**: with the vendor's MFG top glue applied before
`MCU_CONTROL`, the bit-9 = 1 half still never returns.

The caveat is what matters for the next build: `path_before.slc_group6` and
`path_after.slc_group6` are **both** `0x06002006`, i.e. group 6 already carried
the vendor word before the write, and the eight dispatch words have no witness at
all - the shim's console text does not reach any capture (2412's `CSF ooa near`
is absent from its own log too). So the glue is a no-op as a *treatment*: the
build applied a configuration without proving it differed.

What is settled: the vendor glue as a block is not the wall. What is not: whether
the AXI 1-to-2 dispatch words were already `0x855/0x055`. The next flight must
perturb, not apply - write the in-dispatch words to `0xAAA` (a value hardware
cannot already hold), keep the out-dispatch at `0x055`, keep 2412's ladder, and
record "already at the vendor value" bits in `diag_flags` 12/13/14. Dead ladder
= the bridge governs the data path; marker 3 again = the lead closes and only
LK's group table is left.

`docs/matisse-gpu-mcu-wall.md` §67. `boot_a` restored to `2931647a...86b1`,
device in Recovery.

## >>> PREVIOUS 2026-11-08 15:50: 2413 BUILT - THE VENDOR'S MFG GLUE, NOT FLOWN <<<

2413 is 2412 byte for byte except one block written before `MCU_CONTROL`:
`AXCOHERENCE |= 0xF` at `0x13FBF168`, the eight `MFG_1TO2AXI` read-dispatch words
(`0x855` in, `0x055` out), and SLC group 6 (`0x740/0x744 = 0xffffffff`,
`0x748 = 0x06002006`). That is exactly `__gpufreq_acp_control()` plus the group 6
word of `__gpufreq_slc_control()` from `gpufreq_mt6983.c`, which the vendor runs
on **every** GPU power-on and which has provably never run here: the same page
has read back `0x06000006` for group 6 since 2407, i.e. bit 13 ("R cache") clear.
**[Retracted 16:05 - that reading exists in no capture. 2407/2412/2413/2414 all
report `0x06002006`. See the ACTIVE block above and §69.]**
panthor owns `0x13000000` only; the DDK assumes the platform did `0x13fbf000`.

Verified statically, no flight: the disassembly of `shim.elf` shows the eleven
read-modify-writes in the vendor's order immediately after `platform_path(...)`
samples "before", and `0x748` written as `0x06002006`. The report's `slc_group6`
field therefore carries a before/after pair (0x06000006 -> 0x06002006) without
touching the 784-byte ABI, and `diag_flags` bit 11 records that the block ran.

Read it exactly as 2412: `input_va` 4 = the glue removed the wall; `input_va` 3
with `output_va` `0x2412a400` = the glue is not it, and the only remaining
candidate is the group table LK builds before handoff (not in the three trees).

Image `aed0b399...3688`, payload `82ddc442...20d0`, kernel `c01dcbea...d5ea`,
arena `0x40078000`, code `0x401a5000`, 304 tests / 3 skipped, runner
`shim2413-mfgglue-trials-run-once.py` (`1abc5d81...6f77`), preflight passed.
`boot_a` still `2931647a...86b1`; **nothing flown since 2412**.

## >>> PREVIOUS 2026-11-08 15:32: 2412 ANSWERED - BIT 9 IS THE ADDRESS, NOT THE ARENA; THE WALL IS DATA-SIDE <<<

2412 asked one question and got a clean two-line answer. All three control
selections held: the arena leaf `0x0100C400` (bit 9 = 0) returned the firmware's
own `0xb001500c`; the remapped out-of-arena leaf `0x0100D400` (bit 9 = 0) returned
`0x2412a400`, **the word this shim itself planted** at `pa_near + 0x400`, so a
page the arena does not back was translated by the MCU's own table and read
correctly; and `0x0100D200` - same page, same leaf, same tag 6, one address bit
away - never returned. `input_va` 3, `output_va` `0x2412a400`, `mcu_status` 1,
`as_fault` 0, fastboot at 81.37 s (2411 83.42, 2410's crash 73.41 = the normal
timeout path).

Decoded: `bit9-not-arena-shaped`. **The wall is not the arena allocation, not the
read side (2411), not the VA range (code, mirror, shared, BSS page), not the tag
(2409).** It follows the address.

Two things this run pins down beyond the answer:

* **The wall is data-side.** Instruction fetch at bit 9 = 1 has always worked:
  `0x01000200` has bit 9 set, and every run since 2401 patches the two
  instructions there to `nop; bx lr` before going on to execute the ladder - a
  patch that only makes sense if that code runs. Loads and stores are what never
  complete. The firmware therefore does not fail because it cannot be fetched; it
  fails on its first data access past the 512-byte boundary.
  *(Corrected by 2417: this used to cite the 2358-2362 rungs at 0x010019xx, but
  every one of those offsets has bit 9 = 0. The conclusion stands on 0x01000200.)*
* **The offset is not separable from the PA bit.** A translation preserves the
  12-bit offset, so "PA bit 9" and "second 512 B of the 1 KiB" are the same bit
  and no mapping can tell them apart. The series has only sampled offsets
  `0x000`, `0x200`, `0x400` in one page; the periodic shape is unmeasured.

**Where the mechanism has to live:** a 512-byte granule cannot come from a 4 KiB
leaf (attributes and PBHA are per leaf). It has to be outside the MMU - the SLC
group the ADT hands out (`arm,physical-memory-group-manager`), MTK's GMPU, or the
interconnect. That is exactly the §9 item left over.

**The desk audit found it** (`docs/matisse-gpu-upstream-audit.md` §10). MGM is an
empty DT node; GMPU only guards the 16 MiB protected reserve, so neither can
explain ordinary pages. What can: `__gpufreq_acp_control()` in
`gpufreq_mt6983.c:3323`, which the vendor runs on **every** GPU power-on and which
writes `mfg_axi1to2_R_dispatch_mode` = `0x855`/`0x055` into
`0x13FBF8E0/8E8/910/918` and `0x13FBF900/908/920/928`, plus `AXCOHERENCE`
`|= 0xF` at `0x13FBF168`. A "1 to 2 AXI" bridge splits transactions by an address
bit and has no other dimension to split on - and the wall is exactly "one half of
every 1 KiB answers". **And the block is measurably unprogrammed:** the shim has
been reading `0x13FBF748` since 2407 and gets `0x06000006` where
`__gpufreq_slc_control()` writes `0x06002006` (bit 13, "R cache"). **[Retracted
16:05 - never measured; every report reads `0x06002006`, and 2414 showed the
dispatch words already at `0x855`/`0x055`. The lead is closed, §69.]**
panthor never touches `0x13fbf000`; the DDK assumes the platform already did.

**Next is 2413**: 2412's image, addresses and ladder byte for byte, plus that
vendor glue applied before `MCU_CONTROL`, with the dispatch words' before/after on
the console. `input_va` 4 = the wall is the glue; `input_va` 3 with the same
`output_va` = the glue is not it and only LK's group table is left.

**Not flown anything since.** `boot_a` restored to `2931647a...86b1`, device in
Recovery, image `333acd79...a3e72` reproducible byte for byte (verified again
today from the recorded recipe), `docs/matisse-gpu-mcu-wall.md` §65.

## >>> PREVIOUS 2026-11-08 15:35: 2411 ANSWERED - A WRITE AT BIT 9 = 1 STALLS TOO; 2412 IS THAT MINUS THE STORE <<<

2411 did not reach its question, and what stopped it is the cleanest result of
the series. Marker 1 landed, the MCU read `0x0100C400` - an **untouched** firmware
leaf into the arena, tag 6, PA `0x401b1400`, bit 9 = 0 - and got `0xb001500c`,
which is exactly the word the container carries at VA `0x0100C400`
(offset `0xd294`). That word landed at `shared+0x0c`. The next instruction
stores the same word to `shared+0x200`, and marker 2 never appears
(`input_va` 1, `mcu_status` 1 = enabled, not halted).

Between the landing word and the missing marker there is one access:
`shared+0x0c` (bit 9 = 0) landed, `shared+0x200` (bit 9 = 1) never returned.
Same page, same mapping, same tag, same instruction. **A write at bit 9 = 1
stalls exactly like a read**, in a third VA range (the shared section). 2405's
ladder has that store as its marker 3 and 2405..2408 all stopped before it, so
2411 is the first build that ever executed it.

Decoder fixes this run forced: the arena bound was 1 MiB and rejected a control
leaf at `0x401b1000`; it is 2 MiB now, and 2411 re-decodes as
`ooa_remap_observed: true`, `cold_boot_outcome: write-at-bit9-stalled`.

**2412 is 2411 minus that store**: one result word at `shared+0x0c`, no other
slot, everything else identical (0x0100D000 -> 0x40279000 tag 6, 0x0100C000
control leaf, three reads). Image `333acd79...a3e72`, payload `156b7f6c...2e9d`,
303 tests, runner `shim2412-ooa4-trials-run-once.py` (`28a0b698...7fc1`).
**Not flown**, `boot_a` back to `2931647a...86b1`.

## >>> PREVIOUS 2026-11-08 15:20: 2410 CRASHED THE BOOT; 2411 REMOVES THE FAR PAGE <<<

**2410 did not publish anything.** `after-marks.bin` is byte-identical to
`before-marks.bin` (`9e1bdb11...`), and that content is 2409's report - the
kernel never wrote the marks page. Boot reached fastboot at **73.41 s** against
85.4 s for 2408: twelve seconds of CSF timeout never happened. The phone showed
the REDMI logo and reset. `boot_a` was restored to `2931647a...86b1` and the
device is in Recovery; ramoops holds an older Android boot, not this one.

**Diagnosis.** 2410 added one CPU read that must never happen: the witness
dereferenced `platform->firmware_memory + 0x1000`, i.e. the 20 MiB allocation LK
leaves for the GPU, whose own comment in `mtk_gpueb_boot.c` reads "never
dereference or overwrite that allocation". The shim runs with the MMU off, so
that load is a raw physical read of a carveout the CPU does not own; it died
there, before `sweet_csf_boot()`, which is exactly the shape of the evidence:
no report, no 12 s of MCU timeout, a reset at the logo.

**2411 removes the page, not the question.** One remapped leaf only
(`0x0100D000` -> a page of the shim's own BSS at `0x40279000`, one page past the
arena, tag 6), and `0x0100C000` keeps the firmware's own leaf into the arena as
an **instrument control**: read it first, and a stall at marker 1 says the image
is broken rather than anything about memory. Three reads: arena control
(`0x0100C400`, bit 9 = 0), past-arena (`0x0100D400`, bit 9 = 0), past-arena
(`0x0100D200`, bit 9 = 1). Nothing outside the shim image is touched by the CPU.

**Build.** Image `c8d0b033...b233`, payload `a72b45cc...9083`, kernel
`c01dcbea...d5ea`; arena `0x40078000`, code `0x401a5000`, near page
`0x40279000`. 303 tests / 3 skipped. Runner
`shim2411-ooa3-trials-run-once.py`, partition hash `d830862c...c0c3`.
**Not flown**, `boot_a` still `2931647a...86b1`.

Reading: marker 1 -> instrument dead, nothing to read into. Marker 2 -> the page
past the arena is unreachable even at bit 9 = 0 (the wall is about which pages
the GPU may read). Marker 3 -> bit 9 is the address bit, not the allocation.
Marker 4 -> the wall is a property of the arena allocation.

## >>> PREVIOUS 2026-11-08 15:34: 2409 BUILT - FIRST ACCESS OUTSIDE THE ARENA, TAG AS A CONTROL <<<

**The question 2401..2408 could not ask.** Every access that ever stopped the MCU
lies inside `[0x40078000, 0x40278000)`, so "bit 9 has no responder" and "this
allocation's second 512-byte half has no responder" fit all of it. 2409 reads the
same two 512-byte offsets of pages the arena does not back.

**Grounded, not guessed.** The target page is the **last two pages of the
bootloader splash reservation**, which `shim/board.c` already derives from
`/chosen` (`atag,videolfb-fb_base_l/_h`, `vramSize`; `cont_splash_region` is at
`0x9c000000`). Reasons on record: the arena does not back it, the panel is already
scanning it (powered, non-secure for the CPU - our console draws there),
`fb_size > stride*height` so the last page is past the visible frame, and the
address comes from the live tree, so a board that reports something else fails
closed. `panthor` maps ordinary DRAM pages the same way; nothing here is a
device-specific trick.

**The tag is the confound, so it is a controlled variable.** The firmware tags
every leaf group 6 (bits59..62) and group 6's policy was never shown to cover
anything but the arena. ARM's PBHA documentation says the bit meaning is
implementation-defined and that the *same* PA through mappings with different
PBHA is unpredictable, so 2409 never aliases one PA with two tags: it maps two
different pages, `0x0100D000` untagged and `0x0100C000` tagged 6, and reads both
controls before either bit-9 read.

```
marker 1  0x0100D400  ooa+0x0000  tag 0  bit9=0   control
marker 2  0x0100C400  ooa+0x1000  tag 6  bit9=0   control (tag)
marker 3  0x0100D200  ooa+0x0000  tag 0  bit9=1   the question, untagged
marker 4  0x0100C200  ooa+0x1000  tag 6  bit9=1   the question, tagged
marker 5  everything returned
```
1 only -> nothing outside answers, bit 9 untested (SLC/MGM/GMPU next). 2 only ->
the tag decides. 3 -> bit 9 is not arena-shaped. 4 -> bit 9 tracks the tag.
5 -> the wall is a property of the arena allocation.

**Implementation.** `sweet_csf_memory_remap_leaves()` walks the table the builder
wrote, requires a valid leaf, replaces bits47:12 and bits59..62, keeps AttrIdx/AP/
SH/AF/nG/XN, and refuses unaligned VA/PA, tag>15, PA outside pa_bits, PA inside
the arena, or no leaf. It is a separate entry point **compiled only for 2409**:
folding it into the builder changed every older object file, and after moving it
out 2407 rebuilds byte for byte again (`c124e536...1781`, re-verified). The shim
also prints its own CPU read of the four words (`CSF ooa g0/g6`) and the four MCU
slots (`CSF b9 g0/g6`).

**Build.** Image `0b35f105...a148`, payload `0ddae2ee...1dab`, kernel
`c01dcbea...d5ea` (unchanged, still tagged `0x2407` -> decode with
`--build 0x2409 --mark 0x2407`). Shim grew a page: arena `0x40079000`, code
`0x401a6000`, so compare leaves/tags, not absolute PAs. 303 tests / 3 skipped,
including a new remap test (PA+PBHA move, every other bit identical, five refusal
cases). Runner `shim2409-outofarena-trials-run-once.py`, partition hash
`80ce929a...d1ae`. **Not flown**, `boot_a` still `2931647a...86b1`.

## >>> PREVIOUS 2026-11-08 14:46: 2408 RAN - THE RESET COMPLETES, DBG_ENABLED DOES NOT CARE <<<

Flew `184d5353...9801`, read-back verified against `de922fdd...f7a8`, normal boot
reached fastboot at 85.4 s (2407: 85.6 s), `boot_a` restored to `2931647a...86b1`.

**The soft reset works - first completed reset in the series.** `diag_flags` =
`2047`: bit7 attempted, **bit8 `RESET_COMPLETED` arrived inside 100 ms**, bit9
`DBG_ENABLED` before, bit10 still set after. Everything else is 2407:

```
0x000 0xa8620004  0x004 0x07130306  0x00c 0x00000809  0x048 0x07130000
0x034 0x00000100 -> 0x00000101    0x2c0..0x2cc all zero
```
All ten register words and every boot field (`input_va` 2, `groups` 8, `version`
0, `mcu_status` 1, `error` -53) are bit-identical to 2407, before and after. The
ladder is 2406's byte for byte: read 1 `0x0100E400` returns `0x0f10f857`, read 2
`0x0604E400` dies on the bit-9 L3 descriptor. `reset_raw` `0x200` /
`reset_completed` 0 - cleanup's post-MCU reset behaved the same in 2407.

**What this settles.** The "reset never really ran" branch is dead - it ran and
completed. A completed soft reset changed no sampled word, `DBG_ENABLED`
included, so bit 8 is not a reset-cleared halt state left behind by LK/GPUEB; it
behaves like a static strap (panthor names it; r32p1's `mali_kbase_gpu_regmap_csf.h`
does not name a single `GPU_STATUS` bit). **The bit-9 wall is independent of the
reset state**, and the debug-state lead loses its mechanism.

**New asymmetry worth one line.** The same sequence completes *before*
`MCU_CONTROL` and times out *after* the MCU was started and halted, in both 2407
and 2408. Every reset this project ever issued went through the cleanup path, so
"reset never completes" was a property of when it was asked, not of the block.

**Next: 2409, the out-of-arena page** (`docs/matisse-gpu-upstream-audit.md` §9.2).
Reset is out of the queue. Needs the new primitive: map `0x0100D000` to a page
outside the arena (framebuffer `0x9c000000`), read `0x0100D200` (VA/PA bit9=1) and
`0x0100D400` (bit9=0).

Decode note: the kernel was still tagged `SWEET_BUILD_ID 0x2407` (not rebuilt for
this trial), so the capture decodes with `--build 0x2408 --mark 0x2407`; the image
sha identifies the run. `gpu-result.json` is written under
`shim2408-prestartreset-trials/gpu-normal/`.

## >>> PREVIOUS 2026-11-08 14:39: 2408 BUILT - THE RESET PANTHOR DOES, BEFORE ANYTHING ELSE <<<

**2408 is a reset, not a memory experiment.** The new re-audit
(`docs/matisse-gpu-upstream-audit.md`) reordered the queue: before spending a
flight on an out-of-arena page, answer the two facts 2407 left unexplained -
`GPU_STATUS.DBG_ENABLED` set on every read, and `RESET_COMPLETED` a stale bit
that never arrived for this transaction. The out-of-arena page test becomes 2409.

**The block as left in the tree could not have flown.** It was gated by
`SWEET_CSF_PRESTART_RESET`, which no builder passed, so the preprocessor dropped
it; and it wrote `r->gpu_status`, a member that does not exist - the word lives
in `sweet_csf_platform_snapshot`. Both are fixed: the builder passes
`-DSWEET_CSF_PRESTART_RESET=1` for 0x2408 only, and the evidence is four
`diag_flags` bits (7 attempt, 8 completion, 9 `DBG_ENABLED` before, 10 still set
after). `reset_raw` / `reset_completed` stay cleanup's own, the report stays 784
bytes, `gpu_regs_before.reg_034` gives the same word again after the AS setup.
A timeout is recorded, not fatal: the ladder runs either way.

Order is `panthor_gpu_soft_reset()`'s: `INT_CLEAR` bit 8 (write-1-to-clear),
`GPU_CMD = 0x101` (`GPU_CMD_DEF(1,1)`, same encoding as the vendor's
`GPU_COMMAND_CODE_PAYLOAD`), then `RESET_COMPLETED` within 100 ms - issued after
the register snapshot and before the coherency write, the L2 power-on or any AS
command. Correction to the audit, applied there: panthor resets on its
reset/resume path (`panthor_device_reset_work()`, `panthor_device_resume()` via
`panthor_gpu_suspend()`), **not** in `panthor_device_init()`, which trusts the
bootloader. "Reset first" is panthor's reset semantics, not its cold-init
invariant.

**Build.** Image `184d5353...9801` (26,714,112 B), payload `6f82e96c...4af0`,
kernel `c01dcbea...d5ea` (unchanged from 2407, no kernel patches needed), 302
tests / 3 skipped. `.text` grew 0x118 bytes and **the layout did not move**:
arena `0x40078000`, code section `0x401b6000`, code leaf `0x401c44c3`, mirror
`0x401b44c3`, uncached `0x401b74d7` - identical to 2407 in every manifest field,
so a difference in the report belongs to the reset.

Runner `shim2408-prestartreset-trials-run-once.py` (partition hash
`de922fdd...f7a8`). **Not flown**, `boot_a` still `2931647a...86b1`.

Reading: bit8 set + bit10 set -> the reset completes and the GPU is still in
debug; bit9/bit10 clear -> the reset cleared it and the ladder's next result is
about memory, not state; bit8 clear -> the handshake itself never completes, and
the next step is the LK/GPUEB handoff, not another page.

## >>> PREVIOUS 2026-11-08 14:12: 2407 RAN - BLOCK ALIVE, NO SLICE SIGNAL <<<

Flew `c124e536...1781`, `boot_a` restored to `2931647a...86b1`. `input_va` 2,
`shared+12` `0x0f10f857`, seed gone, no fault, `mcu_status` 1, `error` -53,
`firmware_probe_pa` `0x401b6000`, code leaf `0x401c44c3`, mirror `0x401b44c3`.

**2406 reproduced exactly** - same marker, same word, same silent stop at the
bit-9 descriptor. First independent repeat in the series.

**Registers: alive, and silent about slices.**

```
0x000 0xa8620004   0x004 0x07130306   0x00c 0x00000809
0x034 0x00000100 -> 0x00000101 (bit 0 appeared during the attempt)
0x048 0x07130000   0x04c 0
0x2c0 0x2c4 0x2c8 0x2cc = 0 before and after
```

The block is clocked - four words non-zero, `GPU_STATUS` moves - so the zeros are
a fact, not an artefact. But `0x048`'s low half is zero, where a per-slice mask
would sit, and the `0x2c0` words the vendor dump reads beside it are all zero.
**The dual-slice story is not supported.** A negative result, stated as one.

**The sharper question.** Every address that has ever killed the MCU lies inside
the 2 MiB arena `[0x40078000, 0x40278000)` - the 2402 data page, the vendor's
first read `0x401b6bc4`, the descriptors `0x4007f270` / `0x40080270`. No bit-9 = 1
access has ever been made outside it. "bit 9 has no responder" and "this
allocation's second 512-byte half has no responder" fit every measurement so far,
and the series has been treating the stronger one as settled.

**2409 should buy that discriminator**: one known word placed by the kernel in a
page outside the arena, read by the MCU at bit 9 = 1 through a descriptor at
bit 9 = 0. Returns the word -> the dead set is allocation-shaped (window/IOMMU);
hangs -> it is address-shaped (interconnect). 2408 was re-scoped to the reset
after the 2026-11-08 re-audit; see the ACTIVE block above.

## >>> PREVIOUS 2026-11-08 14:05: 2407 BUILT - SAME WALL, PLUS THE REGISTERS THAT COULD EXPLAIN IT <<<

2406 put the wall at one address: the L3 descriptor at `0x4007f270`, the only
bit-9 = 1 address in either walk. 2407 does not probe that wall again; it samples
the ten GPU words that could say why the address has no responder - `0x000`,
`0x004`, `0x00c`, `0x034`, `0x048`, `0x04c`, `0x2c0`, `0x2c4`, `0x2c8`, `0x2cc` -
before `MCU_CONTROL` and again after the attempt. Raw and named by offset: a
register word is a lead, and the build is not allowed to convert one into a claim.

The ladder, the seed and the four accesses are 2406's bytes exactly. The 88-byte
block pushed the shim's `.bss` over a page, so the arena anchor moved `0x77000` ->
`0x78000` and every PA is `0x1000` higher (base `0x401b6000`, code leaf
`0x401c44c3`, mirror `0x401b44c3`). `0x1000` is bit 12, so **no bit-9 relation
moves** - checked by rebuilding the page table, not assumed.
Descriptor: read 1 `0x4007c070` (bit 9 = 0), read 2 `0x40080270` (bit 9 = 1).

Three hardcoded 696s had to go with it, or the block would have vanished without
a word: the shim's property lookup, its `_Static_assert`, and the kernel
forwarder, which copied 696 bytes and emitted 87 marks. The forwarder now takes
`size / 8` marks for any 696..1024-byte property (patch 0204).

Image `c124e536...1781`, kernel `c01dcbea...d5ea` (`SWEET_BUILD_ID 0x2407`,
patches 0203/0204), partition `3388fa8c...f35e`, 300 tests / 3 skipped, preflight
passed, `boot_a` still `2931647a...86b1`. 2404 still rebuilds byte-identically
with the block compiled out. **Not flown.**

## >>> PREVIOUS 2026-11-08 13:36: 2406 RAN - THE WALL IS THE PAGE-TABLE WALK, NOT THE DATA PATH <<<

Flew `38389ecf...c0f9`, `boot_a` restored to `2931647a...86b1` in the same run.
`input_va` 2, `shared+12` `0x0f10f857`, seed gone, `error` -53, `as_fault` 0,
`mmu_raw` 0, `mcu_status` 1.

**Read 1 returned, read 2 never did.** The wiring fix held: the mirror leaf at
`0x0604E000` is `0x401b34c3`, a real mapping with the same attribute bits as the
code leaf `0x401c34c3`.

**Every address on both paths was enumerated; read 2 has exactly one bit 9 = 1:**

```
read 1  L0 0x40077000  L1 0x40078000  L2 0x4007b040  L3 0x4007b070  data 0x401c3400   all 0
read 2  L0 0x40077000  L1 0x40078000  L2 0x4007f180  L3 0x4007f270  data 0x401b3400   one 1
```

The `1` is the L3 descriptor that turns `VA 0x0604E400` into a page - an address
no data access ever names. So bit 9 does not only kill loads (2402's
`0x0100E200`, the vendor's first read at `0x01001BC4` -> PA `0x401b6bc4`); it
kills the table walk too. The transaction never completes and never errors,
which is why `as_fault` stays 0 and `mcu_status` stays 1.

**Cold fetch is not the explanation.** Read 2 is the series' first uncached
table fetch, so "cold" and "bit 9" arrive together - but the reset vector
`0x0100E001` makes the core's very first fetch a cold walk through
`0x40077000` -> `0x40078000` -> `0x4007b040` -> `0x4007b070`, all bit 9 = 0, and
it executes the ladder. Every build in this series that reached the ladder
started that way.

Consequences: a page is walkable only if `(VA >> 18) & 1 == 0`. The code section
`0x01000000..0x0100ffff` satisfies it for all sixteen pages, which is why the
ladder runs. The mirror at `0x06040000..0x0604ffff` does not - every page there has
`(VA >> 18) & 1 == 1`, so no offset in it would have worked, `0x0400` or not.

**Manifest fixed.** `csf_mirror_code` said `0x3000000` and `csf_leaf_probe_va`
listed the 2401 four for every `--mirror-code` build - 2404/2405/2406 all carried
the wrong values, i.e. the 2405 mistake frozen into the evidence record. Both now
come from `chip_spec()`; 2404 and 2406 still rebuild byte for byte, 298 tests.

**Next (2407, not built): sample the registers that would explain it** -
`c->gpu+0x004`, `+0x048` (L2_CONFIG), `+0x0c`, `+0x100..0x11c`, `+0x2c0..0x2cc` -
through the existing `platform_state` path. If bit 9 selects an L2 slice and one
slice is masked off, `0x048` says so; if it is symmetric, the slice theory dies
and the EMI/address-decode direction is next.

## >>> PREVIOUS 2026-11-08 13:31: 2406 BUILT - 2405 WORKED, BUT ITS MIRROR WAS AT THE WRONG VA <<<

**2405 answered the instrument question and nothing else.** `input_va` 2,
`shared+12` `0x0f10f857`, `0xdeadbeef` gone: marker 2 with a DSB behind it means
read 1 completed, and its word landed. The warm bit-9 = 0 read of the executing
page is now confirmed by data, in the same boot as a bit-9 experiment.

**It could not ask the walk question.** `error` -54, `as_fault` `0x0604e400`:
the ladder read an unmapped VA. The shim had been compiled with
`SWEET_CSF_MIRROR_CODE_VA` = `0x03000000` (`mov w10, #0x3000000`) because the
builder still chose it with a hardcoded `build == 0x2404` test, while
`TRACE_PROBE[0x2405]` said `0x06040000`. The leaf-VA table in `Image-bare` was
the 2401 list for the same reason.

Both values now come from `chip_definitions(build_id, mirror_code)`, which reads
`TRACE_PROBE` and raises when `--mirror-code` disagrees with it; a unit test pins
2401/2402/2403/2404/2405/2406 and 2404 still rebuilds byte for byte. The decoder
now checks the leaf at `0x0604E000` first and reports `mirror-not-mapped` instead
of `not-relocated`.

2406 = 2405's program, ladder and addresses, with the wiring fixed: image
`38389ecf...c0f9`, kernel `2805ae74...e4d` (`SWEET_BUILD_ID 0x2406`, patch 0202),
partition `9f3c5f90...8f85`, mirror `0x06040000` -> `0x401b3000`, 297 tests /
3 skipped, preflight passed, `boot_a` still `2931647a...86b1`. **Not flown.**

## >>> PREVIOUS 2026-11-08 13:24: 2405 BUILT - THE SAME ACCESSES, AN INSTRUMENT THAT CAN REPORT <<<

2404 could not answer its own question: markers had no barrier behind them and
`shared+12` was never seeded, so "read 1 stalled" and "marker 2 lost in the store
buffer" print the same report. 2405 changes no address - it adds `DSB SY` after
every marker store and every result store (9 in total, ladder 88 -> 120 bytes) and
has the shim seed `shared+12` with `0xdeadbeef` immediately before `MCU_CONTROL`,
failing closed if the seed does not read back.

Readings: marker 1 + seed intact means read 1 never stored, i.e. a warm bit-9 = 0
read stalled; marker 1 + seed replaced means read 1 returned and the core died
before marker 2; marker 2 + `0x0f10f857` means read 1 returned and the bit-9 walk
is the wall; marker 2 + any other word means read 1 translated to the wrong PA.

The build recipe is no longer guessed: rebuilding 2404 from the recorded inputs
reproduced `3c58fb31...cecd` byte for byte, so the same command with
`--build-id 0x2405` is pinned in `docs/matisse-gpu-mcu-wall.md` section 55.

Image `f53cde64...b8ace`, kernel `4a289747...fd5` (`SWEET_BUILD_ID 0x2405`, patch
0201), partition `af89e9a8...bfbd`, 295 tests / 3 skipped, preflight passed,
`boot_a` still `2931647a...86b1`. **Not flown - awaiting approval.**

## >>> PREVIOUS 2026-11-08 13:05: 2404 RAN - MARKER 1 ONLY, AND THE DATA SLOT WAS FILLER <<<

Flew `3c58fb31...cecd`, `boot_a` restored to `2931647a...86b1`. No fault, MCU still
enabled, `error` -53, `input_va` 1, `output_va` `0x04003000`.

**The build did relocate exactly as planned.** `firmware_probe_pa` `0x401b5000` is
the firmware base for VA `0x01000000`, the live code leaf `0x401c34c3` is base +
0xE000, the mirror leaf `0x401b34c3` has the same attribute bits, and the ladder at
0xE000 really is this build's 88 bytes. The first decode said `not-relocated`
because it compared the base against the probe page; that check now requires the
base plus `code_leaf == base + 0xE000` (68 evidence tests pass).

**`0x04003000` is not a read result.** 2402's shipped ladder contains no store to
`shared+12` at all - it writes markers only - yet 2402's flight read the same word
from that slot. The arena arrives uninitialised, so the slot holds filler until the
ladder writes it. 2404 therefore cannot say what read 1 returned, and the decoder
no longer scores the word at marker 1.

**So the descriptor question is still open**, because marker 1 is written *before*
read 1 and nothing in 2404 separates "read 1 stalled" from "marker 2 was still in
the store buffer behind a stalled read 2". 2402 and 2403 both got `0x0100E400`
back, which makes a stalled baseline unlikely - but that is an argument, not a
measurement.

**2405 = instrument first, same addresses.** `dsb sy` after every marker store and
after the result store; the kernel seeds `shared+12` with `0xDEADBEEF` before it
writes `MCU_CONTROL`; the four accesses stay identical to 2404. Then marker 1 +
intact sentinel means read 1 stalled, marker 2 + `0x0f10f857` means the bit-9 walk
is the wall, and marker 2 + any other word means read 1 translated to the wrong PA.
The 0x48 / 0x2C0 L2-slice snapshot moves to the round after that.

## >>> PREVIOUS 2026-11-08 12:45: 2404 BUILT - CAN THE MMU READ A DESCRIPTOR AT PA BIT 9 = 1? <<<

**The one question that decides whether the address is unfixable.** 2401..2403 left
a single invariate: every MCU access with address bit 9 = 1 hangs and every access
with bit 9 = 0 returns correct data. That is either an address that is dead for
the whole GPU side, or a defect confined to the MCU's own fetches and loads. 2404
separates the two by making the *page walk* read a descriptor at bit 9 = 1.

**Why 0x06040000.** A descriptor's position is an address too. With the executable
section mirrored at `0x06040000`, `L2[48]` sits at table offset `0x180` (bit 9 = 0)
and the mirror's fresh L3 page holds the 64 KiB section at indices `0x40..0x4F`,
i.e. byte offsets `0x200..0x278` - every one of them PA bit 9 = 1. Reading
`0x0604E400` needs a cold walk that fetches its last descriptor at bit 9 = 1, while
the access itself is VA bit 9 = 0 and PA bit 9 = 0 (`0x401b3400`) and names the very
same word as `0x0100E400`.

`0x08000000` was rejected as the mirror base: the Cortex-M7 window decoders on this
family are documented as taking over `0x08000000..0x3FFFFFFF`, and a mis-decode
there would look exactly like a hang. Everything stays below `0x08000000`.

**The leaf is valid on purpose.** An unmapped entry would fault the moment the walk
succeeded and end the run, throwing away reads 3 and 4 - and those are the only
measurements of the store direction anyone has.

```
marker 1  read  0x0100E400   bit9 0, warm        the word must be 0x0f10f857
marker 2  read  0x0604E400   bit9 1 descriptor   the same word, cold walk
marker 3  store 0x5a5a5a5a -> 0x04000200 (bit9 1) + DSB SY
marker 4  read  0x04000200   bit9 1             read-after-write
marker 5  everything returned
```

Every read stores its word to `shared+12`. `shared+16` is the `groups` counter and
`shared+20` is `group_stride`, which the decoder validates as a length - a
`0x5a5a5a5a` there would have made it reject a perfectly good run.

| item | value |
|---|---|
| image | `3c58fb31...cecd`, 26,714,112 B, arena `0x77000` |
| kernel | `04110196...a281`, `SWEET_BUILD_ID 0x2404`, patch 0200 |
| relocated | section `0x401b5000`, probe VA `0x0100E000` -> `0x401c3000` |
| mirror | section `0x401a5000`, entry `0x0604E000` -> `0x401b3000` |
| leaves | `0x30000000401c34c3` / `0x30000000401b34c3` / `0x30000000401b64d7` |
| ladder | 88 B, `tools/matisse-csf-ladder2404.S`, 4-byte aligned |
| container | 130 B changed vs 2403: vector word + 88 B at `0x0100E000` |
| tests | 292 ran, 3 skipped |

Readings: `input_va = 1` the build is wrong. `2` the walk died on a bit 9 = 1
descriptor => the address is dead below the page table and no leaf, attribute or VA
can reach it; the next lead is the GPU L2 slice select (`0x48` HASH / `ASN_HASH`).
`3` the walk returned and the store did not => both directions die, an address
decode fault. `4` the store completed and the read back hung => the address decodes
and accepts writes, only the read response is missing. `5` with `shared+12 =
0x5a5a5a5a` => the block heals once written. `0xe3` a synchronous fault, stacked PC
in `output_va`, CFSR in `group_stride`.

**Status: built, unit-tested, statically verified, preflight passed; not flown.**
`boot_a` is `2931647a...86b1`; the partition hash after writing this image is
`abc9a9ce...a11a`.

## >>> PREVIOUS 2026-11-08 12:21: 2403 RAN - THE VA PREFIX IS OUT; THE WALL IS THE ADDRESS BIT ITSELF <<<

**RESULT: `input_va = 2`.** One read returned, the second never did:

| marker | read | VA | bit 9 | leaf | outcome |
|---|---|---|---|---|---|
| 1 | `0x0100E400` | code `0x0100xxxx` | 0 | `0x401b34c3` | **returned, word = `0x0f10f857`** |
| 2 | `0x0300E200` | alias `0x0300xxxx` | 1 | **same word** | **never returned** |
| 3 | `0x01001200` | code, uncached+PBHA0 | 1 | `0x401a64d7` | never issued |
| 4 | `0x0100E200` | code, 2402's address | 1 | same as 1 | never issued |

`groups = 8`, no `0xE3`, `as_fault = 0`, `mcu_status = 1`, `error = -53`. No fault,
no response, exactly like 2402.

**The alias travelled and is byte-identical.** The live leaves prove the image is
what it claimed:

```
0x0100E000  0x00000000401b34c3   PBHA 0  cached  RO   <- code page
0x0300E000  0x00000000401b34c3   PBHA 0  cached  RO   <- slot 24 copied slot 8
0x01001000  0x00000000401a64d7   PBHA 0  AttrIdx 5    <- the uncached page
0x02000000  0x0060000040091443   PBHA 0  cached  RW
```

`alias_applied`, `uncached_page_applied`, `pbha_cleared`, `relocation_observed`
all true; `firmware_probe_pa = 0x401a5000`, i.e. the arena page shift was
anticipated correctly.

**Three things die with this run.**

1. **"The `0x0100xxxx` VA window is special."** The alias walks the identical L2
   entry, L3 page, leaf word and physical word through `0x0300xxxx` and stalls
   anyway. The refusal is not keyed on the virtual range. This was the last
   surviving form of the window theory.
2. **"Some leaf encoding is the lever."** With PBHA cleared on every leaf the
   code page became cached + PBHA 0 - a cell never measured before - and bit
   9 = 1 still stalls. Measured cells at bit 9 = 1: cached+PBHA 6 (2402),
   uncached+PBHA 6 (2400), cached+PBHA 0 (this run). All dead. The matrix is
   3/4, not 1/4.
3. **"Maybe the returned bytes were wrong all along."** They are not. Read 1
   returned the vendor word `0x0f10f857` from `0x0100E400` - the first data
   verification in this whole series - so every earlier "returned" now rests on a
   measured data path, not an assumption.

**What is left.** Across 2401..2403 the stall now has one invariate: the MCU
access carries address bit 9 = 1. It has been observed with fetches and data
reads, in three virtual ranges (`0x0100`, `0x0300`, `0x0400`), two sections (code
and shared - the stack has never been probed at bit 9 = 1), at least four
physical pages, and every leaf encoding tried. Reads at bit 9 = 0 return correct data. Nothing in the
page table moves it, and per `AS_TRANSCFG = 0x42000006` (`ADRMODE 6 =
AARCH64_4K`) nothing in the page table *can* move it: `PA[11:0] == VA[11:0]`
always.

**2404: the two dimensions never touched - direction, and the last matrix cell.**

```
1 read  0x0100E400 (b9 0)  -> shared+12   baseline + data check 0x0f10f857
2 read  0x04000000 (b9 0)  -> shared+16   the shared page at an even 512B block
3 read  0x04000200 (b9 1)  -> shared+20   uncached + PBHA 0: the 4th cell
4 store 0x5a5a5a5a -> 0x04000200 (b9 1)   does a WRITE complete where the read
                                          in 2401 did not? same address, other
                                          direction
5 read  0x04000200 (b9 1)  -> shared+24   read-after-write, and is it 5a5a5a5a
6 read  0x01001200 (b9 1)  -> shared+28   the 4th cell on the code page too
7 all six returned
```

Read 3 comes before the store on purpose: it is a read, so if it returns we learn
the last attribute cell works *and* the run continues; if it stalls it costs one
marker and the store still gets issued. The store and read 5 use the same address
2401 stalled on, in a page that is RW, so the store tests the bus, not the MMU's
AP bits. `5a5a5a5a` in `shared+24` would be proven by comparing it in the decoder.

**Reading it.** Store stalls (3) => the odd 512 B blocks are dead in both
directions: an address-decode/route problem, and no page-table or attribute
change will ever boot the stock firmware. Store passes, read 5 stalls => the
address decodes and accepts writes, only the read response never returns - a
different bug class with a different owner. Read 3 returns => uncached + PBHA 0
is the working corner and every leaf the firmware touches must be built that way.
Read 3 returns *and* read 5 returns `5a5a5a5a` => the block heals once written,
which would point at cache/tag state rather than decode.

```
image      83372fdc...0a63  partition written and read back
fastboot   85.6 s (2401 82.5 s, 2402 101.1 s); runner finished the restore itself
boot_a     restored and verified 2931647a...86b1, no manual step needed
kernel     0x2403, patch 0199, 289 tests / 3 skipped
```

## >>> PREVIOUS 2026-11-07 23:52: 2402 RAN - BIT 9 IS THE WALL, AND IT IS THE ONLY MOVING PART <<<

**RESULT: `input_va = 4`.** The ladder ran from `0x0100E000` and wrote all four
markers, so three reads returned and the fourth never did:

| marker | read | section | bit 9 | outcome |
|---|---|---|---|---|
| 1 | `0x04000000` | shared | 0 | returned (first read ever made there) |
| 2 | `0x02000000` | stack | 0 | returned (cold; also returned in 2375) |
| 3 | `0x0100E400` | code | 0 | **returned** - cold line in the page we execute from |
| 4 | `0x0100E200` | code | 1 | **never returned** |
| 5, 6 | - | - | 1 | never issued |

`groups = 8`, no `0xE3`, `as_fault = 0`, `mcu_status = 1`, `error = -53`: the
read reached the bus and no response ever came back. It is not a fault.

**Reads 3 and 4 differ in exactly one address bit.** Same 4 KiB page
(`0x0100E000`), same L2 entry, same L3 entry, same leaf word, same physical page,
0x200 apart, no walk involved for either. They also differ in bit 10
(`0x0100E400` has it set and returned), so bit 10 is not a factor - only bit 9
correlates.

**The image is exactly what the build said it was.** `firmware_probe_pa =
0x401a4000` and the four live leaves are the predicted words, so the pre-flight
correction (2402 uses 2400's relocated PA, not 2401's) was right:

```
0x01000000 -> 0x30000000401a44c3    0x0100E000 -> 0x30000000401b24c3
0x01001000 -> 0x30000000401a54c3    0x0100F000 -> 0x30000000401b34c3
```

**Two theories die with this run.**

1. **"A cold data read of an RX page never completes"** (2373/2374). Read 3 is
   exactly that - a cold line, in an executable page, in the page the core is
   fetching from - and it returned.
2. **"The wall is the `0x0100xxxx` window, or a section, or a leaf encoding."**
   It has now been observed with a fetch (2386, 2393) and a data read (2393..2402),
   in three sections, under every leaf encoding tried, cached and non-cacheable,
   with and without the mirror. Bit 9 is the only property that never varies.

**Bit 9 can never be split into a VA half and a PA half.** `AS_TRANSCFG` reads
back `0x42000006`, i.e. `ADRMODE = 6 = AS_TRANSCFG_ADRMODE_AARCH64_4K`: the AS is
a plain AArch64 4 KiB stage-1 MMU. Its output address is 4 KiB aligned, so
`PA[11:0] == VA[11:0]` for every mapping that can be built - bit 9 included.
2382's PA move and 2399's leaf repoint could not have separated them, and no
future page-table change can either.

**What that means for the project.** The vendor firmware's own first data read
(`0x01001BC4`, bit 9 = 1) is in the dead half, so the stock firmware cannot boot
while this holds, and no page table can route around it. The remaining question
is no longer the MMU. It is what makes `A9 = 1` fatal for the MCU and not for the
CPU: the CPU wrote that whole 64 KiB section, bit-9 = 1 halves included, and read
the arena back.

```
image  e7f00f28...e329  partition a9441792...feaf written and read back
fastboot observed at 101.14 s, Recovery 18 s after fbraw reboot-recovery
boot_a restored and verified 2931647a...86b1 (capture 23:49)
kernel 0x2402 (patch 0198), 286 tests
```

**Next, 2403 (superseded design).** This section originally proposed splitting
load from store at bit 9. The build that was actually made is the VA-alias test
described in the ACTIVE section above; the store/load split is queued for 2404.

```
1 read  0x0100E000 (b9 0)  -> store the word to shared+16   value check
2 read  0x0100E1FC (b9 0)  -> store the word to shared+20   last word of the even half
3 store 0x5a5a5a5a to 0x0100E200 (b9 1)                     does a write complete there?
4 read  0x0100E200 (b9 1)  -> store the word to shared+24   and does the read still stall?
5 read  0x0100E400 (b9 0)                                   still alive
```

A stall at 3 says the address itself is dead for both directions. Passing 3 and
stalling at 4 says the address decodes and accepts writes, and only the read
response never comes back - which is a different bug with a different fix. A
value that does not match the image at step 1 would put every "returned" in this
series in question.

## >>> PREVIOUS 2026-11-07 23:45: 2402 BUILT - 2401 RAN AND THE FIRST NON-CODE BIT-9 READ STALLS <<<

**2401's result was `input_va = 1`.** The ladder ran from the mirror at
`0x0300E000` (its marker 1 is in shared and nothing else writes that word), then
the first read - shared `0x04000200` - never completed. Both "control" reads in
that ladder were bit-9 = 1 addresses inherited from 2396, so it could not get
past read 1 and said nothing about the mirror. The mirror plumbing itself was
proven: the four leaves were the predicted words and `mirror_applied`,
`alias_applied` and `relocation_observed` were all true.

**2402 dropped the mirror** so only the read sequence moved: 2400's layout, reset
word `0x4 = 0x0100e001`, ladder back at `0x0100E000`, 72 bytes. Two design
changes against the sketch, both forced by the fact that a stall ends the run:

- **All bit-9 = 0 reads go first.** The earlier order put `0x04000200` second and
  would have stopped at the address 2401 had already answered.
- **The code pair is `0x0100E400` vs `0x0100E200`**, not `0x0100E000` vs
  `0x0100E200`: neither probe is the entry instruction and both sit the same
  distance from the page base.

```
image      e7f00f28...e329  26,714,112 B  arena 0x77000 (2400's layout)
kernel     ff842023...27ba  SWEET_BUILD_ID 0x2402, patch 0198
container  115 B changed: vector word, 72 B at 0x0100E000, 40 B at 0x010019b0
tests      286 ran, 3 skipped
```

## >>> PREVIOUS 2026-11-07 23:40: 2401 REBUILT - OWN-PAGE READ + 0xE3 FAULT ENTRY <<<

The rebuild that flew. Same manipulation (mirror at `0x03000000` through a fresh
L3 page, `L2[40]` reusing `L2[8]`'s L3 page, reset `0x0300e001`), plus: read 3
became `0x0300E200` (the page the ladder is fetched from), markers shifted to
4 `0x03001200` / 5 `0x05001200` / 6 `0x01001200` / 7 all returned, the ladder grew
to 84 bytes, and the fault entry at `0x010019b0` now writes `input_va = 0xE3`
(stacked PC to `output_va`, CFSR to `group_stride`) from its own source file and
constant, so 2383..2400 keep their bytes.

Two build-metadata bugs were fixed on the way, and the flight proved the fix:
`mirror_check()` had added its stand-in base `0x40077000` to arena offsets (every
mirror PA in 2399/2401's manifest was `0x1000` low) and had rebuilt the arena
without the vendor leaf macros (recording `0x…cc7` where the image ships
`0x…4c3`). The four live leaves now match the manifest exactly.

## >>> PREVIOUS 2026-11-07 13:30: 2401 BUILT - 2396..2400 NEVER RAN THEIR FIRST TWO READS <<<

**The 2396..2400 ladder was broken, not the controls.** Those builds pinned
`f8d40200` / `f8d60200` where `ldr.w` needs `d4f80002` / `d5f80002`. Capstone on
the exact manifest bytes decodes the first pair as `bmi` + `movs r2,r0` and the
second as `bvs` + `movs r2,r0` (`lsls` left N=V=0, so neither branch is taken).
Markers 1 and 2 were still written, so `input_va = 3` named a *pending* third
read: the shared read at `0x04000200` and the stack read at `0x02000200` never
executed. Every "shared returned / stack returned" sentence in 2396..2400, and
2399's "the same physical word is readable through the stack VA", is therefore
unsupported.

**What survives.** Each of 2393, 2395, 2397, 2398, 2400 changed only the code
leaf or its physical page, and the one read that did run (`0x01001200`) stalled.
So AttrIdx/MemAttr, cacheability in both directions, AP, SH, nG, XN, group/PBHA
and physical page are still null *for that read*, and a fetch at `0x0100E000`
still runs. 2400's "a non-cacheable page still stalls" is valid; its controls
were not.

**2401 fixes the encoding and adds the two missing controls.** The ladder pins
`d4f80002` / `d5f80002` and an assembly test compares linked bytes with the
manifest, so this cannot regress silently. *That build was superseded at 23:40:
the reshape, the corrected leaf values and the new image SHA are in the active
section above.* Its ladder order was 1 `0x04000200`, 2 `0x02000200`,
3 `0x03001200`, 4 `0x05001200`, 5 `0x01001200`, 6 all returned.

## >>> PREVIOUS 2026-11-07 12:40: 2400 RAN - NON-CACHEABLE STILL STALLS; THE PAGE TABLE IS OUT OF LEVERS <<<

**Correction 2026-11-07 13:30: the "shared and stack reads returned" claims below
are void (see the active section). Only the `0x01001200` read ever executed.**

**RESULT: `input_va = 3`.** 2400 kept 2396's container and ladder and changed
only the cache mode of one leaf: VA `0x01001000` takes AS_MEMATTR index 5 with no
SH bits (`leaf_0x01001000 = 0x30000000401a54d7`), the entry page and every other
leaf keep `0x...4c3`. The read at `0x01001200` stalled anyway.

```
image  fff61b73...84b3  26,714,112 B  kernel a321ee94 (SWEET_BUILD_ID 0x2400)
container d59eb487...0ba8 - byte-identical to 2396..2399 (93 B vs vendor)
leaves 0x30000000401a44c3 0x30000000401a54d7 0x30000000401b24c3 0x30000000401b34c3
probe_page_uncached true (AttrIdx 5, SH 0)
part.  bb4cf321...c63e written and read back, fastboot 121.28 s
boot_a restored 2931647a...86b1 (verified)
```

**The page table has nothing left.** 2393 AttrIdx/MemAttr, 2395 cache in the
fetch direction, 2400 cache in the data direction, 2378 AP, 2374 SH, 2393 nG,
2397 XN, 2398 group/PBHA, 2399 physical page - all null. A fetch from the same
window at `0x0100E000` still completes and runs the ladder; a data read at
`0x01001200` never does, cached or not.

**Also checked, in reply to an outside analysis.** The registers it blamed were
already at vendor values in this capture: `0x304` 0 -> 31 (readback 31,
`noncoherent_protocol_verified` true), AS_MEMATTR `0x888d8f88/0x00084c8d`,
AS_TRANSCFG `0x42000006` = ADRMODE 6 + PTW_MEMATTR_WB + R_ALLOCATE, exactly the
r32p1 pairing. XREADABLE (bit36) and DISABLE_AF_FAULT (bit34) do not exist in the
r32p1 regmap and panthor, the working driver, does not set them either. Its
"PBHA = 0b0011 at bits 63:60" reading is off by a nibble: the field is bits 62:59
and the value was 6, which 2398 already cleared to 0 with no effect.

**Next: 2401 maps the same code section at a second window.** The open question
is whether the wall is the `0x01000000` window or that VA value: map the code
section again at `0x03000000`, reset-vector a ladder at `0x0300E000`, and read
`0x03001200`. Runs and reads -> the window is the property and the firmware could
move; stalls -> the VA value itself is hardwired somewhere above the AS.

Tests: 277 ran, 3 skipped (one memory-builder test and one decode test added for
2400). Patch series is 0001-0196.

## >>> PREVIOUS 2026-11-07 12:15: 2399 RAN - THE WALL IS THE VIRTUAL RANGE, NOT THE PHYSICAL PAGE <<<

**RESULT: `input_va = 3`.** 2399 repointed exactly one leaf: VA `0x01001000`
(the page holding the read target `0x01001200`) now names the physical page behind
VA `0x02000000`, the stack page read 2 was meant to touch. Read 3 stalled on that
leaf anyway.

**Correction 2026-11-07 13:30:** read 2 never executed (the ladder's `f8d6 0200`
is `bvs`+`movs`, not `ldr.w`), so "both reads hit the same physical word
`0x40091200` and read 2 returned" is false. The only measured fact is that the
same read at `0x01001200` stalls when its leaf names the stack page.

```
image  284b95b2...f453  26,714,112 B  kernel 13743a97 (SWEET_BUILD_ID 0x2399)
container d59eb487...0ba8 - byte-identical to 2396/2397/2398 (93 B vs vendor)
leaves 0x30000000401a54c3 0x30000000400914c3 0x30000000401b34c3 0x30000000401b44c3
part.  17f12bce...ffe0 written and read back, fastboot 87.84 s
boot_a restored 2931647a...86b1 (verified)
alias_applied true - the leaf at 0x01001000 is PA 0x40091000 with the code
section's own attribute bits
```

**What it closes (corrected).** The wall does not follow the code section's own
physical pages: pointing the leaf at the stack page did not let the read
complete. It does **not** show that the PA is readable through the stack VA,
because that read never ran, and the alias kept the code attributes, so the
attribute class is still open.

**Build note.** The alias helper costs 0x2cc bytes of shim text and pushed the
0x4000-aligned BSS array ahead of the arena by one page: this build's arena is
`0x40078000`, so every PA is 2396's +0x1000. The builder now pins the expected
arena per build (`0x78000` for 2399) instead of relaxing the check, and the
manifest records it.

**Next: 2400 separates "attributes" from "the VA itself".** 2399 moved only the
PA and kept the code section's attribute bits, so the attribute class is still
open. 2400 copies the stack page's whole descriptor (RW, NX, AttrIdx, SH, group)
onto VA `0x01001000`, same PA, and reads `0x01001200`. Returns -> the wall is the
attribute class and 2400 bisects it; stalls -> the wall is the virtual range
itself and only AS/platform config is left.

Tests: 274 ran, 3 skipped (one new alias test in `test_mali_csf_memory`, one new
2399 decode test in `test_matisse_gpu_evidence`). Patch series now 0001-0195:
0194 is 2398's missing identity, 0195 is 2399. Replay is byte-identical to the
local tree.

## >>> PREVIOUS 2026-11-07 01:05: 2398 RAN - GROUP TAG OUT; THE LEAF IS EXHAUSTED <<<

**RESULT: `input_va = 3`.** 2398's container is 2396's byte for byte; the only
change was clearing the physical memory group tag (leaf bits 59..62) from 6 to 0.
The leaves read back `0x401a44c3` / `0x401a54c3` / `0x401b24c3` / `0x401b34c3`,
tags `[0,0,0,0]`, and the code read stalled anyway.

```
image  d953fa3a...ef47  26,714,112 B  kernel aa81f1e1 (SWEET_BUILD_ID 0x2398)
part.  e56f242d...134b written and read back, fastboot 83.40 s
boot_a restored 2931647a...86b1
```

The tag was worth a flight because no driver ever writes one: kbase uses the
group id as an allocation hint only (`kbase_native_mgm_alloc` marks it
`CSTD_UNUSED`) and the working MT6993 port writes 0. The shim's 6 had no vendor
grounding.

**The leaf is now exhausted**: AttrIndx/MemAttr (2393), cacheability (2395),
AP (2378), SH (2374), nG (2393), XN (2397), group tag (2398) - all null.

**References checked, no new variable.** x9 (MT6993, CSF running) is structurally
identical to us - same leaf encoding, MEMATTR, TRANSCFG, MCU_CONTROL=2, JOB
bit31 wait; its extras are platform-only (SMMU bypass, L2 power, shader
delegation) and the vendor MT6983 kbase has no iommu code at all. OnePlus's
MT6983 kernel is byte-identical to Xiaomi's in this path.

**Next: 2399 decides which side owns the bit.** Alias VA `0x01001000` onto a
stack page (PA `0x40091000`, so the read at `0x01001200` lands at PA
`0x40091200`, bit 9 still set). Returns -> the wall follows the code section's
physical pages and the firmware allocation can move. Stalls -> it follows the
virtual range and no mapping change can fix it.

## >>> PREVIOUS 2026-11-06 23:59: 2393 RAN - VENDOR PAGE ATTRS, SAME 512 WALL <<<

**RESULT: no landing at `0xEA00` / `0x1000` / `0x18EC`. The leaf readback is
`0x4C3`, so the image really ran with vendor page attributes (AttrIdx 0/5, no
nG, read-only code) - and the 512 wall did not move.**

```
image  b6c4efa3...e077  26,714,112 B  kernel 475a9a4c (SWEET_BUILD_ID 0x2393)
part.  642fafcf...8b53 written and read back, fastboot 86.5 s
boot_a restored to 2931647a...86b1 (verified)
outcome cold-boot-fetch-stalls
```

This kills the attribute hypothesis from the vendor audit. One thing is still
missing: a positive control at a known-good address under the same encoding.
2394 does that at `0xE000`. If it runs, the 512 rule is below the driver; if it
also stalls, the vendor encoding itself broke the start and 2393 says nothing.
See `docs/matisse-gpu-mcu-wall.md` section 38.

## >>> PREVIOUS 2026-11-06 23:27: 2391 RAN - NO LANDING; THE FALLBACK READING IS DEAD <<<

**RESULT: none of the three landings wrote. `input_va` stayed at the seed
`0x04002000`, `groups = 8`, `mmu_raw = 0`, `as_fault = 0`, `mcu_status = 1`,
`relocation_observed = true`, `cleanup_error = -53`.**

```
image  372fb8ea...d3dc24  26,714,112 B  kernel 8df00489 (SWEET_BUILD_ID 0x2391)
part.  573cb892...9dfcb71 written and read back, fastboot 89.65 s
boot_a restored to 2931647a...86b1 (verified)
outcome cold-boot-fetch-stalls
```

The word at VA 0x4 was `0x01001A01`; twenty-byte programs sat at `0x1A00`
(literal), `0x1000` (page base) and `0x18EC` (vendor fallback). None ran, so
there is no fallback: `0x18EC` is reachable only when the vendor word names it.
2390 looked like a fallback because the vendor word already pointed there.

**New rule candidate.** All four failing targets - `0x200`, `0x600`, `0x1200`,
`0x1A00` - are 512-byte aligned but not 4 KB aligned. The successes are either
4 KB page bases (`0xE000`, `0x1000`) or not 512-byte aligned (`0x18EC`). In page
1 the same leaf `0x401a5000` carries `0x1000` (runs), `0x1200` (nothing),
`0x18EC` (runs), `0x1A00` (nothing): the only separating property is the low
9 bits.

**Vendor audit (2026-11-06 23:40).** The r32p1 driver has no reset-entry or
512-byte constraint at all: boot is one `MCU_CONTROL=2` write plus a wait on
`JOB_IRQ.bit31`. But the current image is **not** vendor-faithful in its page
attributes: AttrIdx 1 / MEMATTR `0x4c4c9f4c` / leaf nG / writable code, versus
vendor AttrIdx 0 / `0x888d8f88` / no nG / read-only code. 2380 verified the
vendor values; 2381-2391 never enabled them again. So the 512 rule is demoted
to "observed under the current attribute encoding". Details:
`docs/matisse-gpu-vendor-audit.md`; next is 2392 (single variable) then 2393
(vendor attributes).

Caveat: this is a cross-build fit, not a controlled test. 2392 repeats it at
`0x0100EA01` inside the known-good `0xE000` page. Details in
`docs/matisse-gpu-csf-status.md` and `docs/matisse-gpu-mcu-wall.md` section 37.

Commit `9830e14` also backfills identity patches 0183-0188 (2385 is skipped:
its kernel is byte-identical to 2384). Tests: 262 ran, 3 skipped.

## >>> PREVIOUS 2026-11-06: 2390 RAN - THE VENDOR ENTRY RUNS; THE MASK READING IS DEAD <<<

**RESULT: `input_va = 0x010018ec` - the marker is present at the vendor's own entry,
with the reset vector word left exactly as it ships (`0x010018ed`).**
`mmu_raw = 0`, `as_fault = 0`, `mcu_status = 1`, `relocation_observed = true`,
`error = -53`, and the leaves read back as planned.

```
image  9051fedf...5fff3e  26,714,112 B   kernel 1760629a (SWEET_BUILD_ID 0x2390)
part.  2123d7d2...4d8a232  written and read back, fastboot 111.67 s
boot_a restored to 2931647a...86b1 (restored_sha256 verified)
outcome vendor-entry-executed
```

Two marker programs, one word untouched. 0x010018ec is the address the vendor word
names; 0x01001000 is the page base below it. The core wrote 0x010018ec, so it went
where the word says - the vendor entry is reachable in this port.

**This retracts #35.** "Only a page-aligned start executes" cannot be true: 0x18ec
is neither 4 KB nor 512-byte aligned. 2385 and 2389 both pointed at addresses that
happen to be page bases, so both readings fitted the same two successes and only
2390 could tell them apart. It did.

What survives is the part #35 got right by accident and now has a direct proof for:
`SWEET_CSF_RESET_ENTRY_VA` (0x010018ec) is the vendor entry, and the firmware does
start here. `version = 0` / `firmware_ready = 0` therefore do not mean "never
started"; they mean it starts and then hangs.

**What is not settled.** 2386, 2387 and 2388 put the same twenty bytes at
0x01000200, 0x01000600 and 0x01001200 with the vector pointing at them, and none of
them ran. Those three are real non-starts, not stale evidence: their
`cleanup_error` is -53 (the MCU never reached a state the halt handshake could
stop) while 2385/2389/2390 all report 0. A container-level audit of all six images
against the vendor blob shows every difference inside the intended ranges, so this
is not build contamination.

That leaves 2390 ambiguous between two readings, and the next build separates them:

- **exact** - the vector is honoured as written, and the three failures are about
  those addresses specifically (0x200, 0x600, 0x1200 - all 512-byte aligned)
- **fallback** - a non-page-aligned vector is ignored and the core starts at the
  vendor entry anyway, which is why 2390 marked 0x010018ec

Both explain all six trials; only a non-aligned vector pointing somewhere *else*
can tell them apart.

**Also established offline:** `vendor_a-mali_csffw.bin` and
`vendor_a-mali_csffw_reload.bin` are the same 258,048 bytes (sha `de22d2fc...`), so
"the device boots a different blob" is out.

**NEXT: 2391 - vector to 0x01001A01, programs at 0x01001A00 and 0x010018EC.**
0x1A00 is inside the code section, 512-byte aligned and not page aligned, and
nothing has ever executed there. 2390's program stays at 0x18ec as the control:
marker 0x01001A00 means the vector is honoured as written and 2386-2388 need
another cause; marker 0x010018EC means a non-aligned vector is ignored and the
vendor entry started instead; no marker means neither reading holds.

## >>> PREVIOUS 2026-11-06:2389 RAN - ONLY A PAGE-ALIGNED START EXECUTES <<<

**RESULT: `input_va = 0x01001000` - the marker is present.** The same twenty bytes
that did nothing at 0x01001200 in 2388 ran at 0x01001000. `mmu_raw = 0`,
`as_fault = 0`, `mcu_status = 1`, `error = -53`.

```
image  607d911d...662d  26,714,112 B   kernel a9c0c9c7 (SWEET_BUILD_ID 0x2389)
part.  f56ff8f6...e5c1  written and read back, fastboot 85.51 s
boot_a restored to 2931647a...86b1 (restored_sha256 verified)
outcome cold-boot-fetch-completes
```

Five builds, one variable each, now line up:

| build | target | page offset | result |
|---|---|---|---|
| 2385 | 0x0100E000 | 0 | runs |
| 2389 | 0x01001000 | 0 | runs |
| 2386 | 0x01000200 | 0x200 | nothing |
| 2387 | 0x01000600 | 0x600 | nothing |
| 2388 | 0x01001200 | 0x200 | nothing |

2388 and 2389 differ by **one word** - the reset target inside page 1 - and one
of them runs. The page tables are identical in both and were read back from the
arena in 2388, so this is not translation. The rule the data supports: **the low
12 bits of the reset vector are ignored and the core begins at the page base.**

That also explains page 0 without needing it to be cursed: 0x01000200 and
0x01000600 both resolve to 0x01000000, where the vendor's own entry veneer sits
(`ldr r0,[pc,#0]` / `bx r0` into 0x010002ec). Our program never ran there - the
vendor's veneer did, and it hangs. The veneer looked like dead code because it
needs the boot ROM's register state, which only an entry from reset carries.

**Cross-checked against the real MT6983 vendor source** (`MiCode/Xiaomi_Kernel_
OpenSource`, branch `rubens-s-oss` = Redmi K50, MTK tag t-alps-release-s0.mp1...
mt6983, `mali-r32p1`). `kbase_csf_firmware_enable_mcu()` writes MCU_CONTROL =
`MCU_CNTRL_AUTO` (2) and waits for the global interrupt - exactly our sequence.
`convert_mem_flags()` reproduces the memattr pairing from 2380, and
`load_fw_image_section()` copies each section page by page from its data start.
**Nothing in the driver touches the reset vector**, so the vendor firmware relies
on the same word we do - and its value is 0x010018ed, i.e. page base 0x01001000.
The vendor's real entry is therefore the page base, not 0x010018ec, and
`SWEET_CSF_RESET_ENTRY_VA` has been pointing 0x8ec past the entry since 2376.

Open question this does not settle: if the vendor entry is 0x01001000, why has
the unmodified vendor path never reported ready here (`version = 0`,
`firmware_ready = 0`)? Either our AS still hands it something it rejects, or the
entry needs the boot ROM argument registers and something about the AS
programming loses them. That is the next thing to instrument, after 2390.

**2389 shipped without the leaf property** - the builder gate was written as
`build_id == 0x2388`, so the image had no `sweet-csf-leaf` and the decoder
refused it. Fixed to cover both builds; `--allow-missing-leaf` decodes this one
capture, and the marker was read out before that flag existed.

**NEXT: 2390 - the same program at 0x01001000, vector 0x01001201.** Only the
vector moves, from 0x01001001 to 0x01001201. A marker means the low bits are
dropped and 2388 is fully explained; no marker means an unaligned vector does not
start the core at all, which would leave the vendor's 0x010018ed unexplained and
make the entry word itself the next instrument.

## >>> PREVIOUS 2026-11-06:2388 RAN - THE TABLE IS RIGHT AND STILL NOTHING RUNS <<<

**RESULT: `input_va = 0x04000200` - no marker at 0x01001200.** Page 1 does not
execute either, from a vector at block 1. `mmu_raw = 0`, `as_fault = 0`,
`mcu_status = 1`, `relocation_observed = true`, `error = -53`.

```
image  549b62a3...c429  26,714,112 B   kernel 86d908a1 (SWEET_BUILD_ID 0x2388)
part.  3230042c...fabf  written and read back, fastboot 89.65 s
boot_a restored to 2931647a...86b1 (restored_sha256 verified)
outcome cold-boot-fetch-stalls
```

**The new instrument answered first, and it exonerates the page tables.** The
shim now reads the four live leaf descriptors out of the arena it hands the AS
and publishes them in their own 32-byte ADT property (`sweet-csf-leaf`, marks
420..423), so the capture carries the table the MCU walks rather than a plan:

```
leaf 0x01000000  0x30000000401a4c47  PA 0x401a4000
leaf 0x01001000  0x30000000401a5c47  PA 0x401a5000
leaf 0x0100e000  0x30000000401b2c47  PA 0x401b2000
leaf 0x0100f000  0x30000000401b3c47  PA 0x401b3000
```

Four adjacent entries of one L3 table, identical flags (`0xc47`: AttrIndx 1, AF,
RW because this build is `--ro-as-rw`), PAs exactly the relocated plan. No stale
entry, no shadowing, no second table. Every mapping hypothesis in this document
is now retired: the MCU walks the table we build.

That leaves a contradiction worth stating plainly. With the same program, the
same leaf shape and the same reset path, 0x0100E000 runs (2385) and 0x01000200,
0x01000600 (2386/2387) and 0x01001200 (2388) do not. The only structural
difference is that 0x0100E000 is 4 KB aligned and the other three are 512-byte
aligned. A reset-vector mask would be odd - the vendor's own vector is 0x010018ed,
not page aligned - but the vendor path has never been observed to run in this
port either, so it cannot be used to rule the idea out.

**Consequence to keep in view:** the only fetch this port has ever seen complete
is page 14. If that stays true, the vendor firmware has never started here and
every "firmware started" reading in this document is shim-side only.

**NEXT: 2389 - page 1 again, page aligned.** Same 20-byte program at 0x01001000,
reset word -> 0x01001001. Running there means page 1 does execute and the 0x1200
offset was the discriminator; not running means page 1 does not execute at all
and the alignment idea dies with it, leaving "which addresses can the core start
at" as the only open question.

## >>> PREVIOUS 2026-11-06:2387 RAN - PAGE 0 CANNOT BE FETCHED AT ALL <<<

**RESULT: `input_va = 0x04000200` - the marker is absent again.** The reset word
pointed at `0x01000601`, block 3 of the same page that holds the block 2386 could
not reach, and a block no build had ever patched. `groups = 8`, `mmu_raw = 0`,
`as_fault = 0`, `mcu_status = 1`, `relocation_observed = true`, `error = -53`.

```
image  9cca6494...95dd  26,714,112 B   kernel 5172beb0 (SWEET_BUILD_ID 0x2387)
part.  8d48f6d1...db88  written and read back
boot_a restored to 2931647a...86b1 (restored_sha256 verified)
outcome cold-boot-fetch-stalls   fastboot 83.48 s
```

So the bisect answered: the damage is **page-granular, not block-granular**. Two
blocks of page 0 fail (0x01000200, 0x01000600) and page 14 runs (0x0100E000), so
"the block is the wall" (2386's reading) was still one level too small.

**The page tables were re-audited from the real C, not the mirror.** The 2386 note
quoted the Python replica's leaves (`...4cc7`, AttrIndx 1). Compiling
`mali_csf_memory.c` with the production flags into a host harness and walking the
arena it builds gives `...4cc3` (AttrIndx 0) instead - so the replica is not
authoritative and should not be quoted again. It does not change the conclusion:
all sixteen leaves of the code section are identical except PA.

```
0x01000000  ...401a4cc3  PA 0x401a4000     0x0100e000  ...401b2cc3  PA 0x401b2000
0x01001000  ...401a5cc3  PA 0x401a5000     0x0100f000  ...401b3cc3  PA 0x401b3000
   ... same AF/AP/SH/AttrIndx, same group 6, one L3 table, no duplicate leaves
```

Page 0 is the section's base page; page 14 is 56 KB further on. Nothing in the
plan separates them, and the CPU-side probe still reads the container's word at
0x401a4000, so the content is where the tables say it is.

**This run also exposed an operational defect that cost the restore.** `pyusb` was
missing from the python on PATH, so `raw_restore_if_present()` fell back to the
`fastboot` CLI, and that CLI is exactly the transport this LK breaks with
`could not clear input pipe; e0005000` - the reason `tools/fbraw.py` exists. The
stock prefix was written, then the run was interrupted with the device in
fastboot and `boot_a` half-restored. Recovery: installed `pyusb 1.3.1`
(libusb 1.0.30 already present), used the raw channel to `reboot-recovery`, then
ran the runner's `restore-only` phase. It captured `after` **before** writing the
full baseline, so the marks survived, and finished with the baseline verified.
Do not let the CLI fallback stand in for the raw transport again; if `usb` is
missing, that is the first thing to fix.

**NEXT: 2388 - two things, one of them passive.** Active variable stays single:
the reset word -> `0x01001201`, page 1, block 1, a block nothing has patched. Page
1 is where the vendor reset handler at 0x010018ec lives and the port has never
proven the MCU executes it - if page 1 fails too, then the only execution ever
observed is page 14 and every "firmware started" reading in this port is shim-side
only. Passive addition in the same build: record the **live** leaf descriptors for
0x01000000, 0x01001000, 0x0100E000 and 0x0100F000 from the arena the kernel hands
the MCU (it is CPU memory; reading it changes no mapping). That settles whether the
table we compute is the table the MCU walks - the one instrument this port has
never had - and would show a stale page-0 leaf directly if there is one.

## >>> PREVIOUS 2026-11-06:2386 RAN - THE BLOCK IS THE WALL, NOT THE CORE'S STATE <<<

**RESULT: `input_va = 0x04000200` - the marker is absent.** The reset word pointed
at `0x01000201`; the block never ran. `mmu_raw = 0`, `as_fault = 0`,
`mcu_status = 1`, `relocation_observed = true`, `error = -53`. Nothing faulted,
nothing ran - exactly the signature of every earlier attempt on this block, now
with the reset path as the entry.

```
image  e0e8933c...797b  26,714,112 B   kernel 46743d03 (SWEET_BUILD_ID 0x2386)
part.  74285d78...7c58  written and read back
boot_a restored to 2931647a...86b1 (restored_sha256 verified)
outcome cold-boot-fetch-stalls   fastboot 120.97 s
```

2385's NEXT was answered, and the answer retires 2385's own reading. The
discriminator is **not** reset-versus-running core state: `0x01000200` fails as a
reset target too, and `0x0100E000` works as one. Every entry path into that block
- reset fetch (2386), `bl` from a running program (2379/2382/2383), data read
(2373/2375) - ends the same way.

Offline check done first, as the report's own verdict demanded:

```
leaf for 0x01000000  0x30000000401a4cc7   PA 0x401a4000
leaf for 0x0100E000  0x30000000401b2cc7   PA 0x401b2000
```

Identical in every field except PA: same attributes (AttrIndx 1, AF, read-only,
XN=0), same memory group 6, same tables. The container really holds the program at
0x01000200 (`72b60124240604f5007401239b069c6000bffee7`, verified in `csf.bin`),
and the CPU reads the section at 0x401a4000 (word0 matches the container). So the
page tables, the plan and the content are all as intended, and the fetch still
never completes.

So the question changed again: it is about **which block** can be reached, not
about who reaches it. Two blocks are known bad (0x01000200 by every path,
0x01001a00 by the firmware's own literal load at 0x010019dc) and two are known
good (0x01001800 executed, 0x0100E000 fetched at reset). Page 0 and page 14 have
identical leaves, so a page-granular story needs a mechanism the tables do not
show.

**NEXT: 2387 - bisect the block.** Same 20-byte program, reset word -> 0x01000601
(page 0, block 3, never patched by any build). Marker present means block 1 of
page 0 is the only broken thing and the wall is per-block; absent means page 0 as
a whole cannot be reached, which would also explain why the vendor's own entry
veneer at 0x01000000 (a `ldr pc` veneer into 0x010002ec) is dead code in this port.
Do not build another mapping experiment before this bisect answers.

## >>> PREVIOUS 2026-11-06:2385 RAN - A COLD FETCH DOES COMPLETE; THE WALL IS THE RUNNING CORE <<<

**RESULT: `input_va = 0x0100E000` - the marker is present.** The core fetched the
block at 0x0100E000, which nothing had ever touched, and executed it. Counter 8
(the program never writes 16), `mmu_raw = 0`, `as_fault = 0`, `mcu_status = 1`,
`relocation_observed = true`, `error = -53` (the shutdown probe timing out, as
every probe build does).

```
image  c7e3e01d...d9eb  26,714,112 B   kernel 44180108 (byte-identical to 2384)
part.  d1adf486...d952  written and read back
boot_a restored to 2931647a...86b1 (restored_sha256 verified)
outcome cold-boot-fetch-completes
```

**IMPORTANT - the mark on this capture is wrong.** The kernel was built without
bumping `SWEET_BUILD_ID`, so its records are tagged `0x2384`, not `0x2385`. The
report ABI is identical, the image sha identifies the run, and the capture decodes
with `--build 0x2385 --mark 0x2384`. Bump that constant before the next kernel
build, or the same mismatch returns.

What it settles:

- **Cold is not the wall.** A block that no access had ever reached was fetched
  and executed on the first cycle after reset. Everything about "only resident
  blocks work" was an artefact of *who* did the fetching.
- **The wall is the fetch path a running core uses.** 2383's `bl 0x01000200` hangs
  with no fault; 2385's reset word to a colder block does not. Same core, same
  tables, same section, different entry.
- **It also re-reads 2370/2371/2373.** Those read the second block of the code
  section as *data* from a running program (`ldr` at 0x010019dc). The one access
  pattern that never hangs is the one nobody had tried: start there.

Still true and still load-bearing: 2384's `AS_FAULT` result, that a refused access
hangs the MCU without an exception, so the fault entry cannot be the instrument.

**NEXT: 2386 - point the reset word at 0x01000200.** That is the block every
branch and every data read has failed to reach. Same marker/park program, same
mapping, only the vector target changes. Marker present means the block is fine
and the discriminator is reset-vs-running; marker absent means the block or its
page is the problem, and the next step is offline - compare page 0's descriptor,
PA and container bytes against page 14's. Do not build another fetch experiment
before this one answers.

## >>> PREVIOUS 2026-11-06:2384 RAN - THE REFUSAL REACHES THE MMU, NOT THE MCU <<<

**RESULT: counter 8 with the marker set, `error = -54`, `mmu_raw = 1`,
`AS_FAULT = 0x7cd002c2` at `0x03000000` - the exact fault status 2375 recorded
for its unmapped heap read.** The intended positive control (20) did not fire;
what fired is the other instrument, and it is the better one.

```
image be2c5cdb...393d  kernel 0x2384  81.32 s to fastboot
boot_a restored to 2931647a...86b1 (restored_sha256 verified)
outcome refusal-not-signalled  control_fault_va 0x3000000
```

Three sentences, each measured:

- **The read was issued and refused at the AS.** `AS_FAULT_LO` holds exactly
  `0x03000000`, the address the entry program loaded, and `mmu_raw` bit 0 is set.
  Nothing else in this boot touches that address.
- **The refusal never reached the core.** The entry program wrote its marker and
  then stopped: counter 8 (the template seed), no 30, and the 0x010019b0 handler
  never wrote 20. So an AS fault is a hang at the MCU, not an exception - and a
  build whose entry program also runs before SP is loaded has nowhere to stack an
  exception frame anyway.
- **2383 changes instrument, not conclusion.** 2383 read `as_fault = 0` and
  `mmu_raw = 0`; this run proves a refusal sets both. So the cold fetch was not
  refused, and "the fetch stalls without a fault" survives on the MMU words
  instead of on the stub.

This also corrects 2375: `-54` there is the shim reading `mmu_raw`/`AS_FAULT`, not
proof that the core took a fault. The MCU hung in that trial too.

**NEXT: 2385 - can the MCU fetch a cold block at all?** Every fetch measured so far
has been from a block that was already resident: the reset target 0x010018ec sits
in 0x01001800, and 0x01000200 hangs. Point the reset vector itself at a distant
cold block (patch the vector word and place `marker / park` at the new target,
e.g. 0x01010000) and nothing else. Marker present means a cold fetch works at
boot and the wall is the branch/return path inside a running program; absent means
the boot fetch is served by something that never runs again.

## >>> PREVIOUS 2026-11-06:2384 BUILT - A POSITIVE CONTROL FOR THE FAULT ENTRY <<<

2383 concluded "no exception was taken" from a stub that had never been seen to
fire. 2384 makes it fire on purpose: 2383 unchanged, except the 28-byte entry
program writes the marker and then reads the protected section at 0x03000000,
which the plan never maps.

```
kernel  44180108...f3cb  16,724,248 B, 19 bytes from 2383
image   be2c5cdb...393d  26,714,112 B, rebuilt to the same sha
part.   786879f2...7839  predicted boot_a contents
runner  research/matisse/20261031-gpu/shim2384-faultcontrol-trials-run-once.py
```

Built from 2383's spec with only the entry window replaced, so the containers
differ at 0x2790..0x27a5 and nowhere else (test-enforced). Reading:

| counter | meaning |
|---|---|
| 20 | the stub fired: the fault entry works and 2383's 9 is a real measurement |
| 30 | the unmapped read completed without faulting: 2383's 9 must be re-read |
| 8 (template seed) with the marker set | the read neither faulted nor completed: a stall and a silent refusal are indistinguishable, and 2383's result loses its value |

## >>> PREVIOUS 2026-11-06:2383 RAN - NO FAULT WAS TAKEN; THE FETCH JUST STALLS <<<

**RESULT: counter 9, `fault_taken = false`.** The call into 0x01000200 stops the
MCU without raising any exception. In band: `input_va = 0x01000200` (the marker,
so the probe reached the `bl`), `output_va = 0x04002000` and
`group_stride = 0x000000a0` (the template's seeds, never overwritten by the
stub), `relocation_observed = true`, stage 4 / -53 / `mcu_status 1` / `mmu_raw 0`
/ `as_fault 0`.

```
image 27b14944...1f7c  kernel 0x2383  153 marks  fastboot 90.82 s
boot_a restored to 2931647a...86b1
```

Why the negative holds without a positive control yet:

- every fault vector is 0x010019b1, re-checked by the builder each build, so a
  HardFault escalation lands on the same stub;
- the stub sits at 0x010019b0, inside 0x01001800..0x010019ff - the block this
  run already executed to write the marker, so it was warm when the call was
  made;
- the marker is present, so the probe did get to the call.

So this is not a translation refusal: a walker that rejected the fetch would
raise IACCVIOL/IBUSERR/PRECISERR and the stub would have recorded PC and CFSR.
Nothing is signalled at all - the instruction simply never completes.

Combined with 2373/2375/2378/2380/2382 the block-level picture is: cold *data*
pages in other sections read fine; the second 512-byte block of the code section
hangs for both a data read and a fetch; moving that block 1.2 MB in PA changes
nothing; descriptor bits, AttrIndx, share bits and PA are all ruled out. A stall
with no exception, tied to the block rather than to its mapping, points at the
MCU-side access path (fill/ready handshake), not at the page tables.

**NEXT: 2384 - positive control for the fault entry.** The stub has never been
seen to fire, so "the handler did not run" still rests on an argument rather than
a measurement. Put a deliberate fault in the 32-byte entry window (marker, then
`ldr` from the unmapped 0x03000000, then 30, then park) and keep the 2383 fault
stub. 20 + CFSR means the instrument works and 2383's 9 is final; 30 means the
unmapped read did not fault; nothing means the entry window never ran.

## >>> PREVIOUS 2026-11-06:2382 RAN - MOVING THE CODE SECTION'S PA CHANGES NOTHING <<<

**RESULT: `fetch-call-incomplete`, counter 9 - the same number 2379 read.** The
image moved the code section 1,196,032 bytes (PA `0x40080000` -> `0x401a4000`)
and the report proves the move happened in band: `firmware_probe_pa =
0x401a4000`, `relocation_observed = true`, `transtab_lo = 0x40077000` unchanged.
Everything else is 2379's: same container (`367eb386`), same leaf encoding, same
descriptor, same start word. The fresh-block call still does not return.

```
kernel_build                    0x2382
groups / fetch_prime_counter    9            (2379: 9)
stage / error / cleanup_error   4 / -53 / -53
mcu_status, mmu_raw, as_fault   1, 0, 0
version, features, ready        0, 0, 0
memattr                         0x4c4c884c / 0x4c4c4c4c
```

**Conclusion, as narrow as the build:** the hang does not follow the physical
pages this port can move it to. 2378 removed the descriptor bits, 2380 removed
the AttrIndx numbering and the shared SH bits, 2382 removed the physical range -
and 2376, 2378, 2380 and 2382 are now the same report field for field. The
memory-attribute and placement line is closed.

**What is still open:** a counter of 9 covers two mechanisms. Either the fetch
never completes, or it faults and the vendor handler at `0x010019b1` parks -
`AS_FAULT` reads 0 because an MCU-side fault does not set it. Four builds with
three different mappings cannot separate those.

Trial facts: 83.56 s to fastboot, 153 marks, `boot_a` restored to
`2931647a...86b1` (`restored_sha256` verified), partition `47dc4e1d...8b57`
written and read back. First attempt of this image produced real evidence - the
probe fix (CLI instead of pyusb) held.

**NEXT: 2383 - fault vector on the fetch-prime path.** Install a stub at the
vendor fault entry (0x010019b0, inside the block that is mapped and has already
executed) that records the stacked PC from the exception frame and writes a
distinct counter value, then rerun 2382's relocation probe unchanged. Reading:
a new counter value with a PC means the fault mechanism and its instruction; an
unchanged 9 means no fault was taken and the fetch itself is the wall. Do not
move memory again before that answer exists.

## >>> PREVIOUS 2026-11-06:2380 RAN - THE VENDOR MEMATTR PAIRING IS NOT THE WALL <<<

**RESULT: `unchanged`.** The corrected image booted, the marks decoded with
build `0x2380`, and the GPU read back `memattr_lo = 0x888d8f88`,
`memattr_hi = 0x00084c8d` - the vendor table really was programmed. The CSF
report is the 2376/2378 signature field for field:

```
stage / error / cleanup_error   4 / -53 / -53
mcu_status, mmu_raw, as_fault   1, 0, 0
version, features               0, 0
firmware_ready                  0
groups, group_stride            8, 0xa0   (template seeds; no probe ran)
transcfg_lo / reset_raw         0x42000006 / 0x200
```

So the two facts that had never been varied - AttrIndx numbering and the SH bits
on the shared leaf - are **not** the blocker. With 2378 that closes the attribute
line from both ends. Image `0f21ee93...e77bc`, 26,714,112 B, partition
`78a91de6...a9511`, `boot_a` restored to `2931647a...86b1`.

**TWO ATTEMPTS BEFORE THIS ONE PRODUCED NO EVIDENCE, and the cause was mine.**
Attempt 1 aborted at t=30 s because the fastboot probe imported `tools/fbraw.py`
(pyusb), which is not installed; the `finally: restore()` then flashed the stock
prefix over a boot that had not finished. Attempt 2 ran the fixed probe and
behaved the same: fastboot at 87.67 s with `before_tail_sha256 ==
after_tail_sha256`, i.e. nothing reached userdata. The defect: both images
embedded `xnu/out/local/kernel.development.sweet`, a **stale Oct 25 file**
(17,222,952 B), not the build output
`xnu/out/local/build/xnu.obj/DEVELOPMENT_ARM64_SWEET/kernel.development.sweet`
(16,724,248 B). The embedded kernel differed from 2379's in 13,865,824 bytes, so
neither attempt was a single-variable trial. Both are archived with NOTE.txt under
`shim2380-vendormemattr-trials/`. **Always take the DEVELOPMENT_ARM64_SWEET
artifact and check the size against the previous build** - a 61,440-byte image
size delta was the tell.

**Driver state:** `SWEET_CSF_VENDOR_MEMATTR` defaults to 0, so every earlier
build reproduces byte for byte; `--vendor-memattr` selects the vendor mapping and
is what 2380 measured. The 2330 diagnostic `0x4c4c884c` is retired on that path;
the vendor pair is `0x888d8f88` / `0x00084c8d`, proven from the blob at 0x4708C
and 0x47998 (evidence in `research/matisse/20261031-gpu/memattr-disasm-2380.txt`).

**Also landed this round, default off:** `sweet_csf_boot` stages 9/10 plus
`csf_global_init()` - global input page, `GLB_REQ` toggled against the
firmware's ACK with mask 0x40e, CSF doorbell 0 at GPU+0x80000, ACK poll - i.e.
the step `global_init_on_boot()` performs after boot. Evidence goes through a new
96-byte `sweet-csf-global` ADT property; the 696-byte report is untouched;
`SWEET_CSF_GLOBAL_INIT` defaults to 0. OPEN: `sweet_ufs.c` does not forward that
block into SWEETMRK yet (`kernel_marks_wired=false` in the manifest), so 2381
would be console-only. Do not call 2381 runnable until that lands.

**NEXT: 2382 - does the hang follow the physical or the virtual address?** Move
the code section's pages inside the arena (same VA, same leaf bits, same
descriptors, different PA). 2373/2379 measured 512-byte granularity inside the
code section while the stack and read-only sections read cold without trouble;
nothing has separated "this PA range" from "this VA range" yet. kbase and Panthor
both map firmware with ordinary GPU pages, so a PA-dependent hang would point at
the GMPU/SLC routing rather than at translation. (2382 as built reuses the 2379
probe instead of a clean boot, so the counter survives the move - see ACTIVE.)

## >>> PREVIOUS 2026-11-06:2379 - THE FRESH-BLOCK CALL DID NOT RETURN; FETCH ITSELF HANGS <<<

RAN 2026-11-06 14:18. Counter `groups = 9`, outcome `fetch-call-incomplete`:
the probe branched into 0x01000200 (patched to `nop; bx lr`) and never came
back, so the stop is in the fetch/return path, *before* the explicit data read
at 0x01000210. Combined with 2376 this is the strongest statement so far: it is
not only a data read of an unfetched RX block that fails, a plain instruction
fetch of one fails too. Stage 4, error -53, `mcu_status=1`, `mmu_raw=0`,
`as_fault=0`, `version=0`, `firmware_ready=0`, memattr `0x4c4c884c` /
`0x4c4c4c4c`, transcfg `0x42000006`, cleanup -53, `reset_raw=0x200`.
Image `9dc4467d...df6c`, 26,714,112 B, partition `aead007c...f415` written and
read back, journal `complete-restored-Recovery`, no fresh Recovery - it fell to
fastboot after 84.56 s and the raw prefix restore brought it back,
`restored_sha256 = 2931647a...86b1`.

NOT PROVEN BY THIS: that fetch *primes* a block for data access. A non-returning
call cannot distinguish "fetch hung" from "fetch worked and the return was
lost", and the 2366 datum still contradicts the 512-byte-block model. Treat the
exact stopped PC as unknown; 0x010019dc is still a disassembly inference.

THE 2379 DESIGN, for the record:

2378's negative result is unchanged. 2379 now has a literal-free, stack-free
probe from `tools/matisse-csf-fetch-prime.S`: patch 38 bytes at reset handler
0x010018ec and four bytes at 0x01000200 (`nop; bx lr`), with the config/vector
table and original fault handler untouched. BL at 0x01001902 returns to
0x01001906; only then does LDR at 0x0100190a read 0x01000210 into a discarded
register. Marker shared+8 is 0x01000200. Counter shared+16 starts at 8:
9 before BL, 10 after return, 11 after the data read. Keep the 2378 mapping
(`--ro-as-rw`) and MCU_CONTROL=2. The builder enforces those inputs for 2379.

OBSERVATIONS SO FAR: linked Cortex-M7 assembly matches both installed windows;
exactly 40 container bytes differ within those two windows (42 bytes covered).
Original firmware SHA de22d2fc...4f7229a; patched container SHA
367eb386724f2a29f1b32ca39f4042954a804b667ab03228a38dd8941bd16d89.
113 related tests ran successfully, 3 skipped. Full contextual replay of 177
patches, including inherited untracked0093 (hash54f0aaa5...de65365b), exactly
matches local kernel source after identity patch0178 -> build2379. Baseline
2378 kernel/source saved in ignored `shim2379-fetchprime-prep/`.

INFERENCE LIMITS: 9 localises a missing return to the fetch/return path; it
does not expose the exact stopped PC. 10 says this fetch did not make the word
at +0x10 readable. 11 supports fetch priming at this target, not an exact
512-byte window or vendor firmware readiness. Decoder treats MMU faults,
missing markers and unexpected states separately. The proposed vendor stop
at 0x010019dc remains an inference from disassembly and prior probes, not a
direct PC measurement of 2376/2378.

NEXT: finish local incremental kernel/image build, independent image audit,
full host tests, commit and record final hashes. No new CI dispatch or push;
`gh` inspected the existing CI history (origin's most recent listed runs
remain action_required); established local build retains inherited0093.
No device write or boot has been performed in this session. Last verified
device state remains Recovery/boot_a2931647a...86b1 from 2378; not remeasured yet.
Preserve inherited untracked files. A destructive trial needs a separate
confirmation naming the completed 2379 image under AGENTS.md.

## >>> PREVIOUS 2026-11-06:2378 - READ-ONLY WAS NOT IT; NO LEAF FIELD DISTINGUISHES THE CODE PAGE ANY MORE <<<

READ THIS FIRST. Trials 2357-2370 all ran. Until this entry their results existed
only as comments above the per-build `TRACE_PROBE` table in
`tools/matisse-shim-gpu-image.py`; `NOTES.md` still stopped at 2356/2357. Those
comments are the source of everything below; the instrument specs are the truth,
the prose here is the summary.

**2357 - the bounce test failed.** Every 2356 patch kept, only the stub changed:
after recording the site it overwrote the stacked return address with 0x0100192a
(the rung-2 call site) and popped. The rung-2 helper still never ran. So the stub
itself was the prime suspect, not the firmware.

**2358 - the stack was the wall.** The 2351-2357 stub pushed/saved into PSP
(0x0203f000) and popped {r0,r1,r2,pc}. If PSP is not backed by writable RAM the
push writes into a hole and the pop loads garbage into pc, which kills the core at
the first entry regardless of what the firmware does. 2358 removed the stack
entirely (return address never leaves lr, only r3/r12 touched, S-less 32-bit
forms). Result: **rung 2 (0x010019e2) recorded, count reached 2**. Every
"MCU did not execute" verdict from 2344-2357 was an artefact of the stack.

**2359-2362 - the cache helper is not the wall either.** 2359 nop'd both stores in
the cache-enable helper (ICIALLU at 0x010019f0, CCR.IC at 0x010019fa); the core
still died at rung 2. 2360 split the window with two more rungs (isb at
0x010019e6, orr at 0x010019f6) and reported site 0x010019e6 with three entries,
i.e. the kill sits between them - the CCR read. That is impossible on a working
M-profile core (0xe000ed14 is internal), so 2361 put the vendor prologue literals
back (0x40022000, 0x40022004, SHCSR 0xe000ed24): the ladder **lost** a rung
(site 0x010019e2, two entries) with every hardware word identical, so those three
real stores do not unlock the peripheral space, they make the stall come sooner.
2362 returned to 2360's redirects and nop'd the CCR read itself; still stopped at
the isb rung.

**2363 - the core free-runs.** Probing the firmware had become useless, so the
reset vector itself was replaced by `ldr/adds/str/b .-8` on shared+0x10 and
nothing else ran. The counter reached **406,670,326 inside the one-second poll
window**. Clock, fetch path, shared page and the core all work; every earlier
stall is real control flow.

**2364-2366 - the stop follows the next unfetched literal load.** 2364 turned
every 4-byte window of the helper into a rung: the rung at 0x010019ea was entered
and returned (counter 12) and the core died before 0x010019ee, so adding four
bytes of rungs moved the stop forward four bytes - it is not pinned to an address.
2365 put a counter loop at 0x010019ee with its literal at 0x010019fc:
`group_stride` went 0xa0 -> 0xa4 and stopped after one turn. 2366 put the 2363
loop byte-for-byte at 0x010019ee, entered by a single branch with no ladder in
between: it turned **exactly once**, where the same bytes at 0x010018ec turned 406
million times.

**2367-2369 - it is the read, and it is distance-dependent.** 2367 ran a straight
line of 128 `adds r2,#1 / str r2,[r3]` pairs from the reset vector with the
literal 520 bytes away: **not one store landed**. 2368 repeated 2363 byte for byte
and moved only the literal to 0x01001af8 (12 -> 520 bytes): count 406 million ->
**0**. 2369 removed the last confound - the counter pointer built from
movs/lsls/adds and the far word read once into r0 and discarded - and the count
stayed at 8. **The far read itself stops the core; it is not a wrong pointer.**

**2370 - the edge is at 0x01001a00, inside one 4 KiB page.** A sweep probing
0x01001900, 0x01001a00, ... one 0x100 step per turn found that the probe at
0x01001900 returned (it sits inside the loop's own already-fetched code) and the
very next probe hung the core. Same 4 KiB page, same leaf descriptor, so this
cannot be a mapping difference between the two addresses.

**Where this leaves the port.** The blocker is no longer "the firmware does not
run". It is: **a data read by the MCU of code-section bytes it has not yet
fetched hangs the core.** That is a property of the stage-1 leaves that
`xnu/gpu/mali_csf_memory.c` builds for the code section, not of the CSF firmware,
and it explains every ladder stall from 2351 on.

**2371 RAN, 2026-11-06 00:07, and it refuted the "only fetched bytes" reading.**
Image SHA256 `f4d107102129a8a6e6ca6f3adb2cb9f0593b9215ee02e36f066cf1d5c6ba76af`,
26,714,112 B, journal `complete-restored-Recovery`, `restored_sha256` back to
`2931647a...86b1`. Same sweep as 2370 with the step cut from 0x100 to 0x10:

- `groups = 24`, i.e. `groups - 8 = 16` probes returned. The probe pointer walks
  0x01001900 + 0x10*n, so the reads that completed are 0x01001900 .. 0x010019f0
  and the read at **0x01001a00** stopped the core. Every other report field is
  the usual failure (`csf stage 4`, `error -53`, `version 0`, `mcu_status 1`).

So the readable window is 0x01001900..0x010019ff: **256 bytes, ending exactly on
a 0x100 boundary, inside a single 4 KiB page whose leaf covers all of it.** One
probe would have meant "only fetched bytes"; sixteen means it is not a per-byte
fetch property, and it is not the 4 KiB page either. The datum that fits is a
512-byte aligned fetch window: the loop starts at 0x010018ec, so a window at
0x01001800..0x010019ff makes 2363's literal at 0x010018f8 readable, 2365's at
0x010019fc readable for exactly one turn, and 2368/2369's at 0x01001af8 dead -
which is what those trials measured. The one datum this does not explain is 2366
(loop at 0x010019ee turning once with its literal at 0x010019f8, inside that
window); do not treat the window size as settled until a probe starts the loop at
a different base address.

**2372 WAS A NULL: the start word killed it before the map ran.** The whole-section
map booted with the vendor `ENABLE|AUTO` (3) and `MCU_STATUS` stayed 0 for the
entire budget - the MCU was never enabled, so no probe executed and the run says
nothing about reads. Image `03537c40...`, journal `complete-restored-Recovery`.

**2373 RAN THE SAME MAP WITH AUTO ALONE (2): the region limit is dead.** Image
SHA256 `7ef7c11f26d10fb28dd89d95ed694968cc4d32d925e7196070f6f9b85091de8e`,
26,714,112 B, journal `complete-restored-Recovery`, `restored_sha256` back to
`2931647a...86b1`. Nothing changed except the start value, the kernel build id
and the builder's record of it. Result:

- `input_va = 0x01000000` - the loop stores that marker into shared+0x08 *before*
  probe 0, so the map demonstrably started.
- `groups = 10`, and `groups` is `rd(shared+0x10)`, seeded 8 by the firmware
  template, incremented once per probe. So **two** probes completed:
  0x01000000 and 0x01000100 returned, and **0x01000200 stopped the core**.

This refutes the "readable prefix ending at 0x1a00" reading outright: it predicted
every block below 0x1a00 would be readable, and 0x01000200 is 0x1800 below that.
It also kills any "only near the executing code" reading, because 0x01000000 is
0x18ec away from the loop.

**The shape that fits both runs is a 512-byte block that the core has touched.**
Two blocks are readable: `0x01000000..0x010001ff` (the reset vector read at boot)
and `0x01001800..0x010019ff` (the block the loop executes from). Every one of
2371's sixteen returning probes (0x01001900..0x010019f0) is inside the second
block, and 0x01001a00 is the first address of the next one - so 2371's "256-byte
window" was really the tail of a 512-byte window whose head is the executing code.
2366 remains the single datum this does not explain.

**Next: 2374, the one probe that separates "fetch primes the block" from "only
these two blocks are special".** Branch into a fresh block (0x01000200), execute a
few instructions there so the core fetches it, then data-read that same block.
`groups = 9` means the fetch landed but a data read of a fetched block still hung;
`groups = 10` means fetch primes the block for data reads, which is the rule the
driver has to live with; `groups = 8` means the fetch of a fresh block hangs too
and the wall is the translation, not the data path. The marker is stored first, so
all three outcomes are distinguishable.

**2374 KILLED THE SHARE-BIT HYPOTHESIS.** The vendor kernel says a CSF section gets
share bits only when it declares `CSF_FIRMWARE_ENTRY_SHARED`
(`convert_mem_flags()` sets `KBASE_REG_SHARE_BOTH`, `get_mmu_flags()` emits
`ENTRY_SHARE_BITS` only for that flag), and the pinned container's code section at
0x01000000 is `R-X cached shared=0`. This port had been mapping every cached
section `SH=11`. Fixed, rebuilt, same map, one variable: image
`e4fab071...`, 26,714,112 B, `boot_a` back to `2931647a...86b1`, and the result is
**`groups = 10` again - exactly 2373**. Two probes, same two, same hang at
0x01000200. So shareability is not the wall.

**What that leaves.** (2377 later retracted the 2358 half of this - the page does take
writes; see the ACTIVE section.) Put 2374 next to 2358: 2358 believed the
PSP at 0x0203f000 could not be written, and 2374 shows a data read at 0x01000200
cannot be completed, while instruction fetch to the same DRAM at 0x010018ec works
millions of times per second. Every data access that has to leave the GPU hangs;
every instruction fetch does not. The addresses that read are exactly the ones
whose lines the core has already pulled in (the reset vector at 0x01000000, the
code it executes at 0x01001800). That is not a property of the code section - it
would be a property of the **data path**, which the 2371-2374 probes have been
describing all along without naming.

**Next: 2375 must test the data path, not the code section.** Same loop, but the
probe list is one address per section - 0x01001900 (known good, control),
0x02000000 (stack), 0x02800000 (read-only data), 0x03000000 (heap), 0x04000000
(shared) - each incrementing the counter, so the first hang localises itself. If
0x02000000 hangs, the wall has nothing to do with code mapping and every earlier
attribute experiment was measuring the wrong thing; the next suspect becomes the
GPU data path itself (the GMPU the MT6983 device tree describes with
`gmpu_table_size = 0x400000`, or the memory attributes the data path uses).
If 0x02000000 reads, the wall really is specific to the code region and the
remaining attribute difference is the memattr index.

**2375: the wall is the code section after all - and it is not permission.** Five
probes, one per section, each with its own counter increment. Image `54d732cd...`,
`boot_a` back to `2931647a...86b1`. Result `groups = 11`, i.e. three returned:

| probe | section | result |
|---|---|---|
| 0x01001900 | code | returned |
| 0x02000000 | stack | **returned, never touched before** |
| 0x02800000 | read-only data | **returned, never touched before** |
| 0x03000000 | heap | stopped the core |
| 0x04000000 | shared | never reached |

The stack and the read-only data had never been read or fetched by this core, and
both returned. So data reads to ordinary sections work; the earlier idea that the
whole data path is dead was wrong.

**The heap probe was not a hang, and that matters.** 2375 ended with
`error = -54` (FAULT), `mmu_raw = 1`, `as_fault = 0x7cd002c2`, while 2373 and 2374
ended with `error = -53` (TIMEOUT) and `mmu_raw = 0`. The 0x03000000 sections carry
`CSF_FIRMWARE_ENTRY_PROTECTED`, and `sweet_csf_memory.c` skips protected sections -
so that address is simply unmapped, and an unmapped read **faults immediately**.
A mapped-but-unreadable read **hangs without faulting**. Two mechanisms, previously
conflated; now separable in the report.

**What that leaves is narrower than before and stranger.** 0x01000200 is mapped, is
permitted (no fault), and never completes; 0x02000000 is mapped, permitted, never
touched, and completes. The only differences between those two leaves are the ones
the section flags produce: the code page is read-only (AP[2]=1) and executable
(XN=0), the stack page is read-write and XN. Permission cannot be the cause, or the
read would fault like the heap did. So an RX page can be read as data only while
its line is already in the GPU - which is what 2371 measured and 2373/2374
reproduced.

**Before another attribute guess: does the real firmware boot?** Every trial from
2363 to 2375 replaced the reset vector with our own loop, so the probe reads code
as data - something the vendor firmware never does. With the state machine, the
corrected share bits and MCU_CONTROL=2 now in place, the question "does the driver's
power-on sequence work" has not actually been asked since 2358 fixed the stack.
2376 should boot the firmware unpatched and read `firmware_ready`, `version` and
the interface handshake, with no trace probe at all.

**2376 BOOTED THE UNPATCHED FIRMWARE: IT DOES NOT REACH READY.** No trace probe, no
entry patch - the embedded container is byte identical to the vendor file and
0x010018ec still holds `72b62648`. Image `ab6c5fc0...`, `boot_a` back to
`2931647a...86b1`. Result:

- `mcu_status = 1` - the MCU is enabled, so the halt/start state machine and
  `MCU_CONTROL=2` do work;
- `mmu_raw = 0`, `as_fault = 0` - no fault at all;
- `version = 0`, `features = 0`, `firmware_ready = 0`, `error = -53` timeout.

`version` and `features` are `rd(shared)` and `rd(shared+4)` - the words the
**firmware** writes into the output page once it is up. Zero means it never got
that far. So the firmware starts, runs, does not fault, and never completes its
own initialisation.

**What this invalidates.** Everything 2363-2375 concluded was about a probe loop we
had installed ourselves: the "unfetched RX line" property is real but belongs to an
access pattern the firmware never performs. It was never the reason the port is
stuck, and no further attribute work on it will boot anything. The port's actual
state is now measured rather than assumed for the first time since 2358: power,
clocks, MCU start and MMU configuration all work, and the firmware dies silently
somewhere after its reset vector.

**The vector table explains 2376.** The config section (VA 0) holds it:

```
SP        0x02040000      Reset     0x010018ed
NMI/HardFault/MemManage/BusFault/UsageFault   0x010019b1
```

So 0x010018ec **is** the reset handler - every probe from 2363 on patched the right
address - and 0x010019b0 is the shared fault handler, which is why writing a stub
there was harmless.

The vector table's SP is 0x02040000, but the handler overrides it: at 0x01001906 it
loads the literal at 0x01001994 (= **0x0203f000**), does `msr psp, r0`, then sets
CONTROL=2 so SPSEL switches to PSP. So the stack really does start at 0x0203f000 -
the address 2358 named - and its first push writes 0x0203effc. This paragraph
originally blamed that page; 2377 retracted it, the page takes writes. The actual
stop is the literal load named below.

**Next: 2377 tests writes, not reads.** 2375 proved reads work at 0x02000000; the
stack top is a different 4 KiB section. Write a word to 0x02000000 and to
0x0203f000, read both back into the marker, and the answer decides everything: if
the top page does not hold a write, the wall is that page - the firmware's stack -
and the fix is in how that section is mapped, not in the entry path at all.

**Superseded:** the trap-on-the-init-path idea below. Do not build it before the
write test; if the stack page cannot be written the firmware never gets far enough
for a trap to mean anything.

**Next (superseded): 2377 must find where it stops without replacing the reset vector.** The
firmware runs, so the useful instrument is a trap placed on an instruction the
firmware itself executes on its way to `main` - one patched word deep inside the
init path that writes a marker and parks, leaving the entry vector, the section
table and the page table alone. Walking that trap forward a few words at a time
turns "it does not reach ready" into a PC.

**2377: the stack page takes writes, so 2358's inference was wrong.** Two pages, one
pattern, DSB in between, read back and restored, with the counter stepped after each
stage so it names where execution stopped. Image `c63f4c12...`, `boot_a` back to
`2931647a...86b1`, `groups = 11`:

| probe | page | result |
|---|---|---|
| A | 0x02000000 | write landed and read back |
| B | 0x0203f000 | write landed and read back |

`groups = 11` is the "both pages held a write" value; 9 would have meant B's read
stalled and 10 its store. 2358 never tested a store - it ran a stub with a PSP stack,
saw the ladder die, and *inferred* the page was not writable. The page is writable.
The stack was not why 2376 failed.

**2376 explained without another boot: the firmware reads a literal in the block
2371 proved unreadable.** Disassemble the reset handler at 0x010018ec and its three
cache helpers at 0x010019dc, 0x010019ee and 0x010019f2 load literals from
**0x01001bc4..0x01001bcc**. Those three instruction addresses sit in block
0x01001800..0x010019ff; the literals sit in block **0x01001a00..0x01001bff** - the
exact block 2370, 2371 and 2373 measured as stopping the core. Everything before
0x010019dc uses literals at 0x01001988..0x010019ac, inside the executing block, which
is why the core gets that far.

So the firmware runs, reaches 0x010019dc, issues `ldr r0,[pc,#0x1e4]`, and hangs on a
data read of an RX page whose line is not resident - no fault, exactly as 2376
reported. It also re-reads 2359-2362: that ladder kept dying at rung 2 (0x010019e2)
inside this same cache helper, and the experiments there blamed the CCR read; the
stall was always this literal.

**Next: 2378 must make that read complete, and there is now exactly one leaf
difference to test.** 2375 proves reads of RW pages complete; 2373/2374 prove reads
of RX pages hang unless resident; 2377 proves writes to RW pages complete. Between
the code leaf and the stack leaf the only differences are `AP[2]=1` (read-only) and
`XN=0` (executable). 2378 boots the unpatched firmware with `AP[2]` cleared for
sections the firmware declares read-only, one variable, and reads `version`,
`features` and `firmware_ready`. If it reaches ready, the wall was the read-only
attribute; if it still stops, XN or the cache mode is next and the ladder is
unnecessary - 0x010019dc is already the known stop address.

**2378 CLEARED THE READ-ONLY BIT AND NOTHING CHANGED.** Image
`7a284abe...`, container byte identical to the vendor file, no probe, no entry
patch; only the page table differs. Offline the code leaf goes
`0x...9cc7 -> 0x...9c47`, so its low twelve bits become **identical to the stack
leaf's** (`0x...9c47`) - and the trial still reports `mcu_status = 1`,
`mmu_raw = 0`, `version = 0`, `features = 0`, `firmware_ready = 0`, `error = -53`.
Same signature as 2376, field for field.

That closes the attribute line rather than doubting it. After 2378 there is **no
field left in the leaf** that distinguishes the code page from the stack page: same
AttrIndx, same share bits, same AP, same XN, same AF/nG. Yet a cold data read of the
code page hangs and a cold data read of the stack page returns (2375) and takes
writes (2377). So the difference is not in the descriptor. Any explanation has to be
about the access itself.

**Corroboration that the firmware is wedged, not looping.** 2373 ended after its data
read at 0x01000200 hung, and cleaned up with `disable_status = 1`,
`reset_completed = 0`, `reset_raw = 0x200`. 2376 and 2378 end with exactly those.
The probe builds that reach their own `b .` park (2375, 2377) end with
`reset_completed = 1`. 2375 shows the halt request can fail on its own, so this is
corroboration rather than proof - but the failure signature is the same.

**Note on 2356.** That trial already nop'd `79 48 01 60` at 0x010019dc, i.e. both the
literal load and the CSSELR write, and the ladder still did not advance. It was not
evidence against this address: that ladder's own return path (pop after a PSP switch)
was under suspicion at the time, so the result was inconclusive rather than negative.
The difference now is that a real firmware boot with no ladder at all ends in the
wedged state, and the offline literal map names the same instruction.

**Next: 2379 asks whether fetch primes a block, because no attribute can.** The probe
branches into block 0x01000200 - never fetched in these boots - executes two
instructions there so the core must fetch it, returns, and only then data-reads
0x01000210 in that same block. The counter separates the three answers:

- 9  the branch into a fresh block hung: even the fetch path fails there, and the
     wall is more basic than any read/write distinction;
- 10 the fetch landed and the data read of the freshly fetched block still hung:
     residency is not the rule, and the model built from 2371-2375 is wrong;
- 11 the data read completed: fetch primes a block for data access, which is the
     rule the driver has to live with and explains why the firmware dies at
     0x010019dc reading a literal 0x1e4 bytes ahead of itself.

**Driver, this round:** `mali_csf_boot.c` drives the MCU through an explicit state
machine instead of the bare `wr(MCU_CONTROL, 2)`: halt (write 0, poll
`MCU_STATUS == 0`, new `SWEET_CSF_BOOT_HALT` stage), then start, then the wait
loop, whose fault test is now "any status bit other than ENABLED" instead of only
`== 3`. 2372 measured that `ENABLE|AUTO` (3) leaves `MCU_STATUS` at 0 on this SoC
while AUTO alone (2) reaches 1 through the same path, so **2 is the default**
everywhere - shim constant, driver config fallback, `--mcu-control` - and 3 stays
reachable for a single-variable trial. The written/read-back pair lands in the
report's `platform_reserved` word (`path_reserved` keeps its 2335 checkpoint
meaning), so the 696-byte CSF ABI is unchanged. 210 tests pass, 3 skipped.

**Vendor reference, new:** `https://github.com/MiCode/Xiaomi_Kernel_OpenSource`
branch `rubens-s-oss` carries the OEM kernel for this platform
(`arch/arm64/configs/mikrn_matisse_defconfig`, `mikrn_rubens_defconfig`) with the
full MTK GPU stack under `drivers/gpu/mediatek/`: `gpueb/` (the EB driver we have
been reconstructing), `gpu_mali/mali_valhall/{mali-r25p0,r30p0,r32p0,r32p1}` (the
kbase CSF DDK), `gpufreq/`, `ged/`, `gpu_bm/`, `hal/`, `mt-plat/`. Use it as the
authority for the EB power-on sequence and for the firmware mapping instead of
inferring both from measurements. The full OS2.0.2.0 flash package is on disk at
`/Users/xiaohuasheng/Documents/matisse_images_OS2.0.2.0.ULKCNXM_14.0/`
(`flash_all.sh`), so a bad trial is recoverable without the raw backup prefix.

Device discipline unchanged: `boot_a` must verify back to
`2931647a56039722ea2585990b8ef3b1a2daf4c9b990231879f753049eaf86b1` after every
trial; every trial needs a named image SHA.

## >>> HISTORICAL 2026-11-05:2356 HAD NO DEVICE ACCESS AND STILL STOPPED; 2357 TESTS THE LADDER ITSELF <<<

2356 RAN. Image d7acaa1a, one authorized trial, boot_a restored to2931647a.
progress site0x01001914, groups9 -> one entry, version=0xb, features=7,
output_va=0x70000. With BOTH remaining device accesses removed - the MPU call by
nops and the CSSELR store in the0x010019d8 helper by nops - the ladder still does
not reach rung 2.

That is the decisive negative. Every instruction between rung1 and rung2 is now
either a literal load or a shared-page read:
  0x1001918 ldr r0,=shared+0x14   (literal, patched)
  0x100191a ldr r4,[r0]           (shared read, value0xa0)
  0x100191c and r4,r4,#0x80
  0x1001920 mov r0,r4
  0x1001922 nop ;0x1001924 nop   (MPU call removed)
  0x1001926 bl0x10019d8           (helper is now mov r1,#0 ; nop ; nop ; bx lr)
  0x100192a bl0x10019e2           (its first instruction is rung2)
A shared-page read and a literal load cannot stall a core that has just executed
six stores into the same shared page. So the remaining suspect is the LADDER, not
the firmware: either execution never returns from the stub, or the second rung's
`bl` never fires.

2357 TESTS THE INSTRUMENT. Every2356 patch is kept; only the stub changes. After
recording the site and bumping the counter it overwrites the stacked return
address with0x0100192a - the call site of the helper whose first instruction is
rung2 - and then pops:
  push {r0,r1,r2,lr} / mov r0,lr / subs r0,#5
  ldr r3,=shared+0x08 / str r0,[r3]
  ldr r2,=shared+0x10 / ldr r3,[r2] / adds r3,#1 / str r3,[r2]
  ldr r2,=0x0100192a / str r2,[sp,#0xc]     ; overwrite the saved lr
  pop {r0,r1,r2,pc}
Every entry now bounces into the rung-2 helper and back, so the loop is infinite
by design and the shared words get hammered for the length of the boot.
  site0x010019e2 and/or groups far above9 -> the stub returns, the ladder is
      sound, and the stop at0x01001914 in2351-2356 was real firmware behaviour
  site0x01001914 with groups9            -> the stub never returns at all; the
      ladder cannot be trusted past rung1 and the measurement must change

This is a measurement-quality question, not a firmware question. Do not draw
further conclusions about the CSF reset path until it is answered.

Artifacts: kernel23922876 (patch0156, build id only), image
shim2357-bounce-ready/matisse-shim-gpu2357.img,26714112B,
SHA256 93e5648856e120b6e7e076c6bf20e9bff0399c4f84f8f30bc357e29b848e7d13,
predicted partition digest
a37f14543a5a13bf16673e752b0ae82d755af58c67193e2e2ac2e238b4515ff3,
embedded container 67a2b77b4793d710f23b942fb98f9edf8bfb00fb81851280f8a037dcb6499fbd.
90 container bytes change: stub36, nine calls36, four literals12, MPU nop4,
CSSELR nop4, minus bytes that already matched.
verify2357-bounce.py PASS (36-byte stub fully disassembled, all three literal
slots resolved and checked, str r2,[sp,#0xc] confirmed as the saved-lr slot,
both nop pairs and the untouched0xe000ed84 literal confirmed).210 tests pass,
3 skipped.

Runner: shim2357-bounce-trials-run-once.py, refuses to run without
--approved-image-sha256=93e5648856e120b6e7e076c6bf20e9bff0399c4f84f8f30bc357e29b848e7d13.

Device clean: root Recovery, boot_a2931647a, no journal.

## 2026-11-05 earlier:2355 SAYS THE MPU CALL IS NOT IT; 2356 REMOVES THE LAST DEVICE ACCESS

2355 RAN. Image 50ecca37, one authorized trial, boot_a restored to2931647a.
progress site0x01001914, groups9 -> one rung entry again, version=0xb,
features=7, output_va=0x70000. So `bl 0x01003126` - the entire MPU region
programming call - is NOT the wall. Two nops in its place changed nothing.

That leaves exactly one device access between rung1 and rung2:
  0x1001926 bl0x10019d8
  0x10019d8 mov.w r1,#0
  0x10019dc ldr r0,=[0x01001bc4] ->0xe000ed84
  0x10019de str r1,[r0]            <- the write
  0x10019e0 bx lr
0xe000ed84 is CSSELR on a Cortex-M7 (cache size selection); the next helper then
writes0xe000ef50 (I-cache invalidate all) and sets CCR.IC. Everything else in the
window is a literal load, one shared-page read of group_stride (0xa0), an AND and
a MOV.

2356 REMOVES THAT WRITE TOO: `79 48 01 60` at0x010019dc becomes two nops, on top
of2355's MPU-call nops. The literal at0x01001bc4 keeps0xe000ed84, so this is a
removal, not a redirect, and no literal pool entry changes. The gap now contains
NO device access of any kind.
  rung0x010019e2 or later -> the CSSELR write is the wall
  still0x01001914        -> the ladder cannot carry execution across the gap, and
                            the return path (pop {r0,r1,r2,pc} after a PSP switch)
                            has to be questioned instead of the firmware

Why this matters: if a plain CSSELR store stalls with no fault and no reset, the
MCU's cache/PPB complex is not responding the way production hardware does, and
the next question becomes what else must be powered or un-gated for that block -
not which instruction to patch next.

Artifacts: kernel131a0aea (patch0155, build id only), image
shim2356-nodev-ready/matisse-shim-gpu2356.img,26714112B,
SHA256 d7acaa1ab4d1812d65fab7a7c16412b1df8056945bc170a04725bb5066f6d6b2,
predicted partition digest
6d1a511146a71cdcbbf5c855ab515ef619dd5a32ce0cb5f199310a72c7dcd86c,
embedded container 8a0d22787928bb00aa0a96b77426473cdadf9460eabea5fd98ca5867773e4475.
83 container bytes change: stub28, nine calls36, four literals12, MPU nop4, CSSELR nop4.
verify2356-nodev.py PASS (both nop pairs disassembled, the CSSELR literal proven
still0xe000ed84 and byte-identical to the vendor container, MPU body and MPU_CTRL
still vendor, five fault vectors intact).210 tests pass,3 skipped.

Runner: shim2356-nodev-trials-run-once.py, refuses to run without
--approved-image-sha256=d7acaa1ab4d1812d65fab7a7c16412b1df8056945bc170a04725bb5066f6d6b2.

Device clean: root Recovery, boot_a2931647a, no journal.

## 2026-11-05 earlier:2354 SAYS ONE PASS, NOT A RESET LOOP; 2355 DROPS THE MPU CALL

2354 RAN. Image 4711cbe0, one authorized trial, boot_a restored to2931647a.
progress site0x01001914 again, and groups reported9. The groups word is NOT
host-written: the firmware's own shared-section template (file0x3d000) ships
  +0x00 version0   +0x08 input_va0x04002000   +0x10 groups8
  +0x04 features0  +0x0c output_va0x04003000  +0x14 group_stride0xa0
so the stub started counting at8 and one entry left it at9. Rung entries =1.

That kills the reset-loop hypothesis: the core runs the reset path ONCE and then
stops inside the0x01001918..0x0100192a window. It does not restart, and the
earlier worry that every pass rewrote the same word is gone.

WHAT IS IN THAT WINDOW, after2352 (read redirected) and2353 (MPU enable nop):
  0x1001918 ldr r0,=shared+0x14 ; ldr r4,[r0] ; and r4,#0x80 ; mov r0,r4
  0x1001922 bl0x1003126   MPU region programming, straight line, no barriers in it
  0x1001926 bl0x10019d8   mov.w r1,#0 ; ldr r0,=0xe000ed84 ; str r1,[r0] ; bx lr
  0x100192a bl0x10019e2   the helper whose first instruction is rung2
Both calls write only the PPB. The0x10019d8 literal really is0xe000ed84 (SCS),
and the next helper writes0xe000ef50 (I-cache invalidate all) then sets CCR.IC.

2355 REMOVES THE MPU CALL ONLY: `01 f0 00 fc` at0x01001922 becomes two nops.
Stub, counter and the four literal redirects are unchanged from2354, and the MPU
body plus its MPU_CTRL store keep the vendor bytes.
  rung0x010019e2 or later appears -> the MPU call was the wall
  still0x01001914                  -> the single0xe000ed84 store is the wall
The counter also tells us how many rungs the new path reaches (groups-8).

Artifacts: kernel ed50051d (patch0154, build id only), image
shim2355-nompu-ready/matisse-shim-gpu2355.img,26714112B,
SHA256 50ecca37f26d74cba50a81a4bf89b9723e9e3e7e1410747289dc1aa615d24b1c,
predicted partition digest
d3399f186ab3b502e78c0fb9b7735ac1afe23f2c59e5b33ab70f8de6c7525593,
embedded container 8fa97b0b586b4169be707ecad29004c8e880c15456b896becec553f2072bc0f7.
79 container bytes change: stub28, nine calls36, four literals12, nop pair4 minus
one overlapping byte alignment. verify2355-nompu.py PASS (the nop pair is
disassembled, the MPU body and MPU_CTRL confirmed still vendor, five fault
vectors and the whole0x010018ec entry untouched).210 tests pass,3 skipped.
The2354 decode branch now reports rung_hits = groups-8.

RECOVERY RESOURCE. /Users/xiaohuasheng/Documents/matisse_images_OS2.0.2.0.ULKCNXM_14.0
is a complete MT6983 fastboot package (all *_ab partitions, gpueb.img,
preloader_matisse.bin, super.img7.4G). Do NOT run its flash_all*.sh: the first
thing it does is `fastboot getvar anti/product/crc`, which hangs the ABL IOKit
pipe on this device. Flash individual partitions by hand instead. The single
boot_a fallback remains backup/recovery-20261021/boot_a-live-20261021.img.

Runner: shim2355-nompu-trials-run-once.py, refuses to run without
--approved-image-sha256=50ecca37f26d74cba50a81a4bf89b9723e9e3e7e1410747289dc1aa615d24b1c.

Device clean: root Recovery, boot_a2931647a, no journal.

## 2026-11-05 earlier:2353 CLEARED THE MPU ENABLE TOO; 2354 COUNTS THE RUNGS

2353 RAN. Image 4e977884, one authorized trial, boot_a restored to2931647a.
input_va is still0x01001914, version=0xb, features=7, output_va=0x70000.
Nop-ing the single `str r0,[r1,#-8]` at0x01003282 - the MPU_CTRL = 3 store that
would mark the whole0x01000000 region execute-never - changed nothing. So the
MPU enable is not the wall either, and the region writes before it cannot be
blamed through that path.

WHAT IS LEFT. Between the barrier at0x01001914 and the first rung at0x010019e2
there are exactly two calls after both experiments:
  0x1001922 bl0x1003126   MPU region programming, straight-line, no barriers
  0x1001926 bl0x10019d8   `ldr r0,=<lit> ; str r1,[r0]` with r1=0, one SCS write
Both write only to the PPB. Neither can be removed without changing behaviour,
and the fault recorder of2348/2349 recorded nothing even though all five fault
vectors do point at0x010019b1 - so no exception is being taken.

THE REMAINING AMBIGUITY is halt versus reset loop. A core that resets and
re-enters the reset path rewrites the ladder word every pass with exactly the
same value, and re-runs the redirected stores, so version=0xb / features=7 /
output_va=0x70000 look identical in both worlds. That has to be measured
directly before chasing more instructions.

2354 ADDS ONLY A COUNTER. Firmware behaviour is identical to2352: same nine
`bl` rungs, same four literals, and the MPU_CTRL store is restored to the vendor
bytes because2353 already proved the nop is useless. The stub now also loads
shared+0x10, increments it and stores it back, and saves r2 across the call:
  push {r0,r1,r2,lr} / mov r0,lr / subs r0,#5
  ldr r3,=shared+0x08 / str r0,[r3]          ; last site, unchanged
  ldr r2,=shared+0x10 / ldr r3,[r2] / adds r3,#1 / str r3,[r2]
  pop {r0,r1,r2,pc}
shared+0x10 is the reported `groups` word, so the count comes back in the same
report with no kernel change.
  groups == 1  -> the core executed the ladder once and then stopped
  groups  > 1  -> it is re-entering the reset path instead of halting
The r2 save matters: the stub now holds r2 live across the call.

Artifacts: kernel28f046e6 (patch0153, build id only), image
shim2354-counter-ready/matisse-shim-gpu2354.img,26714112B,
SHA256 4711cbe0863f6ba0e5e396dd292b06f71467074fcde6393ce6e7f1d96ffe2ebf,
predicted partition digest
00ee6179314c4a990b38c64171e11692d859f36fb9af6245243fa6ff7d45ceba,
embedded container 570942186e3a84ccdb0b3a9860fd9983e30eafcc7b0987fbf4b7255e4d65af8e.
76 container bytes change: stub28, nine calls36, four literals12.
verify2354-counter.py PASS (stub disassembled, both literal slots resolved and
checked, nine calls re-disassembled, MPU_CTRL back to vendor bytes, all five
fault vectors and the whole0x010018ec entry untouched).
210 tests pass,3 skipped. The 0x2354 decode branch was smoke-tested by relabelling
a real2353 capture, which exercised the groups>1 verdict.

Runner: shim2354-counter-trials-run-once.py, refuses to run without
--approved-image-sha256=4711cbe0863f6ba0e5e396dd292b06f71467074fcde6393ce6e7f1d96ffe2ebf.

Device clean: root Recovery, boot_a2931647a, no journal.

## 2026-11-05 earlier:2352 CLEARED THE READ; THE WALL IS THE MPU ENABLE, SO 2353 NOPS IT

2352 RERAN CLEANLY. Image c63fee8c, boot_a restored to2931647a.
input_va is still0x01001914 - repointing the first peripheral load (0x40003034 ->
shared+0x14, 0xa0) changed nothing at all. So that load is not the wall, and the
core really does stop in the few instructions after the barrier.

What is left there is `bl 0x01003126` at0x01001922. That function is pure MPU
programming: it writes RBAR/RASR pairs at0xe000ed9c for regions4..0x1d, builds
base addresses 0x04000000/0x08000000/0x10000000/0x20000000/0x28000000/0x30000000/
0x38000000/0x40000000/0xe0000000, and finishes at0x01003280 with
  movs r0,#3
  str  r0,[r1,#-8]      ; r1 =0xe000ed9c, so MPU_CTRL(0xe000ed94)=3
  dsb / isb / pop {r4,r5,r7,pc}
Region6 is RBAR0x10000016 (base0x01000000) with RASR0x110c0035, which decodes to
XN=1, AP=priv-RW, normal memory, size26 =>128MB. That marks the code base itself
execute-never once the MPU turns on, which would fault the very next fetch. On a
core that does not deliver the fault anywhere we can see, that is exactly the
"no progress, no exception" picture 2349-2352 kept producing.

2353 NOPS THAT ONE STORE (`41 f8 08 0c` -> two nops at0x01003282) and leaves the
region writes, the ladder and all four literal redirects untouched. Readout:
  input_va advances past0x10019e2 -> enabling the MPU is the wall; the map the
                                    firmware installs does not match this core
  input_va stays0x1001914         -> the region writes themselves, or the
                                    0xe000ed84 store in0x10019d8, is the wall

Artifacts: kernel0d038650 (patch0152, build id only), image
shim2353-mpu-ready/matisse-shim-gpu2353.img,26714112B,
SHA256 4e977884ce2caafe19ce75a1d93be19668b681599f355812027a5ca25f16585f,
predicted partition digest
6aeea616e350951abf8f7d70379dfcef3bc0e3e813a8250e898033c307b0adf0,
embedded container a59a03fde118caa5798a21a88b52ef8310946ffd6d0b204b8deb34b854b4cc40.
80 container bytes change: stub24, nine calls36, four literals12, stub tail4, mpu nop4.
verify2353-mpu.py PASS.210 tests pass,3 skipped.

Runner: shim2353-mpu-trials-run-once.py, refuses to run without
--approved-image-sha256=4e977884ce2caafe19ce75a1d93be19668b681599f355812027a5ca25f16585f.

Device clean: root Recovery, boot_a2931647a, no journal.

## 2026-11-05 earlier:2352 RUN WAS ABORTED DURING RESTORE; RESULT LOST, RERUN NEEDED

The 2352 trial DID run on the phone (journal: written-readback-verified,
fastboot_observed at83.66s), but the operator stopped the runner while it was in
the restore phase. The marks ring only exists in the running kernel and the
capture needs Recovery's adb, so no after-marks.bin was ever written and the
result cannot be recovered - rerun the same image.

State when picked up: device in fastboot with a half-restored boot_a (stock
prefix0x013e8000 flashed, the rest still the probe image), which is why
`reboot-recovery` fell back to fastboot. Recovery: flashed the64MiB
backup/recovery-20261021/boot_a-live-20261021.img straight over boot_a,
`reboot recovery`, then re-checked on device -
  boot_a =2931647a56039722ea2585990b8ef3b1a2daf4c9b990231879f753049eaf86b1
  root Recovery, ro.bootmode=recovery
The stale journal is archived as journal-aborted.json (deliberately NOT closed
via restore-only, which would have captured marks from the wrong boot and
published a bogus after-marks). preflight passes again.

Operational lesson: never interrupt between `image_written_verified` and
`complete_restored_recovery`; if it happens, restore boot_a by hand and archive
the journal instead of running restore-only.

## 2026-11-05 earlier:2351 STOPS ONE STEP AFTER THE BARRIER; 2352 MOVES THE FIRST READ

2351 RAN. Image 518dc208, one authorized trial, boot_a restored to2931647a.
version=0xb, features=7, output_va=0x70000 and input_va=0x01001914 - the ladder
advanced past the barrier entry but never reached 0x010019e2, the first rung
inside the helper called at0x0100192a.

So execution leaves0x01001914 and dies in the next few instructions. With all
three stores redirected, that window is the FIRST real peripheral access of the
whole boot:
  0x1001918 ldr r0,=0x40003034
  0x100191a ldr r4,[r0]        <- the read
  0x100191c and r4,r4,#0x80
  0x1001920 mov r0,r4
  0x1001922 bl 0x1003126
  0x1001926 bl 0x10019d8       -> writes0 to0xe000ed84
  0x100192a bl 0x10019e2       <- rung that was never reached
The read is the prime suspect: a load from a clock-gated block never completes
and never faults, which is exactly what "no progress, no exception" looks like.

2352 REPOINTS THAT ONE LITERAL (0x282c 0x40003034 -> shared+0x14) and changes
nothing else. shared+0x14 is group_stride=0xa0, so bit7 stays set and the later
`cbz r4` branch keeps its original direction. Readout:
  input_va still0x1001914 -> the read was not the wall; the SCS store at
                            0xe000ed84 inside0x10019d8 or0x1003126 is
  input_va0x10019e2 or later -> the 0x40003034 load is the wall

Artifacts: kernel ab78ba05 (patch0151, build id only), image
shim2352-read-ready/matisse-shim-gpu2352.img,26714112B,
SHA256 c63fee8c30916f58d1fbcf292f1ac82491728731c07fad99606f03c4522c0d3c,
predicted partition digest
f0f0ef39ab1d45ed0f39a2a6540fa0272269c8e00eefd075dcf39d82bd79f84b,
embedded container 0b29b6f99b4e3cde2ce2808792af632ad7b087f6f4c7d93f4da8c1033034058a.
76 container bytes change: stub24, nine calls36, four literals12, stub tail4.
verify2352-read.py PASS.210 tests pass,3 skipped.

Runner: shim2352-read-trials-run-once.py, refuses to run without
--approved-image-sha256=c63fee8c30916f58d1fbcf292f1ac82491728731c07fad99606f03c4522c0d3c.

Device clean: root Recovery, boot_a2931647a, no journal.

## 2026-11-05 earlier:2350 HIT THE BARRIER; THE udf PROBE WAS BLIND ALL ALONG

2350 RAN. Image 559fabbd, one authorized trial, boot_a restored to2931647a.
version=0xb, features=7, output_va=0x70000 and input_va=0x04002001 - bit0 was
ORed into the host word, so the MCU really executes the barrier at0x01001914
and `bx lr` resumes it cleanly.

That is the important result of the whole session: the 32-bit `udf` placed on
that barrier never trapped, and neither did the identically built markers in
2344-2347 nor the fault recorder in 2348/2349. The core (or this vector path)
does not turn udf into an exception here. Every "bitmap is0 / no marker" reading
since 2344 was therefore blind, including my own use of it to clear store1 and
store2. What IS proven now, by ordinary stores, is:
  - the reset entry runs to at least0x01001914 (isb after the PSP switch)
  - both original peripheral stores execute when they are real
  - nothing faulted up to that point
So the MCU is NOT stuck in the reset prologue; the old "WFI at0x0100302c"
picture has to be re-measured rather than assumed.

2351 TURNS THE TRICK INTO A LADDER. Nine barriers along the reset path become
`bl 0x010019b0`; the stub saves r0/r1/lr, parks if lr looks like an EXC_RETURN,
otherwise stores (site address) into shared+0x08 and returns with pop {r0,r1,pc}.
Because each visited site overwrites the word, input_va names the LAST site
reached:
  0x4002000 none   0x1001914 isb    0x10019e2 cache-clean helper
  0x10019fc        0x1001a2c        0x1002aec dispatch
  0x1002b26        0x1002b32        0x1003018 end of init
  0x1003036 idle-loop body
The three store literals keep their redirects, so version/features/output_va
still bracket the same run.

Artifacts: kernel82c7c473 (patch0150, build id only), image
shim2351-ladder-ready/matisse-shim-gpu2351.img,26714112B,
SHA256 518dc20896e797fa6ff3a71c019f6be2d9e936eadd0ab2086a02306138c7696c,
predicted partition digest
3696c5f2704a9f3f0f517029657f20a806f70bae3bfc07d51934b5be7717579c,
embedded container 457a0e9150ecb450d99a877eaf7f56f75c72bc2aecd45d71317bc6bedd0fbfb1.
73 container bytes change: stub24, nine calls36, three literals9, plus stub tail.
verify2351-ladder.py PASS (every call site re-disassembled with capstone, not
re-encoded).210 tests pass,3 skipped.

Runner: shim2351-ladder-trials-run-once.py, refuses to run without
--approved-image-sha256=518dc20896e797fa6ff3a71c019f6be2d9e936eadd0ab2086a02306138c7696c.

Device clean: root Recovery, boot_a2931647a, no journal.

## 2026-11-05 earlier:2349 PROVES THE SCS STORE RAN AND NOTHING FAULTED; 2350 DROPS EXCEPTIONS

2349 RAN. Image 9b7c9423, one authorized trial, boot_a restored to2931647a.
version=0xb, features=7, and output_va=0x70000 - the third literal redirect
worked, so the instruction at0x01001904 really executed. input_va stayed at the
host placeholder0x04002000: the udf on the isb still did not trap.

That kills the "posted SCS write" idea as well. Between0x01001904 and the isb
there are only `ldr r0,=0x0203f000`, `msr psp`, `mov.w r0,#2`, `msr control` -
no memory access left. So either the core does not take a 32-bit udf at all, or
the fault vectors do not lead to0x010019b0. Every "bitmap is0" reading since
2344 rests on that assumption, so it has to be tested directly.

2350 REMOVES THE EXCEPTION MODEL FROM THE MEASUREMENT. The isb at0x01001914
becomes `bl 0x010019b0` (00 f0 4c f8) and the stub there uses ordinary
instructions: mov r0,lr / lsrs r0,#28 / cbnz (parks if it was really a fault,
because EXC_RETURN has a nonzero top nibble) / ldr r3,=shared+0x08 / orrs bit0 /
str / bx lr. Nothing depends on vectors, udf or exception entry any more.
  input_va0x04002001 -> the barrier WAS reached (bit0 ORed into the host word)
  input_va0x04002000 -> not reached, and no fault occurred either
The three store literals keep 2349's redirects, so version/features/output_va
still bracket the path in the same boot.

Artifacts: kernel c0bb72e8 (patch0149, build id only), image
shim2350-branch-ready/matisse-shim-gpu2350.img,26714112B,
SHA256 559fabbd0c6a722f993ebbae7d8d6ce2d455035720cf4b18c966cbc48d58c39b,
predicted partition digest
15a79ab92bff9e23593e278359cde65e32a1a194a7e669e2d0fed0fd769129d3,
embedded container 299162663aab43ec23be17655591ea79df2e68a267f4326dcc67f8dce8303e39.
40 container bytes change: stub27, one bl4, three literals9.
verify2350-branch.py PASS.210 tests pass,3 skipped.

Runner: shim2350-branch-trials-run-once.py, refuses to run without
--approved-image-sha256=559fabbd0c6a722f993ebbae7d8d6ce2d455035720cf4b18c966cbc48d58c39b.

Device clean: root Recovery, boot_a2931647a, no journal.

## 2026-11-05 earlier:2348 NO FAULT EITHER; 2349 REDIRECTS THE SCS WRITE

2348 RAN. Image 7cb3892d, one authorized trial, boot_a restored to2931647a.
version=11 (0xb), features=7 - both redirected stores executed. input_va stayed
at the host placeholder0x04002000, i.e. the fault handler recorded NOTHING even
though it now selects MSP or PSP from lr bit2 exactly like the vendor prologue.
So 2343's "no fault" reading was incomplete, but the corrected probe still finds
no exception between store2 and the barrier.

That leaves one memory access in the window: `str r1,[r0]` at0x01001904 with
r0 =0xe000ed24 (SCS SHCSR, literal0x2824) and r1 =0x70000. It neither faults
nor lets execution continue - consistent with a posted write that is never
acknowledged, which stalls the core at or just after the store. Both earlier
posted-write suspects were simply device writes; this one is to the SCS.

2349 SENDS THAT THIRD LITERAL TO THE SHARED PAGE TOO:
  0x281c 0x40022000 -> shared+0x00   (version =0xb)
  0x2820 0x40022004 -> shared+0x04   (features =7)
  0x2824 0xe000ed24 -> shared+0x0c   (output_va =0x70000)
The recorder from 2348 stays (stacked PC -> shared+0x08, then b .), and the udf
on the isb at0x01001914 stays. One boot then separates four worlds:
  output_va0 and input_va0x04002000 -> the store never even issued
  output_va0x70000, input_va placeholder -> store ran, barrier still not reached
  output_va0x70000, input_va0x01001914 -> barrier reached AND fault delivery live
                                         => the SCS write was the whole wall
  input_va0x0100xxxx (other) -> names a different faulting instruction

Artifacts: kernel12dd22c2 (patch0148, build id only), image
shim2349-shcsr-ready/matisse-shim-gpu2349.img,26714112B,
SHA256 9b7c9423daa717f0e8f926b8e3b0dd30771f24b4978947ea538bd8216184464c,
predicted partition digest
2f65e64d336db9253490f841cd2245cd7ea4c1b5c96e919dd777b2d525f55020,
embedded container e0f68faaa5a0f17db7b23fd03d28373d161f59a7967fcd392301f0886749f3c8.
27 container bytes change: stub14, one marker4, three literals9.
verify2349-shcsr.py PASS.210 tests pass,3 skipped.

Runner: shim2349-shcsr-trials-run-once.py, refuses to run without
--approved-image-sha256=9b7c9423daa717f0e8f926b8e3b0dd30771f24b4978947ea538bd8216184464c.

Device clean: root Recovery, boot_a2931647a, no journal.

## 2026-11-05 earlier:2347 LANDED BOTH STORES, STILL NO MARKER; 2348 RECORDS THE FAULT PC

2347 RAN. Image b0455778, one authorized trial, boot_a restored to2931647a.
version=11 (0xb) and input_va=7 - BOTH redirected stores executed, and input_va
is 7 instead of the host placeholder0x04001000, so store2 at0x010018fc really
completed into the shared page. features=0: the isb marker at0x01001914 still
never fired. No device write is outstanding before the barrier, so the
posted-write theory is dead.

What is left in that window is `str r1,[r0]` at0x01001904 with
r0 =0xe000ed24 (SCS SHCSR, the literal at0x2824). It runs BEFORE0x01001908
sets PSP. Every probe so far (2343, 2344, 2345, 2346, 2347) read the exception
frame with `mrs r0,psp` only, so a fault taken on MSP could never be recorded -
the handler would read PSP=0, fault again and never write. That also voids the
2343 "no fault" reading: it only covered faults after the PSP switch.

2348 PUTS THE VENDOR'S OWN STACK SELECTION BACK. The stub keeps the vendor's
first14 bytes byte-for-byte (tst.w lr,#4 / ite eq / mrseq r0,msp / mrsne r0,psp),
then writes the stacked PC to shared+0x08 (input_va, proven writable by 2347)
and parks in b . instead of resuming. Both stores stay redirected, so one boot
answers everything:
  input_va0x01001904 -> the SHCSR store is what faults
  input_va0x0100xxxx -> that instruction is the wall0x1001906/1908/1910 mean
                        the literal load / msr psp / msr control
  input_va0x01001914 -> the UDF on the isb fired, i.e. the path reaches the
                        barrier and fault delivery works
  input_va0x04001000 -> nothing was recorded even with MSP handled

Artifacts: kernel44acadbe (patch0147, build id only), image
shim2348-faultpc-ready/matisse-shim-gpu2348.img,26714112B,
SHA256 7cb3892dc3d0103ab9d52c1d294b67b7eda6f9b25015a991f9991c6d008a5506,
predicted partition digest
631ade459aec33c463a5984a4ddb716a9a8d0ac393dfd8c1a6aba746c1fa8a44,
embedded container cc2e68e8077e76bb2a20db582aa1d7b87c80d764e0c92708b78d300f5e2251c4.
24 container bytes change: stub14, one marker4, two literals6.
verify2348-faultpc.py PASS.210 tests pass,3 skipped.

Runner: shim2348-faultpc-trials-run-once.py, refuses to run without
--approved-image-sha256=7cb3892dc3d0103ab9d52c1d294b67b7eda6f9b25015a991f9991c6d008a5506.

Device clean: root Recovery, boot_a2931647a, no journal.

## 2026-11-05 earlier:2346 MOVED ONE STORE, version=0xb, NO MARKER; 2347 MOVES BOTH

2346 RAN. Image 4117bf42, one authorized trial, boot_a restored to2931647a.
version=11 (0xb) - the redirect worked and the MCU executed the first store at
0x010018f4 - features=0, no marker at all.

So with store1 sent to shared+0 the core still dies before the isb. The only
device write left in that window is store2, `str r1,[0x40022004]` at0x010018fc,
which still pointed at the real peripheral. The posted-write story survives, it
just moves one instruction later: the write retires from the core, the following
literal loads and `msr psp` run, and the first synchronisation (msr control or
the isb) waits for a write that never completes.

2347 REMOVES THE LAST DEVICE WRITE BEFORE THE BARRIER. Both reset-store literals
move into the shared page:
  0x281c 0x40022000 -> shared+0x00   (version reads back0xb = store1 ran)
  0x2820 0x40022004 -> shared+0x08   (input_va reads back7  = store2 ran)
The 0x40003034 load keeps its real target on purpose: with no device write
outstanding, bit0 (isb) and bit2 (entry of the helper at0x010019e2, which is
after the load and after the cache-init call) separate three worlds:
  bitmap0x00 -> not the posted write; something before the barrier is worse
  0x01       -> barrier passed, so the0x40003034 load is the next wall
  0x03+      -> both the stores and the load are fine; the stop is deeper in

Artifacts: kernel0e283cba (patch0146, build id only), image
shim2347-bothstores-ready/matisse-shim-gpu2347.img,26714112B,
SHA256 b045577892e8fdd6ea3636c4fb9b86dc9aecbb34730e5c4dba63d35e46dbeda7,
predicted partition digest
b2fafdf31bf01d86d7787bff6c6e0388e908f9c666d4a094561fc3149dc47f45,
embedded container 5b189136194b9c678ab9e4a95ee437fc3b7625f2bbda06926a1a97f8e22bba45.
67 container bytes change: stub27, markers32, two literals8.
verify2347-bothstores.py PASS.210 tests pass,3 skipped.

Runner: shim2347-bothstores-trials-run-once.py, refuses to run without
--approved-image-sha256=b045577892e8fdd6ea3636c4fb9b86dc9aecbb34730e5c4dba63d35e46dbeda7.

Device clean: root Recovery, boot_a2931647a, no journal.

NEXT: 2347 needs its own boot_a authorization naming that SHA.

## >>> HISTORICAL 2026-11-05:2345 SAID IT DIES BEFORE THE isb; 2346 MOVED THE FIRST STORE <<<

2345 RAN. Image d7efa329, one authorized trial, boot_a restored to2931647a,
bitmap0 again - but this time on a channel 2342 proved writable (shared+4), and
with a marker on the isb at0x01001914, i.e. after `msr control` and before the
first peripheral load. Nothing fired.

TWO THINGS FOLLOW.
1. My mask extraction was wrong: the stub read ldrb r1,[r3] (byte0xf0), not
   [r3,#2]. Any hit would have set0xf0, so a0 bitmap still means "no marker ran"
   - the conclusion holds, but the per-site resolution was broken. 2346 reads
   [r3,#2].
2. The MCU therefore does not reach0x01001914. Between the proven store2
   (0x010018fc, 2342) and that isb there is only a core-private SHCSR write, two
   literal loads, `msr psp`, `movs`, `msr control`. None of those can hang. What
   CAN hang is the earlier store to the REAL0x40022000: a posted write retires
   from the core, lets the next instructions issue, and only stalls at the first
   synchronisation event - which is exactly that isb. That also reconciles the
   three builds: 2341 (both stores to the shared page) ran on to the peripheral
   load and stalled there; 2342 and 2345 (store1 real) stalled at the barrier.

2346 TESTS THAT. One literal changes:0x281c, the target of the first reset
store,0x40022000 -> shared+0 (the same redirect 2340 used, where0xb landed).
Instructions are untouched, the second store and the peripheral load keep their
real targets, and the trace bitmap stays on shared+4 with the [r3,#2] fix.
  bit0 clear            -> the stall is NOT the posted store; something between
                           store2 and the isb is worse than it looks
  bit0 set, bit1 clear  -> the store was blocking; the 0x40003034 load still is
  bit0+bit1             -> both accesses are fine, the stop is further in

Artifacts: kernel ceb28150 (patch0145, build id only), image
shim2346-store1-ready/matisse-shim-gpu2346.img,26714112B,
SHA256 4117bf420481d7827a5f27df73cf6c7dc22728e66b9ed57f57b639c6814f1442,
predicted partition digest
eefe5bafa97d77d02350140011a2c3c4a96160c128caf953a3f77e7c5f3efd86,
embedded container babb08f32edfc3132ae518cbccf6651ae55597382f5549311553b1ac2c47ed0d.
63 container bytes change: stub27 (one byte already matched), eight markers32,
store1 literal4. verify2346-store1.py PASS.210 tests pass,3 skipped.

Runner: shim2346-store1-trials-run-once.py, refuses to run without
--approved-image-sha256=4117bf420481d7827a5f27df73cf6c7dc22728e66b9ed57f57b639c6814f1442.

Device clean: root Recovery, boot_a2931647a, no journal.

NEXT: 2346 needs its own boot_a authorization naming that SHA.

## >>> HISTORICAL 2026-11-04:2344 BITMAP WAS DEAD; 2345 MOVED THE CHANNEL TO shared+4 <<<

2344 RAN. Image 98e90f05, one authorized trial, boot_a restored to2931647a,
bitmap0. That zero is not evidence about the MCU: 2344 wrote its bitmap to
shared+0xffc, and 2341 already proved that exact word never takes a write (the
one dead word in an otherwise writable page). Reusing it was my error; the
2343 fault probe used shared+0x10, which is a live word, so its "no fault"
conclusion still stands.

2345 CHANGES ONLY TWO THINGS. The handler now ORs into shared+4 - the word 2342
proved writable (features=7 landed there) - and the eight markers spend one bit
on the barrier at0x01001914, immediately after `msr control` and before the
peripheral load:
  0x01 0x01001914 isb   post-PSP switch, before the loader of0x40003034
  0x02 0x010019e2 dsb   first entry helper
  0x04 0x01001a2c dsb   third entry helper
  0x08 0x01002aec dsb   dispatch block
  0x10 0x01002b26 dsb   before NVIC->ISER
  0x20 0x01002b32 isb   before the TBB
  0x40 0x01003018 dsb   tail of init
  0x80 0x01003036 isb   inside the wfi idle loop
Handler is the same 28 bytes with one literal changed (shared+0xffc ->
shared+0x4); everything else in the container is identical to 2344, so the
change set is 60 bytes again.

WHY 0x01001914 MATTERS. 2342 proved both peripheral stores execute, and the
next real work is `ldr r0,=0x40003034 / ldr r4,[r0]` at0x01001918 - the first
peripheral READ in the reset path, and the one 2340 chose to repoint when it
wanted to "skip the0x03800000 copy". A stalled read there would look exactly
like what we see: alive, no fault, version0, no progress.

READ IT: bit0x01 clear -> stopped before/at that load (the load is the prime
suspect). bit0x01 set and0x02 clear -> stopped at the load or in the first
helper.0x03 -> the load completed and the helpers ran.0x3f passed the TBB,
0x7f reached the tail,0xff entered the wfi loop.

Artifacts: kernel f30b35ec (patch0144, build id only), image
shim2345-trace2-ready/matisse-shim-gpu2345.img,26714112B,
SHA256 d7efa329856c0993e4f6317861e410856f1053b928b24d38940f970ee35d946e,
predicted partition digest
71c18219bc1e3a068b68a1339e19bf891b359ed16b96fae1719f86f737a210ef,
embedded container dbd6bd5dd574f8907eea3ae5c1e15a481e697755aea61fe65257bb8a5170f56d.
verify2345-trace2.py PASS (same invariants as 2344:60 changed bytes all inside
stub+markers, entry literals and five fault vectors intact, anchor0x77000).
210 tests pass,3 skipped.

Runner: shim2345-trace2-trials-run-once.py, refuses to run without
--approved-image-sha256=d7efa329856c0993e4f6317861e410856f1053b928b24d38940f970ee35d946e.

Device clean: root Recovery, boot_a2931647a, no journal.

NEXT: 2345 needs its own boot_a authorization naming that SHA.

## >>> HISTORICAL 2026-11-04:2343 SAID NO FAULT; 2344 TRIED TO MAP HOW FAR IT GETS <<<

2343 RAN. Image 59caac47, one authorized trial, boot_a restored to2931647a.
groups stayed8, i.e. the word the resumable-stub would overwrite still held the
AP-written group count: NO CORTEX-M EXCEPTION WAS TAKEN. The handler is reached
only through vector0x18 (UsageFault) and PSP is already0x0203f000 by0x01001910,
so a fault after the two proven stores would have been recorded. The MCU is not
trapping; it is stalled.

WHERE IT CAN STALL IS NOW NARROW. 0x0100302c is an idle loop:
  add sp,#4 / pop{r4-r8,sb,sl,fp,lr} / 0x01003032 wfi / cpsie i / isb /
  cpsid i / b0x01003032
so "alive, no fault, no version" is exactly what a firmware sitting in WFI
looks like. Whether it arrives there is the next question.

2344 REPLACES THE PROBE WITH A TRACE. The same fault entry now returns: it ORs
a per-site bit into shared+0xffc and resumes after the marker, so one boot
reports every barrier the MCU provably passed instead of only the first trap.
Eight 4-byte udf.w markers replace dsb/isb barriers (skipping a barrier cannot
corrupt its neighbours), bits in execution order:
  0x01 0x010019e2  0x02 0x010019fc  0x04 0x01001a2c  (entry helper calls)
  0x08 0x01002aec  0x10 0x01002b26  0x20 0x01002b32  (dispatch block, pre-NVIC,
                                                      pre-TBB)
  0x40 0x01003018                                    (tail of init)
  0x80 0x01003036                                    (inside the wfi loop)
Handler (28B, replaced0x010019b0..0x010019cb, original handler is30B):
  mrs r0,psp / ldr r3,[r0,#0x18] / ldrb r1,[r3,#3] / ldr r2,[pc,#0xc] /
  ldr r4,[r2] / orrs r4,r1 / str r4,[r2] / adds r3,#4 / str r3,[r0,#0x18] /
  bx lr / nop / .word0x04000ffc
The udf immediate is the mask itself (hw2 =0xa000|mask, low byte read back with
ldrb), so no table is needed and the handler fits the old handler's slot.
Container changed60 bytes: stub28 + eight markers. Reset entry, both peripheral
stores, the peripheral load and all five fault vectors are byte-identical.
Build2344 also enables SHIM_CSF_ENTRY_CHECKPOINT, which 2343 did not - without
it the kernel never reads shared+0xffc and the bitmap would be invisible.

Artifacts: kernel 6b50a18e (patch0143, build id only), image
shim2344-trace-ready/matisse-shim-gpu2344.img,26714112B,
SHA256 98e90f05fd6ea41437b75fa1df27ac81b26bc506ea2d0384bc3e04adbc55c7b4,
predicted partition digest
0600b222716db709acd7ea2af5c19f361f7f109eb11310e549bd830f72feb337,
embedded container ab2c6b29af3eb09c04d063e91afb5410f98b8e8da0af701612934e09d6454308.
verify2344-trace.py PASS (stub bytes, eight barriers->udf.w masks,60 changed
bytes all inside stub+markers, entry literals0x40022000/0x40022004/0x40003034,
five fault vectors0x010019b1, anchor0x77000).210 tests pass,3 skipped.

Runner: shim2344-trace-trials-run-once.py, refuses to run without
--approved-image-sha256=98e90f05fd6ea41437b75fa1df27ac81b26bc506ea2d0384bc3e04adbc55c7b4.

Device clean: root Recovery, boot_a2931647a, no journal.

READ THE BITMAP: 0x00 never reached the first helper; <=0x20 reached the state
dispatch; 0x3f passed the TBB;0x7f reached the tail of init;0xff entered the wfi
loop. A missing bit is proof of non-arrival, never of failure.

NEXT: 2344 needs its own boot_a authorization naming that SHA.

## >>> HISTORICAL 2026-11-04:2342 CLEARED THE PERIPHERAL; 2343 ASKED IF IT FAULTS <<<

2342 RAN. Image 01a3905b, one authorized trial, boot_a restored to2931647a.
version=0, features=7. In this build store1 went to the REAL0x40022000 and
store2 to shared+4, so features=7 proves the real peripheral accepted its
store and execution continued to the next instruction. THE PERIPHERAL IS NOT
THE BLOCKER, and "the AP must power that block first" is dead.

Where it stops is now bounded: after store2 and before the firmware writes
0x0202c934. 0x01002aec then writes7 to0x40022008 and0x40022100..0x40022600,
sets NVIC->ISER=0x7ffd, and dispatches on the state word at0x0202c7a0 through
a TBB table into dozens of bl calls. Static analysis stops being useful there.

NOTE ON AN EARLIER INFERENCE: private_early is written with strb r3,[0x0202c934]
where r3 = [0x40030000] & 0x3f capped at0xa. A zero there therefore does NOT
prove the firmware never arrived; it can mean it arrived and computed0. Only
version=0 is proof that init did not complete.

BUILD2343 ASKS THE ONE QUESTION LEFT. All five Cortex-M fault vectors (NMI,
HardFault, MemManage, BusFault, UsageFault) point at the same0x010019b1, so
replacing that one handler answers "did it fault" and "where". A20-byte stub
overwrites0x010019b0:
  mrs r0,psp / ldr r1,[r0,#0x18] / ldr r2,[pc,#8] / str r1,[r2] / b .
  .word0x04000010
The stacked PC lands in shared+0x10, which the report already exposes as the
groups field. The reset entry, both peripheral stores, the peripheral load and
the vector table are untouched; exactly20 bytes of the container change.
  groups 0x0100xxxx -> it faulted, and that is the faulting instruction
  groups 8          -> no fault; it is spinning somewhere
  version0x01010000 -> it booted

Artifacts: kernel ea4f9fe315332f21e64d625f718cd588816d174070d10251a1b4c570d918971f
(patch0142), image shim2343-faultprobe-ready/matisse-shim-gpu2343.img,
27119616B, SHA256 59caac477a7b227efb033f50317515c020ae607e9ccec42c33388a720c46861f,
predicted partition digest
25fe0dc2768553e0491cf07d3941edf50b3086be65275f803a96e1a6e7d5e2ce,
embedded container37311174991f366d8e7958fd0a3f54d901b50444bd89e84854ba55def097e0f9.
verify2343-faultprobe.py PASS (stub bytes, five fault vectors still0x010019b1,
entry literals untouched, anchor0x77000, entry offset0xa8ec, leaf
0x3000000040081fc7, entry PA0x400818ec, entry word0x4826b672,293 pages).
210 offline tests pass,3 skipped.

Runner: shim2343-faultprobe-trials-run-once.py, refuses to run without
--approved-image-sha256=59caac477a7b227efb033f50317515c020ae607e9ccec42c33388a720c46861f.

Device clean: root Recovery, boot_a
2931647a56039722ea2585990b8ef3b1a2daf4c9b990231879f753049eaf86b1, no journal,
no pending restoration.

NEXT: 2343 needs its own boot_a authorization naming that SHA.

## >>> HISTORICAL 2026-11-02:2337 ENTRY PTE GATE BUILT OFFLINE; NO DEVICE TRIAL <<<

User corrected active reference to MT6983 Linux5.10 mali_kbase+GPUEB, not
v6.12 panthor. Local pinned mali-r32p1/mali_kbase_csf_firmware.c checks
header major (minor is recorded), reads shared_info[GLB_VERSION/4] and
requires nonzero GLB_VERSION after boot. Original vendor_a mali_csffw.bin
remains pinned SHA de22d2fc...4f7229a. No protocol/platform/memory-map
changes. 2336 CPU word D00CF8DF was code-section start VA01000000/PA40080000,
NOT reset entry. Vector selects Thumb010018ed; instruction VA010018ec,
page VA01001000+0x8ec, leaf3000000040081fc7 -> PA400818ec.

NEW: pre-AUTO guard walks actual AS0 PTEs and reads PA400818ec after the
existing 24B inline overlay. Requires first word4803b672 and exact24B;
logs leaf/entry PA/word separately from legitimate section-start D00CF8DF.
Any mismatch returns STATE before sweet_csf_boot/MCU_CONTROL. Wrong table,
wrong leaf, out-of-arena backing and wrong instruction fail closed. Synthetic
ASan/UBSan and pinned vendor C-loader tests PASS; 52 related tests run,
three skipped (existing optional dependencies), zero failures. Built distinct
2337 locally via
CLT; kernel16724248B SHA ddc8b3c09e5007e41baa1a156e45213c31ab9297659ad8fb98578ab3476291cc.
Image26714112B SHA70f16522004fdd6267f339d0be861cc7c1848979d08ba979b0855453487947c0.
Independent verify2337-entry-guard.py PASS: original container, all293 maps,
root40077000, PTE3000000040081fc7, entry word4803b672, same arena as2336,
stock fallback/ramdisk/signature bytes. Implementation commit628f9cb;no new
CI run. Build and audit in ignored
research/matisse/20261031-gpu/shim2337-entry-guard-{ready,prep}/.
Predicted full temporary boot_a SHA0d37dc4a6598153732033d0f9a2f22b3630d0fdeb26b4f1ed15f836385efd82b.
Adapted one-shot runner shim2337-entry-guard-trials-run-once.py in ignored
research,with full64MiB restore and exact image-hash gate. Read-only Recovery
preflight PASS: root/matisse/_a/recovery,boot_a67108864B and full original
SHA. No active journal or trial.

OBSERVATION: all 2337 evidence is CPU/offline; no MCU execution or firmware
readiness is proven. NO 2337 device boot or partition write; only read-only
Recovery preflight was run.
Last independently verified device state remains root Recovery with full
original boot_a SHA2931647a56039722ea2585990b8ef3b1a2daf4c9b990231879f753049eaf86b1.
The one 2336 hardware authorization is consumed. Any further destructive
device step needs its own confirmation under AGENTS.md. Preserve unrelated
dirty files and untracked0093. NEXT: if a new trial is authorized, run only
the bounded2337 candidate, capture pre-AUTO gate console plus fresh MCU
evidence if the gate passes, then restore all64MiB original boot_a and
independently verify Recovery/identity/geometry/SHA. Do not infer MCU fetch
from CPU PTE readback alone. Implementation committed628f9cb;handoff updated.

## >>> HISTORICAL 2026-11-02:2336 INLINE MARKER ABSENT; FULL RESTORE VERIFIED <<<

ONE authorized2336 trial completed;runner session47583 exit0. Temporary full
boot_a readbackdb9a2a7f...56dc9fb matched prediction. Fastboot85.51s;
single raw session restored stock prefix and rebooted Recovery,then restored
ALL67108864B original boot_a. Separate independent check at
2026-11-02T11:37:27Z verified root/matisse/_a/recovery,boot_a67108864B,
userdata114319917056B and complete original SHA
2931647a56039722ea2585990b8ef3b1a2daf4c9b990231879f753049eaf86b1.
Device left root Recovery;no active runner or pending restoration.

KEY OBSERVATION:fresh2336 progress04000ffc before0/after0,so neither inline
STUB nor tail TRAM observed. True version04000000 stays0;MCU1,JOB/MMU/AS/
GPU faults0;disable-53/status1,cleanup reset_raw200/completed0/error-53.
All common CSF fields match2333 exactly,including paired platform/path.
Fresh148 marks contain all87 correctly tagged2336 CSF qwords,match tail;
before matches2335 after,stale2333/2335 reject expected2336. Console
sweettrial2336 and iBoot publishergpu2336. Audit2336-result.py PASS.

INFERENCE LIMIT:placing first store inline removes2335's remote-tail-fetch
prerequisite,so absence cannot be attributed ONLY to that jump. It still
does NOT show original firmware reached any body PC. First marker targets
04000ffc;2334 success targeted04000000. They share SAME PA page and PTE
3060000040110e43,initially0,but different word/cache line. No MCU PC/AXI
response is observed. Do not claim coherent flag or MMIO cause,or undo2334
proof of its particular first fetch/write. No shareability change or second
trial performed. ONE2336 authorization consumed.

Implementation9a94b98,prepared handoff62ccc8f,running handoff26ff5fb.
No new CI/push;prior gh runs40262872038/40226767824/40226076666 remain
completed/action_required. All device/proprietary evidence ignored under
shim2336-inline-trials/gpu-normal;full restoration and comparison verified.
Unrelated dirt/untracked0093 preserved.

NEXT:offline design a clean one-variable control:copy2334's proven20B
in-place self-loop stub,changing ONLY its store target from04000000 to
04000ffc,then separately sample that word before cleanup. If it fails,
address/line-specific access is implicated; if it succeeds,the longer2336
inline code or its fetch/branch is implicated. Do not reuse the consumed
2336 hardware authorization. Keep existing mappings/NONE/memattr/platform.

## >>> HISTORICAL 2026-11-02:2336 TRIAL RUNNING; FULL RESTORE PENDING <<<

Runner session47583 ACTIVE;do not compete for USB/ADB or launch another trial.
ONE candidate imagef90c1abe...75490d3 written;full boot_a readback matches
predicteddb9a2a7fac2a62eaf40104c15c8396cf0575f044bd5f7c9ed6fa51d7556dc9fb.
Boot requested2026-11-02T11:34:13Z. Journal shim2336-inline-trials/gpu-normal/
journal.json statuswaiting-fresh-Recovery,restore_pendingtrue. Follow runner;
prioritize full67108864B original boot_a restoration,then independent
Recovery identity/geometry/SHA256 before interpreting evidence. Commits
9a94b98 implementation,62ccc8f candidate handoff. No2336 MCU result yet.
No shareability/platform/mapping changes;ONE authorized trial in progress.

## >>> HISTORICAL 2026-11-02:2336 INLINE CANDIDATE VERIFIED; ONE TRIAL PREPARED <<<

User replied 可以 to one corrected inline-first entry checkpoint trial and full
original boot_a restoration. Implementation committed9a94b98. No2336 device
write or active runner yet. 50 targeted tests PASS4.216s. Actual C loader
ASan/UBSan and Unicorn:STUB store at reset-page PC010018f2 before remote
fetch,TRAM at tail0100f904;forbidden tail fetch leaves STUB observable.
Full offline firmware resumes with identical registers,MMIO operations,
private probes and true version01010000/startup-WFI.

CLT kernel build exits0 SHA897139dbf6ab28c38e2cf256413a3b7443114cc5548987ab28aa126a90321fe3;
133-patch contextual replay matches local source. No new CI/push.
Candidate shim2336-inline-ready/matisse-shim-gpu2336.img26714112B SHA
f90c1abe48ecece4feaa7f6ad73b730871c02228caf6f7cc7e3b7054675490d3.
Independent verify2336-inline.py PASS:original containerde22d2fc...,all293
mapping/PTEs,root40077000,shared initialized data,stock fallback/ramdisk/
signature bytes,report696B. Only24B inline reset+64B tail overlays. Signature
authentication/autonomous Recovery unverified. Fresh read-only Recovery
preflight passes root/matisse/_a,boot_a67108864B,userdata114319917056B,
original SHA2931647a56039722ea2585990b8ef3b1a2daf4c9b990231879f753049eaf86b1.
One-shot runner shim2336-inline-trials-run-once.py prepared;predicted full
temporary partition SHAdb9a2a7fac2a62eaf40104c15c8396cf0575f044bd5f7c9ed6fa51d7556dc9fb.
NEXT:run ONE trial,capture fresh evidence,restore ALL67108864B original,and
independently verify Recovery/hash before diagnosis. Preserve unrelated dirt,
untracked0093 and all device/proprietary artifacts outside git.

## >>> HISTORICAL 2026-11-02:2336 INLINE CHECKPOINT AUTHORIZED; PREPARING <<<

User replied "可以" to placing the first marker inline in the proven reset
page. Authorization covers one corrected entry-probe hardware trial and full
original boot_a restoration. No2336 device write/active runner/build yet.
Last independently verified state:root Recovery,full original64MiB boot_a
SHA2931647a56039722ea2585990b8ef3b1a2daf4c9b990231879f753049eaf86b1.

Plan:store STUB at04000ffc directly in reset page01001000,DSB,then branch to
tail0100f900. Tail overwrites the SAME progress word with TRAM5452414d before
reproducing original reset prefix and resuming01001904. True version04000000
stays separate. No stack use,AS/root40077000/PTEs/initialized data/NONE31/
memattr/platform/shader behavior unchanged. Two checkpoints distinguish
observable inline store from observable tail arrival;absence still does not
identify an original firmware PC. Preserve unrelated dirt and untracked0093.
NEXT:assemble/validate/tests/build/independent image audit;fresh read-only
Recovery preflight;one trial,capture before cleanup,full original restore and
independent Recovery/hash verification. No speculation-driven mapping change.

## >>> HISTORICAL 2026-11-02:2335 REMOTE CHECKPOINT ABSENT; FULL RESTORE VERIFIED <<<

ONE2335 trial completed;runner33712 exits0. Fastboot129.26s;single raw session
restored stock prefix and rebooted Recovery. Full67108864B original boot_a
restored;independent check2026-11-02T10:59:35Z root/matisse/_a/recovery,
geometry and SHA2931647a56039722ea2585990b8ef3b1a2daf4c9b990231879f753049eaf86b1
PASS. No active runner or pending restore. Implementation1acf745,in-flight
handoff3dde8f0. No new CI/push. Device left root Recovery.

Fresh2335 kernel/all87 report qwords/148 marks/tail/cmdline/iBoot publisher
verified;before matches2334 after and stale2333/2334 rejected. KEY RESULT:
marker04000ffc remains0 before/after;true version04000000 also0. MCU1,
JOB/MMU/AS/GPU faults0;disable-53/status1;cleanup reset_raw200/completed0/
error-53. ALL common CSF fields exactly match2333,including platform/path.
The remote trampoline marker did NOT execute visibly. This cannot support
"entry marker then original body hangs" or body-PC bisection. Extra code-page
fetch0100f000 and distinct marker cache line are new diagnostic dependencies;
the2334 in-place store result remains valid. Do not revive universal first-
fetch failure or infer coherent-transaction cause from this negative result.

Audit2335-result.py PASS;ignored comparison-2333-2335.json,independent-post-
restore.json and fresh evidence under shim2335-entry-trials/gpu-normal/.
NEXT:remove the probe's pre-marker remote-fetch dependency by placing the
first marker inline in the proven reset page,then a second checkpoint in
the remote trampoline before reproducing the original prefix. Preserve
mappings/protocol/platform and distinguish these checkpoints from version.
This continues the user's requested entry-marker experiment;no speculative
shareability change or original-body bisection is justified yet.

## >>> HISTORICAL 2026-11-02:2335 TRIAL RUNNING; FULL RESTORATION PENDING <<<

Runner session33712 ACTIVE;do not compete for USB/ADB or launch another trial.
ONE candidate imagea47c3852...5f86677 has been written;FULL boot_a readback
matches predictedd240402b81af0a603291a4c42546250614fee5dd7d44ceebb9dac77472b0b18a.
Boot requested2026-11-02T10:55:54Z. Journal shim2335-entry-trials/gpu-normal/
journal.json statuswaiting-fresh-Recovery,restore_pendingtrue. Follow runner
and prioritize full67108864B original boot_a restoration,then independent
Recovery identity/geometry/SHA256 before interpreting evidence. Implementation
committed1acf745. No2335 MCU result yet;user's directed entry experiment is
in progress. No change to shareability or platform controls.

## >>> HISTORICAL 2026-11-02:2335 ENTRY CANDIDATE VERIFIED; ONE TRIAL PREPARED <<<

Latest user directs real firmware with entry marker, unchanged AS/root/memattr/
entry, section inventory and fresh pre-cleanup samples. This authorizes the
next2335 entry-probe trial and full restoration;2334 permission is not reused.
No2335 device write or active runner yet. Fresh read-only Recovery preflight
passes root/matisse/_a,boot_a67108864B,user_data114319917056B and original
SHA2931647a56039722ea2585990b8ef3b1a2daf4c9b990231879f753049eaf86b1.

47 targeted C/ASan/UBSan/Thumb assembly/Unicorn/evidence tests PASS3.443s.
Saved2334 kernel/source controls. Applied0133 identity only,132 contextual
patches including preserved untracked0093 exactly match local kernel source.
CLT build session74850 exits0;kernel SHA4c7b5e6aa12cddf51c3b1f5ff6c534c64aa228b1fe46d654f1801d72b2d6cf05.
gh prior40262872038/40226767824/40226076666 remain completed/action_required;
no new CI dispatch/push. Build logfirmware-static/kernel2335-entry-build.txt.

Candidate shim2335-entry-ready/matisse-shim-gpu2335.img26714112B SHA
a47c38520d4f78babfde27fcff8c0029876c6b3e893b9e6d04ec9f32e5f86677.
Independent verify2335-entry.py PASS:original containerde22d2fc...,all293
mappings/PTEs,arena/root40077000,initialized data,stock fallback/ramdisk/
signature bytes preserved. Signature authentication and autonomous Recovery
remain unverified. Actual C loader applies ONLY8B overlay010018ec+36B at
0100f900 in executable zero tail. Distinct marker04000ffc/PA40110ffc;true
version04000000/PA40110000. Trampoline restores r040022000/r1b/MSP02040000/
PRIMASK1 before resume010018f4. Original and instrumented offline firmware
have same MMIO sequence/private probes/final version01010000/startup-wfi;
993 vs986 instruction hooks. Added fetch page0100f000 means absent marker
alone does not localize failure. No stack use in trampoline. Report696B;
2335 reuses reserved words for marker before/after sampled BEFORE cleanup.

Source corrections:panthor ZERO copies initialized bytes then zeros tail;
DO NOT erase434 nonzero initialized shared bytes. Code start01000000 differs
from vector-selected Thumb entry010018ed. Shared c000001b coherent ABI flag
alone proves no hang:panthor maps coherent modes uncached and2334 accessed
the same shared mapping. Keep NONE31/transcfg42000006/memattr unchanged.

One-shot shim2335-entry-trials-run-once.py prepared,plan under matching trials
folder;predicted full temporary boot_a SHA
d240402b81af0a603291a4c42546250614fee5dd7d44ceebb9dac77472b0b18a.
No trial executed yet. NEXT:commit completed implementation,run this one
bounded candidate,capture fresh2335 evidence,restore ALL67108864B original,
then independently verify Recovery/hash before diagnosis. Do not compete
for USB/ADB once runner is active. Preserve unrelated dirty files0093;
all device/proprietary artifacts ignored. No speculative shareability change.

## >>> HISTORICAL 2026-11-02:2334 REAL MCU STUB STORE PASS; FULL RESTORE VERIFIED <<<

Executed exactly ONE authorized2334 reset-store trial;runner session23392
exited0. Full temporary boot_a readbackaf106351...718fbd8 matched prediction.
Fastboot at85.49s;one raw USB session restored stock prefix and rebooted
Recovery with OKAY. Recovery then restored ALL67108864B original boot_a.
Separate independent root/matisse/_a/Recovery/geometry/full SHA256 PASS at
2026-11-02T10:28:54Z:2931647a56039722ea2585990b8ef3b1a2daf4c9b990231879f753049eaf86b1.
Device left in root Recovery;no active runner or pending restoration.

KEY REAL RESULT:version header before0->after53545542,also matched by
paired access snapshots. The minimal Thumb reset-store code executed on
the MCU and wrote its shared header through the unchanged low-PA arena.
disable_error0/status0;cleanup reset_raw100/reset_completed1/cleanup_error0.
Contrast2333 original CSF:version0,disable-53/status1,reset_raw200/no complete.
All87 qwords320..406 in fresh148 marks are complete and match tail;kernel
mark99 and report tags2334. Old2333/before captures reject expected2334;
before marks/tail exactly match2333's after. Console18657B has fresh
sweettrial2334. Caveat:IBoot display still saysgpu2333 because frozen
shim/gpu.c hard-codes that publisher label. Do NOT claim freshgpu2334
IBoot label;freshness is established by kernel/tags/cmdline and changed
raw evidence. This was detected during result audit;no repeat trial needed.

MCU still sampled ENABLED1,stage4/error-53,JOB_RAW0,firmware_ready0,as
expected:the diagnostic deliberately emits no CSF IRQ/interface. MMU/GPU
faults remain0. Every common platform/path snapshot,including PDC/SLC and
protection masks,is identical2333. Common differences are only version,
successful disable/reset/cleanup and their derived fields. Root PA40077000,
COHERENCY_NONE31,AS_TRANSCFG42000006 and mappings are unchanged.

Inference supported:MCU reset-entry execution,that code page and shared
write work at low physical addresses with these tables. The proposed
failure at the very first vector/fetch/page-walk on this same path is
contradicted. NOT proven:all original firmware pages/private stack/MMIO/
peripheral initialization work. Original CSF may stall on a later access;
no original-firmware PC or bus/DEVAPC/EMI fault is identified. Keep firmware
readiness strict;this marker is NOT a valid interface/version/IRQ success.

Evidence ignored under shim2334-reset-trials/gpu-normal/{journal.json,
gpu-result.json,comparison-2333-2334.json,independent-post-restore.json,
pretrial-freshness.json,before/after-marks.bin,before/after-tail.bin,
after-console.txt,recovery-dmesg.txt} and gpu-normal-run.txt. Repeatable
audit2334-result.py PASS;plan complete-restored-Recovery,one consumed trial,
restore_pendingfalse. Build/verifier/runner pins in historical handoff below.
Implementation81dd6b0,patch-format9cbd7ec,in-flight handoffd497787. No push,
new CI run,second trial,DEVAPC/EMI clear,high-RAM move or further MMIO change.
Unrelated dirt/untracked0093 preserved;no device/proprietary data staged.

NEXT:offline inspect original reset010018ec through first private startup
stores and MCU-view MMIO,then design one discriminating checkpoint candidate.
Use existing source/disassembly/fetch audit;do not blindly rerun unchanged
CSF or infer that all DRAM/security paths are proven. A future image should
also make publisher labels explicit without confusing this frozen-control
trial. No further hardware experiment is currently authorized.

## >>> HISTORICAL 2026-11-02:2334 TRIAL RUNNING; ORIGINAL RESTORE PENDING <<<

Runner session23392 is ACTIVE. It wrote the ONE authorized candidate;
full boot_a readbackaf10635174cb7bfaf50a1c56453222bb426fbfce8845326ab0964b158718fbd8
matches prediction. Boot requested2026-11-02T10:26:16Z. Local journal
shim2334-reset-trials/gpu-normal/journal.json statuswaiting-fresh-Recovery,
restore_pending=true. DO NOT compete for USB/ADB or launch a second trial.
Follow the runner and prioritize FULL67108864B original restoration,then
independent root/matisse/_a/Recovery/full SHA256 before interpreting evidence.
Authorization is now consumed by this one trial;no second experiment.

Implementation/source/build handoff committed81dd6b0;patch formatting fix
9cbd7ec preserves identical generated source and passes contextual replay
test0.748s. User trial authorization remains active. Dispatch the one-shot
runner below once;after it starts follow only its local journal and prioritize
restoration. Do not launch a second runner or compete for USB/ADB.

2334 candidate BUILD+INDEPENDENT VERIFICATION PASS. CLT session19978 exit0;
kernel16724248B SHAa68627e3f6b0716081b61cd4f6d83d6c8454e50f702dc0dbbc8d90caa3ebb7c2.
131-patch contextual replay exactly matches current sweet_ufs source;
relative2333 ONLY SWEET_BUILD_ID changed. No new CI dispatch;gh prior
40262872038/40226767824/40226076666 remain completed/action_required.
Candidate shim2334-reset-ready/matisse-shim-gpu2334.img26714112B SHA256
aef92ca586ffc75960ed54c720fc72b671c133a7b543747c6f3dd6ebb0dd1ed0.
Independent verifier proves every rebuilt shim object except csf_blob.o
byte-identical2333;the linked shim before payload differs ONLY by20B at
the firmware reset handler. Same arena40077000,all293 mappings/PTEs/vectors
identical;reset PA400818ec/version40110000. Embedded firmware3a8e0a1c...
80d47a0f is original with ONLY file2780..2793 patched. Actual C arena equals
offline validated d3cc2c16...76a8259e. Firmware diagnostic-only;no IRQ/valid
interface. Stock Linux+32MiB,ramdisk,signature bytes intact;signature NOT
authenticated and automatic Recovery NOT verified. Existing raw-prefix
plus full64MiB restoration path retained. Exact-blob offline stub replay PASS.

Prepared authorized one-shot runner shim2334-reset-trials-run-once.py SHA
bf986f0556d1dc97fb35d9608271dfa66183f02c2572cef99f6cb277d86fd962;
read-only preflight PASS. Plan shim2334-reset-trials/restoration-plan.json
status authorized-prepared,trial_count_executed0,restore_pendingfalse.
Predicted full temporary boot_a SHA256
af10635174cb7bfaf50a1c56453222bb426fbfce8845326ab0964b158718fbd8.
No phone write yet. NEXT:commit completed implementation,execute this ONE
already authorized trial,follow journal and restore ALL67108864B original;
independently verify Recovery identity/geometry/full hash before diagnosis.
No concurrent ADB/raw USB actions once runner starts. Do not repeat trial.

User explicitly said "可以上机现在在rec" after the20B Thumb stub explanation.
This authorizes ONE reset-store diagnostic phone trial and its complete
original boot_a restoration;no repeat trial or other hardware experiment.
No renewed permission question is needed for this already authorized step.
Read-only preflight2026-11-02T10:17:32Z PASS:root/matisse/_a/recovery,
boot_a67108864B and userdata114319917056B;full original boot_a SHA256
2931647a56039722ea2585990b8ef3b1a2daf4c9b990231879f753049eaf86b1
matches the independent full local backup. No runner/restore was active.

Builder now supports explicit2334 reset-store mode:patch only the original
container's20 reset-entry bytes,and use the unchanged loader/shim objects
and original2333 arena placement. It re-runs the actual C loader and rejects
any difference from the verified offline patched arena. No added device
register writes. Patch0132 changes ONLY kernel build identity2333->2334;
696B report layout preserved. Decoder separates fresh stub marker from
firmware-ready,which is always false for this diagnostic build.
44 targeted tests PASS3.131s. Saved prior kernel/source pins under ignored
firmware-static/kernel2333-control and sweet_ufs2333-control.c. Applied0132
to the verified local build source and launched CLT kernel build session19978,
logfirmware-static/kernel2334-reset-build.txt. No2334 image or write yet.
NEXT:finish build,independently verify exact candidate/unchanged mappings,
prepare the bounded one-shot restoration runner,execute ONE authorized trial,
capture fresh2334 evidence,and restore ALL64MiB with independent SHA256.
Preserve unrelated dirt/untracked0093;keep all device/proprietary data ignored.

## >>> HISTORICAL 2026-11-02: RESET-STORE STUB VERIFIED OFFLINE; NO NEW PHONE TRIAL <<<

Reviewed the user's bus-path diagnosis against actual2333 code/evidence.
Initial soft reset completed; MCU AUTO/disable timeout with no version/IRQ
is compatible with a blocked memory transaction, NOT proof of first-fetch
or page-walk hang. No real MCU PC/bus response/DEVAPC/EMI violation evidence
has been collected. Existing MFG1 protection exclusions remain narrow.

Corrections grounded in existing sources:55667788 is GPUEB handoff magic
read at13c1fd24,not a CSF container header. GPUEB INIT0/POWER_ON1 already
acknowledged before MCU start. Actual mali_csffw starts c3f13a6e;the C loader
validates it and uses header section VAs. Version is at MCU VA04000000,
not input04002000/output04003000. Reset vector VA0 contains MSP02040000
and Thumb entry010018ed. With unchanged2333 arena40077000,reset code is
PA400818ec,version PA40110000;code section starts PA40080000. Full used
arena ends401a4000,not400bc000(private probe page only). Original MT6983
source identifies PLL CON1 bit31 as SDM_PCW_CHG,not lock or POSDIV.

Added public20B Thumb/M-class reset-store assembly and opt-in offline
--reset-store-stub to tools/matisse-csf-fetch-audit.py. It replaces ONLY
20 bytes at the vector-selected reset entry,stores53545542 to the correct
version header,DSB,self-loop. Original vectors/PTEs/other arena bytes stay
identical. It never supplies an IRQ/valid interface;firmware_ready remains
false and the hardware readiness gate is unchanged. No shim or kernel
behavior changed. Implementation committed6cbf445 (3 files);this handoff
and the detailed diagnosis are committed separately.

21 targeted tests PASS0.560s,including actual C loader ASan/UBSan,ARM
Thumb cross-assembly/zero relocation check,emulated store,RO rejection,
and prefilled-marker-without-execution rejection. Exact proprietary blob
offline replay at measured2333 PA/group6 reaches diagnostic-self-loop
in6 instruction hooks,one4B shared write53545542,no MMIO/probe writes or
access violations. Original arena SHAa4c928c5...1feb9fc2 matches2333;
stub arena d3cc2c1637107d16e281d6302e989c4afc7325e9c1b4417eb38c7a3076a8259e.
Normal firmware replay byte-for-JSON equals HEAD:986 instructions,
version01010000,startup-wfi. These are synthetic results,not phone fetch.
Ignored reports:firmware-static/reset-store-2333-offline.json and
reset-store-normal-regression.json under research/matisse/20261031-gpu/.

No new image,kernel build,CI dispatch,push,device write/reboot/MMIO access
or restoration was performed. gh lists prior40262872038/40226767824/
40226076666 completed/action_required;no new run ID. Last measured device
state remains2333's fully restored root Recovery;not refreshed this turn.
Unrelated dirty files/untracked0093 preserved;no proprietary data staged.

NEXT:integrate the validated reset patch as an explicit shim diagnostic
candidate with frozen2333 controls,verify actual placement and fresh build
identity,and prepare its one-shot full64MiB restoration plan. No candidate
or runner exists yet. Audit exact MT6983 DEVAPC/EMI status ownership and
clear semantics before adding access;no guessed clear writes. A missing
stub marker still cannot distinguish reset/vector/fetch/write failure.
Keep real firmware readiness dependent on fresh global IRQ and valid
nonzero interface. No concrete new boot_a write has been confirmed;
AGENTS requires confirmation before a destructive device step.

## >>> HISTORICAL 2026-10-31: CSF2333 TRIAL COMPLETE; FULL RESTORE VERIFIED <<<

Executed exactly ONE authorized2333 image36be7135 trial;runner session19724
exited0. Full candidate boot_a readback4dc84a77...b65cc580 matched prediction.
Fastboot at86.58s;single raw USB session download/flash:boot_a/reboot-recovery
all OKAY. Recovery restored ALL67108864B original boot_a. Separate independent
root/matisse/_a/recovery/geometry/full SHA256 PASS at2026-10-31T08:19:45Z:
2931647a56039722ea2585990b8ef3b1a2daf4c9b990231879f753049eaf86b1.
No active runner or pending restore;device left in root Recovery.

Fresh2333 marks148 include87 complete CSF qwords320..406,exactly match tail.
Console18657B names gpu2333/sweettrial2333. Before marks/tail byte-match
previous2332 after;stale2332 rejects expected2333. Paired path flags3;
all common GPU/CSF fields are IDENTICAL2332 except kernel build label.
MCU remainsstage4/error-53/status1,version0,JOB_RAW0,MMU_RAW0,AS status/fault0;
disable-53/status1,reset_raw200/reset_completed0,cleanup-53. Not firmware-ready.

New observed before==after:path RPC enable0/statusfff0fff0;INFRA enable0/
statusffffffe0;EMI0 enable0/statusff800020;EMI1 enable0/statusff802020.
Exact original MFG1 masks RPCf0000/INFRAf/EMI0+1c0000 are ALL CLEAR in enable
AND status before AUTO and after timeout. Gate passed and MCU AUTO ran.
PDC CG018d0001;ST0/1/2/4/5/6 each02000001,all sampled active-control bit0 set.
SLC group606002006 matches original source literal. These are measured
control words,not proof of MCU fetch,all memory-path reachability or shader
power. The specific missing-MFG1-protection hypothesis is not supported by
this trial;do not force clear unrelated RPC bits or replay MFG0 words.
FirmwareCPU readbackd00cf8df,VA01000000/PA40080000,arena40077000 unchanged.

Evidence ignored under shim2333-path-trials/gpu-normal/{journal.json,
gpu-result.json,comparison-2332-2333.json,platform-field-analysis.json,
independent-post-restore.json,before/after-marks.bin,before/after-tail.bin,
after-console.txt,recovery-dmesg.txt} and gpu-normal-run.txt. Freshness/ABI/
comparison and independent restoration PASS. No rebuild,test suite,CI run
or push. Implementation24c968b/build handoffd900294 remain applicable.
Authorization consumed;no second trial. NEXT:offline inspect original MCU
AUTO/debug/CSF initialization prerequisites against the unchanged startup
registers. No root cause or new hardware experiment selected yet. Preserve
unrelated dirty files and untracked0093;do not stage device/proprietary data.
Measured result/docs committed6f8822d. Trial authorization fully consumed;
no2334 image,new runner,build or device-write permission exists.

## >>> HISTORICAL 2026-10-31: CSF2333 SINGLE TRIAL AUTHORIZED <<<

User replied 可以 to ONE exact2333 image36be7135 boot_a trial,fresh paired
path evidence,full67108864B original restoration and independent SHA256.
Fresh preflight root/matisse/_a/Recovery/full original hash PASS;candidate,
backup,stock-prefix and runner dfe50627 pins match. No existing2333 journal
or active runner. Authorization covers this single trial and restoration.
Runner session19724 active;written full partition SHA2564dc84a77...b65cc580
matches prediction;boot requested. Follow journal and prioritize complete
original restoration. Do not compete for ADB/raw USB while runner active.
No second trial or forced MFG/RPC write is authorized.

## >>> HISTORICAL 2026-10-31: CSF2333 PLATFORM PATH BUILT; TRIAL UNAPPROVED <<<

2332 trial and full restoration are complete below;no new device write.
Pinned Xiaomi270b84910b941bf75490fccdb5fb2b3021dd7cbf scpsys MFG1 table
contradicts the proposed RPC halfword decode:enable103c/status1048 are
separate registers;MFG1 mask000f0000,so observedfff0fff0 has those STATUS
bits clear. Enable103c,INFRAca0/cac and EMIc60/c6c/c70/c7c are not sampled.
SPM statusf includes MFG0 bit1,MFG1 bit2,MFG2 bit3. PDCv2/fake-SPM means
PWR_CON low bits alone do not establish off domains. MFG0 SRAM sleep9/13
differs from MFG1 powerdown8/12;do not copy MFG0 words to other domains.
Implemented:2333 appends paired exact-mask RPC/INFRA/EMI plus raw PDC/SLC
snapshots;blocks MCU AUTO if a documented MFG1 protection bit remains set.
No forced rails/clock/protection writes. Reset already waits IRQ bit8.
ABI696B/87 qwords320..406,old560B prefix preserved;publication/decoder and
contextual patch0131 complete.72 targeted tests PASS5.399s,including real C
ASan/UBSan,each documented protection bit,blocked-before/no-AUTO,after-only
obstruction,unchanged unblocked write trace,source pins and stale ABI tests.
Three freestanding ARM64-Werror/PIC compiles PASS. Full local CLT kernel
build exit0,16724248B SHA256
61790395f3043744234f0363aceed595fcf35b8dcf0b18836fa4259c1df94bfa.
130-patch contextual replay MATCH source81775100f8f01e0e5404c60ddf29f3045ba581dbcf256df48e49f6d2ab0f3ad8;
preserved untracked0093 hash54f0aaa5...de65365b. No new CI run or push.
gh latest40262872038/40226767824/40226076666 remain action_required.

Candidate shim2333-path-ready/matisse-shim-gpu2333.img,26714112B,SHA256
36be7135a2ffa2995a8c3e7f518d73191c4188e9ec563c9d86670d7dc16497b5.
Independent verifier PASS:stock Linux+32MiB/ramdisk/signature bytes,pinned
sources/frozen objects,696B ADT,PIC,rootrw0/ufsrw0,all293 mapped pages.
Arena PA40077000/executable PA40080000 AND full arena bytes unchanged2332;
firmware/memory/GPUEB objects byte-identical2332. Signature is retained,
NOT authenticated;automatic Recovery and2333 hardware readiness unverified.
Historical2331/2332 decode byte-for-JSON identical;2326..2330 differ only
previously introduced error provenance labels,not raw CSF/GPU fields.

Only read-only Recovery preflights ran at2026-10-31T08:11:39Z:root/matisse/
_a/recovery,boot_a67108864B,full original hash2931647a...9eaf86b1 PASS.
Prepared runner shim2333-path-trials-run-once.py SHA256
dfe5062718f431169e7cd1b9b84804b16338c451372e86ee0a8c3be8046f8c46;
plan prepared-unapproved,authorization null,trial_count_executed0,no journal.
Predicted full temporary boot_a hash
4dc84a77ea14e5716cb0f2a0496ac5104a2ac700eaa91e8db0be1a1bb65cc580.
No new device writes/reboots/hardware results or pending restore. Prior2332
authorization consumed. NEXT:confirm ONE exact2333 image36be7135 boot_a
trial,fresh evidence,full64MiB original restoration and independent hash
before entering runner write branch,as AGENTS requires. Otherwise continue
offline source audit. Preserve unrelated dirt/untracked0093. Ignored evidence:
firmware-static/path2333-*,kernel2333-*,shim2333-path-ready/manifest.json and
independent-verification.json,verify2333-path.py,and prepared runner/plan.
Implementation/source audit/tests/build result committed24c968b (16 files).
Only intended files staged;unrelated shim/collector/marks dirt and0093 stay
untouched. No push,CI dispatch or2333 device write. Next approval question
must identify candidate36be7135 and full64MiB original restoration.

## >>> HISTORICAL 2026-10-31: CSF2332 TRIAL COMPLETE; FULL RESTORE VERIFIED <<<

Executed exactly one authorized2332 trial;runner session72667 exited0.
Full trial boot_a readback49404819...adb8cad1 matched prediction. Reached
Fastboot85.62s;raw download/flash:boot_a/reboot-recovery all OKAY. Then
Recovery restored ALL67108864B original boot_a. Independent post-restore
root/matisse/_a/recovery/geometry/full SHA256 PASS at07:54:53Z:
2931647a56039722ea2585990b8ef3b1a2daf4c9b990231879f753049eaf86b1.
No active runner or pending restore. Device left in root Recovery.
Fresh2332 marks131 include70 complete qwords320..389 and match tail;
console18569B names gpu2332/sweettrial2332. Before marks/tail byte-match
previous2331;stale2331 fails expected2332. Paired access flags3. Both
snapshots:code wordd00cf8df atCPU PA40080000 matches expected;version0,
MMU_RAW0,JOB_RAW0,AS status/fault/address0,L2_READY1/0,transition0/0.
MCU remains stage4/error-53/status1;disable-53/status1,reset_raw200,
reset_completed0,cleanup-53;no firmware-ready or acceleration success.
Full comparison against2331 changes only build tag and expected4KiB
relocations TRANSTAB/private PA. All other common GPU/CSF fields,including
platform power/clock/RPC words,are identical. CPU code-byte visibility and
L2-ready are now measured together;these do not prove MCU fetch,PC,EMI
reachability or that forced MFG/RPC writes are needed. AS_ACTIVE is0,not1.
Detailed fresh evidence and independent restore JSON stay ignored under
shim2332-access-trials/gpu-normal/. Authorization consumed;no second trial.
Freshness/ABI/common-field audit PASS;documents updated for measured result.
NEXT:offline audit original PDC CG/ST and EMI/memory-path initialization
before selecting a distinct next experiment. No blind MFG/RPC writes or repeated2332. Implementation
c2adc13/build handoff81f9fc3;measured result committed18aaa47.
No rebuild,CI run,push or repeated tests.

## >>> HISTORICAL 2026-10-31: CSF2332 SINGLE TRIAL AUTHORIZED <<<

User specifically replied 可以 to ONE normal2332 image2d57a0d0 boot_a trial,
fresh paired evidence,complete64MiB original restoration and independent
SHA256 verification. Fresh root/matisse/_a/Recovery preflight PASS;full
boot_a SHA2562931647a56039722ea2585990b8ef3b1a2daf4c9b990231879f753049eaf86b1.
Candidate2d57a0d05cdb9aff350d614dce1c1ad0bd0bd0efcf294ed3901fac3f2639c038,
runner908f37f522bd267653fbcc83bcee4c1455ce3ce73b9e7846e4f6152a1b4eb270,
backup and stock-prefix pins match. No existing2332 journal/active runner.
Authorization covers exactly this one trial and its complete restoration.
Runner session72667 active. Candidate boot_a full readback verified SHA256
494048191baa24a9ce2ddbb88eadf789b9b52a57d40080a1883e91dbadb8cad1;
normal reboot requested,journal waiting-fresh-Recovery,restore_pending=true.
Do not compete with active runner for ADB/raw USB. Restore first.
Once started,follow shim2332-access-trials/gpu-normal/journal.json and
prioritize full original restore plus independent hash before interpreting
GPU evidence. Do not launch a second trial. No force-MFG/RPC writes added.

## >>> HISTORICAL 2026-10-31: CSF2332 ACCESS SNAPSHOT VERIFIED; TRIAL UNAPPROVED <<<

User proposes paired AS0/L2/firmware-word diagnostics plus forced MFG1/2 and
RPC sleep-protection writes. Selected corrected READ-ONLY snapshot only.
AS0+04 is TRANSTAB_HI,+08/+0c MEMATTR,+18 COMMAND; fault/address/status are
241c/2420/2424/2428. L2_READY160,write-only L2_PWRON1a0;140/180 are shader.
Pinned Panthor panthor_mmu_fault_mask explicitly treats MMU upper16 as
REQ_COMPLETE (legacy shared KMD header has a different bus-error definition).
2331 already measured MMU_RAW0,AS0 fault/address/status0,L2_READY1,version0.
JOB platform field is STAT100c;job_raw is RAW1000. Executable01000000 is
separate from shared04000000. No MCU PC or stalled-AXI proof exists.
GPUEB/PDCv2 ownership,fake-SPM APIs and unverified RPC1048 bit semantics
remain reasons NOT to force MFG1/2 or clearfff0. No rail/PLL/RPC writes added.

2332 implementation:opt-in paired correct readable AS0/L2 fields,owned CPU
arena executable first-word and shared version,before AUTO/after wait before
cleanup. Native shim CPU MMU/caches off;barrier before readback. Expected
word derives from pinned firmware;CPU readback is not MCU execution. Old
440-byte prefix preserved,new120B,total560B/70 qwords320..389;patch0130.
Decoder rejects incomplete/contradictory success evidence and stale builds.
73 targeted tests PASS8.879s;after decoder strengthening20 evidence tests
PASS0.967s. ASan/UBSan boot and ABI tests plus same-config snapshot on/off
actual-C write traces PASS;freestanding ARM64-Werror compile PASS.

Local full CLT kernel build exit0,size16724248 SHA256
f399367f1a0b6a336a8515b899a6d718f8d126332ef326549c70bb4030841438.
129-patch contextual source replay matches sweet_ufs SHA256
5c5add1eccbbafb4f7e76743aff53277ee57cb0403f7e4c415e2f7ef2a243cc8;
includes preserved inherited untracked0093 SHA25654f0aaa5a0390bc0678eca60e55bc192d3ebea315daab808a3c456a1ce65365b.
No new GitHub Actions run or push. Fresh gh list:40262872038,40226767824,
40226076666 all completed/action_required;these are prior runs,not2332 builds.

Candidate:research/matisse/20261031-gpu/shim2332-access-ready/
matisse-shim-gpu2332.img,26714112B,SHA256
2d57a0d05cdb9aff350d614dce1c1ad0bd0bd0efcf294ed3901fac3f2639c038.
Independent verify2332-access.py PASS:80402548B expanded,stock Linux+32MiB,
intact ramdisk/signature bytes,source/frozen pins,560B/70-qword ADT,PIC and
rootrw0/ufsrw0. Signature is retained,NOT authenticated;automatic Recovery
is NOT verified. Firmware/memory/GPUEB objects byte-equal2331.
Code growth moves BSS arena PA40076000->40077000 (+4096),NOT byte-identical
physical mapping. Accepted/documented diagnostic placement difference:
actual C rebuilt both arenas;all300 nonzero table/leaf descriptors move
by4096 with identical nonaddress bits,all293 mapped pages preserve VA,
relative offsets and payload bytes. New arena SHA256
a4c928c577a6033e2e1ade2fd2352965270bd8ff6e4f473d4f7d391c1feb9fc2.
Executable probe VA01000000,offset9000,PA40080000,expected wordd00cf8df.
These are offline checks,not measured physical reachability;extra reads
and different PAs mean this is not a strictly address-identical trial.

Fresh separate read-only Recovery preflight2026-10-31T07:46:44Z PASS:
root/matisse/_a/recovery,boot_a67108864B,full original SHA256
2931647a56039722ea2585990b8ef3b1a2daf4c9b990231879f753049eaf86b1.
Prepared one-shot runner shim2332-access-trials-run-once.py SHA256
908f37f522bd267653fbcc83bcee4c1455ce3ce73b9e7846e4f6152a1b4eb270;
its read-only preflight also PASS. Predicted full candidate boot_a SHA256
494048191baa24a9ce2ddbb88eadf789b9b52a57d40080a1883e91dbadb8cad1.
Plan shim2332-access-trials/restoration-plan.json is prepared-unapproved,
authorization=null,trial_count_executed0,restore_pending=false;no journal.
No2332 flash,reboot,MMIO hardware test or readiness result exists.2331
approval is consumed. No active runner or pending restoration.

Ignored evidence:firmware-static/access2332-{tests-final,evidence-final}.txt,
kernel2332-access-build.txt,kernel2332-source-replay.json,
access2332-independent-recovery-preflight.json;shim2332-access-ready/
{manifest.json,independent-verification.json};verify2332-access.py and
prepared runner/plan. Decoder rechecked actual2326..2331 captures unchanged.
NEXT:ask specific approval for ONE normal2332 image2d57a0d0 boot_a trial,
fresh paired evidence,full64MiB original restoration and independent hash.
Do not enter runner write branch before that confirmation. Preserve all
unrelated shim/collector/marks dirt,untracked0093 and device/proprietary data.
Implementation committed c2adc13 (12 files,225 insertions/29 deletions).
This handoff/docs are committed separately. The inherited unrelated dirty
files and untracked0093 were not staged. No failed command reached any
device write;only read-only Recovery preflights ran.

## >>> HISTORICAL 2026-10-31: CSF2331 SNAPSHOT TRIAL; MCU TIMEOUT; FULL RESTORE <<<

User approved ONE normal2331 imagee1920561 boot_a trial,fresh evidence and
complete original restoration. Executed exactly once;runner session62578
exited0. Candidate26714112B SHA256
e1920561234a68e4472b91ffa2e724385940c6f7c441fc237b80b1a3b4746ad2.
Full candidate boot_a readback matched predicted SHA256
efa6122218e60edd6b515281be3a2b8319ab3910b329a99c3cabee2b5ec799ff.
Normal boot reached Fastboot after82.54s;one persistent raw USB session
returned OKAY for stock-prefix download013e8000,flash:boot_a,reboot-recovery.
Recovery captured evidence then restored ALL67108864B original boot_a.
Separate independent root/matisse/_a/Recovery/geometry/full SHA256 PASS:
2931647a56039722ea2585990b8ef3b1a2daf4c9b990231879f753049eaf86b1.
Journal/plan complete-restored-Recovery,restore_pending=false,one consumed
authorization,evidence_decoded=true. No active runner or pending restore;
no user USB/key intervention. No rebuild,CI run,push or repeated test suite.

Fresh marks build2331/count116 include55 CSF qwords320..374 and exactly
match the4198400B tail. Before marks/tail byte-equal2330 previous after;
stale2330 rejects expected2331. Fresh18657B console independently names
gpu2331/sweettrial2331. All common CSF and GPU fields exactly equal2330;
new platform flags3 confirm both before/after samples. MCU staysstage4,
error-53,status1,JOB_RAW0,MMU_RAW0,AS status/fault0,version0,L2_READY1;
disable still times out-53,status1;reset_raw200/reset_completed0,cleanup-53.
GPUEB INIT0/ON1/OFF0 and initial reset100 remain observed. Firmware-ready
and acceleration remain false.82.54s vs2330's84.57s is one-run timing only.

Measured before->after AUTO:GPU_STATUS100->101,MCU_CONTROL0->2. GPU fault
status/address and JOB_INT_STAT remain0. Both SPM status words stayf;
MFG power0..3 stayc000224d/c0000112/c0000112/1112;PLL words82177627/832013b1,
TOPCKGEN_SELff030000,RPC_SLP_PROTECTfff0fff0 remain unchanged. These raw
words are not yet a power-tree/clock-lock diagnosis;MCU enabled does not
prove firmware PC. No fault does not exclude blocked memory transactions.
Offline field decode byte-compared gpufreq_mt6983.c/.h to pinned original
xiaomi-rubens270b84910b941bf75490fccdb5fb2b3021dd7cbf. CLK_CFG30 bits16/17
both select MAIN;this does not prove frequency/lock/downstream gates.
GPU_STATUS after has ACTIVE1,PROTM0. Both SPM words maskedffffe aree.
Reference PDCv2 is enabled,manual MFG2..18 power-on is conditional on its
being disabled,and fake SPM PWR_CON APIs exist. Therefore missing shader
domain bits alone do not diagnose a missing rail. PDC CG/ST and EMI state
were not sampled. Further platform interpretation is in ignored
platform-field-analysis.json;no extra device register access was made.

Ignored evidence:shim2331-platform-trials/gpu-normal/{journal.json,
gpu-result.json,comparison-2330-2331.json,platform-field-analysis.json,
independent-post-restore.txt,
before/after-marks.bin,before/after-tail.bin,after-console.txt,recovery-dmesg.txt}
and gpu-normal-run.txt. Dmesg891592B. Implementation8ea682a/build handoff
5862456 remain applicable. NEXT: offline compare pinned vendor/binary PDC
CG/ST and EMI/memory-path initialization against the shim to choose a
discriminating next check. Do not blindly repeat2331 or directly write
rails/clocks;another concrete image/write needs specific confirmation.
Preserve unrelated dirt/untracked0093 and keep device data out of git.

## >>> HISTORICAL 2026-10-31: CSF2331 SINGLE TRIAL AUTHORIZED <<<

User specifically replied 可以 to ONE normal2331 imagee1920561 boot_a
trial,fresh evidence and complete64MiB original restoration with independent
SHA256 verification. Fresh root/matisse/_a/Recovery preflight PASS; full
boot_a SHA2562931647a56039722ea2585990b8ef3b1a2daf4c9b990231879f753049eaf86b1.
Candidate,backup,stock-prefix and runner815b1c07 pins match. No prior2331
journal or active runner. Authorization covers this one trial and its
restoration only. Once started, follow shim2331-platform-trials/gpu-normal/
journal.json and prioritize full original restoration and independent hash
before interpreting GPU evidence. Do not launch a second trial.

## >>> HISTORICAL 2026-10-31: CSF2331 PLATFORM SNAPSHOT BUILT AND VERIFIED <<<

Implementation committed8ea682a (bounded platform snapshots,440B evidence,
error provenance,original vendor_boot DT inventory,pinned pairing controls
and regression tests/docs). Resumed from the previous agent's completed
build artifacts; did not rebuild
or repeat the completed suite. Re-read the pasted Panthor guidance and
reviewed the actual independent shim/MMIO code. The requested Linux DT/DMA
changes are not directly applicable here. No new device write/reboot/trial.

Existing platform2331-tests-final.txt records71 tests PASS in8.446s, including
ASan/UBSan C boot/state/cleanup, complete440B ABI publication/decoding,
normal contextual patch application, vendor write isolation and v3/v4 DT
parsing. The snapshot on/off traces have exactly identical MMIO writes.
Three freestanding ARM64 objects and no-ABS64 checks PASS. Existing local
CLT full kernel build completed successfully:16724248B SHA256
75c4fa7171ab9f26cedabf992f4c8e63431f5742c819fb7e1b1c505bb05c6dcc.
128-patch contextual sweet_ufs replay matches source SHA256
6ab87350d5d41ec374052102167116703c974e816c03125644fdfca509c965bb,
including inherited untracked0093 SHA25654f0aaa5a0390bc0678eca60e55bc192d3ebea315daab808a3c456a1ce65365b.
No new CI run or push; gh lists prior action_required runs only.

Build-only candidate:research/matisse/20261031-gpu/shim2331-platform-ready/
matisse-shim-gpu2331.img,26714112B SHA256
e1920561234a68e4472b91ffa2e724385940c6f7c441fc237b80b1a3b4746ad2.
Independent verifier rerun PASS:expanded80402548B, stock Linux at+32MiB,
intact ramdisk/signature bytes, source/frozen pins,440B/55 qwords320..374,
rootrw0/ufsrw0/PIC. Signature retained, NOT authenticated; automatic Recovery
is NOT verified. Firmware and memory objects byte-equal2330,arena PA40076000
unchanged. Read-only snapshots do not trace MCU instruction execution or
measure PLL frequency/lock. No firmware-ready or acceleration claim.

Fresh independent read-only runner preflight PASS again:root Recovery,
matisse/_a,boot_a67108864B,full original SHA256
2931647a56039722ea2585990b8ef3b1a2daf4c9b990231879f753049eaf86b1.
Runner shim2331-platform-trials-run-once.py SHA256
815b1c075bafb0f1dfd292ceb500a5de02eda210df0b6c2b18fdcb54c4d627c3.
Plan remains prepared-unapproved,authorization=null,trial_count_executed0,
restore_pending=false; no journal or active runner. Predicted candidate
full boot_a SHA256efa6122218e60edd6b515281be3a2b8319ab3910b329a99c3cabee2b5ec799ff.
Re-decoded actual2326..2330 captures: only error_name,error_domain and
error_source change; all hardware fields and readiness outcomes unchanged.
Runner/image/backup pins and unconsumed plan/no journal rechecked PASS.
NEXT: request specific confirmation for ONE normal2331 imagee1920561 trial,
fresh evidence, complete64MiB original restoration and independent hash.
Do not start the runner's write branch without that confirmation. Preserve
unrelated shim/ramcollector/sweet-marks changes,untracked0093 and device data.
No2331 device write/boot result exists yet. The project AGENTS.md requires
confirmation for each destructive step; earlier2330 authorization was
consumed and cannot be reused for this distinct image.

## >>> HISTORICAL 2026-10-31: POST2330 PLATFORM AUDIT; SNAPSHOT IMPLEMENTATION <<<

Latest user guidance redirects to original DT, GPUEB, clocks and power before
more descriptor changes. Confirmed project-local SWEET_CSF_BOOT_TIMEOUT=-53;
it is not Linux errno.2330 INIT0/ON1/OFF0,initial reset100 and matching CSF
stage4/error-53 trace top-level stage8 to powered_probe. Decoder now reports
error_domain/source and preserves colliding negative GPUEB reply values.
2326..2330 re-decode changes only error_name plus two provenance fields.

Package vendor_boot v4 DT table at44339200 contains one FDT at+64,335048B
SHA256783b7fb871087991e97d0d944932981d7b11e207deef2f74d67e8a20cc12ffae,byte-equal
device LK DTB. GPU/GPUEB/gpufreq/wrapper properties equal Recovery live6.
GPU compatible mediatek,mali + arm,mali-valhall;IRQ names GPU/MMU/JOB/EVENT/
PWR. No GPU iommus,dma-coherent,clocks,power-domains or assigned-clock-parents.
FHCTL gpu0/2/3 uses fhctl-gpueb. Channel1 TX10/RXbc,8 send/recv pins,276/640
bytes validate. Missing runtime memory in Recovery/static DT is mode2,not
normal-boot failure. Inventory now inspects bounded v3/v4 vendor_boot DTBs.

Deferred SH2331 draft saved ignored firmware-static/deferred2331-pre-platform-
audit.patch;memory.c/.h and fetch-audit.py restored exactly2330. No SH change.
12-case vendor controls retained;full pinned audit passes293 pages/647 helper
calls,unchanged arena hash.51 targeted plus6 inventory tests PASS before
snapshot edits. Fresh read-only root/matisse/_a/Recovery boot_a67108864B hash
2931647a...86b1 PASS. No device writes/reboot;prior trial approval consumed.

New pasted guidance applied to this independent shim,not Linux:opt-in read-only
platform/fault snapshots before/after AUTO,keeping2330 writes/mapping policy.
2331 now means snapshot diagnostic,NOT deferred SH candidate. Report extends
304->440B/55 qwords;tests/build in progress. Do not install example IRQs,
mutate DT,mask SHADER_PRESENT or write rails/clocks. Version0/no IRQ proves
no readiness,not no execution. GPU_STATUS bits0/1 are activity;L2_READY is
160,not140. Shader mask770017 has10 bits;arena40076000..401a2000 below4GiB.
NEXT: finish regression tests,freestanding compile,contextual kernel build,
build-only candidate and independent verification;update docs and commit.
No new device flash/trial authorized. Preserve unrelated dirt/untracked0093.

## >>> HISTORICAL 2026-10-31: CSF2330 CACHED-BYTE TRIAL; MCU TIMEOUT; FULL RESTORE <<<

User specifically approved ONE normal2330 image2acb4014 boot_a trial,fresh
evidence and complete original restoration. Executed exactly once; runner
session69961 exited0. Candidate26714112B SHA256
2acb401446915ff72a7b3d8ee5c9d9dcd89cd04b89062ab388a9ea275519a06f.
Full temporary boot_a readback matched predicted
42768433ce974e59d1b0c55c1d191a36e283fd2b76dcf594026ed29c35b970cf.
Normal boot reached Fastboot after84.57s. One persistent raw USB session
returned OKAY for stock-prefix download013e8000,flash:boot_a and
reboot-recovery. Recovery then restored all67108864B original boot_a.
Independent subsequent root/matisse/_a/recovery/geometry and full SHA256 PASS:
2931647a56039722ea2585990b8ef3b1a2daf4c9b990231879f753049eaf86b1.
Journal complete-restored-Recovery,restore_pending=false,evidence_decoded=true;
plan records one consumed authorization and independently verified full
restoration. No active runner/pending restore or user USB/key intervention.
Fresh Recovery dmesg818553B. No new build,CI run,push or repeated test suite.

Fresh marks build2330/count99 contain38 complete CSF qwords320..357 and
match the captured4198400B tail. Before marks/tail exactly match2329's
previous after capture; stale2329 rejects expected2330. The18657B console
independently names gpu2330/sweettrial=2330. MEMATTR low4c4c884c/high4c4c4c4c
readback matches the intended cached-byte change. TRANSCFG42000006 and
coherency31/request/readback/after remain correct; group6/293 are software
metadata only. IRQ gate/L2_READY1 persist. MCU remains stage4/error-53,
status1,JOB_RAW0,MMU_RAW0,version0 and AS status/fault0; no firmware-ready.

Exact common-field comparison against2329 finds these endpoint differences:
MEMATTR low4c4c9f4c->4c4c884c; shared_alloc_after1d->0,so shared word04000018
now stays0->0; tiler_ready_lo1->0; gpu_raw600->200 and reset_raw600->200.
The derived shared startup_memory_changed flag becomes false. Every other
common CSF field and every common GPU field is identical. Private early/
feature/late words remain0. Disable still times out-53,status1; reset does
not complete and cleanup_error-53. Added vendor_cached_byte_readback_matches
is true,not a readiness substitute. This one run does not establish that
the byte change caused the endpoint differences or identify the MCU PC.
84.57s versus2329's99.87s is a single-run timing observation only.

Ignored evidence: shim2330-trials/gpu-normal/{journal.json,gpu-result.json,
comparison-2329-2330.json,independent-post-restore.txt,before/after-marks.bin,
before/after-tail.bin,after-console.txt,recovery-dmesg.txt} and
shim2330-trials/gpu-normal-run.txt. Freshness/report completeness/common-field
comparison and independent full restoration checks PASS. Implementation
ad073cf/build handofff95d603 and63-test/build checks remain applicable.
NEXT: offline investigate the vendor cache-byte/shareability pairing and
per-section descriptor/table contract using paired2329/2330 evidence. Do
not adopt88 as a confirmed fix or blindly repeat2330. This one-trial
approval is consumed; another concrete image/write needs confirmation.
Preserve unrelated dirt and inherited untracked0093. No GPU success claim.

## >>> HISTORICAL 2026-10-31: CSF2330 SINGLE TRIAL AUTHORIZED <<<

User specifically replied 可以 to ONE normal2330 image2acb4014 boot_a trial,
fresh evidence collection and complete64MiB original restoration with an
independent hash. Fresh read-only Recovery preflight PASS; exact runner
d4905881 and image/backup/stock-prefix pins match the prepared plan.
This authorization covers this one trial and restoration only. Once started,
follow shim2330-trials/gpu-normal/journal.json and prioritize full restore
plus independent hash2931647a before interpreting GPU evidence.

## >>> HISTORICAL 2026-10-31: CSF2330 CACHED-BYTE BUILT AND VERIFIED <<<

User replied 可以 to OFFLINE continuation after restored2329. No new device
write/reboot approved or performed. Implementation committed ad073cf.
New actual-C leaf/index audit checks all293 firmware pages:145 cached use
probe index1/byte9f versus vendor index0/byte88;148 shared use probe
index0/byte4c versus vendor index5/byte4c. Copying the entire vendor MEMATTR
without changing PTE indices would select8f for cached and88 for shared.
Do not do that. The selected opt-in2330 diagnostic changes only byte1
9f->88 in our MEMATTR: low4c4c9f4c->4c4c884c,XOR1700; high stays4c4c4c4c.
All293 selected raw bytes then match the vendor per-section bytes. This is
not an effective-cache model or a diagnosed cause of the real MCU timeout.

vendor_cached_memattr accepts0/1;0 preserves2329 and2 rejects before IO.
Shim opts1. Wrong low/high MEMATTR readback rejects before MCU. Actual C
ASan/UBSan trace differs from2329 in exactly ONE write, with all other
writes/order/cleanup identical under the same synthetic prerequisites.
No PTE/SH/nG/PXN/table/firmware/MGM group6/coherency31/INA0/IRQ/MCU sequence
change. Group6 arena SHA256 remains
e6cba8456388fe7fc2ba49aee64814478ebdc3491ba5480290b01f9ebe1c91dd.
csf_memory.o/csf_firmware.o/csf_blob.o and csf.bin byte-equal2329; arena PA
40076000 unchanged. Report remains304B/38 qwords320..357. Decoder requires
2330 MEMATTR and all prior fresh IRQ/version/interface/cleanup gates; an
attribute match alone never proves firmware-ready. Contextual patch0128
only bumps build2329->2330. Remaining SH/nG/PXN/table differences persist.
Pinned entry_set_pte47250..472c8 forces403 and separately updates packed
counter nibbles in the first3 table words; no table change selected or
hardware meaning inferred. Detailed disassembly stays ignored.

63 targeted tests PASS4.011s,including exact C write isolation,ASan/UBSan,
invalid config/low+high readback negatives,ABI and contextual patches.
Actual2326/2327/2328/2329 captures decode byte-equal their saved JSON.
Three changed files freestanding ARM64/no ABS64 PASS. Full local CLT kernel
build exit0,16724248B SHA256
7b5519f0c5ef4e7c5474dd2cc92921469306c9b189f3ef5b1db17f0e5054b40a.
The Xcode-only wrapper rejected missing Xcode before compilation; retried
successfully with existing tools/build-xnu-clt.sh. No CI/push.
Build-only candidate26714112B SHA256
2acb401446915ff72a7b3d8ee5c9d9dcd89cd04b89062ab388a9ea275519a06f,
research/matisse/20261031-gpu/shim2330-ready/matisse-shim-gpu2330.img.
Independent expanded80402548B/intact stock Linux+32MiB/ramdisk/signature
bytes/source+frozen pins/304B ABI/rootrw0/ufsrw0/PIC PASS. Signature bytes
retained,NOT authenticated; automatic Recovery remains unverified.
127-patch contextual kernel replay matches source SHA256
cbe6a5dad1bcf5f1f57d5123ca4eace14bac41578d8316961c5e2bd92c3dbccc,
including preserved untracked0093 hash54f0aaa5a0390bc0678eca60e55bc192d3ebea315daab808a3c456a1ce65365b.

Fresh read-only preflight PASS: root matisse/_a/Recovery,boot_a67108864B,
full original SHA2562931647a56039722ea2585990b8ef3b1a2daf4c9b990231879f753049eaf86b1.
Separate shim2330-trials-run-once.py SHA256
d49058813b781860acc928db62d51702df2fbf070db59a122b4a22521eb58ade;
ONLY read-only preflight executed. Plan prepared-unapproved,authorization
null,trial_count_executed0,restore_pending=false,no journal/active runner.
Predicted candidate full boot_a SHA256
42768433ce974e59d1b0c55c1d191a36e283fd2b76dcf594026ed29c35b970cf.
Original backup/prefix pins unchanged. Ignored evidence: firmware-static/
{post2329-memattr-index-audit,post2329-table-helper,memattr2330-isolation,
vendor-register2330-audit,kernel2330-source-replay}.json;shim2330-ready/
{manifest,independent-verification}.json and build/test/preflight logs.
NEXT: request specific confirmation for ONE normal2330 image2acb4014 boot_a
trial,full candidate readback/fresh2330 evidence and complete original64MiB
restoration/independent hash2931647a. Do not run its write branch yet.
Preserve unrelated dirt and inherited untracked0093. No GPU success claim.

## >>> COMPLETE 2026-10-31: CSF2329 INA TRIAL; MCU TIMEOUT; FULL RESTORE <<<

User specifically approved ONE normal2329 image83c635bb boot_a trial, fresh
evidence collection and complete original restoration. Executed exactly once;
runner session77144 exited0. Candidate26714112B SHA256
83c635bbd15a08bb3333105bc949fd2c9fa21caaad05920844d751875601fe25.
Full temporary boot_a readback matched predicted
b9626544096d47c370d2bfc3653966e51e237483ee6913127725433041a00fe1.
Normal boot reached Fastboot after99.87s. One persistent raw USB session
returned OKAY for stock-prefix download013e8000,flash:boot_a and
reboot-recovery. Recovery then restored all67108864B original boot_a.
Separate post-restore matisse/_a/root/recovery/geometry and SHA256 PASS:
2931647a56039722ea2585990b8ef3b1a2daf4c9b990231879f753049eaf86b1.
Journal complete-restored-Recovery,restore_pending=false,evidence_decoded=true;
plan records one consumed authorization and independent full restoration.
No active runner or pending restore; no user USB/key intervention requested.
Fresh Recovery dmesg841950B. No new build,CI run or push in this trial.

Fresh marks build2329/count99 contain38 complete CSF qwords320..357 and
match the captured4198400B tail. Before marks/tail exactly match2328's
previous after capture; stale2328 rejects expected2329. The18657B console
independently names gpu2329/sweettrial=2329. Every common decoded CSF
field matches2328 except hardware TRANSCFG420001c6->42000006; the new
vendor_ina_readback_matches is true. Every common GPU field matches2328.
Coherency31/readback31/after31,group6/293 software leaves,IRQ gate and
L2_READY1 persist. MCU remains stage4/error-53,status1,JOB_RAW0,MMU_RAW0,
version0,AS status/fault0. Private marker words stay0; shared04000018
changes0->1d. Disable error-53,reset_raw600/reset_completed0,cleanup-53.
Firmware-ready remains false. INA matching the vendor alone did not establish
the handshake in this configuration; it does not identify the timeout cause.
99.87s versus2328's83.54s is a single-run observation, not attributed to INA.

Ignored evidence: shim2329-trials/gpu-normal/{journal.json,gpu-result.json,
comparison-2328-2329.json,independent-post-restore.txt,before/after-marks.bin,
before/after-tail.bin,after-console.txt,recovery-dmesg.txt} and
shim2329-trials/gpu-normal-run.txt. Freshness/report completeness/exact common
field comparison and independent full restore checks PASS. Source b6bb9e1
and build handoff50f3bf3 remain applicable; no rebuild/tests repeated.
NEXT: offline pinned vendor MEMATTR/cache/descriptor/table differences and
MCU startup comparison. Do not repeat2329 blindly. This trial approval is
consumed; another concrete image/write needs specific confirmation.
Preserve unrelated dirt and inherited untracked0093.

## >>> HISTORICAL 2026-10-31: CSF2329 SINGLE TRIAL AUTHORIZED <<<

User specifically replied 可以 to ONE normal2329 trial of image83c635bb,
fresh evidence collection and complete64MiB original boot_a restoration
with independent hash. Fresh read-only Recovery preflight PASS; exact
runner284b2227 and image/backup pins match the prepared restoration plan.
This authorization covers this one trial and restoration only. Once started,
follow shim2329-trials/gpu-normal/journal.json and prioritize full restore
plus independent hash2931647a before interpreting GPU evidence.

## >>> HISTORICAL 2026-10-31: CSF2329 INA-ONLY BUILT AND VERIFIED <<<

Offline continuation authorized after restored2328; no new image/write approved.
Audit commit3f33f13; INA diagnostic implementation commitb6bb9e1.
2329 changes only the opt-in AS_TRANSCFG INA field relative to2328:
420001c6->42000006 (XOR1c0), matching executed pinned vendor protocol31
MMIO slice45e80..45fd4. Actual C ASan/UBSan trace differs in exactly ONE
write; all other writes/order/cleanup identical under the same synthetic
prerequisites. Default0 preserves2328; invalid option2 rejects before IO;
wrong readback stops before MCU. Group6 arena SHA256 unchanged
e6cba8456388fe7fc2ba49aee64814478ebdc3491ba5480290b01f9ebe1c91dd.
Firmware, descriptor tables/leaves, MEMATTR/cache, coherency31, IRQ masks,
MCU AUTO/disable/reset and report304B/38 qwords320..357 are unchanged.
csf_memory.o/csf_firmware.o/csf_blob.o and embedded blob byte-equal2328.
No timeout diagnosis, firmware-ready or GPU acceleration claim.

59 targeted tests PASS3.730s, including old ABI/new INA negatives, sanitizer
state machine, exact-write isolation and contextual patch sequence. Actual
2326/2327/2328 hardware captures decode byte-for-byte equivalent JSON.
Three changed source files freestanding ARM64/no ABS64 relocation PASS.
Local full kernel build exit0,16724248B SHA256
9ea37e6018022e8a87eb6ed622d19cd18849fc58e33144dc74cf57acda371877.
Build-only candidate26714112B SHA256
83c635bbd15a08bb3333105bc949fd2c9fa21caaad05920844d751875601fe25,
research/matisse/20261031-gpu/shim2329-ready/matisse-shim-gpu2329.img.
Independent components/pins/frozen objects/expanded80402548B/intact stock
Linux+32MiB/ramdisk/signature bytes/304B ABI/rootrw0/ufsrw0/PIC PASS.
Signature bytes retained, NOT authenticated; automatic Recovery unverified.
Contextual kernel source replay matches built tree, requiring inherited
untracked0093 hash54f0aaa5a0390bc0678eca60e55bc192d3ebea315daab808a3c456a1ce65365b.
No CI/push/device write/reboot in this milestone. Preserve unrelated dirt.

Fresh read-only preflight PASS: matisse/_a/root Recovery,boot_a67108864B,
full original SHA2562931647a56039722ea2585990b8ef3b1a2daf4c9b990231879f753049eaf86b1.
Separate shim2329-trials-run-once.py SHA256
284b22279b00352be32bf902fc586005438ee3e00aee33bd596d449451602def;
ONLY read-only preflight ran. restoration-plan.json prepared-unapproved,
authorization=null,trial_count_executed=0,restore_pending=false,no journal.
Predicted candidate full boot_a SHA256
b9626544096d47c370d2bfc3653966e51e237483ee6913127725433041a00fe1.
Full backup/prefix pins unchanged. Evidence ignored: firmware-static/
{ina2329-isolation,kernel2329-source-replay,vendor-register2329-audit}.json,
shim2329-ready/{manifest,independent-verification}.json and build/test logs.
NEXT: ask specific approval for ONE normal2329 image83c635bb boot_a trial,
full candidate readback, fresh2329 capture, then complete original64MiB
restore/independent hash2931647a. Do not execute runner write branch yet.

## >>> COMPLETE 2026-10-31: POST2328 OFFLINE REGISTER AND INPUT AUDIT <<<

User replied 可以 to offline continuation after restored2328. No new device
write/reboot is authorized. Audit implementation committed3f33f13;57 targeted
tests PASS3.476s. Pinned relocation-free vendor instruction slices now execute
AS TRANSCFG/root/MEMATTR writes, UPDATE and initial/reload MCU AUTO. Actual
C probe MMIO writes captured under ASan/UBSan. Coherency31 yields vendor
TRANSCFG42000006 (probe420001c6);0/1 controls yield62000006. AS7 stride/high
root controls PASS. MCU AUTO is2 in both initial/reload paths, matching probe.
All293 vendor leaf descriptors executed/compared against actual group6 arena.
Remaining low cache/SH/nG/PXN/table differences persist; none is diagnosed.

Old replay MMIO40000010=a8620004 and40030004=2000000a were synthetic
assumptions, NOT measured MCU/host aliases. New explicit inputs expose this.
Pinned01002f96..01002fd6 computes shared+18 as3+bits11:8(word10)+bit_length
of shader mask. Synthetic word10=300,shader770017 reproduces1d; it does not
identify real writer/PC. Low word30004 can leave private early marker0 while
reaching synthetic WFI/version01010000. Real private-late0/version0 remains
unexplained. Evidence ignored under firmware-static/post2328-{vendor-register-
audit,input-sensitivity,replay-hypothetical-inputs}.json.
The explicit opt-in INA-only2329 candidate is now built/checked above.
No candidate device write is authorized by the offline continuation.

## >>> COMPLETE 2026-10-31: CSF2328 GROUP6 TRIAL; MCU TIMEOUT; FULL RESTORE <<<

User explicitly replied 可以 to ONE normal2328 trial of imagea880c846 and
full original boot_a restoration. Executed exactly once; runner session89703
exited0. Candidate26714112B SHA256
a880c8465cbc02deaa287a4925e54a911722e938fde1685fecf0410d733959a6.
Full temporary boot_a readback matched predicted
1987a83a69676c290dca9a80c8aa95aa4502dd39982df192df6d8cd3e9cf3176.
Normal boot reached Fastboot after83.54s. One persistent raw USB session
returned OKAY for stock-prefix download013e8000,flash:boot_a and
reboot-recovery. Recovery then restored all67108864B original boot_a.
Separate post-restore root/matisse/_a/recovery/geometry and SHA256 PASS:
2931647a56039722ea2585990b8ef3b1a2daf4c9b990231879f753049eaf86b1.
Journal complete-restored-Recovery,restore_pending=false,evidence_decoded=true.
No active runner or pending restore. No user USB/key intervention.
Fresh Recovery dmesg890576B. No new build/CI/push in this trial.

Fresh marks build2328/count99 contain38 complete CSF qwords320..357,
matching the captured4198400B tail. Before marks build2327/count98 exactly
match the previous trial; old marks reject expected2328. The18657B console
independently names gpu2328/sweettrial=2328. New software metadata reports
group6/293 leaves; this is NOT hardware translation/routing readback.
Every common decoded GPU/CSF field is identical to2327: platform INIT0/ON1/
OFF0,SPM3->7,GPU_IDa8620004,initial reset100,AS_PRESENTff; coherency request/
immediate readback/after31,diag_flags127,IRQ mask gate PASS. MCU remains
stage4/error-53,MCU_STATUS1,JOB_RAW0,MMU_RAW0,version0,AS fault/status0.
L2_READY1,TRANSCFG420001c6,rootPA40076000,MEMATTR4c4c9f4c/4c4c4c4c.
Private marker words stay0; shared04000018 changes0->1d. Disable timeout-53,
reset_raw600/reset_completed0,cleanup_error-53. Firmware-ready remains false.

Group6 leaf tagging alone did not establish the handshake in this trial.
This does not prove hardware consumed the tag or identify the timeout cause.
Return83.54s versus2327's180.34s is an observation, not attributable to the
tag from single runs. No firmware-ready or GPU acceleration claim.
Ignored evidence: shim2328-trials/gpu-normal/{journal.json,gpu-result.json,
comparison-2327-2328.json,independent-post-restore.txt,before/after-marks.bin,
before/after-tail.bin,after-console.txt,recovery-dmesg.txt} and
shim2328-trials/gpu-normal-run.txt. Restoration plan records one consumed
authorization and independently verified full restoration.
Implementation5ba6301/build handoff4b4c524;48-test/build results unchanged.
Freshness/report completeness/previous-trial alignment/comparison checks PASS.
NEXT: continue offline pinned vendor cache/AS/PTE and MCU startup comparison,
selecting any next diagnostic from evidence. Do not repeat2328 blindly.
This approval is consumed; another concrete image/write needs confirmation.
Preserve unrelated dirt and inherited untracked0093.

## >>> HISTORICAL 2026-10-31: CSF2328 BUILD AND SINGLE-TRIAL AUTHORIZATION <<<

User specifically replied 可以 to ONE normal2328 imagea880c846 boot_a
trial, fresh evidence collection and full64MiB original restoration.
Read-only preflight repeated PASS; runner hashbf0cf466 and prefixfe6e8fbf
match the prepared restoration plan. This authorization covers this one
trial and its restoration only. Follow shim2328-trials/gpu-normal/journal.json
once started; prioritize full restore and independent hash before analysis.

User replied 可以 to offline continuation after restored2327 (cf5024d).
New pinned vendor-helper audit found omitted MGM transformation: actual
mali_mgm SHA25622113cb61a7b1fab5e552ff028a7e45c8ef40cfe57b2bdd67ea835b017d0f2f9,
helper97c..9dc selects default6 when override+210 is0 and ORs bits59..62.
Recovery DT GPU links phandle59 to /mgm. Requested group argument does not
select this helper's result. Synthetic override3 gives3; no Android runtime
override or physical routing was measured. This is not a timeout diagnosis.

New tools/matisse-csf-vendor-mmu-audit.py pins KMD/MGM/blob and executes
bounded relocation-free AArch64 flag/ATE/PTE/AS/MGM helpers in Unicorn.
Compares actual independent arena:293 ordinary leaves. Existing vendor
cache/SH/nG/PXN/table/TRANSCFG differences remain separate hypotheses.
2328 isolates group6 leaves only; group0 API preserves2327 bytes. Exact
full-arena comparison changes293 bytes only (one high byte per leaf),
leaving PA, tables, low attributes, firmware/data, AS and startup unchanged.
Coherency31 remains requested/read back. Report304B/38 marks320..357 adds
software requested group/page count, NOT hardware translation readback.
Fresh IRQ/version/interface/disable/reset still required for readiness.

48 targeted tests PASS3.219s (ASan/UBSan plus ELF/hash/relocation negatives,
ABI/decode and contextual patches). Separate real-fw group0/6/15 sanitizer
checks PASS. Group0/6 synthetic startup identical986 steps/WFI/version01010000,
no modeled fault; high-bit routing/cache/physical execution are NOT modeled.
Local full kernel build exit0;16724248B SHA256
e0d046e63aa909626dfa771fa3ebaf377e11c3530437936cd5faf8653c1aaf4f.
Build-only image26714112B SHA256
a880c8465cbc02deaa287a4925e54a911722e938fde1685fecf0410d733959a6,
research/matisse/20261031-gpu/shim2328-ready/matisse-shim-gpu2328.img.
Independent pins/component/expanded80402548B/fallback+32MiB/304B ABI/rootrw0/
ufsrw0/PIC checks PASS. Signature bytes retained, not authenticated;
automatic Recovery unverified. Kernel replay matches with inherited untracked
0093 hash54f0aaa5a0390bc0678eca60e55bc192d3ebea315daab808a3c456a1ce65365b.
No new CI/push/device write/reboot. Preserve unrelated dirt and0093.
Implementation committed as5ba6301 (17 files). Staged source whitespace
checks PASS excluding0126's intentional unified-diff context whitespace;
contextual patch replay already PASS. No rebuild or hardware trial repeated.

Fresh root Recovery matisse/_a/uid0/67108864B boot_a SHA256 verified:
2931647a56039722ea2585990b8ef3b1a2daf4c9b990231879f753049eaf86b1.
Separate pinned shim2328-trials-run-once.py/restoration-plan.json prepared;
ONLY read-only preflight ran/PASS. No active journal,restore_pending=false.
Ignored firmware-static/{vendor-mmu2328-audit,group6-isolation2328,
fetch-audit-group6-2328,kernel2328-source-replay}.json and build/test logs
record evidence. Full original/prefix pins are unchanged.
The authorized trial and full restoration are now complete as recorded
above. This historical preparation entry does not authorize another write.

## >>> COMPLETE 2026-10-31: CSF2327 PROTOCOL31 VERIFIED; MCU TIMEOUT; FULL RESTORE <<<

User explicitly replied 可以 to ONE normal2327 trial of imagea6247426
and full original restoration. Executed once; runner session19194 exited0.
Candidate26714112B SHA256
a624742667410660768dd0349a9622b73439dcfd71975edbd1918832defdd30c.
Full temporary boot_a readback matched predicted
3682d6a6727d4d24157de1524e566ec8da76b6513eee4434851a987aec5afe3d.
Fastboot returned after180.34s. One persistent raw USB session
returned OKAY for stock-prefix download013e8000,flash:boot_a and
reboot-recovery. Recovery then restored full67108864B original boot_a.
Independent root/matisse/_a/recovery/geometry and SHA256 PASS:
2931647a56039722ea2585990b8ef3b1a2daf4c9b990231879f753049eaf86b1.
Journal complete-restored-Recovery,restore_pending=false,evidence_decoded=true.
No active runner or pending restore. No user USB/key intervention.
Fresh Recovery dmesg869052B. No new build/CI/push this trial.

Fresh marks build2327/count98 contain37 complete CSF qwords320..356;
marks match the captured4198400B tail. Before marks were2326/count97,
and18657B after-console independently names gpu2327/sweettrial2327.
Platform INIT0/ON1/OFF0,SPM3->7,GPU_IDa8620004,initial reset100,AS_PRESENTff.
Coherency features1,before0,requested31,immediate readback31,after31;
diag_flags127 and noncoherent_protocol_verified=true. Thus the intended
protocol write persisted through MCU wait. MCU still stage4/error-53,
MCU_STATUS1,JOB_RAW0,MMU_RAW0,version0,AS fault/status0,no fresh global IRQ.
L2_READY1,TRANSCFG420001c6,rootPA40076000,MEMATTR4c4c9f4c/4c4c4c4c.
IRQ mask gate passed GPU80503,JOBffffffff,MMUff. Endpoint shader
PRESENT770017/transition0/ready0,tilerPRESENT1/transition0/ready1.
CSF/SHADER/TILER/L2_MMU_CONFIG remain0. Private marker words remain0;
shared04000018 remains0->1d. MCU disable still times out-53,status1;
cleanup reset_raw600/reset_completed0,cleanup_error-53.

Compared with2326, all common CSF fields are identical except diag_flags
31->127 and coherency_after0->31. Added request/readback are31. This
establishes protocol NONE alone was insufficient for handshake under this
configuration; it does not identify the timeout cause or firmware PC. The
longer USB return180.34s versus93.73s is an observation, not attributable
to coherency from one run. No firmware-ready or GPU acceleration claim.

Ignored evidence: shim2327-trials/gpu-normal/{journal.json,gpu-result.json,
comparison-2326-2327.json,independent-post-restore.txt,before/after-marks.bin,
before/after-tail.bin,after-console.txt,recovery-dmesg.txt}, plus
shim2327-trials/gpu-normal-run.txt. Restoration plan updated complete.
Implementation5147ace/build handoff9763e7c; previous41 tests PASS remain
unchanged. New evidence decode/freshness/tail alignment checks PASS.
NEXT: continue offline vendor AS/PTE/cache/MCU startup comparison; do not
repeat2327 or change more registers blindly. This single-trial approval is
consumed; any new concrete image/write requires confirmation. Preserve all
unrelated shim/collector/sweet-marks edits and untracked0093.

## >>> HISTORICAL 2026-10-31: CSF2327 BUILD MILESTONE; TRIAL NOW COMPLETE <<<

Fresh read-only Recovery preflight confirms matisse/_a/recovery, uid0,
67108864-byte boot_a SHA2562931647a56039722ea2585990b8ef3b1a2daf4c9b990231879f753049eaf86b1.
Raw evidence: recovery-live-6/raw-state.txt. Official OS2.0.2.0 package is
/Users/xiaohuasheng/Documents/matisse_images_OS2.0.2.0.ULKCNXM_14.0.
No reboot/partition write/CI/push in this milestone; prior2326 approval is
consumed. Current device remains root Recovery, restore_pending=false.

2327 isolates GPU+304 protocol NONE=31, from pinned vendor KMD default
and feature19. The option is explicit0/1 (zero preserves old boot behavior),
sets the protocol before L2/AS/MCU and checks immediate exact readback.
PTE, MEMATTR, TRANSCFG and four quirk registers are unchanged. Report296B
appends requested/readback words; flags32/64 indicate attempt/match;
mark320..356. Failed readback rejects before MCU and still resets.
The decoder requires fresh IRQ/version and successful cleanup, not just
protocol readback.41 targeted tests PASS5.173s, ASan/UBSan included.

Static vendor reconstruction (KMD22b26f30, GPUa8620004/modela0020000):
feature19 present,24 absent; production issue record12 at rodata126e0,
revision4 selects list12e1c={1,15,19,30,31,32}; issue4/21 absent.
corestack_driver_control is BSS0. With observed zero reset configs,
SHADER/TILER/CSF/L2_MMU all derive0. Coherency default31 is the isolated
nonzero difference. See firmware-static/vendor-2327-data-audit.json;
these are static derivations, not proof of timeout cause or runtime state.

Local full kernel build exited0; kernel16724248B SHA256
3817002e5b249c9cd0efeb55ee42a9d42147422e2ce13f562ebc6f368ac655f9.
Build-only image26714112B SHA256
a624742667410660768dd0349a9622b73439dcfd71975edbd1918832defdd30c
at shim2327-ready/matisse-shim-gpu2327.img. Independent verification PASS:
manifest/source/frozen objects, expanded80402548B, intact stock Linux at
+32MiB, ramdisk/signature bytes,296B report/37 marks,rootrw0/ufsrw0.
Signature bytes retained, not authenticated; automatic Recovery unverified.
Kernel replay matches only when the EXISTING untracked0093 console patch
is included; recorded hash54f0aaa5a0390bc0678eca60e55bc192d3ebea315daab808a3c456a1ce65365b.
That inherited patch is preserved/uncommitted, not newly introduced.
Three modified source files freestanding ARM64/PIC relocation checks PASS.
No new CI run, push, reboot or device partition write.
Implementation commit5147ace; completed changes committed. Source whitespace
checks PASS; contextual patch replay PASS (patch context whitespace is
intentional unified-diff syntax).

Prepared shim2327-trials/restoration-plan.json and a separate pinned
shim2327-trials-run-once.py; ONLY its read-only preflight branch ran/PASS.
No active trial journal,restore_pending=false. Full baseline backup and
stock prefix hashes PASS. Predicted candidate full boot_a hash
3682d6a6727d4d24157de1524e566ec8da76b6513eee4434851a987aec5afe3d.
NEXT: ask for one concrete normal2327 trial: write imagea6247426
to boot_a, normal boot, collect fresh2327 evidence, restore full64MiB
baseline2931647a and independently hash. No approval granted for this
image yet; don't execute runner's write branch. Preserve unrelated dirt.

## >>> COMPLETE 2026-10-31: CSF2326 HARDWARE STARTUP EVIDENCE; FULL RESTORE <<<

User approved one normal CSF2326 GPU/MCU trial with complete restoration.
The device started in root Recovery and read-only preflight passed. Candidate
image `matisse-shim-gpu2326.img` SHA256
2b55baf18e88a68f4e642ab35bda1cdb95987452710bc1b56a964aa99d544b87 was
written to boot_a and full-partition readback matched predicted
b585e5f36c09081670118aec1f0468020e3ca5c62b37e62732579b115986ea91.

Normal boot reached Fastboot after93.73s. One persistent fbraw session
flashed the known stock20MiB prefix (download013e8000 and flash OKAY),
requested reboot-recovery OKAY, and Recovery then restored the complete
67108864-byte original boot_a. Final device is root Recovery,
`matisse/_a/recovery`, and independent hash verification passed:
2931647a56039722ea2585990b8ef3b1a2daf4c9b990231879f753049eaf86b1.
Journal `shim2326-trials/gpu-normal/journal.json` is
`complete-restored-Recovery`, `restore_pending=false`; no active runner or
pending restoration remains. Fresh Recovery dmesg is873828B.

Fresh marks use build2326/count97 and decode successfully. Platform remains
INIT0/ON1/OFF0, SPM3->7, GPU_IDa8620004, initial reset100, AS_PRESENTff.
CSF passes the mask gate: GPU mask80503, JOB maskffffffff, MMU maskff,
`irq_gate_passed=1`; L2_READY1, TRANSCFG420001c6, rootPA40076000. MCU still
times out at stage4/error-53 with MCU_STATUS1, JOB_RAW0, MMU_RAW0, AS fault/
status0, version0 and no fresh global interface IRQ. Poststart core state is
shader PRESENT770017/transition0/ready0 and tiler PRESENT1/transition0/
ready1. Cleanup reports disable timeout-53, reset_raw600 and
reset_completed0, so firmware-ready remains false.

New evidence fields are complete (`diag_flags=31`): coherency features1,
COHERENCY_ENABLE before/after0, CSF/SHADER/TILER/L2_MMU_CONFIG all0 before/
after, AS_MEMATTR `0x4c4c9f4c/0x4c4c4c4c`, private probe page400bb000.
Private early/feature/late words remain0->0. Shared VA04000018 changes
0->0x1d. This is the only sampled mutation; the read-only probe cannot
identify the writer or map it to a firmware PC, so it is evidence of startup
activity only, not proof of full firmware execution.

Ignored evidence is under
`research/matisse/20261031-gpu/shim2326-trials/gpu-normal/` including
after marks/console, decoded report, Recovery dmesg and journal. No Android
partitions besides the temporary boot_a write were changed; full restoration
and hash verification passed. No further flash is authorized by this result.

## >>> ACTIVE 2026-10-31: CSF2326 STARTUP EVIDENCE BUILD; NO DEVICE TRIAL <<<

The next diagnostic is built and has not been flashed. Device remains the
last verified root Recovery with original64MiB boot_a hash
2931647a56039722ea2585990b8ef3b1a2daf4c9b990231879f753049eaf86b1;
restore_pending=false. No new partition-write approval was requested or
used. The generated image is for review/testing only.

CSF2326 appends a288-byte report and marks320..355. It snapshots before and
after values for COHERENCY_ENABLE(0x304), CSF_CONFIG(0xf00), SHADER_CONFIG
(0xf04), TILER_CONFIG(0xf08), L2_MMU_CONFIG(0xf0c), programmed AS_MEMATTR
(0x2408/0x240c), and the pinned firmware's early private/shared words. The
private samples are read from the shim arena while the power reference is
held; they do not change GPU behavior and are not readiness proof.

The private probe maps the ordinary section covering MCU VA0x0202c000 and
records words at arena+0x934 (firmware writes at PC01002bce), +0x93c (writes
around01002bea/01002c16), +0x22c (01002f14), plus shared VA0x04000018
(01002fd6). A synthetic run shows all four words change after the modeled
startup path; a stuck TILER transition changes only the first two. This is a
useful endpoint marker, not a physical MCU trace.

Local kernel build exited0; kernel16724248B SHA256
b445ec59b58d7533e94e0b4dc0f3e71507426da78c9e9ec1b2cbe668d588a691.
Build-only image:
`research/matisse/20261031-gpu/shim2326-ready/matisse-shim-gpu2326.img`,
26714112B SHA256
2b55baf18e88a68f4e642ab35bda1cdb95987452710bc1b56a964aa99d544b87.
Report decoder and 40 targeted tests PASS (3.111s); tests cover old report
ABIs, 2326 startup fields, invalid sampling and report-size publication.
No CI run/push/device action. Full 2326 image artifacts remain ignored.

NEXT: review the diagnostic ABI and, only with a separate concrete approval,
perform one 2326 hardware trial using its exact image, then restore/hash the
full original boot_a. Do not infer firmware fetch or timeout cause from this
build-only or synthetic evidence. Preserve unrelated collector/shim dirt.

## >>> ACTIVE 2026-10-31: OFFLINE CSF FETCH AUDIT PASS; HARDWARE STILL BLOCKED <<<

Read this section before the historical2325 trial entries below. Device was
last independently verified root Recovery with complete original64MiB boot_a
hash2931647a; restore_pending=false. No device command, image change, new
kernel build, CI run or push in this offline milestone. Previous2325 flash
approvals are consumed; continuing static work does not authorize another
partition write. GPU power/reset passed in2325; MCU handshake did NOT.

New tools/matisse-csf-fetch-audit.py compiles the ACTUAL portable C parser/
memory builder under ASan/UBSan, walks its four-level48-bit/4KiB page tables
at measured rootPA40076000, and loads Unicorn from those translated arena
bytes. Every startup instruction/data access is checked for AF, AP, RO and
PXN/UXN. CLI pins proprietary blobde22d2fc; unsupported firmware is rejected
because startup PC/MMIO assumptions are blob-specific. No blobs committed.

Synthetic controls: zero-transition reaches01003032 WFI in986 instructions,
shared version01010000, no access violations; transition clearing on fourth
read reaches WFI in1004. Stuck transition hits10000-step cap in TILER loop
01002ee4..01002ef2,version0. Artificial shared-page RO stops instruction640
at PC01002fd6 writing04000018. These show loader bytes/permissions support
THIS synthetic path and that the audit catches a real startup write. They
do NOT emulate GPU MMU/cache/DRAM/clocks, locate the physical MCU PC, prove
hardware fetch or diagnose2325. Real version remains0.

39 targeted tests PASS (3.177s);8 new permission/bounds tests need no blob or
Unicorn. C memory source SHA256b30ea8dc07278f9bc1cfa4d9d37a20bf6659e2cb2385a51ea616227dca5100fc;
parser17520e27cb0a48bf00db23cd26ae7c719c0ef564e82c28fc778ce62eb434991a.
Ignored firmware-static/fetch-audit-{zero,transition-completes,transition-stuck,
readonly-negative}.json and csf-fetch-audit-tests.txt preserve outputs.

Focused vendor comparison: cached sections use vendor index0/attr88/no SH
versus probe index1/attr9f/SH_IS; shared firmware cache-mode3 falls to mode0
under vendor coherency31, using index5/attr4c/no SH versus probe index0/4c/
SH_OS. Vendor entry_set_pte47250 adds403 plus software count bits55..58 to
table entries; probe emits PA|3. These are observations, not demonstrated
defects. Do not copy vendor attributes without testing their effective meaning.

NEXT: design evidence-only sampling of reset/init register values and early
firmware memory writes, retaining current startup behavior. Need hardware
evidence to distinguish no-fetch from early-start stall; endpoint core state
and synthetic replay alone cannot do that. Do not rerun an old trial script.
Prior completed commits: normal2325 result32dbb13, patch regression5bbd6b6,
vendor audit/handoff a665688. Preserve unrelated shim/collector-v2 changes.

## >>> COMPLETE 2026-10-31: CSF2325 MCU TIMEOUT; MASKS OBSERVED; FULL RESTORE <<<

Specifically approved normal2325 trial executed ONCE. Runner87765 exited0.
Fresh build2325/count85 marks (before2324/count77),18657B console confirms
sweettrial2325/gpu2325. Platform INIT0/ON1/OFF0,SPM3->7,GPU_IDa8620004,
initial reset100,reference released. Actual prestart masks GPU80503,
JOBffffffff,MMUff,AS_PRESENTff; irq_gate_passed1. Unlike2324, MCU AUTO was
issued. This run establishes that literal MMUffff readback is inappropriate
on this device;2324 did not record its own GPU/MMU masks, so attribution of
that earlier rejection remains inference, not a measured2324 register value.

CSF stage4/error-53,MCU_STATUS1,JOB_RAW0,MMU_RAW0,AS status/fault/address0,
L2_READY1,TRANSCFG420001c6,rootPA40076000. sample_flags15: pre/post shared
and core sampling executed. Version before/after0,features0,input04002000,
output04003000,groups8,stridea0; input/output/group fields are preloaded
blob metadata, NOT firmware-execution proof. No fresh global IRQ/version.
Poststart SHADER_PRESENT770017,SHADER_TRANSITION0,SHADER_READY0;
TILER_PRESENT1,TILER_TRANSITION0,TILER_READY1; all high words0. Thus the
captured endpoint is not an outstanding shader/tiler transition. It does
NOT prove which instructions ran or exclude an earlier transient/core wait.
GPU_RAW600,disable_status1/disable_error-53,reset_raw600/reset_completed0,
cleanup_error-53. Internal IRQ enable change alone did not achieve handshake.
Firmware-ready/acceleration still unproven; aggregate callback failed.

Fastboot enumerated99.82s after reboot. One persistent fbraw session
verified identity/slot/geometry, stock20MiB prefix download/flash OKAY,
reboot-recovery OKAY. Recovery restored full67108864B original boot_a;
independent matisse/_a/recovery/root,geometry and complete SHA256
2931647a56039722ea2585990b8ef3b1a2daf4c9b990231879f753049eaf86b1 PASS.
Fresh Recovery dmesg874306B. No USB/key intervention,SIGINT or blind retry.
Journal shim2325-trials/gpu-normal/journal.json complete-restored-Recovery,
restore_pending=false,evidence_decoded=true. No active runner/restore duty.
Host-managed restoration, NOT autonomous Recovery from normal XNU.

Posttrial STATIC audit: exact vendor KMD22b26f30/live Recovery DTB4fa4d9fe.
Full /soc/mali node lacks system-coherency and quirks_gpu/sc/tiler/mmu.
Vendor default31 flows to COHERENCY_ENABLE+304 via feature19 (present in
modela0020000 feature list); probe does not record/program its actual value.
Vendor derives/writes CSF_CONFIGf00,SHADER_CONFIGf04,TILER_CONFIGf08,
L2_MMU_CONFIGf0c. Default MMU-quirk path clears0f000000; no model table entry
for this G710. Effective PTE/cache and firmware-fetch audit remains NEXT;
register differences are observations, NOT demonstrated timeout causes.
No speculative hardware changes. Ignored firmware-static/{vendor-init-audit.txt,
post2325-vendor-audit.json}. Corrected firmware effective TILER_PWRON190/194
(R8=40000010), not shader180/184; synthetic replay is not hardware execution.
Fixed0123 patch serialization to carry ordinary context (no zero-context
apply flag required). Both git apply and patch replay PASS and reproduce
exact built2325 source; full tracked evidence-patch sequence PASS,display
trace remains16. Added CI-style patch-sequence regression. Image/kernel
bytes unchanged; no rebuild or additional device action.
31 targeted tests PASS (3.080s), including normal git-apply patch regression;
git diff --check PASS. No second2325 trial,new image/device write authorized.
Implementation3f29061,handoffcb2ad31,fallback98f9438,normal result32dbb13;
patch/tooling regression and documentation correction committed5bbd6b6.
Fresh11-test module PASS (0.826s);31-test suite above remains PASS.
No new build/CI/push this normal trial.
Evidence ignored gpu-normal/{after-marks.bin,after-console.txt,gpu-result.json,
journal.json,independent-post-restore.txt,recovery-dmesg.txt},gpu-normal-run.txt.
Preserve unrelated collector-v2/shim work. Older2325 pretrial text historical.

## >>> COMPLETE 2026-10-31: CSF2325 RECOVERY FALLBACK PASS; FULL RESTORE <<<

User specifically approved image06759c12 Recovery-fallback boot_a write,
reboot Recovery, then full original restoration. Executed ONCE; runner43725
exited0. New Recovery observed26.53s after adb reboot recovery. Candidate
full-partition readback matched predicted SHA256
5193d19a93bfe4065a5833d0f46e72250810335b452075d9bc3d51730739ba3e.
No Fastboot,user USB/key intervention or SIGINT. Fresh Recovery dmesg863855B.
Full67108864B original boot_a restored and independently rehashed
2931647a56039722ea2585990b8ef3b1a2daf4c9b990231879f753049eaf86b1.
Independent matisse/_a/recovery/root and geometry verified. Journal
shim2325-trials/recovery-fallback/journal.json complete-restored-Recovery,
restore_pending=false; no active runner or pending restore.

Before/after4198400B tails and4096B marks are byte-identical, as expected
for Recovery bypass. This verifies2325 Recovery entry/BSS and embedded stock
Linux fallback only; it does not execute normal MCU startup or establish
firmware readiness, acceleration or normal-XNU automatic Recovery.

NEXT: obtain separate specific approval for ONE normal2325 MCU trial with
same image06759c12: Recovery boot_a write -> normal reboot -> fresh2325
marks320..343 and console -> full64MiB baseline restore/hash2931647a.
Fallback approval is consumed; no normal2325 write authorized yet.
Implementation3f29061, handoffcb2ad31. No new build/CI/push or source edit.
Evidence ignored recovery-fallback/{journal.json,independent-post-restore.txt,
recovery-dmesg.txt,before/after-tail.bin,before/after-marks.bin} and sibling
recovery-fallback-run.txt. Unrelated collector-v2/shim dirt preserved.

## >>> ACTIVE 2026-10-31: CSF2325 BUILT; NEW MASK/CORE EVIDENCE; NO TRIAL <<<

Normal2324 trial completed and full boot_a restore independently verified;
see result below. Firmware did NOT start: 2324 rejected before MCU_CONTROL_AUTO.
Its JOB mask readback was ffffffff; GPU/MMU readbacks were not recorded, so
the rejected register is unknown. Do not claim 2324 tested the IRQ hypothesis.

2325 retains requested mask writes GPU80503/JOBffffffff/MMUffff and records
all exact GPU/JOB/MMU readbacks plus AS_PRESENT. Gate now requires JOB global
bit31, GPU fault/protected/reset bits103, and MMU page-fault mask for each
present AS0..15 bit. Reserved/unimplemented bits may read zero. It records
shader+tiler PRESENT/PWRTRANS/READY before MCU start and after startup wait;
the latter snapshot measures endpoint core state but cannot identify the
firmware program counter or prove that instructions executed. Firmware
disassembly at01002ee4 waits for TILER_PRESENT (GPU+110/114) & TILER_PWRTRANS
(GPU+210/214) to clear, then writes TILER_PWRON (MCU40000190/194). R8 is
40000010; [r8,#180/184] is not SHADER_PWRON. Synthetic replay corroborates
the effective addresses, not actual MCU execution.2324 captured neither state.

2325 source, report decoder and strict models implemented.30 targeted tests
PASS (2.478s); actual pinned firmware ASan/UBSan replay PASS:7 ordinary,
3 protected skipped,8 table pages,1232896B arena,606208B shared. Full local
kernel build exit0, no CI/push;16724248B SHA256
da73b367cb071992f592485431bc7ac963c3ce200709eee61236774a70459f39.
Image26714112B SHA256
06759c12f2bfb0bd7a7631909e03adb6e7411668dd4f346338797cd31d7e611f.
Predicted candidate full boot_a SHA256
5193d19a93bfe4065a5833d0f46e72250810335b452075d9bc3d51730739ba3e.
Independent source/frozen-object/image/fallback checks PASS; rootrw=0,
ufsrw=0; retained signature not authenticated. Readonly Recovery preflight
PASS; current full boot_a still baseline2931647a, no write/reboot/new runner
or restore duty.

Ignored runner shim2325-trials/run-once.py pins the image/hash, baseline,
partition prediction and recovery strategy. Next requires specific approval
for ONE2325 Recovery-fallback write/reboot and full64MiB restore/hash. Only
after fallback passes request separate normal MCU trial. No2325 device write
is authorized. Implementation/tests/docs committed3f29061; no CI run.
Evidence csf2325-tests.txt,csf2325-real-fw-test.txt,
kernel-csf2325-build.txt,shim2325-build-arguments.json,
shim2325-ready/independent-verification.json,
shim2325-trials/preflight.txt. Preserve unrelated collector-v2/shim dirt.

## >>> COMPLETE 2026-10-31: CSF2324 PRE-MCU MASK GATE REJECTED; FULL RESTORE <<<

Specifically approved normal2324 trial executed ONCE. Runner21671 exited0.
Fresh build2324/count77 marks and18657B console gpu2324/sweettrial2324.
Platform INIT0/ON1/OFF0,SPM3->7,GPU_IDa8620004,initial reset100 repeated;
reference released. CSF stage3/error-52, sample_flags1,version_before0,
L2_READY1,TRANSCFG420001c6,rootPA40076000,JOB_MASKffffffff. The exact
internal-mask readback gate rejected BEFORE MCU_CONTROL_AUTO, so MCU was
NOT started. JOB mask readback passed; either GPU or MMU mask differed
from the literal requirement (or both). Neither value is recorded in2324;
do NOT assert which failed. Runtime interface was NOT sampled; zero report
fields are unobserved. This trial cannot test the IRQ-enable hypothesis
against2323's firmware timeout. Disable status/error0,reset_raw100,
reset_completed1,cleanup_error0: cleanup verified. Firmware-ready false.

Fastboot enumerated83.56s after normal boot. Runner's one persistent fbraw
session verified matisse/slot/geometry, stock20MiB prefix download/flash
OKAY and reboot-recovery OKAY. Recovery restored full67108864B boot_a;
independent full read/hash2931647a56039722ea2585990b8ef3b1a2daf4c9b990231879f753049eaf86b1,
identity matisse/_a/recovery/root and geometry PASS. No user USB/key action,
SIGINT or blind transport retry. Recovery dmesg891397B. Journal
shim2324-trials/gpu-normal/journal.json complete-restored-Recovery,
restore_pending=false,evidence_decoded=true. No active runner/restore duty.
This is host-managed restoration, not autonomous Recovery from XNU.

Next STATIC audit implemented GPU/MMU mask bits and the overly literal
readback gate; preserve actual masks in a successor report before another
MCU attempt. GPU AS_PRESENTff is measured, but the rejected mask register
is NOT identified yet. No second2324 trial,new image/write approved.
Implementation6d59d9c,patch e6a84ae,fallback3a286d1. No new build/CI/push.
Evidence ignored gpu-normal/{after-marks.bin,after-console.txt,gpu-result.json,
journal.json,independent-post-restore.txt,recovery-dmesg.txt} and sibling
gpu-normal-run.txt. Unrelated collector-v2/shim work preserved.

## >>> COMPLETE 2026-10-31: CSF2324 RECOVERY FALLBACK PASS; FULL RESTORE <<<

User specifically approved imageb8214a7e Recovery-fallback boot_a write,
reboot Recovery, then complete original restoration. Executed ONCE; runner
session83683 exited0. New Recovery observed26.56s after adb reboot recovery.
Candidate full-partition readback matched prediction
8d7de4d7f5cac9a6b73f50df7f3e8da23a9bc163e9a0db34bd25bf5bbbf0b8f1.
No Fastboot, user USB/key intervention or SIGINT. Fresh Recovery dmesg842253B.
Full67108864B original boot_a restored, then independently rehashed
2931647a56039722ea2585990b8ef3b1a2daf4c9b990231879f753049eaf86b1.
Independent matisse/_a/recovery/root and geometry verified. Journal
shim2324-trials/recovery-fallback/journal.json complete-restored-Recovery,
restore_pending=false; no active test/restore runner or restoration pending.

Before/after4198400B diagnostic tails and4096B marks are byte-identical,
as expected for Recovery bypass. Historical2323 console/marks are NOT fresh
2324 GPU evidence. This verifies2324 Recovery entry/BSS and embedded stock
Linux fallback only; it does not execute normal MCU startup or establish
firmware readiness, acceleration or autonomous Recovery from normal XNU.

NEXT: obtain specific approval for ONE normal2324 MCU trial with SAME image
b8214a7e5166f396db9b6e7ac42331c6c592662473347288b32e6ab5679506f1:
Recovery boot_a write -> normal reboot -> capture fresh2324 marks320..335
and console -> full64MiB baseline restore/hash. Same-image fallback PASSED.
Normal XNU automatic Recovery remains UNRELIABLE; persistent fbraw stock-
prefix restoration stays available if Fastboot appears. Fallback approval
is consumed; no normal2324 trial/write authorized yet. Implementation
6d59d9c, final patch/handoffe6a84ae. No new build,CI run/push or source edit.
Evidence ignored recovery-fallback/{journal.json,independent-post-restore.txt,
recovery-dmesg.txt,before/after-tail.bin,before/after-marks.bin} and sibling
recovery-fallback-run.txt. Unrelated collector-v2/shim dirt preserved.
The older pre-trial2324 section below is historical and superseded here.

## >>> ACTIVE 2026-10-31: CSF2324 BUILT; STATIC STARTUP AUDIT; NO DEVICE TRIAL <<<

Latest hardware evidence remains the restored2323 timeout below.2324 has
NOT been written or booted. No restoration is pending. No new hardware trial
is authorized at this handoff; the earlier2323 approvals were consumed.

Pinned CSF reset vector Thumb010018ed (file2780) was decoded in MCLASS mode.
Startup waits at01002ee4..01002ef2 for SHADER_PWRTRANS & SHADER_PRESENT to
clear, publishes version01010000 at01003012 and first global IRQ80000000
at0100301c, then reaches WFI01003032. A synthetic Unicorn Cortex-M7 replay
reaches WFI in986 instructions; injected persistent shader transition stalls
at the wait loop (500000 cap), clearing it after4 reads reaches WFI in1004.
This is simplified fake MMIO, NOT hardware proof or a diagnosis of2323.
Actual2323 shader transition state was not captured. Optional trace pointers
are zero and handled by startup; ignored trace/config entries alone are not
shown to block initial version publication.

2324 changes only internal IRQ setup/reporting: GPU CLEAR/MASK80503,
JOB MASKffffffff,MMU MASKffff immediately before AUTO2, exact readback gate.
Matches measured vendor kbase_pm_enable_interrupts; CPU DAIF/GIC unchanged,
RAW still polled. Report128B offset124 now JOB mask; old2323 reserved-zero
ABI preserved in decoder. Original masks restored during cleanup. This is
an untested hardware hypothesis, not an established fix. No shader queue,
doorbell,Vulkan/Metal or new quirk-register programming.

29 targeted tests PASS (including ASan/UBSan and old/new evidence decoding).
Pinned actual-blob memory replay PASS:7 ordinary/3 protected skipped,
8 tables/1232896B/shared606208B. Local kernel build session29800 exit0;
no CI run/push. Kernel16724248B SHA256
fe02cab05b52f75fa08f93098e2093dd9a1e9f3df16aab9c7091da840daa90cf.
Builder session7673 exit0. Image26710016B:
research/matisse/20261031-gpu/shim2324-ready/matisse-shim-gpu2324.img
SHA256 b8214a7e5166f396db9b6e7ac42331c6c592662473347288b32e6ab5679506f1.
Full candidate boot_a prediction8d7de4d7f5cac9a6b73f50df7f3e8da23a9bc163e9a0db34bd25bf5bbbf0b8f1.
Independent source/image/payload verification PASS. Expanded80402548B,
stock Linux+32MiB,frozen2313 objects,ramdisk/signature bytes unchanged;
rootrw=0/ufsrw=0. Signature retained, not authenticated. All blobs/dumps
remain ignored. Unrelated collector-v2 and dirty shim work preserved.

Source review and git diff --check PASS. Final rerun29 tests PASS (2.563s).
Ignored shim2324-trials/run-once.py prepared from the tested2323 runner,
with exact2324 image and full-partition prediction pinned. Readonly
preflight exited0: Recovery identity/slot/root/geometry matched; full64MiB
live boot_a baseline SHA2562931647a reverified. No write/reboot, active
trial runner or pending restoration. Evidence shim2324-trials/preflight.txt.

Implementation/tests/docs committed6d59d9c. Build-ID patch context was
subsequently corrected and applied to a temporary2323-source fixture,
exactly reproducing the already-built2324 source. Candidate/source hashes
remain unchanged. Specific approval requested for ONE2324 Recovery-fallback
boot_a write/reboot and full64MiB restore/hash2931647a; awaiting reply, NOT
executed. Normal MCU trial needs its own approval after SAME-image fallback
passes. No historical run-ui script,official fastboot,blind USB reopen or
bootloader/recovery edit. The candidate has NOT run on hardware. No CI/push.
Evidence: firmware-static/{startup-detail.txt,replay*.json,replay.py},
csf2324-tests.txt,csf2324-real-fw-test.txt,kernel-csf2324-build.txt,
shim2324-build-arguments.json,shim2324-ready/independent-verification.json.

## >>> COMPLETE 2026-10-31: CSF2323 NORMAL TIMEOUT; FULL RESTORE <<<

Authorized normal2323 trial ran ONCE. Runner32766 exited0; journal
shim2323-trials/gpu-normal/journal.json complete-restored-Recovery,
restore_pending=false. Fastboot enumerated86.57s; host detected it without
opening/retrying commands, then existing one persistent fbraw session
verified identity/slot/geometry, downloaded/flashed stock20MiB prefix OKAY,
reboot-recovery OKAY. Recovery full64MiB boot_a restored/hash independently
2931647a56039722ea2585990b8ef3b1a2daf4c9b990231879f753049eaf86b1.
No user USB/key intervention, no SIGINT, no pending restore or active runner.

Fresh marks build2323,count77 (before2322,count72), console18657B confirms
sweettrial2323/gpu2323. Platform INIT0/ON1/OFF0,SPM3->7,GPU_IDa8620004,
initial reset100,ownership released. initial_power_reset_observed=true;
aggregate failed on callback. CSF stage4/error-53, MCU_STATUS1,JOB_RAW0,
MMU_RAW0,AS fault/status/address0,L2 ready1. Config readback420001c6,
rootPA40076000. sample_flags3: shared interface actually sampled this time.
version_before0/version_after0,features0,input04002000,output04003000,
groups8,stridea0. These metadata match blob; no fresh readiness IRQ or
version publication. This does NOT prove that firmware executed.
GPU_RAW600,disable_status1/disable_error-53; reset_raw600/reset_completed0,
cleanup_error-53. Firmware-ready/acceleration not achieved.

No2323 second trial or new image approved. Continue STATIC audit from these
measurements: table/cache change alone did not produce handshake; examine
MCU boot prerequisites, IRQ delivery/internal GPU event ownership and vendor
G710 initialization. Do not call the VA/cache discrepancy a proven cause.
Evidence ignored gpu-normal/{gpu-result.json,after-marks.bin,after-console.txt,
recovery-dmesg.txt,independent-post-restore.txt}; sibling gpu-normal-run.txt.
Implementation41c0b94, prior fallback12aa100; no new CI/build/source change.

## >>> COMPLETE 2026-10-31: CSF2323 RECOVERY FALLBACK PASS; FULL RESTORE <<<

User specifically confirmed image23b2c8dc Recovery-fallback boot_a write,
reboot Recovery, then original restoration. Executed ONCE; runner85408 exit0.
New Recovery observed26.53s after adb reboot recovery. Candidate full-partition
readbackbf7caf4432b7717002cd7dc9168914662820327b30f499454cdc6acc58c7bac7
matched predicted candidate prefix + unchanged baseline tail. No Fastboot,
user unplug or keys needed. Fresh Recovery dmesg889488B captured.
Full67108864B original boot_a restored, then independently rehashed
2931647a56039722ea2585990b8ef3b1a2daf4c9b990231879f753049eaf86b1.
Independent identity matisse/_a/recovery/root and geometry verified.
No active trial/restore runner or pending restoration.

Authoritative ignored shim2323-trials/recovery-fallback/journal.json:
complete-restored-Recovery,restore_pending=false,new_recovery_observed=true,
return_seconds26.53. Evidence before/after tail4198400B and marks4096B
byte-identical, expected for Recovery bypass. Console history is NOT fresh
2323 MCU evidence. Independent-post-restore.txt and recovery-dmesg.txt saved.
Image shim2323-ready/matisse-shim-gpu2323.img26710016B SHA256
23b2c8dc56f9a7b72a585efa9ebcf889d2979e1dca6fb58fe53dbf81eafb3137.
This verifies2323 Recovery entry/BSS and intact stock Linux fallback ONLY;
not normal GPU/MCU execution, firmware readiness or acceleration.

NEXT: obtain specific approval for ONE normal2323 MCU trial with SAME image,
Recovery boot_a write -> normal reboot -> fresh2323 marks320..335 and console
-> full64MiB baseline restore/hash. Same-image fallback prerequisite PASSED.
Normal XNU automatic Recovery remains UNRELIABLE; persistent fbraw prefix
restore is available if Fastboot appears. No normal2323 write authorized
by the just-completed fallback confirmation. Implementation41c0b94,
build handoff500f36f; no CI/build/source changes this trial. Unrelated dirty
collector-v2/shim work preserved. Older no-write notes are historical.

## >>> ACTIVE 2026-10-31: CSF2323 BUILT; NO DEVICE WRITE <<<

Implementation/tests/docs committed41c0b94 on codex/matisse-xnu-screen-log.
Next-specific approval question covers Recovery fallback only, not normal
MCU execution. No2323 trial has started at this handoff.

2322 normal result committed703f99b; full boot_a restoration remains complete.
Static audit: vendor AUTO2 already correct. Vendor MMU setup6 + WB/RA42000000,
no INA observed; Panthor v6.12 hardwareVA48/WB and cached firmware sections
differ from2322 VA32/all-NC. These are HYPOTHESES, not proved timeout causes.
JOB mask vendorffffffff vs probe0 remains untested.

2323 independent tables4KiB/L0/VA48, TRANSCFG420001c6, full lock47, cached
mode1 WB(index1/9f), others NC(index0/4c); root/config readbacks validated.
Pinned blob sanitizer replay7 ordinary/3 protected/8 tables/1232896B PASS.
Report128B adds explicit sample flags, GPU RAW/AS status/root/config/disable
result and prestart version; timeout now captures shared fields. Disable
failure cannot be hidden by reset success. Fresh IRQ remains necessary.
Kernel patch0121 uses build2323, CSF marks320..335. Decoder preserves2321/
2322 and separates initial observed reset from aggregate callback failure.

32 targeted tests PASS (ASan/UBSan,128B ADT, decoder, FDT/board). Local kernel
session27382 exit0, no CI/push. Kernel16724248B SHA256
77c7248c13d55fe4d2db365bc9cf2d728849e51eb371abfbc5b8c4304a5442f8.
Image shim2323-ready/matisse-shim-gpu2323.img26710016B SHA256
23b2c8dc56f9a7b72a585efa9ebcf889d2979e1dca6fb58fe53dbf81eafb3137.
Freestanding compile/link/component readback and source manifest equality PASS.
Expanded80402548B; Linux+32MiB, ramdisk/signature/frozen2313 objects retained.
Recovery identity matisse/_a/recovery/root read again; no write/reboot.
Readonly runner preflight independently rehashed full64MiB boot_a baseline
2931647a56039722ea2585990b8ef3b1a2daf4c9b990231879f753049eaf86b1.
Ignored shim2323-trials/run-once.py prepared; only preflight executed.
No pending restore or active trial runner.

Next: one specifically confirmed2323 Recovery-fallback boot_a trial, then
full64MiB restore/hash2931647a. Normal probe needs its own confirmation
after same-image fallback. No2323 hardware claim. Unrelated collector-v2
and dirty shim work retained. Static facts detailed in CSF bring-up doc.

## >>> COMPLETE 2026-10-31: CSF2322 MCU START TIMEOUT; FULL RESTORE <<<

Authorized normal2322 trial executed ONCE, runner63108 exited0. Fresh
SWEETMRK build2322,count72 (before2321,count61), report320..330 decoded.
Fresh console sweettrial2322/gpu2322 agrees. L2_PRESENT1,L2_READY1,
MMU_FEATURES2830,MCU_STATUS1(enabled),JOB_RAW0,MMU_RAW0,AS fault/status addr0.
CSF stage4/error-53 timeout; no fresh global readiness IRQ. Firmware fields
were NOT sampled on timeout (zeros are unobserved,not actual shared data).
Cleanup_error-53,reset_raw600,reset_completed0. Do NOT call firmware ready.
Platform INIT0,ON1,SPM3->7,GPU_IDa8620004,initial reset100;OFF0 and acquired0.
Aggregate platform stage8/error-53 reflects callback failure, not failed
initial reset. Per-phase initial power/reset still observed; full combined
transaction failed. Shared7fa30000,extra79a00000. No Vulkan/Metal claim.

Normal boot ended at Fastboot (~126s enumerated18d1:d00d), not automatic
Recovery. Host SIGINT to waiting runner only entered its finally restoration;
KeyboardInterrupt in journal is HOST control, not a device panic. Persistent
fbraw verified product/slot/geometry; stock20MiB prefixfe6e8fbf flash OKAY,
reboot-recovery OKAY03:08:13Z. No user USB/keys action needed. Recovery full
64MiB backup restored/hash2931647a56039722ea2585990b8ef3b1a2daf4c9b990231879f753049eaf86b1.
Independent identity/hash verified. Journal complete-restored-Recovery,
restore_pending=false; no active test/restore runner. No second image test.

Evidence ignored shim2322-trials/gpu-normal/{after-console.txt,after-marks.bin,
gpu-result.json,journal.json,independent-post-restore.txt},gpu-normal-run.txt.
Next STATIC audit actual vendor MCU page-table width, firmware mapping/cache
policy, IRQ enables, model quirks and cleanup. No new flash authorized.
Hypotheses must not be stated as measured causes. Record source/test fixes
and build concrete successor before any next-specific-trial confirmation.

## >>> COMPLETE 2026-10-31: CSF2322 RECOVERY FALLBACK PASS; FULL RESTORE <<<

User specifically confirmed image5ade1013 Recovery-fallback boot_a write,
reboot Recovery, then original restoration. That exact trial is COMPLETE.
Runner session93726 exited0. New Recovery observed26.53s after adb reboot
recovery. Written entire partition readback15f5c01989f8023b0e84219a2dafb036fce26b580fd744e66c4ceac060b189cd
matched candidate prefix + unchanged baseline tail. Fresh Linux dmesg and
Recovery confirmed. Full67108864B boot_a restored/hash2931647a56039722ea2585990b8ef3b1a2daf4c9b990231879f753049eaf86b1.
Independent post-run read verified matisse/_a/recovery/root and same full
hash. No pending restoration or active trial runner. No Fastboot used.

Authoritative ignored journal shim2322-trials/recovery-fallback/journal.json:
status complete-restored-Recovery,restore_pending=false,new_recovery_observed
true,return_seconds26.53. Image26710016B SHA256
5ade1013c6cae1119d04af74db5a446c6e7401e682da6b74010bc4b4ad189e64.
Independent-post-restore.txt and recovery-dmesg.txt saved alongside captures.
Before/after tail and marks are byte-identical, as expected for Recovery
bypass. This tests the2322 entry/stack/BSS and embedded original Linux path;
NOT normal shim GPU/MCU execution, firmware readiness or acceleration.

NEXT concrete action: obtain specific approval for ONE normal2322 CSF trial
using this same image, written from Recovery to boot_a only; reboot normal,
capture fresh2322 marks320..330, then full baseline restore/hash. Same-image
Recovery-fallback prerequisite now PASSED. Automatic return from NORMAL
XNU remains unverified/unreliable; prior2321 required manual Fastboot. Keep
fbraw persistent-session stock-prefix restore available; never official
fastboot or repeated blind USB reopen. No normal2322 write is authorized by
the just-completed fallback confirmation. No CI/build needed this turn.
Implementation c806996, previous handoff3110535; unrelated dirt preserved.
Earlier "not run" notes below are superseded by this completion section.

## >>> ACTIVE 2026-10-31: CSF2322 BUILT/REVIEWED; EXACT TRIAL APPROVAL NEXT <<<

No2322 partition write/reboot has occurred. Recovery online, full64MiB boot_a
independently rehashed2931647a56039722ea2585990b8ef3b1a2daf4c9b990231879f753049eaf86b1.
No active test/restore runner, no restore_pending duty. User asked continue;
AGENTS.md still requires specific confirmation before each destructive step.
Next: confirm2322 Recovery fallback boot_a write, restore full baseline/hash;
only after success confirm/run normal CSF probe. Automatic Recovery remains
UNRELIABLE. No hardware CSF boot claim.

Independent4KiB/32-bit stage1 MCU firmware loader and bounded L2/AS0/MCU
state machine implemented. Own2MiB shim BSS arena, live GPUEB/XNU overlap
checks. Pinned device blob de22d2fc sanitizer replay PASS:7 ordinary sections,
3 protected skipped,7 table pages,1228800B required,shared606208B VA04000000.
Review fixes: explicitly establish unmapped AS0 (reset mode0/1,zero table),
LOCK4GiB then FLUSH_MEM before root UPDATE; MMU high16 REQ_COMPLETE is not
fault; CSG controls start+0x1000. Fresh global JOB raw IRQbit31 + valid global
interface required. MCU disable/reset and GPUEB release; readiness/cleanup
kept separate. No global config/doorbell, shader work, Vulkan or Metal yet.

Local incremental kernel0120 session52988 exited0. Kernel2322 SHA256
f8a78e1868f75103352167290105814444ec685987e3faf248c5dbeec996fa47,
16724248B. No CI/push. Patch0120 adds88B CSF report marks320..330 and
platform300..308,all2322. Decoder --build0x2322 rejects partial/stale/duplicate
records;2321 supported.38 targeted tests PASS, ASan/UBSan plus actual blob.
Initial image link failed because2MiB BSS exceeds ADR reach; start.S now
ADRP+ADD for stack/BSS. Final freestanding link/component readback PASS.

FINAL image (earlier build1/ready/ready2 superseded):
research/matisse/20261031-gpu/shim2322-final/matisse-shim-gpu2322.img
26710016B SHA2565ade1013c6cae1119d04af74db5a446c6e7401e682da6b74010bc4b4ad189e64.
Expanded80402548B,stock Linux+32MiB,readonly root. Arena shim offset483328,
BSSend2580576,shimend2650112,payload2650128 (offsets,not runtime PAs).
No proprietary blob/dump committed. Frozen2313 board/UFS/display retained;
unrelated dirty shim.c/build.sh and collector-v2 preserved.

Ignored shim2322-trials/run-once.py prepared, readonly preflight PASS. Exact
image approval token required. Baseline/image hash checks, journal before
write, full partition readback, fresh tail+marks, full64MiB restore/hash.
Same-image Recovery fallback required before normal trial. No official
fastboot: one persistent fbraw session restores known20MiB stock prefix then
requests Recovery for full restore. No blind repeated raw reopen on timeout.
Script NOT run except preflight. Manual Fastboot may still be necessary.
Docs: docs/matisse-csf-bringup.md. Implementation commit c806996.
All completed source/tests/docs committed; no CI/push. Waiting only for
the specific2322 boot_a Recovery-fallback write confirmation. Prior
collector/unrelated work remains dirty and untouched.

## >>> COMPLETE 2026-10-31: REAL GPU POWER + SOFT RESET VERIFIED; FULL RESTORE <<<

Latest instruction fulfilled: flash original image, enter Recovery and read
logs. No further GPU trial. Device independently checked matisse/_a/root
Recovery. Full boot_a67108864B SHA256
2931647a56039722ea2585990b8ef3b1a2daf4c9b990231879f753049eaf86b1.
Authoritative shim2321-trials/gpu-normal/journal.json restore_pending=false.
All test/restore runner sessions completed; no pending restoration.

HARDWARE SUCCESS from fresh2321 console AND independent marks300..308,
kernel mark2321: stage10,error0,INIT0,POWER_ON1,POWER_OFF0,
GPUEB magic55667788,GPU_IDa8620004,GPU_STATUS100,AS_PRESENTff,
reset_rawstat100,SPM before3(second3)/after7. Shared2MiB PA7fa30000,
extra20MiB firmware PA79a00000; both below XNU RAM100000000..22e000000.
Single power reference released. This proves platform power and completed
Mali soft reset; NOT CSF firmware boot/MMU/shader/Vulkan/Metal readiness.
Fresh console confirms sweettrial2321 and readonly root. Log fix0119 works:
new18713B console seq1 replaces historical2317 instead of silently refusing.

AUTORECOVERY FAILED: user could only enter Fastboot. Do not claim automatic
watchdog Recovery success. Existing fbraw completed stock20MiB prefix
fe6e8fbf flash + reboot-recovery; full64MiB backup restored via Recovery,
then independently hashed. Platform-tools and ad-hoc USB retries failed
before writes. Never use64MiB platform-tools flash as the preferred restore.
Raw evidence shim2321-trials/gpu-normal/{after-console.txt,after-marks.bin,
gpu-result.json,journal.json}; transport restore-fbraw-log.txt. All ignored.

Commits3056f54(power/reset),87ad680(fallback record),264c9cf(log fix0119),
d555ebc(independent decoder). Local kernel/image2321 SHA e733b11f/32a9768f;
51 host tests PASS including sanitizer bounds/driver/decoder; local kernel
build PASS; no CI runs or pushes. Collector-v2 and unrelated dirty files
retained. NEXT CSF MCU firmware page tables/memory/boot-ready handshake;
not implemented. Any future boot test must not assume automatic Recovery.
Earlier RESTORE_PENDING/RUNNING notes below are superseded by this section.

## >>> RESTORE PENDING 2026-10-31: GPU2321; USER REQUESTED ORIGINAL FASTBOOT RESTORE <<<

User reports keys only reach Fastboot and automatic Recovery did not work.
User explicitly directs flash ORIGINAL image then reboot Recovery and read
logs. Do NOT start another GPU image. GPU2321 journal restore_pending=true.
Original runner PID6369 temporarily SIGSTOP to prevent racing reboots;
new dedicated restore-via-fastboot.py active, waits exact one device then
checks matisse,slot a,64MiB boot_a; flashes full backup2931647a ONLY, requests
Recovery and resumes original runner to capture tail/full restore+readback.
No LK/vendor_boot/DTBO/root write. Fastboot enumerated but product getvar timed out (IOKit pipe errors).
Host libusb reset completed; retrying restoration transport. New restore helper research/matisse/20261031-gpu/shim2321-trials/
restore-via-fastboot.py; both runners must be accounted for before stopping.

Correction: prior2320 fresh Recovery return121.41s is OBSERVED; autonomous
watchdog causality was inferred, not independently established.2321 automatic
return is FAILED per user. No fresh2321 logs recovered yet. Never claim GPU
power/reset or automatic-return success without the new evidence.

## >>> ACTIVE 2026-10-31: GPU2321 LOG FIX BUILT; SECOND NORMAL TRIAL NEXT <<<

Local build and48 host tests PASS; no CI.0119 fixes actual read-only raw
console writes (only last1025 blocks exception), adds ADT report marks300..308
and bumps kernel mark2321. GPU state machine unchanged. New kernel SHA256
e733b11f51c7194d44e765d2a79866fd876d6a013d0af846188a8ccab2e68656.
Image shim2321-ready/matisse-shim-gpu2321.img26656768B SHA256
32a9768f580d0a67b677f260cc9f5007a4c55ec9edd07b06fe49ca19cfd054a3.
Fallback Linux+32MiB and generic ramdisk identical to tested2320. Root read-only.
Fresh runner shim2321-trials/run-once.py retains tested2320 fallback journal
as prerequisite. NEXT one normal GPU trial, full baseline boot_a restore,
then decode gpu2321 console and independent report marks. No pending restore
at this save; device Recovery. Preserve pre-existing dirty files/collector.

## >>> ACTIVE 2026-10-31: GPU2320 NORMAL RETURNED; READONLY LOG GUARD FIX IN PROGRESS <<<

Recovery fallback commit87ad680. Normal gpu2320 trial returned fresh
Recovery automatically in121.41s. Full boot_a restored/readback2931647a,
journal shim2320-trials/gpu-normal/journal.json restore_pending=false.
Only tail block1024 changed; historical2317 console bytes/header unchanged.
Fresh SWEETMRK count52 proves XNU reached root mount and launchd exec;
old kernel build mark still2316 because that constant was not bumped.
NO GPU_ID/power/reset result recovered; do not claim GPU success.

Root cause observed in local source:0093 removed su.writable guard only
in sweet_log_start, while ufs_write_blocks still rejects read-only writes.
New0119 bounds the diagnostic exception to last1025 blocks, keeps all VFS
writes blocked, and records ADT sweet-gpu-report as9 independent progress
marks300..308. Build ID bumped2321. Local incremental kernel build running;
no new CI or further partition write. New image will retain tested stock
Linux fallback and readonly root. Preserve unrelated dirty files/collector.

## >>> ACTIVE 2026-10-31: GPU2320 RECOVERY FALLBACK VERIFIED; NORMAL TRIAL NEXT <<<

Commit3056f54 contains bounded shim GPU power/reset implementation. First
hardware phase completed: GPU2320 recovery-mode fallback boot returned fresh
Recovery in26.56s. Full64MiB boot_a restored with readback SHA256
2931647a56039722ea2585990b8ef3b1a2daf4c9b990231879f753049eaf86b1.
Journal research/matisse/20261031-gpu/shim2320-trials/recovery-fallback/
journal.json status complete-restored-Recovery,restore_pending=false.
This verifies embedded stock Linux recovery bypass, NOT normal GPU operation
or automatic watchdog return.47 local host tests re-run PASS; no CI.
NEXT run gpu-normal with same imagebc8ecb9f, then restore full boot_a and
inspect only fresh gpu2320 persistent evidence. Preserve collector-v2 and
all unrelated dirty files. No LK/vendor_boot/DTBO/root writes.

## >>> ACTIVE 2026-10-31: GPU2320 BUILT; RECOVERY FALLBACK TEST NEXT <<<

User latest: keep collector-v2; prioritize GPU power/init through shim and
continue tests without repeated prompts. No GPU hardware claim yet.
Implemented independent GPUEB transport/power/reset core and optional shim
live-FDT adapter, with bounded replies, ownership, SPM gates, memory-conflict
refusal and CSF soft-reset0x101.47 host tests PASS including ASan/UBSan.
New kernel0118 only adds ADT-controlled automatic Recovery window; local
incremental build PASS, no CI. Kernel SHA2567c16716c6a047bdd0615011cbb66862ce452259ca3f573220cf261c2cf975f8c.
Image research/matisse/20261031-gpu/shim2320-ready/matisse-shim-gpu2320.img
26652672B SHA256bc8ecb9fa343de62f5554bda69fbe10549e90fef5ba637d4c390d9449cb12f04.
Expanded80402548B under measured DTB limit. Original package Linux intact
at+32MiB for mode2/unknown fallback before shim_main. Frozen2313 board/UFS/
display objects retained; current dirty shim.c/build.sh excluded. Root
ufsrw=0/rootrw=0; diagnostic summary via existing version print/SWEETLOG.
WDT31s armed by shim, normal XNU feed stops after60s only for this ADT.

Fresh Recovery preflight confirmed matisse/_a/root; full64MiB boot_a still
baseline2931647a. NEXT one Recovery-only fallback verification with fresh
runner research/matisse/20261031-gpu/shim2320-trials/run-once.py; then full
restore/readback. Only if that passes run normal GPU trial. Journal in
{recovery-fallback,gpu-normal}/journal.json is authoritative restoration
state. No write at this handoff save. Preserve pre-existing unrelated dirty
files and collector-v2. Never execute/import historical run-ui runners.

## >>> ACTIVE 2026-10-31: SHIM GPU POWER/INIT; COLLECTOR CHANGES RETAINED <<<

Latest user steering: keep collector-v2 work (do NOT revert it), prioritize
MT6983 GPU power and initialization through the existing shim/XNU path.
Continue without repeated unplug/permission prompts; report substantial
progress. No new boot test or partition write in this phase yet.
Recovery is online, boot_a was fully restored (baseline2931647a); no active
runner or pending restore. Preserve existing unrelated dirty shim files.

Fresh read-only userdata tail capture independently verifies established
SWEETLOG works: userdata114319917056B, log offset114315718656B,4198400B
capture, version1,size4194304,total317844,seq116 plus SWEETMRK. Decoded
console is HISTORICAL successful2317 XNU boot, not a new GPU test. Artifacts:
research/matisse/20261031-gpu/shim-handoff/{existing-log.bin,
existing-log-manifest.json,existing-console.txt}. Do not repeat old claims
that persistent logging is broken or use legacy boot+4MiB SWLG offsets.

Next implement independently written, bounded shim GPUEB mailbox/power
initialization with explicit handoff, memory-ownership and timeout checks;
first validate host and freestanding compilation. Reuse frozen2313 shim
objects/2317 payload, not the current dirty shim.c/build.sh. GPUEB runtime
reservations and GPU_ID remain UNMEASURED. Firmware parsing and IPI wire
encoding alone do not establish power-on or CSF readiness.

## >>> COMPLETE 2026-10-31: ONE RAM COLLECTOR TRIAL; FULL BOOT_A RESTORED; RECOVERY ONLINE <<<

Result and receiver fix commit b422c33 is local (not pushed). No CI run.
The single specifically authorized collector trial is COMPLETE. User preferred
Recovery write; no fastboot flash occurred. First fastboot getvar attempt
failed before write, USB replug+fastboot reboot recovery worked. The new
Recovery runner24278 exited0 after full original boot_a restoration and
SHA256 readback. No active runner or restoration duty remains.

Collector image21450752B SHA25650813edab73c4ebcb4554cb41360457f180df1df593d0325ebc76fe64f2dee6d
was staged and hashed in /tmp, written to boot_a with dd+fsync, full64MiB
partition readback3b5ef7f319e3b9a56373381ae87b77aba47229e4cff74c33cb7aedbd44420c42
matched image prefix+original tail. Normal adb reboot at09:35:00 China time.
USB ACM appeared within7s then disconnected during receive (ENXIO); no
complete frame/collection saved. This is partial transport evidence, NOT
GPUEB addresses/GPU_ID/acceleration, and does not establish panic or WDT.

User physically entered Recovery. Runner restored full67108864B original
backup via Recovery dd+fsync; readback09:36:10 China time equals
2931647a56039722ea2585990b8ef3b1a2daf4c9b990231879f753049eaf86b1.
Independent post-restoration read-only check confirmed matisse/_a/Recovery
and same full hash. journal.json restore_pending=false,collection_received=false.
Artifacts are ignored research/matisse/20261031-gpu/
collector-trial-recovery-20261031/{journal.json,receive.txt,post-recovery/}.
No LK/vendor_boot/DTBO/userdata writes or second test.

Post-Recovery pstore console262132B is CORRUPTED/STALE: contains old Recovery
uptime~863..953s and prior reboot,bootloader, NOT a usable collector log.
No SWEET-ENTRY/collector/gpueb trial record found. /proc/last_kmsg absent;
exec-out error text must NOT be called a valid last_kmsg. New pl_lk140881B
is current mode2 Recovery log only, not normal-boot evidence. Cause of
USB disconnect remains unknown; cannot diagnose GPUEB failure from this.

Fixed receiver cleanup to close descriptor even if tty disappears and
preserve original read exception instead of masking with tcsetattr ENXIO.
11 collector tests PASS (2 new disconnection regressions),git diff --check
PASS. No new kernel build/CI. Next local work: preserve partial serial
bytes and get durable early-init diagnostics before proposing another
image. Any next boot_a write requires fresh specific authorization.
Preserve unrelated shim/build.sh,shim/shim.c,tools/sweet-marks.py,0093,
.DS_Store,.workbuddy. Previous RUNNING/RESTORE notes are historical.

## >>> RESTORE PENDING 2026-10-31: ACM APPEARED THEN DISCONNECTED; AWAIT RECOVERY <<<

New Recovery runner session24278 remains ACTIVE, waiting for Recovery to
restore full boot_a. journal.json in collector-trial-recovery-20261031 is
authoritative: restore_pending=true,collection_received=false.
ACM enumerated once within7s of adb normal reboot, then receiver read
failed ENXIO Device not configured; tty cleanup also raised ENXIO. No valid
collection was saved. This proves some USB ACM enumeration, NOT successful
GPUEB handoff capture or a diagnosed panic/reboot cause. ADB/fastboot/ACM
were then absent. User asked via async input to hold Power+Volume Up and
enter Recovery (or report Fastboot). No second test is planned/authorized.
NEXT finish full original64MiB restoration and SHA256 readback before any
further work, then pull read-only pstore/last_kmsg if available. Preserve
user/root/LK/vendor_boot. Do not stop with restore_pending=true.

## >>> RUNNING 2026-10-31: COLLECTOR WRITTEN IN RECOVERY; RESTORE_PENDING=TRUE <<<

User explicitly preferred Recovery write over fastboot flash. First fastboot
preflight timed out on getvar, BEFORE any flash (old collector-trial journal
restore_pending=false). User replugged USB; fastboot reboot recovery then
succeeded. New dedicated Recovery runner session24278 is ACTIVE:
research/matisse/20261031-gpu/collector-trial-recovery-20261031/run-recovery-once.py
with journal.json in same directory as restoration source of truth.

Recovery preflight reverified matisse/_a/root,64MiB boot_a baseline2931647a,
local image50813eda and full backup. Staged helper in /tmp; dd+fsync wrote
collector21450752B to boot_a ONLY. Full64MiB partition readback equals predicted
3b5ef7f319e3b9a56373381ae87b77aba47229e4cff74c33cb7aedbd44420c42
(short collector prefix plus unchanged original tail). adb reboot normal
issued successfully at2026-10-31T01:35:00Z (09:35 Asia/Shanghai).

RESTORATION IS STILL REQUIRED. Runner waits120s for a new ACM port then
waits Recovery. It can request reboot recovery if fastboot is available;
otherwise physical keys may be necessary. It restores full67108864B backup
with Recovery dd+fsync and clears restore_pending only after SHA2562931647a
readback. Never cancel without continuing restoration (supports --restore-only).
No LK/vendor_boot/DTBO/userdata writes. No collection or GPU result yet.
NEXT monitor live runner and complete restore; do not stop with armed boot_a.

## >>> ACTIVE 2026-10-31: USER AUTHORIZED ONE COLLECTOR BOOT_A TRIAL + FULL RESTORE <<<

User explicitly answered 可以 to the concrete temporary collector boot_a
flash, one normal boot collection, full64MiB original boot_a restoration
and return to Recovery. This authorization is specific to image50813eda
and baseline2931647a; no LK/vendor_boot/DTBO/userdata writes authorized.
Fresh Recovery preflight matisse/_a/root,boot_a67108864B,full SHA256 matches
baseline; local image+backup hashes verified.9 collector tests PASS again.
Dedicated new runner (no old imports) is ignored under research/matisse/
20261031-gpu/collector-trial-20261031/run-collector-once.py. Its journal.json
is restoration source of truth. It sets restore_pending BEFORE flash, then
waits for fastboot and restores full backup, reboots Recovery, and clears
restore_pending ONLY after full Recovery SHA256 readback. Collector has no
USB command shell, so user physical Power+Volume- may be needed after
collection to enter fastboot. No partition write yet at this handoff save.
NEXT execute the authorized one-shot runner, monitor, restore and document
exact outcome; do not stop while restoration is pending. Prior notes follow.

## >>> ACTIVE 2026-10-31: RAM COLLECTOR BUILT; BOOT_A FLASH NOT AUTHORIZED YET <<<

User approved RAM-only collector development, then asked to reboot Recovery
after testing. Current Recovery stayed online; NO reboot/partition write/
USB rebind/insmod performed. No active runner or pending restoration.
Implementation commit2650520 is local (not pushed). Repeated independent
build is byte-identical; no new CI run.
A specific boot_a flash confirmation is still required by AGENTS.md; the
collector image did not exist when the earlier general approval was given.

New tools/matisse-ramcollector.py reads bounded newc/ELF, selects17 explicit
USB/PMIC/clock prerequisites, uses static Recovery BusyBox, adds separate
rdinit PID1. tools/ramcollector/init mounts pseudo filesystems only, disables
modprobe, excludes UFS/MMC/GPU/GPUEB, snapshots FDT/pl_lk/dmesg before/after
modules, exports immutable hash+base64 tar via ACM. No USB command receiver.
Tools/matisse-collector-receive.py bounds and verifies frame/archive before
writing new host output. No firmware binaries or raw device data committed.

Critical fix: actual vendor_boot platform fragment is just4B legacy LZ4
magic02214c18. Gzip appended to that would be invalid; collector uses legacy
LZ4, verified repeated-prefix decompression against actual fragment. Own
/matisse-collector paths avoid Android init selection; actual normal LK
fragment selection and minimal module closure remain BOOT-UNTESTED.
Reference driver mode3 is peripheral, used to avoid charger/Type-C stack.
log_store module is included for proc/pl_lk; no proc write requested.

Build artifact research/matisse/20261031-gpu/matisse-gpueb-ramcollector.img
21450752B SHA25650813edab73c4ebcb4554cb41360457f180df1df593d0325ebc76fe64f2dee6d.
Ramdisk1867289B legacyLZ4,40 entries,17 modules; compressed kernel/signature
identical to existing GPUEB probe, expanded48945268B. Signature retained,
NOT re-signed/authenticated. No new full XNU build or CI run.

Validation:9 new host tests + GPUEB10/entryprobe14/Android7 PASS (40 total
this phase). Recovery --snapshot-only executed from /tmp,26 files packed
and receiver verified; transmission used existing ADB, NOT ACM. PID1,
module loading/USB enumeration/normal boot are NOT tested; no new GPU_ID,
shared PA or acceleration result. Fresh boot_a read-only hash still equals
full64MiB baseline2931647a56039722ea2585990b8ef3b1a2daf4c9b990231879f753049eaf86b1;
local full backup independently verified. Raw evidence collector-analysis/
under ignored GPU research. Details and pending guarded procedure are
docs/matisse-ramcollector.md.

NEXT: obtain specific authorization for temporary boot_a collector flash,
one normal-mode collection, full64MiB boot_a restore and Recovery return.
Only then implement a fresh dedicated guarded runner/journal, preflight
slot/product/size/hashes, receive over exact ACM port, restore/readback.
Do not execute historical run-ui runners or flash LK/vendor_boot/DTBO/root.
Then audit normal GPUEB reservations versus XNU RAM before any GPU MMIO.
Preserve unrelated dirty shim/build.sh,shim/shim.c,tools/sweet-marks.py,
0093,.DS_Store,.workbuddy. Previous handoffs follow.

## >>> ACTIVE 2026-10-31: GPUEB RECOVERY SKIP CONFIRMED; PROTOCOL + FDT PROBE BUILT <<<

Latest user authorization supersedes STATIC-only notes below: device online
and available for tests. Complete package now exists in Documents/
matisse_images_OS2.0.2.0.ULKCNXM_14.0/images. Read-only collection and
local code/builds authorized; each partition flash still needs specific
confirmation. Android remains unavailable after userdata changes.

Fresh recovery-live-2 inventory succeeded: root Recovery, matisse/_a,
5.10.209-android12-9-00019-g4ea09a298bb4-ab12292661. live.dtb was pulled
and hash verified. No mali0/bound Mali/GPUEB/gpufreq drivers; SCPSYS bound.
No gpueb_mem_addr/size in fresh DT. CONFIG_DEVMEM is not set, /dev/mem
absent; a userspace devmem probe cannot work. No GPU_ID read.

Read-only partition dumps verified before and after pull:
gpueb_a and gpueb_b1048576B, both SHA256
0650aa96d8df7cf98b6b63e8ebaeb02d6b323989d769b1b7ab8c4e0884ae489d;
lk_a8388608B SHA2563520fe6bac0d3486ded623149ea7f0a95f4653c4206566fda99361f0ea52e202;
dtbo_a33554432B SHA2567256d964d84ca2c446c8cd748589b57fd2cd48354d8a2e7cdb38000043015ce7.
Artifacts/manifests remain ignored under research/matisse/20261031-gpu/.
GPUEB MTK container identifies tinysys-gpueb-RV33_A; both slots match.
User confirms actual device LK was deliberately modified; use its dump as
authority. Component comparison: LK payload differs by59B, bl2_ext/aee/DTB
identical; cert2 size shifts later file offsets by0x430. Actual LK DTB at
0x27d310 (not package0x27cee0), SHA256783b7fb8...cc12ffae. Package gpueb
and dtbo match device prefixes with all-zero partition tails. Full package
super SHA256 matches prior loose super;33 smaller image/binary hashes saved,
17 MTK containers parsed. No firmware or device dump committed.

New read-only /proc/pl_lk140879B SHA256937ed759...14942da records mode2.
Actual LK payload0xc998..0xca0c explicitly skips GPUEB loader in mode2;
normal branch0xca4c calls loader0x1ff4c. Loader injects BE64 runtime memory
at0x2005c..0x200b8. Hence missing Recovery handoff is explained, not proof
normal boot lacks GPUEB. Do not infer readiness from a0ms profile string.

Implemented tools/android-mtk.py component-aware bounded reader; GPU
inventory validates mailbox/memory tables and reports missing handoff
without guessing PA. xnu/gpu/mtk_gpueb_protocol.{c,h} independently encodes
confirmed32B INIT/POWER ABI and checks memory layout/signed replies. No
mailbox transport, MMIO, firmware execution, or kernel integration.
shim/entryprobe_gpueb.c and mkentryprobe --level gpueb describe only live
FDT handoff then return to Linux. Real live DT host replay gives stage9004,
mode2, Mali13000000+480000, no shared PA; not a hardware probe result.

Build-only artifact research/matisse/20261031-gpu/gpueb-handoff-probe.img:
20963328B SHA256094d4e563a97317119cbcdab0d3f1bda34ae3b49f694e3b95ca7b671b9b7a71f.
NDK28.2 LLVM link PASS, expanded48945268B within0x7c80000; ramdisk/signature
identical to package boot.img8775a30a...95d9cb7, inner kernel differs only
banner. Historical restored boot_a itself already contains2MiB old probe;
its inner kernel also matches package except old banner. Do not nest probes.

IMPORTANT: probe image is NOT ready for normal-mode hardware trial yet.
Actual vendor_boot has4B platform fragment + type2 Recovery fragment;
normal LK inclusion of Recovery ramdisk unverified. Normal boot of this
image may try unavailable Android. Recovery boot would repeat skip-mode2.
NEXT: prepare RAM-only collector (no userdata mounts) or same-boot XNU
handoff logging, verify normal boot ramdisk selection and firmware memory
reservation against XNU RAM window, then request specific boot_a flash
authorization. Do not flash LK/vendor_boot or execute old trial runners.
GPUEB loader allocates dynamic2MiB shared +20MiB extra regions; PA unknown
in normal boot, cannot assume they avoid XNU100000000..22e000000 window.

Validation53 tests PASS (GPUEB10,entryprobe14,Android7,CSF1,shim8,board9,keys4);
ASan/UBSan CSF+GPUEB8192 mutations each PASS; freestanding arm64-apple-darwin
protocol compile PASS. No new full XNU build, CI run, flash/boot, GPU_ID or
GPU execution. Recovery live-3 inventory7 records PASS; full audit is
docs/matisse-gpueb-handoff.md. Completed implementation commit824d867
(local, not pushed). Final read-only boot_a SHA256 still matches complete
64MiB restored baseline2931647a56039722ea2585990b8ef3b1a2daf4c9b990231879f753049eaf86b1;
no restore pending and no active test runner. Probe remains build-only.
Preserve unrelated shim/build.sh,shim/shim.c,tools/sweet-marks.py,0093,
.DS_Store and .workbuddy changes. Previous handoffs follow.

## >>> HISTORICAL 2026-10-31: STATIC GPU IMAGE AUDIT + CSF PARSER; Android unavailable <<<

USER STEERING: Android cannot boot after userdata changes; only STATIC
analysis from now on. Do not reboot to Android, wait for rooted Android,
load vendor GPU modules, or infer permission for partition writes. No
device writes/boots/MMIO performed this task. Last2317 input/UI/restoration
evidence below remains historical and unchanged. Current device mode is
NOT established after the user attempted to change modes.

Code commit c8988fd adds read-only sparse/LP extraction tool, Recovery/rooted
Android inventory tool (not required for next static work), FDT/DTBO parser,
portable xnu/gpu/mali_csf_firmware.{c,h}, and5 passing tests. C parser is
NOT wired into a kernel patch or boot path; validates containers only, no
firmware execution/GPU acceleration claim. Docs/matisse-gpu-static-audit.md
contains the findings and next implementation dependencies.
Final validation also included existing board/key regressions:18 tests
PASS total,11 extracted artifact hashes+firmware identity PASS,git diff
--check and documentation links/fences PASS. Static audit/docs milestone
5749b0b and implementation c8988fd are local commits; not pushed.

Source images are /Users/xiaohuasheng/Documents/{super,lk,vcp,dtbo}.img.
super7918405960B SHA256289951fb8db34509591ada6259737b0522cc5a923f878171e9b746031e601957;
source size/mtime unchanged across hash. Sparse LP geometry/header/tables
checksums PASS. Extracted vendor_a2041831424B SHA256cc8a64dc...19defe59;
vendor_dlkm_a19492864B b70368db...7d4514b. EROFS1.9.4 dump.erofs --cat
used to extract individual files without mounting or changing images.
Artifacts/manifests stay in research/matisse/20261031-gpu/, ignored.

Static facts: Mali module .modinfo r32p1-01eac0 (UK version1.18), KMD
1823016B SHA25622b26f30...2d742a3b. Vendor module vermagic5.10.209-
android12-9-gad068458f122 differs from Recovery kernel. CSF/reload binaries
are identical258048B SHA256de22d2fc06bc8a859968499a6e609c27fe838be062bf5c97d92ea9f904f7229a.
Format0.1/hash0x01010000/tableEnd0x300,21 entries/10 sections/3 protected.
7 sections are not16KiB aligned (4 non-protected); shared VA04000000..
04094000. Runtime CSF GLB_VERSION/ABI NOT measured; format hash is NOT ABI.
Actual blob parse passes ASan/UBSan,8192 deterministic mutations PASS,
freestanding arm64-apple-darwin single-file compile -Wall/-Wextra/-Werror
PASS. No full XNU build/CI dispatch/run ID or boot in this task.

LK has valid embedded FDT at0x27cee0,size335048B; GPUEB enabled, mailbox
tables and dual buck. LK strings name tinysys-gpueb-RV33_A and runtime
gpueb_mem_addr/size injection; strings alone do NOT prove a boot executed
the loader. vcp.img header is tinysys-vcp-RV55_A, not GPUEB firmware. No
independent gpueb.img found in supplied inputs. Historical Recovery DT
20261026 GPUEB node lacks runtime mem_addr/size; no invented carveout.
GPUEB-mode wrapper sends CMD_INIT_SHARED_MEM0 then CMD_POWER_CONTROL6
over IPI_ID_GPUFREQ; binary confirms8-word message, timeout arg0x2710.
Do NOT choose AP power table simply because AP code exists in module.

Mesa25.1.0 pinned from official remote to5c142e46f3f6e752ed745fd48912ebb8fad67145.
Its model table lacks G710; unknown model fails VK_ERROR_INCOMPATIBLE_DRIVER.
No G610 spoofing. This pin is a reproducible audit baseline, not latest or
G710 support claim. Reference snapshots retained in ignored research.

Earlier this turn ADB did confirm matisse/_a/root Recovery5.10.209-
android12-9-00019-g4ea09a298bb4-ab12292661, no mali0/bound Mali/GPUEB/
gpufreq driver, runtime unsupported. User then disconnected/rebooted;
automatic inventory failed before live.dtb capture (failed manifest retained).
Do not call historical DTB a fresh read or claim GPU_ID was read.

NEXT STATIC ACTION: reverse LK GPUEB boot-mode branch and runtime shared-
memory/FDT handoff, locate independent GPUEB partition image if available,
then implement bounded mailbox transport with confirmed ABI. In parallel
dependency order, design4KiB GPU page mappings backed by16KiB XNU pages
and audit G710 model/errata. Do not change startup/power until handoff and
owners are understood. No active runner/restore started in this task.
Preserve unrelated shim/build.sh,shim/shim.c,tools/sweet-marks.py,0093,
.DS_Store and .workbuddy changes. Completed code is committed locally.

Previous route/hardware handoffs follow; latest STATIC-only instruction wins.

## >>> ACTIVE 2026-10-31: GPU ROUTE AUDITED; 0x2317 hardware baseline unchanged <<<

User supplied the UniXNU/Mali layering constraint. Documentation commit
51e7537 adds docs/matisse-gpu-plan.md and links it from the Chinese roadmap.
Decision: reuse architectural boundaries only; investigate MT6983 CSF /
Panthor / PanVK with a Darwin KMD interface. No Adreno740/Turnip/GMU port
is implied. AIR/Metal reuse on this iOS16 ABI remains unverified.

Observed source facts: research/matisse/mt6983.dts declares Mali MMIO
0x13000000+0x480000 and GPUEB support. MiCode/MTK_kernel_modules local
rubens-s-oss commit c66b3c9ce7b5c0bc3d72a829f6542200deaa8a9c, r32p1
MT6983 OOT Makefile explicitly enables CONFIG_MALI_CSF_SUPPORT=y; its CSF
loader defaults to mali_csffw.bin. This is reference-source evidence, NOT
the running device's driver version, firmware hash, GPU_ID or powered state.
Mali-G710 is the expected model, not newly hardware-read in this task.

Important correction to supplied licensing claim: Linux v6.12 Panthor
drv/fw/mmu/gpu/heap/sched/device/gem .c files are GPL-2.0 OR MIT; Panthor
UAPI is MIT. Panfrost drv is GPL-2.0. Audit dependencies individually; do
not treat all Linux DRM or MTK kbase as MIT. Mesa official support table
snapshot lists G310/G610 but not G710, so G610 support/conformance does
not prove G710 works. Linux ioctl compatibility alone is insufficient;
matrix covers BO/VM/CSF groups/tiler heaps/syncobj/sharing and the risk of
mapping a 4KiB-isolated MMIO register page into 16KiB XNU user pages.

Validation: git diff --check PASS; 10 downloaded v6.12 reference hashes
and all8 stated Panthor license headers verified, Mesa snapshot hash and
local Markdown target/fences checked. References/manifests are ignored in
research/matisse/20261031-gpu/, no third-party source/blobs committed.
UniXNU GPU port webpage returned HTTP403; its detailed guide was not
independently verified. AdrenoMetal README confirms sheng/A740 composition.
No kernel/source driver edits, build, CI dispatch, boot or device writes
in this task; no new build/boot/CI result or GPU acceleration claim.
Prior2317 restoration evidence below remains the latest hardware result,
not a live Recovery connectivity check performed in this task.

Next concrete action: phase0 read-only live-DT/driver/firmware inventory
and pin a Mesa revision for phase1 capability + Darwin interface audit,
before designing an opt-in hardware probe. Do not read unpowered GPU
MMIO, run old trial scripts, or write boot_a/userdata without the required
fresh confirmation. Preserve unrelated dirty shim/build.sh,shim/shim.c,
tools/sweet-marks.py and untracked0093/.DS_Store/.workbuddy.

The following ACTIVE heading is the preserved last hardware handoff.

## >>> ACTIVE 2026-10-31: 0x2317 native1440x3200 + TOUCH + ALL3 KEYS VERIFIED; stock boot_a RESTORED; Recovery online <<<


CURRENT RESULT (supersedes RUNNING/pending notes below): user's request to
fix resolution and enable touch/buttons is COMPLETE and hardware-confirmed.
User observed full-screen1440x3200, working touch, power/volume+/volume-.
Trial2317 fresh logs independently show MT6363 chip63, KP_EN1, all3 physical
press/release -> HID events to backboardd, plus display on/off. Touch75 log
records, key PMIF errors0, panic records0. Manual FASTBOOT218.26s; runner55131
completed, full64MiB original boot_a restored and independently readback
SHA2562931647a56039722ea2585990b8ef3b1a2daf4c9b990231879f753049eaf86b1.
boot-ui-2317-result.json restore_pending=false. Device is now Recovery.
DO NOT rerun/import old trial runners. No active restore or hardware trial.

Exact successful artifact: research/matisse/20261031-hs/
matisse-ui-native-keys-2317.img (7073792B, SHA256
a9e9a0ff876915e5d9258e451ee31967572bf435d0d10373e02366bcdcaeac4d).
Kernel marks/build2316 (same kernel reused): e25c06b0...857269. Native ADT
matisse-userland-native-keys-2317.adt adds ONLY344B verified/sweet-keys to
working2315 native ADT; identity/display/touch unchanged. Root flashlight
correction2314 remains installed; no root/GPT changes in this input task.

Completed fixes:955694e native canvas;3210bda missing0094 local integration,
0117 shared locked PMIF and keypad stride4,0099 clean-build context;
379adbf payload rejects enabled keys with missing/invalid node. Latest
successful trial handoff72a2f33.20 tests PASS, full local kernel build exit0,
image+payload+symbols independently verified. Fork Actions dispatch HTTP422
repository disabled, no new CI run. Success evidence is
ui2317-user-observation.json / ui2317-key-focus.txt / ui2317-verification.json.
Preserve unrelated dirty shim/build.sh,shim/shim.c,tools/sweet-marks.py and
untracked0093. Any next work is a new requested feature, not unresolved input.

Latest verified handoff: trial0x2313 returned FASTBOOT at157.15s. User
confirms this was MANUAL and screen was Apple/black; no spontaneous crash
or visible UI is established. Runner58786 exited successfully. Full64MiB
original boot_a restored; boot_a_restore_pending=false and independent
Recovery readback SHA2562931647a56039722ea2585990b8ef3b1a2daf4c9b990231879f753049eaf86b1.
Recovery was online at the end of the preceding phase. Do not rerun/import runner.

SpringBoard still waits in FigFlashlightRemoteCreate sync XPC. Actual20H392
MediaToolbox _FigMediaServerStart gates FigStartCaptureServers on
StartRecorderServer. CMCaptureCore FigStartCaptureServers starts both
FigPreloadShaders and FigFlashlightServerStart. Existing root tweak sets
StartRecorderServer=false to avoid a verified NULL-OpenGL shader-prewarm
crash. This static dependency strongly explains absent flashlight replies;
mediaserverd sampled in ordinary CFRunLoop/workqueue waits. Next: find a
minimal way to retain shader/GPU protection while allowing flashlight
startup, before making root changes. No host root/database mutation yet.
Fresh evidence: research/matisse/20261031-hs/ui2313-console.txt and
dis-Fig{MediaServerStart,StartCaptureServers}.txt. Shared-cache slide0x8984000.
PosterBoard crashed once (sig5, pc0x1ca0fc268); causal role unproven.
Read-only analysis root remains /tmp/ios-sweet-20H392-analysis (disk7).
2314 preparation: tools/sweet-media-flashlight.py validates exact20H392
cache25 UUID/SHA256, then changes two instructions so FigStartCaptureServers
starts flashlight only (first object=existing flashlight CFString, next=nil).
Recorder XML becomes true at identical length; shader/camera paths stay out.
Dry-run validates3 cache bytes+5 XML bytes; all3 configs share one inode.
No device root writes yet. Live HFS journal start/end differ, so pulling
16GiB live root for native replay and a preimage-checked differential update.
Original boot_a remains restored, Recovery online. Prepared2314 image
7069696B SHA2564202e13c009e55ca29fe6b30811375c9356ddc11bc3983541031740f73a547eb;
identical kernel2311/ADT2312; only cmdline trial ID and PosterBoard sampler
added. No kernel build or new CI. Do not import/execute run-ui-2314.py yet.

2314 native-image milestone: pulled current16GiB root SHA256
9ed3b9d4bd2447a0a3adce867637f83971bd430d4c16206b895e760748b14016.
APFS clone mounted with native macOS HFS; journal replay completed. Patched
in place, preserved hardlinks/uid/gid/modes/extents (cache fork clumpSize
340->0 is a native metadata update; logicalSize/blocks/extents unchanged).
Unmounted native fsck_hfs -fn exit0, volume appears OK. Journal now clean,
start=end3142656; volume attributes0x80002100. Patched disassembly confirms
str xzr,[sp] then first object FigFlashlightServerStart, so shaders/camera
are not in the iteration. Image SHA256
4c5c6bd2b9d6f01752204d05ab8801b315645638a08e40dcd7d8d1780d7ad642.
Delta34 runs/573440B, every device preimage matched in read-only preflight.
Now applying with per-run readback; see apply-root-delta-2314-result.json.
Keep live-root-before-2314.dmg and root-delta-2314 before blocks for rollback.
No GPT/other partition changes. 0x2314 boot runner NOT STARTED yet.

0x2314 BOOT STARTED Unix1793404200.192118. Root delta34/34 runs applied
and individually readback verified; root write_pending=false. boot_a image
written and full-partition SHA256c28b9ac8db4714d14c8fd2cd9f496b967590d1745f4e215a7ce48e7f98b76e6b verified.
boot-ui-2314-result.json now boot_a_restore_pending=true. Runner session97112
monitors1200s and restores original64MiB boot_a upon FASTBOOT/Recovery.
NEVER import/rerun run-ui-2314.py. No UI claim; need screen observation and
fresh sweettrial=2314 logs. Kernel marks intentionally remain2311.
Original/local root and delta preimages preserved. Read-only analysis disk7
detached; no live image mount remains. Code380cce3 pushed; handoff9a66163
records native replay. No new kernel/CI; fork Actions remains disabled.

MILESTONE: user answered2314 screen question with “出现锁屏、设置或主屏幕”.
This is first positive user observation of visible iOS UI on matisse in this
sequence. Exact lock/setup/home screen not yet distinguished; touch remains
OFF. Flashlight-only correction was the sole root change beyond native HFS
journal replay. Fresh logs still require Recovery return; do not infer their
contents or claim touch works. Runner97112 continues, stock boot_a restore
pending until FASTBOOT/Recovery. Record observation separately in
ui2314-user-observation.json because runner owns boot result JSON.

2314 user clarifies exact screen: LOCK SCREEN. User manually returned to
FASTBOOT at176.77s. Runner has flashed full64MiB stock boot_a (raw fastboot
OKAY) and requested Recovery (OKAY); awaiting Recovery independent hash
verification and fresh logs. Current restore_pending remains true until
that completes. Do not confuse prior Apple framebuffer thumbnails with
this new physical screen observation. Touch still disabled.

FINAL2314: user confirms LOCK SCREEN and manual return; FASTBOOT176.77s.
Runner97112 completed exit0; original64MiB boot_a restored and independently
readback verified SHA2562931647a56039722ea2585990b8ef3b1a2daf4c9b990231879f753049eaf86b1.
restore_pending=false; Recovery online. Fresh console sweettrial=2314 has
SpringBoard26 main in UIApplicationMain/GSEventRunModal/CFRunLoop at105.499s,
not flashlight sync wait. GUI swaps reach40, app surfaces4..10 created.
Mediaserverd28 main idle; no mediaserverd crash. PosterBoard crashes once
in initial switcher config but replacement233 reaches UIApplicationMain;
not a blocker to observed lock screen. Actual shared-cache slide0x3a9d8000.
Perf confirms NormalWB attr0, M/C/I and WB walks, R87.84MiB/s, R/W/S errors0.
FBIMG first3 frames2/3/6 still Apple; these early RAM samples do not contradict
later user-confirmed physical lock screen. Analysis images detached.
User now requests correct resolution plus touch and keys. Existing canvas
1125x2436 was centered inside1440x3200 panel; next use sweetfb_native=1 and
verified touch enable1/init1/rails1/mark1/delay3 plus sweetkeys=2. Root correction
remains installed; no new root mutation required. Do not reuse stale source
in research/matisse/xnu-upstream as the final2311 build tree.

2315 prepared for user's resolution/input request: same exact2311 kernel,
shim and installed root as2314; native canvas1440x3200 set consistently in
ADT /arm-io/disp0 and kernel/HID boot arg sweetfb_native=1. tools/mkpayload.py
now synchronizes opt-in native ADT dimensions with sweet-fbcon; default
canvas1125x2436 unchanged. Identity props/other ADT bytes unchanged (revert
just2 dimensions reconstructs2312 ADT). sweetkeys=2 feeds HID; sweettouch=1,
init=1, rails=1, mark=1, delay=3 use hardware-proven SALIXP path. USB/battery
remain off. No kernel/CI rebuild. Eight board tests, four actual present/HID
ASan+UBSan geometries and five touch/PMIF mocks all PASS. Independent image
check PASS;533-byte cmdline not truncated. Image7069696B SHA256
181ec5e5e9a5caaa325eab0ce76c062851057d7d818c84f9466ba0819b64df7e;
expected written boot_a hash1a12a71ce7f90a7ea5fd0965e5dc94fef7fe83e5e05c60424201c7bf3f8a90a0.
Runner run-ui-2315.py prepared, not started at this note. Never import it.

0x2315 BOOT STARTED Unix1793404673.039019. Full written boot_a verified
SHA2561a12a71ce7f90a7ea5fd0965e5dc94fef7fe83e5e05c60424201c7bf3f8a90a0;
resultboot-ui-2315-result.json restore_pending=true. Runner session71161
monitors1200s with full stock boot_a restore on FASTBOOT/Recovery return.
Never import/rerun run-ui-2315.py. User authorized enabling touch/keys and
correcting resolution. Code955694e pushed; exact kernel2311 unchanged.
Need actual native display and touch/keys user observation, then fresh2315
marks/console and final stock hash verification. No current success claim
for input/native mode. Prior2314 lock screen success and restore confirmed.

MILESTONE2315: user explicitly reports “全屏且触摸有响应”. Physical
native-screen coverage and touch response are therefore user-confirmed. No
keys success claim. Prior agent found the2311 kernel omits the MT6363 keys
driver despite sweetkeys=2; this continuation is verifying source/linkage
and repairing it before rebuilding. Existing2315 runner PID38223 remains
active with stock boot_a restoration armed; do not import/rerun it. Preserve
the working2315 display/touch configuration and unrelated dirty files.

FINAL2315: user manually returned to FASTBOOT at244.11s. Runner exited
after restoring full64MiB stock boot_a and Recovery hash verification:
2931647a56039722ea2585990b8ef3b1a2daf4c9b990231879f753049eaf86b1;
restore_pending=false. Fresh console confirms AppleCLCD1440x3200 and both
1440x3200 surfaces and HID touch down/up events. User separately confirms
full-screen and responsive touch. Keys failure now observed in console:
Qualcomm fallback unsupported arbiter version0x2; current local2311 tree
omitted0094 source, hook and files entry. Kernel2316 build includes them
plus0117 to use shared locked sweet_spmi reads (SID4 only0009/001e, no
independent PMIF init writes), validate chip0x63, correct keypad stride4.
Recovery live read confirms MT6363 chip0009=63, TOPSTATUS001e=1e idle.
Full rebuild ongoing; 15 existing board/touch/UI/HS tests PASS. No new boot
started or2316 hardware success claimed yet. No root/GPT changes.

2316 READY: full local CLT build and final incremental build exit0; actual
MT6363 init/thread/SPMI/HID symbols linked. Kernel16724112B SHA256
e25c06b017016cc9deb984fc8635f963ebd00bc5b3f20ae96116673608857269.
Code0117 shares locked PMIF, restricts new reads to SID4 0009/001e, checks
chip63 and fixes keypad16-bit registers stride4 (vendor source verified).
Also fixed0099 context to retain0094 files entry in clean patch replay;
4 new ASan/UBSan key/allowlist/dispatch/clean-build tests +15 existing tests
PASS. Current local key/SPMI sources match replayed patches (init comments
aligned; no functional delta). Actions remains disabled on fork; gh run list
last successful40127176212, no new CI run. Independent2316 image check PASS:
7073792B SHA256b43e18cd4d28480c7d731ffa676f45c5b1a7d1d35ae09b1af4f472a42ade9b80;
expected full written boot_a72fa34e30c41668e58b349e2e30e8839651591555c20a990088e00743fc8d88d.
ADT exactly matches working native2315; touch flags unchanged. Frozen8dc3bce
shim objects reused; old loader rebuilt byte-identically before changing only
its EMBEDDED_XNU_BYTES for the96B larger kernel payload. Stock ramdisk and
signature exact. Runner run-ui-2316.py prepared, NOT STARTED as of this entry;
never import it. Recovery online, stock boot_a independently verified.

0x2316 BOOT STARTED Unix1793405375.97475. Full written boot_a SHA256
72fa34e30c41668e58b349e2e30e8839651591555c20a990088e00743fc8d88d verified
before reboot. Code3210bda pushed to fork/codex/matisse-xnu-screen-log.
Runner session89729 monitors1200s and restores full stock boot_a on manual
FASTBOOT/Recovery return. boot-ui-2316-result.json restore_pending=true.
NEVER import/rerun run-ui-2316.py. Previous2315 success/restoration remains
verified. Need user's actual power/volup/voldown response, then fresh2316
console/marks and independent restored hash. No current key hardware success
claim. Root flashlight correction unchanged; no GPT/other partition edits.

2316 verification follow-up: exact final4 key/SPMI source files match full
patch replay. Independent image/payload/symbol checks PASS again;19 tests
PASS. gh workflow dispatch on50516f0 attempted and returned HTTP422:
"Actions has been disabled for this repository" (workflow metadata still
reports state=active, so metadata alone does not establish usable Actions).
No new CI run ID. Local full/final builds are the build evidence. User has
been asked to test short power/volume presses and touch on the running2316;
no reply received at this note. Original boot_a restore remains armed.

2316 USER OBSERVATION: “全屏触摸正常，但有按键无响应”. Native display and
touch remain user-confirmed; keys are NOT fully working. Asked which of
power/volume-up/volume-down fail and requested manual FASTBOOT after short
press tests for fresh log extraction and original boot restore. Runner
session89729 remains owner; no new image or speculative hardware change.

FINAL2316: user confirms all THREE buttons unresponsive; full-screen and
touch remain good. Manual FASTBOOT at189.31s, runner89729 exits0; stock
boot_a restored and independent Recovery hash2931647a...86b1, pending=false.
Fresh console67 HID touch records, no panic; key path still Qualcomm fallback
unsupported arbiter0x2. Root cause verified: actual inherited2315/2316 ADT
has NO /sweet-keys (despite current mkadt generator including it); linked
MT driver returns0 before PMIF. No MT key status/event exists this trial.
Prepared2317 reuses exact kernel2316, marks stay2316; append ONLY verified
/sweet-keys node344B to native2315 ADT. Removing it reconstructs old ADT
exactly. Command line changes only trial ID2317; loader size updated using
same frozen objects. mkpayload now rejects enabled matisse keys unless that
exact verified node is present; regression covers missing/malformed node.
2317 image7073792B SHA256a9e9a0ff876915e5d9258e451ee31967572bf435d0d10373e02366bcdcaeac4d.
Expected written boot_a189255571d7d196b49acb1fc8eaeeb6e6180aec06c00cd5e1468219afb982a66.
Independent image/payload/symbol/native-geometry check PASS. No2317 boot yet
as of this entry; run-ui-2317.py prepared, never import it. Root unchanged.

0x2317 BOOT STARTED Unix1793405748.363124. Trial ID2317, exact kernel
2316/marks2316. Full written boot_a readback verified SHA256
189255571d7d196b49acb1fc8eaeeb6e6180aec06c00cd5e1468219afb982a66.
Runner session55131 owns1200s monitor and full stock boot_a restore after
FASTBOOT/Recovery return. boot-ui-2317-result.json restore_pending=true;
never import/rerun run-ui-2317.py. Code379adbf pushed.20 tests PASS.
Need user power/volup/voldown behavior and retained full-screen/touch, then
fresh2317 logs; no key success claim yet. All prior boot_a restores verified.

MILESTONE2317: direct user reply “电源和两个音量键均正常，触摸正常”.
Native full-screen, touch response, power and both volume buttons are now
USER-CONFIRMED working on actual hardware. Exact working image is
matisse-ui-native-keys-2317.img SHA256
a9e9a0ff876915e5d9258e451ee31967572bf435d0d10373e02366bcdcaeac4d;
kernel2316 e25c06b0..., native1440x3200 ADT with verified/sweet-keys node.
Do not confuse2316 failure (missing ADT node) with this successful2317 trial.
Runner55131 still owns restoration; pending=true until FASTBOOT/Recovery
return and independent hash/log readback. Need archive final key events and
restore result. Success observation saved separately; runner owns resultJSON.

Earlier RUNNING/pending entries below are superseded by this handoff.

Read this handoff before the historical entries below. 0x230f returned to
FASTBOOT at759.79s after the user's requested return. Full64MiB original
boot_a restored and verified SHA2562931647a56039722ea2585990b8ef3b1a2daf4c9b990231879f753049eaf86b1;
boot-ui-230f-result.json restore_pending=false. User saw boot text updating;
UI is not confirmed. Watchdog after forced return is not a spontaneous crash.
October31 Recovery USB was initially absent, then reconnected by the user.
Live preflight reconfirms matisse/_a, stock boot_a hash and userdata size
114319917056B. No new device writes in this continuation yet.

Fresh230f marks/build ID and console were recovered under
research/matisse/20261027-userland/ui230f-*. DME_GET confirms TX/RX gear1,
one active lane each, PA_PWRMODE0x55 (SLOWAUTO/PWM), HS series1. Last snapshot
at707920ms:4792 reads/446234624B, prep20336us, hardware652093493us,
post19409us, errors0, sleeps0. Command throughput about0.65MiB/s, almost all
hardware wait; lock waiting is cumulative across callers. No fixed per-read
millisecond delay: pending polls delay1us, optional ufswait is off.

MAIR0x0c08044f00bb44ff is valid. All valid sampled kernel/DMA and user
header/PC/SP PTEs use index0=0xff Normal Inner/Outer WB. Cached32MiB memcpy
4081us is two512KiB regions repeatedly copied, not sustained DRAM bandwidth.
CRITICAL:230f SCTLR/PAR samples are INVALID. Darwin assembler treats ';' as
comment; actual kernel emits only MRS MAIR_EL1 then stores uninitialized
SCTLR/PAR outputs. Disassembly proves missing MRS SCTLR/AT/ISB/MRS PAR.
Do not infer caches disabled. Startup binary sets SCTLR0x3454593d (M/C/I).
Runtime SCTLR/TCR/PAR still need corrected newline-separated instructions.
CPU kprintf register records were not captured in persistent console.

0115/build0x2310 now implements corrected register sampling and opt-in
ufshs=1: HS Gear1/one lane/seriesA, separate power-mode completion,
HCS PWR_LOCAL and exact DME readbacks. It times the same1MiB READ(10) in
PWM/HS and exactly compares its first4KiB before allowing root writes.
Any transition/readback/data failure leaves the disk offline. Default is
unchanged without ufshs=1. Sampler lines bounded to240B to preserve newline.
Full local CLT build exit0, kernel16723920B SHA256
d8f1c7d126ca07932b268c1994d39c37de680fb136f15e1cd4d03ba69f5aa3c2.
Actual kernel disassembly at0xfffffe00074dccfc shows MAIR/SCTLR/TCR/MPIDR
reads then AT S1E1R, ISB, MRS PAR and IRQ restoration. Five targeted tests
PASS, including modeled HS completion/failure cases and ASan/UBSan.
Legacy ignored decode-perf.py now explicitly invalidates old SCTLR/PAR
and does not label missing PTEs as WB. Hardware trial still pending.
Artifacts go in research/matisse/20261031-hs/. Preserve the user's unrelated
dirty shim/build.sh, shim/shim.c, tools/sweet-marks.py and untracked0093.
Code committedccf9716 and pushed to fork/codex/matisse-xnu-screen-log.
gh workflow dispatch was attempted but returned HTTP422: Actions disabled
on Jinsens/ios-sweet. No new CI run ID; local full build and tests passed.
Verified ready image matisse-ui-hs-2310.img7069696B SHA256
335e5c99139e20770020b85cb378257768a360176904fc49b54bdb65caa92b6b,
stock ramdisk/signature and embedded gzip/Image/payload all match.
0x2310 BOOT STARTED Unix1793400280.713899; full written boot_a hash
cec6ec95337ad29466532cf893d249814f12f87cbb78d164d74d041588eb54a2.
boot-ui-2310-result.json restore_pending=true; runner is watching for1200s
and restores the entire original boot_a upon FASTBOOT/Recovery return.
Boot args equal230f plus ufshs=1; input/USB remain off. Need screen
observation and fresh2310 persistent logs. No HS/UI runtime claim yet.
Runner run-ui-2310.py has top-level flashing;
do not import it. Restore helper run-power.py remains safe to import.

logd_helper230f shared-cache slide0x0f2b8000, main header0x1043a8000.
t0 from467s pc0x1b5f3cbd4 is dyld4::Atlas::Image::ml()+232, a Mach-O
header load; stack is forEachSegment -> helper+0x5554 (return from
_dyld_image_for_each_segment_info) -> SharedCache::forEachImage ->
_dyld_shared_cache_for_each_image -> helper+0x5014 ->
forEachInstalledCacheWithSystemPath -> _dyld_for_each_installed_shared_cache.
This establishes cache-image harvesting, not its cause or an infinite loop.
Raw symbol/disassembly evidence in20261031-hs/helper-* and logd-helper-*.
Readonly pristine root was mounted at/tmp/ios-sweet-20H392-analysis (disk7)
for symbolication and detached afterwards. SpringBoard/backboardd remain before UI;
no GUI open/swap observed in230f. Current2310 result still pending.

0x2310 RETURNED FASTBOOT at393.12s after user's forced return, with Apple/
frozen/black screen choice. Original64MiB boot_a restored and full hash
2931647a...86b1 verified again live; result restore_pending=false.
Fresh41 marks identify2310; console is new (not stale). HS cap local/peer
gear4 and2lanes available. Requested HS G1/1lane/seriesA FAST verifies
PA_PWRMODE0x11 and all selected attrs. Same1MiB read PWM1519023us ->
HS8870us, exact first4KiB match, error0. Uptime345485ms totals:
R20674/1591185408B/hw17376214us, all-phase throughput86.52MiB/s;
W26464/1167171584B, errors0 for R/W/S. Baseline PWM read is included in
these cumulative totals. No fixed delay/read bottleneck remains demonstrated.
Corrected MMU v2: MPIDR0x81000100, MAIR0xc08044f00bb44ff,
SCTLR0x3454599d (M/C/I all1), TCR0x226511a511 (all walk policies1/WB),
DMA PAR0xff00000104f04b00 (success, Normal WB0xff). Valid sampled PTEs0.

Userland progressed materially: logd/logd_helper idle in worker waits;
backboardd opens AppleCLCD and IOCoreSurfaceRoot, creates BGRA surfaces2/3,
and submits swaps2..6 before the first105s sample. NO visible UI confirmed.
SpringBoard t0 now stable in _LSContextInitCommon's unfair-lock wait,
through LSApplicationRecord/ControlCenterServices initialization. Its t1
and a backboardd worker await NSXPC replies through
__LAUNCH_SERVICES_IS_RESEEDING_ITS_DATABASE_AND_MAY_BLOCK ->
_LSCopyServerStore. Backboardd main is in its normal CFRunLoop wait (not
proven deadlocked). Shared-cache slide0x1df88000. Focused symbols in
ui2310-focus-symbols.txt. Need sample lsd and its service dependencies next.
Need distinguish blocked UI services/rendering
from panel transfer. No further flashing until this evidence is understood.
Readonly pristine root remounted at/tmp/ios-sweet-20H392-analysis for this
second symbolication pass; detach when done.

0116/build2311 prepared next: unchanged validated HS mode, sampler names
SpringBoard,backboardd,lsd,installd,containermanagerd,runningboardd,
mobileactivationd,launchd. Adds periodic DSP transfer counters and optional
sweetfbshot=1: first3 presented framebuffer-RAM thumbnails80x178 grayscale
through existing persistent console. No new disk area/writer. These images
do not prove physical-panel output. tools/sweet-fbimage.py only emits
complete frames. Full local CLT build exit0,16724016B; seven targeted tests
PASS (ASan/UBSan actual present, DSI ordering, HS error cases, assembly,
resident sampling). No new CI; fork Actions remains disabled.
Kernel SHA2560abc76d94dfdace929bfb47d744d993039c35cefcf32327fc44251973b8162a2.
Code commit62250ce, pushed to fork. Image7069696B SHA256
641fb948bfb4f5a4e5b2d2a260c7d748c98347988d6c27756a610c5cfa244c4d;
stock sections and payload verified. 0x2311 BOOT STARTED Unix1793401275.321538,
full written boot_a hashd0908aefcb593d06b1a0eed161d70c09a7051751f573dbb290d524ffea65c9ce.
boot-ui-2311-result.json restore_pending=true; runner session79300 watches
1200s and restores on FASTBOOT/Recovery return. Never import run-ui-2311.py.
Need fresh2311 marks, lsd stacks and FBIMG thumbnails; no current UI claim.

0x2311 RETURNED FASTBOOT at243.02s after user's forced return; user saw
Apple/black screen. Runner restored original64MiB boot_a and result now
boot_a_restore_pending=false. Live Recovery readback independently matches
2931647a56039722ea2585990b8ef3b1a2daf4c9b990231879f753049eaf86b1.
Fresh marks identify2311; console244652B. Decoder recovered all3 complete
80x178 FBIMG frames2/3/4; visual inspection of2/4 shows white Apple logo
on black. This is actual framebuffer RAM content, not physical panel proof.
DSP counters fixed at calls134381/pushes208/busy_skips0 by first105s sample;
no later GUI presents were observed. HS reads1357123584B by225485ms,
R/W/S errors0; MMU v2 on MPIDR0x81000200 again confirms M/C/I, WB RAM.
Lsd102 sampled at105/165/225s with actual shared-cache slide0x1b02c000:
t0 performJournalRecovery -> dispatch_sync; t1 BuiltInAppInstallSessionID
-> MIInstallationIdentity -> libMobileGestalt -> semaphore_wait, unchanged;
t2 LSDatabaseBlockingFetchClient waits for seeding; t3 restoreInactiveInstalls
waits for a dispatch group. A MG worker runs CFRunLoopRunSpecific from
libMobileGestalt func_19c57c4dc. Full symbols in ui2311-lsd-symbols.txt/json.
Next: disassemble MG wait chain and identify the exact missing property/
notification before changing userland or registry. No lsd database mutation.
Readonly pristine root remains mounted for this analysis; detach when done.

MG disassembly establishes exact missing input: func_19c5716e8 reads
/chosen/mac-address-wifi0 then sdio/wlan/marconi-wifi before waiting for
IONetworkController in func_19c57c084. The trial ADT has none. The same
identity computation next needs Bluetooth; func_19c56883c directly reads
/chosen/mac-address-bluetooth0. tools/mkadt.py adds both6-byte locally
administered synthetic values, alongside existing synthetic ECID; no radio
support or userland/database mutation. Seven existing board tests PASS.
Prepared trial0x2312 REUSES EXACT kernel2311 (no kernel rebuild/new CI),
adds only2 ADT props (removing them reconstructs original ADT byte-for-byte)
and sweettrial=2312. Frozen shim source unchanged from2311/8dc3bce.
Image7069696B SHA25632552d4daf99fbf8b3038561d5c9ca1b56e8e80fe4d7bfbadacab122606d71ec;
stock ramdisk/signature, Image/payload, cmdline/ADT checks all PASS.
Expected full written boot_a SHA256cb42a503c14b9bb5165205f0a0f528753d2d568bd9764266c54bae422a4a5fb2.
Runner run-ui-2312.py is prepared but NOT STARTED here; never import it.

Identity correction committeddd5a8d9; trial0x2312 BOOT STARTED
Unix1793402082.485483. Resultboot-ui-2312-result.json has
boot_a_restore_pending=true; runner session14598 watches1200s and restores
stock on FASTBOOT/Recovery return. Fresh logs must contain sweettrial=2312;
kernel marks intentionally remain2311 because the kernel is identical.
No runtime claim yet. Readonly analysis root remains mounted.

Trial0x2312 RETURNED FASTBOOT at208.11s after requested forced return.
User initially reported black, later text/Apple. Original64MiB boot_a
restored and independently rechecked SHA2562931647a...86b1 in Recovery;
restore_pending=false. Fresh console has sweettrial=2312; marks intentionally
remain2311. The ADT identity correction WORKED for the observed blocker:
lsd100 main now ordinary CFRunLoop, no MG/seeding worker; installd178 now
executes and idles in CFRunLoop; runningboardd's LS sync wait gone.
SpringBoard advances to a different sync XPC call by105/165s; full symbols
are being recovered using actual slide0x289cc000. Visible UI not confirmed.
First3 framebuffer shots remain Apple logo. DSP counters214 pushes fixed
by105s. R/W/S errors0; PA_PWRMODE0x11, corrected MMU still M/C/I and WB.
Next: identify SpringBoard's new synchronous service dependency. No root
filesystem/database edits were made by the host.

2312 focus symbols complete: SpringBoard t0 at105/165s in
FigFlashlightRemoteCreate -> flashlightRemote_ensureClientEstablished ->
FigXPCRemoteClientCreate -> FigXPCConnectionSendSyncMessageCreatingReply.
Actual disassembly names com.apple.coremedia.flashlight, owned by mediaserverd
in the stock job. Need sample mediaserverd before changing config. Existing
root StartRecorderServer=false is a prior GPU-crash workaround; whether it
also suppresses the flashlight service is unproven. Trial2313 is preparing
with identical2311 kernel/2312 ADT and only sampler cmdline changed. Includes
mediaserverd, containermanager, mobileactivation (proc_name uses16-byte
p_comm, so original full long names did not match). No next boot started.

2313 image ready: kernel2311 and ADT2312 hashes unchanged; stock sections
and embedded payload verified. Image7069696B SHA256
e527e28648911d26db4e3457fc895fbc3d7c72817d6e824d52e1c8d41a6cedfe; expected full written hash
30567ce223a60392919f0a808ec2efb784c0b31153cd310d6aa1bcb02f264be1. No kernel source/build/CI change.

Trial0x2313 BOOT STARTED Unix1793402549.9406872; full written
boot_a hash30567ce223a60392919f0a808ec2efb784c0b31153cd310d6aa1bcb02f264be1.
Runner session58786 watches1200s; restore_pending=true. Do not import runner.
Need fresh sweettrial=2313 console, mediaserverd sample and stock restore.

## Historical 2026-10-27 userland installation and trials

User request: bring the online device through real iOS userland into UI.
User explicitly authorized partition/flashing operations in this session
("你可以进行分区表操作，还有刷入操作") and waived userdata backup
("不需要备份 user data"). Plan uses existing userdata without GPT changes;
keep bootloaders, recovery, modem/persist and existing backups intact.
This authorization covers this userland installation and its boot trials.

Observed preflight: root ADB Recovery, matisse, slot _a; userdata
114319917056 B. Full boot_a hash matches backup:
2931647a56039722ea2585990b8ef3b1a2daf4c9b990231879f753049eaf86b1.
Existing userdata is the 64 MiB HFS test root, not the old sweet UI image.
Downloads/iPhone10,3,iPhone10,6_16.7.16_20H392_Restore.ipsw contains
20H392/16.7.16, D22AP/D221AP; all three disk images and D22AP DT extracted
with ZIP CRC verification under research/matisse/20261027-userland/ipsw/.
OS SHA256 80f426d5b8fca8552f95be427434f1911dbb4c2c6d28aad94f2426ddd0c92483;
SystemOS 9cd738f3b0169055549df84ad6d8d13e50a2da39af618ce0522ca4e06df86849;
AppOS 391f2df322c3172b021b2874f6da5c3e78b70b3df8f502e1a4af2b1d715c4608.
The known-good matisse-dual ADT lacked /product: added real unflagged D22AP
properties in local matisse-userland.adt; hardware geometry unchanged.

Native macOS root repack via tools/mkiosroot-macos.py completed:
16 GiB raw journaled case-sensitive HFSX, preserving numeric IDs as root.
macOS administrator authentication succeeded; no password was shared.
Root build log: research/matisse/20261027-userland/build-root.log.
Device writes are recorded below; no UI claim. First trial uses
0x230c (built on the verified0x230b source), ufsrw=1/rootrw=1 and real launchd/dyld boot args,
serial=3/ufslogsecs=1, input/USB disabled initially. mkpayload now has an
explicit --allow-matisse-root-write opt-in; read-only remains its default.
Seven board-profile tests passed (including write opt-in checks).
User's existing shim/build.sh, shim/shim.c, tools/sweet-marks.py and untracked
0093 patch are retained separately. Frozen tracked shim excludes --kick edits.
No new CI run; using the previously hardware-tested 0x230b kernel.

Milestone: native copy/tweaks completed. The builder's final fsck call on a
regular file failed (macOS requires a block device); no data-copy failure.
Separate readonly /dev/rdisk5 fsck_hfs -fn reported iOSRoot appears OK,
followed by readonly mounted verification of all four executable owners,
modes/content and arm64 shared-cache hardlinks. root-verify.json records
this recovery; tools/mkiosroot-macos.py now checks an attached block device.
No mobileactivationd system container existed in the source, so the optional
data ark seed was skipped; native activation status remains to be observed.

0x230c changes (0111): AppleCLCD always presents 1125x2436 unless native is
requested, centering on larger panels and clearing the margins on first
present. HID converts the board drivers' normalized 1080x2400 input to the
same physical/centered viewport and clamps margin contacts. Previous code
fell back to native 1440x3200 on matisse. Complete local CLT build exit0;
kernel 16723464 B SHA256
59d0d777e22863a7d06b3e00673aeb8c7709f831e42a70b971d84ba2b4ef5164.
Actual present() and HID mapping statements compiled into a host harness
with ASan+UBSan: 1080x2400, 1440x3200, native1440x3200 and1125x2436 all PASS,
including per-pixel destination verification and normalized input bounds.
Logs: build-kernel-230c.log and test-canvas.log under the userland directory.

Userdata installation COMPLETE and readback_matches=true:16GiB raw root,
gzip over adb shell -T to dd, write223.86s, whole operation249.47s.
Local and full on-device installed-range SHA256 both
361cf02f1f2e8b9b710d45270397fda818e39c3f68d2d89911b345b6a6c1c043.
No GPT changes or userdata backup. Existing diagnostic tail is preserved.
0x230c v4 boot image7065600B SHA256
1a9f6bbc6aec439a0fae66516cf5bc84e7f6767c26887fcdc9c121fc180ee81b;
stock ramdisk/signature and gzip/Image/payload length/content verified.
Boot cmdline: research/matisse/20261027-userland/userland-cmdline.txt.
Boot trial and stock restoration are prepared in run-userland.py.
0x230c trial observed real Apple userland: photo IMG20261027025320.jpg and
persistent console confirm launchd, SpringBoard PID26 and backboardd PID56.
UI has NOT appeared. There is no AppleCLCD userspace-open trace or swap yet.
Sample2..7 captured both daemons' stacks; these need symbolication before
attributing the blocker. CPU-wake resource exception errors are not a proven
cause. The runner's SystemExit(0) is its600s no-USB timeout, not a kernel crash.
User returned phone to FASTBOOT; product=matisse verified. Full64MiB original
boot_a was flashed with fbraw, rebooted Recovery, readback SHA256 verified:
2931647a56039722ea2585990b8ef3b1a2daf4c9b990231879f753049eaf86b1.
boot-userland-result.json now has boot_a_restore_pending=false.
Persistent log recovered: userland-console.txt,49747B, ring4MiB,flush122;
marks41,build0x230c, launchd exec success. Recovery bootreason=Watchdog after
user's forced return; do not attribute that reason to a spontaneous XNU reset.
Prepared but NOT BOOTED: matisse-ui-touch-230c.img7065600B, SHA256
11dff09b884af56054cdee93ebe2fbe64f2dff367aaa450df729d6577c99c261.
Same0x230c kernel, touch=1/init=1/rails=1/mark=1/delay3, no diagnostic hold;
stock ramdisk/signature and embedded payload checks pass. This is for the
next UI/input trial only after the baseline boot result is understood.
Detached root fsck was explicitly rerun with returncode0: fsck-final.log.
Commits:057f331 native root tooling;8f98ccc canvas/HID+fsck fix;
400abc8 verified root installation;30c142c first boot handoff.

Symbolication complete: research/host-tools/ipsw-3.1.739/ipsw (official
release checksum7121fce3...3c0e), mounted20H392 cache and userland-symbols.txt.
Backboardd samples5..7: mach_msg2_trap <- firehose_send_register <-
firehose_client_reconnect <- os_trace_init_slow <- BKLogCommon <- main.
Its send to logd has not completed. SpringBoard samples2..7 move through
dyld notifyDtrace/ObjC map_images/load_categories (still pre-main); this is
progress, not evidence of one unchanged lockup. No GUI swaps recorded.
Pulled current16GiB filesystem for diagnostics (334.68s over gzip6,006,002,291B).
fsck_hfs -fn reports volume appears OK; dirty journal needed a local shadow
mount, which replayed successfully. No device root writes during diagnosis.
logd.0.log shows UUID harvesting at~8min, two errno2 assertions at+90880;
Persist/HighVolume empty; incomplete5.6MiB uuidtext/dsc temp file, no .ips.
Copied local logs to after230c-*.log. No proven logd root cause yet.

0112 / build0x230d fixes a separate confirmed source omission: GUI present()
and display fade must call sweet_display_refresh(1) on the command panel;
old code refreshed only from console, which is muted at first GUI swap.
Adds C++ C-linkage declarations and configurable sampler timing + uptime.
Full local CLT build exit0. Kernel16723464B SHA256
8d6ef2f83cd3b042238a263ab3fd988d2de6a923083ea9a34028572db6584bfe.
2 targeted tests PASS: actual patched present under ASan+UBSan validates
all pixels and copy-before-transfer across four geometries/two frames;
existing DSI bounded-busy/pipeline-order test also passes.
Image matisse-ui-diagnostic-230d.img7065600B SHA256
cbe88a85d866e5fd3422a930419e29051e888e1f58c2d2f84bc6c9e6b2109b45.
Stock v4 ramdisk/signature and gzip Image/payload length/content verified.
0112 implementation/test commit9b6c6d6; prior restored-userland handoff3ad8269.
0x230d BOOT STARTED (Unix1793042090.959381); full boot_a write hash verified
as ec6631103dfe02705bf84121806877d0ff60d2a3f83e15a4b77d1d987cb6d0f9.
boot-ui-230d-result.json records boot_a_restore_pending=true. run-ui-230d.py
is watching for1200s and restores via fbraw on FASTBOOT/Recovery return.
If it times out without USB, manually reuse powertrial.restore() then pull
ui230d-* logs (never import top-level run-ui-230d.py).
Root unchanged; touch/keys/USB remain disabled; trial samples
SpringBoard/backboardd/logd/launchd/notifyd every60s.

0x230d returned FASTBOOT after772.46s; runner restored the complete64MiB
original boot_a and verified2931647a56039722ea2585990b8ef3b1a2daf4c9b990231879f753049eaf86b1.
boot-ui-230d-result.json has boot_a_restore_pending=false. Recovery is online.
Recovered ui230d-console.txt:45848B, flush120,41 marks/build0x230d, launchd
exec success. No GUI open/swap trace. User last saw boot text updating.
Return bootreason=Watchdog; whether forced by user is not established.
Symbolicated74 cache addresses with actual slide0x49004000 in
ui230d-symbols.txt. logd main AND harvest queue await synchronous replies
from logd_helper (logd+0x9b78, migration op6 for directory3, and UUID
harvest op1). backboardd samples4/5 await firehose registration. SpringBoard
continues through pre-main dyld/ObjC. launchd has threads in sync()/write().
The reason logd_helper is slow/blocked remains open; previous samples did
not include it. No new filesystem writes or reflash in this recovery.

User now requests a concrete audit of shim MAIR/PTE attributes, XNU
arm_vm_init/user mappings and per-read UFS delays. Inspect actual0x230d
local build tree/frozen shim, then instrument actual attributes and I/O
phase timings as needed before choosing an optimization. Keep hardware
observations separate from source-only findings. Native activation and
UI/input are still unverified. No new CI run; full local CLT build and2
targeted tests passed for0x230d.

0x230e diagnostic milestone (not booted yet): source audit found no global
kernel/user RAM NC/Device mapping and no fixed millisecond delay per UFS
read. The normal embedded XNU shim path jumps with MMU/caches OFF; shim's
mmu_enable diagnostic mapping is not inherited. XNU expects MAIR
0x0c08044f00bb44ff, default managed RAM index0=0xff, M/C/I enabled and
Inner/Outer WB page-table walks. UFS completion polls delay(1us); optional
50us-spin/200us-sleep mode is absent from0x230d. Gear is not yet observed.
Report: docs/matisse-mmu-ufs-audit.md. Added opt-in sweetperf register/PTE,
memcpy, UFS phase/mutex/copy timing and readonly negotiated-link diagnostics.
Sampler no longer holds task_lock across faulting vm_map_read_user; resident
managed WB copies only, protected by pmap/PVH locks. Host ASan+UBSan test PASS;
0113 applies cleanly to saved pre-230e sources. Final full CLT build exit0,
kernel16723824B SHA256946f623065a621e1de3d892579e506599ec781fae78879a9c6bca7f18d8f76a8.
No new CI run. cmdline428 bytes adds sweetperf=1 and logd_helper sampling.
Current device still Recovery; original boot_a restored/verified as above.
User also points to Documents/{lk,vcp,dtbo}.img for readonly display audit.
Next: verified230e image trial, actual MMU/UFS evidence, restore boot_a.

0x230e BOOT STARTED (Unix1793044393.947674); diagnostics commit9230192.
Image matisse-ui-perf-230e.img7069696B SHA256f3598b81dd61fcfb1b173bac8e30f76226640a810b1a7d2d11185969804b9c87.
Stock ramdisk/signature, gzip/Image size, aligned SWEETAPP payload length and
content all verified. Full boot_a written hashbf5a7a9362a697e118ee630fc9ec2b3b50b7709b3879c4503c18487e143ff935.
boot-ui-230e-result.json has boot_a_restore_pending=true. Runner session14609
watches1200s and restores original via fbraw on FASTBOOT/Recovery return.
Do NOT import run-ui-230e.py (top-level flashes). If host USB stays absent,
request screen observation and user return to FASTBOOT, then restore/pull.
0x230e samples logd_helper too; sweetperf=1; touch/keys/USB still off.
No new userdata installation or partition-table changes. Runtime evidence
and original boot_a restoration are still pending; no UI success claim.

0x230e trial finished after247.41s when the user returned FASTBOOT because
screen showed Apple/frozen/black (the combined choice; exact image unknown).
Full original64MiB boot_a restored and SHA2562931647a...86b1 verified;
boot-ui-230e-result.json restore_pending=false. Recovery online. Marks and
console are byte-identical to230d (build230d,41 marks); NO230e runtime
performance evidence was produced. Do not relabel these stale logs as230e.
No new build mark means failure before the mark channel becomes live;
exact PC/panic cause unknown. Source review found added IOLog in CPU init
runs at splsched/IRQs disabled, while _IOLogv asserts interrupts enabled
when CPUs are running (IOLib.cpp1590). This is a concrete context violation,
but there is no captured230e panic proving it was the sole cause.
0114/build230f replaces it with existing-safe kprintf and defers all optional
PTE/AT/memcpy/DME probes to the first background performance snapshot after
persistent logging is active. Bounce benchmark holds sweet_ufs_lock; prints
happen outside it. No link mode/gear changes. Patch dry-apply and resident
sampler ASan/UBSan test PASS; final CLT build in progress. User's display
references readonly audit: DTBO and live DT both l11_38_0a_0a_dsc_cmd,lcm;
LK contains matching driver and display addresses agree. VCP identified as
tinysys-vcp-RV55_A; no new display dependency proven. Raw evidence saved in
display-reference-audit.json and {lk,vcp}-display-strings.txt (ignored).

0x230f full CLT build exit0; kernel16723880B SHA2563ccc1849d8e421e0f01d79a99e17461de6d985c94fc4288090529c948e4b02f3.
No new CI run. 0114 applies cleanly; sampler sanitizer test passes.

0x230f BOOT STARTED (Unix1793044977.1065621); source commit7ccc630.
Image7069696B SHA256b82ff566cf49c32a07f17a3d35ef0d2dd6746bc52b194eaee90a9db48ffebe2b; full written boot_a
SHA2563dd1fcc199b10e21310a247a36dbd3058adfb3b509a729bab3478f5469bb3302. Stock sections and embedded payload
verified. boot-ui-230f-result.json restore_pending=true; runner session39967
watches1200s and restores on return. Do NOT import its top-level runner.
Need screen observation, fresh230f marks/MMU/UFS evidence, then verify
restoration. The230e logs are stale230d and must not be used as230e results.

## >>> ACTIVE 2026-10-27 (touch): 0x230b receives real SALIXP touch events; boot_a restored and verified <<<

**Read this before the older entries below: the old PMIC voltage / VTP-LP
conclusions are invalidated by a confirmed PMIF command-addressing bug.**
Recovery chip ID `36 40`, FW `0x0020`, cfg `0x001b`, ICR `0x42` confirm
ST FTS/FTM5 SALIXP (commercial package part number not read).
User's `Documents/dtbo.img` matches live FDT: SPI6 CS0 12 MHz,
GPIO3 reset / GPIO8 IRQ, st_fts_L11.ftb, VRF18_AIF 1.8 V / VTP 3.3 V.

Old sweet_spmi.c used `PMIF_CMD_REG=1` (5-bit address) with 16-bit addresses.
Vendor source and Recovery module disassembly require type3 EXT_REG_LONG:
SID5 0x1d23 read must be `0xc5001d23`. Therefore old readbacks, noop-write
success, claimed rail voltages, upper-nibble mode theory and attributing
watchdog resets to the physical VTP LP transition are **not established**.
The wrong opcode is certain; where old writes landed / whether this explains
all reset events remains unknown. Preserve historical raw results, not their
old electrical interpretation. See `docs/matisse-touch-report.md`.

Code commits: audit `b000e85`, guarded touch supply startup `998bf3b`;
hardware outcome report `8c73962`, prior handoff `c0869aa` (2026-10-27).
Both 0x230a and 0x230b were booted
with separate explicit user authorization and restored afterwards.

**0x230b succeeded at kernel touch input:** ID36:40, Ready, A5/01 System
Info (FW0020/cfg001b), Sense On err0, then 19 down +19 up records, finger0.
Six down/up pairs have different scaled positions, demonstrating motion
handling. The driver calls the existing SweetHID path at1080x2400 logical
coordinates. iOS UI interaction, multitouch and sustained stability are
not yet verified. After87.86s the host saw fastboot; Recovery reports
Watchdog. No hold-end mark102 or init-failure mark64 was captured, so do
not attribute this reset to missing launchd or a particular PMIC operation.

Completed changes for this milestone:
- 0106 restores the missing local diagnostic baseline for existing 0108.
- 0109 fixes PMIF reads, removes touch power-write trials and makes
  sweet_spmi_write return failure without MMIO. `sweetpmicaudit=1` reads
  SID5 0009/1bbf/1d23/1e8d/1e35 eight times before mountroot (mark201).
- Optional `sweettouchinit=1`: correct FA 20 00 00 24 81 reset -> Ready03
  <=100ms -> valid A5/01 System Info + FW -> A0 00 01 Sense On.
  The 0x230a audit used init=0; 0x230b used init=1.
  87 is FIFO read, not flush. Fix bitbang short-RX
  debug overread; release contacts after Ready/error. Marks202-204 added.
- Sync SWEET_MARK_MAX=160 and build ID 0x230a. Three new mock tests passed.

Full local CLT XNU build exit0, kernel 16723304 B SHA256
`099fce838614cf3a9e0dc64f1b0492482b5ff5aef91cd8521b38d926565be6e9`.
NDK28.2 shim built from frozen tracked HEAD 4910067 (excludes existing user
--kick edits). boot v4 image 7061504 B SHA256
`20a5c23bdde95a90da47d57425a0703d26e53c897bd63618c48a56aa49dae412`.
Stock ramdisk/signature, gzip/Image size, embedded payload length/content
all verified. Existing untracked 0093 is in the local kernel; keep it separate.
No new CI run. Artifacts, exact cmdline, verifiers, build/test logs and raw
read-only Recovery evidence: `research/matisse/20261027-ic-diagnosis/`.

User explicitly approved boot testing on 2026-10-27: “可以启动测试”.
`run-audit.py --execute-approved` completed and restored full boot_a. Preflight: Recovery/matisse/_a, boot_a matches full backup SHA256
`2931647a56039722ea2585990b8ef3b1a2daf4c9b990231879f753049eaf86b1`.
Hardware result: 57 new marks, build0x230a. All eight mark201 reads matched,
err=0, ID=73, VRF18_EN=00, VTP_EN=00, VRF18_SEL=0c, VTP_SEL=04.
This invalidates the old XNU EN=03/selector-high-nibble interpretations.
Mark96: SPI err=0, ID=00:00. The worker ran at3s and the full30s hold ended;
marks reached init candidates ENOENT and mark64 (missing launchd).
After135.47s the host saw fastboot; fbraw flashed the complete64MiB backup
and rebooted Recovery. Restored hash is the same2931647a...86b1 above.
Recovery reports Watchdog; do not attribute it to a PMIC write (there were
none). No SWEETLOG header was found; marks are the valid evidence.
Seven targeted tests pass (3 hardware mocks +4 mark decoder checks); fixed
an old test's count97 rejection to count161 for the160-record format.
0110 (commit `998bf3b`) was built and booted as0x230b: strict cold
snapshot73/00/00/0c/04 guard; set selectors while disabled; enable VDD then
AVDD; verify73/01/01/0c/0d before releasing reset. Dedicated API allows only
four fixed field targets, preserves other bits, verifies each write, and
refuses an enabled rail's selector change. General write API stays blocked.
Nine targeted tests pass (5 hardware mocks +4 mark checks).
Final local CLT build exit0. Frozen NDK28.2 shim uses b000e85. Artifacts:
`research/matisse/20261027-ic-diagnosis/power-230b/`.
- Kernel 16723464 B SHA256
  `8b3a9cdda5f7aa7bf3b936ffeea826b22e18c6a14156cd78ea88b7e033b56c76`.
- Image `matisse-xnu-230b-touch-power.img`, 7065600 B SHA256
  `a9e52c55d08c6d5896694942eb39a36ff5f7f7f7481d152eae229f55d47f8336`.
- v4 / stock ramdisk + signature / gzip / embedded payload checks pass.
- Cmdline uses audit=1, sweettouchrails=1, sweettouchinit=1, 30s hold;
  keys/battery/USB off. Marks205 cold guard,206 each config,207 powered
  guard,208 reset release, then96 ID,202/203/204 Ready/info/Sense On.
- User authorized0x230b: “你可以刷入并测试”.
  `run-power.py --execute-approved` completed, exit0, and restored the full
  64MiB boot_a backup via fbraw. Preflight and final on-device SHA256 both
  equal `2931647a56039722ea2585990b8ef3b1a2daf4c9b990231879f753049eaf86b1`.
- 99 new marks, build0x230b: all four mark206 supply operations err0;
  mark207 verifies73/01/01/0c/0d; mark208 reset release err0; mark96 ID3640;
  mark202 Ready=1; mark203 FW0020/cfg001b/A501; mark204 Sense On err0.
- 19 down /19 up records (97/98), finger0. Raw down X3845..9995,
  Y12425..19655; six pairs changed position after scaling. Evidence:
  `power-after-marks.bin` / `.txt`, `power-result.json`, `touch-summary.json`.
- No SWEETLOG console header. Mark84 here is normal display telemetry;
  its presence alone is not panic evidence. The Watchdog cause is open.
- Recovery/matisse/_a is online after restore. A fresh read again returned
  `{ 000000003640 }`; a final read-only boot_a hash check matched the backup.
  Both trials used the existing userdata-tail diagnostic record area.

Next concrete work: investigate the Watchdog and incomplete30s hold using
the retained marks, scheduler/watchdog code and console capture path; then
prepare a focused stability trial with explicit user authorization for any
new destructive step. Do not repeat the completed0x230b trial merely to
prove touch input again. UI/multitouch validation remains separate work.
No new CI run; complete CLT build and9 targeted tests passed for0x230b.

LK/VCP were statically inspected, not modified. LK known LDO helper xrefs
use other rails (1b87/1e29/1cce); no confirmed VTP init path found yet.
VCP is tinysys-vcp-RV55_A. File hashes and details are in the report.

## >>> ACTIVE 2026-10-27 (matisse touch): 0117/0118 VTP mode trials both reset the SoC <<<

The device was in OrangeFox Recovery (`matisse`, slot `_a`) before and after both temporary `boot_a` tests. The full
backup was restored after each test and verified as
`2931647a56039722ea2585990b8ef3b1a2daf4c9b990231879f753049eaf86b1`.

**0117, image `373985c383abf8e220687500526937bde558fcfa1cf342f207f85b53d9926770`.**
The early hook wrote the vendor-looking unlock bytes (`0x142a=0x43`,
`0x142b=0x55`) and mark 199 recorded `err=0`. The following full-byte write
`0x1d23=0x01` returned `err=0` (mark 195), then the SoC stopped before marks
198/196. Marks were recovered after boot: the last record is 195.

**0118, image `850e1c534ca051c3a82ca91ecd3417586a4a25280a6ae4e90ae893c681a0f6d`.**
The write was changed to the vendor `regmap_update_bits` shape: read
`0x1d23=0x03`, preserve all other bits, clear only bit 1, and write `0x01`.
Mark 200 recorded `old=0x03 new=0x01`; mark 195 again recorded `err=0`, and
the boot stopped immediately afterward. Recovery reported
`ro.boot.bootreason=Watchdog`; no XNU panic record was produced. This proves
the reset is triggered by the physical VTP mode transition, not by the
unlock-key sequence or by replacing the full-byte write with read-modify-write.

Artifacts are under `research/matisse/20261026-vtpunlock/` and
`research/matisse/20261027-vtprmw/`; 0118 marks are saved as
`vtprmw-after-marks.txt`. Do not perform another `0x1d23` write in XNU.
The next useful work is read-only board-level evidence: measure VTP/touch
connector voltage or identify the bootloader's PMIC initialization path. The
working Recovery state remains the reference (`0x1d23=0x01`, `0x1e35=0x0d`).

## >>> ACTIVE 2026-10-26 13:40 (matisse touch): VRF18 is now really on, VTP is the wall <<<

Three boot_v4 shim images were built with the local CLT toolchain and run
(boot_a written, restored, hash verified after each: `2931647a...86b1`).

**0108 (`sweetvrf=1 sweetidprobe=1`, image `f9421f03...`) - what it ruled out.**
Marks 183/194/195/155 show the rail writes: `0x1e8d` read 0x70 at boot, ramped
to 0x7c, `0x1bbf` 0x00 -> 0x01, no reset. Mark 154 (`a=1` = hi 0, lo 1) shows
INT still low, and 157/158 show a hand-clocked 0x81 + two chip-ID reads at
~500 kHz returning all zero. So with VRF18 nominally enabled the controller
still looks unpowered.

**The vsel byte carries a second field.** XNU reads `0x1e8d = 0x70` and
`0x1e35 = 0x74/0x75`; Recovery reads `0x0c` / `0x0d`. Bits 4..6 stay set under
the bootloader and are cleared by the vendor path. Comparing every MT6373 LDO
in the Recovery dump shows disabled rails keep plain small selectors (VRF13
0x07, VRF12 0x03, VFP 0x04), so 0x40 is not a plain "disabled" flag - it is a
mode/range field that the vendor clears when it programs the rail.

**0109 (`sweetvpower=1`, energise from the bottom: `0x1e8d` 0 -> 12, then
`0x1bbf=1`, then `0x1e35` 0 -> 13, then `0x1d23=1`) - the SoC reset.** Marks
stop right after 174 (`0x1e8d` reached 0x0c, "ENRI"): no 175, no 184. So the
fatal step is the VTP sequence, and switching VTP's field at 1.2 V is already
enough to take the SoC down.

**0109a (`sweetvpower=1`, VRF18 only) - survived, still silent.** 174 reached
0x0c, 159 shows `0x1bbf` readback 0x01, the boot went all the way to
`load_init_program` and panicked on the missing launchd. INT still 0 (mark
154), bit-bang ID still 00 (157/158). **This is the first XNU boot where
VRF18_AIF is genuinely at 1.8 V with the mode bits cleared, and the chip does
not answer.**

**0109b (`sweetvpower=3`, VTP ramped inside the bootloader's mode,
0x75 -> 0x7d) - survived, still silent.** 175 "KEEP" at sel 13, 152 reads back
`vrf=0x0c/en=1`, `vtp=0x7d/en=3`. INT 0, bit-bang ID 00 again. So raising the
VTP selector without touching the mode bits changes nothing the chip can see,
while forcing the mode change (0x0d) resets the SoC.

**Where this leaves it.** VRF18's I/O rail is now provably correct, so the
remaining single fault is VTP: the controller needs avdd at 3.3 V, the 3.3 V
setting is a mode change in `0x1e35`, and that mode change resets the SoC even
when it is made at the bottom of the table with reset held low. Because VTP's
only device-tree consumer is `spi6.0-avdd`, the reset is not a normal load
brownout; the two remaining explanations are (a) the touch panel's own
capacitance inrush when the rail finally comes up, and (b) a PMIC protection
event that the vendor kernel handles and XNU does not.

**Next options, in order of information per risk.**
1. Measure VTP (and the touch connector's VDDI) with a meter while an XNU
   image runs - that settles whether 0x7d is 1.8 V or 3.3 V and whether the
   mode change is even needed.
2. Retry the `0x0d` switch with `cpus=1` and the write moved to the earliest
   hook, to cut VSYS load during the surge (cheap, but the same reset is
   likely).
3. Find the vendor's LK PMIC init (or a schematic) for VTP: if LK can leave
   VTP at 0x0d, XNU never has to touch it.

Artifacts: `research/matisse/20261026-idprobe/` (0108),
`research/matisse/20261026-vpower/` (0109, 0109a, 0109b) with payloads,
images, `*.json` hashes and the verifier used for each. New marks 152, 159,
173-175 are decoded by `tools/sweet-marks.py`.

## >>> ACTIVE 2026-10-26 12:55 (matisse touch, 0108): rail map proven from the stock module, VRF/INT/bit-bang probe built - NOT FLASHED <<<

**Request (user): "/Users/xiaohuasheng/Documents/twrp 有设备树 现在再继续帮我移植触摸功能".**
The tree at `Documents/twrp/device_xiaomi_matisse-TWRP` is TWRP/OrangeFox for
matisse with `TARGET_NO_KERNEL` and a prebuilt `prebuilt/dtb`; it carries no
kernel source, so the useful material was the stock **vendor_boot ramdisk**,
which is on this Mac at `Documents/twrp/stock-vendor_boot_a.img`.

**Device tree facts (measured).** `prebuilt/dtb` is an MTK `dt_table` with one
FDT at offset 64. It has `/spi6@11016000` (`mediatek,pad-select = <1>`, IRQ
0xf1, clocks 0x19/0x3f/0x19/0x95/0x3/0x13) but **no touch child**: the board
touch node comes from the DTB overlay in the stock ramdisk. The live Recovery
DTB has it at `/spi6@11016000/fts@0` (`st,spi`): `spi-max-frequency = 12 MHz`,
`fts,reset-gpio = <&pio 3 0>` (+ `fts,reset-gpio-enable`), `fts,irq-gpio =
<&pio 8 0>`, `fts,irq-flags = 0x2008` (level low + oneshot), `vdd-supply =
VRF18_AIF`, `avdd-supply = VTP`, fw `st_fts_L11.ftb`. Its three pinctrl states
(`pmx_ts_active`, `pmx_ts_suspend`, `pmx_ts_spi_mode`) resolve to **empty
nodes**, i.e. the vendor kernel does not program those pads at all - LK does.

**The modules answer the power question.** `stock-vendor_boot_a.img` is header
v4: ramdisk 44,333,100 B LZ4 at 0x1000, `dtb` (25 MB dt_table) after it. The
ramdisk inflates to 89,466,112 B and holds `lib/modules/mt6373-regulator.ko`,
`fts_touch_spi.ko`, `xiaomi_touch.ko`, `pinctrl-mt6373.ko` (symbols not
stripped). From `mt6373-regulator.ko`'s descriptor table (stride 0x220):

| rail | desc | vsel_reg | vsel_mask | enable_reg | enable value | table |
|---|---|---|---|---|---|---|
| VRF18_AIF | @.data 0x1910 | `0x1e8d` | `0xf` | `0x1bbf` | `0x01` | `ldo_volt_table3[12] = 1800 mV` |
| VTP | @.data 0x2960 | `0x1e35` | `0xf` | `0x1d23` | `0x01` | `ldo_volt_table1[13] = 3300 mV` |

So 0x1bbf/0x1d23/0x1e8d/0x1e35 **is** the right mapping (previously inferred),
and "enable" writes the literal value `0x01`, which clears VTP's LP bit as a
side effect. `st_spi_ctrdata` = {0, 300, 30} (setup/hold), `fts_system_reset`
sends one byte `0x81` - both already match the port.

**Golden runtime state from Recovery (read-only, adb root).**
`regulator_summary`: `mt6373_vrf18_aif` enabled 1800 mV normal, `mt6373_vtp`
enabled **3300 mV normal**, and each has exactly **one** consumer -
`spi6.0-vdd` / `spi6.0-avdd`. Nothing else on the SoC shares those rails, so
the boots that died on a rail write were **not** a load brownout; the write
sequence/PMIF path is what needs fixing, not the voltage.
`clk_summary`: spi_sel 208 MHz, spi6_bclk 208 MHz, spi6_hclk 156 MHz (all
runtime-suspended at idle). `pinconf-pins`: 164 PD, **165 PU**, 166/167 PD,
7 mA, mux func2; GPIO3 out hi (bias PD); **GPIO8 in hi, bias disabled, input
enabled**. `gpio`: `gpio-270 (fts_gpio_270) out hi`, `gpio-275 (fts_gpio_275)
in hi IRQ`.

**Port bug found while reading this back.** The XNU driver never muxes GPIO8
to GPIO function 0; LK leaves that pad in whatever mode it uses, and a pad
that is still routed to another block reads 0 in the GPIO DIN register no
matter what the chip does. Every previous "INT stays low, therefore the chip
is dead" observation is therefore **not evidence**. Fix is in 0108.

**Change 0108.** `sweetvrf=1` runs a new `mt_vrf_enable_only()` in the
pre-mount hook: it ramps `0x1e8d` to selector 12 **while VRF18 is still
disabled**, sets `0x1bbf = 1`, waits 20 ms and re-reads all four registers
(VTP untouched). `sweetidprobe=1` runs `mt_id_probe()` in the worker: GPIO8 ->
function 0 + DIR in + IES, 64 DIN samples (mark 154), then a hand-clocked
`0x81` (156) and two chip-ID reads at ~500 kHz (157/158) with the SPI6
controller out of the path. Marks 154-158 are decoded by `tools/sweet-marks.py`.

**Build (this Mac, no Xcode.app).** `tools/build-xnu-local.sh` wants
`Xcode.app`; CLT alone has clang/ld/dsymutil but no `xcodebuild`. New
`tools/build-xnu-clt.sh` runs the same `make install` against
`xnu/out/local` with `DEVELOPER_DIR=/Library/Developer/CommandLineTools`:
one file recompiled, whole kernel relinked, **79 s**. Shim built with NDK
28.2 clang/lld via `shim/build.sh <payload> --template
backup/recovery-20261021/boot_a-live-20261021.img --v4` (absolute paths; the
script `cd`s to `shim/`).

**Artifacts** in `research/matisse/20261026-idprobe/`:
kernel 16,723,368 B `13cc3aa9...`; payload 16,719,248 B
`664504c2...`; boot `matisse-xnu-0108-idprobe.img` 7,065,600 B SHA256
`f9421f035a6332c9251f08c18a2ab4a79caed3c6b81a3f4094b5b722d0659a78`, header
v4, stock ramdisk and signature verified, payload embedded byte-for-byte
(`verify-idprobe-image.py`).

**Next (needs the usual one `boot_a` write, restored afterwards).** Same
`--template` + restore flow as the other touch runners. Read the result:
154 with `hi=1` = the chip drives its INT line and is alive (then the fault is
SPI6 controller programming); 154 `hi=0 lo=1` with pull disabled = still dead;
157/158 non-zero = the chip answers hand-clocked SPI, so only the controller
is wrong; all-zero bit-bang = the chip itself never boots (VTP at 1.8 V/LP is
then the remaining suspect, and the pre-charge order in the 2026-10-26 08:40
section is the next thing to try - do not write 0x1d23 blind).
Repo note: `xnu/out/` is gitignored, so the driver that carries the 0108-0137
PMIC work exists only on this Mac; `patches/0108-...` is an incremental diff
against that state, not something CI can apply on top of 0107.

## >>> ACTIVE 2026-10-26 (USB): device tree read, diagnostic hold built - NOT FLASHED <<<

**Request (user): "/Users/xiaohuasheng/Documents/twrp 有设备树 现在再继续帮我移植 USB 功能".**
The TWRP device tree (`Documents/twrp/device_xiaomi_matisse-TWRP`) and the live
recovery were used as the reference the earlier USB runs lacked.

**What the device tree settles (measured, not inferred).** `prebuilt/dtb` is an
MTK `dt_table` (magic `0xd7b7ab1e`) holding one FDT at offset 64; the live
recovery DTB (`research/matisse/20261025-touch/recovery-live-20261026.dtb`,
410,299 B) is the same board with overlays applied. USB0 is `usb0@11201000`
(`mediatek,mt6983-mtu3`; MAC `0x11201000+0x2e00`, IPPC `0x11203e00+0x100`,
IRQ 160), `dr_mode="otg"`, `maximum-speed="high-speed"`,
`mediatek,force-vbus`, `usb-role-switch`; PHY `usb-phy0@11e40000` with efuse
calibration cells. There is **no MUIC node and no MUIC driver**: kallsyms has
no `muic` symbol, `mtk_chg_type_det.ko` only listens to the MT6375 TCPC
notifier, and the only I2C "USB" chip is `xmusb350@35` on `i2c@11e00000`,
which is a QC2/QC3/HVDCP charger-type IC (`XMCHG_XMUSB350` strings,
`ops_xmusb350_*`), not a data-path switch. `typec_mux_switch` and
`usb_dp_selector@10005600` are DP-alt-mode orientation only. The earlier
"MT6363 MUIC is the prime suspect" note is **not supported**: the D+/D- path
has no software switch on this board.

**Known-good register reference (live recovery, adb up).** Read through
`/sys/kernel/debug/usb/11201000.usb0/regs/*` while adb worked: IPPC
`PW_CTRL0 0x10411020`, `PW_CTRL1 1`, `PW_CTRL2 0`, `PW_CTRL3 1`,
`OTG_STS 0x16c016c0`, `U3_CTRL_0P 0x88`, `U2_CTRL_0P 0x48`,
`HW_ID 0x20180724`; CSR `DEVICE_CONF 0x04000003`,
`POWER_MANAGEMENT 0x64f1`, `DEVICE_CONTROL 0x99`, `USB20_OPSTATE 0x12`,
`LINK_STATE_MACHINE 0x00ff0101`, `MISC_CTRL 0x80000003`, `LV1IER 0x37`,
`EPIER 0x00010001`, `QIER0 0x00020002`, `QIER1 0x00160006`. XNU's takeover
reproduces these within the LK handoff, so the written values are not the
obvious fault.

**New hypothesis (fits every previous observation).** The MTU3 poll thread is
created in `sweet_usb_probe()` before mountroot, but the kernel panics on the
missing `/sbin/launchd` almost at once; the touch worker showed exactly this
"created but never ran" pattern until `sweettouchhold`. A D+ pull-up that
appears and disappears inside the host's port-debounce window leaves no device
in `ioreg` - which is what every USB run reported. macOS `log show` at default
level also hides the xHCI port messages.

**Change 0107 (built, verified, not flashed).**
`xnu/patches/0107-matisse-usb-diagnostic-hold.patch`: `sweetusbhold=N`
(0..120 s, absent = off) sleeps PID 1 in timed waits before
`load_init_program`, exactly like `sweettouchhold`, then
`sweet_mtu3_snapshot()` records the controller state. New marks: 43 poll
thread entered, 44 first poll (`a`=EP0CSR, `b`=COMMON_USB_INTR), 45 1000 polls
(`a`=setups<<32|resets), 46 polls/setups/resets, 47 EP0CSR +
COMMON/LINK interrupt status, 48 DEVICE_CONF + POWER_MANAGEMENT/speed, 49
LINK_STATE_MACHINE + USB20_OPSTATE/configured, 105/106 hold start/end.
`tools/mkpayload.py` now accepts `sweetusb=0..3` and validates
`sweetusbhold=0..120`; `tools/sweet-marks.py` decodes the new codes.

**Artifacts.** kernel 16,723,368 B `766b292c...`; payload 16,719,200 B
`cfac72a0...`; boot image
`research/matisse/20261026-usb/matisse-xnu-0107-usbhold.img`, 7,065,600 B,
SHA256 `9d3f874dbd2f8c2e3cfe7703bf2392b01a87de5591f5ec2828994145cd70530b`,
header v4, stock ramdisk and boot signature verified, payload embedded
byte-for-byte (checked by `verify-usbhold-image.py`). The frozen shim was
rebuilt with `shim/build.sh` (Xcode 16.4 + NDK 28.2 clang/ld.lld), so the
embedded-length constant is compiled instead of patched at two MOVZ sites.

**Next (needs explicit approval for one `boot_a` write).**
`research/matisse/20261025-usb/run-usb-boot.py usbhold107 <img> <sha> --window=240`.
It now records every new host USB device (not only VID 0x1209), pulls and
decodes the mark block, greps the macOS USB log for the run window, and falls
back to `restore-boot-a.py` over fastboot when recovery does not return.
Reading the result: mark 43 absent = the poller never ran; 44-45 present with
no host device = controller/PHY; 46-49 with `setups>0` but `configured=0` =
EP0; `configured=1` = enumeration worked and the ECM side is next.

## >>> ACTIVE 2026-10-26 (matisse touch): Recovery inspection and platform trial <<<

**Device / safety:** the user authorized temporary `boot_a` flash tests and
reported the phone in Recovery. Current state is OrangeFox Recovery, product
`matisse`, slot `_a`. The full backup at
`backup/recovery-20261021/boot_a-live-20261021.img` is 67,108,864 bytes and
has SHA256 `2931647a56039722ea2585990b8ef3b1a2daf4c9b990231879f753049eaf86b1`.
The latest trial restored the entire backup and verified this exact hash.
No GPT, recovery, bootloader, modem or persist partition was written. The test
kernel did update the existing last-block boot-mark channel in `userdata`; no
userdata filesystem content was changed. Diagnostic copies remain in the
ignored research directory.

**Recovery inspection (2026-10-26):** saved live DTB at
`research/matisse/20261025-touch/recovery-live-20261026.dtb`, SHA256
`ba9acc0a3c0b9741d6a530f5328519628848068adc4fe376a57ece853e9d1ad6`.
Recovery binds `fts` (`st,spi`) under SPI6 at `0x11016000`; SPI6_B uses
GPIO164–167, function 2, 7 mA. Reset is GPIO3, IRQ GPIO8. Supplies VRF18_AIF
(1.8 V) and VTP (3.3 V) are on. `pinctrl-handles` reports `pmx_ts_spi_mode`.
An idle `clk_summary` showed the SPI clock disabled at that sample; this alone
is not evidence of a fault because runtime PM can autosuspend it. No firmware,
reset, calibration, regulator or storage writes were performed.

**Patch 0102 and local build:** the read-only FTS poller now has an MT6983
platform handoff that selects the live board's SPI6 parent and gates, GPIO164–167
function 2, and drive strength 7. It does not touch touch reset or PMIC rails.
`tools/sweet-marks.py` now decodes mark 100. Single-file clang check passed and
the full XNU build succeeded with Xcode 16.4 (16F6): kernel 16,705,944 bytes,
SHA256 `e576f0f2a7f00e80c7c975a3434acef74c57f3ac17dd5b9f9714953b406b5d6a`
(build ID `0x2308`). Optional-header and `strip --minimize` warnings were
nonfatal. There is no CI build for this trial.

**Image and hardware result:**
`research/matisse/20261025-touch/matisse-xnu-touch-platform.img` is 7,057,408
bytes, SHA256 `a267abb2b3ff07192842417bc95cd80ee1ccb300c009dbbbb2da8df323f67ac2`.
The v4 header, stock Recovery ramdisk, and signature matched the original.
Read-only preflight passed. Temporary `boot_a` readback SHA256 was
`9746d9626fc76b16f87e1740eaacfd3ee7349828582a8cd9b8ebd0f18e957c67`; the
runner detected Fastboot instead of a Recovery return and automatically
restored the full backup, then verified the original hash above.

The persisted mark block has 71 records for build `0x2308`. Mark 100 reads back
`CLK_CFG_7=0x81010001`, peripheral gate `0x7f7e3f0e`, SPI6 pin mode
`0x22222222`, drive fields `0x00000fc0`, matching the intended clock/pin
configuration writes. Mark 89 says `sweettouch=1`, tracing enabled, thread
creation returned success (`status=4`), but worker stage remains 1. There are no
worker-wakeup mark 88, SPI ID result 96, or contact marks 97/98. The userdata
console region has no SWEETLOG header. Thus the platform MMIO readbacks are
confirmed, but SPI communication and touch events are **not** confirmed. The
user was asked to tap during the boot window; actual taps are unconfirmed.

**Follow-up diagnostic hold (patch 0103):** the prior trial showed the worker
thread was created but had not run before the incomplete test root reached the
missing-init panic. Added `sweettouchhold=N`, capped at 120 seconds and disabled
unless explicitly set, to sleep PID 1 in timed waits before `load_init_program`.
The test image uses `sweettouchhold=45` and `sweettouchdelay=1` so scheduled
threads can probe and poll before the expected panic. Full XNU build succeeded;
kernel is 16,705,992 bytes, SHA256
`44d39d3fe746a6c0dfb4e505ea625aefadb132f35a87ae5dc2f10ce5951e6ae8`.

The hold payload is 16,701,872 bytes, SHA256
`4545346834e3284903262db057489c4673657e8144f880466f0374fe7f81ba29`.
The frozen shim's embedded-length check was updated at its two verified
AArch64 MOVZ sites from `0xfed980` to `0xfed9b0`; package validation confirms
exact payload match, boot v4, original Recovery ramdisk and signature. The new
boot image is 7,061,504 bytes, SHA256
`3409f4708f59fac680507a1d927e2a4fb5e57f0fda08b135cf4e62bea6590b00`.
Read-only device preflight passed on Recovery and verified the original
`boot_a` backup hash. Patch 0104 was then flashed temporarily, and the runner
restored the full backup after the device entered Fastboot. It verified the
original `boot_a` hash and returned the device to Recovery.

**Patch 0104 hardware result (2026-10-26):** the kernel is 16,705,992 bytes,
SHA256 `593b6a8fb27924aafdd9d792463d9435820e13f9946de391d68d6bcde4402f10`.
The v4 test image is 7,061,504 bytes, SHA256
`ab563d6639b0d9e88809fa2661da2d8906355715ac104e17d6d8585d2315d01d`; payload
SHA256 `d4cd887d6add97d6c5d0be4c41d6d462f2b94c30c468e554363e7937f754276b`.
Image preflight confirmed the original Recovery ramdisk and signature. Marks
show the worker ran, SPI transfer returned `err=0`, CFG0 read back as
`0x012b001d`, CFG3 was `0`, CMD was `0x83010`, and STATUS0 was `0`; the FTS ID
remained `00:00`, with no touch down/up marks. Hold start/end marks were both
present. The runner detected Fastboot and restored the exact original backup
hash `2931647a56039722ea2585990b8ef3b1a2daf4c9b990231879f753049eaf86b1`.
The user was asked to tap in the test window, but actual taps are unconfirmed.
Thus matching the Recovery controller's enhanced CS timing did not establish
SPI communication; the earlier CS-timing root-cause guess is disproven.

**Patch 0105 hardware result (2026-10-26):** local Xcode 16.4 build succeeded;
kernel SHA256 `958ea6ccae259e79708956049736d5f0c02fcceaa08cd94b8c5224ea0557bdbd`,
16,705,992 bytes. Payload SHA256
`66610274374b292bc399c25a339ed4de8bd89ead1cad18a1202c9ae362671adf`; v4 image
SHA256 `8be7b3d8084b7a25b6a052032b67b8cf0896b12fae6f4dac743c03ce30d2e562`,
7,057,408 bytes. Original ramdisk and signature validated. The written image
readback hash was `a4c8ebc562d1a4f2aaf2cfc8f46b6a91c12c781511e40f15ad0f7c78a233ca7d`.
The device entered Fastboot; the runner restored `boot_a` and verified the
original full-backup hash, then rebooted Recovery. The latest mark block has
76 records for build `0x2308`; chip-ID mark 96 remains `00:00`, there are no
97/98 touch events, and hold marks 101/102 are present. Mark 104 is absent
because the reset helper runs before the UFS mark channel is available (inference
from the boot call order); the subsequent init snapshot reports worker status 4,
which means the helper's GPIO mode/output readback passed before the worker was
created. GPIO3 reset release alone did not restore SPI responses.

**Patch 0106 hardware result (2026-10-26):** a comparison sweep replaced the
single chip-ID read. Kernel 16,706,112 bytes, SHA256
`b65ad033a4a45ee984f306a1edb5b831a2d5fabdbca4911d5918e881a06e416f`; payload
16,701,984 bytes, SHA256
`95b9f4613f3df64107338baed0acdf0ea243161a4787830b7a1bd9c7c50e766f`; v4 image
7,061,504 bytes, SHA256
`41110a912d727c4dac04e727022756477f30b31477b7fab863be6c2c19467624`.
Artifacts: `research/matisse/20261025-touch/matisse-xnu-touch-spi-sweep.{img,json,payload}`,
runner `run-touch-spi-sweep.py`, repacker `repack-touch-spi-sweep.py` (rewrites
the two 32-bit MOVZ/MOVK `EMBEDDED_XNU_BYTES` sites at image offsets 0x53e4 and
0x5470 because the payload length changed). The sweep runs only with
`sweettouchsweep=1`; the production path is unchanged.

Marks (86 records, build `0x2308`) give the first unambiguous split:
- 110: `CFG3=0`, `PAD_SEL=0` before the first transfer. The boot firmware leaves
  the pad selector at SPI6_A; only the DT value 1 selects SPI6_B, and the write
  sticks (`mark 118` reads back 1). Nothing was lost by the old `CFG3=0` write.
- 111 internal loopback (`SPI_CMD_SPIM_LOOP`) returned the transmitted pattern
  exactly: `rx=a5 5a 3c c3 0f f0 96 69`, `match=1`, `err=0`, 3,514 ns for 8 bytes.
  The controller, its bus clock, the TX/RX FIFO and the shifter therefore work;
  the 3.5 us duration rules out a stale FINISH bit.
- 112..116 all returned eight zero bytes: 4-byte address with `CFG3=0` (3,919 ns),
  4-byte address with `CFG3` preserved, 3-byte address with `CFG3` preserved,
  `PAD_SEL=0`, and `SAMPLE_SEL=1`. Chip ID stayed `00:00` and no 97/98 events.
- 117/118: `STATUS1=1` after every attempt, i.e. the transfer completed normally
  in all five variants.
So the earlier CS-timing, CFG3 and address-framing hypotheses are all disproven,
and the fault is downstream of the SPI controller: the chip never drives MISO in
any configuration. Remaining candidates are the pad-level output path (the
speculative `IOCFG_BM+0x004` drive write is unverified and may have zeroed pad
fields) or the chip's power/reset state during an XNU boot.

Device safety: the test ran to the expected missing-init panic and the phone was
in Fastboot afterwards; `tools/fbraw.py flash boot_a` restored the full 64 MiB
backup and `sha256sum` on-device confirms
`2931647a56039722ea2585990b8ef3b1a2daf4c9b990231879f753049eaf86b1`. No other
partition was touched.

**Patches 0107-0111 (2026-10-26, pad-level sweep):** five temporary boots
narrowed the fault from "controller" to "the chip never answers". Source of the
last build is snapshotted at
`research/matisse/20261025-touch/sweet_matisse_touch-0111.c`; run artifacts are
`matisse-xnu-touch-{pad-observation,bitbang,gpiomode,ies,irqcheck}.{img,json,payload}`
with matching `*-after-marks.{bin,txt}`. Every trial ended in the expected
missing-init panic, `boot_a` was restored from the full backup each time, and
`sha256sum` on device returned `2931647a56...86b1` after every restore.
- The PIO layout is 0x10 bytes per 32 pins (data +0x0, set +0x4, clear +0x8),
  so DIN for pins 160..191 is at `0x10005250`, not `0x214`. The earlier "all
  pads low" reading was a wrong register.
- The mode write used by patch 0102 (`0x1000544c`) is a **no-op**: readback of
  `0x440` never changes. Writing the data register `0x10005440` directly works
  (`0x22221111` -> `0x00001111`), which is what made a real bit-bang possible.
- With the corrected DIN, CSB (GPIO165) is driven low during a transfer and
  released afterwards, so the SPI6 controller does reach the pads. Loopback
  still returns the exact TX pattern in 3.9 us, so the shifter and bus clock run.
- GPIO-mode bit-bang (verified mux switch, MI as input, CS/CLK/MOSI driven by
  hand at ~500 kHz) returns eight zero bytes for both 4-byte and 3-byte address
  framings: the chip does not answer even without the SPI controller.
- MT6983 register tables were recovered from the vendor source
  (`MiCode/Xiaomi_Kernel_OpenSource`, branch `rubens-s-oss`,
  `drivers/pinctrl/mediatek/pinctrl-mt6983.c`). IOCFG base 5 = `0x11d30000`
  is the block for GPIO160..167; IES word `+0x0050` bits 15/14/16/13, PU
  `+0x00A0`, PD `+0x0070`, drive `+0x0110`. IES read back all ones, so input
  enable was never the missing piece.
- The PU/PD words read from XNU (`0xfb7a5beb` / `0x00048410`) match Recovery's
  `pinconf-pins` exactly (165 pull-up, 164/166/167 pull-down), which proves the
  whole pad configuration survives the reboot and that every DIN reading above
  is trustworthy.
- Touch IRQ (GPIO8, IOCFG base 11 = `0x11f10000`, IES `+0x0060` bit 16) had its
  input enable **clear**; setting it did not change the level: 64 samples read
  0 before and after a 200 ms reset pulse, while Recovery reports the same line
  as `in hi`. A long reset plus a repeat chip-ID read still returned `00:00`.
Conclusion: mux, IES, bias, reset drive and the SPI controller are all correct
and identical to Recovery; the touch controller itself never drives MISO or INT
during an XNU boot, i.e. it is not running. The remaining explanation is its
supply: Recovery shows `mt6373_vrf18_aif` (1.8 V) and `mt6373_vtp` (3.3 V)
enabled with `spi6.0-vdd` / `spi6.0-avdd` as the only consumers, and XNU never
enables either rail.

**Next:** read the MT6373 LDO enable state from XNU before anything else. The
SPMI helper (`bsd/dev/sweet_spmi.c`) only supports SID 0 reads through the
MT6363 channel and has no write path, so first locate the MT6373 SID and the two
LDO enable registers (DT `regulator.55` = `mt6373_vrf18_aif`, `regulator.64` =
`mt6373_vtp`), add a read-only probe and record it in a mark. Only after a
confirmed "disabled" reading should `sweet_spmi` grow a write so the two rails
can be enabled exactly as the FTS probe does (vdd then avdd, no voltage change),
followed by the same temporary boot and full `boot_a` restore. Do not enable
Matisse touch by default until chip ID `36:40` and down/up events 97/98 are
observed.

**Unrelated worktree state:** keep pre-existing edits out of commits:
`shim/build.sh`, `shim/shim.c`, `.DS_Store`, `.workbuddy/`, and the untracked
`xnu/patches/0093-sweet-log-readonly.patch`.

## >>> ACTIVE 2026-10-25 (display): readable text with 0098; source fix validated <<<

**Latest:** 0146 showed **full-screen green**, and 0150 showed **readable text**,
both confirmed by the user. Root cause: the primary mutex must start before
the secondary. Reversed order (0139+) stalls both OVL outputs. Earlier partial
frame in 0138 came from its different, delayed secondary start; it was not the
0139 result. 0147 also completed two normal refreshes with DSI_INTSTA `0x6`.

Patch `0098-matisse-dual-pipeline-refresh.patch` and mkadt's secondary-reg
are prepared. Local source/kernel now contain 0098, build `0x2308`; Xcode
16.4 build succeeded, 24 targeted tests passed, both changed kernel files
replay exactly. 0148 source-build reached its BRK in 32.71 s with status
`0x16` and two pushes. 0149 reached `_load_init_program` in 70.34 s and
recorded build `0x2308`. In 0150 the user saw readable text; its runner did
not detect a changed Recovery boot ID within 180 s, then restored `boot_a`
through ADB and verified the full backup hash. A post-run read-only check
confirmed Recovery, `matisse`, slot `_a`, and the same hash. The 0150 return
timeout means its checkpoint was not independently verified. Commit
`d5b3146` contains the source, ADT and test changes. No new CI run. Device
dumps remain outside git.

**Measured:** DSC0 CON = `0x10089` selects two upstream display pipelines.
DISPSYS1 at `0x14400000` is in the live FDT; 0137 read mutex MOD0 `0x7fff5`,
OVL_EN `0xe00001`, right OVL address `0xfcb3fb40` (= left + 720*4), pitch
`0x1680`. 0138 enabled its mutex before the primary refresh and produced the
user-visible partial frame. This establishes that the second pipeline matters;
it does not yet establish why the rest of the frame is corrupt.

**0135-0139 recovered results:** all hit the expected BRK and restored the
full boot_a backup, SHA256 `2931647a56039722ea2585990b8ef3b1a2daf4c9b990231879f753049eaf86b1`.
No new UFS marks are expected (the probes stop at UFS entry).
- 0135: 32-bit MMIO reads returned OVL FLOW_CTRL `0x08041020`, RDMA0_DBG
  `0x201fe001`; return 32.87 s; image `3a71dfd1f5500afcd76f17dc47e1356aff22b88304f0e91fcaec5a408d3904ef`.
- 0136: RDMA global `0x101`, DSC CON `0x10089`; return 33.79 s; image
  `324164a3aae98274f444a87224b462562c0ad1cafd10e72ff9acff998782f80c`.
- 0137: secondary register readback above; return 32.77 s; image
  `39e069dfaa2c03cd2e7ea722d8072281b7eaa658aa3fdccbad26d6922e688ba4`.
- 0138: partial frame; DSI_INTSTA `0x80000006`, secondary OVL FLOW_CTRL
  `0xc8c02`; return 94.84 s; image
  `2915b582a373e54ba741cec897121813857dd5d2ea567bbaca9af9d32adf3bf5`.
- 0139: both mutexes triggered from the first refresh, then all 1440*3200
  pixels filled green before a forced refresh. DSI_INTSTA `0x80000004`,
  pushes 2; return 32.78 s; image
  `869099f462e084925ade3e9afd678294bc3724192c99c4013bb59c092d706560`.
  BUSY remains set, so frame completion is not established.

**Source/artifact lineage:** the old 0131/0139 diagnostic source and 0x2307
kernel are preserved in `20261025-display-0148/before/` and
`kernel-before-0148.development.sweet`. The current 0098 is based on 0097's
bounded BUSY poll/throttle, with validated secondary mapping and primary-
before-secondary triggering; it does not include the unconditional TE/rearm
loop or fixed 15 ms stop. 0148 preserves the unchanged RTC/IOBSD diagnostic
wait skips and green probe separately in payloads, not production source.
The unmodified kernel and ADT are packaged as `matisse-xnu-0148-dual.payload`.
The project still lacks launchd in its test root; this display task does not
install userland.

**0140 measured:** both primary and secondary OVL FLOW_CTRL_DBG are
`0x08041020`: FSM processing, output valid=1, ready=0. Both are stalled by
backpressure downstream, rather than one OVL simply not starting. Expected
BRK, return 33.78 s, complete backup restoration verified. Image
`a0c96f340041bee25d259244c07805130fd51e74866aeb407fd128de4fb4cc97`.
The first preflight aborted without writes because the phone had moved to
Fastboot; fbraw reboot-recovery succeeded before the verified test.

**0141 measured:** DSI_STATE_DBG6 `0x10008` still means waiting for RDMA
frame data, DSC_INTSTA `1` has DONE set (could include an earlier frame; it
was not cleared before this probe). Expected BRK, return 32.87 s, boot_a
restored/verified. Image
`f0645c3d184ad96a430b1feba50593984ddcbd198fcbfd85652798ebba6b57a4`.

**0142 measured:** skipping the initial refresh BL at `0xfffffe000747b6a0`
was not sufficient to isolate one transfer: push count stayed 2 (another
console caller triggered refresh). User saw only REDMI; DSI_INTSTA
`0x80000004`, expected BRK, return 32.81 s, full boot_a restored.
Image `736acd68853f5c313fcd673e7735486745ec151beddb1c967d9935683cb98dc6`.

**0143 measured:** force==2 gate reduced pushes to exactly **1**, but
DSI_INTSTA remained `0x80000004` and user saw only REDMI. Thus overlapping
refreshes alone cannot explain this stall. Expected BRK, return
33.78 s, full boot_a restoration verified. Image
`4a5b36b1f8424a28f5012d025dde8f463526ee6fee1b827917ac4d4c891cc08d`.
This diagnostic replaces only the invocation-counter prologue; readiness,
throttle, locking and push count remain intact.

**0144 measured:** vendor DSI engine reset before START did not resolve
one-frame stall: pushes 1, INTSTA `0x80000004`, user saw only REDMI.
Expected BRK, 33.79 s return, full boot_a restored/verified. Image
`b48f413a27090040bfe0b8ec837c5c8d70c76e338cca60d4471f918fd76339fb`.
The guarded reset detour used unused early-vector padding and replayed the
displaced instruction; the reset did not touch PHY/panel controls.

**0145 no checkpoint observed:** the MMSYS VALID1/READY1 probe did not
return; Fastboot was detected at about 100 s. SIGTERM invoked the runner's
finally restoration; full boot_a restored and verified. No register values
were obtained. Do not infer a specific hardware fault from this trial.

**BREAKTHROUGH 0146 — user confirms FULL GREEN:** changing just the order of
the two MUTEX_EN=1 writes (primary first, secondary second, as in vendor
mtk_disp_mutex_enable_cmdq) makes DSI_INTSTA `0x6`: BUSY clears, CMD_DONE set.
Exactly 1 push, expected BRK, return 32.72 s, full boot_a restored.
Image `3f7fc2f18ef20734c1efc6c5d6bffbb2c39ace8d8d7342f27380daea0da73e34`.
This is a controlled two-instruction change from 0143 (no DSI reset): swap
the two MMIO-base loads at `0xfffffe000747b970` and `0xfffffe000747b980`.
The binary swap is valid only for the validated dual pipeline; do not ship
it as general driver code. The production source must implement primary
before secondary explicitly and preserve the single-pipeline branch.

**0147 repeated-frame result:** expected BRK, DSI_INTSTA `0x6`, pushes 2,
full boot_a restored/verified. Image
`66d667144255438f6707ad306cb7c094677a35ff21bec1971459d7bca7ad565a`.
No separate screen report was requested for this intermediate run.

**Next:** if validating beyond the display, package a normal boot image using
the committed 0098 source without the diagnostic wait skips. The display
output is confirmed readable; a full OS boot still has the separate missing
`launchd` test-root limitation. Keep source experiments reproducible and do
not reinstate the disproven PA cache-clean claim in the historical handoff
below. User authorized test boots; each trial uses the established full
`boot_a` backup/restore procedure.

User now reports **stuck on REDMI logo**, not the older partial-frame symptom.
Read-only check: device is `matisse`, Recovery, slot `_a`; full `boot_a`
SHA256 matches the verified backup (`2931647a56039722ea2585990b8ef3b1a2daf4c9b990231879f753049eaf86b1`). This was the initial preflight; the authorized trials below temporarily replaced
`boot_a` and restored its complete verified backup after every test.

The last userdata mark block has 64 records, **no build-ID mark 99**, 4588
refresh calls / 201 pushes, legacy mark 92 = 201 / 201, and reaches init exec
ENOENT. This is an older run, not evidence that 0111 executed. Saved locally
at `research/matisse/20261025-display-0112/before-marks.bin`, SHA256
`aef91eb4f52a5caa447fbf91cf8de90b022594be8ab4d80487c4cd8715131308`.

**Corrections to the previous handoff (source evidence, not a hardware result):**
- `start.s` maps the visible framebuffer Normal-NC, and `sweet_early_init`
  verifies PAR attributes `0x44`. The earlier claim that early drawing is
  through a cacheable mapping is false for this source tree.
- `arm_vm_init` replaces TTBR0 before `fbcon_probe` calls display init. 0111
  then executes `dc cvac` on the physical framebuffer address. That address
  is no longer a valid CPU VA; the new clean can itself fault. Do not flash
  0111 as the next test.
- `HAS_UCNORMAL_MEM` is absent for SWEET. The previous `initialize_screen`
  change therefore still selects `VM_WIMG_IO`, **not** WCOMB. Make the SWEET
  mapping explicit and record its translated physical address / attributes.
- Pre-UFS calls to `sweet_mark` are dropped; marks 90/96/97 cannot diagnose
  early mappings. Cache those measurements and replay them once UFS is ready.
- 0111 updates the refresh throttle only on success; a stuck BUSY retries the
  20 ms wait on every character. Throttle failed attempts too.

**Completed (commit `d56e16f`, local build; no new CI run):** patch
`0095-matisse-display-mapping-and-marks.patch` saves the prior untracked
USB/root progress marks plus the display fixes in git. Framebuffer aliases
now explicitly use WCOMB for SWEET; no PA-based cache operation remains.
DSI uses the vendor 0->1 strobe and a 20 ms BUSY bound, with failed attempts
also throttled to 5 Hz. This does not make the shared scanout buffer tear-free.
Marks 90/91/93 record the actual console VA/PA, first/last PAR translation,
geometry and pre-poll DSI status; 94/95 save LK's DSI command setup. Build ID
is `0x2303`; mark 92 is busy-skips/status only for IDs >= `0x2302`.

Local build succeeded with Xcode 16.4. Logs and exact packaging commands are
in `research/matisse/20261025-display-0112/`. 9 patched source files replay
byte-for-byte onto the source baseline with 0090/0093/0094 applied (0091/0092
were already present). The local kernel, like 0111, does not contain the
separate 0094 key driver; `sweetkeys=0` is unchanged for this display test.
Tests: refresh latency/strobe harness (1), mark decoder (4), entryprobe (13),
and breakpoint (10) passed. `validate-repo.py` still fails on the disabled
0085 numbering gap and CRLF shell scripts (3 tools and patches 0019/0020/0026).

Artifacts (all in that research directory except kernel):
- Kernel `xnu/out/local/fakeroot/System/Library/Kernels/kernel.development.sweet`,
  16,705,704 B, SHA256 `67841f7d046527f39b99ecb483245cc67b9f8a79c57b4ccdf8c61c766da11263`.
- Normal payload `matisse-xnu-0112-ncmap.payload`, 16,701,536 B,
  `ac2f7cac59419c24b9a0dc3974e85b65a0c918abf179a11a68eab6d7f36d5e81`.
- Normal boot image `entryprobe-el1-xnu-0112-ncmap.img`, 26,615,808 B,
  `a281d14cbe9e0946459dea0d4550aeac19a017a3f8aca30f1f22c67d67aee2ad`.
- **Selected test** `entryprobe-el1-xnu-0112-ncmap-brk.img`, 26,615,808 B,
  `760aa1e8f50346efe209d7c3ab127e82910162085fe52bdf77d8ff89a690a637`.
  Its payload is `f4fd2748aa3fca36e6cf1400e452aa677508c85bdd2ac4d973ab8beadf1d8054`.
  Exactly one instruction differs: BRK #0x5357 at `_load_init_program`,
  VA `0xfffffe00077dc0bc` / PA `0x1017dc0bc` (entry offset `0x35ac34`).
  Intended to return to Recovery after display/UFS/root-mount diagnostics,
  before the known missing-init panic. This return has not yet been tested.
- Both embedded payloads byte-match their source; the early/high vectors,
  bootstrap TTBR0 and cache-clean bounds match 0111. High vector `-0x3488`;
  the scan helper prints multiple candidates, so the synchronous-slot guard
  and old manifest were checked explicitly.

**Authorization for this trial:** user said "现在设备在 recovery 你可以随时测试"
after the 0112 test/restore plan was described. Proceed with this selected
image and its full boot_a restoration. Read-only preflight passed;
`run-display-test.py` defaults to preflight, `--execute-approved` runs the
trial. It requires a *changed Linux boot ID* before collecting results,
avoiding the old immediate-ADB-return race. Preserve trial-result.json,
marks and dmesg locally; do not commit device dumps. On failure to return,
it waits for manual FASTBOOT and restores the verified backup.

**0112 hardware result (FAILED to reach checkpoint):** user saw only the
REDMI logo. No automatic Recovery return within 100 s. The device appeared
in Fastboot during restoration; full backup flash succeeded, first
`reboot recovery` failed, explicit retry succeeded. Recovery then confirmed
full boot_a SHA256 `2931647a56039722ea2585990b8ef3b1a2daf4c9b990231879f753049eaf86b1`.
The mark block is byte-identical to before (`aef91eb4...`), still no build ID.
Thus there is **no evidence 0112 reached UFS init**. The SWEET-ENTRY display
record in recovered dmesg belongs to the restored backup, not this probe.
Trial artifacts: `trial-result.json`, `trial-after-marks.bin/.txt`,
`trial-dmesg.txt`. Written partition hash was
`eefab04a2e9f8467cf6ffec9079a5689b289134bfe33d116532c2b00770f8374`.

**0113 checkpoint PASS:** BRK at display init entry
`0xfffffe000747b3cc` / PA `0x10147b3cc` hit with ESR `0xf2005357`.
Returned to Recovery in 29.57 s; full boot_a restored/verified. Image
`research/matisse/20261025-display-0113/entryprobe-el1-xnu-0113-display-entry-brk.img`
SHA256 `5d66e6dc9aef045726c394d5cb93ecc99edd4bfe52ac203780cea3e077a88c74`.
Thus 0112's boot path reaches the display driver's entry. No new marks are
expected because this checkpoint is before UFS. Next probe 0114 is at
`_initialize_screen` entry, after serial/display initialization.

**0114 checkpoint PASS:** `_initialize_screen` at `0xfffffe0007455354`
hit with ESR `0xf2005357`; returned in 29.56 s, boot_a restored/verified.
Image SHA256 `d5f344680a638367d80c83d0a4da7beadebd50d98f5473092ea4e78af2fe4330`,
artifacts in `research/matisse/20261025-display-0114/`. This proves the DSI
init/first refresh returned. Next 0115 catches `_panic_trap_to_debugger`
entry so the panic format pointer can name the failure inside/after console
initialization, instead of merely timing out waiting for root init.

**0115 panic-entry probe did not return** within 100 s; boot_a restored and
verified through Fastboot/Recovery. Image `a9fa4e6902d00d7d10414a450d29e49b2735d41dc68a0423ddc638ac112ff277`;
artifacts in `research/matisse/20261025-display-0115/`. This alone does not
prove absence of a fault, only that the panic-entry checkpoint was not observed.
User pointed out the userdata tail log: read its last 1025 x 4096 bytes,
starting at byte 114315718656 of a 114319917056-byte partition. All bytes
before the final SWEETMRK block are zero, no SWEETLOG header anywhere.
Dump SHA256 `d03e54b39ee9cd2f28dafc3bca14557b9c4b07ecafa6644171ac23f0b6d6ae5b`.
Next 0116 targets `initialize_screen` immediately after `ml_io_map_unmappable`
returns (VA `0xfffffe0007455508`), to narrow the stall further.

**0116 mapping-return checkpoint PASS:** PC `0xfffffe0007455508`,
ESR `0xf2005357`, returned framebuffer VA `0xfffffe000d4db000` in x0.
Recovery returned; full boot_a restored/verified. Image SHA256
`4f92d2701dd05ae5043d2fe7e072e5157837bf22c9cab24b4bfa6f9e5d2a6030`.
Artifacts in `research/matisse/20261025-display-0116/`.

**New source bug fixed for 0117:** early `io_map()` maps
`round_page(size + start_offset)` but advanced its VA allocator by only
`round_page(size)`. Framebuffer PA `0xfcb3f000` has offset `0x3000` in a 16K
page; it therefore overlaps the next early mapping by a page. Patch 0096
advances by `alloc_size` instead. This is a verified allocator defect, but
whether it explains the device stall is still a hypothesis. A harness
compiled from the real function checked 20,480 adjacent allocations at 4K
and 16K granules; old code fails the bounds assertion, new code passes.
Build ID is now `0x2304`. 0095 was also corrected to retain the existing
0093 log-start change (the initial WIP source had unintentionally reverted
it); that change alone still does not bypass `ufs_write_blocks`' rw gate.
New sources compiled successfully; 0096 patch replay matches both inputs.
Next test: 0117, returning at `_load_init_program` (`0xfffffe00077dc0ac`).

**0117 test FAIL:** image `6240fdc4d14180d5378bcb556e431d9b5aeb9262507df5541301ccc84a24fd93`
did not return within 100 s. Boot_a restored and full hash verified. The
allocator correction (commit `98c72a1`) is valid, but it is not sufficient to
resolve the current stall. Build kernel SHA256
`a8a9fd618078f44a946db52a1986483fb3531b8298dbed903df6969b67df9c5d`;
normal payload `401562f6ca601a002582a48cb7a47d97caf9231d965fdc7095e4981f6261fb31`.
Next 0118 breaks at `_PE_init_printf`, called just after PE_create_console,
to check whether the first initialize_screen call returns.

**0118 checkpoint PASS:** `_PE_init_printf` entry at `0xfffffe0007a5c664`
with x0=0 confirms the first `initialize_screen` call **returned**. Thus the
stall is later than initial console setup. Full boot_a restored/verified.
Image `30b0a34ad5b06beca0de506bd72b2a56d1e4f795f0a9ad50681c4efde5d1aaa4`;
artifacts in `research/matisse/20261025-display-0118/`. Next 0119 probes
`vcattach`, where the video console is enabled after VM initialization.

**0119 checkpoint PASS (recovered from the previous agent's saved result):**
`_vcattach` entry at `0xfffffe00074579fc`, ESR `0xf2005357`, Recovery return
29.58 s. Image SHA256 `4a10bd07ead6ac054eaa86112853016cbc93ecaef921f25b4a17eee4ca4fef8c`.
The mark block is unchanged as expected before UFS. `trial-result.json`
records full boot_a restoration to `2931647a...`; artifacts are in
`research/matisse/20261025-display-0119/`. User subsequently reports Fastboot;
next action is Recovery reboot/readback and 0120 at vcattach's common return
(`0xfffffe0007457be4`) to determine whether enabling/replaying the console
completes. No new kernel build or CI run is needed for that breakpoint.

**0120 artifact (hardware result below):** common vcattach epilogue at
`0xfffffe0007457be4`; image
`research/matisse/20261025-display-0120/entryprobe-el1-xnu-0120-vcattach-return-brk.img`,
SHA256 `4bfadc2401a760e1bd1e34c401c8f2f9f127bb4cc8e94085cfbdce40d3f51b6b`.
Host checks prove exactly one BRK replacement, exact embedded payload, and
0119's same vector/TTBR0/cache-clean parameters. No new CI run.

**Current macOS Fastboot recovery lesson:** official platform-tools 37 queries
can work while reboot/flash commands hang. The full-backup flash attempt
this turn timed out before reporting a transfer; fbraw's first download
also timed out before DATA, so it never sent image bytes or `flash:boot_a`.
After attempting libusb endpoint clear (both returned Pipe error), the next
query returned `FAILRead USB error`; a fresh `fbraw.py getvar:product` returned
`OKAYmatisse`, then `fbraw.py reboot-recovery` returned `OKAY`. Recovery ADB
returned; full boot_a hash matched `2931647a...`. Use `tools/fbraw.py` for local
fastboot commands, as the 2026-10-21 notes already advised; 0120's restore runner now does so. Do not assume
an official-client timeout means the bootloader did not process the command.

**0120 checkpoint PASS:** `pc=fffffe0007457be4`, ESR `0xf2005357`.
Full boot_a restored and verified `2931647a...`. This proves vcattach returns,
not that it draws: its graphics-boot branch can skip screen acquisition and
message replay. Observed x0 `fffffe0007be5540` is the progress-lock address,
consistent with that early branch (hypothesis pending the boot-mode check).
Next 0121 breaks at `_bsd_init` entry `0xfffffe000775d1c4`.

**0121 checkpoint PASS:** `_bsd_init` entry `0xfffffe000775d1c4`,
ESR `0xf2005357`. Image `7993ec6d86beb908d669b833ae55e7d032d83f1fb54d1cb9d4b6fcf0d2a080aa`;
artifacts in `research/matisse/20261025-display-0121/`. Full boot_a restored
and hash verified. Thus VM/IOKit startup and enabling interrupts complete.
Current loader sets `Video.v_display=1`; payload uses `serial=0 -noprogress`.
Those source settings explain why vcattach can return without text output;
changing that alone has not been tested. Next 0122 probes UFS rootdev entry
`0xfffffe00074dd2d0` (the UFS init function is inlined there).

**0122 UFS-entry checkpoint NOT OBSERVED:** image
`7d8ce49fa12145ebb6992cde5884ea26bb1f5175159791d976c64d9479361b82`
did not return within 100 s. User entered Fastboot; the updated fbraw restore
path restored full boot_a and verified `2931647a...`. Result is in
`research/matisse/20261025-display-0122/trial-result.json`. This narrows the
last observed progress to BSD entry (0121) before UFS rootdev (0122), but a
missing checkpoint alone cannot distinguish hang from failure of the relay.
0123 prepared at `_kminit` `0xfffffe000792dc08`, inside bsd_autoconf (inlined
into bsd_init). Initial 0122 launch aborted before writing because the device
had moved from the prior same-boot recovery to Fastboot; fbraw reboot of the
restored image returned to Recovery and preflight verified it before testing.

**0123 kminit checkpoint NOT OBSERVED:** image
`1849877c2ff839b71f245da5502c00399ed89412b8ef092eec8cb40ec575092c`
did not return within 100 s. User reported Recovery; runner restored full
boot_a and verified `2931647a...`. Artifacts in `20261025-display-0123/`.
Next 0124 probes BSD at `0xfffffe000775d628`, immediately before
IOKitInitializeTime (after bsd_bufferinit), within the unobserved interval.

**0124 checkpoint PASS:** `pc=fffffe000775d628`, ESR `0xf2005357`,
immediately before IOKitInitializeTime; full boot_a restored and verified.
Image `c61d00c23170cc123970ef718a4d57d5bbab022febdda0ade0ee29d70368e308`.
This reproduces the older 2026-10-23 watchdog/wait issue: entryprobe leaves
LK's ~31 s AP watchdog running, but this fresh 0117 payload has both 30 s
RTC/IOBSD waits intact (unlike older rtcfast diagnostic payloads). Thus the
prior no-return tests do NOT yet locate a new display-driver hang. Next 0125
keeps the same kernel/ADT/args and changes only the two timeout constants to
zero (four guarded instructions), preserving matching/cleanup calls, plus
BRK at load_init_program `0xfffffe00077dc0ac`. Exact changes are saved in
`research/matisse/20261025-display-0125/wait-patches.json`; not yet a hardware
result. This is a diagnostic workaround, not a production RTC/watchdog fix.

**0125 zero-timeout / load_init checkpoint NOT OBSERVED:** image
`14dbcad6269f5c694c5acd3ed0da7285e776c0f2428488d4edfadfc78388fc8e`
did not return in 100 s. User reported Recovery; full boot_a restored and
verified. Post-timeout marks still match the old 64-record block (no build
ID), and dmesg's display probe belongs to the restored backup. This test
does not establish which stage failed. Next 0126 uses the older hardware-
passed rtcfast method: bypass the wait calls themselves (three guarded
instructions) and stop earlier, at UFS rootdev entry. This diagnostic RTC
NOP leaves one temporary matching dictionary unreleased; do not promote
that binary patch to a production kernel fix. Records and payloads are in
`research/matisse/20261025-display-0126/`.

**0126 rtcfast / UFS-entry checkpoint NOT OBSERVED:** image
`433a56399862688c05cae1a8ea1d935156988fc39a215713aaf0f1477e3d26ac`
did not return within 100 s. User reported Recovery; the runner restored full boot_a and verified
`2931647a...` (confirmed again by a live readback). Since bypassing both calls still does not reach UFS, the
watchdog/waits explanation is not sufficient. Next 0127 uses that same
rtcfast base with BRK immediately after IOKitInitializeTime (`775d62c`),
paired with 0124's successful before-call checkpoint (`775d628`).

**0127 checkpoint PASS (saved result recovered):** rtcfast payload returned
at `0xfffffe000775d62c`, immediately after IOKitInitializeTime, ESR
`0xf2005357`, in 32.77 s. Image SHA256
`8e7990b1038e4e10e41049b6621d2b8760d836798bc6c465c70ee096a91ce095`.
Full boot_a restored and verified; no UFS marks expected at this point.

**Verified machine-code defect, patch 0097 in progress:** Darwin ARM64
assembly uses semicolons as comments. `disp_counter()` emitted ISB but no
CNTPCT read, leaving timeout/throttle registers uninitialized. Both PAR
checks in `sweet_early_init` and `sweet_display_set_target` emitted AT but
neither ISB nor MRS PAR_EL1, so the source's translation checks were not
actually performed. `ufs_smc` also lost all instructions after its first
MOV, including SMC. The normal `ml_get_hwclock` CNTVCT reader is intact.
These are disassembly observations; their contribution to the visible logo
and the pre-UFS stall still requires hardware testing. Replace separators
with explicit newlines, verify emitted instructions and rebuild as 0x2305.
Preserved pre-fix kernel/sources in `20261025-display-0128/`.

**0097 built and 0128 testing:** all three changed sources replay exactly.
Darwin assembler regression tests pass for the timer, all four PAR checks,
and SMC arguments/call; the existing stalled-DSI host test also passes.
The linked kernel contains 4 CNTPCT reads in refresh, 2 PAR reads in each
console helper, and 3 inlined UFS SMCs. Kernel SHA256
`5e43f1a0ae65a95efffc61639b435207b9fe5f4fb9a035bb4e47d3cbcaf13516`, 16705680 bytes; build ID `0x2305`.
Local build succeeded with Xcode 16.4; no new CI run. 0128 boot image
`cc5ec95ee064cf5db0b71bcbd32c1f4dafa8616915877c9802686d496564eba7`, 26615808 bytes, with the same RTC/IOBSD diagnostic wait skips
relocated to the new kernel (manifest in `20261025-display-0128/`).
Checkpoint is `_sweet_ufs_rootdev` `0xfffffe00074dd2d0`. Embedded payload,
single BRK, both vectors and bootstrap TTBR0 storage validated. Trial
launched with ongoing user authorization; full restoration remains required.

**0128 UFS-entry checkpoint PASS:** PC `0xfffffe00074dd2d0`, ESR
`0xf2005357`, Recovery return 32.75 s. Full boot_a restored and verified.
This passes the same rtcfast/UFS checkpoint that 0126 failed before 0097.
Marks remain unchanged, expected because the checkpoint is before UFS init.
Patch/tests/handoff committed in `85269a5`; no new CI run.
Next 0129 uses the exact same rtcfast base and moves only the BRK to
`_load_init_program` `0xfffffe00077dc0e8`, to collect current display marks.
0129 image SHA256 `b3ee7648b67a6074709129d445dccf5d111e92fe2258dd9192efffda2d863889`.
User confirms 0128 still showed only the REDMI logo.

**0129 reached root mount; load-init relay NOT OBSERVED:** no return in 100 s;
user returned to Recovery and full boot_a restored/verified. Readback after
recovery has a NEW 63-record mark block, build `0x2305`, ending at mark 60
(before load_init_program), with successful root mount / VFS_ROOT marks.
Thus this is NOT evidence of a UFS failure. A late BRK relay may fail after
thread/CPU changes; the reason is unproven. Marks saved as
`20261025-display-0129/after-timeout-marks.bin/.txt`. Current framebuffer
VA `0xfffffe000d4df000` maps PA `0xfcb3f000`; both endpoint PARs have Normal-NC
attributes `0x44` and correct pages. 4588 refresh calls, 1 push, 0 busy skips,
last (immediately-after-push) DSI INTSTA `0x80000004`. All later calls may
have fallen inside the 200 ms throttle window; this remains a hypothesis.

Next 0130 uses the known-returning UFS-entry checkpoint and a guarded
22-instruction cave in unused early-vector slot 14: mask IRQ to retain this
CPU, wait 500 ms on CNTVCT, force one display refresh, wait 500 ms, then BRK.
Capture `x0 = status<<32 | busy_skips`, `x16 = pushes`. No kernel rebuild;
base is 0128 rtcfast. This distinguishes a missing final push from a busy
DSI engine. Artifacts in `20261025-display-0130/`.

**0130 PASS / panel unchanged:** returned at cave PC `0xfffffe0007482768`,
ESR `0xf2005357`, x0 `0x8000000400000001`: DSI remained BUSY after a 500 ms
wait and the forced refresh skipped once. User still saw only REDMI. Full
boot_a restored/verified. Image `a02b21df6a89d4f84fc9d59785894e0c46afed9ff41d054c3809863a41b8a145`.
Correction: the banner's x16 field actually captures interrupted x12; the
0130 attempt to report pushes through x16 is invalid. Use x12 next time.

**0131 experiment preparing (not production patch):** local source replaces
the BUSY gate with the previously working shim's per-frame MEM_CONTI/control/
PHY re-arm, 40 ms bounded TE wait, CFG/mutex pulse, START 0->1, 15 ms drain,
status clear and mutex stop. Retains corrected timer reads and 5 Hz throttle.
Counter named busy_skips means TE timeouts only in this diagnostic build.
Build ID 0x2306; originals saved in `20261025-display-0131/before/` and the
0x2305 kernel is preserved there. This source experiment is not yet a git
patch; do not mistake the modified local build tree for committed 0097. Local
build succeeded (Xcode 16.4, no CI); kernel SHA256 `1d9e24c54ff3d1a1f0eaef950e419c37fa544b06eafe88faa8d93a19972274b6`.
0131 boot SHA256 `0991ad412f2c4845f15ea4d6557b52b3a41f11b24e7875e780d6e9937d567efe`; 24-instruction cave
uses x12 for pushes, and guards the updated global layout. First launch
aborted read-only because device moved to Fastboot; fbraw reboot-recovery
returned OKAY. Runner will recheck Recovery/device/slot/full boot_a before
launch. No new write occurred during the aborted preflight.

**0131 hardware PASS relay, no visible change:** after successful re-preflight,
returned at `0xfffffe0007482770` in 33.76 s, x0 `0x8000000000000000`
(status BUSY, zero TE timeouts), x12/banner x16=2 pushes. User saw only REDMI.
Full boot_a restored/verified. Full shim sequence alone has not fixed display.

Next 0132 fills the verified mapped framebuffer with `0xff00ff00` (1440x3200,
18,432,000 bytes), forces the same refresh, waits 500 ms, then records live
DSI_INTSTA in x0 and pushes via x12. 27 guarded instructions fit precisely
in early-vector slot 14 after its relay stub. Image SHA256
`127532910603e26acd82b4c7d640921aa9eeb449ab4017e6dd8d5d02fd0a70c2`;
source/manifest/disassembly/embedded-payload validation in
`20261025-display-0132/`.

**0132 PASS relay / no green:** full-frame stores completed, forced refresh,
500 ms wait; live DSI_INTSTA `0x80000004` and 2 pushes. User still saw REDMI.
This rules out text-console enablement as the sole cause of no output.

**0133 PASS / FSM diagnosis:** DSI_STATE_DBG6 `0x00010008`, DBG7 `1`,
DEBUG_SEL `0x600`. CMCTL bits14:0 = `8`, which vendor
`mtk_dsi_cmd_mode_parse_state()` defines as "Waiting frame data from RDMA
for type-1 command". The engine remains BUSY waiting on its upstream path;
TE pulses are present. No new screen observation requested for this readback.
0132: image `127532910603e26acd82b4c7d640921aa9eeb449ab4017e6dd8d5d02fd0a70c2`, Recovery return 32.78 s, expected BRK and full boot_a restore verified.
0133: image `81a6da96390fafae2a6545fe0257c757970a143f81db699b0890edeed277bd8d`, Recovery return 32.77 s, expected BRK and full boot_a restore verified.

Next 0134 samples OVL0_2L FLOW_CTRL_DBG `0x240`, ADDCON_DBG `0x244`,
RDMA0_DBG `0x24c` after the same green-fill/rearm test.

**0134 no relay within 100 s:** user returned to Recovery, full boot_a
restored/verified. Image `bb23ba6b858b5d9e7070766cf085a60c64c0c83b2152077622b3c61a9ad40202`.
No OVL register result obtained. 0134 used a 64-bit read for the adjacent
FLOW_CTRL/ADDCON registers; unsupported bus width is one hypothesis, not a
proven cause. 0135 changes that single LDR to 32-bit, retaining the separate
32-bit RDMA0_DBG read. Trial launched, result pending. If the relay still
fails, consider a cpus=1 control to rule out a migrated checkpoint thread
(the banner MPIDR is the original shim handoff, not the checkpoint CPU).

 Do not infer a DSI hardware fault from the unchanged logo.
User has authorized ongoing tests ("你可以随时测试"); retain full restoration
and hash verification for each trial. Normal XNU still lacks `/sbin/launchd`.

## >>> ACTIVE 2026-10-25 (display): partial frame / color bars fix - BUILT, NOT FLASHED <<<

**New symptom (user): the panel now shows something, but only the top, then
color bars, with a grey block in the top-right.** This is progress past the
"stuck on logo" state: frames are being pushed, but torn/corrupt.

**Root cause (three overlapping faults, all in the refresh path):**

1. **D-cache never reached DRAM.** The boot hands `boot_args.Video.v_baseAddr`
   as a plain physical address (bit 0 clear). `video_console` already has the
   `makeMapping` write-combining fix (map anything below
   `VM_MIN_KERNEL_ADDRESS` as `VM_WIMG_WCOMB`), but *before* that runs, the
   early console draws through the bootstrap identity mapping into D-cache;
   only evicted lines reach DRAM, so the OVL scans a few top lines then
   garbage. Fixed by cleaning the framebuffer to the point of coherency
   (`dc cvac`, 64-byte lines) before each push while identity-mapped.
2. **In-flight frames were overwritten.** The old refresh waited for TE with a
   10 ms bound (too short for the ~16.7 ms TE), then forced the push anyway on
   timeout, and `DSI_START` was written as a level. The result is a torn
   frame. Fixed to mirror rubens-s-oss `mtk_dsi_poll_for_idle()`: poll
   `DSI_INTSTA` bit31 (`DSI_BUSY`, *not* FRAME_DONE bit4) with a 20 ms bound
   and **skip** the frame if the DSIM is still busy.
3. **`DSI_START` strobe.** `mtk_dsi_start()` writes 0 then 1; a bare 1 only
   works once per boot (already in the working tree).

**Code changed (build tree `xnu/out/local/xnu/`, mirrored to
`research/matisse/20261025-usb/display-wip/`):**

- `osfmk/arm64/sweet_matisse_dsi.c`: added `disp_clean_framebuffer()`
  (`dc cvac` guarded by `disp_fb_needs_clean`); rewrote
  `sweet_display_refresh()` to poll `DSI_INT_BUSY` and skip when busy; 5 fps
  throttle (was 20); `sweet_display_set_target(va,phys,stride,height)`
  replaces the old `sweet_display_probe_va()` magenta-block probe; new
  counters `sweet_disp_busy_skips` / `sweet_disp_status` (replaces
  `sweet_disp_te_timeouts`); mutex now only toggles `EN` (LK's MOD/SOF route
  is left untouched).
- `osfmk/arm64/sweet_matisse_dsi.h`: declaration/stub renamed to
  `sweet_display_set_target`; exported counters updated.
- `osfmk/console/video_console.c`: call site now `sweet_display_set_target`
  (the WC remap in `initialize_screen` already existed).
- `bsd/dev/sweet_ufs.c`: `SWEET_BUILD_ID 0x2301 -> 0x2302`; mark 92 now dumps
  `busy_skips`/`status` instead of `te_timeouts`/`pushes`.

**Build + artifacts (host, nothing written to the phone):**

- Kernel `xnu/out/local/fakeroot/System/Library/Kernels/kernel.development.sweet`,
  16,705,840 B, SHA256 `10582345406be54d6a7fdce0fd36c5601235118098959d412a846736724de62f`.
  New symbols `_sweet_display_set_target`, `_sweet_disp_busy_skips`,
  `_sweet_disp_status` present. Built with
  `DEVELOPER_DIR=~/Downloads/Xcode.app/Contents/Developer tools/build-xnu-local.sh xnu/out/local kernel`.
- Payload `research/matisse/20261025-usb/matisse-xnu-0111-cacheclean.payload`,
  16,701,664 B, SHA256 `77c6a9d467577b96c053b630bd0cead4500dc4824595918a48da4b1e264baa43`
  (ADT `matisse-usb.adt`, cmdline unchanged).
- Boot image `research/matisse/20261025-usb/entryprobe-el1-xnu-0111-cacheclean.img`,
  26,615,808 B, SHA256 `e1bfa8124c4f2bd872c68a83bbe45ebec77283db115f3c9cc1f37db0673ef9e5`.

**High vector offset correction.** The local-build high exception table is at
**`-0x3488`**, not `-0x4488` (the `-0x4488` in older notes was for CI-era
kernels). `mkentryprobe` refuses `-0x4488` ("expected branch/NOP padded high
exception slots"); the correct table is the 12-branch + 4-NOP table at
`-0x3488` (the 4 NOPs are the AArch64 EL0_32 slots). Early table stays
`0xb78`. The 0111 image's resolved vector fields byte-match the 0110 json.

**Next: hardware test (needs explicit user approval to write `boot_a`).**
Flash `entryprobe-el1-xnu-0111-cacheclean.img` via recovery `dd`, then read
`tools/sweet-marks.py --pull`. Read mark 92 (`a`=`busy_skips`, `b`=last
`DSI_INTSTA`): `busy_skips` ~= pushes and `status` bit31 stuck set means the
DSIM never reports idle on this command-mode path and the skip starves the
panel (then re-enable TE pacing); `busy_skips` low + pushes climbing means the
busy poll works and the cache-clean should show a full, stable frame. Marks
70..85 confirm `sweet_display_init()` still accepts LK's state.

## >>> ACTIVE 2026-10-25 (display): why the panel stays on the boot logo <<<

**Short answer: the kernel never gets a frame onto the DSIM, and the code that
was supposed to try had never been reachable.** Everything below is measured
on the phone with the new boot progress marks (see the USB section) plus the
shim's own display probe; none of it is inferred from datasheets.

**What is already correct.** `sweet_display_init()` accepts LK's state on this
panel (`sweet_matisse_dsi.c`, dumped as marks 70..85, one boot):

    stage 9 (all gates passed)   width 1440  height 3200  stride 5760
    clk gates 0/0/0 (all on)     DSI mode 0  PSCTRL 0x2c0505a0 (DSC)
    SIZE_CON 0x0c8001e0          VACT 0x0c80  BUF_CON0 1 (cmd FIFO on)
    INTSTA 0x4 (TE_RDY set)      OVL_EN 0xe00001
    OVL_L0_ADDR 0xfcb3f000 == OVL_L0_PITCH 0x1680 == ADT reg[0]

So LK leaves exactly the documented command-mode DSC state, the panel still
sends TE, and the OVL is scanning the surface the ADT names. `initialize_screen`
is reached, `gc_initialized && gc_enabled` is true, and `vcputc_options()`
really draws (mark 86 counted 4588 console characters).

**Three real bugs found on the way, all fixed in the working tree**
(`research/matisse/20261025-usb/display-wip/` holds the exact sources):

1. `sweet_display_refresh()` had drifted away from the sequence that was
   hardware-validated in `shim/display.c`: it did not re-arm `DSI_MEM_CONTI`
   (0x90 = 0x3c), `DSI_CON_CTRL`/PHY per frame, and it dropped the 15 ms
   panel-drain + mutex stop.
2. `DSI_START` is a **strobe**, not a level: vendor `mtk_dsi_start()` writes
   0 then 1. Writing only 1 works once per boot and then every later frame is
   silently dropped. This is directly observed: the shim's own `display-kick`
   probe draws a *moving* green bar, and on this device the bar **appears but
   never moves** (user-confirmed) - exactly one frame per boot.
3. Mirroring the shim sequence into the kernel made boot unusable: 40 ms TE
   bound + 15 ms drain per frame, called from every console character, is more
   than 100% of the CPU at 20 fps and the watchdog resets before `bsd_init`
   finishes. Nothing after build 9 reached the mark channel at all (the mark
   block stayed byte-identical to build 9's, which is how this was caught).
   Even at 10 fps it did not reach it, so the per-frame re-arm itself is
   suspect on this IP and was reverted.

**Also worth knowing (not yet proven either way):** `video_console` receives
`boot_args.Video.v_baseAddr` = `0xfcb3f000`, i.e. a plain physical address with
bit 0 clear. XNU's convention is that bit 0 set means "physical, map it
yourself" (`makeMapping` in `initialize_screen`); with bit 0 clear it uses the
value as a *virtual* address, so console draws go through shim/bootstrap
identity mappings instead of a write-combining kernel mapping. Forcing
`makeMapping` for addresses below `VM_MIN_KERNEL_ADDRESS` compiled but that
build also never reached the mark channel, so it is untested, not disproven.
The cheap alternative is one line in `shim/loader.c`: set
`ba->Video.v_baseAddr = brd.fb_base | 1`, and mask bit 0 in
`sweet_early_init()` where the same field is used as a physical address.

**Current tree state: bootable baseline.** `sweet_display_refresh()` is back to
the pre-experiment body plus the DSI_START strobe and a TE-timeout counter
(mark 92, `a` = timeouts, `b` = pushes). Build and flash that first: if marks
reach `sweet_ufs_init` again, the baseline is good, and mark 92 then answers the
one question that decides the next move - whether the panel still pulses TE
while the kernel is pushing. Timeouts > 0 means the DSIM link is dead by the
time XNU runs and the panel needs a real re-init (PLL/PHY, `mtk_mipi_tx.c`;
`DSI_TXRX_CTRL`, DSC table), not more frame triggering.

**Operational notes for display work specifically.** A 64 KiB
`ml_io_map_wcomb(fb_phys, 0x10000)` fill inside `sweet_display_init()` (early,
before `initialize_screen`) is enough to stop the kernel dead - no marks at
all. Do not touch the framebuffer from there; do it after `bsd_init` if needed.
`--level display-kick` is the only display check that does not depend on XNU:
its green bar appearing proves the panel accepts a frame at shim time.

## >>> 2026-10-25 (USB): local build + progress marks; the logo loop is not USB <<<

**Local XNU build works without a KDK and without CI.** `xnu/out/ci-40115544522`
turned out to be a *complete* build tree (sources, generated headers, every
`.o`, `fakeroot`), so a rebuild is incremental: 10-20 s for one file plus the
link, instead of a 45-minute full build. `tools/build-xnu-local.sh <tree>`
does it:

- Xcode 16.4 lives at `~/Downloads/Xcode.app`; `DEVELOPER_DIR` is honoured, and
  `xcode-select -s` is *not* needed (it would require sudo, which this account
  does not have).
- The tree's generated Makefiles and `.d` files hard-code the CI path
  `/Users/runner/work/ios-sweet/ios-sweet/dxb`. Rewriting that prefix to the
  local tree (1129 text files) is what makes `make` work at all - without it
  every rule fails with "No rule to make target .../runner/...".
- `ctfconvert`/`ctfmerge` are not in Xcode; they come from the CI
  `xnu-linklibs` artifact (`xnu/out/ci-40101113289/xnu-linklibs/linklibs.tgz`,
  together with the real `libfirehose_kernel.a`, which goes into
  `fakeroot/usr/local/lib/kernel/`).
- Xcode 16 dropped `usr/lib/libcc_kext.a`; `-lcc_kext` still resolves through
  clang, and the kernel links.
- The dSYM step copies LLDB's Python macros with `env python`, which does not
  exist; the build script installs a no-op `python` shim so `make install`
  finishes. It is cosmetic only.
- Segments of the locally linked kernel are byte-for-byte the same *sizes* as
  the CI kernel (`__TEXT` 1441792, `__TEXT_EXEC` 8749056, `__DATA` 5488640);
  only `__LINKEDIT` differs. It boots, which the marks below prove.

**The shim's vector offsets move with every rebuild.** `mkentryprobe` refuses a
stale `--xnu-high-vector-offset` ("expected branch/NOP padded high exception
slots"). `tools/xnu-vector-offsets.py NEW.payload [--ref OLD.payload]` prints
both offsets; the early table stayed at `0xb78` and the high table at
`-0x3488` across three rebuilds, but check it every time.

**New: boot progress marks (uncommitted, `bsd/dev/sweet_ufs.c` `sweet_mark`).**
No console exists on this board, and the persistent log ring cannot help
(two independent reasons: it is fed from `_cnputs()`, which never runs without
a console, and `ufs_write_blocks()` refuses everything while `ufsrw=0`). A mark
appends one 24-byte record to a BSS array and rewrites it into the **last block
of userdata**, bypassing `su.writable` on purpose - that one block is inside
the log ring area, so no filesystem block is touched. Read it back with
`tools/sweet-marks.py --pull` (works in recovery, no root needed beyond adb).

**Result of run 0095/0096/0097 (three boots, all restored):**

| marks | meaning |
| --- | --- |
| 10-12 | userdata geometry known, USB probe entered and **returned** |
| 1-15, 20-24, 30-42 | MTU3 probe, DMA, ifnet, full `mt_hw_init`, **soft connect** |
| 50, 55, 51 | `bsd_init` -> `vfs_mountroot` -> **root mounted** |
| 53, 54 | `IOSecureBSDRoot`, root vnode |
| 60, 62, 65 | `load_init_program` entered |
| 63 (i=0, errno 2), 63 (i=1, errno 2) | candidates tried, **ENOENT** |
| 64 (i=2, errno 2) | about to `panic("Process 1 exec ... failed")` |

Three corrections to what this project believed:

1. **The MTU3 driver does not hang.** It runs to the very last statement of
   `mt_hw_init()` and `sweet_usb_probe()` returns normally. The earlier
   "failure is at or before soft-connect" inference was wrong: the absence of
   host enumeration is not evidence of a hang.
2. **The REDMI-logo loop is not caused by USB.** Boot reaches `launchd` exec;
   the 64 MiB HFS+ test volume has no `/sbin/launchd`, `execve` returns ENOENT,
   the kernel panics and the watchdog resets the board ~31 s later. This is the
   already-known "next blocker: a real root image" - the same loop would happen
   with `sweetusb=0`. Together with `sweetusb=1` also looping, that closes the
   case: nothing about the USB driver is involved in the loop.
3. **The host sees nothing at all**, not even a failed enumeration: `log show`
   over the run window has no USB event, and `ioreg` never lists `0x1209`.
   With `SOFT_CONN` (bit 6) set in `U3D_POWER_MANAGEMENT` (read back as
   `0x64e1`), the pull-up is asserted in the controller, so the D+/D- pair is
   not reaching the host. The prime suspect is the **MT6363 MUIC/USB switch**:
   on MediaTek boards the PMIC routes the port's data lines to either the AP
   or the charger, LK only sets that up for fastboot, and a normal boot never
   asks for it. The ADT has **no MUIC node** (`/sweet-usb` is the only USB
   node), while patch 0094 already has a working SPMI/PMIF path to MT6363, so
   this is reachable but is new work: read the vendor MUIC register map, add a
   `/sweet-usb-switch` (or extend `/sweet-usb`) with the SPMI address, and put
   the port in USB/device mode before soft-connect.

**Operational lessons (both cost a run):**

- `restore-boot-a.py` used to restore over **adb** as soon as adb was up, so
  one run was destroyed by it: it rewrote `boot_a` one second after the test
  image was written and before the reboot, and the probe never executed. It is
  now **fastboot-only** by default (`--allow-adb` to override); adb being up
  means the phone booted the image that is in `boot_a`, so touching it is
  pointless.
- Write images with recovery `dd` from `adb push`; `fastboot boot` is rejected
  by this ABL, and a bare `fastboot reboot` boots the stock path and fails AVB
  in a few seconds (looks like "faster reboot").

**Next, in order:** (a) `sweetusb=3` diagnostic that reads back
`U3D_POWER_MANAGEMENT` after the soft-connect write and marks `IPPC_OTG_STS`
(VBUS) and `PW_STS1/2` - one run, tells whether VBUS is even seen;
(b) the MUIC work above; (c) only then the network side of the driver.

## >>> 2026-10-25 (keys): MT6363 PON keys + keypad volume-down (patch 0094) <<<


**Numbering.** This landed as `0093-sweet-mt6363-keys.patch` at 03:50 and was
CI-validated as such (run 40127176212); a parallel session then produced
`0093-sweet-log-readonly.patch` (04:00, sweet_ufs.c only, uncommitted at the
time of writing), so this patch was renamed to **0094** to keep one patch per
number. Only the filename changed - the diff and the built kernel are the
same.

**Request (user): "帮我移植按键功能" then "设备在线 你可以直接参考设备的".**
sweet's `bsd/dev/sweet_keys.c` polls the Qualcomm PM6150/PM6150L SPMI
arbiter; matisse has neither that arbiter nor those GPIOs, so the driver had
to be re-hosted, not recompiled.

**Measured on the device (OrangeFox, root adb, nothing written):**

- `/proc/bus/input/devices`: `mtk-pmic-keys` at
  `1c015000.spmi/spmi-0/0-04/mtk-pmic-keys` reports KEY 0x73 (115,
  volume-up) and 0x74 (116, power) - the DTS child called `home` is wired to
  volume-up, `power` is PWRKEY. `mtk-kpd` at `1c00e000.kp` reports only KEY
  0x72 (114, volume-down). Touch is `fts` on SPI6.
- `mount -t debugfs none /sys/kernel/debug` works in recovery, so
  `/sys/kernel/debug/regmap/0-04/registers` exposes the whole MT6363 map:
  `0x0009 = 0x63` (the id in `probe chip id=0x63`) and `0x001e
  TOPSTATUS = 0x1e` at rest (bit2 = CHRDET, charger attached).
- Sampling `0x1c..0x21` at ~10 Hz while the operator pressed keys showed
  exactly two bits dropping, never together: **bit1 (0x1c)** and **bit3
  (0x16)**. MT6359's mainline masks are PWRKEY `0x2` (bit1) and HOMEKEY
  `0x8` (bit3); the vendor MT6363 entry (`0x1`/`0x3`) is dead code because
  that chip takes the release-IRQ path and never reads the debounce
  register. So bit1 = PWRKEY = power, bit3 = HOMEKEY/RESIN = volume-up,
  both active low.
- **Unfinished:** the run was cut short when the phone dropped off USB (the
  operator held power; `adb` and `fastboot` both empty afterwards) before
  `dmesg | grep "key ="` could be correlated with the samples. That
  correlation is what would *name* the two bits instead of inferring them
  from MT6359. Repeat: sample
  `sed -n 31p /sys/kernel/debug/regmap/0-04/registers` with `/proc/uptime`
  next to it, press one key at a time, then match the `(pressed) key =116`
  lines' timestamps. The ADT carries `power-bit`/`volup-bit`, so a swap
  costs a new payload, not a new kernel build.

**Driver (patch `xnu/patches/0094-sweet-mt6363-keys.patch`,
`bsd/dev/sweet_mt_keys.c`).** `sweet_keys_init()` keeps its name and now
tries `sweet_mt_keys_start(level)` first; it returns 0 when the ADT has no
`/sweet-keys` node, so sweet still runs the Qualcomm path unchanged.

- Power/volume-up: poll MT6363 `TOPSTATUS` (0x001e) over the MT6983 PMIF at
  `0x1c015000`. Register map is the vendor `mt6xxx_regs` table, AP software
  interface channel 2 (`soc_chan = 2`): `STA 0x8a8`, `ACC 0x880`,
  `RDATA 0x894`, `VLD_CLR 0x8a4` - re-derived from the enum in
  `spmi-mtk-pmif-core.c`, not from the table's textual order. Each read is
  the vendor FSM: wait `SWINF == IDLE`, write
  `(3 << 30) | (sid << 24) | (bc << 16) | addr` to ACC (extended register
  read long, the opcode an `reg_bits = 16` regmap uses), wait
  `SWINF == WFVLDCLR`, take RDATA, write 1 to VLD_CLR.
- Init writes are the vendor probe's own values (`INF_EN`/`ARB_EN` =
  0xffffffff, `CMDISSUE_EN` = `INIT_DONE` = 1); LK normally leaves them so
  no clock, regulator or IRQ work is done. `sweetkeys=1` reports only.
- Volume-down: read `KP_MEM1..KP_MEM5` (0x04..0x14, u16) of `kp@1c00e000`
  and take bit 0 of MEM1, active low, per `mtk-kpd.c`
  (`pressed = (state & mask) == 0`). The bootloader keymap
  (`mediatek,hw-init-map = <114 0 ...>`) puts volume-down at index 0. If
  `KP_EN` bit 0 is clear the driver sets it; all-zero MEM registers mean
  "not scanning" and are ignored. `sweetkpd=0` skips the block.
- 20 ms poll from one kernel thread with a 2-sample (40 ms) debounce; a
  failed SPMI read keeps the previous state instead of inventing a release.
  Every edge prints `SWEET MT KEYS: <name> down=<0|1> topstatus=0x..`.

**Tooling.** `tools/mkadt.py --board matisse` emits `/sweet-keys`
(`compatible mediatek,mt6363-keys`, `reg = 0x1c015000 0x900 0x1c00e000
0x1000`, `spmi-sid 4`, `power-bit 1`, `volup-bit 3`, `voldown-index 0`).
`tools/mkpayload.py` moves `sweetkeys` from the pinned-off list to a range:
0 off, 1 report only, 2 default. 63 host tests pass, and the patch applies
cleanly on the 0092 tree; `validate-repo.py` still fails only on the
pre-existing `[[ ]]` shell syntax in 0019/0020/0026.

**CI.** Run **40127176212** (`10a6412`, Jinsens `codex/matisse-xnu-screen-log`)
**succeeded** in 9m33s. Kernel `xnu/out/ci-40127176212/kernel.development.sweet`,
17,223,696 B, SHA256 `d7630599ec9041d8dc766016aad6e512601d7ed7e5e58ab921a2b51449b70615`
(matches `SHA256SUMS`). `_sweet_mt_keys_start` is linked at
`0xfffffe00074eab68` and the image carries 8 `SWEET MT KEYS` strings. Built,
**not** packaged into a payload and **not** flashed.

**Local clang check is not a signal here.** With CLT 17's SDK, `sys/param.h`
-> SDK `string.h`/`refcnt_internal.h` fail identically for the existing
`sweet_keys.c` and the new file (13 errors each), i.e. the environment, not
this code. CI is the gate.

**Next.** (1) Finish the bit naming above in recovery. (2) A hardware boot
needs one observability decision first: `sweet_log_start()` refuses to flush
unless `su.writable` and the matisse policy pins `ufsrw=0`, the framebuffer
console is dark (0085 disabled) and the MTU3 live log is unproven - so a
keys boot either allows `ufsrw=1` for the 4 MiB ring in userdata or gets a
BRK cave probe. Writing `boot_a` needs explicit approval. (3) HID only
reaches something once a real iOS root runs; on the 64 MiB HFS test volume
`sweet_hid_key()` has no consumer and the log lines are the whole proof.

**Note on 0093 (parallel work).** The other session's
`0093-sweet-log-readonly.patch` drops the `su.writable` gate, i.e. exactly
the blocker in (2): with it the ring flushes at `ufsrw=0`, so a keys boot
can be read back from recovery without making the root writable. Read the
ring with `tools/sweet-log-pull.sh` and look for `SWEET MT KEYS:`.

## >>> ACTIVE 2026-10-25 (USB): first boot FAILED - no enumeration, 31 s logo loop <<<

**Two more runs since the first one, both with the persistent log forced on -
and the log stayed empty.** `0093`'s gate can be removed without a build by
NOPping `cbz w9` at VA `0xfffffe00074e8c84` (the `su.writable` test in
`sweet_log_start()`, inlined into `sweet_ufs_init`); `patch-log-on.py` rewrites
the payload and refuses if the byte is not the expected `0x34000349`. The
patched payload was verified *inside the built image* (`1f2003d5` at file
offset 5,132,404):

- `sweetusb=2` + log (`entryprobe-el1-xnu-0092-usb-log.img`, `c9171532...`):
  looped; log area **all zero**.
- `sweetusb=1` + log (`entryprobe-el1-xnu-0092-usb1-log.img`, `e3f1f45b...`):
  **also looped**; log area **all zero** again.

So removing the write-protection gate is *not* sufficient on this board. The
area is never even given a header, which `sweet_log_thread()` writes on every
flush where `total != flushed`; either the thread never starts (boot dies
before `sweet_ufs_init()` reaches `sweet_log_start()`) or the ring never
advances because `sweet_log_append()` is only called from `_cnputs()` and no
console is attached here. **Do not rely on 0093 alone for the keys log** -
confirm with a boot whose mountroot is known good before trusting it.

**`sweetusb=1` (register reads only, no controller start) still loops**, so
the hang is not inside the QMU/EP0 pulse code: either reading the IPPC/MAC
window wedges the bus, or the boot fails after mountroot for a reason that has
nothing to do with USB. The empty log cannot separate those yet.

**Local build is blocked on Xcode, not on patience.** `brew install jq gum
bash cmake ninja` succeeded (bash 5.3.20, cmake 4.4.4, gum 2.0.2, jq 1.8.2,
ninja 1.13.2). This machine has CLT only - no `xcodebuild`, no `iig`, and
`build.sh` needs both (`xcrun --find iig`); Xcode 15.x is required because
Xcode 16's `iig` emits `IORPC.kernelContent`, which xnu-8796 lacks. `xcodes`
cannot be installed unattended: Homebrew ships no bottles for Intel x86_64 any
more, so it builds from source, and fetching Xcode needs an Apple ID login.

**Run 1 (approved): `entryprobe-el1-xnu-0092-usb.img`, SHA256 `d0c37b35...`,
written into `boot_a` with recovery `dd`.** Result: the phone looped at the
REDMI logo and **no `idVendor 0x1209` device ever appeared on the host** over a
2-minute watch; `adb` never returned. The run script was cancelled before its
restore step, which left the test image in `boot_a` and produced the loop the
user saw - a cancelled run must be treated as "phone still armed".

**Recovery that worked:** hold Power+Volume Down -> `fastboot`,
`fastboot flash boot_a backup/recovery-20261021/boot_a-live-20261021.img`,
then `fastboot reboot recovery`; `boot_a` re-verified `2931647a...` over adb.

**Operational facts (learned the hard way):**

- `fastboot boot` is **rejected** by this ABL (`Booting FAILED (remote:
  'unknown command')`); a test image can only go into `boot_a`.
- `fastboot flash` after another large write in the same session fails with
  `usb_write failed with status e0004061` / `e00002d9`. One big write per
  fresh, hand-entered fastboot session.
- `fastboot reboot` (plain) makes the bootloader treat the recovery image as a
  normal boot and fail AVB within seconds - that fast loop is not the XNU
  test. Always `fastboot reboot recovery`.
- A watchdog reset re-boots `boot_a`, so a hung XNU re-enters the same shim
  forever: expect one manual Power+Volume Down per test, then
  `research/matisse/20261025-usb/restore-boot-a.py`.

**Ruled out by reading after the run:**

- `ml_io_map()` handles an unaligned base - `osfmk/arm/io_map.c` returns
  `start + phys_addr - trunc_page(phys_addr)`, so `ml_io_map(0x11203e00,
  0x100)` really points at IPPC.
- `mt_if_create()` is line-for-line `ud_if_create()`, and the
  `kmem_alloc_contig(... PAGE_MASK, 0, 0, KMA_DATA|KMA_ZERO|KMA_PERMANENT,
  VM_KERN_MEMORY_IOKIT)` + `pmap_find_phys` pair is identical to the sweet
  driver that works on hardware.
- So the only never-run-on-this-SoC code before the D+ pull-up is
  `mt_hw_init()`.

**Inference from "no enumeration":** reaching the last statement of
`mt_hw_init()` (`POWER_MANAGEMENT |= SOFT_CONN|SUSPENDM_ENABLE`) holds the
pull-up for the whole 31 s watchdog window even with the CPU halted. Caveat:
a port that never completes the host's reset also produces no `ioreg` node,
so "nothing listed" only proves the host never *reset* the device, not that
D+ was never pulled up. With that caveat the failure still sits at or before
soft-connect: either a bus stall/fault while driving IPPC/MAC (the
`DEV_RST_CTRL` device-function reset is the only step that changes hardware
state LK established), or that reset clears `DEVICE_CONTROL` (LK left `0x99`,
DC_SESSION=1) so the port never electrically connects.

**Run 2 (approved, ran, banner unread):**
`entryprobe-el1-xnu-0092-usb-mtthread-brk.img`, SHA256 `d2f72e5b...` - same
payload with `BRK #0x5357` at `_mt_thread` (`0xfffffe00074f0800`, replacing
`sub sp, sp, #0x130`). A record whose `pc` is that VA means bring-up finished
and only the poll loop is left to explain; no record means the fault is in
`mt_hw_init`. The phone looped again and then came up on its own (probably the
ABL retry counter falling back to slot B), so the banner has not been read;
`boot_a` may still hold the BRK image.

**Tooling added:** `run-usb-boot.py` (verify/write/readback/restore plus a
host `0x1209` watch, now SIGTERM-safe), `restore-boot-a.py` (fastboot or adb
restore, then reboot recovery and grep dmesg), `watch-usb.py`.

## >>> 2026-10-25 (USB): pre-boot audit; image rebuilt on the 0092 kernel <<<

**Request (user): "再继续推进 USB 移植功能".** Driver `0090-sweet-mtu3-usb.patch`
is unchanged since commit `a686a6a`; this pass is the pre-boot audit plus a
fresh image built on the current kernel, not new driver code.

**Audit against the vendor source** (`research/matisse/kernel-rubens-oss/drivers/usb/mtu3`,
`research/matisse/linux-mtu3`) found the register work faithful - no change made:

- IPPC/EPCTL/USB2-CSR offsets, `EP0CSR`/`TX*CSR`/`RX*CSR` field masks,
  `QMU_Q_*`, `QMU_TX_ZLP`/`QMU_RX_COZ`, `DEV_ADDR` shift 24, `DMAREQEN`,
  `EP_RST` bit layout all match `mtu3_hw_regs.h`.
- GPD encoding matches `mtu3_qmu.c`: gen2cp TX carries buf-high in dw0[27:24]
  and next-high in dw0[31:28], RX in dw3[27:24]/dw3[31:28]; RX buffer length
  is `(len & 0xfffff) << 12`; IOC|HWO set last after a `dmb`.
- EP0 follows `mtu3_gadget_ep0.c`: SETUP ack with `SETUPPKTRDY|DPHTX`, TX
  pump waits for `TXPKTRDY` to clear before `DATAEND`, RX acks `RXPKTRDY` and
  ends on a short packet, no-data requests ack in the status stage.
- Bring-up order matches `mtu3_hw_init()`: `device_reset` (IPPC DEV_RST bit0)
  *before* `device_enable`, then `csr_init`, `DEVICE_CONF=0`, VBUS force,
  `QFCR` (gen2cp), TXDEEMPH, then HS-only speed and soft connect.
  `is_u3 = DEV_CAP[7:0]`, `gen2cp = HW_SUB_ID[31:16] >= 0x1003` are the same
  expressions the vendor uses (probe showed trunk 0x1006, so gen2cp).
- FIFO split (base 0 for U3 IP, 64 B + halved for U2 IP), slot 2 (U3) / 1 (U2)
  for bulk and 0 for the interrupt EP match `mtu3_fifo_init()` / `mtu3_ep_enable()`.
- A bus reset does not need EP0 maxp re-programming: `mtu3_state_reset()`
  only clears software state, so the MAC keeps `EP0CSR.maxpacket`.

**Two blind spots recorded, not fixed:** the driver never programs
`COMMON_USB_INTR_ENABLE` (0x2418) or `DEV_LINK_INTR_ENABLE` (0x0850), so
bus-reset and speed-change *status* are only trusted to latch with the
vendor's enables written; and it does not re-read `MISC_CTRL[31]`
(DMA_ADDR_36BIT) after the device reset. The vendor only ever *reads* that
bit to pick a 36/32-bit DMA mask, i.e. it is a bootloader strap, so the
36-bit GPD encoding should hold - worth confirming before believing a DMA
fault.

**Observability on this board is thin.** `sweet_log_start()` refuses to flush
unless `su.writable`, and the matisse payload policy pins `ufsrw=0`, so the
4 MiB persistent console ring in userdata is off; the framebuffer console is
dark (0085 disabled); `shim/diag.c` notes log_store access hung on hardware.
The only hard signal is **host USB enumeration**. If a run shows nothing, the
next step is a BRK cave probe in the poll thread (like
`tools/xnu_smp_irqprobe.py`) that dumps the `mt` struct, not another blind boot.

**Built and verified (not flashed).** `research/matisse/20261025-usb/`:
- `matisse-xnu-0092-usb.payload`, 16,629,568 B, SHA256 `b1ca2d52...`, from
  the 0092 kernel `68781200...` (`xnu/out/ci-40124596123`), cmdline
  `debug=0xc serial=0 cpus=8 keepsyms=1 -enable_kprintf_spam rd=ufsroot0
  ufsrw=0 ufscache=1 -noprogress sweetkeys=0 sweettouch=0 sweetbattery=0 sweetusb=2`.
- `entryprobe-el1-xnu-0092-usb.img`, 26,578,944 B, SHA256
  `d0c37b35...`, usual el1-xnu recipe (vector `0xb78`, high `-0x4488`,
  TTBR0 `0x10117c000`, clean limit `0x108000000`, `--ufs-init --ufs-query full`,
  template `backup/boot_a-stock.img`). Payload verified byte-for-byte at
  decompressed offset 48,947,216; `/sweet-usb` present with
  `reg = 0x11201000 0x2e00 0x11203e00 0x100`; kernel carries 24 `SWEET MTU3`
  strings.
- `run-usb-boot.py NAME IMAGE SHA` replaces `run-approved-probe.py`: same
  verify-write-readback-restore discipline, but it also polls the host USB
  tree for `idVendor 0x1209` and new `en*` interfaces while the image runs,
  and records the time-to-appear. Live boot_a hash checked read-only first
  (`2931647a...`, matches the backup).

**Phone state:** in recovery, boot_a == `2931647a...`. Nothing written.

**Next:** user approval for one `boot_a` write + boot of
`entryprobe-el1-xnu-0092-usb.img`, watched with `run-usb-boot.py`.

## >>> ACTIVE 2026-10-25 (cache, 0092): report ADT geometry when measurement is absent <<<

**Request (user): the ADT/topology/hw.l3cachesize/do_cacheid bullets ending
with "帮我解决而且现在已经完成一部分了".** Status of each item, split into
already-landed and new work:

- **ADT sizes** - landed in `6b7d1da`. `tools/mkadt.py` writes
  `l2-cache-size`/`l3-cache-size` on every matisse CPU (256K A510, 512K A710,
  1M X2; 8M shared L3) and marks cores 0-3 `cluster-type='E'`, 4-7 `'P'`.
  `ml_parse_cpu_topology()` therefore fills `cpu->l2_cache_size/l3_cache_size`,
  so SweetCPU's `ml_processor_info_t` is no longer zero. Test:
  `tools/tests/test_mkadt_boards.py::test_matisse_eight_cpus_and_timer`.
- **`hw.l3cachesize`** - `0089` already replaced the unconditional
  `0xFFFFFFFF` with the measured `c_l3size`; `0091` fixed the FEAT_CCIDX
  decode that made every value wrong. `hw.l3cachesize` returns `EINVAL` only
  when the size is genuinely unknown.
- **do_cacheid() per cluster** - `0089` samples every core of a cluster type
  and keeps the largest private L2 (A710 512K vs X2 1M), so the boot A510 is
  no longer the only core measured for the P cluster.
- **Heterogeneous reporting** - E/P types + `MAX_CPU_CLUSTERS 2` are in
  `0089`; `ml_processor_register` keeps every CPU in pset0 (the non-edge
  clutch scheduler has one hierarchy). `hw.nperflevels` = 2,
  perflevel0 = P, perflevel1 = E.

**Gap found while auditing (fixed here, patch
`xnu/patches/0092-sweet-cache-report-fallback.patch`):**

1. `ml_cpu_get_info_type()` answered only from `cpuid_cache_info[]`, so a
   cluster type that had not measured yet reported L2/L3 = 0 and then
   `0xFFFFFFFF`. It now falls back per cluster type to the largest ADT
   `l2-cache-size`/`l3-cache-size`, and only returns `0xFFFFFFFF` when the ADT
   has no value either. Measured geometry still drives cache maintenance and
   `vm_cache_geometry_colors`.
2. `cache_info_type()` sleeps until `c_valid` for a non-boot cluster type.
   With `cpus=4` the P cores never run `do_cacheid()`, so any
   `hw.perflevel0.*` read would sleep forever. It now returns the empty entry
   when `cpuid_cache_info_bitmap` shows that no core of that type has ever
   entered `do_cacheid()`; the ADT fallback above then answers. Cache line size
   falls back to the boot cluster's (uniform 64 B on this SoC).
3. `hw.cachesize[2]` used `cache_info_type()->c_l2size`, which on this board is
   the shared L3 (do_cacheid selects CSSELR_L3 when CLIDR.Ctype3 == 4). Under
   SWEET it now reports the private L2 of the lowest perflevel, matching the
   meaning of that array entry.

**Verified locally.** 0092 applies forward and reverse cleanly; `clang
-fsyntax-only` with the exact ci-40115544522 flags (extracted from the run log,
CLT SDK substituted for the Xcode SDK) gives 0 errors for `cpuid.c`,
`machine_routines_common.c` and `kern_mib.c`, and no new warnings at the edited
lines; all 63 host tests pass. `tools/validate-repo.py` still fails on
pre-existing `[[ ]]` shell syntax in 0019/0020/0026, unrelated to this change.

**CI run 40124596123 (0092): success**, artifact
`xnu/out/ci-40124596123/kernel.development.sweet` (17,239,952 B, SHA256
`68781200ce96...`). The log shows `Applying patch:
.../patches/0092-sweet-cache-report-fallback.patch`; `_sweet_topology_cache_size`
is inlined into `_ml_cpu_get_info_type`, so the kernel size is unchanged.

**Hardware probe PASS (2026-10-25, approval: "上实机测试一下是否能够使用").**
`research/matisse/20261025-cache-0092/`: ADT, payload, BRK manifest,
`entryprobe-el1-xnu-0092-cache-brk.img` (26,578,944 B, SHA256 `1ced03d9...`),
readback/restore images. The runner rewrote 64 MiB, verified
`07d2c66a...`, restored `2931647a...` and re-verified. One record:

```
SWEET-ENTRY v1 ... far=fffffe1019310000 pc=fffffe000748d73c esr=00000000f2005357
x0=0008000000800000 x16=0010000000000000
```

Decoded (cave VA `0xfffffe000748d714`, checkpoint `0xfffffe00077713a4`):

- E (A510): private L2 `0x80000` = **512 KiB**, L3 `0x800000` = **8 MiB**.
- P (A710/X2): private L2 `0x100000` = **1 MiB**, L3 **0**.

So the CCIDX fix (0091) produces real geometry (the 0089 values `0x200`/`0x400`
are gone), per-type sampling works (P's 1 MiB differs from E's 512 KiB), and
**P really has `c_l3size == 0`** - it is not the race suspected earlier. That
makes 0092's ADT fallback load-bearing: without it `hw.perflevel0.l3cachesize`
would be `0xFFFFFFFF` and the sysctl would return `EINVAL`.

The probe also shows the measured A510 L2 is 512 KiB, not the 256 KiB the ADT
claimed; `tools/mkadt.py` and its test now say `0x80000` (measured geometry is
still what drives coloring and cache maintenance; the ADT only answers
reporting before/without a measurement).

**Not exercised on hardware:** the fallback itself is only reachable through
`ml_cpu_get_info_type()`, and there is no userland to read
`hw.perflevel0.l3cachesize` yet. A second cave that `bl`s
`_ml_cpu_get_info_type` would prove it but needs a kernel-stack frame at the
checkpoint; not done here.

**Not done / next:** any further boot_a write needs new explicit approval; the
0092 approval is consumed by the run above.

**`sctlr` in SWEET-ENTRY is a handoff value.** It is SCTLR_EL1 at the shim
entry point (the probe clears M/C/I first, hence `0x30d00980`), not XNU's
running state; `tools/mkentryprobe.py` now says so next to the field list,
and the bring-up checklist tells readers to use `pc`/`esr`/`far` for kernel
checkpoints.

## >>> ACTIVE 2026-10-25 (cache): E/P L2/L3 probe - FEAT_CCIDX truncation, patch 0091 <<<

**Request (user): "L1、L2、L3 都全开了吗" plus the cache/ADT gap bullets
ending with "帮我解决".**

**0089 probe ran (approval: "允许，现在刷入探针（推荐）").** Materials in
`research/matisse/20261025-hetero-cache/`: ADT, payload, BRK cave manifest,
`entryprobe-el1-xnu-0089-hetero-cache-brk.img` (26,570,752 B, SHA256
`966a0e56...`), restore image `2931647a...`. The runner rewrote 64 MiB of
`boot_a`, verified it, and restored the stock image in `finally`; exactly one
banner survived (`hetero-cache-dmesg.txt`):

```
... x0=0000020000000400 x16=0000020000000000 ...
```

`x0` = E entry (A510 boot core): `c_priv_l2size=0x200`, `c_l3size=0x400`;
`x16` = P entry: `0x200` / `0`. Those are impossible geometries (L2 512 B,
L3 1 KiB), so 0089 read real data into a broken decode.

**Root cause: FEAT_CCIDX.** With CCIDX, `CCSIDR_EL1` is 64-bit: NumSets
`[55:32]`, Associativity `[23:3]`; the legacy layout is NumSets `[27:13]`,
Associativity `[12:3]`. `machine_read_ccsidr()` returns `uint32_t`
(`osfmk/arm/machine_cpuid.c:56`), so NumSets is lost and
`arm_cache_ccsidr_t` sees NumSets-1=0. Size becomes `linesz * assoc`:
8-way L2 -> `64*8 = 0x200`; 16-way L3 -> `64*16 = 0x400`, matching the banner
byte-for-byte. P's `c_l3size=0` is not yet conclusive: the cave reads
concurrently with secondaries, and the main path stores `c_priv_l2size`
(+0x30) before `c_l3size` (+0x34), so a P core may have been sampled
mid-`do_cacheid`.

**Same truncation in set/way maintenance.** `GET_CACHE_CONFIG` in
`osfmk/arm64/caches_asm.s` extracts ways `[12:3]` and sets `[27:13]`. Under
CCIDX it derives one set per way, so `CleanPoC_Dcache`/`FlushPoC_Dcache`
(`arm64/cpu.c:333` on every CPU; bulk path when
`length >= cache_info()->c_bulksize_op`) only touch the first set of each
way. This becomes more visible once `c_bulksize_op` is no longer 0x200.

**Patch `xnu/patches/0091-sweet-ccidx-cache.patch`.** `cpuid.c` gains
`ccsidr_geometry()`: 64-bit `CCSIDR_EL1` plus `ID_AA64MMFR2_EL1.CCIDX`
`[23:20]`, decoding CCIDX assoc/nsets `[23:3]`/`[55:32]` and legacy
`[12:3]`/`[27:13]`; all four decode sites use it. `caches_asm.s` selects the
same fields with `csel` (x4 = CCIDX version, third scratch is reused only
after the way increment is final). `proc_reg.h` defines
`ID_AA64MMFR2_EL1_CCIDX_*`. The legacy branch is bit-identical to the old
bitfields, so non-CCIDX cores do not change; `c_type` still comes from the
low word (used only in the boot kprintf).

**Local verification.** Applying 0089 then 0091 to pristine xnu reproduces
this tree; `clang -fsyntax-only` with the ci-40115544522 flags passes for
`cpuid.c`; `caches_asm.s` assembles and the disassembly keeps the way
increment in x11; all 63 host tests pass.

**Expected once 0091 runs** (measured values, not ADT guesses): E private L2
`0x40000` (256 KiB) and L3 `0x800000` (8 MiB); P private L2 `0x80000`
(A710 512 KiB) or `0x100000` (X2 1 MiB when that core has run), P L3 TBD -
likely `0x800000`; the earlier 0 may be the probe race above. `hw.perflevel1`
maps to E, `perflevel0` to P; the boot-cluster non-perflevel
`hw.l2cachesize`/`hw.l3cachesize` therefore report E.

**CI run 40120476258 (0091): success.** Build 14m18s; artifact
`xnu/out/ci-40120476258/xnu-kernel/kernel.development.sweet` (17,239,952 B,
SHA256 `54994bd4...`). Verified in the binary, not just in the sources:

- `_do_cacheid` (`0xfffffe000748083c`) decodes 64-bit CCSIDR at every site:
  `mrs x8, CCSIDR_EL1`, `mrs x9, ID_AA64MMFR2_EL1`, `tst x9,#0xf00000`,
  `ubfx x9,#3,#10` / `ubfx x12,#3,#21` with `csel` for ways,
  `ubfx w11,#13,#15` / `ubfx x8,#32,#24` with `csel` for sets, so
  size = linesz*ways*sets rather than linesz*ways.
- `GET_CACHE_CONFIG` inlined into `_clean_mmu_dcache` (`0xfffffe000747d900`)
  and `_CleanPoU_Dcache` (`0xfffffe000747d9e8`): `mrs x4, ID_AA64MMFR2_EL1;
  ubfx x4,x4,#20,#4; cmp x4,#0` selects CCIDX ways/sets with `csel`; the
  way-stride magic is unchanged and the increment still survives in x11.
- Layout for the cave: `_cpuid_cache_info` = `0xfffffe0007c5da98`
  (was `...7c59a98`), entry stride `0x38`; stores at entry+`0x24`
  (`c_l2size`), +`0x30` (`c_priv_l2size`), +`0x34` (`c_l3size`) confirm the
  offsets used by `tools/xnu_cacheprobe.py`.

**0091 payload built** for a re-probe:
`research/matisse/20261025-cache-0091/matisse-xnu-0091.payload`
(16,629,568 B, SHA256 `4cad7a19...`), same 8-core ADT and cmdline as 0089.
`__TEXT_EXEC` grew `0x854000 -> 0x858000` and every later segment moved
+`0x4000`; `kernel_end` `0xfffffe00084d4000`. Because of that shift the 0089
addresses cannot be reused:
checkpoint `cbz w0` after `bl _vfs_mountroot` is now VA `0xfffffe0007771324`
(PA `0x101771324`, original word `0x34000180`). The cave is unchanged:
`_LowExceptionVectorBase` is still `0xfffffe000748d000`, its slot 14 still
`B .`+NOPs, so cave VA `0xfffffe000748d714` (PA `0x10148d714`) and
`cpuid_cache_info` above apply. `_bootstrap_pagetables` is still
`0xfffffe000717c000` in `__DATA_CONST`, so the verified
`--xnu-restore-ttbr0 0x10117c000` remains valid; `tools/mkentryprobe.py`
re-validates that the page is still zero in the new payload.

**Open question before the re-probe: is P's `c_l3size=0` real?** In 0089 the
P entry had `c_priv_l2size=0x200` but `c_l3size=0`. The first P core to run
takes the main path and stores `c_priv_l2size` (+0x30) before `c_l3size`
(+0x34); `SweetCPU::startAll` starts CPUs one at a time and waits for each
`initCPU`, so by `bsd_init` all 8 should be past `do_cacheid` - but a race is
not provable from one sample. If instead P's CLIDR really has Ctype3 != 4,
the main path takes the `Ctype2==4` branch, leaving `c_l3size=0` and setting
`c_l2size` = private L2; that would make the 0 correct rather than a decode
bug. To answer both in one flash, extend `tools/xnu_cacheprobe.py` before
building the image: keep `x0 = (E.priv_l2<<32)|E.l3`, and pack the P fields
as 12-bit page counts `x16 = (P.l3>>12) | ((P.priv_l2>>12)<<12) |
((P.c_l2size>>12)<<24)`. Then `l3=0, c_l2size==priv_l2` means Ctype3 absent;
`l3=0, c_l2size=0` means the main path never reached the geometry block.
Update the matching unit test (`tools/tests/test_xnu_cacheprobe.py`).

**Next action: build `entryprobe-el1-xnu-0091-hetero-cache-brk.img`** with
the established recipe (`--xnu-vector-offset 0xb78 --xnu-high-vector-offset
-0x4488 --xnu-clean --xnu-clean-limit 0x108000000 --xnu-restore-ttbr0
0x10117c000 --xnu-selective --ufs-init --ufs-query full --template
backup/boot_a-stock.img`), run it through the readback/restore runner, then
read the single `SWEET-ENTRY` record. Any new `boot_a` write - this probe or
the real kernel - still needs explicit user approval; the 0089 approval is
consumed. Do not flash without it.

## >>> ACTIVE 2026-10-25 (USB): handoff PASS - MTU3 powered, HS device, soft-connected <<<

**Request (user): "帮我移植 USB 功能，尽可能把 USB 功能恢复，然后输出日志".**
matisse USB is MediaTek MTU3 (usb0@11201000 MAC, ippc@11203e00) + XSPHY,
not sweet's Qualcomm DWC3, so the existing USB patches cannot drive it. The
vendor recovery driver proves HS device mode works (ADB over bulk
ep1in/ep1out, `gadget (high-speed) pullup D+`); LK logged
"USB enum timeout ... cannot detect tools", so its handoff state was unknown.

**Probe PASS (2026-10-25).** `research/matisse/20261025-usb/`:
`entryprobe-usb-snapshot.img`, 20,832,256 B, SHA256 `0480bcc8...`; new level
`usb` (`ENTRY_LEVEL=1` + `ENTRY_USB_SNAPSHOT` in `tools/mkentryprobe.py` /
`shim/entryprobe.c`), read-only, taken right after `board_probe` with
MAC/IPPC resolved from the live usb0 node. The full 64 MiB `boot_a` was
written, read back and verified (`01f6765a...`), then restored to
`2931647a...` and re-verified; exactly one record:

```
SWEET-ENTRY v1 el=0000000000000001 midr=00000000410fd462 mpidr=0000000081000000 freq=0000000000c65d40 dtb=16c016c000000000 sctlr=0000000800000048 stage=0000000000006000 fault=000060a100000099 esr=0000001f00000000 far=2018072410060000 pc=5a00000080000003 gicd=1041102000000001 vtimer=0000000000000001 fb=01013d0f00000001 x0=0000000000ff0101 x16=00000020000000ff spsr=0000004000000000
```

`stage=0x6000` = complete. Fields are `first register << 32 | second`
(lower address first), per `USB_FIELDS`; MAC offsets verified in the
disassembly. Decoded (live recovery values in parentheses for contrast):

| Field | Register pair | Handoff value | Live recovery |
| --- | --- | --- | --- |
| gicd | IPPC PW_CTRL0 / PW_CTRL1 | `0x10411020` / `0x1` | same |
| vtimer | IPPC PW_CTRL2 / PW_CTRL3 | `0x0` / `0x1` | same |
| fb | IPPC PW_STS1 / PW_STS2 | `0x01013d0f` / `0x1` | |
| dtb | IPPC OTG_STS / SPM_CTRL | `0x16c016c0` / `0x0` | same |
| sctlr | IPPC U3_CTRL_0P / U2_CTRL_0P | `0x8` / `0x48` | `0x88` / `0x48` |
| esr | IPPC REF_CK_CTRL / DEV_RST_CTRL | `0x1f` / `0x0` | |
| far | IPPC HW_ID / HW_SUB_ID | `0x20180724` / `0x10060000` | same |
| pc | MAC DEVICE_CONF / MISC_CTRL | `0x5a000000` / `0x80000003` | `0x59000003` / same |
| fault | MAC POWER_MANAGEMENT / DEVICE_CONTROL | `0x60a1` / `0x99` | `0x64f1` / `0x99` |
| x0 | MAC USB3_CONFIG / LINK_STATE_MACHINE | `0x0` / `0x00ff0101` | same |
| x16 | MAC LV1ISR / LV1IER | `0x20` / `0xff` | `0x0` / `0x37` |
| spsr | MAC EP0CSR / RXCOUNT0 | `0x40` / `0x0` | `0x00200440` / `0x0` |

**What LK leaves for XNU:**

- **Powered and clocked.** PW_CTRL2 DEV_PDN=0; U3/U2 PORT_PDN=0 and DIS=0;
  PW_STS1 `0x01013d0f` has SYSPLL_STABLE(0), REF_RST_B(8), SYS125_RST_B(10),
  XHCI_RST_B(11) and U3_MAC_RST_B(16) all set; PW_STS2 U2_MAC_SYS_RST_B=1;
  REF_CK_CTRL=`0x1f`; DEV_RST_CTRL=0. No MTK clock/scpsys/XSPHY bring-up is
  needed for the first enumeration; XNU must simply not reset those domains.
- **Device mode, HS-only, VBUS forced.** U2_CTRL HOST(2)=0, OTG_SEL(7)=0;
  U3_CTRL DUAL_MODE(7)=0; USB3_CONFIG=0; POWER_MANAGEMENT SOFT_CONN(6),
  HS_ENABLE(5), SUSPENDM_ENABLE(0) all 1; DEVICE_CONTROL `0x99`
  (DC_SESSION=1); MISC_CTRL `0x80000003` = DMA_ADDR_36BIT(31) +
  VBUS_FRC_EN(0) + VBUS_ON(1); OTG_STS VBUS_VALID(9)=1.
- **The host had enumerated LK's gadget up to SET_ADDRESS.** DEVICE_CONF
  `0x5a000000` decodes to DEV_ADDR=0x5a (90), speed field 0 (live ADB:
  address 0x59, speed 3); EP0 max packet is 64 (`0x40`), no SETUP/RX pending,
  but LV1ISR EP_CTRL_INTR(5) is pending and LV1IER=`0xff`.
- **36-bit DMA.** MISC_CTRL bit31 is set, so GPD/TRB addresses must stay
  below 64 GiB (16-byte aligned, low 4 bits encoded if following the vendor
  QMU format).

**Driver implemented (2026-10-25, not yet booted).** Commits `bca092a`
(driver + ADT node + payload policy) and `a686a6a` (read the MAC only after
the IPPC power check); pushed to `fork/codex/matisse-xnu-screen-log`.
`xnu/patches/0090-sweet-mtu3-usb.patch` adds `bsd/dev/sweet_mtu3.c`, its
`bsd/conf/files` entry, and a `sweet_mtu3_probe()` dispatch at the top of
`sweet_usb_probe()` (returns 0 when the ADT has no `/sweet-usb`, so sweet
still probes DWC3). The driver resets only the MTU3 device function, drives
EP0 from FIFO0 and bulk/notification endpoints through the gen2cp QMU with
36-bit DMA, polls from one kernel thread, and reuses the DWC3 CDC-ECM
descriptors, `ue0` 192.168.7.2/24 and UDP 192.168.7.1:5140 log. `mkadt.py`
adds a matisse-only `/sweet-usb`
(`reg = 0x11201000 0x2e00 0x11203e00 0x100`); `mkpayload.py` accepts
`sweetusb=0..2` on matisse and defaults to 2. Observation: local
`clang -fsyntax-only` with the ci-40103653699 defines passes, 0090 applies
clean to the patched tree, and all 63 host tests pass. CI run **40116784474
success** (kernel `b0ad9f5e...`, 24 `SWEET MTU3` strings linked).
Built, **not flashed**, `research/matisse/20261025-usb/`: ADT
`matisse-usb.adt` (`d61d7fbf...`, has `/sweet-usb`), payload
`matisse-xnu-0090-usb.payload` 16,629,568 B (`4e0d07a5...`, cmdline
`... rd=ufsroot0 ufsrw=0 ufscache=1 -noprogress ... sweetusb=2`), entryprobe
image `entryprobe-el1-xnu-0090-usb.img` 26,578,944 B (`e12259a7...`) with
the usual el1-xnu recipe (offsets unchanged: vector `0xb78`, high
`-0x4488`, TTBR0 `0x10117c000`, clean limit `0x108000000`, `--ufs-init
--ufs-query full`, template `backup/boot_a-stock.img`). Verified the
decompressed kernel embeds the payload byte-for-byte at 48,947,216 and the
ADT carries the USB node. The phone was in recovery; flashing awaits
explicit user confirmation. Host side (macOS) must wait for the CDC-ECM
interface, assign 192.168.7.1/24 and listen on UDP 5140.

**Takeover plan (next):** mask/clear LV1, pulse IPPC DEV_RST_CTRL bit0 to
reset only the device function (not the IP/clock domains), set DEVICE_CONF=0,
EP0 maxpkt 64, then re-enable interrupts and let the host re-enumerate.
EP0 uses FIFO0 (`0x300`) / EP0CSR (`0x100`) / RXCOUNT0 (`0x108`); CDC-ECM
data EPs use QMU (vendor/ADB uses ep1in/ep1out bulk). Reuse `sweet_usb.c`'s
CDC-ECM descriptors, ifnet and UDP live-log code; add a matisse MTU3
transport and a `sweet-usb` ADT node (MAC/IPPC regs + IRQ 160), and allow
`sweetusb=1` on matisse in `tools/mkpayload.py`.

## >>> ACTIVE 2026-10-25: per-CPU IRQ probe PASS (IPIs 8/8, timer demand-driven) <<<

## >>> ACTIVE 2026-10-25: per-CPU IRQ probe PASS (IPIs 8/8, timer demand-driven) <<<

**Question (user: "irq正常吗").** The 8-core probe proved SGI1 ran on every
core, but not which CPUs take timer/IPI interrupts afterwards. Instead of
rebuilding the kernel, `tools/xnu_smp_irqprobe.py` rewrites the mountroot
checkpoint (`cbz w0` at VA `0xfffffe000776ee3c`) into `B 0xfffffe000748d714`,
a 26-word cave in early-vector slot 14: read CNTVCT, busy-wait 2 s
(26,000,000 ticks at 13 MHz), scan `CpuDataEntries[7..0]`
(VA `0xfffffe0007be1bd8`, vaddr at entry+8), test `cdp+0x228` (ipi_cnt, 64-bit
pair incremented in `_cpu_signal_handler_internal`) and `cdp+0x238`
(`_rtclock_intr` timer_cnt), build one-bit-per-CPU masks, put them in x0/x12
and `BRK #0x5357`. Offsets were re-checked against the 0088 Mach-O:
`ldr x8,[cdp+0x238]` at `fffffe00074963c4` and the 2x64-bit increment at
`[cdp+0x228]` in `_cpu_signal_handler_internal`.

**Hardware PASS (2026-10-25).** `research/matisse/20261025-smp8-irq/`:
`entryprobe-el1-xnu-0088-smp8-irq-brk.img`, 26,570,752 B, SHA256
`ee8e652b...`, same recipe as the 8-core probe; written partition
`726c122f...`. Recovery came back just after the flash script's 45 s window,
so its `finally` left the test image in place; dmesg was captured and the
stock `boot_a` restored manually (`2931647a...`, full 64 MiB verified).
Banner (exactly one record):

```
SWEET-ENTRY v1 el=0000000000000001 midr=00000000410fd462 mpidr=0000000081000000 freq=0000000000c65d40 dtb=0000000000000000 sctlr=0000000030d00980 stage=0000000000000087 fault=0000000000000001 esr=00000000f2005357 far=fffffe10108b0000 pc=fffffe000748d778 gicd=0105000000360000 vtimer=0501000000000000 fb=0000000121020004 x0=0000000000000003 x16=00000000000000ff spsr=0000000062400204
```

`pc` is the cave's BRK and `esr=f2005357` confirms it. `x0=0x03` = timer mask
(logical CPUs 0 and 1); `x16=0xff` = IPI mask (all CPUs 0-7).

**Interpretation.** Per-CPU interrupt delivery works on all eight cores: each
CpuData entry is valid and every core has handled at least one CPU signal
(the initCPU SGI1 self-test alone guarantees the count). Both counters are
cumulative since boot. Timer IRQs are demand-driven: XNU arm64 is tickless
and `SetIdlePop()` arms the vtimer only when `rtcPop` is a real future
deadline; otherwise it programs the clamped maximum (rtcPop starts at
`EndOfAllTime`), so idle cores with no scheduled thread legitimately keep a
zero timer count. CPU1's nonzero timer_cnt is the first per-secondary vtimer
evidence; CPUs 2-7 have no direct vtimer-interrupt proof yet because nothing
ran there. A later checkpoint (after launchd/threads are active) or a loaded
8-core run would prove that. Raise the flash script's recovery wait to ~120 s
next time.

**Next.** Real-root 8-core boot with `matisse-xnu-0088-smp8.payload`, then
check per-CPU scheduler activity; CPU_OFF/quiesce and heterogeneous cluster
reporting remain unimplemented.

## 8-core matisse probe (PASS 2026-10-25)

**Goal (user request): enable all eight cores.** The 0088 kernel already has
the SMP path (0065 PSCI CPU_ON + legacy IOCPU, 0078 8 cores, 0084 single-CPU
`ml_wait_max_cpus` early return); matisse never used it because
`tools/mkadt.py` emitted one `arm,cortex-a510` CPU node, which SweetCPU
(IONameMatch `qcom,kryo470`) cannot match. Host-side fix:

- `tools/mkadt.py --board matisse` now emits 8 CPUs from the live FDT:
  cpu@000..300 `arm,cortex-a55`, cpu@100..200 `arm,cortex-a78`, `reg`
  (MPIDR Aff1:Aff0) 0x000..0x700, compatible = `qcom,kryo470` + real core +
  `ARM,v8` (Qualcomm string first so the existing driver matches), cpu0
  `state=running`, cpu1-7 `stopped`.
- `tools/mkpayload.py` matisse policy now accepts `cpus=1..8` and appends
  `cpus=<topology count>` when absent (8 by default); the other guards
  (`sweetkeys=0 ... ufsrw=0 -noprogress`) are unchanged.
- 48 tools tests pass (`python3 -m unittest discover -s tools/tests -q`).

**Built (not flashed).** Directory `research/matisse/20261025-smp8/`:

- `matisse-8core.adt`, 10,332 B, SHA256 `4c67dbd7...`.
- `matisse-xnu-0088-smp8.payload`, 16,611,760 B, SHA256 `f2650fdf...`;
  kernel 0088 (`893ac2a0...`, unchanged), cmdline `debug=0xc serial=0 cpus=8
  keepsyms=1 -enable_kprintf_spam rd=ufsroot0 ufsrw=0 ufscache=1 -noprogress
  sweetkeys=0 sweettouch=0 sweetbattery=0 sweetusb=0` (test 4 plus `cpus=8`).
- `matisse-xnu-0088-smp8-brk.payload`, SHA256 `57f5e212...`: BRK #0x5357 at
  entry offset 0x2e29b4 (VA `0xfffffe000776ee3c`, PA `0x10176ee3c`, payload
  file offset 7,778,860) replacing `cbz w0` (0x34000180) after
  `bl _vfs_mountroot` - the same checkpoint that returned x0=0 in test 4.
- `entryprobe-el1-xnu-0088-smp8-mountroot-brk.img`, 26,570,752 B, SHA256
  `8511db44...`, same recipe as the 0088 HFS probe (`--level el1-xnu`,
  selective vectors, vector offset 0xb78, high vector -0x4488, clean limit
  0x108000000, TTBR0 restore 0x10117c000, `--ufs-init --ufs-query full`,
  max image 67,108,864, template `backup/boot_a-stock.img`). Verified: the
  decompressed kernel (65,558,976 B) contains the payload byte-for-byte at
  decompressed offset 48,947,216, BRK word 0xd42a6ae0 at 7,778,860, the
  embedded ADT has 8 CPUs with reg 0/0x100/.../0x700, cmdline has `cpus=8`.

**Why the banner proves SMP.** `machine_conf()` sets
`machine_info.max_cpus = max_cpu_id + 1 = 8`; `kperf_init_early()` then
blocks in `ml_wait_max_cpus()` until SweetCPU's startAll publishes
`ml_set_max_cpus(8)`. startAll waits for every CPU's `initCPU()` and a real
SGI1 round trip (`sweet_cpu_signal_is_enabled`) and panics on a 5 s timeout
or a non-zero PSCI CPU_ON rc. Reaching the mountroot BRK therefore means all
8 cores ran `sweet_secondary_entry`, their own `pe_init_fiq` (GICR, vtimer
PPI 27, SGI1) and initCPU. Failure modes: panic at `SWEET CPU: ...` (driver
match, CPU_ON rc, timeout) or a hang before the banner.

**Hardware PASS (2026-10-25).** Pushed the probe (device-side SHA256 matched),
`dd bs=1M conv=fsync` to `boot_a`; the written 64 MiB partition hashed
`27107856...`, the expected image + original tail. `adb reboot recovery`
brought recovery back 66 s later; `dmesg-smp8.txt` holds the banner:

```
SWEET-ENTRY v1 el=1 midr=410fd462 mpidr=81000000 stage=0x87 fault=1
esr=f2005357 pc=fffffe000776ee3c x0=0 x16=0x182b spsr=62400204
```

x0=0 is the same vfs_mountroot success as test 4, now with `cpus=8`. Since
`kperf_init_early()` only proceeds after `ml_set_max_cpus(8)` and SweetCPU
publishes that only after every one of the 8 CPUs completed initCPU and
answered SGI1, this proves all eight cores (MPIDR 0x000..0x700) started via
PSCI CPU_ON, initialized their own GICR + vtimer INTID 27 and entered XNU,
and that UFS rootdev + HFS mount still work. MIDR 0x410fd462 (part 0xd46) is
a Cortex-A510 boot core; the live FDT's `a55`/`a78` names are descriptive
(the real MT6983 cores are A510/A710/X2). Stock `boot_a` was restored
immediately after and verified `2931647a...` (full 64 MiB), device back in
recovery, slot `_a`.

**Next for SMP.** CPU_OFF/quiesce and heterogeneous cluster reporting remain
unimplemented (SweetCPU panics). A non-BRK 8-core payload is
`matisse-xnu-0088-smp8.payload` for the next real-root boot; it still uses
`rd=ufsroot0` (the 64 MiB HFS test volume).

## >>> ACTIVE 2026-10-25: HFS root MOUNTS from UFS (`vfs_mountroot`=0) <<<

**Test 4 (mountroot) hardware PASS.** The 0088 kernel probe was built with a
BRK at the `cbz w0` after `bl _vfs_mountroot` (VA `0xfffffe000776ee3c`) and
booted from `boot_a` over a 64 MiB raw HFS+ test volume written at the start
of `userdata`. Banner (`ufs-0088-hfsroot-dmesg.txt`):
`SWEET-ENTRY v1 el=1 stage=0x87 fault=1 esr=f2005357
pc=fffffe000776ee3c x0=0 x16=0x182b spsr=60400204`. **x0=0** means
`vfs_mountroot` returned success: the UFS block device (`/dev/ufsroot0`,
found via the LUN scan) was read, the `H+` volume header was accepted, and
the HFS root was mounted. Probe image
`entryprobe-el1-xnu-0088-hfsroot-mountroot-brk.img` (26,570,752 B, SHA256
`8c84ec8d4ff495ee1e10abd10a02e1afc701e44a727bb8882601b68185c949f2`,
BRK at payload file offset 7,778,860) was written and read back inside
recovery; stock `boot_a` restored immediately after and verified
`2931647a...` (full 64 MiB partition hash).

**Flashing route: use recovery root ADB, not fastboot.** This bootloader
rejects `fastboot boot` ("unknown command") and `fastboot flash` wedged once
(usb_write e00002d9). Both the probe write and the stock restore were done
with `adb push` to `/tmp` + `dd ... of=/dev/block/by-name/boot_a conv=fsync`
in recovery (adbd is root there), then verified with a partition readback
hash. `dd` the full 64 MiB backup on restore; the probe image is smaller
than the partition and leaves the old tail in place, which Android's boot
header ignores.

**Test 3 (0088 LUN scan) hardware PASS.** Banner after the probe boot
(`ufs-0088-lunscan-dmesg.txt`):
`SWEET-ENTRY v1 el=1 stage=0x87 fault=1 esr=f2005357
pc=fffffe0007a42c88 x0=0 x16=fffffe000702e078 spsr=60400204`. The BRK fired
at the `cbnz w0` with **x0=0**, so `sweet_ufs_rootdev` found the GPT on LUN 2
via the scan, found the `userdata` partition, registered `/dev/ufsroot0` and
its char device, and returned success before the HFS mount is reached.
Stock `boot_a` was restored immediately after and verified `2931647a...`.
Log: `research/matisse/20261024-ufs-wdt/flash-0088-lunscan.log`.

**Test volume used for test 4.** `userdata` is `/dev/block/sdc86`
(223,281,088 512-byte sectors = 114.3 GB). On 2026-10-24, with user approval,
a 64 MiB raw HFS+ volume was written at its start (destroying the Android
userdata filesystem; GPT and every other partition untouched). Created with
`hdiutil create -layout NONE -size 64m -fs HFS+ -volname iOSRoot`:
`hfs-test/none.dmg`, SHA256
`8b8db5ef44562ee4af008ca92678e1519274a3b93bf1355033ddf56beb08d826`,
`H+` at byte 1024, version 4. Pushed and `dd`'d to
`/dev/block/by-name/userdata` (`bs=1M count=64`) in recovery, readback hash
verified. So Android will no longer boot normally until userdata is
reformatted.

**Next blocker: a real root image.** No `ios16-root-*.img`/`.simg` exists on
this Mac (`/Volumes` scan found none; the old images lived on the Linux host
at `/run/media/dipa/android/ios-sweet-ipsw/`). The 64 MiB test volume only
proves mounting; an actual iOS boot needs the real root copied over (or into
`userdata` after the test volume). Everything up to and including
`vfs_mountroot` is now proven on hardware.

**Device (verified after test 4): root ADB in Recovery, slot `_a`, `boot_a`
`2931647a56039722ea2585990b8ef3b1a2daf4c9b990231879f753049eaf86b1`.**
Both probe boots were followed by a stock restore; the last one reflashed
`backup/recovery-20261021/boot_a-live-20261021.img` and
`sha256sum /dev/block/by-name/boot_a` matched. The 0086 probe (`b988da3f...`)
had hung at the logo; with 0087's watchdog feed the same BRK is now reached
and relayed in ~50 s, so that hang was most likely a watchdog reset during
the XNU waits.

**Second hardware result: the GPT signature check fails.** Multi-BRK banner
(`ufs-0087-multibrk-dmesg.txt`):
`SWEET-ENTRY v1 el=1 stage=0x87 fault=1 esr=f2005357 far=fffffe39766bc000
pc=fffffe00074e88c4 x0=fffffe0007088f39 x16=0 spsr=20400204`. `pc` is the
inlined "LUN %u has no GPT" branch (0x...88c4), not the DT-node, 64AS,
bad-entries or last<first sites. Since that branch is only reachable after
`ufs_take_over_host`, `ufs_device_init` (SET+READ fDeviceInit), TUR and
`READ(10)` of LBA 1 all returned success, the host takeover and SCSI path
work.

**Root cause: the GPT is not on LUN 0.** The driver hardcoded `su.lun = 0`.
On this device (read from recovery, read-only) LUN 0 and 1 are the UFS boot
LUNs: `0:0:0:0`/`0:0:0:1` are 4 MiB (`logical_block_count` 0x400,
`boot_lun_id` 1/2) and contain `MMM` MTK boot images at byte 4096. The user
LUN with the GPT is **LUN 2** (`0:0:0:2`, 128 GiB,
`logical_block_size` 0x0C = 4096, `boot_lun_id` 0): `dd bs=4096 skip=1`
starts with `EFI PART` and the header names the usual GPT entries. So the
READ succeeded and returned boot-LUN data, not zeros. Logical block size is
4096, matching `UFS_BLOCK`.

**Fix built in CI: run 40106917827 (`14eaca5`), 7m28s, success.** Kernel
`xnu/out/ci-40106917827/kernel.development.sweet`, SHA256
`893ac2a00641fc438c013939a0927411229503f396ce714b15b9b56574b4538c`
(17,223,000 B, matches SHA256SUMS). `_ufs_lun_has_gpt` 0xfffffe00074e8bfc,
`_sweet_ufs_rootdev` 0xfffffe00074e8090 (unchanged), `_IOFindBSDRoot`
0xfffffe0007a425d4 (+0x120), entry VA still 0xfffffe000748c488. The `cbnz w0`
after `bl _sweet_ufs_rootdev` is now 0xfffffe0007a42c88 (PA 0x101a42c88);
BRK #0x5357 inserted there (payload offset 0x5b6800 from entry, file offset
10743928 in the payload).

**Probe (flashed and tested, PASS).**
`research/matisse/20261024-ufs-wdt/entryprobe-el1-xnu-0088-lunscan-ufs-brk.img`,
26,570,752 B, SHA256
`8c67bac892817ee7381b042f96a26368bed1b407c4ee2e35e67abc7eb8d08b39`; payload
`matisse-xnu-0088-lunscan-brk.payload` SHA256 `79ce42f5...` (embedded copy
verified byte-equal inside the decompressed kernel, BRK word at decompressed
offset 59,691,144). Same recipe as 0087 and the same ADT
`shim/out/matisse-ufs.adt`; declared LUN scan, no `ufslun=` in the cmdline.
Result to read: banner `x0` = `sweet_ufs_rootdev` return value; `x0=0` means
the scan found LUN 2, the GPT and `userdata`, `x0=6` means still ENXIO.

**First hardware result: `sweet_ufs_rootdev` returns ENXIO (6).** Recovery
dmesg banner (`ufs-0087-wdt-dmesg.txt`):
`SWEET-ENTRY v1 el=1 fault=1 esr=f2005357 pc=fffffe0007a42b68 x0=6
x16=0200000110000640 spsr=60400204`, stage `0x87` (loader checkpoint S7
"jump", so payload and loader stages all completed). The EL1 BRK fired at the
`cbnz w0` after `bl _sweet_ufs_rootdev` with `w0=6`. UFS/SCSI failures would
return `0x2xx`..`0x5xx`, `0x8xxx` or ETIMEDOUT and a missing partition name
returns ENOENT, so ENXIO narrows it to: missing `/sweet-ufs` node, the 64AS
DMA check (ruled out: CAP was 0x3587071f, bit 24 set), the GPT signature /
entry-table / bounds checks, or `bdevsw_add` / `cdevsw_add`.

**Fastboot note.** After the aborted first attempts the bootloader's
fastboot state was wedged (`fastboot flash` sat before "Sending",
`usb_write failed e00002d9`); `fastboot reboot-bootloader` cleared it and the
same command then flashed in 0.9 s. Stale `fastboot` processes must be killed
before retrying.

**0087 built and verified in CI.** Run 40103653699 (`1ef6f0e`) succeeded in
13m34s. Kernel `xnu/out/ci-40103653699/xnu-kernel/kernel.development.sweet`,
SHA256 `dc6925e8f0c9307853569608d888f92ab8438547d89726b876f7adbc358de615`
(17,222,960 B). `_ZN10IOWatchdog5startEP9IOService` 0xfffffe0007a6701c,
`_ZL18sweet_mtk_wdt_feedPvi` 0xfffffe0007a674b8, `_ZL13sweet_mtk_wdt`
0xfffffe000806e060. `start()` maps 0x1c007000/0x1000 with `ml_io_map`, reads
MODE/LENGTH/STATUS and logs `SWEET WDT: MTK WDT mode=0x%08x length=0x%x
status=0x%08x`, then `kernel_thread_start`; the feed loop stores 0x1971 at
+0x08 and `IOSleep(1000)`. `IOWatchdog` is in `KernelConfigTables.cpp`
(IOResources/IOWatchdog). The 0086 SET→poll fix is present too:
`sweet_ufs_rootdev` 0xfffffe00074e8090, SET at 0x...798, 1000 x 1 ms READ
loop at 0x...7c0.

**Text layout unchanged vs 0086**, so the proven offsets still hold: entry
0xfffffe000748c488, virt_base 0xfffffe0006000000, kernel_end
0xfffffe00084d0000, `_bootstrap_pagetables` 0xfffffe000717c000 (PA
0x10117c000), `_IOFindBSDRoot` 0xfffffe0007a424b4, BRK site (the `cbnz w0`
after `bl _sweet_ufs_rootdev`) 0xfffffe0007a42b68 = payload offset 0x5b66e0.

**Probe image (flashed and tested).**
`research/matisse/20261024-ufs-wdt/entryprobe-el1-xnu-0087-wdt-ufs-brk.img`,
26,570,752 B, SHA256
`76b55890cff1bb3cc6b8c28383ecaf1c680bb38f4588ac26f62550c8cac71546`; payload
`8e75de9f...`. Recipe: `backup/boot_a-stock.img`,
`--xnu-vector-offset 0xb78`, `--xnu-high-vector-offset=-0x4488`,
`--xnu-clean --xnu-clean-limit 0x108000000`, `--xnu-restore-ttbr0
0x10117c000`, `--xnu-selective`, `--ufs-init --ufs-query full`,
`--max-image-size 67108864`, NDK 28.2.13676358.

**Branch bisect (flashed and tested).**
`research/matisse/20261024-ufs-wdt/entryprobe-el1-xnu-0087-wdt-multibrk.img`,
SHA256 `2d3b3e74...`, payload `ff750159...`: the same 0087 kernel with seven
BRKs so one boot identifies the failing branch by `pc` in the banner.
`sweet_ufs_init` is inlined into `sweet_ufs_rootdev`; the mapped sites are
DT-node printf 0xfffffe00074e8260, DMA printf setup 0x...8330, GPT no
signature 0x...88c4, GPT bad entries 0x...88f4, GPT last<first 0x...8a14,
shared ENXIO tail (bdev/cdev registration) 0x...8264, and the post-call
`cbnz` 0xfffffe0007a42b68 (hit means w0=0, success).

**0086 build verified; the ufs_query arity question is closed.** CI run
40101113289 (`9a19655`) built kernel `aa765f0d...` from the 7-argument
`ufs_query` source, but both call sites pass constant
`idn/index/selector/len` = 1/0/0/0, so clang specializes the static
function: `_ufs_query` receives `w0=opcode, w1=write, x2=&value` and
hardcodes cmd[13..15] = 1/0/0. The compiled `ufs_device_init` at
`0xfffffe00074e8798` does SET_FLAG (0x06) then READ_FLAG (0x05) with a
1000 x 1 ms poll, so the intended fix is in the binary. The "3-argument"
reading was constant propagation, not a stale build. The exact patched
source is in `xnu/out/ci-40101113289/xnu-buildtree/buildtree.tgz`
(`xnu/bsd/dev/sweet_ufs.c:426/524`).

**HFS registration checked; no fix needed.** xnu-8796.141.3 and hfs-627
contain no `PEARL_HFS` or `NABU_HFS`; this build path is `SWEET_HFS`. The CI
buildtree has `bsd/kern/bsd_init.c:700` = `#if SWEET_HFS ...
sweet_hfs_register();`, `bsd/conf/files` lists the `optional sweet_hfs`
objects, and the kernel contains `_sweet_hfs_register` (0x77d12e4),
`_hfs_vfsops` (0x7220200) and `_hfs_init_zones` (0x77c3d44). HFS is
registered before `vfs_mountroot`; do not add a second hook.

**MTK watchdog driver (patch `0087-sweet-mtk-wdt.patch`).**
`iokit/Kernel/arm/SweetWatchdog.cpp` now maps 0x1c007000
(`mediatek,mt6983-wdt`, not the older 0x10007000), prints MODE/LENGTH/STATUS
once at IOWatchdog start, and starts a kernel thread that writes RESTART
(0x08) = 0x1971 every second. The service still does not enable the
watchdog and keeps its no-op check-in/PMU behaviour. Compiled in run
40103653699 and booted in the 0087 probe; the probe relayed back to recovery,
so the feed prevented the resets that killed the 0086 test.

**Next.** Needs explicit approval to write `boot_a` for the multi-BRK image.
Plan: flash, boot recovery, read the banner `pc`/`x0`, restore
`backup/recovery-20261021/boot_a-live-20261021.img` and verify
`2931647a...`. Then fix the identified branch: if it is the GPT signature,
check the read path/cache coherence and the LBA (userdata should still hold
the Android GPT); if it is the shared ENXIO tail, `x0` holds the failing
`bdevsw_add`/`cdevsw_add` result. If the post-call BRK fires with `x0=0`,
UFS is up and the next task is mounting HFS from it.

## >>> ACTIVE 2026-10-23: UFS link/commands work in shim; XNU EIO remains <<<

**Current device (verified): Recovery, root, slot `_a`.** The full
67,108,864-byte `boot_a` was restored from
`backup/recovery-20261021/boot_a-live-20261021.img` and read back as
`2931647a56039722ea2585990b8ef3b1a2daf4c9b990231879f753049eaf86b1`.
`boot_b` is a separate image
(`8775a30a95a44ca5c8d83c38df4d77e2c4c8bad315ac54fb9d1dae60495d9cb7`). No
`userdata` write. Each new `boot_a` write still needs explicit approval. The
intermediate trim-prefix restore was `861da6b8...`; the full live backup has
replaced it.

**UFS bring-up resumed; the earlier two tests are confounded (2026-10-23).**
Two images were flashed:

1. `shim/out/shim-boot-0085-ufs.img` (SHA256 `d4f3746c...`), a production-style
   `rd=ufsroot0 serial=0` image with the new `/sweet-ufs` ADT node. The
   partition hash matched `1f41b3a7...`, but `adb reboot recovery` left the
   panel on the first logo with no ADB/fastboot. The shim leaves the WDT off,
   so it did not self-recover. A production image has no diagnostic relay, so
   "no ADB/fastboot" alone proves nothing.
2. `shim/out/entryprobe-el1-ufs-entry-brk.img` (SHA256 `46d5487e...`), with a
   BRK at `_sweet_ufs_rootdev` VA `0xfffffe00074e8090`. Partition hash matched
   `c1a2687a...`, but it also hung at the first logo; the BRK did not hit.

**Confound measured (payload bytes, 2026-10-23).** Both 0085 UFS payloads are
byte-identical to the unpatched `ci-39850065490` kernel: `matisse-xnu-0085-ufs.payload`
and `matisse-xnu-0085-ufs-entry-brk.payload` have **no rtcfast patches**. The
BRK at `_sweet_ufs_rootdev` is only reached after `IOKitInitializeTime`'s 30 s
RTC wait and `IOFindBSDRoot`'s 30 s IOMedia wait, i.e. after roughly 60 s.
Any observation shorter than that cannot prove a miss. In addition, 0085 is
the video-console-refresh kernel that was never booted successfully; it must
be separated from UFS. The rtcfast patches (10 bytes at VAs
`0xfffffe00079ad070`, `0xfffffe0007a41e70`, `0xfffffe0007a41eb4`) are present
only in the proven 0084 payload.

**HARDWARE PASS (2026-10-23): `_sweet_ufs_rootdev` entry reached.**
`research/matisse/20261023-ufs/entryprobe-el1-ufs-rtcfast-entry-brk.img`,
26,562,560 B, SHA256
`f9ceaf53a4663aea422e5f1a316d321e445a72ca7f6879bd0fc2228048367a3a`;
payload `matisse-xnu-0084-ufs-entry-brk.payload`, 16,605,888 B, SHA256
`71a8ca22a74d278f6e72f955830a0e6c59fe7ffe492608a5b611ab49c10a8e5c`
(kernel 0084 `28190f5b...`, ADT `matisse-ufs.adt` `1020d120...`, cmdline
`... rd=ufsroot0 ufsrw=0 ... serial=0`). Selective vectors, clean range
`[0x100000000,0x108000000)`, TTBR0 restore `0x10117c000`, standard offsets
`0xb78` / `-0x4488`. BRK word verified at payload offset `0x4e4480`
(PA `0x1014e8090`); all three rtcfast words verified. Written-partition
SHA256 `73392f038083c938478dcd6180850b25fef77d34702a604e01df26112cf61c2b`
matched the full readback. Same-boot record (recovery `dmesg`, one line):

```
SWEET-ENTRY v1 ... stage=0000000000000087 fault=0000000000000001
esr=00000000f2005357 far=fffffe30bb9bc000 pc=fffffe00074e8090
... x0=fffffe0007c03938 x16=ffffffffffffffff spsr=0000000060400204
```

The device was online again 30.7 s after `adb reboot recovery`. The full
original `boot_a` was rewritten and verified as `2931647a...` (the restore dd
succeeded; one adb pull failed transiently, and the re-pull of the on-device
`/tmp/ufs-readback.img` matched). **Conclusion:** with the UFS ADT and
`rd=ufsroot0`, XNU parses the root device and calls `_sweet_ufs_rootdev`; the
earlier entry-BRK "miss" was the unpatched 60 s of RTC/IOMedia waits (and/or
the 0085 kernel), not a pre-UFS hang. This says nothing yet about
`ufs_take_over_host()`.

**HARDWARE FAILURE (2026-10-23): full-init checkpoint missed; panic/reboot.**
`research/matisse/20261023-ufs/entryprobe-el1-ufs-init-done-brk.img`,
26,562,560 B, SHA256
`0c946c92453ef7adb6c91e78e82f9f51860d0ca3268ef51c1503b37f4fc72f5f`;
payload SHA256 `1fb92fa405d3b470ded408323efc611c1d0ad62d258394667cdaca8b2f78d761`.
BRK at VA `0xfffffe00074e86c4` (payload offset `0x4e4ab4`, PA `0x1014e86c4`),
replacing `bl printf` (`0x97f98462`) immediately after `su.ready = true`.
Written-partition SHA256
`729936dfd5ba8bc7b7dfc2ca8fd9e3a0221860cd3818c5ccabdab822a4b42ce1`
matched the full readback. The device did **not** return; the user observed a
logo reboot loop. No SWEET-ENTRY record. Recovery: the user entered fastboot;
`fastboot flash boot_a backup/boot_a-stock-trim.img` (`fe6e8fbf...`) OKAY,
Recovery online in 26 s, then the full 67,108,864-byte original was written
and the on-device SHA256 verified as `2931647a...`. (One `adb push` dropped
mid-copy and left `d86975b2...`; re-pushing and checking the file hash on the
device before `dd` fixed it. Always verify `/tmp` and the partition.)

A miss at `0x74e86c4` means one of `ufs_take_over_host()`, the TURs,
`ufs_find_partition()` (GPT), or the devfs/bdevsw registration failed and
`IOFindBSDRoot` panicked. It does **not** yet say which. In the 0084 build the
first TUR `bl ufs_scsi` is at VA `0xfffffe00074e83b4`; reaching it proves the
inlined `ufs_take_over_host()` succeeded. The likely early gates are CAP bit
24 (64AS) with DMA above 4 GiB, HCE bit 0 / HCS DP+UTRLRDY, or an
outstanding UTRLDBR.

**New probe feature (commit `deaa731`): read-only UFSHCI snapshot.**
`tools/mkentryprobe.py --ufs-regs` (levels `el1-xnu`/`el1-load`) calls
`entryprobe_ufs_snapshot()` before the XNU jump and encodes eight registers
into fields the EL1-XNU record does not otherwise use:
`gicd = CAP<<32|VER`, `vtimer = HCS<<32|HCE`,
`fb = UTRLBAU<<32|UTRLBA`, `dtb = UTRLDBR<<32|UTRLRSR`. CAP bit 24 is 64AS.
No register is written. The function was checked in the built ELF
(`ldr` from one base at offsets 0, 8, 0x30, 0x34, 0x50, 0x54, 0x58, 0x60,
then the four `field()` calls at banner offsets 0x103/0x11b/0x12f/0x6a).
45 tools tests pass (one new validation test).

**Prepared, not flashed (safe snapshot):**
`research/matisse/20261023-ufs/entryprobe-el1-ufs-regs.img`,
26,562,560 B, SHA256
`ba1ed1c41c5ae2052d2fb2a7a7bf0e78e28f2104a8bf2c06601ebae2173797b6`;
level `el1-load` (copies the payload, never jumps to XNU), `--ufs-regs`,
payload `matisse-xnu-0084-ufs-rtcfast.payload` SHA256
`755ae110f814e67245ea8d1f1c0b7694e65ca8b312e5316db7a39b5d8b4a1478`.
It must return to stock Linux in the same boot regardless of UFS state.
Predicted written partition
`75c514ba0f382b96596f386a8245b06d8fec3fcb5700f136144392582a61309c`.

**Prepared, not flashed (takeover checkpoint):**
`research/matisse/20261023-ufs/entryprobe-el1-ufs-takeover-brk.img`,
26,562,560 B, SHA256
`6e0eb654887b9b7a1e310579c9a24765a4ce9c9c541bb290dc8ceffe18507fd5`;
payload SHA256 `de5d62c6d1bb38a845151d0b9b9a182f0a4e9c9c93b8402388999b4bb9f3317c`;
rtcfast + `--ufs-regs`, BRK at VA `0xfffffe00074e83b4` (payload offset
`0x4e47a4`, PA `0x1014e83b4`), replacing the first TUR `bl ufs_scsi`
(`0x940000f7`). A hit proves host takeover succeeded and also carries the
pre-XNU register snapshot. Predicted written partition
`789468272a2e190ec69a762b185c8a47834124510f8e3d2bf79af90b249e25b7`.

**HARDWARE PASS (2026-10-23): pre-XNU UFSHCI state is takeover-ready.**
`research/matisse/20261023-ufs/entryprobe-el1-ufs-regs.img`,
26,562,560 B, SHA256
`ba1ed1c41c5ae2052d2fb2a7a7bf0e78e28f2104a8bf2c06601ebae2173797b6`
(`el1-load`, `--ufs-regs`, payload `755ae110...`), written partition
`75c514ba0f382b96596f386a8245b06d8fec3fcb5700f136144392582a61309c`;
device returned in 30.6 s and the original `boot_a` was restored/verified.
Record (fields repurposed by the snapshot):

```
gicd=3587071f00000200  -> CAP=0x3587071f VER=0x00000200
vtimer=0000010f00000001 -> HCS=0x0000010f HCE=0x00000001
fb=0000000051254400     -> UTRLBAU=0x00000000 UTRLBA=0x51254400
dtb=0000000000000001    -> UTRLDBR=0x00000000 UTRLRSR=0x00000001
stage=000000000000007f
```

CAP bit 24 (64AS) is set, so DMA above 4 GiB is explicitly supported and the
driver's ENXIO gate passes. HCE=1 and HCS has DP|UTRLRDY|UCRDY; no request is
outstanding and the bootloader's list is running. The host is in the state
`ufs_take_over_host()` expects, so the full-init failure is in the takeover
write-back or (more likely) the first SCSI command / GPT read, or in the
devfs registration. UTRLBA=0x51254400 is low memory and 1 KiB aligned.

**Prepared, not flashed: UFS error-code checkpoint.**
`research/matisse/20261023-ufs/entryprobe-el1-ufs-error-brk.img`,
26,562,560 B, SHA256
`f7fb157e0d009191ec544026db126d9156b55f462a7ba83328782b5f1ac0d532`;
payload `matisse-xnu-0084-ufs-error-brk.payload`, 16,605,888 B, SHA256
`63a9634d6c478dc1d9edcff2805504fa2b0acd42391c6ac299117ef79c99daee`.
rtcfast + `--ufs-regs`; BRK at VA `0xfffffe0007a42488` (payload offset
`0xa3e878`, PA `0x101a42488`) replaces the `cbnz w0` (`0x350032c0`) right
after `bl _sweet_ufs_rootdev` in `IOFindBSDRoot`. This intercepts both
outcomes instead of letting the error path panic and reboot:

- `x0 == 0`: the whole UFS init (takeover, TUR, GPT, bdevsw/cdevsw/devfs)
  succeeded.
- `x0 != 0`: `x0` is the driver's errno (5 EIO, 6 ENXIO, 12 ENOMEM,
  16 EBUSY, 2 ENOENT, 60 ETIMEDOUT, ...).

Expected record: `pc=fffffe0007a42488`, plus the same UFS snapshot fields.
Predicted written partition
`094d6c7d3cd1472fac68f67e295ce28107a013abec541a6da320749e499b4ddd`.
The test can take up to ~15 s of SCSI timeouts; the relay returns to Recovery
in the same boot.

**HARDWARE RESULT (2026-10-23): `sweet_ufs_rootdev` returns ETIMEDOUT.**
`research/matisse/20261023-ufs/entryprobe-el1-ufs-error-brk.img`,
SHA256 `f7fb157e0d009191ec544026db126d9156b55f462a7ba83328782b5f1ac0d532`,
written partition `094d6c7d...`; device returned in 40.9 s and `boot_a` was
restored/verified. Same-boot record:

```
pc=fffffe0007a42488 esr=f2005357 x0=000000000000003c
gicd=3587071f00000200 vtimer=0000010f00000001 fb=0000000051254400
dtb=0000000000000001
```

`x0 = 0x3c` is **ETIMEDOUT (60)** from `ufs_scsi()`: the UTRL doorbell bit 0
never cleared before the 5 s deadline, three TUR attempts. This proves
`ufs_take_over_host()` succeeded (UTRLBA/UTRLBAU/UTRLRSR readback passed);
the host accepted the kernel's transfer list but never processed slot 0.
The extra ~10 s over the baseline (`online after 40.9 s`) is the SCSI
timeout budget. The host's own CAP/HCS/HCE/UTRL state was takeover-ready
(previous snapshot), so the remaining differences are the kernel's
**above-4-GiB UTRL/DMA address** and any MTK-specific host handoff.

**HARDWARE RESULT (2026-10-23): low-memory selftest processed; OCS 5.**
`research/matisse/20261023-ufs/entryprobe-el1-ufs-selftest.img`,
26,566,656 B, written partition
`a8698232a87020f7a6fbbd7dd5b48b7d79c45a8f41ee1fc80c79cce05790b9aa`;
device returned in 34.7 s and `boot_a` was restored/verified. Record:

```
esr=0000000000000005  -> test stage 5 (GPT scan returned)
x0=0000000000000001   -> READ CAPACITY rc 1 (timeout)
x16=0000000000000500  -> OCS 5, SCSI status 0
gicd=3587071f00000200 vtimer=0000010f00000001
fb=0000000051254400   dtb=0000000000000001
```

The low-memory UTRL **is** processed (the doorbell clears), unlike the
kernel's above-4-GiB list. `x16` is stale from the last completed TUR
because a timed-out `scsi()` does not update OCS/status; OCS 5 is
`OCS_PEER_COMM_FAILURE` in Linux `include/ufs/ufshci.h` (not "invalid
header"). `spsr` (last LBA) is 0. `far` (block size) is overwritten by
`loader_boot`'s `diag_stage`; use only `esr`/`x0`/`x16`/`spsr` for the test.

**Root cause found: SCSI CDBs were submitted as native UFS commands.**
Linux `include/ufs/ufshci.h` defines `UTP_CMD_TYPE_SCSI = 0x0`,
`UTP_CMD_TYPE_UFS = 0x1`, `UTP_CMD_TYPE_DEV_MANAGE = 0x2`. Both
`shim/ufs.c` and `bsd/dev/sweet_ufs.c` set `dw0 |= 1 << 28` (**CT=1**,
native UFS) for a SCSI CDB UPIU. The sweet/Qualcomm host tolerated it; the
MTK host fails the transfer with `OCS_PEER_COMM_FAILURE` (5). Commit
`fd8d369` fixes the shim (`dw0 = (dd << 25) | (1 << 24)`); the kernel needs
the same one-line change plus a CI rebuild (patch 0086, not yet written).

**HARDWARE RESULT (2026-10-23): CT=0 changes OCS 5 -> 7.**
`research/matisse/20261023-ufs/entryprobe-el1-ufs-selftest-ct0.img`,
SHA256 `fb2e4338...`, written partition `8f829d29...`; device returned in
30.7 s (no SCSI timeouts) and `boot_a` was restored/verified. Record:

```
esr=0000000000000005  -> stage 5 (GPT scan returned)
x0=0000000000000002   -> READ CAPACITY rc 2 (OCS set)
x16=0000000000000700  -> OCS 7 (OCS_FATAL_ERROR), status 0
spsr=0                -> last LBA 0
```

So CT=0 makes the host complete the command instead of reporting
`OCS_PEER_COMM_FAILURE` (5). The first **data** command (READ CAPACITY,
8 bytes) now ends in `OCS_FATAL_ERROR` (7). The TUR result is overwritten in
this encoding, so it is not yet known whether the no-data TUR succeeded.
Likely remaining suspects: the UCD/PRDT alignment (the shim's UCD was only
128-byte aligned), the PRDT/data descriptor, or the response UPIU.

**HARDWARE RESULT (2026-10-23): TUR itself gets OCS 7, no response UPIU.**
`research/matisse/20261023-ufs/entryprobe-el1-ufs-selftest-ct0-v2.img`,
26,566,656 B, SHA256 `a669f68e...`, written partition `70b5a2a7...`;
device returned in 30.7 s and `boot_a` was restored/verified. Record:

```
esr=0000000000000005  -> stage 5 (GPT scan returned)
gicd=0000000000000702 -> TUR rc 2 (OCS), OCS 7 (FATAL_ERROR),
                         SCSI status 0, response[0/6/7] = 0
vtimer=0000000000000702 -> READ CAPACITY identical
fb=0 dtb=0            -> last LBA 0, block size 0
```

4 KiB-aligning the UTRL/UCD changed nothing, and the **no-data TUR** fails
the same way: the host completes it with `OCS_FATAL_ERROR` and writes no
response UPIU. So this is not PRDT/data alignment; the command does not
reach a responsive device. The likely cause is the UniPro link state after
LK: the MTK host's auto-hibernate (Linux sysfs shows `auto_hibern8=5000`
us) can leave the link in HIBERN8 when XNU takes over.

**HARDWARE RESULT (2026-10-23): link is not hibernated; hibernate exit fails.**
`research/matisse/20261023-ufs/entryprobe-el1-ufs-selftest-ct0-v3.img`,
SHA256 `71002069...`, written partition `ce33e949...`; returned in 30.7 s,
`boot_a` restored/verified. Record:

```
fault=0x10f      -> HCS after = 0x10f (DP|UTRLRDY|UCCS=1|UCRDY)
x0=0             -> IS before = 0 (no pending UIC/hibernate/link-lost bits)
x16=0x400        -> IS after = UIC_COMMAND_COMPL only (no 0x20 exit bit)
spsr=0x1         -> UIC ARG2 result 1 (failure)
gicd=0x702 vtimer=0x702 -> TUR and READ CAPACITY still OCS 7
```

So the link is **not** in HIBERN8 (`IS` had neither 0x40 enter nor 0x20
exit), and `DME_HIBERNATE_EXIT` is rejected with result 1. Hibernation wake
is not the missing step. The probe's UTRL is at PA **0x40020000**: the
stock Linux Image's `Kernel code` in `/proc/iomem` starts at 0x40200000 and
the probe prefix is 2 MiB before it, so this selftest really did use
low-memory, 4 KiB-aligned descriptors. (The kernel's own UTRL above 4 GiB
is still a separate, unproven difference; it timed out rather than
completing with OCS.)

**HARDWARE RESULT (2026-10-23): wake strategies fail; vendor pre-link needed.**
`research/matisse/20261023-ufs/entryprobe-el1-ufs-selftest-ct0-v5.img`,
SHA256 `5f023d29...`, written partition `2dac484c...`; returned in 31.7 s,
`boot_a` restored/verified. Record:

```
gicd=0fff000000000702 -> strategy 0 baseline: TUR rc 2, OCS 7, HCS 0xf
vtimer=0f01000000000702 -> strategy 1 hibernate exit: OCS 7, UIC result 1
fb=0f01000000000702     -> strategy 2 DME_LINK_STARTUP: OCS 7, UIC result 1
dtb=00000000000000fe    -> strategy 3 HCE reset failed; HCS after = 0x8
x0=0 x16=0x10f spsr=0 fault=0x8
```

A bare `DME_LINK_STARTUP` (0x16) fails with UIC result 1, and toggling
HCE alone leaves HCS 0x8 (device not present / lists not ready).
`/proc/iomem` on Recovery gives `Kernel code 0x40200000`; the probe prefix
is 2 MiB below it, so the shim UTRL was at PA 0x40020000: genuinely
low-memory and 4 KiB aligned. The shim's OCS 7 is therefore not the
above-4-GiB issue (that remains specific to the XNU driver's timeout).

**Vendor sequence found (MiCode rubens-s-oss, `drivers/scsi/ufs/ufs-mediatek.c`).**
MediaTek's `pre_link` runs before every `DME_LINK_STARTUP`:
`DME_SET VS_UNIPROPOWERDOWNCONTROL (0xD0A8) = 0`, then clears bit 6 of
`VS_SAVEPOWERCONTROL (0xD0A6)` (disable deep stall); `hce_enable_notify`
also asserts the UniPro/HCI/crypto resets and sets
`REG_UFS_XOUFS_CTRL (0x140) |= 0x80`. A bare link startup without this
fails, matching the result.

**HARDWARE RESULT (2026-10-23): pre-link alone does not start the link.**
`research/matisse/20261023-ufs/entryprobe-el1-ufs-selftest-ct0-v6.img`,
SHA256 `0d367d5a...`, written partition `18c9a00c...`; returned in 30.7 s,
`boot_a` restored/verified. Record:

```
gicd=0fff000000000702 -> strategy 0 baseline: OCS 7
vtimer=0f01000000000702 -> strategy 1 hibernate exit: OCS 7, UIC 1
fb=0f01000000000702     -> strategy 2 MTK pre-link + LINK_STARTUP: OCS 7, UIC 1
dtb=0f01000000000702    -> strategy 3 pre-link + DME_ENABLE + LINK_STARTUP: OCS 7, UIC 1
x0=0 x16=0x10f spsr=0x401 fault=0x10f
```

`VS_UNIPROPOWERDOWNCONTROL`/`VS_SAVEPOWERCONTROL` and `DME_ENABLE` are not
enough; the link still refuses to start (UIC result 1). The host stays
HCS 0x10f, so the failure is not a state loss from our commands.

**Reset-controller decode (live FDT).** `ufs_ao_cfg@112b8000` and
`ufs_pdn_cfg@112bc000` expose `ti,syscon-reset` children with
`ti,reset-bits` (7 cells: assert offset/bit, deassert offset/bit, status
offset/bit, flags):
- unipro (ao idx 0): assert 0x44 bit 1, deassert 0x48 bit 1
- crypto (pdn idx 0): assert 0x44 bit 0, deassert 0x48 bit 0
- hci (pdn idx 1): assert 0x44 bit 1, deassert 0x48 bit 1
- flags 0x1c = ASSERT_SET | DEASSERT_SET | STATUS_NONE → set the bit to
  assert/deassert; use read-modify-write.
The vendor `ufs_mtk_host_reset` asserts hci/crypto/unipro, waits ~100 us,
deasserts unipro/crypto/hci, then sets `XOUFS_CTRL (0x140) |= 0x80` before
the HCE cycle.

**HARDWARE RESULT (2026-10-23): reset leaves HCS=0x8 (UCRDY), then fixes.**
`research/matisse/20261023-ufs/entryprobe-el1-ufs-selftest-ct0-v7.img`,
SHA256 `150619b5...`, written partition `fb8e23be...`; returned in 31.7 s,
`boot_a` restored/verified. Record: strategies 0-2 unchanged (OCS 7,
UIC 1 for link startup); strategy 3 = `0xfe`; `fault=0x8`. So the syscon
reset + XOUFS + HCE cycle brought HCE up with **HCS=0x8 (UCRDY)** but the
readiness gate expected DP as well, which only appears after the link
starts. Strategy 3 therefore skipped the pre-link/link startup. This is a
test bug, not a host failure: UCRDY is exactly the expected post-HCE state.

**HARDWARE RESULT (2026-10-23): UTRLRDY is not a post-HCE bit.**
`research/matisse/20261023-ufs/entryprobe-el1-ufs-selftest-ct0-v8.img`,
SHA256 `9dfe6a03...`, written partition `84ea176b...`; returned in 31.7 s,
`boot_a` restored/verified. Strategy 3 still `0xfe` with HCS 0x8. Since
`UTRLRDY` is only set after the request-list base/RSR are programmed
(`claim_host`), waiting for it before the link startup is another false
gate. HCE/UCRDY is the correct post-reset condition.

**HARDWARE RESULT (2026-10-23): reset + link startup still UIC 1.**
`research/matisse/20261023-ufs/entryprobe-el1-ufs-selftest-ct0-v9.img`,
SHA256 `db72f919...`, written partition `c40c0a48...`; returned in 32.7 s,
`boot_a` restored/verified. Record:

```
dtb=0801000000000001 -> strategy 3: TUR rc 1 (timeout), OCS 0,
                        UIC result 1, post-HCS = 0x8
spsr=0x404           -> IS after = UIC_COMMAND_COMPL | UIC_ERROR
```

So even after the syscon reset and HCE, `DME_LINK_STARTUP` still returns
UIC result 1 and raises `UIC_ERROR`; the host stays at UCRDY (0x8), no
device/list. The remaining vendor prerequisites are the reference clock
(`REG_UFS_REFCLK_CTRL` 0x144, REQUEST bit0 / ACK bit1), the UFS clocks and
the M-PHY/regulators. Note `REG_UFS_MTK_HW_VER` is 0x2240, outside the ADT
node's 0x1000 `reg` size (the live node is 0x2300); any driver access there
needs a larger mapping.

**HARDWARE RESULT (2026-10-23): ref clock is acked; link still fails.**
`research/matisse/20261023-ufs/entryprobe-el1-ufs-selftest-ct0-v10.img`,
SHA256 `2f26cdb7...`, written partition `9f02fdba...`; returned in 33.7 s,
`boot_a` restored/verified (`2931647a...`). Record:

```
gicd = 0x0fff000000000702  strategy 0 baseline: OCS 7, HCS 0xf
vtimer=0x0f01000000000702 strategy 1 refclk + pre-link + link: OCS 7,
                            UIC 1, HCS 0xf
fb    =0x0801000000000001  strategy 2 refclk + reset + refclk + pre-link +
                            link: rc 1 (timeout), OCS 0, UIC 1, HCS 0x8
dtb   =0x0801000000000001  strategy 3 reset + pre-link + link (no refclk):
                            rc 1, OCS 0, UIC 1, HCS 0x8
spsr  =3                   refclk ctrl [1:0]=3: REQUEST set and ACK received
fault =0x8                 post-HCS: UCRDY only
```

The reference clock handshake succeeds (the vendor's `setup_ref_clk`
precondition is met), so the remaining missing piece is the **UniPro /
M-PHY / link clock and power-domain init** that Linux performs at probe,
not just the ref clock. `DME_LINK_STARTUP` returns UIC result 1 and raises
`UIC_ERROR` even before any reset, so the link is not carrying commands
at handoff; LK evidently leaves the link/PHY powered down or unconfigured.
The `ufs_mtk_mphy_power_on` path is optional per DT (`phys` absent in the
live FDT), which leaves `ufs_mtk_setup_clocks`/`setup_regulators` and the
power-domain state as the suspects. Porting those needs the vendor clock
gate/power-domain register map; they are not reachable by a simple UIC or
HCE sequence.

**HARDWARE FAILURE (2026-10-23): v11 topckgen clock-gate write hangs.**
`research/matisse/20261023-ufs/entryprobe-el1-ufs-selftest-ct0-v11.img`,
SHA256 `6b21ef53...`, written partition `b19b53dc...` (verified). After
`adb reboot recovery` the device never returned within 100 s; it is stuck
at the logo/reboot loop, `adb` and `fastboot` both see nothing.
`boot_a` **contained the v11 image** and the full backup was not
restored. The last action was `mtk_clocks_on()` clearing pdn bits in the
topckgen `CLK_CFG_*_CLR` registers (UFS clocks); that write is the prime
suspect (the clock/power-domain handshake via the CLR/UPDATE registers
is not safe while the UFS power domain is in its handoff state). The shim
function is now **read-only** (commit after `ffebf76`) so no future build
repeats the write.

**Recovered 2026-10-23:** user entered fastboot; `fastboot flash boot_a
backup/boot_a-stock-trim.img` (SHA `fe6e8fbf...`) OK, Recovery came back
in 26.4 s, the full `boot_a-live-20261021.img` was pushed, `dd`-ed and
the partition verified `2931647a...`. Device is in Recovery, slot `_a`.

**Recovery steps (for reference):**
1. Power+VolumeDown -> fastboot.
2. `fastboot flash boot_a backup/boot_a-stock-trim.img`
   (20,873,216 B, SHA `fe6e8fbf...`).
3. Power+VolumeUp -> Recovery; confirm `adb devices` shows
   `Q4NVQWVW4DI7EUSW recovery`.
4. Push `backup/recovery-20261021/boot_a-live-20261021.img`
   (67,108,864 B), `dd` to `/dev/block/by-name/boot_a`, verify
   `2931647a56039722ea2585990b8ef3b1a2daf4c9b990231879f753049eaf86b1`.

Until step 4 succeeds, treat `boot_a` as the test image; do not boot
Android/system.

**Prepared, not flashed: UFS topckgen gate enable (v11).**
`research/matisse/20261023-ufs/entryprobe-el1-ufs-selftest-ct0-v11.img`,
26,570,752 B, SHA256
`6b21ef5348d84f9d231a654bb18074b0893f2a0da46e71171ad59565ad9d1add`;
predicted written partition
`b19b53dc5a2460bdebdbde2dc2451f133c32c4d711c9c1d50e32f19add1d9c56`.
The five UFS clocks in the DT are topckgen mux-gates: IDs 247/174/175/
176/192 = `ufs_hd_haxi` (`CLK_CFG_0` bit 23), `aes_ufsfde` (`CLK_CFG_13`
bit 31), `ufs` (`CLK_CFG_14` bit 7), `ufs_mbist` (`CLK_CFG_14` bit 15),
`ufs_hf_fmem` (`CLK_CFG_18` bit 15). `mtk_clocks_on()` clears any set pdn
bits via the CLR registers and pulses `CLK_CFG_UPDATE_0/1/2`, then records
the before/after masks in `spsr` bits [15:0] (bit per clock). `spsr`
[31:16] is the refclk control. If no gate was set, the clocks were
already on and the power-domain/regulator path is next; if a gate was
set and the link now starts, the XNU port needs this clock step too.

**Prepared, not flashed: UFS device reset via SMC (v13).**
`research/matisse/20261023-ufs/entryprobe-el1-ufs-selftest-ct0-v13.img`,
26,570,752 B, SHA256
`28f690d2ebc96efc0a63ba3ae93969c9b05ddcb7d1f2329874f7a72e94054798`;
predicted written partition
`948ee259fd4bc1a71af595c14ccb8a53f427a15df678e43f66cfaf0d01b2adb3`.
Linux Recovery shows `ufs0` power domain **off** and the UFS controller
suspended even while `ufs_hd_haxi_sel`/`ufs_hf_fmem_sel` clocks are on
(`ufs_sel`/`ufs_mbist_sel`/`aes_ufsfde_sel` off). The vendor resets the
**device** (not just the host) through the secure monitor:
`arm_smccc_smc(MTK_SIP_UFS_CONTROL=0x82000276,
UFS_MTK_SIP_DEVICE_RESET=BIT(1)=2, high)`, holding the active-low line
low >=10 us then releasing and waiting 10-15 ms
(`ufs_mtk_device_reset`). v13 strategy 3: host reset -> SMC device reset
(assert/release) -> refclk -> pre-link -> link startup. `spsr` bits
[31:16] are the SMC a0 result, [1:0] the refclk ACK. A hang is possible
if the monitor rejects the call; recovery is the trim-prefix path.

**HARDWARE RESULT (2026-10-23): SMC device reset brings the link up.**
`research/matisse/20261023-ufs/entryprobe-el1-ufs-selftest-ct0-v13.img`,
SHA256 `28f690d2...`, written partition `948ee259...`; returned in 31.7 s,
`boot_a` restored/verified. Record:

```
spsr = 0x0000000000000003  SMC a0=0 (device reset accepted), refclk acked
dtb  = 0x0f00000000000702  strategy 3 (host reset + SMC device reset +
                            refclk + link startup): TUR rc 2, OCS 7,
                            status 0, UIC 0, post-HCS 0xf
fault= 0x0f                final HCS DP|UTRLRDY|UCRDY
```

The SMC reset (`arm_smccc_smc(0x82000276, 2, 0/1)`) makes
`DME_LINK_STARTUP` return **UIC 0** and sets **DP**: the link is finally
up. The remaining TUR OCS 7 exposed the UTRD-header bug below; it is not
a link failure.

**ROOT CAUSE (UTRD header endianness).** Linux `struct
request_desc_header` on little-endian is byte2 bitfields: bit0 interrupt,
bits1-2 data direction, bits4-7 command_type. The shim (and the XNU
`bsd/dev/sweet_ufs.c`) wrote `dw0 = (dd << 25) | (1 << 24)`, which lands
in **byte3 reserved bits** and leaves the interrupt bit clear. The host
then rejects the command with OCS 7 once the link works. The correct
value for a no-data SCSI TUR is `dw0 = (1 | (dd << 1)) << 16`
(0x00010000 for TUR). This also means the earlier "CT=1 -> CT=0" change
was based on the wrong byte layout; the actual SCSI command type is 0 in
byte2 bits4-7.

**Prepared, not flashed: fixed-UTRD test (v14).**
`research/matisse/20261023-ufs/entryprobe-el1-ufs-selftest-ct0-v14.img`,
26,570,752 B, SHA256
`77f30da4f03f92ac7ee51afb834106bd374ce0e8f34d9a6cfc74707429e80bc2`;
predicted written partition
`a40327d2b97075edbbc242ef3d1fa2485147376106011d379271dd906a8bbc54`.
Strategies unchanged (3 = host reset + SMC device reset + refclk + link
startup); the corrected DW0 applies to every TUR. Success is strategy 3
TUR rc 0, OCS 0, status 0, post-HCS 0xf.

**HARDWARE RESULT (2026-10-23): corrected-UTRD v14 changes nothing.**
`research/matisse/20261023-ufs/entryprobe-el1-ufs-selftest-ct0-v14.img`,
SHA256 `77f30da4...`, written partition `a40327d2...`; returned in 31.7 s,
`boot_a` restored/verified. Strategy 3 still
`0x0f00000000000702` (rc 2, OCS 7, UIC 0, post-HCS 0xf), i.e. the UTRD
byte2 edit had no effect.

**Correction: DW0 was already right.** The vendor `ufshci.h` defines
`UTP_REQ_DESC_INT_CMD=0x01000000` (bit24),
`UPIU_COMMAND_TYPE_OFFSET=28`,`UTP_DEVICE_TO_HOST=0x04000000` (bit26),
`UTP_NO_DATA_TRANSFER=0`. So `(dd<<25)|(1<<24)` was correct; the v14
byte2 form was wrong and is reverted. The link-up TUR OCS 7 therefore
comes from the UTP path, not the descriptor header.

**Prepared, not flashed: NOP OUT first (v15).**
`research/matisse/20261023-ufs/entryprobe-el1-ufs-selftest-ct0-v15.img`,
26,570,752 B, SHA256
`fcde69bef92cd4fcf9b5514f9967f55785a15e83f743969d22ce4e653065c3bb`;
predicted written partition
`218621a175fec19bd61525b9f01c7028b74a194b11e767697481267886de46d5`.
Linux `ufshcd_verify_dev_init` sends a NOP OUT (UPIU 0x00,
`UTP_CMD_TYPE_UFS_STORAGE=1`) immediately after link startup, before
any SCSI command. v15 does the same in strategy 3, then the TUR. `spsr`
packs smc (bits32-39), NOP OCS (bits16-23), NOP rc (bits8-15), refclk
(bits0-7). If NOP is rc0/OCS0 and the TUR is still OCS 7, the failure is
SCSI/UPIU-specific; if NOP is also OCS 7, the UTP path is not ready.

**HARDWARE RESULT (2026-10-23): NOP OUT succeeds; SCSI OCS 7 is a
command-type bug.** v15 image `fcde69be...`, partition `218621a1...`;
returned in 31.7 s, `boot_a` restored/verified. `spsr=0x303` decodes as
smc a0=0, NOP OCS=0, NOP rc=3, refclk=3. rc 3 was our check expecting a
RESPONSE (0x21) for a NOP; the NOP IN UPIU is 0x20, so the **NOP OUT
completed successfully (OCS 0)** and the UTP/link path is proven.

The vendor `ufshcd_comp_scsi_upiu` selects the command type by version:
`ufs_version <= 1.1` -> `UTP_CMD_TYPE_SCSI` (0), otherwise
`UTP_CMD_TYPE_UFS_STORAGE` (1). Our controller reports VER=0x200 (2.0),
so **SCSI commands must also use CT=1**. The TUR was sent with CT=0 and
the host rejected it with OCS 7 (fatal) while the CT=1 NOP succeeded.
This also explains why the earlier "CT=1 -> CT=0" change looked useful
when the link was down: it was not the cause then, but CT=1 is correct.

**Prepared, not flashed: CT=1 SCSI (v16).**
`research/matisse/20261023-ufs/entryprobe-el1-ufs-selftest-ct0-v16.img`,
26,570,752 B, SHA256
`beab6bc7067b5a01511420f6e5576cd65f7fe77adfe3ef4ac703d8cac83465c0`;
predicted written partition
`146c02062c9bae00dcc90b734230d6ca02169151004dab3aa87f9552a28a312d`.
`scsi()` now passes ctype 1; the NOP response check accepts 0x20. Success
for strategy 3: NOP rc0/OCS0, TUR rc0/OCS0/status0, post-HCS 0xf,
`spsr` = 3 (smc 0, NOP 0, refclk 3).

**HARDWARE PASS (2026-10-23): UFS SCSI works on hardware.** v16 image
`beab6bc7...`, partition `146c0206...`; returned in 31.7 s, `boot_a`
restored/verified. `spsr=3` (smc a0=0, NOP rc0/OCS0, refclk 3) and
`dtb=0x0f00020121020004` decodes as strategy 3: TUR **rc 4 (CHECK
CONDITION)**, **OCS 0**, status **0x02**, resp UPIU **0x21**, UIC **0**,
post-HCS **0xf**. That is a complete UPIU round trip: the link is up,
the NOP OUT and the SCSI TUR both complete, and the device returns a
unit-attention status (normal after reset). The earlier OCS 7 was
because SCSI was sent with CT=0; for UFSHCI 2.0 (`VER=0x200`) the vendor
uses `UTP_CMD_TYPE_UFS_STORAGE` (CT=1) for SCSI too.

**Proven on-hardware sequence (shim, `shim/ufs.c`):**
1. `mtk_host_reset`: syscon assert/deassert UniPro/HCI/crypto, XOUFS
   (0x140) |= 0x80, UTRLRSR=0, HCE 1->0->1, wait UCRDY.
2. SMC device reset: `arm_smccc_smc(0x82000276, 2, 0)`, >=10 us,
   `(..., 2, 1)`, 10 ms. (Vendor arm64 ID is 0xC2000276; the SMC32
   form worked. XNU tries 0xC2 then falls back to 0x82.)
3. Ref clock: `REG_REFCLK_CTRL` (0x144) REQUEST bit0, wait ACK bit1.
4. MTK pre-link: DME_SET 0xD0A8=0; clear bit6 of 0xD0A6 if set.
5. `DME_LINK_STARTUP` (0x16); UIC result 0.
6. Program UTRL base/RSR, check DP|UTRLRDY.
7. NOP OUT (CT=1, UPIU 0x00) then SCSI TUR (CT=1, UPIU 0x01).

**XNU port: `xnu/patches/0086-sweet-ufs-mtk-reset-link.patch`**
(commit pending CI). It adds the syscon mappings (`0x112b8000`,
`0x112bc000`), SMC device reset, refclock, pre-link, host reset, UIC
helper, and rewrites `ufs_take_over_host` to run the sequence before
taking the request list. `sweet_ufs.c` passes the local XNU compile
check (`tools/xnu-cc.py` with the CI buildtree, 0 failures). The
existing TUR retry loop covers the unit-attention status. CI build is
triggered by the push; then build the boot image with the new kernel and
test `rd=ufsroot0` on hardware (approval + full restore as usual).

**Open items.** Confirm the correct SMC ID on the next boot (`0xC2` vs
`0x82`); the driver falls back automatically. The XNU `ufs_scsi` already
uses CT=1. Root mount still needs the iOS root image on hardware; the
local Mac has no iOS root image (it is on the Linux host), so the
partition/GPT + TUR proof is the limit of this session.

**Prepared, not flashed: XNU UFS pre-init image (no CI needed).**
`research/matisse/20261023-ufs/entryprobe-el1-xnu-ufs-init.img`,
26,570,752 B, SHA256
`74ee0eb7c049a0140e8132a3bc321790a48766da7119163200f3cb810c2cf3d4`;
predicted written partition
`3e0f1e59802afcd89fe7ebbf52910647abfa8c6110fd2ebf71867c8866aa16d7`.
This boots the **unpatched 0084 XNU kernel** (payload `matisse-xnu-0084-
ufs-rtcfast.payload`, SHA `755ae110...`) and runs the new shim
`--ufs-init` before the jump: host reset, SMC device reset, refclock,
pre-link, link startup, then programs the shim's low UTRL and RSR=1.
The 0084 `sweet_ufs` driver already uses CT=1 and low-DMA, and its
takeover check sees DP|UTRLRDY; it then replaces the list and issues the
TUR. `--ufs-init` (commit in `tools/mkentryprobe.py`, `shim/ufs.c`,
`shim/entryprobe.c`) requires el1-xnu/el1-load; 47 tools tests pass.
This avoids the CI push blocker (GitHub user Jinsens has no write access
to dipa-studio/ios-sweet; remote main does not contain our commits).

Success criteria: XNU console prints
`SWEET UFS: "userdata" on LUN 0: first block ...` and proceeds; the
persistent log (if written) lives in the UFS partition, which is itself
proof the read/write path works. Observe the panel; restore `boot_a`
after the test as usual.

**HARDWARE RESULT (2026-10-23): XNU pre-init image hangs at logo.**
Image `74ee0eb7...` (full XNU) and checkpoint image `a85ca565...`
(partition `6de8ff11...`) both never returned; the user saw the logo
reboot loop. `boot_a` was restored through fastboot (trim `fe6e8fbf...`,
Recovery up in 26.4 s, full `2931647a...` verified). The shim pre-init
or the XNU path hung before any checkpoint. Next isolation:
`research/matisse/20261023-ufs/entryprobe-el1-ufs-preinit.img`, SHA256
`f4758deb...`, predicted `7e547768...`: runs `--ufs-init` at el1-load
(no XNU jump) and records stage/HCS in the banner. `esr` = init stage
(1 host reset failed, 2 link startup failed, 3 ready), `far` =
HCS<<32|UTRLRSR. This tells whether `init_ufs_link` itself hangs/fails
at the XNU call site.

**HARDWARE RESULT (2026-10-23): pre-init completes at el1-load.**
`entryprobe-el1-ufs-preinit.img` (`f4758deb...`, partition `7e547768...`)
returned in 29.7 s; banner `esr=3` = `init_ufs_link` reached **ready**
(stage 3). `stage`/`far` were overwritten by the loader afterwards, but
the stage value is the function's own counter. So the pre-init sequence
itself is good; the logo hang is **inside XNU** after the jump.

**Prepared, not flashed: pre-init + error checkpoint.**
`research/matisse/20261023-ufs/entryprobe-el1-xnu-ufs-init-error-brk.img`,
26,570,752 B, SHA256
`e7b21527e491b998a664f156444e725b971e617fefb7b82186403f68b158f9b0`;
predicted written partition
`7f4a9ef8b153ceab1fff0864b330e2e0140e78db7e5e121b7e4c2f663b2e5e96`.
Boots the **unpatched 0084 kernel** with `--ufs-init`; the payload's BRK
replaces `cbnz w0` after `bl _sweet_ufs_rootdev` (`0xfffffe0007a42488`),
so the shim records x0 = the driver's return code. Previously (link
down) this was `0x3c` = ETIMEDOUT. Now: 0 means the driver took over and
found the partition; other errno values pin the failing stage.

**HARDWARE RESULT (2026-10-23): XNU driver returns EIO at takeover.**
Pre-init + error-BRK image `e7b21527...` (partition `7f4a9ef8...`)
returned in 29.6 s; `pc=fffffe0007a42488` (the `cbnz w0` after
`_sweet_ufs_rootdev`), **x0=5 = EIO**. Disassembly of `sweet_ufs.o`
(SHA-fetched from the kernel archive) shows the EIO block at VA
`fffffe00074e8368+0x130` reached by two `b.ne` at `...8374`
(`c1000054`) and `...8380` (`61000054`) when `UTRLBA`/`UTRLBAU` do not
read back as programmed. XNU's contiguous DMA is in the high DDR bank
(`dram-base=0x100000000`), so the suspect is the controller's 64-bit
UTRL base readback (CAP_64AS is set, but the register may not retain
the high word).

**Prepared, not flashed: high-UTRL-base readback probe.**
`research/matisse/20261023-ufs/entryprobe-el1-ufs-preinit-highprobe.img`,
26,570,752 B, SHA256
`97e348429c705684b10560d3f83c3e1219eec6d84f2b37093b28a08d3c09bfac`;
predicted partition `566f28da...`. `init_ufs_link` zeroes one 4 KiB
scratch page at physical `0x1_00000000`, programs UTRLBA=0, UTRLBAU=1,
RSR=1, reads them back, then restores the low list **without ringing a
doorbell**. Banner `x0 = UTRLBAU<<32|UTRLBA` (expect `0x100000000`),
`x16 = UTRLRSR` (expect 1). If BAU reads 0, low DMA is mandatory
(kernel patch/ADT); if it sticks, the EIO is elsewhere.

**HARDWARE RESULT (2026-10-23): host keeps the high UTRL base.**
High-probe image `97e34842...` (partition `566f28da...`) returned in
30.7 s; banner `x0=0x0000000100000000` (UTRLBAU=1, UTRLBA=0) and
`x16=1` (UTRLRSR). 64-bit UTRL programming works, so the XNU EIO is
**not** the base readback; it is `ufs_scsi`'s command-failure path
(`ocs || upiu != 0x21 || resp[6] || resp[7]`) returning EIO. The first
TUR after the device reset gets **CHECK CONDITION (unit attention)** and
the driver retries the TUR without a REQUEST SENSE, so all three retries
fail. The shim now clears the UA in `init_ufs_link`: TUR, REQUEST SENSE
(0x03, 18 bytes) if the TUR failed, TUR again; stage 4 = cleared.

**Prepared, not flashed: UA-clearing pre-init + error checkpoint.**
`research/matisse/20261023-ufs/entryprobe-el1-xnu-ufs-init-ua-clear-error-brk.img`,
26,570,752 B, SHA256
`6b9a2b08f88179b8acadc9f14484fea84a3886f63eeb447611992d7f6de9fce4`;
predicted partition `7c92190b...`. Unpatched 0084 kernel, BRK after
`_sweet_ufs_rootdev`: x0=0 means the driver took over, read the GPT and
set up ufsroot0; 2 = ENOENT (partition name/read); 5 = TUR still fails.
`spsr`/banner `pc` carries the shim's own TUR result.

**Prepared, not flashed: low-RAM XNU checkpoint (UFS DMA below 4 GiB).**
`research/matisse/20261023-ufs/entryprobe-el1-xnu-ufs-lowmem-error-brk.img`,
26,570,752 B, SHA256
`a91ca8eb5e8017dd4432ca11358723cacd928413ae8bfc704d4bd89ea4a02236`;
predicted partition `6408aa5a...`. `tools/mkadt.py --low-mem` (board
matisse) emits `dram-base=0x80000000`, `dram-size=0xf800000` (the free
248 MiB before the first low-bank carve-out, consys at 0x8f800000).
Payload `matisse-xnu-0084-ufs-lowmem-error-brk.payload` (SHA
`1c5884a3...`) is the same 0084 kernel with rtcfast + the error BRK,
rebuilt with the low ADT and the same cmdline. Image flags use
`--xnu-clean-limit 0x8f800000` and `--xnu-restore-ttbr0 0x8117c000`
(0x117c000 offset from the new base; the high-mem value was
0x10117c000). With the UFS DMA allocation now below 4 GiB, the driver's
UTRLBAU is 0 and the UA was cleared by the shim; the error checkpoint
should reach x0=0. Risk: 248 MiB may be below XNU's minimum, and the
TTBR0 offset is inferred, so the checkpoint may miss.

**HARDWARE FAILURE (2026-10-23): low-RAM XNU hangs before the checkpoint.**
Image `a91ca8eb...` (partition `6408aa5a...`) never returned in 120 s;
logo reboot loop. Recovery: fastboot trim `fe6e8fbf...`, Recovery in
26.5 s, full `2931647a...` restored/verified. So the 248 MiB low window
(0x80000000-0x8f800000) is not enough for XNU's bootstrap, or the
inferred bootstrap TTBR0 0x8117c000 / clean limit is wrong. Do not
repeat this image. The low-bank carve-outs (consys at 0x8f800000, md at
0xd0000000, fb 0xfcb3f000, ...) mean a larger low window needs explicit
reserved-memory nodes in the ADT.

**Open question: does the shim's UA clear work?** The XNU driver's first
TUR after the pre-init still returns EIO. Test at el1-load with
`--ufs-init`: banner x0 = `info[3]` = second TUR packed
`rc | OCS<<8 | status<<16 | resp0<<24`; x16 = high UTRL readback. If
status is 0, the UA is clear and the XNU EIO is a high-DMA/command issue;
if status 2, the device still reports unit attention (needs a different
sense/clear or the driver's retry logic).

**HARDWARE RESULT (2026-10-23): UA persists after SENSE.** el1-load
UA image `98fa8264...` (partition `8acb824a...`) returned in 30.7 s;
banner `x0=0x21020004`: second TUR rc4, OCS0, **status 2** (CHECK
CONDITION), response UPIU 0x21. So the REQUEST SENSE did not clear the
unit attention. `x16=0x100000000` again confirms the high UTRL base.

**Likely cause: wrong SMC ID.** The shim used `0x82000276`, the SMC32
form; the vendor arm64 ID is
`ARM_SMCCC_CALL_VAL(FAST_CALL, SMC_64, OWNER_SIP, 0x276)=0xc2000276`.
`mtk_device_reset` now tries 0xc2 first, falls back to 0x82, and records
the first a0 in `ufs_test_info[4]`.

**Prepared, not flashed: SMC64 reset + UA check.**
`research/matisse/20261023-ufs/entryprobe-el1-ufs-preinit-smc64.img`,
26,570,752 B, SHA256
`51f0be0a98879e80b34900ebc88238f1c3cc77cb63bfd771563a99511f28180e`;
predicted partition `d299b125...`. el1-load only; banner
`x16`=first SMC a0 (0 = 0xc2 accepted), `x0`=second TUR
(`0x21000000` = GOOD, `0x21020004` = still CHECK CONDITION).

**HARDWARE RESULT (2026-10-23): SMC64 ID accepted; UA still persists.**
SMC64 image `51f0be0a...` (partition `d299b125...`) returned in 30.7 s;
banner `x16=0` = `0xc2000276` accepted (a0=0), `x0=0x21020004` = second
TUR still OCS 0, **status 2 (CHECK CONDITION)**, RESPONSE UPIU 0x21.
So the reset ID is fixed (the kernel patch 0086 already prefers 0xc2),
but the device keeps reporting unit attention / not-ready after TUR ->
REQUEST SENSE -> TUR. The sense command may itself be failing, or the
device needs the vendor's QUERY/power-mode init (Linux runs NOP OUT,
QUERY device/geometry/unit descriptors, and a power mode change before
SCSI). This is a kernel-driver task, not a shim one.

**Session status.** Shim UFS is proven end-to-end: link startup (host
reset + SMC64 device reset + refclock + pre-link), NOP OUT, SCSI TUR with
CT=1, RESPONSE UPIU 0x21, OCS 0. XNU's unpatched 0084 driver takes over
the live link but its first TUR returns EIO; the low-RAM ADT test hung
before its checkpoint (do not repeat). Device restored, `boot_a`
`2931647a...` verified, slot `_a`, Recovery online.

**Remaining work (needs CI or push access).** The GitHub credential on
this Mac is `Jinsens`, which gets 403 on `dipa-studio/ios-sweet`; remote
main does not contain our commits. Once `xnu/patches/0086` is on main,
the CI build can test a kernel that (a) runs the MTK reset/link sequence
itself and (b) implements the device init/UA handling (e.g., NOP OUT,
QUERY, power mode, or a REQUEST SENSE that is known to work). A proper
low-DMA path (reserved low region in the ADT or a low `max_pnum`
allocation with low pages actually managed) is still unproven.

**CI ACCESS SOLVED (2026-10-23).** The user's fork is
`https://github.com/Jinsens/ios-sweet`; the local `fork` remote points
there and `main` was fast-forwarded `58f7c2c..7cecd9b`. A plain push did
not trigger `xnu.yml` because `xnu/patches/0086` was already in the
fork's history (paths filter), so the workflow was started with
`workflow_dispatch` (API, run **39953360175**, commit `7cecd9b`).
Artifacts `xnu-kernel`/`xnu-buildtree` are downloaded to
`xnu/out/ci-39953360175/` by `/tmp/watch_ci.py` (uses the git credential
token, never prints it). The 0086 kernel needs a fresh payload
(`mkpayload.py` with the UFS ADT and the usual cmdline); rtcfast/BRK
binary patches are 0084-specific and are **not** applied to 0086.

**CI 0086 built (run 39953360175).** Kernel
`xnu/out/ci-39953360175/kernel.development.sweet`, SHA256
`0f40d4b7...`, 17,206,416 B. `_sweet_ufs_rootdev` is still at
`0xfffffe00074e8090` (same as 0084), and its caller's `cbnz w0` moved to
`0xfffffe0007a42868`. Patched that word to BRK `0xd42a6ae0`, built
`matisse-xnu-0086-ufs-error-brk.payload` (SHA `29ae9909...`) with the
UFS ADT and the usual cmdline. rtcfast is **not** applied (0084 VAs).

**Prepared, not flashed: 0086 self-init error checkpoint.**
`research/matisse/20261023-ufs/entryprobe-el1-xnu-0086-ufs-error-brk.img`,
26,562,560 B, SHA256
`53aac6c33058b970057fe5efc21837b1c95687bf2873829fc39335692605ef66`;
predicted partition `d8e83381...`. No shim `--ufs-init`: the 0086
driver runs the MTK host reset, SMC64 device reset, refclock, pre-link,
link startup and takeover itself, then the BRK records x0. Without
rtcfast the boot waits ~60 s; allow 180 s.

**HYBRID KERNEL (2026-10-23): 0084+0086, no 0085.** CI run
39956168337 built with `0085-matisse-video-console-refresh.patch`
renamed to `.disabled`; kernel SHA256 `217659ff...`, 17,222,848 B.
`sweet_ufs.o` is the 0086 build (host reset/link strings). Function
`_sweet_ufs_rootdev` at `0xfffffe00074e8090`, caller `0xfffffe0007a42864`
(`cbnz w0` at `+4`). rtcfast sites shifted +0x3e0:
`0x79ad450` (`0x94005459`), `0x7a42250` (`0x97fe0ab8`), `0x7a42294`
(`0x340000e9`); error BRK at `0x7a42868`. Image
`entryprobe-el1-xnu-hybrid-ufs-error-brk.img`, SHA256
`25335318...`, predicted partition `805c96e0...`. No shim `--ufs-init`;
the 0086 driver does the full MTK init. x0 after rootdev: 0 success,
5 EIO, 2 ENOENT, 6 ENXIO.

**HARDWARE RESULT (2026-10-23): hybrid (no 0085) reaches the checkpoint;
x0=6 ENXIO.** Image `25335318...` (partition `805c96e0...`) returned in
31.7 s, `pc=fffffe0007a42868`, **x0=6**. So 0085 was indeed the logo
hang; the 0086 driver runs but its host reset/link path returns ENXIO
(`host reset failed` or `link startup failed`).

**ROOT CAUSE CANDIDATE (fixed, CI rebuilding): SMCCC a3-a7.** The
compiled `ufs_smc` sets only x0/x1/x2 before `smc #0`; x3-x7 were left
uninitialized. SMCCC requires a3-a7 = 0. The shim's call happened to
work; in the kernel the garbage registers can make the monitor reject
the UFS reset, leaving the link down -> ENXIO. Both the shim `smc3` and
the kernel `ufs_smc` now zero x3-x7 with `mov xN, xzr` before `smc #0`.
Commit `d561707`; CI run dispatched (0085 still disabled) to rebuild the
hybrid; next step: locate the function (pattern), apply the shifted
rtcfast (+0x3e0) and error BRK, rebuild the image, and read x0.

**Prepared, not flashed: SMC-register-fix hybrid checkpoint.**
Kernel `xnu/out/ci-39957884892/kernel.development.sweet` SHA
`4c61c01f...` (0084+0086, 0085 disabled, x3-x7 zeroed before smc).
Function `0x74e8090`, caller `0x7a42864`; rtcfast +0x3e0, error BRK at
`0x7a42868`. Image `entryprobe-el1-xnu-hybrid2-ufs-error-brk.img`,
SHA256 `b6f04c04...`, predicted partition `5c3af8b9...`. x0: 0 success,
5 EIO (TUR/UA), 6 ENXIO (reset/link still failing).

**ROOT CAUSE (ENXIO): HCS_UCRDY is bit 3, not bit 2.** The shim has
`HCS_UCRDY (1u << 3)` and its host reset works (post-HCE HCS=0x8). The
0086 kernel patch copied `(1u << 2)`, which is UTMRLRDY and never sets
after the MTK HCE cycle, so `ufs_host_reset` always timed out and
returned ENXIO (x0=6). Fixed in `0086` (commit `97cd5b2`); CI run for
`97cd5b2` dispatched (0085 still disabled).

**Prepared: UCRDY-fix hybrid checkpoint.** Kernel
`xnu/out/ci-39959703617/kernel.development.sweet` SHA `9394c4b9...`;
same function/caller VAs, rtcfast +0x3e0, error BRK. Image
`entryprobe-el1-xnu-hybrid3-ufs-error-brk.img`, SHA `0e0ff01c...`,
predicted partition `d6c6240a...`. x0: 0 success, 5 EIO (TUR/UA),
6 ENXIO (link startup).

**Prepared: stage-code hybrid checkpoint.** Kernel
`xnu/out/ci-39961292229/kernel.development.sweet` SHA `cc87d449...`;
caller moved +0x20 (0x7a42884); rtcfast at 0x79ad470/0x7a42270/0x7a422b4;
error BRK at 0x7a42888. Image `entryprobe-el1-xnu-hybrid4-ufs-error-brk.img`,
SHA `bfa5505d...`, predicted `3b55186a...`. x0: 0x106 host reset,
0x107 link startup, 0x108 not-ready, 0 success.

**STAGE RESULT: x0=0x107 = link startup fails in XNU.** The UCRDY fix
(host reset now passes) leaves `DME_LINK_STARTUP` failing. The shim runs
the same sequence successfully at EL1 before XNU; the likely difference
is that the kernel's `smc #0` is trapped/no-op (XNU/EL2 or monitor
state), so the UFS device is never reset. Testing the same kernel with
the shim `--ufs-init` (device reset + link before the jump):
image `entryprobe-el1-xnu-hybrid4-ufs-preinit-error-brk.img`, SHA
`b9413b49...`, predicted `1421a6f4...`. If the driver's link startup
then succeeds, x0=5 (TUR/UA) or 0; if 0x107 again, the kernel's host
reset itself breaks the link.

**Pre-init stage test: x0=5 EIO.** With the shim `--ufs-init` (SMC64
device reset + link before XNU), the stage-code driver's host reset and
link startup now succeed; it reaches the TUR, which fails with EIO. This
proves the kernel's `smc` does not reset the device and the shim pre-init
is required. Instrumented `ufs_scsi` failure codes in 0086 (commit
`841ec85`): 0x2xx OCS, 0x300 bad UPIU, 0x4xx SCSI status, 0x5xx sense.
CI run for `841ec85` dispatched.

**Prepared: SCSI-code pre-init checkpoint.** Kernel
`xnu/out/ci-39963150738/kernel.development.sweet` SHA `a945461b...`;
caller 0x7a428a4 (+0x20), rtcfast 0x79ad490/0x7a42290/0x7a422d4, BRK
0x7a428a8. Image `entryprobe-el1-xnu-hybrid5-ufs-preinit-error-brk.img`
SHA `9325913d...`, predicted `5fcdbe95...`. x0: 0x2xx OCS, 0x300 UPIU,
0x4xx SCSI status (0x402 UA), 0x5xx sense.

**Shim device init (QUERY).** The kernel TUR returns response UPIU
`resp[6]=1` (target failure), consistent with fDeviceInit still set after
the SMC reset. `shim/ufs.c` now runs the Linux `ufshcd_device_init`
equivalent before the TUR: QUERY read flag fDeviceInit (0x0B); if set,
read the Configuration Descriptor (IDN 0x01), write it back, poll the flag;
then TUR. Stage is stored in `ufs_test_info[5]` (0x10/0x20/0x30/0x40/0x50
prefixes on failure). Image `entryprobe-el1-xnu-hybrid5-ufs-preinit-query.img`
SHA `22bff0bf...`, predicted `75feaf5d...`, same instrumented kernel.
Expected x0: 0x402 (UA reached), 0 (success), or 0x401 unchanged.

**Kernel-side device init.** The shim's query did not change the driver's
target failure (`x0=0x401`): the driver's own host reset runs after the
shim, so device init must happen inside 0086. Added `ufs_query` (UPIU
0x16: read flag 0x05, read/write descriptor 0x01/0x02, value at response
byte 24) and `ufs_device_init` (fDeviceInit 0x0B -> read/write config
descriptor 0x01 -> poll) after `ufs_take_over_host`, before the TUR.
Stage-coded failures: 0x8000 | (stage << 8) | query rc. Committed
`c7eed42`; CI dispatched.

**Prepared: kernel query-init checkpoint.** Kernel `ci-39965437795`
SHA `5ee4dd00...`; caller moved +0x480 to 0x7a42d04; rtcfast
0x79ad8f0/0x7a426f0/0x7a42734; BRK 0x7a42d08. Image
`entryprobe-el1-xnu-hybrid6-ufs-preinit-error-brk.img` SHA `01bd63da...`,
predicted `fb8460fc...`. x0: 0x8xxx = device-init stage failure
(0x810x flag read, 0x820x config read, 0x8300 bad descriptor, 0x840x
write, 0x8500 poll), 0x402 UA, 0x401 flag-clear-but-target-failure,
0 = TUR/GPT passed.

**DMA cache bug.** The kernel's UTRD/UCD live in cached `kmem_alloc_contig`
memory, but `su.cache` defaults to false (boot arg `ufscache=1`), so the
driver never cleans/invalidates them: the host can read stale command data
and the CPU can read stale responses. The earlier ENXIO/EIO/0x401/0x81fe
results are suspect until this is fixed. Image with `ufscache=1`:
`entryprobe-el1-xnu-hybrid6-cache-ufs-preinit-error-brk.img` SHA
`84b5771e...`, predicted `ee745558...`; same query-init kernel.

**Low-DMA test.** `ufscache=1` did not change x0 (0x81fe), so cache alone is
not it. The driver's DMA block now maps 0x40080000 (free window inside the
2 MiB probe prefix; code/BSS end <0x80000, stock image at 0x40200000;
block 0x40080000-0x40184000). Test-only: commit `9ee9d4b`; CI dispatched.
If the low-DMA TUR gets status 2 (UA) or 0, the >4 GiB UCD/UTRL address is
the failure; if unchanged, the UPIU/device state is.

**Local kernel builds work.** Without Xcode, the CI archive + buildtree are
enough: extract `kernel.development.sweet.a` (1098 objects), compile
`sweet_ufs.c` with the CI compile flags rewired to the local buildtree,
compile `xnu/libsa/nonlto.c`, stub the five `__firehose_*` symbols, and
link with `clang++` + `linkarguments` + `libclang_rt.cc_kext.a` (CLT).
`strip -S` gives a kernel whose `__TEXT_EXEC` base matches; only object
placement after `sweet_ufs.o` shifts (local `_sweet_ufs_rootdev`
0xfffffe00074e7090, caller `bl` 0x7a41c64, `cbnz` 0x7a41c68). No CTF.
Local test image `entryprobe-el1-xnu-local-ufs-lowdma-query.img` SHA
`f41d0b57...`, predicted `8f8ae8cf...`; kernel includes low DMA at
0x40080000 + kernel QUERY init, shim pre-init, BRK at 0x7a41c68.

**Low-DMA and local-link dead ends (2026-10-23).**
- Low DMA at 0x40080000 (`ml_io_map`) logo-reboots even with the CI-built
  kernel `7cbb139f` and `ufscache=1`; revert the low-DMA patch (done to
  `c7eed42`, high-DMA query + stage/SCSI codes). Do not retry this window.
- Local kernel builds link and strip, but even the control link with the
  original `sweet_ufs.o` logo-reboots. The buildtree archive lacks
  `libfirehose_kernel.a`, Xcode's `libcc_kext.a` and the CTF tools;
  substituting CLT `libclang_rt.cc_kext.a` + firehose stubs produces a
  non-bootable kernel. CI remains the only working kernel build path.
- Last good checkpoint: kernel `5ee4dd00` / run 39965437795 (query init,
  high DMA) returns x0=0x81fe: QUERY read flag fDeviceInit response UPIU
  byte 6 = 0xfe. Next: capture the full query response (all 32 bytes) and
  verify the query UPIU offsets/opcode against the device; the TUR then
  still returns target failure (0x401).

**Local link bootstrap (CI artifact `xnu-linklibs`).** `.github/workflows/
xnu.yml` now uploads `xnu-linklibs` (real `libfirehose_kernel.a`, Xcode 15
`libcc_kext.a`, ctf tools) next to `xnu-buildtree` and `xnu-kernel`.
Local relink recipe (no Xcode):
1. Extract `kernel.development.sweet.a` (1098 objects) and the
   `xnu-buildtree` (patched xnu + generated headers).
2. Compile `sweet_ufs.c` with the CI flags (from the run log) rewired to
   the extracted buildtree; cwd must be `build/xnu.obj/DEVELOPMENT_ARM64_SWEET/bsd/DEVELOPMENT`
   for `meta_features.h`/config headers. Compile `xnu/libsa/nonlto.c` the
   same way.
3. Link with the CI `linkarguments` (rewrite runner paths; output
   `kernel.*.unstripped`), the 1094-object filelist, `nonlto.o`,
   `version.o`/`lastkernel*.o`, the real `-lfirehose_kernel` and
   Xcode's `-lcc_kext` (from `xnu-linklibs`). The CLT substitutes
   (firehose stubs + `libclang_rt.cc_kext.a`) produced a kernel that
   logo-reboots even with the original object.
4. `strip -S`; local `__TEXT_EXEC` vmsize is not rounded to 0x4000 and
   VAs after `sweet_ufs.o` differ from CI; derive patch VAs from the
   local unstripped `nm`/disassembly.

**CI run 39974967885** (`d200e0e`, workflow adds `xnu-linklibs`) builds the
real `libfirehose_kernel.a` + Xcode 15 `libcc_kext.a`. The local control
kernel's segment table matches the CI kernel exactly (same vmaddrs/sizes
for every segment; only `__CTF` is absent locally), so the logo reboot is
not segment layout. Next: relink the control (archive `sweet_ufs.o`, real
libs, CLT `ld`) and boot it; if it reaches x0=0x81fe, local links work and
the remaining driver work can be done without CI.

**Real-lib local link matches CI.** With `libfirehose_kernel.a` from
`xnu-linklibs` and CLT `libclang_rt.cc_kext.a`, the control link (archive
`sweet_ufs.o`) places `_sweet_ufs_rootdev` at 0xfffffe00074e8090, exactly
the CI VA; `_IOFindBSDRoot` is 0x7a42654 and the call/cbnz at
0x7a42d04/0x7a42d08. The firehose stub's smaller code had shifted every
later object by -0x1000, so earlier local kernels were also misaligned.
Image `entryprobe-el1-xnu-local-ctrl-real.img` SHA `77feacc4...`,
predicted `67bba14b...`; expected x0=0x81fe if the local kernel boots.

**Real firehose + CLT cc_kext still logo-reboots.** The control link with
`libfirehose_kernel.a` (run 39974967885) and CLT `libclang_rt.cc_kext.a`
matches the CI VAs exactly but the kernel does not boot; the remaining
substitute is the compiler-rt library (Xcode `libcc_kext.a`) and possibly
the `ld`/`strip` version. Workflow run 39977655530 (`16812dc`) uploads
Xcode's `libcc_kext.a`, `libclang_rt.cc_kext.a`, `ld-xcode` and
`strip-xcode` in `xnu-linklibs`. Next: relink the control with the Xcode
cc_kext (same archive object) and boot it; if that works, compile the
driver locally and continue the query/UA work without CI.

**Local-link attempt closed (2026-10-23).** Relinking the control with the
real `libfirehose_kernel.a` (arm64) and Xcode 15's
`libclang_rt.cc_kext.a`, exact CI symbol layout
(`_sweet_ufs_rootdev` 0x74e8090), still logo-reboots; CLT `ld`/`strip` and
the absent CTF/dSYM remain. Do not spend more boots on local links until
Xcode 15's full toolchain (or its `ld`/`strip` + CTF chain) is available.
CI (`workflow_dispatch`) is the only reliable kernel build path.
`xnu-linklibs` now carries `libfirehose_kernel.a`,
`libclang_rt.cc_kext.a`, `ld-xcode`, `strip-xcode`, `ctfconvert`,
`ctfmerge` for that future attempt. `boot_a` is restored to
`2931647a...`.

**UFS state at stop.** The working checkpoint is the CI high-DMA query
kernel (`5ee4dd00`, later `527152b0`) with the shim `--ufs-init`: the
driver's host reset/link pass (the kernel `smc` still does not reset the
device; the shim does), then QUERY read-flag fDeviceInit fails with
response UPIU byte 6 = 0xfe (x0=0x81fe), and the TUR returns target
failure (0x401). No QUERY variant, low-DMA window, or local link has
worked. Next investigation is offline: capture the full query response
(type/opcode/idn/status/value) and compare the query UPIU layout with
JEDEC; consider dropping QUERY and handling the post-reset unit attention
with SCSI REQUEST SENSE/retry instead.

**ROOT CAUSE of the 0xfe query response (commit `0c37b5c`).** Linux
`ufshcd_compose_upiu` puts the query function in UPIU header byte 1:
0x01 standard read, 0x81 standard write. Our query left byte 1 zero, so
the device rejected every query (response UPIU byte 6 = 0xfe). Also:
- `QUERY_FLAG_IDN_FDEVICEINIT` is **0x01**, not 0x0B (0x0B is
  PERMANENTLY_DISABLE_FW_UPDATE).
- `struct utp_upiu_query` has `length` at bytes 18-19 and `value` at
  bytes 20-23; we read value at 24.
- Linux init is `SET_FLAG fDeviceInit` (query func 0x81, opcode 0x06)
  then poll `READ_FLAG` (0x05, IDN 0x01) until cleared, not a
  configuration-descriptor write.
Fixed in the kernel and the shim pre-init. CI dispatched for `0c37b5c`;
next test is the same error checkpoint with `--ufs-init`.

**Prepared: query-fix checkpoint.** Kernel `ci-39980826816` SHA
`61be134c...`; caller `0x7a42b44`, BRK `0x7a42b48`. Image
`entryprobe-el1-xnu-queryfix-ufs-preinit.img` SHA `8606be22...`,
predicted `989b55d7...`. x0: 0 rootdev success; 0x810x-0x830x device-init
failures (SET/READ/poll); 0x4xx TUR status; 0x2xx OCS.

**STOPPED 2026-10-24 at user request.** Device is in Recovery;
`boot_a` verified `2931647a56039722ea2585990b8ef3b1a2daf4c9b990231879f753049eaf86b1`.
No test image is flashed. User's uncommitted `shim/build.sh`/`shim/shim.c`
were not touched; the temporary shim variant was reverted.

Last state: query UPIU bugs fixed in `0c37b5c`/`0fb9293` (header byte 1 =
0x01 read / 0x81 write, fDeviceInit flag IDN 0x01, value at response byte
20, read-first + SET/poll). CI kernel `21ceb868` (run 39985645667) with
checkpoint `0983addf` still logo-reboots before the checkpoint, as did the
SET-first kernel `61be134c`. The hang is therefore in the new device-init
queries (shim pre-init and/or driver SET), not proven to be link/PHY.
Next (offline first): isolate with an `el1-load --ufs-init` image that
records the shim's `ufs_test_info[5]` and does NOT run device_init, then
add only READ_FLAG, then SET_FLAG. Do not resume device tests without a
concrete isolation plan.

**Next action.** Port the vendor `ufs_mtk_setup_clocks`/`setup_regulators`
and the power-domain state (or find how LK leaves the link); the shim's
`mtk_host_reset` + `refclk_on` + pre-link sequence is correct but not
sufficient. The kernel-side fixes already proven necessary: CT=0
(`UTP_CMD_TYPE_SCSI`), low-DMA UTRL/UCD, syscon reset sequence, XOUFS bit
0x80, HCE restart, pre-link MIB writes, refclk request. Do not patch the
kernel until the link starts in the shim; the XNU init path will fail the
same way.

No `userdata` write was made. Device is in Recovery, slot `_a`, `boot_a`
`2931647a...` (verified). Each `boot_a` write still needs explicit approval.

## >>> UFS device-init fixed; TUR GOOD (2026-10-24) <<<

Each hardware run below used explicit approval; `boot_a` was restored and
verified `2931647a56039722ea2585990b8ef3b1a2daf4c9b990231879f753049eaf86b1`
right after it.

- Power-mode probe `entryprobe-el1-ufs-query-power.img`, 26,570,752 B,
  SHA256 `88aeae48228f4fb56fb8405cd1493d456caac8dc9636910af37b331045b3e980`:
  banner `dtb=0 gicd=0103110000360000 vtimer=0302000000000011`: READ
  ATTRIBUTE IDN 0x02 succeeded and `bCurrentPowerMode` was already 0x11, so
  power mode is not the cause. First TUR still target failure
  (`fb=0000000121020004`).
- Fixed probe `entryprobe-el1-ufs-query-full.img`, 26,570,752 B, SHA256
  `04a23f165cd73db2586c2023b90384c3e4da7c3e745db2bbc443115edc6d5338`:
  banner `dtb=0` (SET+poll returned 0), `fb=0000000121020004` (first TUR
  still target failure), `spsr=0000700021000000` (REQUEST SENSE rc0,
  sense data 0x70), `x0=0000000021000000`: **second TUR GOOD**. Same-boot
  stock recovery dmesg in `research/matisse/20261023-ufs/ufs-query-{power,
  full}-dmesg.txt`.

**Root cause.** Linux `ufshcd_complete_dev_init` always SETs fDeviceInit=1
and then polls READ_FLAG until 0. `device_init` skipped the SET whenever the
first READ_FLAG returned 0, which is what a device that has not started or
completed its init reports after the shim's SMC reset; the SCSI target then
rejects every command (including REQUEST SENSE) with TARGET FAILURE
(response byte 6 = 1, status 2). With the unconditional SET_FLAG (opcode
0x06, IDN 0x01) plus poll, REQUEST SENSE succeeds and the next TUR is GOOD.

**Changes.** `shim/ufs.c` `device_init` (NONE/READ/SET/POWER/FULL; SET and
FULL always SET), `shim/entryprobe.c` (FB = first TUR, SPSR = sense
record), `tools/mkentryprobe.py` (`power` mode) and its tests. XNU patch
0086 `ufs_device_init` now always SETs too: its old read-first early return
had the same bug after the driver's own device reset. 48 unit tests,
`git diff --check` and `git apply --numstat` pass.

**Next.** Push and let CI build the 0086 kernel; package an XNU boot image
with `--ufs-init` and check `_sweet_ufs_rootdev` = 0 on hardware, then the
iOS root in `userdata`. Each `boot_a` write still needs explicit approval.

Device: Recovery, slot `_a`, `boot_a` `2931647a...` verified.

## Summary at pause (handoff for the next session)

**Proven on hardware.** XNU reaches BSD initialization, mounts md0, executes
`load_init_program`, and runs PID 1 in EL0. The open/write/select checkpoints
all hit; PID 1 opens `/dev/console`, writes the banner, and enters the 5 s
heartbeat loop. `serial=3` was routing the console to the UART; `serial=0`
restores the video console, and the serial0 loop test displayed the normal
scrolling boot text. The shim UFS code had three real bugs, now fixed: GPT
fields were read big-endian, writes lacked the UPIU W flag, and the timeout
used a fixed 19.2 MHz clock.

**Not proven / parked.** XNU UFS host takeover on matisse. Both the
production-style `rd=ufsroot0` image and the `_sweet_ufs_rootdev` BRK
checkpoint hung at the first logo with no ADB/fastboot; the BRK did not hit.
This is not proof that the UFS controller is broken: the hang may be earlier
(ADT/payload/`IOKitBSDInit`) or the checkpoint image may not have reached the
relay. `userdata` was not written. Production 0085 video-console output is also
not confirmed; the serial0 evidence came from the 0084 entryprobe build.

**Next session, in order.**
1. `boot_a` is already restored to `2931647a...`; re-verify it before any new
   test, and keep the same trim-prefix -> Recovery -> live-backup recovery path
   ready.
2. Bisect the UFS boot earlier: BRK at `IOKitBSDInit` entry and `bsd_init`
   entry using the UFS ADT; compare with the same payload using the old ADT and
   `rd=md0` to separate UFS from payload/ADT placement.
3. Run a shim-only read-only UFS probe (CAP/VER/HCS/HCE/UTRL/GPT) with a safe
   visible or persistent log; check CAP.64AS and DMA above 4 GiB before trusting
   the XNU takeover.
4. Only then retry `sweet_ufs.c`, read-only, and keep `ufsrw=0`; no `userdata`
   write until the read path is proven.
5. For display, flash the prepared 0085 serial0 loop image
   (`87199095...`) to confirm `sweet_display_refresh`; if still dark, trace
   `vcputc_options` -> DSI/TE.

**The logo and the BSD result are separate.** Diagnostic BRK records prove
`bsd_init` ran through `vfs_mountroot` (x0=0) and reached `load_init_program`;
mockfs/md0 was mounted. The panel showing LK's first logo says only that the
command-mode DSI path is not pushing new frames, not that the kernel stopped.
**PID 1 is alive and looping.** The EL0 open checkpoint hit, with
`stage=87 esr=0000000056000080 pc=0000000100000420 x0=00000001000004c0
x16=0000000000000005 spsr=0000000000000000`: an EL0t AArch64 `open` carrying
the `/dev/console` path pointer from `tools/sweet-init.S`. The write checkpoint
then hit with `pc=00000001000004a8 x0=0000000000000000
x16=0000000000000004 spsr=0`: `open` returned fd 0, the failure branch was not
taken, and the first console `write` was issued. The select checkpoint then
hit with `pc=0000000100000488 x0=0 x16=000000000000005d spsr=0`: the hello,
getpid and alive writes returned and init entered its 5 s heartbeat loop.
Evidence: `research/matisse/20261023-pid1/{open,write,select}-dmesg.txt`.
The correct test trigger was `adb reboot recovery`, not `adb reboot`; the
normal-mode run ended with `ro.boot.bootreason=Watchdog` and produced no
readable record.

**Console routing root cause found: `serial=3`.** XNU `arm_init.c` calls
`serial_init()`, then parses `serial=3` (SERIALMODE_OUTPUT|SERIALMODE_INPUT).
Because the UART enumerated successfully, it sets `serial_console_enabled` and
calls `switch_to_serial_console()`, setting `cons_ops_index` to
`SERIAL_CONS_OPS`. `get_cons_ops_index()` is a single-console selector, so
kernel `kprintf` and `/dev/console` writes go to the UART and never reach
`vcputc_options()`; patch 0085's `sweet_display_refresh(0)` is inside
`vcputc_options`, so it never runs. This is independent of the DSI gate.

Tested with `serial=0` (VC_CONS_OPS remains the default) and a diagnostic init
that BRKs after three heartbeat `select` returns:
`shim/out/entryprobe-el1-ramdisk-loop-serial0.img`, 26,566,656 B, SHA256
`ad7aea74942bdc2d9643458657b952ce534b5ac71127bb0e923cee4f1986ca3e`;
partition hash `41d6f1cf...` matched. The BRK hit with
`esr=00000000f2005357 pc=0000000100000498 spsr=0000000060000000` (EL0t), so
three heartbeats executed and the relay returned to Recovery in 46 s. Payload:
`shim/out/matisse-xnu-ramdisk-loop-serial0.payload`, 16,622,400 B, SHA256
`8e3cf39c8d0a3bdff43d1e67f1d0e610ce438485f8142e49fe21aec02ac01759`
(rtcfast kernel patches preserved, init replaced with the loop-BRK variant,
`serial=3` -> `serial=0`). Evidence: `loop-serial0-dmesg.txt`. **Panel
observation is the pending half of this test**: if the serial0 build drew
`*** SWEET userspace...` and heartbeats, `serial=3` is confirmed as the console
root cause; if not, the remaining gap is video console/DSI refresh.

Because the 0084 rtcfast kernel has no 0085 refresh hook, a matching 0085
serial0 loop image is also prepared (NOT flashed):
`shim/out/entryprobe-el1-ramdisk-0085-loop-serial0.img`, 26,566,656 B,
SHA256 `87199095ea18cf3b6ab05c92d8abb5c64284af4177debedcdb8131ffcae509d7`;
partition hash
`7b3a67b68de489829769b4da716be51143fb532b4fa3e19f5759e28894876189`.
Payload `shim/out/matisse-xnu-0085-ramdisk-loop-serial0.payload`, 16,622,352 B,
SHA256 `0bc90cad72f583e23e042aa44042d0c6e5f931e49b36da82c90c58d6a89da4c1`
(0085 kernel, loop init, `serial=0`). It keeps the original 30 s RTC/IOMedia
waits, so expect about 60 s before PID 1; the shim leaves the WDT off.

**Watchdog fact check (device evidence, correcting the `WDT_AUTO_RESET`
theory).** MediaTek does have a WDT here: the live DTB has
`watchdog@1c007000` compatible `mediatek,mt6983-wdt`, `/sys/class/watchdog/watchdog0`
exists, and Recovery dmesg says `mtk-wdt 1c007000.watchdog: Watchdog enabled
(timeout=31 sec, nowayout=0)`; the current boot command line carries
`aee_aed.pureason=Watchdog`. The WDT is real. However, current
`tools/mkentryprobe.py` does not define `WDT_AUTO_RESET` or `XNU_DIAG`
(confirmed by `llvm-nm`: no `shim_wdt_restore` in the diagnostic ELF), so the
shim leaves the WDT disabled in these probe builds. A probe that misses will
hang with no automatic Recovery return; recover with Power + Volume Down.


**UFS fixes and matisse probe (2026-10-23).** Three shim bugs from the roadmap
review are fixed (commit `b2dc0c2`): GPT entry LBA/count are now little-endian
with a 64-bit entry LBA and a 128-byte entry-size check; the Command UPIU sets
the W flag for host-to-device writes; the command timeout uses the real
`cntfrq_el0` instead of a fixed 19.2 MHz. The matisse ADT now exposes
`/sweet-ufs` at `0x112b0000/0x1000`, compatible `mediatek,mt8183-ufshci`
(commit `d242d41`), so `bsd/dev/sweet_ufs.c` can attempt the host takeover.

Recovery baseline (read-only): `ufshcd-mtk 112b0000.ufshci`, Samsung
KLUDG4UHGC-B0E1, three LUNs; LUN0 is `sdc`, 124,960,768 KiB; link is gear 4,
2 lanes, FAST MODE. The live FDT UFS base is `0x112b0000`.

UFS test artifacts (both flashed and both hung at the logo; keep for
inspection, do not re-flash without new evidence):

- `shim/out/shim-boot-0085-ufs.img`, 7,004,160 B, SHA256
  `d4f3746ce3cffe3f29f013da8b11224e49d09ce7b797a58aeef5c4804815c512`;
  payload 16,605,840 B SHA256
  `60f82519ca572b355c44986a81cd36f05cd7e70215fd9ecf2022a8294e02d77f`,
  ADT 4664 B SHA256 `1020d120...`, cmdline `rd=ufsroot0 ufsrw=0 serial=0`.
  Partition hash matched `1f41b3a7...`.
- `shim/out/entryprobe-el1-ufs-entry-brk.img`, 26,562,560 B, SHA256
  `46d5487ed1e675a8fd8d6ff2e3f6043ff2ca58f97e747a2d110132c519f03ee4`;
  payload `shim/out/matisse-xnu-0085-ufs-entry-brk.payload` SHA256
  `8632817047d1655a2194f5b877757ad9e256ccb859bec594e26137738583577f`.
  BRK at `_sweet_ufs_rootdev` VA `0xfffffe00074e8090` (entry offset `0x5bc08`,
  replaces `sub sp,sp,#0x120`); partition hash matched `c1a2687a...`.
  The BRK did not hit. A working checkpoint would relay to Recovery and print
  `pc=fffffe00074e8090`; no such record was produced.

**Display constants audit.** For matisse the active values are correct:
`shim/board.c` and `tools/mkadt.py` select `0xfcb3f000`, 1440x3200, stride
5760, and the live FDT overrides them. `0x9c000000` / 1080x2400 are only the
sweet/unknown-board fallbacks. Patch `0082` replaced the old early-console
`0x9c000000` writes from `0010`/`0012` with Boot_Video arguments populated by
`shim/loader.c`. Patches `0061`/`0046` still carry iPhone-X logical sizing for
later userland (`1125x2436`, dot pitch 458); that does not explain the
pre-userspace logo. No stale matisse framebuffer hardcode was found.

**EL0 syscall checkpoints (open/write/select PASS).** The new selective
vector also redirects slot 8 (AArch64 EL0 synchronous). It forwards ordinary
syscalls unchanged and aborts to the proven Recovery relay at the first EL0
SVC whose x16 matches `--el0-syscall`. This directly proves whether
`load_init_program` produced a running PID 1, and whether
`open("/dev/console")` returned, without a display or UART.

- **PASS:** `shim/out/entryprobe-el1-ramdisk-syscall-open.img`, 26,566,656 B,
  SHA256 `162320a626c3ddc0baf819bafa2ce72251aa580bbc1c232ea1a5efa5e315de30`;
  raw-write partition hash `3bdf4811b03bb461ad6f644808a55facfe70f38c3f7f2b095b51ebb0626991ac`
  matched the on-device readback. `--el0-syscall 5` hit:
  `esr=0000000056000080`, `pc=0000000100000420`,
  `x0=00000001000004c0` (path pointer), `x16=0000000000000005`,
  `spsr=0000000000000000`. The relay returned to Recovery in about 20 s.
- **PASS:** `shim/out/entryprobe-el1-ramdisk-syscall-write.img`, 26,566,656 B,
  SHA256 `23270c33bfedb861a2ffcb20fab639c80981d47d95dbb93aa29a282c4ea94f92`;
  raw-write partition hash
  `fa931660ff74fd3420754735095e23411e2de754eb578bd8d7040dc47d318a8c`
  matched the on-device readback. `--el0-syscall 4` hit:
  `esr=0000000056000080`, `pc=00000001000004a8`,
  `x0=0000000000000000` (fd returned by open), `x16=0000000000000004`,
  `spsr=0000000000000000`. This proves open returned and the first write was
  issued.
- **PASS:** `shim/out/entryprobe-el1-ramdisk-syscall-select.img`, 26,566,656 B,
  SHA256 `8233800cac3f98b15eaedbf2dac996657954b26d00536bfc2d578e428dc0fbd7`;
  raw-write partition hash
  `1185a03a7d0d1a9acee02e232499afbb98ecb48e52d39a53fe54c77274cf1930`
  matched the on-device readback. `--el0-syscall 93` hit:
  `esr=0000000056000080`, `pc=0000000100000488`, `x0=0`,
  `x16=000000000000005d`, `spsr=0`. The console writes returned and init
  entered the 5 s `select` heartbeat loop.
- All three PASS images embed payload `shim/out/matisse-xnu-ramdisk-rtcfast.payload`, 16,622,400 B,
  SHA256 `2ff27355d4c416516760243811ef6bec2bf71815dfbf18346060f36dd07d4a44`.
  It is the hardware-passed RAM-disk kernel with the RTC and IOMedia 30 s waits
  bypassed and the old `load_init_program` BRK removed (the only four words
  differing from `matisse-xnu-ramdisk-init.payload` are the two waits, the
  timeout branch and that BRK).
- Build validation: banner record 384 B (cap 406), slot 8 original `b` kept,
  stub 100 B (<128), embedded payload hash matched, key words checked
  (`0x77ee118: d104c3ff`, `0x79ad070: d503201f`, `0x7a41e70: aa1f03e0`,
  `0x7a41eb4: 14000007`, slot 8 `140003b3`). All 44 tools tests pass.
- Next frontier is display, not PID 1. `serial=3` was routing all console output
  to the UART; the serial0 loop build proved three heartbeats (BRK record)
  after removing it. If the panel showed the text, make `serial=0` the
  production cmdline; if it stayed at the logo, trace `vcputc_options` ->
  `sweet_display_refresh` and the DSI/TE push. Trigger probes with
  `adb reboot recovery`; restore `boot_a` from the live backup after every
  test.

## >>> ACTIVE 2026-10-23 (Asia/Shanghai): BSD mounts md0; display refresh fix prepared <<<

**Current device (verified): Recovery, boot_a fully restored.** The latest
full 67,108,864-byte readback (`thread-brk-v2-restored.img`) matches original SHA256
`2931647a56039722ea2585990b8ef3b1a2daf4c9b990231879f753049eaf86b1`.
Online hardware is **matisse / Redmi K50 Pro / MT6983**, not README's
sweet / Qualcomm target. XNU's original initialization through formal page-table
construction and the first switch to those tables inside arm_vm_init are
hardware-proven, as are TTBR0 teardown, TLB invalidation and early console
mark 10 using the relocated framebuffer, and the complete arm_vm_init return.
Serial_init also returned success (x0=1) on hardware, followed by startup
phase 4, console/printf setup, idle init and PE_init_platform(TRUE). CPU/timer/
GIC setup and early_random also passed up to the machine_startup call.
machine_startup and kernel_bootstrap have now reached vm_mem_bootstrap;
vm_page_bootstrap, zone_bootstrap, vm_object_bootstrap, vm_map_init,
kmem_init (with the KMEM and ZALLOC startup phases, including zone_init) and
vm_fault_init have all returned on hardware: the **complete
vm_mem_bootstrap returned** to kernel_bootstrap. `sched_init`, task/thread
init and `load_context` then ran, and the **bootstrap thread executed on
hardware** (`kernel_bootstrap_thread` after `current_processor`).
`idle_thread_create`, `sched_startup` (first real `thread_block` round trip)
and `thread_daemon_init` have also returned on hardware. The kernel then
reached `spllo()` with interrupts enabled and returned from
`initialize_screen`. Selective diagnostic vectors are hardware-proven, and a
500 ms CNTVCT busy-wait with interrupts enabled advanced `sched_tick` by 3:
timer-interrupt delivery and scheduler maintenance are proven. A direct jump
to the `bl bsd_init` call failed into an infinite reboot loop; `boot_a` was
fully restored. The post-lockdown checkpoint then passed; the XNUPOST-skip
diagnostic still looped, and a payload test confirmed the post-lockdown hang
is `kperf_init_early()` -> `ml_wait_max_cpus()`. Returning 1 from that barrier
on the single-CPU topology let kperf, the full CONFIG_XNUPOST suite and
`PE_lockdown_iokit` pass; execution reached the `bl bsd_init` site. The
permanent CI kernel with that fix was then hardware-validated end-to-end and
reached the `bl bsd_init` site with XNUPOST and kperf untouched. Later RAM-disk
diagnostics executed `bsd_init`: `vfs_mountroot` returned success (`x0=0`),
`bsd_utaskbootstrap` ran, and execution reached `load_init_program`. Thus BSD
initialization and mounting the mockfs/md0 root are proven on hardware.
Successful PID 1 execution and full kernel boot remain unproven; the
production screen stayed dark. The display path has now been traced to two
gaps: `sweet_display_init()` treated transient DSI `TE_RDY` as a hard
readiness gate, and the command-mode refresh hook covered `pe_serial.c` but
not XNU's graphical `video_console.c`. New patch
`xnu/patches/0085-matisse-video-console-refresh.patch` removes that gate and
refreshes after graphical console output. It applies to the CI XNU source and
both affected files pass local ARM64 Mach-O object compilation (0 failures)
using the recorded DEVELOPMENT/SWEET flags. All 44 tools tests pass. CI and
hardware validation are still pending; the screen fix is not yet proven.
Device state is last verified as
Recovery with the full original `boot_a` restored and hash
`2931647a56039722ea2585990b8ef3b1a2daf4c9b990231879f753049eaf86b1`.

**Completed: `sched_startup` return (hardware PASS).**
`shim/out/entryprobe-el1-sched-startup-brk.img`, 26,562,560 B, SHA256
`c1859ef9626ff2a66689c0b63d25aa10e23645e987db1c851435a43f0c5bf5b9`;
payload SHA256 `196c4de70325c597e6c80089dcc45048eb30a72f6f0488f27e34f33b4ed14a72`.
Same dual-slot selective vectors, 128 MiB cleanup range
`[0x100000000, 0x108000000)`, bootstrap TTBR0 restore `0x10117c000`, debug
payload base `b6eafe9a...` and stock template `7a6a462d...` as the
hardware-passed thread image. BRK at entry offset `0x62334c`, payload offset
`0xaabbc4`, VA `0xfffffe0007aaf7d4` / PA `0x101aaf7d4`, immediately after
`bl sched_startup`; it replaces `ldrb w8,[x21,#0x20c]` (`0x394832a8`).

Same-boot `sched-startup-dmesg.txt` records
`stage=87 fault=1 esr=f2005357 far=0 pc=fffffe0007aaf7d4`, x0 `1`. Thus
`idle_thread_create` and `sched_startup` returned on hardware, including the
first real `thread_block` round trip (`sched_init_thread` blocks, bootstrap
resumes). The ESR is the inserted BRK. The device returned to Recovery about
30 s after `adb reboot recovery`. The predicted written-partition SHA256
`259d0ae9...` matched the full 67,108,864-byte readback, and the complete
original was written back and verified as `2931647a...`. Evidence:
sched-startup-dmesg.txt, before/written/restored images and prepared-build.txt
in `research/matisse/20261023-sched-startup/`.

**Completed: `thread_daemon_init` return (hardware PASS).**
`shim/out/entryprobe-el1-thread-daemon-brk.img`, 26,562,560 B, SHA256
`f16c296dd10705f0434c29c0cc0e6460411730d1be1a0899a88809c9aea4f4e8`;
payload SHA256 `d41aec2a63d98734a89d1a5935de37e568f0d3b5cd6a6b18d363199f432f30f7`.
BRK at entry offset `0x623384`, payload offset `0xaabbfc`, VA
`0xfffffe0007aaf80c` / PA `0x101aaf80c`, after `bl thread_daemon_init`;
replaces `mov w0,#0xe` (`0x528001c0`) immediately before
`kernel_startup_initialize_upto(STARTUP_SUB_THREAD_CALL)`. Same selective,
cleanup and TTBR0 setup as the passed images.

Same-boot `thread-daemon-dmesg.txt` records
`stage=87 fault=1 esr=f2005357 far=0 pc=fffffe0007aaf80c`, x0 `0`. Thus
`thread_daemon_init` returned as well: `idle_thread_create`, `sched_startup`
and `thread_daemon_init` have all completed on hardware. The device returned
to Recovery about 30 s after `adb reboot recovery`; predicted written-partition
SHA256 `a20d347f...` matched the full readback, and the complete original was
written back and verified as `2931647a...`. Evidence: thread-daemon-dmesg.txt,
written/restored images and prepared-build.txt.

The build recipe is proven: rebuilding the hardware-passed thread image from
the same template/payload/offsets (`--xnu-vector-offset 0xb78`,
`--xnu-high-vector-offset=-0x4488`, `--xnu-clean --xnu-clean-limit
0x108000000`, `--xnu-restore-ttbr0 0x10117c000`, `--xnu-selective`, NDK
28.2.13676358) reproduced SHA256 `154449c1...` byte-for-byte. Each new payload
differs from the base by exactly one BRK word. All 37 tools tests pass. The
stale `entryprobe-el1-sched-init-brk.img` / payload `e7c026b4...` remains
slot-4-only and must not be used.

Device state after this test (observed): root ADB in Recovery, slot `_a`,
`boot_a` fully restored to SHA256
`2931647a56039722ea2585990b8ef3b1a2daf4c9b990231879f753049eaf86b1`. Each
further `boot_a` write needs separate approval. After the BRK record, write
back the full original and verify the hash; on failure, restore the trimmed
stock prefix via fastboot, boot Recovery, then write the full backup. Never
leave a test image in `boot_a`.

**Docs:** `docs/matisse-xnu-ios-roadmap-zh.md` updated on 2026-10-23 with the scheduler, timer-IRQ, lockdown, kperf and `bsd_init` results.

**ACTIVE: production RAM-disk boot reaches load_init but console is dark
(2026-10-23).** Production images `fa6607a8...` (original waits) and
`236b9828...` (RTC/IOMedia waits bypassed) were flashed; both stayed static
with a black/logo screen and no Recovery, so the AP watchdog remained off and
the kernel did not reset. A third production image `996197e5...` also NOPed the
`bl sweet_display_init` in `serial_init` (`0xfffffe0007a7c73c`); the screen
stayed dark. Diagnostic BRK evidence proves `bsd_init` executed through
`vfs_mountroot` (x0=0) and `load_init_program` entry. `mountroot` success means
mockfs/md0 is mounted. What remains unproven is PID 1 execution/console: the
framebuffer console shows nothing, and the init's first action
`open("/dev/console")` may block or the console may be headless. Next evidence
path should be the XNU msgbuf/serial, not more blind framebuffer boots.
Final state after this run: `boot_a` was restored from the full 64 MiB backup and verified as `2931647a56039722ea2585990b8ef3b1a2daf4c9b990231879f753049eaf86b1`; device is in Recovery, slot `_a`. No `userdata` write.

**ACTIVE: diagnostic watchdog artifact found (2026-10-23).**
`mkentryprobe.py` compiles the shim with `WDT_AUTO_RESET`, which re-arms the
MT6983 31 s AP watchdog so a hung XNU resets. Every "infinite reboot" after a
BRK checkpoint or no-BRK diagnostic image is therefore partly an artifact. The
production `shim/build.sh` path calls `wdt_disable_raw()` at shim entry and
leaves the watchdog off. Built production image `shim/out/shim-boot.img`
(7,008,256 B, SHA256 `fa6607a8ee617fa3da8e816180e43f8ac867465d986556face0ba56533b3686c`)
from the original RAM-disk payload and flashed it; predicted partition
`e08af82b...` matched. This boot, not the diagnostic images, is the real test
of the 30 s RTC + 30 s IOMedia waits and the minimal init.

**ACTIVE: bsd_init bisection found two 30 s waits (2026-10-23).**
Checkpoints after `kauth_init`, `kmem_suballoc`, `bsd_bufferinit`, and
(once the waits were patched) `vfsinit`, `IOKitBSDInit`, `vfs_mountroot`
(x0=0), `bsd_utaskbootstrap`, and `load_init_program` all returned. The two
blockers were `IOKitInitializeTime` waiting 30 s for an RTC service at
`0xfffffe00079ad070`, and `IOFindBSDRoot` waiting 30 s for IOMedia at
`0xfffffe0007a41e70` before `mdevadd` creates md0. The hardware watchdog
resets at ~30 s, so both waits look like a boot loop. Diagnostic payloads skip
both (`nop waitForService`, `mov x0,xzr` + `b` over the timeout sleep) and
reach `load_init_program` (`pc=fffffe00077ee118`). A checkpoint at the first
`load_init_program_at_path` return (`0x77ee214`) did not hit, so exec likely
succeeded; `tools/sweet-init.S` then hangs forever if `open("/dev/console")`
fails, which also triggers the watchdog. Built `research/sweet-init-diag`
(SHA256 `2917403c...`) that falls back to fd 1 and never spins, payload
`shim/out/matisse-xnu-0084-diaginit-rtcfast.payload` (`fdef6e15...`) and image
`entryprobe-el1-diaginit-rtcfast.img` (`4f0376b3...`), not yet booted.

**ACTIVE: RAM-disk bsd_init diagnostics (2026-10-23).** Built
`research/sweet-init` (16,635 B, SHA256 `f5de3714...`), payload
`shim/out/matisse-xnu-0084-ramdisk.payload` (SHA256 `4df6b274...`, ADT
`RAMDisk=<0x1024d0000,0x8000>`, cmdline `rd=md0`), and a no-BRK image
`entryprobe-el1-ramdisk.img` (`b337bfbf...`). Hardware: no-BRK boot loops with
`aee_aed.pureason=Watchdog`, so `bsd_init` hangs, not panics. `bsd_init` entry
checkpoint `entryprobe-el1-bsd-entry-ramdisk-brk.img` (`e6d4bf7e...`) returned
`pc=fffffe000776e048 x0=0`, proving the RAM-disk payload enters `bsd_init`.
Checkpoints at `bsd_utaskbootstrap` entry (`679fa200...`), `IOFindBSDRoot`
return (`0f1be906...`), and a no-wait variant (`060d436c...`) all looped.
Disassembly: `IOFindBSDRoot` calls `IOService::waitForMatchingService` with a
30 s timeout before `mdevadd` (which prints "Added memory device md0"); the
watchdog resets around the same time. Next diagnostic:
`entryprobe-el1-fastroot-ramdisk-brk.img` (`7ee792f1...`) patches the wait to
return 0 and replaces the timeout `cbz` with `b 0x...1ed0`, then BRKs after
`IOFindBSDRoot`; expected to reach `mdevadd`/return x0. Device is currently in
the no-wait loop; waiting for manual fastboot to restore full `boot_a`.

**Next:** execute `bsd_init` itself with a RAM-disk root (prepared, NOT
flashed). Host-only build on 2026-10-23 reused CI kernel 39828405447
(`28190f5b...`, patch 0084), `shim/out/matisse.adt` and the static init
`research/sweet-init` (rebuilt from `tools/sweet-init.S` with NDK clang +
`tools/mkinit.py`, byte-identical SHA256
`f5de3714ff95e6a3b9ece30723f677de0f3f74ec5eb985a00c5ae872f0ac9bf1`).

- `shim/out/matisse-xnu-ramdisk-init.payload`, 16,622,400 B, SHA256
  `4df6b274603e3897e9699bb7bc11791556f1067868e772a0fdf1592d5354f9b9`.
  Cmdline: `debug=0xc serial=3 cpus=1 keepsyms=1 -enable_kprintf_spam rd=md0
  sweetkeys=0 sweettouch=0 sweetbattery=0 sweetusb=0 ufsrw=0 -noprogress`
  (135 B, `rd=md0` preserved by `platform_cmdline`).
- RAM disk segment VA `0xfffffe00084d0000`, 32 KiB, PA `0x1024d0000`;
  ADT `/chosen/memory-map/RAMDisk = <0x1024d0000, 0x8000>`. ADT is copied at
  PA `0x1024d8000` (4508 B), boot_args at `0x1024dc000`, topOfKernelData
  `0x1024e0000`; all inside the proven 128 MiB cleanup range
  `[0x100000000, 0x108000000)`.
- `shim/out/entryprobe-el1-ramdisk-init.img`, 26,562,560 B, SHA256
  `b337bfbf86bbe62c769bf6521df0331f65e7cf7d0c4d9973d83b0ae0cafcbe75`
  (no BRK; selective dual-slot vectors, stock-template SHA `7a6a462d...`).
  Expected panel output: `BSD root: md0`, `hfs: mounted SweetRoot...` is not
  used here (mockfs), `load_init_program: attempting to load /sbin/launchd`,
  then `*** SWEET userspace: init running as PID 1 ***` and a
  `SWEET init: still alive` line every 5 s.
- Checkpoints (same payload plus one `BRK #0x5357`):
  `entryprobe-el1-ramdisk-bsdinit-return-brk.img` SHA256
  `9a8c43dbe6b2c13bf9ad2136c21320bc7bf23df878759b63bd4b7d57d40c1821`,
  BRK at VA `0xfffffe0007aafc04` (immediately after `bl bsd_init` returns);
  `entryprobe-el1-ramdisk-load-init-brk.img` SHA256
  `b4af6752d90b82a46b814de428f92e1eeabc39073f15dfdf1a44c6bcc68928e8`,
  BRK at `_load_init_program` VA `0xfffffe00077ee118`.
- Validation: re-parsed both compressed boot Images, matched the embedded
  `SWEETAPP` payload SHA, the init bytes and `MH_MAGIC_64`, the ADT RAMDisk
  pair, the cmdline length, and that only the checkpoint payloads contain the
  BRK word. All 44 tools tests pass.
- Device baseline read-only check this turn: Recovery, root ADB, slot `_a`,
  `boot_a` SHA256 `2931647a...` matches the full backup. No flash was
  performed. Each `boot_a` write still requires explicit approval.

Next action: flash the no-BRK image, boot it, and photograph/observe the
panel. If it does not reach PID 1, use the `bsdinit-return` checkpoint next;
if that passes but userland does not, use the `load-init` checkpoint.

**Failed: XNUPOST-skip diagnostic (hardware, infinite reboot).**
`shim/out/entryprobe-el1-bsd-init-skiptest-brk.img`, 26,562,560 B, SHA256
`ce02efbf38a55aac1186e7b653e53505836cc4a4e29d0271fec1456c5283021a`;
payload SHA256 `29beb4b8bfd0508764101d9b5b4628a3ae6c33bfb34912edf9dfa7477969e10e`.
It NOPed `kernel_list_tests`, `kernel_do_post` and the `cbnz w0` panic
branch, then inserted BRK at `bl bsd_init`. The written partition matched the
predicted SHA256 `13524b46...`. The device still entered an infinite reboot
loop; no SWEET-ENTRY. Recovery used the same manual-fastboot → trimmed-prefix
→ full-backup path; `boot_a` verified `2931647a...`. CONFIG_XNUPOST is
therefore not the blocker.

**Completed: NOP-kperf checkpoint (hardware PASS; kperf confirmed).**
`shim/out/entryprobe-el1-bsd-init-nokperf-brk.img`, 26,562,560 B, SHA256
`14bef24d4f369ea13bbcb854eeedb1c7ba540cd3601250a6c8e6bac4fe183cf1`;
payload SHA256 `b2ae537f5e791b6441c780708a2598d2165b588d3d240188a9847c3cabc0c4f6`
(`research/.../nokperf-build.py`). It NOPs both XNUPOST calls and the panic
branch, NOPs `bl kperf_init_early` (`0x7aafbdc`), and breaks at the
`bl bsd_init` site (`0x7aafbe0`).

Same-boot `nokperf-dmesg.txt` records
`stage=87 fault=1 esr=f2005357 far=0 pc=fffffe0007aafbe0`, x0 `0`. With
kperf skipped, execution reached `bl bsd_init`; `PE_lockdown_iokit` and
`vm_set_restrictions` returned. Written-partition SHA256 `c4921d05...`
matched the readback; the full original was restored and verified as
`2931647a...`.

Root cause (source): kperf calls `ml_wait_max_cpus()`, which blocks until
`ml_set_max_cpus()` sets `max_cpus_initialized = MAX_CPUS_SET`. On matisse the
ADT CPU node is `arm,cortex-a510` + `ARM,v8`, while the SweetCPU personality
matches only `qcom,kryo470`; the CPU driver never instantiates, so the setter
is never called and the barrier sleeps forever. `machine_info.max_cpus` is 1
because the matisse ADT has a single CPU node.

**Completed: payload max_cpus fix (hardware PASS; pre-bsd path cleared).**
`shim/out/entryprobe-el1-bsd-init-maxcpu-fix.img`, 26,562,560 B, SHA256
`8783158b9d5ba83e5154b6817da60175020778d7743a14f1f85837d2ff066ee2`;
payload SHA256 `6d45243bc5fd475ff434df217b7516eee33a4a0f8b6596655d61d4cae6956f1a`.
It replaced the first two instructions of `ml_wait_max_cpus()` (VA
`0xfffffe000748fe28`) with `mov w0,#1; ret`, kept CONFIG_XNUPOST and kperf
enabled, and broke at `bl bsd_init` (`0x7aafbe0`). Only 12 payload bytes
differed from the debug payload.

Same-boot `maxcpu-dmesg.txt` records
`stage=87 fault=1 esr=f2005357 far=0 pc=fffffe0007aafbe0`, x0 `0`. The
single-CPU `ml_wait_max_cpus` return let `kperf_init_early()` and the full
CONFIG_XNUPOST suite pass; `PE_lockdown_iokit` and `vm_set_restrictions` also
returned. Written-partition SHA256 `ad487813...` matched the readback; the
full original was restored and verified as `2931647a...`.

Permanent source fix: `xnu/patches/0084-sweet-single-cpu-max-cpus.patch`
makes `ml_wait_max_cpus()` in `osfmk/arm/machine_routines_common.c` return
immediately when `machine_info.max_cpus <= 1`; the sole CPU is already
executing and the IOKit CPU driver may never publish the flag (SweetCPU
matches `qcom,kryo470`, matisse uses `arm,cortex-a510`). Local single-file
compile with `tools/xnu-cc.py` passes (0 of 1 failed on the ci-39158169212
tree). Committed as `b616374`, pushed to `Jinsens/ios-sweet`, and built by CI
run `39828405447` (the first dispatch on `main`, run `39826038020`, was
cancelled before any step; the retry on `codex/matisse-xnu-screen-log`
succeeded). New kernel
`xnu/out/ci-39828405447/kernel.development.sweet` SHA256
`28190f5b4c274b4d5c1501f08b776873c5a9190ec67b74021bd4f42b795267f2`;
payload `shim/out/matisse-xnu-ci39828405447.payload` SHA256
`e39237a808568658c363b8d10fbac9916b4093c2f8b0992cebfbc870c13f887c`.

**Completed: permanent-fix validation (hardware PASS).**
`shim/out/entryprobe-el1-bsd-init-0084-brk.img`, 26,562,560 B, SHA256
`1cd72d232491a871296d611720a8ac55774f4c743a286131841b2dff1da93599`;
payload SHA256 `d634f707bc0aecccd438fa312d0f69254706a7cb2b04ddba6ac886183835b425`.
The new kernel's `_kernel_bootstrap_thread` is at `0xfffffe0007aaf754`; the
BRK is at VA `0xfffffe0007aafc00` / PA `0x101aafc00` (entry offset
`0x623778`), replacing `bl bsd_init` (`0x97f2f912`). XNUPOST and kperf were
untouched. Same vector/cleanup/TTBR0 parameters as before: the early and high
vector tables and `bootstrap_pagetables` did not move.

Same-boot `ci0084-dmesg.txt` records
`stage=87 fault=1 esr=f2005357 far=0 pc=fffffe0007aafc00`, x0 `0`.
Predicted written-partition SHA256 `65c410be...` matched the full readback;
the complete original was restored and verified as `2931647a...`. Patch 0084
is hardware-validated end-to-end: the real CONFIG_XNUPOST suite and
`kperf_init_early()` returned and execution reached `bl bsd_init`. 44 tools
tests pass.

**Completed: first post-`spllo` checkpoint (hardware PASS).**
`shim/out/entryprobe-el1-spllo-brk.img`, 26,562,560 B, SHA256
`ff8e21bfdd891cb86ccf6de2ec85fb82ab148e8877e598e74b8728059b80b02a`;
payload SHA256 `c9622ac8894e638f1f269189a7ddee8adf30cf83f9d5619116110de1bb2ecc55`.
BRK at entry offset `0x623564`, payload offset `0xaabddc`, VA
`0xfffffe0007aaf9ec` / PA `0x101aaf9ec`, immediately after
`bl initialize_screen`, i.e. after `spllo()` enabled interrupts and
`initialize_screen(NULL, kPEAcquireScreen)` returned; it replaced
`bl vm_commpage_init` (`0x97e63a74`). Same dual-slot selective vectors,
128 MiB cleanup range and TTBR0 restore as the passed images.

Same-boot `spllo-dmesg.txt` records
`stage=87 fault=1 esr=f2005357 far=0 pc=fffffe0007aaf9ec`, x0
`fffffe0007c57408`. Thus `kernel_startup_initialize_upto` through
`STARTUP_SUB_EARLY_BOOT` (16), `PE_init_iokit`, `spllo()` and
`initialize_screen` returned with interrupts enabled. The device returned to
Recovery about 30 s after `adb reboot recovery`; predicted written-partition
SHA256 `8ac9faaa...` matched the full readback, and the complete original was
written back and verified as `2931647a...`.

That checkpoint alone did not prove a timer IRQ was delivered (the scheduler
tick interval is 125 ms and the code between `spllo()` and it may be shorter).
The dedicated probe below did.

**Completed: timer-tick proof (hardware PASS).**
`shim/out/entryprobe-el1-tick-brk.img`, 26,562,560 B, SHA256
`80c8f80fc924c94900c11f3c37b35a2a116dd728d81c21e1b80075c22a731a64`;
payload SHA256 `a9dcaf248023333832276bffab285cacb5fc8f7ca43789ed3647b332ba9ca9fb`.
Instead of a plain BRK after `initialize_screen`, the checkpoint instruction
at VA `0xfffffe0007aaf9ec` branches to a cave at VA `0xfffffe000748d714`
(early-vector slot 14 plus 20 bytes; `diag_arm_sentinels()` rewrites only the
first five words of each early slot). The cave calls `vm_commpage_init`,
reads `sched_tick` (VA `0xfffffe0007b94698`), busy-waits 6,500,000
`CNTVCT_EL0` ticks (500 ms at the measured 13 MHz) with interrupts left
enabled, re-reads `sched_tick`, subtracts, and executes BRK #0x5357.

Same-boot `tick-dmesg.txt` records
`stage=87 fault=1 esr=f2005357 far=0 pc=fffffe000748d744`, x0 `3`. The
`sched_tick` delta of 3 over 500 ms proves timer interrupts were delivered,
XNU's normal IRQ path ran, and the scheduler maintenance continuation ran
three times. The wait uses CNTVCT directly, so a broken interrupt path would
still have returned with x0 0. Predicted written-partition SHA256
`2f895215...` matched the full readback; the complete original was written
back and verified as `2931647a...`. Tool `tools/xnu_tickprobe.py`; 44 tools
tests pass. The image uses the same dual-slot selective vectors, 128 MiB
cleanup range and TTBR0 restore.

**Failed: `bsd_init`-entry big jump (hardware, infinite reboot).**
`shim/out/entryprobe-el1-bsd-init-brk.img`, 26,562,560 B, SHA256
`7a5b60b59c21fa4d69b4b0f1f6a13e0ea230c7e10ec2eecb8f94bd9136badee0`,
payload `cc0ec308...`, BRK at entry offset `0x623758` / VA
`0xfffffe0007aafbe0` / PA `0x101aafbe0`, replacing the `bl bsd_init`
(`0x97f2f912`) at the end of `kernel_bootstrap_thread`. The written partition
readback matched the predicted SHA256 `b07b8a78...`. The device did **not**
return; it entered an infinite reboot loop and no SWEET-ENTRY record was
captured. Do not reuse this image.

Recovery (completed): user entered fastboot manually;
`fastboot flash boot_a backup/boot_a-stock-trim.img` (20,873,216 B, SHA256
`fe6e8fbf...`) returned Sending/Writing OKAY. `fastboot reboot recovery`
reported a USB status failure, but Recovery came up in 27 s. The complete
67,108,864-byte original was then written and read back as
`2931647a56039722ea2585990b8ef3b1a2daf4c9b990231879f753049eaf86b1`.

The cause was narrowed by the next test: the post-lockdown checkpoint
passed, so lockdown and the diagnostic relay are not the failure. The
remaining candidates are the CONFIG_XNUPOST tests (`kernel_list_tests` /
`kernel_do_post`), `PE_lockdown_iokit`, `vm_set_restrictions`,
`kperf_init_early`, or the final return from the `bl bsd_init` site.

**Completed: post-lockdown checkpoint (hardware PASS).**
`shim/out/entryprobe-el1-lockdown-brk.img`, 26,562,560 B, SHA256
`f68a28a8f3c6c564e0b89ea540ef59828175ab20f311996a80a4c51c5e6b074a`;
payload SHA256 `c5b99715dc5886e327d2d1ef9cefa3d8db2550c901b4ce3949a5b66c0014a93e`.
BRK at entry offset `0x6236cc`, payload offset `0xaabf44`, VA
`0xfffffe0007aafb54` / PA `0x101aafb54`, immediately after
`bl machine_lockdown`, before `bl kernel_list_tests`; it replaced
`bl kernel_list_tests` (`0x97e41107`).

Same-boot `lockdown-dmesg.txt` records
`stage=87 fault=1 esr=f2005357 far=0 pc=fffffe0007aafb54`, x0
`fffffe00072e0000`. `OSKextRemoveKextBootstrap` and `machine_lockdown`
returned, and the selective vector relay, 128 MiB cache cleanup and bootstrap
TTBR0 restore still work after the ROX lockdown. Written-partition SHA256
`d0537227...` matched the readback; the full original was restored and
verified as `2931647a...`.

Memory review: `bootstrap_pagetables` (VA `0xfffffe000717c000`, PA
`0x10117c000`, the TTBR0 restore page) is in `__DATA_CONST`;
`arm_vm_prot_finalize()` frees `__BOOTDATA` at VA `0xfffffe0008080000`
(PA `0x102080000`), not this page. The vector stubs are in `__TEXT_EXEC`
and stay executable after the ROX lockdown. This is now hardware-proven.

**Completed: bootstrap-thread checkpoint (hardware PASS).**
`shim/out/entryprobe-el1-thread-brk.img`, rebuilt with dual-slot selective
vectors, 26,562,560 B, SHA256
`154449c1e72284e4111a353c969549d7a810c9a7906cafe6b2160191a39be872`.
Payload SHA256 `3b44b2bf052a865074a19b51ad0b447e0f5552f2b5cda370233fc2ef75d08d06`.
BRK offset `0x6232c4` at VA `0xfffffe0007aaf74c` / PA `0x101aaf74c`, after
`current_processor` returns inside `kernel_bootstrap_thread`. Cleanup range
stayed `[0x100000000, 0x108000000)` (128 MiB).

Same-boot `thread-brk-v2-dmesg.txt` records
`stage=87 fault=1 esr=f2005357 far=0 pc=fffffe0007aaf74c`, with
x0 `fffffe0007b88180`. Kernel thread creation, `load_context` and the
bootstrap thread's first C call therefore ran on hardware. The ESR is the
inserted BRK. Automatic Recovery return and the complete original
67,108,864-byte boot_a restoration/readback SHA256 `2931647a...` were
verified; the written partition matched the predicted `c57c8252...` hash.
Per user direction this image was tested directly, without host emulation;
evidence is the BRK record plus the full restoration check.

**Completed: selective diagnostic vectors (hardware PASS; EL1t root cause).**
- XNU executes with SPSel=0 (EL1t), so a BRK from kernel C code takes vector
  slot 0, not slot 4. The first selective image patched only slot 4; the BRK
  reached XNU's original EL1t handler instead, which reset the device. The
  bootstrap-thread checkpoint itself was never implicated.
- Fix: the stub is installed in **both** synchronous slots 0 and 4; each
  copy has its forward B and its relay B patched at install time. The stub
  saves/restores x16/x17 and preserves every GPR on the forward path.
  IRQ/FIQ/SError and EL0 synchronous slots stay original; the diagnostic
  relay lives in unused AArch32 slots 12/13.
- Hardware PASS on the known-good vm-return checkpoint:
  `shim/out/entryprobe-el1-vm-return-sel.img`, SHA256
  `81652ccf2912acb70630fe781985386eedce35c12cf90ad13f9f7d8fb50ceced`,
  partition `281a4a26...`. `sel-vm-return-v2-dmesg.txt` records
  `stage=87 fault=1 esr=f2005357 pc=fffffe00073644d8`, x0
  `fffffe00080bbbc0`; automatic return and full restore verified.
- 23 tool tests and `selective-stub-microtest.txt` pass. Commits `5f3ba55`
  (initial) and `42d6582` (dual-slot fix).

**Historical (superseded): first bootstrap-thread attempt with slot-4-only vectors.**
`shim/out/entryprobe-el1-thread-brk.img`, 26,562,560 B, SHA256
`1787a79128f3eb39edabcbdbadbc0fd56ab44203806f5835f7685ac6151f0dcc`.
Payload SHA256 `3b44b2bf052a865074a19b51ad0b447e0f5552f2b5cda370233fc2ef75d08d06`.
BRK offset `0x6232c4` at VA `0xfffffe0007aaf74c` / PA `0x101aaf74c`, after
`current_processor` returns inside `kernel_bootstrap_thread`. Selective
vectors; cleanup range stayed `[0x100000000, 0x108000000)` (128 MiB).
Expected record: `pc=fffffe0007aaf74c`.

The device did not return to Recovery within 45 s and entered a reboot loop;
no SWEET-ENTRY record was captured. The user entered fastboot manually. The
20,873,216-byte trimmed stock prefix was flashed (fastboot printed pipe
errors, but `Sending` and `Writing` both returned OKAY), and
`fastboot reboot recovery` reported "Command failed" yet the device booted
Recovery. The complete original 67,108,864-byte boot_a was then written and
read back; SHA256 `2931647a56039722ea2585990b8ef3b1a2daf4c9b990231879f753049eaf86b1`
verified. The device is in Recovery. Evidence: `thread-brk-restore.log` and
`thread-brk-restored.img`.

The cause is established by the later dual-slot hardware pass: XNU executes
with SPSel=0, so the BRK took vector slot 0 (EL1t) while this image patched
only slot 4. It reached XNU's original EL1t handler and reset. The
bootstrap-thread checkpoint itself was never implicated.

The earlier slot-4-only selective image `4d67b49b...` and its model evidence
are superseded. The `sched_init` fallback image `e7fe406e...` was also built
with slot-4-only vectors; do not use it without rebuilding.

**Completed: full vm_mem_bootstrap return (hardware PASS).**
`shim/out/entryprobe-el1-vm-return-brk.img`, 26,562,560 B, SHA256
`99d68ed6d5c870070a116e223b7ba29bd76b1e619c34e444f05146c92b1106fa`.
Payload SHA256 `fac094b493eb2156f627c4ab96247db4db314e8bbef644fed38d39b9b35b1a2d`.
BRK offset `-0x127fb0` at VA `0xfffffe00073644d8` / PA `0x1013644d8`, the
first instruction after `bl vm_mem_bootstrap` in `kernel_bootstrap`. Same
shared relay, high vectors, TTBR0 restore and x0 recorder; cleanup range
stayed `[0x100000000, 0x108000000)` (128 MiB).

Same-boot `vm-return-brk-dmesg.txt` records
`stage=87 fault=1 esr=f2005357 far=0 pc=fffffe00073644d8`, with
x0 `fffffe00080bbbc0` — identical to the host model. vm_retire_boot_pages,
vm_map_init, kmem_init (including the KMEM and ZALLOC startup phases and
zone_init) and vm_fault_init therefore all returned, and kernel_bootstrap
resumed after the complete VM bootstrap. The ESR is the inserted BRK, not
an unexpected kernel fault. Automatic Recovery return and the complete
original 67,108,864-byte boot_a restoration/readback SHA256 `2931647a...`
were verified; the written partition matched the predicted `376eb489...`
hash. Evidence: manifest, same-boot dmesg, before/written/restored images
and the emulation log. Preparation commit `3d638e1`. No source changes and
no new CI.

Host model full-path PASS (`vm-return-brk-emulation.txt`). At the trap:
TTBR0 empty `0x1024d8000`, TTBR1 `0x1024dc000`, DAIF masked, VBAR still
`0xfffffe0007488000`, GIC state unchanged. `vm_pages` still maps PA
`0x102ac4000..0x1038c16cf`, and `avail_start` stays `0x102838000`. True
translated-PA stores (the hook reports physical addresses) total 20,021,604
with max PA `0x1039e3fff`, inside the 128 MiB range. Bootstrap-TTBR0
identity aliases cover the whole 128 MiB window and were probed OK through
`0x220000000`; `0x22e000000` is **unmapped**, so do not extend the clean
limit beyond the validated window without new evidence. Six high kernel-map
VAs fault in `mmu_kvtop` (AT/PAR.F), expected for unmapped probes. The
bootstrap-TTBR0 restore, the 128 MiB clean loop and the return to stock
Linux with original SCTLR/SP/SPSel/DTB all pass in the model. These are
host-model results; the hardware result is the BRK record plus the full
restoration check.

**Completed: zone/object bootstrap checkpoint (hardware PASS).**
`shim/out/entryprobe-el1-zone-object-brk.img`, 26,562,560 B, SHA256
`e4231b9071f0a559c72a8d4961acfe895e2a91eb2ebae525647be1704018695a`.
Payload SHA256 `878148b67d4b242e294b716322ae87d60a2a8da99c2dfbfc8acb0e18d8233fc4`.
BRK offset `0x633648` at VA `0xfffffe0007abfad0` / PA `0x101abfad0`
replaces `bl vm_retire_boot_pages`, so it stops only after both
`zone_bootstrap` and `vm_object_bootstrap` return; that single-instruction
empty retire call is deliberately not executed. Same shared relay, high
vectors, TTBR0 restore and x0 recorder; cleanup range stays
`[0x100000000, 0x108000000)` (128 MiB).

Same-boot `zone-object-brk-dmesg.txt` records
`stage=87 fault=1 esr=f2005357 far=0 pc=fffffe0007abfad0`, with
x0 `fffffe0007b482a0`. vm_page_bootstrap, zone_bootstrap and
vm_object_bootstrap therefore all returned inside vm_mem_bootstrap; the
ESR is the inserted BRK, not an unexpected kernel fault. Automatic Recovery
return and the complete original 67,108,864-byte boot_a restoration/readback
SHA256 `2931647a...` were verified. The written partition matched the
predicted `ddef7f6a...` hash. Evidence: manifest, same-boot dmesg,
before/written/restored images and the emulation log in the evidence
directory. Preparation commit `1e233f4`. No source changes and no new CI.

Host model `zone-object-brk-emulation.txt` had predicted the same x0 and
PC. At the trap: TTBR0 empty `0x1024d8000`, TTBR1 `0x1024dc000`, DAIF
masked, GIC model unchanged. `vm_pages` still spans VA
`0xfffffe000eb38000..0xfffffe000f9356d0`; sampled first/last mappings are PA
`0x102ac4000` and `0x1038c16cf`, inside the cleanup range. `avail_start`
stayed `0x102838000`. The earlier `0x1024fbfff` store figure came from a
hook that treated physical addresses as virtual and is superseded: the
later state run measures true translated-PA stores through a deeper point
at max `0x1039e3fff`, so this checkpoint's 128 MiB range was sufficient.
Bootstrap-TTBR0 identity aliases across the whole 128 MiB window, the
high-vector page, the cleanup loop and the return to stock Linux with
original SCTLR/SP/SPSel/DTB all passed. These remain host-model results, not
hardware execution; the hardware result above is the BRK record plus the
full restoration check.

Evidence is ignored under `research/matisse/20261022-xnu-resume/`.
Each test below had explicit user approval including restoration. This LK
has no working `fastboot boot`; tests temporarily replace boot_a. A new
boot_a test requires separate confirmation per AGENTS.md. Do not write
vendor_boot, userdata, GPT, bootloaders, recovery, modem or persist.

**Observed results, in order:**

- Exact display control `entryprobe-display-kick-hw-ok.img`, 20,836,352 B,
  SHA256 `b8cec21a912dc978b7b78fddd343253e9a93b95b3d91e275bca0fe0bc0eeee3f`:
  user saw test screen and moving green bar; same-boot Recovery log had no
  OVL/CMDQ timeout errors. The old control reports `0x500007` despite visible
  refresh (known FRAME_DONE-check limitation).
- `entryprobe-el1-display.img`, 20,836,352 B, SHA256
  `a3131110a6a7876d08ade3518e87fdcf9a557b7500eecb2f43722f060e9dd4f0`:
  user saw EL1 text; same-boot stage `0x74`, fault 0, display_error 0,
  display result 1. **Actual initial entry is already EL1** despite LK's
  misleading `via EL2` message. MIDR `0x410fd462`, MPIDR `0x81000000`,
  CNTFRQ 13 MHz, SCTLR `0x30d00980`. EL2/HVC return branch remains untested.
- Full shim `shim-boot-xnu-resume.img`, 7,008,256 B, SHA256
  `b89fcc7c29cd9faa9c200c4ba7713bf1ad55c7bd9196d0e3271d0fd448eefafb`:
  user saw only Redmi logo; forced fastboot entry and full recovery completed.
- Direct loader/jump `entryprobe-el1-xnu.img`, 26,562,560 B, SHA256
  `bee6ee32f76f7faa6c1df8736f4eef54b81f1f5978bc087507cfabe10ec73c42`:
  user saw only logo, no Recovery; host later observed preloader USB.
  Full boot_a restored. The logo alone does not establish an execution stage.
- **Load-only `entryprobe-el1-load.img`, 26,562,560 B, SHA256
  `9e6c2bec44ccef8dc9e4681ca3c360f9930805b4003be4a0ebd80eb52a568c52`:**
  returned automatically to Recovery. Same-boot `el1-load-dmesg.txt` has
  `stage=7f fault=0 esr=0 far=410fd462 pc=81000000`, timer INTID 27.
  The loader reached its last S7 ID checkpoint and returned through
  LOADER_NO_JUMP, after copying XNU segments, ADT and boot_args. FAR/PC here
  are MIDR/MPIDR diagnostic values, not exception addresses. Full boot_a
  restoration and the 64 MiB SHA256 above were verified afterward.

All tests restored the full original partition. A trimmed fastboot restore
alone previously left one 4 KiB block of test data beyond the prefix; always
follow it with a full Recovery write and complete readback hash. Recovery
/tmp is cleared each reboot: re-push the backup before each restoration.
Use `dd ... && sync` and accept adb state `recovery` as online. Recovery dd
can append statistics to stdout or silently truncate streaming output: use an
on-device temporary readback file plus adb pull and verify its exact length.

**Build and implementation:** latest successful kernel CI remains
`Jinsens/ios-sweet` run **39640336293**, commit `dd9752e`; no new CI run.
`xnu/out/ci-39640336293/kernel.development.sweet` SHA256
`bc308789486ee96b380ce374bc7fe4c1894f4a115da9662b4cb0cf9a016b543c`.
Debug payload `shim/out/matisse-xnu-debug.payload` SHA256
`b6eafe9a953aea1d18a34d579e43e172f1bb0f60a289a51b303d463e13e8fe95`
adds only `-enable_kprintf_spam`. XNU entry PA `0x10148c488`, boot_args
`0x1024d4000`, top `0x1024d8000`; physBase `0x100000000`, memSize
`0x12e000000`. Probe Image 65,552,896 B; marker offset 48,947,200;
stock Linux +2 MiB and live DTB `0x47c80000` remain intact.

The timer reader now handles GIC interrupt tuples of **four cells on
MT6983 and three on sweet**, yielding virtual INTID 27 and physical 30
against the live tree. 27 host tests pass, all nine original diagnostic
levels plus el1-xnu/el1-load cross-compile. XNU video mapping checks pass
11 cases. Full repo validation still fails on six pre-existing CRLF shell
files; do not report it as passing.

Commits: `712b44f` (display-control/restoration handoff), `031d329` (EL1
probe, hardware-tested display refresh, initial timer fix). Commit `850e1d2` records the load-only control and four-cell timer work. Pre-existing
`shim/build.sh` --kick and `shim/shim.c` KICK_ONLY work remains untested;
the old mkentryprobe `xnu` level is likewise untested. Preserve these edits.

**Next concrete action:** extend the bootstrap-thread checkpoint to
`sched_startup`/`idle_thread_create` and then to `thread_daemon_init`, still
with the dual-slot selective vectors. After that, verify timer interrupt
delivery with normal XNU vectors and a running thread. Per user direction,
go directly to device tests; do not spend time on full-boot emulation.
Re-check the dirty physical range at each deeper checkpoint; the 128 MiB
window covered this thread entry but is not proven for later allocations.
The bootstrap-thread image `154449c1` passed and was fully restored;
selective vectors `81652ccf` passed at the vm-return checkpoint; the earlier
full-return `99d68ed6`, zone/object `e4231b90` and post-vm_page `e9b81b88`
also passed. Rebuild the stale `sched_init` image before any use. No device
test is currently authorized.
The requested standalone Chinese report is
[docs/matisse-xnu-ios-roadmap-zh.md](docs/matisse-xnu-ios-roadmap-zh.md):
complete progress, minimal userspace, real iOS, UFS, touch, USB and acceptance
criteria. The latest user request is to receive this report after the test.

**Source/Recovery corrections established while preparing the report:**
- This exact CI kernel has only RET at vm_retire_boot_pages
  (`0xfffffe0007439678`); the source implementation is empty. Earlier warnings
  treating that function itself as a page-table teardown are too conservative.
  Later allocations/mapping changes still require lifetime/cleanup review.
- The diagnostic vector table must not replace normal XNU IRQ/SVC/page-fault
  handling when proceeding into interrupts and userspace. Preserve/restore
  normal vectors or implement a selective diagnostic handler first.
- Touch is **ST FTS**, not the historical FocalTech label: live spi6.0
  compatible is `st,spi`, bound driver `fts`, Recovery module
  `fts_touch_spi.ko`, firmware `st_fts_L11.ftb`. Exact IC still needs ID
  confirmation. SPI6/CS0/mode0/12 MHz and 14400x32000 coordinate range agree
  with device logs and vendor DTS. Evidence: `touch-driver-binding.txt`.
- Pending shim UFS review: GPT LE fields are read using be32 (entry LBA is
  also 64-bit), write UPIU lacks W flag, timeout assumes 19.2 MHz instead of
  measured 13 MHz. These are source findings, not a proven explanation of
  earlier host-takeover failure; no UFS source changes made this turn.
- Existing XNU UFS init also launches keys/touch/USB; decouple these for
  independent RAM-disk driver tests. Current payload has no RAMDisk/root arg.

Do not reuse the bootstrap-table relay at later stages without separately
proving its tables, vectors, saved state and cleanup mappings survive.
The shared relay restores bootstrap TTBR0 only on exception; the older
per-slot relay cannot be used after identity-map teardown.

**Completed entry BRK test:** `entryprobe-el1-entry-brk.img`, 26,562,560 B,
SHA256 `386420a822f8e7e4c368d5882b1509cdcbdbe70ffd08bf32e1d96cc84a824ded`.
Same-boot Recovery captured `stage=87 fault=5 esr=f2005357 far=0 pc=10148c488`.
It returned automatically; full 64 MiB restoration verified. The first
exec-out readback silently truncated at 59,225,600 B; a full on-device tmp
read plus adb pull completed and matched the original hash. Always validate
length; use tmp readback + pull if streaming is truncated.

**Completed pre-VBAR test:** `entryprobe-el1-vbar-brk.img`, 26,562,560 B,
SHA256 `1291e310667744208e5328d72ca9c7c293e3ea2859dbddf86856725f57dd4660`.
Same-boot Recovery captured `stage=87 fault=5 esr=f2005357 far=0 pc=10148e104`.
The original entry branch and first six start_first_cpu instructions ran.
Automatic Recovery return and complete original boot_a hash verified.
Commits: `6c9772e` (bounded breakpoint tooling), `1c7dc60` (entry result),
`286923e` (pre-VBAR result). Exact manifests/logs/readbacks are in the evidence
directory above. Neither test proves the remaining original initialization.

**Completed: early-vector relay + page-table checkpoint**
`shim/out/entryprobe-el1-tables-brk.img`, 26562560 B, SHA256
`276ffdd70208c8190f46614b6f09893fb3e9d822ec09ed81f1d8b2f5dfcead4d`.
Payload SHA256 `69f1676576e11b2f5bcac36c49a255c4a5b7fa6d63442c360fe9ee657eca4c06`.
One payload BRK replaces common_start's first instruction at `0x10148e444`
(entry offset `0x1fbc`), after bootstrap/video page tables are prepared and
before TCR/TTBR/MMU configuration. `--xnu-vector-offset 0xb78` validates the
16 early spin-vector slots at `0x10148d000` and enables the loader to replace
each slot with a 64-bit register-indirect branch to the corresponding probe
vector. XNU's original VBAR write remains intact. Diagnostic use is limited
to MMU-off checkpoints; the probe prefix is not in XNU's page tables.
The stackless exception recorder now restores the initial SPSel before SP,
because XNU switches to SP_EL0 with an unmapped KVA before this checkpoint.
Expected ESR `0xf2005357`, PC `0x10148e444`, fault slot **1** (EL1t sync).
An earlier real exception will instead record its own ESR/PC.

31 host tests pass. Full image executed in Unicorn with modeled display/
clock and manually modeled BRK exception entry: actual loader, XNU code up
to common_start, generated vector trampolines and probe fallback ran; original
SP, SPSel and DTB argument restored at stock Linux entry. This is host-only
evidence, NOT hardware success. Log `tables-brk-emulation.txt`.
Predicted written-partition SHA256 `a5c00b3edbc254030c4d962bd6b9ccfb830aea6d1fff7ed443703680091f8ce0`.
**Hardware PASS (explicitly approved):** same-boot `tables-brk-dmesg.txt`
recorded `stage=87 fault=1 esr=f2005357 far=0 pc=10148e444`. The kernel
executed boot_args loads, stack changes and page-table initialization up to
common_start. The relay handled an EL1t exception and returned automatically
to Recovery. Full 64 MiB original boot_a hash verified after restoration.
Next prepare a breakpoint before the high-VA VBAR switch at `0x10148e4f8`,
after TCR/TTBR/MAIR and TLB/cache operations, still before MMU enable.

**Completed: MMU configuration checkpoint**
`shim/out/entryprobe-el1-mmu-config-brk.img`, 26562560 B, SHA256
`36228bdb46ade73cb03dc5fc628c5cf675b5ac87956398d4c17f08e26c334f51`.
Payload SHA256 `3f7c78fbc5b7f1ab25a18d88cc3afc4f64f57d61010721fe4fed6aca181d2f58`.
BRK offset `0x2070` replaces MSR VBAR_EL1 at `0x10148e4f8`, just before
XNU changes from low physical vectors to its high virtual vectors.
The same early-vector relay remains enabled. Host execution with modeled
MMIO/BRK reached `0x10148e4f8`, then returned to stock Linux with original
SP/SPSel/DTB restored (`mmu-config-brk-emulation.txt`). Hardware PASS with explicit approval: same-boot Recovery recorded
`stage=87 fault=1 esr=f2005357 far=0 pc=10148e4f8`. All pre-MMU
TCR/TTBR/MAIR and TLB/cache operations executed. Automatic return and full
64 MiB restoration verified (`mmu-config-brk-dmesg.txt` and readback). Predicted partition SHA256
`d99e68b1110f8b421ecd8bf88a0f6ff0de8872962381de66d391761f22b4ce00`.
Device remains in restored Recovery; no new write yet.

**Completed: immediate MMU-on checkpoint**
`shim/out/entryprobe-el1-mmu-on-brk.img`, 26562560 B, SHA256
`7937d19c9ef74c5c7c9557098596902c054010b4553d6a7a6e2f9d152fc15f16`.
Payload SHA256 `38ac4bda2a6a711c45adc09ecd97488313415c14efddb0cfbac68aef463aaa9e`.
BRK at entry+`0x20a8` = `0x10148e530` replaces RET to arm_init after
MMU enable, CPACR and TPIDR initialization. No kernel C code runs.
The low vector relay is retained. `--xnu-high-vector-offset=-0x4488`
validates branch/NOP slots and installs a copied stackless assembly relay
in the high vector table at PA `0x101488000`. It first branches from the
high virtual mapping to its own physical identity alias, then disables
M/C/I and jumps back to the probe. The probe restores original SCTLR and
SPSel/SP. **Only safe for the immediate checkpoint before cached C writes
or bootstrap identity-map teardown; do not use for arbitrary later stages.**
XNU's original high VBAR and SCTLR writes execute unchanged.

32 host tests pass. Unicorn's CPU model advertises MMFR0 `0x1124` (no 16K
granule), so CPU-mode emulation faults at MMU enable and cannot validate
this target. With a modeled 16K translation callback walking XNU's actual
L1/L2 descriptors, actual startup/relay code reaches `0x10148e530` and
returns to stock Linux with original SCTLR/SP/SPSel/DTB restored. This is
host model evidence only, not a real CPU transition. Logs:
`mmu-on-brk-emulation.txt`, `mmu-on-brk-modeled-emulation.txt`.
The earlier independent hardware MMU probe did verify 16K support.
Predicted partition SHA256 `557bdf81d00c77f5d81ee683de2989a4257cce30cccfe329193ae3a66fc8ae56`.
**Hardware PASS (explicitly approved):** same-boot Recovery captured
`stage=87 fault=1 esr=f2005357 far=0 pc=10148e530`. XNU's real high VBAR
and SCTLR writes executed, then CPACR/TPIDR and boot_args VA conversion.
The high-vector relay returned automatically to Recovery. Complete original
64 MiB boot_a hash verified. Evidence: `mmu-on-brk-dmesg.txt`, manifest and
restored image. Next: a bounded early-C checkpoint with explicit cache
clean/invalidate before leaving XNU's bootstrap identity mapping.

**Completed: bounded early-C checkpoint**
`shim/out/entryprobe-el1-early-c-brk.img`, 26562560 B, SHA256
`98e8829d84edeabf476c0c837cfefe1a132d993e6baee39082e3bf54eaa835ff`.
Payload SHA256 `37ba85594c75f1ec7b4260a6ce20a4bfc56d44ee0385cfdbab6510cf3acdba6e`.
BRK offset `0x649428` replaces the BL to arm_set_kernel_tbi at
VA `0xfffffe0007ad58b0` / PA `0x101ad58b0`. It stops after arm_init's
prologue, sweet_early_init and sweet_early_mark; before later initialization.
The high-vector relay now has optional `--xnu-clean`: after switching to
its physical alias it cleans/invalidates each D-cache line in
`[0x100000000, 0x1024d8000)` using CTR_EL0's line size, then disables MMU
and returns to the probe. This covers the kernel's static globals/stacks,
ADT and boot_args used here. It still requires bootstrap identity mappings
and must not be reused after VM remapping/allocation without a new review.
The copied relay is 120 bytes and linker-checked to fit each 128-byte slot.

33 host tests pass. With modeled MMIO/16K translation/BRK entry, actual XNU
C code reached the high-VA checkpoint, the cache-maintenance loop executed,
and original SCTLR/SP/SPSel/DTB were restored at Linux entry. Emulation does
not model cache coherency or real hardware timing. Evidence:
`early-c-brk-emulation.txt`. Predicted partition SHA256
`370a7bc51f1cb74fce3d0b966851664927707668eb8ce06d83a7882ff25a398e`. Device remains restored in Recovery;
**Hardware PASS (explicitly approved):** `early-c-brk-dmesg.txt` records
`stage=87 fault=1 esr=f2005357 far=0 pc=fffffe0007ad58b0`. arm_init's
C prologue, sweet_early_init and first sweet_early_mark ran. Cache cleanup
and automatic return to Recovery succeeded. Full 64 MiB original boot_a
hash verified. MMU-on milestone `9161917`; bounded cleanup tooling `ccb1d03`.
Next: stop before arm_vm_init while bootstrap identity mappings still exist.

**Completed: pre-VM checkpoint**
`shim/out/entryprobe-el1-pre-vm-brk.img`, 26562560 B, SHA256
`25d5d260f4eb2f7ebb215062d81b8e97c5eabaebfa84aed9a17f1f015e0aef63`.
Payload SHA256 `b7a0fe56181f8ae2104b2258c08f1bf7f6aedfcaf58e55dd3737cf7d17117a38`.
BRK offset `0x649c9c` at VA `0xfffffe0007ad6124` / PA `0x101ad6124`
replaces the call to arm_vm_init. Same bounded cache cleanup and low/high
exception relays as the hardware-passed early-C test. No VM-map teardown
or later device driver initialization executes. Static bootstrap storage
remains inside the cleanup range.

Host emulation reached this checkpoint and restored original SCTLR/SP/SPSel/
DTB using Unicorn MAX (LSE atomics supported), modeled 16K translation,
MMIO and exception entry. Default A72 model stops at LDADD; that is an
emulator feature limitation, not evidence of a device failure. Log:
`pre-vm-brk-max-emulation.txt`. Existing 33 host tests remain passing;
no new source changes for this image. Predicted partition SHA256
`f42873e5419cdc5a786c4f933f09d947775294c48333f11d042c800f9f90d43c`.
**Hardware PASS (explicitly approved):** same-boot `pre-vm-brk-dmesg.txt`
records `stage=87 fault=1 esr=f2005357 far=0 pc=fffffe0007ad6124`.
Platform setup, CPU topology, bootstrap thread, CPU/timer initialization and
early startup reached arm_vm_init. Automatic Recovery return and full
64 MiB original boot_a hash verified. Early-C result commit `ec4d84f`.
Next: stop just before the first TTBR1 switch inside arm_vm_init; expand
cache cleanup to cover newly allocated page tables.

**Completed: final-table construction checkpoint**
`shim/out/entryprobe-el1-final-tables-brk.img`, 26562560 B, SHA256
`340b962813b4bc3cd6cf699525c5003b7643087becc3915dba0390e42de5ec52`.
Payload SHA256 `9ccf10dd33d42a9d79588de2374b8bcbbff759f56e757d2ce5345ea4813f62fc`.
BRK entry-relative offset `-0x86b0` at VA `0xfffffe0007483dd8` /
PA `0x101483dd8` replaces BL set_mmu_ttb_alternate. Original bootstrap
TTBR0/TTBR1 are still active, preserving the validated fallback.
`--xnu-clean-limit 0x104000000` extends cleanup to the first 64 MiB of
managed RAM to include arm_vm_init's new page tables. Generator validates
the extension is aligned, covers the original bootstrap range, and stays
inside the declared managed RAM. Signed offsets now allow checkpoints in
functions located before __start.

34 host tests pass. Unicorn MAX with modeled 16K translations and AT/PAR
operations executes through this checkpoint and returns to Linux with
original SCTLR/SP/SPSel/DTB. Allocation and final table pointers are recorded
in `final-tables-brk-emulation.txt`; alloc end is within the 64 MiB cleanup.
CPU-mode AT cannot handle this model's missing 16K support, so AT/PAR is
explicitly modeled. Predicted partition
SHA256 `23320b4789d653d980e8c1d5320333cff4ca94da62ed4ab61f8f224e24b0c218`.
**Hardware PASS (explicitly approved):** same-boot `final-tables-brk-dmesg.txt`
records `stage=87 fault=1 esr=f2005357 far=0 pc=fffffe0007483dd8`.
arm_vm_init built the formal tables and reached its first TTBR1 switch.
The ESR is the inserted BRK, not an unexpected kernel exception. Automatic
Recovery return and the complete 64 MiB original boot_a hash were verified
(`final-tables-brk-manifest.json` and `final-tables-brk-restored.img`).
Pre-VM milestone commit `21fecbe`; bounded cleanup tooling `cb96eaa`.
No new kernel CI run; the tested kernel remains run `39640336293` / `dd9752e`.

**Completed: first formal TTBR1 switch checkpoint**
`shim/out/entryprobe-el1-ttbr1-brk.img`, 26,562,560 B, SHA256
`e9fbcb8119f7a0ca1153306dab5bb0d015b15c34f1f803ada5df3bf0ae072cf2`.
Payload `shim/out/matisse-xnu-ttbr1-brk.payload` SHA256
`66fae84c6e5d019989189ae9657a7a25106d5188939a81c03194a5b01fc0a873`.
BRK entry offset `-0x86ac` at VA `0xfffffe0007483ddc` / PA `0x101483ddc`
replaces BL ml_enable_monitor, immediately after set_mmu_ttb_alternate
returns. Same 64 MiB cache cleanup and low/high vector relays as the last
hardware-passed image. Predicted full written-partition SHA256
`2aab2ebd0f3d4fb94242bcc3f6b3179107695d2569d76b9fd0f1dfc133e0d595`.

Image cross-compile succeeded. Host modeled execution passed
(`emulate-ttbr1.py`, `ttbr1-brk-emulation.txt` in the ignored evidence folder).
The explicit 16K walker now handles L3 pages and privileged permissions;
after the actual TTBR1 MSR it flushes modeled translations before continuing.
New TTBR1 `0x1024dc000` maps the checkpoint and high vectors RX at their
expected PAs; unchanged TTBR0 `0x10117c000` retains executable identity
mapping for the relay and readable identity aliases across the cleanup
range. The BRK, cleanup and Linux return all execute; original SCTLR/SP/
SPSel/DTB are restored. Unicorn's fixed stop address itself triggered an
unmapped-address lookup on a TLB flush; using a Linux-entry execution hook
avoids that host-only issue. MMIO, translation, AT/PAR and exception entry
remain modeled, so this is NOT a hardware result. No tracked source changes
or new kernel CI were needed. Final-table hardware result commit `780b9c5`;
TTBR1 preparation `2c5355f`.
**Hardware PASS (explicitly approved):** same-boot `ttbr1-brk-dmesg.txt`
records `stage=87 fault=1 esr=f2005357 far=0 pc=fffffe0007483ddc`.
The original set_mmu_ttb_alternate executed and returned with the formal
TTBR1 installed. Automatic Recovery return and complete original 64 MiB
boot_a restoration/hash were verified (`ttbr1-brk-manifest.json`).

**Completed: TTBR0 teardown + relocated early-console checkpoint**
`shim/out/entryprobe-el1-ttbr0-off-brk.img`, 26,562,560 B, SHA256
`c73eb57fafc6efe21aba965f54b28e3442f23aa64cf0cd8e26de8c36714c2bba`.
Payload SHA256 `d4449cd59bcad9cb5988cb46c91ecde3870a51b1d80624c4208f9ee9a1ca1170`.
BRK entry offset `-0x8670` = VA `0xfffffe0007483e18` / PA `0x101483e18`,
after the original TTBR0 replacement, TLB invalidation and early mark 10;
before kva_active becomes true. Predicted full partition SHA256
`98a72e930421759bb74002e166e5e1c887f88cb017c7e9ba9ab794a428f86d11`.

New `--xnu-restore-ttbr0 0x10117c000` is derived from the kernel's
bootstrap_pagetables symbol and modeled actual TTBR0. The builder checks
alignment, segment bounds, initially zero storage and cache-clean coverage.
It does not prove runtime table contents: those are checked by the host
walker at this checkpoint. The shared 2 KiB high vector template retains
all 16 slot entries, holds common code in slot 0 (end +0x7c) and literals
behind slot 1's branch (end +0xb0). Linker assertions enforce boundaries.
On exception it restores that TTBR0, invalidates TLBs, branches to an
identity alias, cleans `[0x100000000,0x104000000)`, disables MMU/caches and
returns to the slot-specific probe recorder. Normal XNU execution retains
its original TTBR0 teardown. This is only validated while bootstrap tables,
high vector mappings and compatible TCR survive, and allocations stay in
the cleanup range; do not assume this supports arbitrary later checkpoints.

36 host tests pass. New image cross-compiles. Modeled execution reaches the
BRK with empty TTBR0 `0x1024d8000`, formal TTBR1 `0x1024dc000`, and alloc end
`0x1024fc000`; all 16 high-vector entries restore SCTLR/SP/SPSel/DTB and
return to Linux. Logs: `ttbr0-off-brk-emulation.txt` and
`ttbr0-all-vectors-emulation.txt`. Translation/AT/MMIO/exception entry remain
modeled and cache coherence is not modeled.
Rebuilding the previous TTBR1 image without the new option reproduces
`e9fbcb81` byte-for-byte. No kernel CI run; TTBR1 hardware milestone `8a257b2`.
Shared-relay implementation commit `f1b6d14`.
**Hardware PASS (explicitly approved):** same-boot `ttbr0-off-brk-dmesg.txt`
records `stage=87 fault=1 esr=f2005357 far=0 pc=fffffe0007483e18`.
Original TTBR0 teardown, TLB flush and relocated early-console mark 10
executed. The shared relay restored bootstrap TTBR0 and returned to Recovery.
Complete 64 MiB original boot_a hash verified after restoration; see
`ttbr0-off-brk-manifest.json` and full restored readback.

**Completed: complete arm_vm_init checkpoint**
`shim/out/entryprobe-el1-post-vm-brk.img`, 26,562,560 B, SHA256
`9ac98004aea8b30e9ab6a5a5d1360c66930d814d2ed2622154b438dbbb032b89`.
Payload SHA256 `534508b7776fc84aba87edd866b5a5373684a390d82e64f5c02136c4557399a2`.
BRK at entry offset `0x649ca0`, VA `0xfffffe0007ad6128` / PA `0x101ad6128`,
immediately after arm_vm_init returns to arm_init. Uses the hardware-passed
shared relay with bootstrap TTBR0 `0x10117c000` and cleanup ending
`0x104000000`. Predicted full partition SHA256
`d00c603d4c08ec89ed6be181b6cf10dbb4df8b6cef1a07e7b8ffa99393dec7cf`.
Cross-compile and modeled execution pass (`post-vm-brk-emulation.txt`):
reaches the return, allocation end `0x102838000` is inside cleanup, bootstrap
identity table contents still cover the cleanup aliases, current TTBR0 is
empty and formal TTBR1 still maps the high relay RX. Restores original
SCTLR/SP/SPSel/DTB and returns to Linux. Modeling limitations above still
apply. No new tracked source change, no new CI. TTBR0 result `7090a94`;
post-VM preparation `0e9e385`.
**Hardware PASS (explicitly approved):** same-boot `post-vm-brk-dmesg.txt`
records `stage=87 fault=1 esr=f2005357 far=0 pc=fffffe0007ad6128`.
The entire arm_vm_init returned to arm_init. Automatic Recovery return and
complete 64 MiB original boot_a restoration/hash verified; evidence includes
`post-vm-brk-manifest.json` and restored readback.

**Completed: console initialization checkpoint with return value**
`shim/out/entryprobe-el1-post-serial-x0-brk.img`, 26,562,560 B, SHA256
`e9888fe6991bfa4c3084bb60d3b57ffe5c4567c25e144fae26bf2518642b840d`.
Payload `shim/out/matisse-xnu-post-serial-brk.payload` SHA256
`6b8478ff154070014df4c7bab9afd67a92f755b66913f0747a6d419d092454e0`.
BRK at entry offset `0x649cdc` = VA `0xfffffe0007ad6164` / PA `0x101ad6164`,
immediately after serial_init. Same shared relay and cleanup bound as the
post-VM pass. Predicted full written-partition SHA256
`c56ea9c53276c9b72ea9b913c66ae3716be18a6de7e99f0495562feafce57e9f`.
The ordinary probe banner now appends `x0`; the exception recorder captures
it before reusing that register. This distinguishes a successful return
from a skipped/failed console setup without repurposing FAR or PC.

36 host tests and cross-compile pass. Modeled execution reaches the BRK
with x0=1, fbcon_base `0xfffffe000a003000`, disp_base `0xfffffe000d4c0000`,
disp_ready=1 and alloc end `0x102838000`, then returns to Linux with x0=1
in the banner and original boot registers restored. The harness now models
kernel CNTFRQ/CNTPCT/CNTVCT instructions as well as prefix counters. Display
MMIO remains modeled; a successful host display state is NOT proof of
hardware panel refresh. Evidence: `post-serial-x0-brk-emulation.txt`.
The older `post-serial-brk` image `dabd026d` has no x0 field and was never
flashed; use the x0 image above. Full VM hardware milestone `c4c2014`.
Return-value recorder commit `e24a92c`.
**Hardware PASS (explicitly approved):** same-boot
`post-serial-x0-brk-dmesg.txt` records
`stage=87 fault=1 esr=f2005357 far=0 pc=fffffe0007ad6164 x0=1`.
serial_init returned success. Automatic Recovery return and complete original
64 MiB boot_a hash verified after restoration. No user panel observation has
been collected for this round; don't equate x0=1 with visible text.

**Completed: later platform initialization checkpoint**
`shim/out/entryprobe-el1-post-platform-brk.img`, 26,562,560 B, SHA256
`a89bd1c087c1a33311c4546db3b6044212c9400b46f401f47996a0a88d011ae1`.
Payload SHA256 `41a9bc023a3f4170c800b1fe85c578316ad348c525c01a6e0356fc6408d0785c`.
BRK at entry offset `0x649e50`, VA `0xfffffe0007ad62d8` / PA `0x101ad62d8`,
after kernel startup through phase 4, console creation/printf setup, idle
initialization and PE_init_platform(TRUE). Same relay/cleanup/x0 recorder.
Predicted partition SHA256
`fca03c37a66e2b863ca95cd666c25c8fc75532cb2f855aa9f87d2324aaa7acb8`.
Cross-compile and host modeled execution pass, including original-register
restoration and Linux return (`post-platform-brk-emulation.txt`). Its first
host attempt exhausted the 20M post-TTBR0 instruction bound in another
framebuffer clear; increasing that bound to 180M reaches the expected BRK.
Allocation end remains `0x102838000`; bootstrap table and high-vector checks
still pass. x0 at this void-function checkpoint has no success/failure meaning.
No new source change or CI run. Console hardware milestone `2ff0748`.
Preparation commit `6d264bc`.
**Hardware PASS (explicitly approved):** same-boot `post-platform-brk-dmesg.txt`
records `stage=87 fault=1 esr=f2005357 far=0 pc=fffffe0007ad62d8`,
with x0 `fffffe00080bbc00` (not a status value at this checkpoint).
Original PE_init_platform(TRUE) returned. Automatic Recovery return and
complete original 64 MiB boot_a restoration/hash verified.

**Completed: CPU/timer/GIC setup before machine_startup**
`shim/out/entryprobe-el1-pre-machine-brk.img`, 26,562,560 B, SHA256
`34efc91a3be079fef6b793144e0f9d33289c70e008f628f155bc2e8468ad62fe`.
Payload SHA256 `b2d31f7170972ae4920524b90fbaad4d7bb6ff5daff30b366304c44729d63122`.
BRK offset `0x649f18` at VA `0xfffffe0007ad63a0` / PA `0x101ad63a0`
replaces BL machine_startup, after CPU timebase/timer setup, PE_init_cpu,
FIQ/GIC context initialization, chosen-property checks and early_random.
Same shared relay, x0 recorder and 64 MiB cache-clean range. Predicted
partition SHA256 `975bb3bb8c7d362c1061018e403c7a89d15add86c9f3dfcd855479a893a08e63`.

Cross-compile and modeled execution pass (`pre-machine-brk-emulation.txt`).
The first run stopped at a previously unmodeled GICR_TYPER read, PA
`0xc440008`, in pe_init_fiq. The host harness now models GIC MMIO and the
ICC_SRE/BPR1/PMR/CTLR/IGRPEN1 registers; CPU0 affinity/frame agree with
Recovery's observed redistributor 0 at `0xc440000`. Awake/RWP-clear state and
system-register behavior are model assumptions, not hardware measurements.
No interrupt delivery is modeled. At the checkpoint all DAIF bits remain
masked, modeled GIC enables PPI 27 and SGI 1, allocation end `0x102838000`
remains in cleanup, and the existing mapping/return checks pass. Normal Linux
entry follows with original SCTLR/SP/SPSel/DTB restored. This test exercises
real GIC setup for the first time in this XNU path. No new source changes or
CI run. Platform hardware result `3168dbb`; preparation `27e123d`.
**Hardware PASS (explicitly approved):** same-boot `pre-machine-brk-dmesg.txt`
records `stage=87 fault=1 esr=f2005357 far=0 pc=fffffe0007ad63a0`,
x0 `fffffe0007177a68` (boot_args). CPU/timer/GIC context initialization,
chosen-property checks and early_random ran. Automatic Recovery return and
complete original 64 MiB boot_a restoration/hash verified.

**Completed: kernel_bootstrap through vm_page_bootstrap**
`shim/out/entryprobe-el1-post-vm-page-brk.img`, 26,562,560 B, SHA256
`e9b81b88927d98d3b1eef0876679f661ffc610ee498cc9a481b38692c267f461`.
Payload SHA256 `3d6f731bb3ad5e5fe2629ddc0489ba9ebe2f003ff988eda2246b47607ab9992d`.
BRK offset `0x633628` at VA `0xfffffe0007abfab0` / PA `0x101abfab0`,
after vm_page_bootstrap returns inside vm_mem_bootstrap; before zone/object
bootstrap and vm_retire_boot_pages. Uses the existing shared relay/x0
recorder with cleanup extended to `0x108000000` (128 MiB). Predicted
partition SHA256 `02d97949e29ca0de8386f88a869c2cfbaf71311c1b3b519ee1bf3e1d8c9ebc2c`.

Cross-compile and modeled execution pass (`post-vm-page-brk-emulation.txt`).
vm_pages spans VA `0xfffffe000eb38000` to `0xfffffe000f9356d0`; sampled
first/last mappings point to PA `0x102ac4000` and `0x1038c16cf` respectively,
inside the cleanup range. The modeled managed-RAM window is limited to
128 MiB; bootstrap identity aliases across that window and high vectors
are checked before executing the fallback. DAIF stays masked, GIC model
checks pass, and original boot registers are restored at Linux entry.
These are host model results. No new source changes or CI. CPU/GIC hardware
milestone `cfb5e8c`; this checkpoint preparation `0032264`.
**Hardware PASS (explicitly approved):** same-boot `post-vm-page-brk-dmesg.txt`
records `stage=87 fault=1 esr=f2005357 far=0 pc=fffffe0007abfab0`,
x0 `0xa526f9c` (not a success status at this checkpoint). Original
vm_page_bootstrap returned inside vm_mem_bootstrap. The expected BRK is
deliberately inserted, not an unexpected kernel fault. Automatic Recovery
return and full 67,108,864-byte boot_a restoration/readback SHA256 verified.
Evidence: `post-vm-page-brk-manifest.json`, same-boot dmesg and full restored
readback in the evidence directory. No panel observation collected this round.

`oem expdb` exports a gzip 128 MiB dump but has no SWLG/SWX2 evidence; it is
not a usable shim log. GenieZone stage-2/RKP messages are a possible lead,
not an established cause. Full-shim Unicorn emulation reached XNU entry
with modeled MMIO; this does not prove hardware execution.

## >>> SESSION 2026-10-22 - diagnostic kick: log_store trace + XNU sentinels (read first) <<<

**Device state at this writing (observation):** `boot_a` contains the
diagnostic image `shim/out/shim-boot.img`, 7,008,256 bytes, SHA256
`d2960f102eaf3b5e280e28de1511b645c5d448bf6a3af888fa05c86027ac5cba` (boot v4).
It was flashed via `tools/fbraw.py flash boot_a` (both `download:` and
`flash:boot_a` returned OKAY). After `fastboot reboot`, the handset showed the
LK/Redmi logo and **no USB device enumerated** for over 30 seconds. It did not
reset because this diagnostic build deliberately leaves the MTK AP watchdog
disabled after the jump. `boot_a` is **not restored yet**. XNU entry is not
established.

`fastboot boot shim/out/shim-boot.img` was tried first: LK accepted the
6.8 MB transfer, then stayed in fastboot with no "Booting" response, i.e. this
LK still has no working temporary boot. Do not use it as a non-destructive
path.

**What this image does (host-verified, hardware not yet read back):**
- The shim writes a stage trace to MediaTek's `log_store` reserved memory
  (`mediatek,log_store` in the live FDT; PA `0x7ffbf000`, size `0x40000`).
  The trace header `SWX2BOOT\n` and log lines are mirrored at offsets
  `0x1000`, `0x10000` and `0x30000` so a partial LK append cannot hide all
  copies. `fastboot oem lkmsg` dumps exactly these 262,144 bytes
  (`DATA00040000`), and the dump survives a reset. This is **not** the
  ramoops pstore zone (`0x48090000`) and not `/chosen/log_store`
  (`0x11df00`).
- Stages on the panel and in the trace: `S0 wdt` (watchdog mode before/after
  disable), `S1 board`, `S1 disp` (`display_probe` result and error code),
  `S3 payload`, `S4 layout`, `S5 copied`, `S6 bootarg`, `S7 jump`
  (`SCTLR_EL1`), `S7 EL` (`CurrentEL`, `CNTFRQ`), `S7 ID` (`MIDR`, `MPIDR`),
  `SENT`, then `XNU jumping`. Every stage calls `display_refresh()` only
  when `display_probe()` succeeded; otherwise the panel keeps the LK logo.
- Before the jump the shim plants `0x584e55454e545259` ("XNUENTRY") in three
  XNU globals. The next shim boot reads them:
  | Global | PA (this payload) | Written by |
  | --- | --- | --- |
  | `bootstrap_pagetables` | `0x10117c000` | `start_first_cpu` zeroing loop |
  | `const_boot_args` | `0x101177a68` | `arm_init` (`const_boot_args = *args`) |
  | `gPhysBase` | `0x101178100` | `arm_vm_init` |
  | `gVirtBase` | `0x101178110` | `arm_vm_init` |
  A word still equal to the magic means that stage was not reached. The PAs
  are generated by `tools/diag_syms.py KERNEL PAYLOAD > shim/out/diag_syms.h`
  and compile-checked against the payload header; never hardcode them.
  Every boot also writes `SWX2SENT BS=… BA=… GP=… GV=…` at
  `log_store_end - 0x800`, and a reporter boot writes
  `SWX2 REPORT BS=… BA=… GP=… GV=…` at `log_store_end - 0x400`.

**Interpreting the logo:** "no USB" only proves LK stopped its fastboot
gadget. "Panel never changed" is consistent with (a) a shim hang before
`display_probe`, (b) `display_probe` failing and `display_force_refresh()`
returning because `dsi`/`mutex` were never resolved, or (c) a successful push
that the command-mode panel did not latch. The trace distinguishes these;
the logo alone does not.

**`oem p2u on` does not help here:** its implementation in this LK
(`app/mt_boot/sys_commands.c`) only appends `printk.disable_uart=0` to the
next **Linux kernel** command line. It touches neither the shim nor XNU and
does not create a USB console.

**Next concrete actions:**
1. Add `shim/out/diag_syms.h` generation to the build (already wired via
   `XNU_DIAG_KERNEL=…`).
2. Force reset to fastboot (long-press Power, then Power+VolumeDown), run
   `research/.../fbraw.py oem lkmsg OUT.bin`, and copy `OUT.bin` under
   `research/matisse/` (gitignored). Read the `S1 disp` line first.
3. If the trace shows `S7 jump` + `SENT`, the next boot's `SWX2SENT`/reporter
   words establish XNU entry; if it stops at `S1`, fix the display path
   before blaming XNU.
4. Restore `boot_a` from `shim/out/boot_a-live-restore-trim.img` (SHA256
   `a0d33cfa174920eb8da48c78bb956dc40d6345689a24e38f8700addf2c2d2183`),
   `oem reboot-recovery`, then verify the complete 64 MiB partition hashes
   to `2931647a56039722ea2585990b8ef3b1a2daf4c9b990231879f753049eaf86b1`.

A second diagnostic build is ready but **not flashed**: `b0e6197727eaecce…`
adds the always-on `SWX2SENT` summary and falls back to the measured matisse
display bases (`0x14017000`/`0x14001000`/`0x14004000`/`0x14000000`) when the
live-FDT lookup fails; every existing state guard is still enforced.

**Update after the first three hardware boots (19:30):**

- `d2960f10…` (gzip, log_store enabled) booted, showed the LK/Redmi logo
  and stayed. After a forced fastboot entry, a 262,144-byte `oem lkmsg`
  dump contained **no** `SWX2` bytes at `0x1000`, `0x10000` or `0x30000`.
  The shim therefore stopped at the first `log_store` access in
  `diag_early`, exactly like the earlier `logstore` entry probe. The
  log-store path is now opt-in (`-DDIAG_LOGSTORE`) and off by default.
- `3e3814a9…` (raw Image, 18,128,896 B, log_store off) rebooted instead of
  staying at the logo. A stable logo means the shim reached
  `wdt_disable_raw()`; a reboot means it did not. Raw Image entry is not
  usable on this LK for this payload; do not use `--raw` without a control.
- `0e6e62b6…` (gzip, 7,008,256 B, log_store off, early OVL read guarded,
  OVL scanout adoption) booted and remained alive for more than 37 s with
  no USB enumeration and no reset. The operator's panel report is pending.
  Since the watchdog stays disabled only after `wdt_disable_raw()`, this
  boot certainly reached C.
- `expdb` after the failed boot contains LK's
  `boot linux-64 via EL2, pc=0x40000000, x0=0x47c80000, mode=0x3c5`
  and no shim/XNU records. That is expected: the shim has no expdb writer.
- `expdb` also still contains the old `SWTX1` banner from the live
  `boot_a` wrapper, so it is not a per-boot record.

**Next control:** re-run the exact validated display probe
`shim/out/entryprobe-display-kick-hw-ok.img` (20,836,352 B, SHA256
`b8cec21a912dc978b7b78fddd343253e9a93b95b3d91e275bca0fe0bc0eeee3f`).
If the panel shows its test screen and moving bar again, the panel/LK state
is healthy and the full shim's display path is the fault. If it does not,
the LK display handoff state changed and the probe's recorded state must be
re-measured before any XNU display work.

`boot_a` currently contains `0e6e62b66f3246fadd5de23a70e54ff74148ab59a150e38eb0e4a058e1f863f9`,
not the live backup. Restore it before any non-test boot.

**UFS/expdb partition-log probe (`939e4875…`, 7,004,160 B, gzip):** built
with `-DDIAG_UFS_LOG`. After the console/display probe it calls `test_ufs()`
(prints CAP/HCS/HCE/UTRLBA/claim/TUR/CAPACITY and the big GPT partitions),
then `ufs_log_write("expdb", blocks - 32, con_text(), len)`, which writes a
`SWLG` header and the console text eight blocks before the end of `expdb`,
then halts. The image was flashed and booted; no USB appeared within 20 s.
The panel state was not reported. Read the result from recovery:

```sh
adb exec-out 'dd if=/dev/block/by-name/expdb bs=1M 2>/dev/null' > expdb.bin
truncate -s 134217728 expdb.bin
python3 tools/shimlog.py --file expdb.bin --scan   # prints "SWLG at 0x..."
```

`tools/shimlog.py --scan` was added for this. If `SWLG` is absent, the MTK
UFS host takeover (`ufs_ready()`/`claim_host()`) failed before the write; the
panel `test_ufs` lines, if visible, carry the failing register state. The
`SWLG` text is the console text up to the probe, so it also carries the
display-stage result.

`fastboot oem dump_pllk_log` returned only `INFO` lines from
`mi_get_lock_state` and no `DATA` payload in this test, unlike
`oem lkmsg`, which returned `DATA00040000`. Do not treat `dump_pllk_log` as a
working text channel until its response framing is measured.

The bounds-checked PL/LK writer (`shim/logstore.c`, `/chosen/log_store` at
`0x11df00`, 64 KiB, header `0xabcd1234`/`0xcdab3412`) has not been retried
after the earlier probe hung; that probe likely wrote past the 64 KiB buffer
at `+0x3ff00`. A retry must stay inside the `off_lk + sz_lk` region and use
`/proc/pl_lk` (same Linux boot) or a measured fastboot dump.

**Process correction (observed):** sending `fastboot oem reboot-recovery`
while a test image is still in `boot_a` does **not** enter recovery; the
phone ends up at the logo with no USB and no fastboot. The required order is:
Power+VolumeDown to fastboot, flash
`shim/out/boot_a-live-restore-trim.img`, then `oem reboot-recovery`. The
expdb `SWLG` block, if the UFS write succeeded, survives that reset; RAM
log_store and sentinels do not.

**Fastboot-only expdb read:** this LK also registers `oem expdb` and contains
`read_expdb`/`deflateInit2` strings. Try
`tools/fbraw.py oem expdb OUT.bin` in fastboot before restoring; it may
return a compressed expdb image (decompress with zlib) and would avoid the
recovery boot entirely.




## >>> SESSION 2026-10-22 - device recheck before next XNU attempt <<<

**Read-only hardware check:** The connected Redmi K50 Pro is already in
Recovery (`ro.bootmode=recovery`, slot `_a`). A fresh 64 MiB read of
`boot_a` has SHA256
`2931647a56039722ea2585990b8ef3b1a2daf4c9b990231879f753049eaf86b1`, matching
`backup/recovery-20261021/boot_a-live-20261021.img`. The original/live `boot_a`
is therefore already restored; no flash was needed for this check. `vendor_boot`
is also 64 MiB, but was not read or changed. No partition was written.

The user clarified that the handset cannot enter Recovery while a temporary
shim/test image remains in `boot_a`: restore the original `boot_a` first, then
request `reboot-recovery`. Keep this as the required cleanup sequence after
every hardware test. Reconfirmed this turn: Recovery ADB reports slot `_a`,
root access, and a 67,108,864-byte `boot_a`; a fresh full readback (discarding
the recovery `dd` tool's 79-byte stdout trailer) hashes to
`2931647a56039722ea2585990b8ef3b1a2daf4c9b990231879f753049eaf86b1`, exactly
matching the full restore backup. No partition was written. Host currently
sees Recovery over ADB and no fastboot device; do not infer the handset is in
fastboot from the earlier report.

**Host-only rebuild check (2026-10-22):** The NDK 28.2.13676358 LLVM tools
were put on `PATH`; `bash shim/build.sh out/matisse-xnu.payload --template
../backup/recovery-20261021/boot_a-live-20261021.img` completed. The resulting
boot-v4 image is 7,004,160 bytes with SHA256
`8b4a6986111d6d75363b83ff429faf83c8bcdf33b084cb0edcd57e9e0aefb943` (same
bytes as the already-tested candidate), inflated Image 16,859,648 bytes,
embedded-payload marker offset 253,952, and embedded payload length 16,605,680.
The generic ramdisk matches the original boot image byte-for-byte. All 26
`tools/tests` unit tests pass. This rebuild adds no new hardware evidence and
was not flashed; no XNU startup success is established.

**Next:** instrument the next boot-v4 test to leave distinct visible checkpoints
after payload discovery, segment copy, boot_args/ADT setup, and immediately
before the XNU branch. Add a minimal earliest-entry XNU checkpoint before
`arm_init`; for this command-mode panel it must use the known-good MT6983 DSI
refresh sequence rather than only changing framebuffer memory. First run all
host layout/range/build checks. Hardware validation must remain temporary
`boot_a` only, with full partition readback before the test and full 64 MiB
restore + hash verification afterward.

## >>> SESSION 2026-10-22 - embedded XNU hardware attempt (read first) <<<

**Outcome / evidence:** The user reported that the embedded-payload candidate
stayed at the first boot screen without progress, then manually entered
fastboot. The candidate was `shim/out/shim-boot.img`, SHA256
`8b4a6986111d6d75363b83ff429faf83c8bcdf33b084cb0edcd57e9e0aefb943` (7,004,160
bytes; boot-v4; CI XNU payload 39640336293). Only the first 7,004,160 bytes of
`boot_a` were written. Before reboot, a full 67,108,864-byte readback matched
the predicted SHA256 `4f876b7ba93a95cde1f8bb8cb54a97abec68920ea2591f1a73ed7650dc2726f9`.
ADB did not return during a 131-second watch. This proves the candidate did not
reach recovery/ADB; it does **not** prove whether XNU entry was reached.

`fastboot oem lkmsg` returned 256 KiB, but its contents are the known stale
Android log buffer and are not evidence from this attempt. The candidate
therefore has no trustworthy same-boot XNU trace. User-visible shim output was
previously reported, but the exact final on-screen line for this image was not
captured. Do not claim that the new payload path or XNU entry has passed.

**Recovery completed:** In fastboot, `tools/fbraw.py flash boot_a
shim/out/boot_a-live-restore-trim.img` succeeded. The 20,832,256-byte trimmed
image was verified byte-for-byte as a prefix of the full 64 MiB backup (SHA256
`a0d33cfa174920eb8da48c78bb956dc40d6345689a24e38f8700addf2c2d2183`). Then
`reboot-recovery` returned OKAY. In recovery, the complete `boot_a` readback
SHA256 is `2931647a56039722ea2585990b8ef3b1a2daf4c9b990231879f753049eaf86b1`,
matching the full backup. Current slot `_a`, current mode recovery. No
`vendor_boot`, userdata, GPT, bootloader, modem, persist, or calibration
partition was written.

Evidence files are under
`research/matisse/20261022-embedded-payload-test/` (gitignored): stale LK dump,
fastboot command logs, and recovery dmesg after restore. That recovery dmesg
shows the restored old `SWEET-ENTRY v1` wrapper executing; it is only a restore
control, not the candidate boot.

**Next:** The embedded image's shim path still needs an unambiguous on-screen
handoff/early-XNU marker or a same-boot persistent trace before another blind
reflash. Existing XNU early framebuffer marks (patches 0082/0083) begin after
XNU enters `arm_init`; the next diagnostic should expose the earliest possible
XNU entry stage and refresh that marker on the MT6983 command-mode panel. Keep
the test limited to temporary `boot_a`, and fully restore/hash it after each
run. XNU startup remains unproven; do not change `vendor_boot` or userdata.

## >>> SESSION 2026-10-22/23 - XNU/display bisection (read first) <<<

**2026-10-22 XNU payload delivery update (host only):** User reports that
shim output is visible, but XNU does not start; no current screen text/photo
or XNU boot trace was supplied, so the exact failing stage is not measured.
The previous boot-v4 image appended 16,605,680 raw payload bytes directly to
boot.img's 1,250,233-byte compressed **generic** ramdisk. That placed the
`SWEETXNU` magic at offset 1 modulo 8, which the loader's 8-byte-step scan
cannot find if the ramdisk is copied at its measured 8-byte-aligned base;
whether MTK LK also discards the raw compressed-stream trailer is unknown.
Recovery's ramdisk lives in `vendor_boot` and was not modified.

A new boot-v4 path embeds the payload after the shim Image's 4 KiB-aligned
`_end`, with `SWEETAPP`+u64 length metadata; it enlarges the ARM64 Image
header and leaves boot.img's generic ramdisk byte-identical to the verified
backup. `loader.c` reads the embedded payload directly and bounds-checks
segments and ADT before the XNU jump; the old boot-v2 initrd path is retained.
The jump message now pushes an MTK frame and waits ~200 ms before handoff.
Host build `shim/out/shim-boot.img`: 7,004,160 B, SHA256
`8b4a6986111d6d75363b83ff429faf83c8bcdf33b084cb0edcd57e9e0aefb943`;
inflated Image 16,859,648 B; marker offset 253,952; embedded payload exactly
matches `shim/out/matisse-xnu.payload` (SHA256 `df778ce8...ae19e`, from
successful XNU CI run 39640336293). 26 host unit tests pass, the full shim
cross-build passes (pre-existing unused `reset()` warning), and the separate
entry-probe XNU build still cross-compiles from the original stock template.
**No new image was written to the phone, and XNU remains untested on hardware.**
Next: obtain explicit confirmation for a **boot_a-only** temporary test; read
back the full partition after writing and restore the complete 64 MiB backup
SHA256 `2931647a...86b1` after the result. Do not write `vendor_boot`, userdata
or GPT. The prior notes about display regression are earlier observations;
request the exact screen text from the user's visible shim run if the XNU
stage remains unclear.

**Device state:** `boot_a` restored to the verified live image
`backup/recovery-20261021/boot_a-live-20261021.img`; full 64 MiB readback
SHA256 `2931647a56039722ea2585990b8ef3b1a2daf4c9b990231879f753049eaf86b1`
matches. No other partition was written. The live image is itself an old
`SWEET-ENTRY v1` probe wrapper around the stock kernel (same ramdisk, 2 MiB
prefix); it boots Android/recovery normally.

**2026-10-22 read-only preflight:** recovery ADB enumerates with root;
`blockdev --getsize64 /dev/block/by-name/boot_a` reports 67,108,864 bytes.
A fresh full-device `adb exec-out dd` read confirms SHA256 `2931647a...86b1`
for the first 67,108,864 bytes, identical to the local verified restore image.
This recovery’s `dd` appends 79 bytes of transfer statistics to **stdout**,
not stderr: never hash the untrimmed ADB output as a partition image.
The original kick image and local restore image also match their recorded
hashes. No partition write or control boot was performed in this preflight.
Await explicit authorization before writing the kick image to `boot_a`;
this LK does not implement temporary `fastboot boot`.

**2026-10-22 same-boot execution control (no partition write):** rebooted the
existing, restored `boot_a` directly back into recovery. ADB returned after
23.4 seconds; its new-boot dmesg contains a `SWEET-ENTRY v1` banner at
`[0.000000]`. All fields in the matching boot-image banner are initially
zero; the live banner has nonzero stage/register fields, confirming the
**currently installed entry-probe shim still executes** in this boot. Raw
log is gitignored at
`research/matisse/20261022-shim-control/recovery-existing-boota-dmesg.txt`.
This is not a test of the newer full shim, screen refresh or XNU. Host-side
comparison shows that the validated `display-kick` image and later normal
`display-kick` build have identical unpacked stock-kernel regions, but
13,866 bytes differ within their 2 MiB prefix; this alone cannot tell
whether the build changed behavior or the recovery panel state changed.
A fresh hardware control with the exact validated image remains the next step.
The 64 MiB restore backup contains nonzero data past the 20,836,352-byte
probe image (32,202 nonzero bytes); restore and hash the **full** 64 MiB,
not just a trimmed prefix. The expected full-partition hash during a probe
write, if the existing tail is preserved, is
`016331b382ae2c88c668931c8feaa448c42f48948b440fdb7b83b455853b97a7`.

**New measured facts:**

- `fastboot oem lkmsg` holds a stale previous-Android kernel ring, not the
  current recovery boot. It is not a same-boot log channel.
- The device's own `/lib/modules/mtk_wdt.ko` (pulled, SHA256
  `f41c25ad...`) gives the MT6983 AP-watchdog protocol: base `0x1c007000`,
  MODE bit0 enable, key **`0x22000000`** (`movk w10,#0x2200,lsl#16` in
  `mtk_wdt_stop`), PING at `+0x08` = `0x1971`. Stock dmesg reports
  `mtk-wdt 1c007000.watchdog: Watchdog enabled (timeout=31 sec)`.
- Shim execution is proven: a clean shim built with `MINIMAL_PROBE` (prints
  then halts) resets on a **~45 s** USB/preloader period, while a shim that
  calls PSCI reset at entry resets on a **~9.7 s** period. The former is the
  31 s watchdog after halt; the latter is immediate. The shim therefore does
  execute on MTK LK.
- The display path regressed in this session. The exact validated kick image
  `shim/out/entryprobe-display-kick-hw-ok.img` (20,836,352 B, SHA256
  `b8cec21a912dc978b7b78fddd343253e9a93b95b3d91e275bca0fe0bc0eeee3f`) is
  retained, but newly built `xnu`-level probes (with and without payload),
  the clean shim, the permissive-clock shim, the forced-push shim and
  RAW_PAINT all showed only logo/black and reset when booted from recovery.
  The validated image has not yet been re-run as a control; do not conclude
  the recovery-mode display state from the new builds.
- Appending the 16.6 MB XNU payload directly after the gzip stock ramdisk
  makes a 37.4 MB boot image; the hybrid `entryprobe-xnu.img` did not display.
  A valid ramdisk or separate-partition payload channel is still needed.
- `persist_mark` (write to `0x00d01100+0x3ff00`) is now compiled out unless
  `DIAG_MARK`; it was present in every failing diagnostic build.
- `DIAG_MARK`/`WDT_HALT`/`WDT_NO_TOUCH`/`RAW_PAINT`/`RAW_RESET` are still
  uncommitted working-tree diagnostics. Record the macro used for any image.

**Next concrete action:** with explicit authorization, test the new
embedded-payload `shim/out/shim-boot.img` on `boot_a` and record the final
visible loader/XNU line before recovery restoration. If the user-reported
visible shim is not reproducible for this new build, first rerun the exact
validated display-kick image `b8cec21a` as a display control. Keep each
partition write separately authorized and verify full restoration.

## >>> MATISSE PORT (Redmi K50 Pro, MT6983) - handoff 2026-10-22 <<<

### DISPLAY REFRESH PROVEN ON HARDWARE 2026-10-22

**The panel now refreshes from the LK-handoff state.** A same-boot shim probe
(`shim/entryprobe_display.c`, level `display-kick`) enabled the DSI engine and
pushed command-mode frames: the operator saw the test screen and a moving
green bar change on the phone, then the device returned to recovery in the
same boot. This is the first verified screen-log path on matisse.

Two hardware runs, temporary `boot_a` writes only, each read back fully:

1. Read-only probe `shim/out/entryprobe-display-v3.img` (20,836,352 B,
   SHA256 `76a2c57fce82feb238c9b9e96e4894e905f159a5036a054f1eccd5c434ca42e1`)
   ran from a temporary `boot_a` and returned to recovery. Raw dmesg:
   `research/matisse/20261021-live/entryprobe-display-v3-dmesg.txt`.
2. Refresh probe (validated build) `shim/out/entryprobe-display-kick-hw-ok.img`
   (20,836,352 B, SHA256 `b8cec21a912dc978b7b78fddd343253e9a93b95b3d91e275bca0fe0bc0eeee3f`)
   showed new frames on the panel. Raw dmesg:
   `research/matisse/20261021-live/entryprobe-display-kick-v3-dmesg.txt`.
   Recovery dmesg has **0** `ovl status error` and **0** CMDQ timeouts, so the
   corrected restore leaves the next kernel's display init healthy (unlike the
   old direct-trigger experiment).
3. `boot_a` was restored from `backup/recovery-20261021/boot_a-live-20261021.img`
   (the exact pre-test live image, SHA256
   `2931647a56039722ea2585990b8ef3b1a2daf4c9b990231879f753049eaf86b1`); the
   full 67,108,864-byte readback matches. Note the live image differs from the
   older `boot_a-stock.img`; the live one is now the restore source.

**Measured LK handoff (read-only, live FDT, `SWTX1` record):**

| Block | Value |
| --- | --- |
| DSI0 CON_CTRL / MODE_CTRL | `0x0` / `0x0` (engine off, command mode) |
| DSI0 START / INTSTA | `0x1` / `0x4` (TE_RDY set; panel sending TE) |
| DSI0 TXRX_CTRL / PSCTRL | `0x0001023c` / `0x2c0505a0` (4 lanes, DSC, 1440-byte lines) |
| DSI0 SIZE_CON / VACT | `0x0c8001e0` / `0xc80` (3200x2x720 DSC) |
| DSI0 MEM_CONTI / BUF_CON0 | `0x3c` / `0x1` (cmd-mode buffer enabled) |
| DSI0 BUF_CON1 / RW_TIMES | `0x0dfd00b1` / `512000` |
| DSI0 LCCON / LD0CON | `0x001f1f01` / `0x8` (HS clock on) |
| MIPI PLL_PWR / CON0 | `0x1` / `0x9cec4ec4` (PLL running at 1.36 GHz) |
| clock gates 0/1/2 status | `0x0` / `0x0` / `0x0` = **all enabled** (MTK status bit 0 = on) |
| OVL0_2L EN / L0_ADDR / pitch | `0x00e00001` / `0xfcb3f000` / `5760` |
| OVL0_2L SRC_CON / SRC_SIZE0 | `0x1` / `0x0c8002d0` (720-wide slices) |
| disp_mutex0 EN / SOF | `0x0` / `0x0` (stopped) |
| disp_mutex0 MOD0 / MOD1 | `0x004ffff5` / `0x202` (OVL1_2L, DSC0, DSI0 present) |
| GCE threads 3/5 | idle (`CURR_STATUS`/`WAIT_TOKEN` 0) |

**Validated minimal refresh:** LK has already done panel rails/reset, the DSI
PHY PLL/HS clock, DSC/PPS and the command-mode buffer. No panel power/reset,
PHY, DSC or GCE programming is needed to show new pixels — the OVL is still
scanning `boot_args.Video`. The shim sequence that worked:

1. Require clock gates DSI0/DSI_CLK/OVL0_2L enabled, DSI command mode, DSC
   PSCTRL, expected SIZE_CON/VACT, BUF_CON0 bit0, OVL enabled at the boot
   framebuffer with the boot stride, and TE_RDY.
2. `DSI_PHY_LCPAT=0x55`, `DSI_PHY_LCCON |= 1`, clear the stale TE flag.
3. Wait for TE_RDY (W0C: write `~TE`), then `MUTEX_CFG=0`, `MUTEX_EN=0`,
   `MUTEX_EN=1`, `DSI_START=1`.
4. Repeat for each frame; disable the mutex when stopping.

`INTSTA` bit4 (FRAME_DONE) **never asserted** on the command-mode path even
though the panel refreshed; completion cannot be polled there. Pace refreshes
by time instead. Do not repeat the old mutex+START-only experiment that
skipped the clock/DSC/buffer preconditions.

**XNU port (patch 0083, compiled locally, not yet booted):**
`osfmk/arm64/sweet_matisse_dsi.c` validates the same handoff state and issues
the same sequence; `pexpert/arm/pe_serial.c` calls it from `fbcon_probe` and
after each drawn character; `mkadt.py --board matisse` now emits a
`sweet-display` node (`reg=<0x14000000 0x18000>`, panel
`l11_38_0a_0a_dsc_cmd`). Local CI-flag syntax/object compile of both files
passes. Patch applies cleanly after 0082. Next: CI build, then temporary
`shim-boot.img` test (needs explicit user confirmation).

**XNU CI + image (2026-10-22):** GitHub Actions run **39640336293** on
`Jinsens/ios-sweet` branch `codex/matisse-xnu-screen-log` completed
**success** (first two runs failed on missing header export, then on `SWEET`
not being defined without `pexpert/arm64/board_config.h`; both fixed).
Kernel `xnu/out/ci-39640336293/kernel.development.sweet`: 17,222,800 B,
Mach-O `arm64`, SHA256
`bc308789486ee96b380ce374bc7fe4c1894f4a115da9662b4cb0cf9a016b543c`.
Linked symbols `_sweet_display_init` and `_sweet_display_refresh` present.
Payload `shim/out/matisse-xnu.payload`: 16,605,680 B, SHA256
`df778ce8960ad2b8f4fed21103fb9e78d7fe630627e21c5155fadf0fdccae19e`
(ADT 4456 B with `sweet-display`; cmdline `debug=0xc serial=3 cpus=1
keepsyms=1 sweetkeys=0 sweettouch=0 sweetbattery=0 sweetusb=0 ufsrw=0
-noprogress`). Boot image `shim/out/shim-boot.img`: v4, 17,883,136 B,
SHA256 `f60e9af968f71cb60bf3da8d5d34d1cb6e757f39f3c6b7a99fea444b3ca3c163`.
**Not flashed or booted.** Booting it is the next hardware step and needs
explicit confirmation; recovery is Power+VolDown to fastboot, then restore
`backup/recovery-20261021/boot_a-live-20261021.img` and read back.

**Tooling:** `tools/mkentryprobe.py --level display-kick` (guarded writes,
21-field compact `SWTX1` banner; field `k` = stage<<16|code) and
`tools/decode-display-probe.py [--kick]`. The record fits the 407-byte Linux
banner exactly. `tools/xnu-cc.py` now honors `XNU_CC`.

## >>> MATISSE PORT (Redmi K50 Pro, MT6983) - handoff 2026-10-21 <<<

### ACTIVE UPDATE 2026-10-21 - XNU built; frame-trigger still blocks visible logs

**CURRENT DEVICE STATE:** the user most recently reported the handset is in
fastboot. A host query on 2026-10-21 using fastboot 37.0.0 saw zero visible
devices, so the present USB/device state is not independently confirmed. The
last verified state was OrangeFox recovery with `boot_a` fully restored from
`backup/boot_a-stock-trim.img`. Entire 67,108,864-byte partition readback
`backup/recovery-20261021/boot_a-final-after-all-probes.img` byte-matches
`backup/boot_a-stock.img`, SHA256
`7a6a462d5e8858c6f7ecd77655363dd84964d44ea6e7c239e961632996a96e94`.
No test image remains installed. No userdata, vendor_boot, LK/preloader,
GPT or calibration writes were performed. This is the preserved known-good
(possibly Magisk-patched) backup, not a newly verified pristine vendor image.

**Completed implementation commits:** `3021f5a` (same-boot entry/FDT/MMU/timer
probe + logging safety), `8a31ac8` (actual IRQ/EOI + guarded matisse
ADT/payload), `6cbbcbe` (XNU Boot_Video early framebuffer mapping), and
`2cf0290` (read-only display snapshot probe, FDT parser fixes and build fix).

**CURRENT MILESTONE 2026-10-21:** working branch
`codex/matisse-xnu-screen-log`. Patch 0082 removes early Qualcomm framebuffer
physical-address/geometry assumptions and derives the surface from
`boot_args.Video`; the final TTBR1 alias walks the new XNU root, maps visible
pixels only, handles up to two 32MiB blocks and refuses a bad/colliding
surface. Normal fbcon validates the surface dimensions.

GitHub Actions run **39595694178** (head `bfd7eb60fe0602f85bfc81bc33a18b4f23c03505`)
completed **success** on 2026-10-21. Kernel artifact:
`xnu/out/ci-39595694178/kernel.development.sweet`, Mach-O plain `arm64`
(not arm64e), 17,206,200 bytes, SHA256
`911db7b3c3616face11ccc730869e12ccf0c72ba5efaee8f3eedd01af7cfc367`.
Payload built with measured matisse ADT and safe one-core/no-device-driver
boot args: `xnu/out/ci-39595694178/matisse-xnu.payload` (16,605,200 B).
Boot-v4 test image also built:
`shim/out/shim-boot.img` (17,883,136 B, original recovery ramdisk plus payload).
It has **not been flashed**; XNU has not yet been booted on hardware.
`/product` is missing from the local Apple D22AP ADT, generator warns/omits it.

Validation: all five early-console Mach-O units syntax/object compiled against
successful run 39158169212's build tree; 11 instruction-level actual-assembly
mapping cases passed. Whole existing 81-patch series applied to Apple
xnu-8796.141.3; new patch applies and CI built/linked it. These do not prove
hardware MMU behavior or screen output.

**LATEST HOST MILESTONE 2026-10-21 (commit `4b05707`):** the read-only `display` probe now
separates FDT/register-window lookup status from the raw register values. The
old `ffffffffffffffff` mutex fields were ambiguous because the same value was
also used as the lookup-failure sentinel. Host-decoding the saved live DTB
resolves `/disp_mutex@14001000` with register windows `0x14001000` and
`0x14401000`; this is a DTB parse result, not proof of live MMIO contents. The
new snapshot records a two-bit status for each register pair, reads both
mutex windows, and snapshots GCE display trigger-loop threads 3 and 5
(CURR_STATUS/WAIT_TOKEN) using their live-FDT base. This remains read-only;
no display/clock/PHY/GCE writes were added.

All seven entry-probe levels cross-compile against the stock v4 template;
all 21 Python tests pass and `git diff --check` is clean. The rebuilt v2
read-only display probe is `shim/out/entryprobe-display-v2.img` (20,832,256 B,
SHA256 `a0d33cfa174920eb8da48c78bb956dc40d6345689a24e38f8700addf2c2d2183`);
it has **not** been transferred, booted or flashed. Fastboot reported zero
visible devices, so no hardware probe result is available for this milestone.
The append-only log-store host ASan/UBSan test previously passed. Rebuilt
`shim/out/shim-boot.img` from the CI XNU payload and stock template: v4,
17,883,136 bytes, SHA256
`9300e166763b4ba69e85fa17867156f24cfa1d0ec9b1fa961e0515c1efe761cf`.
None of these images has been written to the phone.

**DISPLAY BLOCKER, now measured:** read-only entry probe saw DSI0
CON_CTRL=0 (DSI_EN clear), MODE_CTRL=0 (command mode), START=1,
INTSTA=4, CMDQ_SIZE=0x8001, SIZE_CON=0x0c8001e0. OVL0_2L reports
L0_ADDR=`0xfcb3f000`, L0_PITCH=`0x1680` (5760), EN=`0x00e00001`;
the ordinary OVL0 L0 address was zero. The probe reached stage 15 without an
exception, but the final mutex fields were `ffffffff`; because the v1 probe
used that same bit pattern for FDT/range lookup failure, those two fields do
not establish the actual mutex register values. Do not claim mutex state from
that snapshot. DSI framebuffer stores alone are not a validated
panel refresh path.

A one-shot DSI/mutex/start experiment was stopped. The subsequent recovery
dmesg contains 129 CMDQ “SW timeout Pre-dump” records and repeated waits on
token 641; the stock baseline has none. The Xiaomi MT6983 GCE header names
641 `CMDQ_SYNC_TOKEN_STREAM_EOF` (a software sync token, not a DSI-TE event).
The sequence and timeouts correlate, but causation is not isolated; it did not
provide verified visible text. Do NOT repeat direct DSI_START/DSI_EN toggles.
The panel compatible is `l11_38_0a_0a_dsc_cmd,lcm`; the vendor driver has a
WQHD DSC command table plus rail/reset, DSI/PHY and display-pipeline setup.
That initialization/refresh path is not ported to XNU. The ignored local
source snapshot `research/matisse/panel-l11-38-0a-0a-dsc-cmd.c` matches the
live compatible and contains the WQHD 1440x3200 DSC PPS/DCS init table; its
prepare path sequences VDDI (`vaud18`), DVDD GPIO 193, VCI (`vibr`), then
reset GPIO 86. The init callback is separate from prepare. The corresponding
DT/driver/GCE material is in ignored `research/matisse/mt6983.dts`,
`research/matisse/mtk_dsi.c`, `research/matisse/mtk_drm_crtc.c`, and
`research/matisse/mt6983-gce.h`; the GCE header distinguishes DSI0 TE event
358 from software STREAM_EOF token 641. These are source observations, not a
validated XNU port. There is no validated screen-log path yet.

**NEXT CONCRETE ACTION:** when the phone is again visible in fastboot, run the
read-only `shim/out/entryprobe-display-v2.img` via temporary `fastboot boot`
(not `fastboot flash`) and collect the same-boot Linux banner from recovery.
Decode `display_status` before interpreting any all-ones register pair. If
that probe returns normally, use its mutex/GCE values to begin a source-driven
XNU panel/DSI/DSC port. No DSI_START/DSI_EN toggles; use the real DSI0 TE
hardware event rather than software STREAM_EOF. The v2 image has not yet been
run on hardware.

GitHub CLI is installed in ignored research/host-tools. Upstream is read-only;
`Jinsens/ios-sweet` fork was created for CI. XNU branch commit has not been
merged upstream. Before any further temporary `boot_a` write, obtain explicit
user confirmation per device procedure. No userdata, GPT, vendor_boot, LK,
preloader or calibration partitions were written.

**Additional completed host work:** `mkadt.py --board matisse`: one A510
(affinity=0), 13MHz, PPI27, GICD 0xc400000/size0x40000, GICR
0xc440000/size0x200000, fb 0xfcb3f000/1440x3200/stride5760, kernel RAM
0x100000000+0x12e000000, no Qualcomm UFS node. Retains iPhone10,3/D22AP
and logical 1125x2436 canvas. Not a generic daumier profile. `mkpayload.py`
recognizes it and rejects conflicting/truncated boot-args, requiring
cpus=1/sweetkeys=0/sweettouch=0/sweetbattery=0/sweetusb=0/ufsrw=0.
13 host unit tests PASS, existing sweet/QEMU profiles tested unchanged.
Apple /product ADT is missing locally; generator warns and omits that node.

**Hardware results:**

| Probe | Stage/fault | Observation |
| --- | --- | --- |
| entry | 1 / 0 | EL1, MIDR0x410fd462, MPIDR0x81000000, CNTFRQ13MHz, DTB0x47c80000, SCTLR0x30d00980 |
| board | 2 / 0 | Actual shim board_probe discovers GICD0xc400000, PPI27, fb0xfcb3f000 |
| mmu | 5 / 0 | Actual shim/mmu.c enables 16KiB granule, rc0, AT succeeds; SCTLR0x30d01985 |
| timer | 7 / 0 | Redist0xc440000, GICD_CTLR0x12; ISTATUS and PPI27 pending asserted after ~100us |
| irq | 9 / 0 | **Actual IRQ entry/EOI PASS**: rc0, count1, last INTID27; returns to recovery |
| display | level 15 / no fault | Read-only DSI0 snapshot: CON_CTRL=0, MODE_CTRL=0, START=1, INTSTA=4; OVL L0_ADDR=0xfcb3f000, pitch=5760. Mutex fields unresolved in this probe; no writes attempted. |
| logstore | no Linux result | FAIL to return; isolated extra direct PL/LK memory-access path, root cause unknown |

Every successful probe handed back to the preserved original Linux kernel
within the SAME boot and returned to recovery. Each flashed prefix was
read back fully and matched first. IRQ test saves/restores modified GIC
and timer state; timer-only stage leaves CPU DAIF masked. IRQ probe SHA256
`961f9a260d7dffd2e267b08102a8cb6ca53461d2c76b9a50a4318261128e77f5`
(20,832,256 bytes). Exact raw dmesg logs, readbacks and source/layout/hash
manifests are gitignored under `research/matisse/20261021-live/` and
`shim/out/entryprobe-{entry,board,mmu,timer,irq}.{img,json,elf}`.
MMU image SHA256 cabdfa644bfaa3b0514fad5e2fae44469e8e2e56c9a38e21c8808c2f7d14bbb2;
timer image SHA256 c8d5c402126d9a699cca197b00cb5559d0cae0563b7d466c62f949db834d5a2b.

**Safety fix:** old dram_log() wrote text INTO the packed 256-byte
log_store header (including pointer/signature). New writer is append-only,
validates bounds/overflow/tag length and needs a live FDT-provided header;
ASan+UBSan host cases PASS. Nonetheless direct log_store access is NOT
hardware-working: normal dram_log and markers are disabled unless explicitly
SHIM_LOGSTORE_MARK. Raw partition logs and misc BCB writes are opt-in only
via SHIM_STORAGE_LOG. Stop relying on a warm-reset PL/LK log reader.

Fresh backup set (read-only) at `backup/recovery-20261021/manifest.json`:
boot_a, vendor_boot_a, dtbo_a, lk_a/b, vbmeta_a/b, misc, persist,
nvcfg/nvdata/nvram, protect1/2, seccfg. Fresh live DTB (410,235 bytes),
stock dmesg, PL/LK log, partitions and iomem in the live research directory.
Host FDT reader passes on this live tree under ASan/UBSan. Complete shim
cross-build passes (pre-existing unused reset() warning only); C ABS64
relocation check passes. No Apple artifact/device dump/serial is tracked.

Local toolchain: installed Android NDK
`/Users/xiaohuasheng/Library/Android/sdk/ndk/28.2.13676358/toolchains/llvm/prebuilt/darwin-x86_64/bin`.
ADB/fastboot:
`/Users/xiaohuasheng/Library/Android/sdk/platform-tools/{adb,fastboot}`;
USB needs escalated access. `tools/fbraw.py` works around LK's macOS
platform-tools pipe error. Prefer `adb devices -l` then direct exec-out:
`adb wait-for-device` sometimes remains waiting although recovery enumerates.
The linked kernel/boot probes and same-boot diagnostic format are documented
in `docs/matisse-bringup.md`.

All device-state summaries and experiments BELOW are historical and
superseded by this section; in particular the old bootloop snapshot is NOT
current.

### UPDATE 2026-10-21 late - log channel found, phone needs stock boot restored

**Device state right now:** `boot_a` contains the instrumented shim
(`shim/out/shim-boot.img`, log_store marker build, `EXTRA_CFLAGS=-DSHIM_LOGSTORE_MARK`).
The phone bootloops on it and does not enter recovery from the `misc`
`boot-recovery` BCB; it is currently not enumerating on USB. Restore with
`fastboot flash boot_a backup/boot_a-stock-trim.img` after Power+VolDown.
The stock image is intact; nothing else was written.

**Why the marker test is still unproven:** the shim writes a valid append into
the **pl_lk log_store buffer** (`dram_buf_header.buf_addr` = 0x7ffbf000 from
the 256-byte header at `/chosen/log_store` = 0x00df1100). `fastboot oem lkmsg`
dumps a **different** 256 KiB buffer (the kernel/UART `klog`, all Android
`dmesg` text), so absence of `SWEET-SHIM` there proves nothing. `/proc/pl_lk`
in recovery is the right reader.

**Verified log_store layout** (recovery `/proc/pl_lk`, live header):
- sram header sig 0xabcd1234 at 0x00df1100; packed DRAM buffer address at +0x14,
  size at +0x1c; `pl_lk_log` at +0x40: sig 0xcdab3412, buff_size 0x40000,
  off_pl **0x400**, sz_pl, off_lk = 0x400 + sz_pl, sz_lk.
- The PL/LK text is clean. `oem lpmsg` returns 0x10000 bytes; `oem lkmsg`
  returns 0x40000 bytes of the kernel log, not the PL/LK sections.
- `shim/logstore.c` appends `SWEET-SHIM <tag> a=... b=...\n` at
  `buf + off_lk + sz_lk` and bumps sz_lk, guarded by the sig and bounds.

**Fastboot on macOS:** platform-tools 34.0.5 and 37.0.0 both fail with
`could not clear input pipe ... usb_read failed e00002e8` after sending a
command to this LK, even for `reboot`; `fastboot devices` still works.
`tools/fbraw.py` (pyusb + libusb) speaks the protocol directly and **works**:
`oem lkmsg` returned exactly 0x40000 bytes and `reboot-recovery` returned
OKAY. Use it for all local fastboot operations.

**BCB caveat:** writing `boot-recovery` into misc block 0 from recovery did
not make LK boot recovery after the shim reset; the phone kept booting
`boot_a`. Do not rely on that loop for log retrieval until the MTK boot-mode
selection is understood.


**Goal:** run the same iOS bring-up on the user's Redmi K50 Pro (`matisse`,
MT6983 / Dimensity 9000, 8 GB, 1440x3200, UFS 3.1). Everything below was
measured on the device or read out of its own firmware, not from datasheets.

### Device state right now (safe)

- `boot_a` is **byte-identical to `backup/boot_a-stock.img`** (verified with
  `adb exec-out dd`, sha256 `ba4255e2...`). Android boots normally; OrangeFox
  recovery boots (`adb reboot recovery`). Nothing else was written.
- `misc` command block is zero (no pending boot-recovery), `oops` is zero.
- The Magisk-patched stock boot is the backup: kernel 19,610,141 B gzip ->
  46,848,116 B `ARMd`, ramdisk 1,250,233 B lz4 (vs 1,380,091 B in the
  firmware package - that difference is Magisk).

### Device facts

| Item | Value | Source |
| --- | --- | --- |
| Product | `matisse`, 22011211C, board `mt6983` | getprop |
| Bootloader | MTK LK (`lk_a` 2.8 MB), `verifiedbootstate=orange` | `lk.img`, getprop |
| boot.img | header **v4**, kernel **gzip**, ramdisk **lz4**, 4096 B signature block, AVB footer (SHA256_RSA2048) | `boot.img` |
| vendor_boot | header v4, dtb 335,112 B, `vendor_ramdisk` lz4, tags/dtb 0x47c80000 | `vendor_boot.img` |
| `fastboot boot` | **NOT SUPPORTED** - LK's command table is download/flash/erase/getvar/oem/set_active only | `lk.img` strings |
| Recovery | lives in **vendor_boot**; there is no recovery partition | TWRP BoardConfig, partitions |
| RAM | `/memory` 0x40000000 + 8 GiB; carve-outs up to 0x22e000000 | live FDT |
| Usable window | 0x100000000 .. 0x22e000000 (4.72 GiB) | live FDT |
| GIC | GICv3, GICD **0x0c400000** (0x40000), GICR **0x0c440000** (0x200000) | live FDT `/interrupt-controller` |
| Timer | CNTFRQ **13 MHz**, virt PPI 11 -> INTID **27**, phys 14 -> 30 | live FDT `/timer` |
| UFS | `ufshci@112b0000`, `mediatek,mt8183-ufshci`, Samsung KLUDG4UHGC-B0E1 | live FDT, sysfs |
| Framebuffer | base **0xfcb3f000**, vramSize **0x34c0000** (3 frames), panel 1440x3200 | `/chosen/atag,videolfb*` |
| Panel | `nt36672e_fhdp_dsi_vdo_120hz_jdi_dphy_drv`, **DSC command mode** | `/chosen/atag,videolfb-lcmname` |
| Touch | FocalTech `fts@0` on SPI6 0x11016000, IRQ GPIO 8, reset GPIO 3 | live FDT |
| Keys | MT6363 (`spmi@1c015000/pmic@4/mt6363keys`), power 116, home 115 | live FDT |
| Battery | MT6375 charger+gauge at I2C 0x11e01000 | live FDT, dmesg |
| USB | MTU3 + xHCI 0x11201000 / 0x11200000 (not DWC3) | live FDT |
| DRAM logs | `ram_console` 0x00d01100 (512 KiB), `log_store` 0x00df1100 (256 B) | `/chosen` |

### What was built (all committed)

The shim is now **board-generic**: `shim/board.c` reads the framebuffer, GIC,
timer PPIs, UFS base, RAM, initrd and the DRAM log buffers out of the **live
FDT**; per-board constants are only fallbacks.

- `shim/fdt.c` - real FDT walker: path lookup with a match stack, multi-entry
  `reg`, string lists, `compatible` search. **Verified on the dumped matisse
  tree** (`shim/host_board.c`: board matisse, fb 0xfcb3f000/0x34c0000,
  gicd 0xc400000, gicr 0xc440000, virt 27, ufs 0x112b0000, dram 8 GiB,
  initrd 0x66f00000..0x6aa514be, lcm name). Two real bugs found that way:
  `~3UL` truncates on Windows/LLP64, and "/" must be zero path components.
- `shim/start.S` - drops EL2 -> EL1 (LK may enter at EL2), sets VBAR_EL2
  early, and turns off a bootloader-left MMU before any C runs.
- `shim/loader.c` - finds the payload by scanning the initrd for `SWEETXNU`
  (MTK concatenates boot.img and vendor_boot ramdisks).
- `shim/console.c` - parameterized geometry, `con_redraw` to repaint into
  another scanout buffer, keeps a text copy for the log channels.
- `shim/ufs.c` - parameterized by the board's UFS base; partition read/write,
  `ufs_mark` progress blocks, `ufs_log_write`.
- `shim/shim.c` - stage markers (`mark()`), DRAM log (`dram_log()`), boot to
  recovery via the `misc` BCB, halt instead of reset on panic.
- `tools/mkbootimg.py` - packs header v2 (ABL) and v4 (LK) from a stock
  template, keeping the signature block; `shim/build.sh` gzips the kernel when
  the template's is gzip and builds with clang+lld (Windows/MSYS2 works:
  `PATH=/d/msys2/ucrt64/bin:$PATH EXTRA_CFLAGS=... bash build.sh --template ...`).
- `tools/avbtool.py` (LineageOS copy, patched for Windows `os.urandom`),
  `tools/shimlog.py`, `tools/matisse-flash.sh`.

### What the hardware did (the important part)

1. **LK accepts our image and jumps to our code.** Proof: a 92-byte stub
   kernel (`shim/out/reset_stub.bin`, just `smc PSCI_SYSTEM_RESET`) makes the
   phone blink and reboot instantly, while the stock image sits on the logo.
2. **The panel is not a usable output.** Every shim build (full, minimal,
   no-clear) shows only the logo, then the watchdog resets. The panel is
   command-mode DSI with DSC: LK pushes one frame into the panel's GRAM and
   stops, so framebuffer writes never appear. `atag,videolfb-islcm_inited`
   is 0 in a normal boot. **Do not spend more time on the framebuffer until
   something drives the DSI command queue.**
3. **UFS writes from the shim never land.** `ufs_mark`/`ufs_log_write` into
   `oops` and `boot_a`+4 MiB left the blocks zero. Either the MTK host is
   gated after LK (clocks/power) or our UTRL takeover fails; the marker
   records HCS/HCE/UTRLBA/UTRLRSR so a successful run would show which.
4. **DRAM logs are the promising channel.** `fastboot oem lkmsg` really does
   dump text (it printed the previous kernel's console), and `oem lpmsg`
   returns OKAY. The 04:11 build wrote plain text into `log_store` and
   `ram_console` and `lpmsg` came back empty - so either the shim never
   reached `shim_main`, or `lpmsg` parses a header we did not write.

### Next experiment (start here tomorrow)

Bisect between `_start` and `shim_main` with the DRAM channel, no C:

1. In `start.S`, as the **first** instructions after saving x0, write a magic
   word + a byte counter to `log_store+0x80` and `ram_console+0x100`, then
   `smc` reset. Boot it, `fastboot oem lkmsg` / `oem lpmsg`.
2. If nothing: the write itself is the problem (address wrong, or the buffers
   are re-initialised by LK after the jump). Then read the `log_store` header
   format out of `lk.img` (`oem lkmsg` prints `DATA%08llx` chunks - the dump
   path probably walks a ring header).
3. If it works: move the marker forward one step at a time (after bss zeroing,
   after `board_probe`, after `con_clear`, after `mmu_enable`, after
   `test_gic`, after `test_ufs`) and the first missing marker names the fault.
4. Only then fix the real blocker (likely the UFS host: compare the MTK
   `ufshcd-mtk` probe sequence in the vendor kernel, or keep LK's list and
   issue commands through it).

### Operational rules learned the hard way

- **Always flash a trimmed image.** `fastboot flash` of a 64 MiB file wedges
  LK's USB stack ("Write to device failed (no link)"); trimming to the AVB
  `original_image_size` (or just the real size) works every time. Re-entering
  fastboot needs Power + Volume Down by hand.
- **`adb shell 'dd ...' > file` corrupts binaries on Windows** (CRLF). Use
  `adb exec-out` for every pull; `adb push` for writes.
- Recovery is in `vendor_boot`, so a broken `boot_a` does not cost recovery:
  `fastboot reboot recovery` still works, and `fastboot flash boot_a
  backup/boot_a-stock.img` (trimmed) restores normal boot.
- The device's own firmware package is at
  `D:/am/matisse_images_OS2.0.2.0.ULKCNXM_20250401.0000.00_14.0_cn_7623fe2c93/`
  (boot.img, vendor_boot.img, dtbo.img, lk.img, preloader, scatter).
- The TWRP/OrangeFox device tree at `D:/twrp/` has the MTK bootctrl layout
  (`bootctrl/boot_control_definition.h`: BCB at misc block 0, magic
  `0x42414342` in `slot_suffix`) and the working vendor_boot repack scripts.


## Agent handoff / active work (2026-10-15, latest)

### >>> UPDATE 2026-10-18 (read first, then the 10-17 handoff below) <<<

**STATE at end of 2026-10-18 (evening):**
- On the phone: userdata = **image v15** (`/run/media/dipa/android/ios-sweet-ipsw/ios16-root-20H392-v15.img/.simg`; = v14 + `/private/var/preferences/SystemConfiguration/preferences.plist` with one network service "USB Ethernet": Interface DeviceName ue0 Type Ethernet, IPv4 Manual 192.168.7.2/24 router 192.168.7.1, DNS 1.1.1.1 8.8.8.8, set "Automatic" as CurrentSet). Fallback image v14 (v12/v13 deleted).
- Kernels: **0078** = all 8 cores (`cpus=8`, cpu6/7 = A76, homogeneous SMP; mkadt now emits 8 CPU nodes; ADT `shim/out/sweet-0078hi.adt`); **0079** = display off/on via IOMFB selector 12 kern_RequestPowerChange(state) (fade over 6 vsyncs, then black; verified: power button gives "SWEET FB: display off/on"); **0080** = `SWEET NET: <proc> route add/delete/change ...` and `... add/delete address ...` trace (built, `shim/out/shim-boot-0080s.img`, NOT booted yet).
- **Internet over USB: not working yet.** Host side is ready (temporary iptables: FORWARD accept for 192.168.7.0/24 + MASQUERADE, comment "ios-sweet"; lost on host reboot). With v15 the phone sent no DNS and no outbound traffic (only mDNS/ARP) -> configd probably did not apply the service (or did, without default route/DNS). Next: boot 0080s on v15, watch `SWEET NET` lines (does configd add 192.168.7.2 / default route on ue0?). If configd ignores ue0 (not an IOKit IONetworkInterface; configd 1241.140.6 source in `research/configd-1241`, SCNetworkInterface createInterface needs IONetworkInterface -> controller (IOMACAddress, SelfNamed) -> bus), add IOKit stand-ins and/or rename the ifnet to en*.
- Live log listener (`nc -ukl 5140`) may still be running, writing `logs/live-0078s.txt`.

**LIVE LOG over USB (0077, boot 0077s): no more recovery round-trips.** Boot an image with `sweetusb=2`, run `tools/sweet-usbnet.sh logs/live-NAME.txt` on the PC: it waits for the phone's CDC-ECM interface, sets 192.168.7.1/24 (sudo) and prints/saves the kernel console the phone streams every 100 ms as UDP to 192.168.7.1:5140 (starts with the last 64 KiB). `ping 192.168.7.2` checks the link. Current image: `shim/out/shim-boot-0077s.img` (kernel 0077, ADT sweet-0069hi, cpus=6, sweetfb_noconsole=1, sweetfb_hz=30, sweetusb=2). The recovery pull (`tools/sweet-log-pull.sh`) is still the way after a panic/hang before USB comes up.

**🎉 USB networking works (boot 0076s, 18:24 local): `ping 192.168.7.2` from the PC answers in ~1 ms, 0 % loss (200-packet burst, 1500-byte frames, 512/1024-byte frames).** 0075: CDC-ECM function (bulk 0x81/0x01, interrupt 0x82 NETWORK_CONNECTION; host MAC 02:00:5e:77:ee:01) + kernel ethernet ifnet `ue0` (legacy output, header strip like if_fake) with 192.168.7.2/24 set from the kernel (proto_plumb + SIOCAIFADDR on an in-kernel socket). 0076: received frames into one cluster mbuf (mbuf_allocpacket gave a first mbuf of length 0 -> panic "Failed mbuf validity check: len -14"). Host side (Linux cdc_ether, interface `enp0s20f0u3u1`): `nmcli dev set IF managed no; sudo ip addr add 192.168.7.1/24 dev IF; sudo ip link set IF up`. Boot image `shim/out/shim-boot-0076s.img` (`sweetusb=2`). iOS itself does not see ue0 yet (configd needs an IONetworkInterface in IOKit).

**USB device mode works (boot 0074s, 17:45 local): the host enumerates the phone at high speed as `1209:0001 ios-sweet "Sweet iOS (USB bring-up)"`.** 0072 read-only probe: ABL leaves the USB30_PRIM GDSC and all 7 USB clocks on, DWC3 v3.20a (GSNPSID 0x5533320a) in device mode (GCTL 0x00112000), halted (DCTL RUN_STOP 0, DSTS 0x00d3de04), event buffer still at ABL's 0xfdfc8000, QUSB2 PHY alive. 0073 (`sweetusb=2`): DCTL soft reset, own event buffer (polled, interrupt masked), ep0 DEPSTARTCFG/SETEPCONFIG/SETTRANSFRESOURCE, setup TRB, RUN_STOP; control-transfer state machine as Linux ep0.c; descriptors: vendor class, no data endpoints. It ran but no event came: **0074** forces the VBUS session in the Qualcomm wrapper (QSCRATCH 0xa6f8800: HS_PHY_CTRL |= UTMI_OTG_VBUS_VALID(20)|SW_SESSVLD_SEL(28), SS_PHY_CTRL |= LANE0_PWR_PRESENT(24), as Linux dwc3_qcom_vbus_override_enable) -> connect + enumeration. Image `shim/out/shim-boot-0074s.img`. Black Phone app: main thread waits in -[VMVoicemailManager fetchAccounts] (sync XPC; voicemail needs the modem).

**Navigation works (boot 0071s on v14, log `logs/boot-0071s.txt`):** swipe up from the bottom edge returns to the home screen; app switcher works. Two fixes: **0070** pid_hibernate (syscall 435 was nosys on the macOS config -> SIGSYS killed SpringBoard in -[SBToAppsWorkspaceTransaction _didComplete] when an app left the foreground; the only CONFIG_EMBEDDED-only entry in syscalls.master); **0071** touches starting within 48 px of an edge carry kIOHIDDigitizerEventFromEdgeTip (UIKit `_UIEventHIDTouchEdgeTypeForHIDEvent` reads the digitizer EventMask 0xb0007 bits 0x800/0x1000/0x2000/0x40000). Diagnosed, not fixed: Settings (Preferences) SIGTRAP in PodcastsUI func_1cdc47c58: force-unwrap of `URL.volumeTotalCapacity` (nil on our HFS+ root). Phone/Photos/Messages show black (MobilePhone launches, no crash) - next: stack samples via boot-arg `sweetsample=MobilePhone,MobileSlideShow,MobileSMS,SpringBoard` (image `shim/out/shim-boot-0071s.img`).

**🎉🎉 MILESTONE 2026-10-18 ~15:30 local: iOS 16.7 SPRINGBOARD HOME SCREEN ON THE PHONE** (boot `shim/out/shim-boot-0069s.img` = kernel 0069 + ADT `shim/out/sweet-0069hi.adt`, image **v14**; log `logs/boot-0069s-v14-HOMESCREEN.txt`). Home screen with a few apps, Settings opens, Control Center / lock screen / notification center work, touch + buttons work, 6 A55 cores (`cpus=6`), `sweetfb_noconsole=1 sweetfb_hz=30`. Known issue: cannot leave Settings (home gesture / AssistiveTouch home do nothing) - to investigate.
What it took today (in order): 0058 HID services (Apple IOHIDFamily-1915 user client), 0059 iPhone X identity (hw.product etc.), 0060 SPMI keys + GENI touch, 0061 1125x2436 presented display, 0062 RPMh L11C touch power + IOPMPowerSource battery, 0063 GENI FIFO packing (Goodix GT9896), 0064 PRIV_WORK_INTERVAL grant (SpringBoard "Failed to create work interval"), 0065 SMP via PSCI (6 A55), 0066 crash map regions, 0067 console mute without cons_ops write, 0068 IOSurface lookup of an already-mapped surface returns base -1 (backboardd snapshot crash), 0069 UFS log flush 10 s. Image v13: CommCenter removed from launchd.plist, BKNoWatchdogs. **Image v14** = v13 + Setup skipped (`/var/mobile/Library/Preferences/com.apple.purplebuddy.plist` SetupDone/SetupFinishedAllSteps true, SetupVersion 11, daemonizeNeedsToRun false; purplebuddy.notbackedup mini-buddy flags false; managedconfiguration.notbackedup LockdownActivationIndicatesCloudConfigurationAvailable false; springboard MCForceShowCloudConfigurationUI false) + mobileactivationd data ark seeded (`/private/var/containers/Data/System/D90C94C4-F94E-4FCF-8A28-A93BE3846D8E/Library/internal/data_ark.plist`, -ActivationState Activated etc.) + MediaToolbox D22/D221/Default SubServerConfiguration StartRecorderServer=false (mediaserverd crash loop: portrait-filter prewarm called NULL GL). **Activation:** ADT /chosen certificate-production-status 0, effective-production-status-ap 0, certificate-security-mode 1, effective-security-mode-sep 1 -> mobileactivationd's native Hactivation branch (Codex `codex/activation/report.md`; alternative 4-byte daemon patch documented there). Fallback image v13; v12 deleted.

**🎉 TOUCH WORKS (boot 0063u on image v13, 2026-10-18 ~13:15 local):** tapping (i) on Setup's Hello opens the device-info sheet; swipe-up is recognised (spinner, then back to Hello - under investigation). Chain: RPMh L11C vote (0062, `bsd/dev/sweet_rpmh.c`) -> GT9896 @0x5d on GENI SE7 (0063 fixed FIFO packing: register address went out byte-swapped) -> sweet_hid_touch -> SweetHIDTouch -> backboardd. Battery icon OK (0062 SweetBattery IOPMPowerSource, static 100 %). **Image v13** (= v12 + CommCenter jobs removed from launchd.plist + `BKNoWatchdogs`=true and `FBLaunchWatchdogExceptions{com.apple.purplebuddy:100}` in /var/mobile/Library/Preferences/com.apple.springboard.plist): Setup no longer killed by the scene-create watchdog (it blocked in CoreTelephony getSubscriptionInfo -> CommCenter, Codex `codex/setup/report.md`; that report also lists how to skip Setup: SetupDone/SetupFinishedAllSteps/SetupVersion=11 in com.apple.purplebuddy.plist + activation check). v9 deleted, fallback = v12. Input latency ~1 min with 1 CPU -> Codex task 11 = SMP via PSCI (`codex/smp/`).

**INPUT WORKS (boot 0060u on a freshly flashed v12, log `logs/boot-0060u.txt`):** power, volume up, volume down reach iOS (PMIC -> sweet_keys.c -> SweetHIDButtons -> backboardd). Power locks/unlocks (screen "off" shows the kernel console because the panel never really turns off). **Device identity fixed: iPhone X** (home indicator, Face-ID-style Setup). Earlier test (0059u, `sweethidtest=15` fake Home presses) advanced Setup from Hello to the language list.
- **0058** HID: `iokit/Kernel/arm/hid/`: IOHIDEventServiceUserClient + IOHIDEventServiceQueue + IOHIDEvent compiled UNCHANGED from Apple IOHIDFamily-1915.140.3 (= exact version of the iOS 16.7 IOHIDLib, clone in `research/iohid-1915`) over our minimal IOHIDEventService (SweetHID.cpp: SweetHIDButtons consumer page 0x0C power 0x30 / vol 0xE9/0xEA / menu 0x40; SweetHIDTouch digitizer collections). C hooks `sweet_hid_key(key, down)` (0 power, 1 vol+, 2 vol-, 3 home) and `sweet_hid_touch(finger, down, x, y)`. HID logs go to IOLog. Boot-arg `sweethidtest=N` = fake Home press every N s.
- **0059** identity: hw.machine/hw.model/hw.target/hw.product from the ADT (macOS-config kernel used to answer "iPad8,6"/"Redmi Note 10 Pro"). mkadt: root compatible `D22AP|iPhone10,3|xiaomi,sweet|...`, model iPhone10,3, target-type D22, `/product` copied from the real D22AP device tree (`research/ipsw-x/d22ap.adt`, extracted from the IPSW, NOT in git), `/buttons home-button-type 2`. Codex report `codex/mg/report.md`: MG ProductType = sysctl **hw.product** (unrecognized -> iPod), HWModelStr = hw.target, HomeButtonType = `/buttons/home-button-type`; disk cache `/private/var/containers/Shared/SystemGroup/systemgroup.com.apple.mobilegestaltcache/Library/Caches/com.apple.MobileGestalt.plist` (keyed by build + UUID only -> stale iPod answers survived; reflashed clean v12 to clear it).
- **0060** drivers by Codex (`codex/input/hw-report.md`): `bsd/dev/sweet_keys.c` (SPMI arbiter v5 observer reads, PON 0x810 bits KPDPWR/RESIN SID0, PM6150L GPIO2 SID4 0xc110; works), `bsd/dev/sweet_touch.c` (GENI SE7 I2C @0xa84000, starts 45 s after boot). Touch result: SE7 fw ok (proto 3) but **0x5d and 0x38 both time out -> touch IC unpowered** (L11C LDO needs an RPMh vote). Codex task 8 = RPMh client (`codex/rpmh/`), task 7 = battery (`codex/battery/`).
- **0061** (CI 39117078444): red status bar "rdar:45025538" = UIKit "No status bar visual provider for screen" (360x800 pt is no real iPhone). AppleCLCD now presents **1125x2436** (iPhone X) and shows the centered 1080x2400; touch mapped the same; ADT canvas 1125x2436. `sweetfb_native=1` reverts.
- Images: `shim/out/shim-boot-0060b.img` (0060 + /buttons ADT `sweet-0060hi.adt`). Next: 0061 image with ADT from current mkadt.

### >>> HANDOFF 2026-10-17 late (read this first) <<<

**STATE: iOS 16.7 Setup.app "Hello" screen is ON THE PHONE** (boot `shim/out/shim-boot-0057u.img` on image v12). Photo `/run/media/dipa/android/ios-sweet-work/MILESTONE-setup-hello-2026-10-17.jpg`. SpringBoard + backboardd + Setup run; nothing crashes in the GUI path. Remaining crash/relaunch loops: installcoordinationd (should be fixed by 0057, unverified), mediaserverd (VirtualAudio removed in v12, unverified), mobileactivationd (~100/boot, not analysed), bluetoothd + fairplayd.H2 relaunch constantly (no hardware).

**What is on the phone now:** userdata = image **v12** (`/run/media/dipa/android/ios-sweet-ipsw/ios16-root-20H392-v12.img` + `.simg` + `.sha256`; v9 kept as fallback, v8/v10/v11 deleted or superseded). Kernel **0057** (`xnu/out-0057`, CI `39067532732`). ADT **`shim/out/sweet-0057hi.adt`** (QEMU twin `research/q0057-hi.adt`). Boot image **`shim/out/shim-boot-0057u.img`**. Boot args: `debug=0xc serial=3 cpus=1 keepsyms=1 -enable_kprintf_spam -noprogress rd=ufsroot0 unentitled_ios_sim_launch=1 ignition_level=1 wdt_test=no_user_checkin ufsrw=1 rootrw=1 launchd_unsecure_cache=1 wdt=-1`.

**Build a phone image** (kernel K, ADT A): `python3 tools/mkpayload.py $K $A shim/out/payload-X.bin --cmdline "$B" && (cd shim && ./build.sh ../shim/out/payload-X.bin && cp out/shim-boot.img out/shim-boot-X.img)` then check `python3 tools/unpack_bootv2.py shim/out/shim-boot-X.img shim/out/check-X && cmp shim/out/check-X/ramdisk shim/out/payload-X.bin`. QEMU smoke test: `python3 tools/mkpayload.py $K research/q0057-hi.adt $S/csq/payloadX.bin --ramdisk $S/csq/root-fork.img --cmdline "debug=0xc serial=3 cpus=1 keepsyms=1 -enable_kprintf_spam -noprogress rd=md0"` + `PATH=~/swift/usr/bin:$PATH python3 tools/qemu-sweet.py ... --secs 40 --kernel $K --fail-on-panic` (S = scratchpad; root-fork.img lives in the session scratchpad csq/ dir and may be gone in a new session).

**Kernel workflow:** edit `research/bt28/xnu/...` (keep the pre-edit copy in `research/preNNNN/`), syntax check `python3 tools/xnu-cc.py research/run28.log research/bt28 <file>`, make `xnu/patches/NNNN-*.patch` with `diff -u pre bt28 | sed` path rewrite, add new/changed files to `research/check-patch-order.py` list, run it (must say applied + MATCH), commit + push -> GitHub Actions `xnu` builds (~8 min) -> `gh run download <id> -R dipa-studio/ios-sweet -n xnu-kernel -D xnu/out-NNNN`. **Repo is PUBLIC since 2026-10-17** (private macOS runner minutes ran out: "recent account payments have failed"); public = free runners. Commit trailer: only `Co-Authored-By: dipa-studio <183933817+dipa-studio@users.noreply.github.com>`.

**Phone workflow (user does buttons, Claude runs commands):**
- Boot test kernel: phone in fastboot -> `fastboot boot shim/out/shim-boot-X.img`. NEVER `fastboot getvar`.
- **Read logs WITHOUT filming:** after a test the user holds Power+VolDown -> fastboot -> `fastboot boot recovery/recovery.img` (OrangeFox, temp) -> wait for `adb shell true` -> `tools/sweet-log-pull.sh /run/media/dipa/android/ios-sweet-work/logs/<name>.txt` (reads the 4 MiB console ring the kernel keeps in the last 1025 blocks of userdata; patch 0047). Then `adb reboot bootloader` brings the phone back to fastboot without the user.
- **Flash a root image:** `fastboot flash -S 512M userdata <img>.simg` (7 min, 25 chunks). After a big flash the Xiaomi ABL fastboot hangs: next `fastboot boot` stalls at "Sending" -> the USER must re-enter fastboot by hand (Power+VolDown). Do not retry commands against the hung ABL. A flash right after `adb reboot bootloader` once failed on chunk 1 (USB protocol error): just retry. User must NOT unplug during flash (once interrupted at 25/25 -> reflash).
- **Edit the phone root without reflashing (same-length only):** find the file's raw offset in the local image (it is one extent; search the image for its first 4 KiB), compare with `adb exec-out dd if=/dev/block/sda34 ...`, then `adb push` changed 4 KiB blocks and `dd of=/dev/block/sda34 seek=... conv=notrunc,fsync`, read back. Recovery kernel has no hfsplus.
- **Pull the whole phone root** (12 min): `adb exec-out "dd if=/dev/block/sda34 bs=1048576 count=16384" > img`; mount ro with udisksctl or `sudo mount -t hfsplus -o loop,ro`. To write into a pulled image: `sudo fsck.hfsplus -fy` first (volume is never cleanly unmounted -> Linux mounts ro even with -o force), then `sudo mount -t hfsplus -o loop,force`.
- Making images: copy latest img with `cp --sparse=always`, mount rw with force, change, `sync; umount`, `sha256sum`, `img2simg`. Keep only the latest image + one fallback on the SSD (/home is ~98% full; big work files live in `/run/media/dipa/android/ios-sweet-work/`, old kernels/images archived in `.../ios-sweet-work/archive/`).

**Diagnostics built into the kernel (all SWEET-only):** persistent console log (0047, boot-arg sweetlog=0 off; flush every ~1 s); `|name| text` copies of /dev/null writes for processes in `sweetnull` (default backboardd,SpringBoard; 0048); `IOK name:` IOKit lookup/open trace for `sweetiolog` (default backboardd,SpringBoard; 0049/0054, 400 lines max); `SWEET Sandbox: proc op N` (0050); `STR ...` heap text dump on SIGABRT/SIGTRAP for `sweetscan` (default backboardd,SpringBoard; 0051/0053) - this is how NSException/BSAssert reasons were found; `SMP name tN pc .. bt ..` user stack sampler for `sweetsample` (default SpringBoard,backboardd; first at 90 s then every 120 s, 40 samples, 16 frames; 0054/0055); `SWEET FB: N swaps` every 1000 swaps; `CRASH name ...` crash reports (0043/0044). Symbolicate cache addresses with `ipsw dyld a2s research/dsc/dyld_shared_cache_arm64 <addr - slide>`; main-binary addresses: addr - mh + 0x100000000.

**Patches added today (0046-0057, all CI-built):** 0046 IOSurface (IOCoreSurfaceRoot) + IOMobileFramebuffer (AppleCLCD on /arm-io/disp0) + arm-io nubs; 0047 persistent log; 0048 /dev/null tee; 0049 IOKit trace; 0050 permissive "Sandbox" MAC policy; 0051/0053 heap text on crash; 0052 RENAME_SWAP via exchangedata on HFS; 0054/0055 sampler, swap counter, AKS selectors 35 (extended device state = 17) and 101; 0056 panel copy from the vsync timer at 10 Hz (sweetfb_hz) instead of every swap; 0057 no config_ext_resolver (ACL group entries resolve without memberd). ADT (tools/mkadt.py): /arm-io/disp0, /chosen/display-scale 3, /chosen/unique-chip-id (synthetic 0x5357454554000001) + chip-id 0x8015 -> IOPlatformUUID A9683613-3704-53F2-95D0-98A8FB574E78. Image v9-v12: /private/var/containers/{Bundle,Data/System,Shared/SystemGroup,Temp}; launchd.plist StandardOut/ErrorPath renamed to ...PatX (pointing jobs at /dev/console stops them launching: EACCES); v12: LastSystemVersion=20H392 in plain /var/mobile/Library/Preferences/com.apple.migration.plist (stops the 1-hour data migration that ran every boot), VirtualAudio.plugin moved to /Library/Audio/Plug-Ins/HAL.disabled/.

**Codex helper** (`codex exec --skip-git-repo-check -m gpt-6.1-sol -c model_reasoning_effort=high -s workspace-write -C /run/media/dipa/android/ios-sweet-work/codex -o OUT "$(cat task.md)" < /dev/null`, run detached with setsid nohup; config already defaults to gpt-6.1-sol high). Reports in `/run/media/dipa/android/ios-sweet-work/codex/`: mediaserverd-report.md, installcoordinationd-report.md (-> 0057), ufs-performance.md (ranked UFS speed plan), **ufs/0058-sweet-ufs-faster.patch** (READY, not yet applied: ufslogsecs default 10 s log flush batching, optional ufscache=1 directional cache ops, optional ufswait=1 spin-then-sleep; syntax-checked, host-stub verified; see ufs/README.md). Apply it as patch 0058 after review.

**Claude safety-classifier note:** several messages about QuartzCore renderer selection / writing an HFS reader tool were cut off by an automatic classifier (false positives, user agrees). Keep those topics short or let them be; they are not blockers now (rendering already works).

**NEXT STEPS (in order):**
1. **Input** (Setup stuck on Hello): touch + power + volume as IOHIDEventService/IOHIDDevice services backboardd matches (log shows backboardd matching IOHIDDevice with DeviceUsagePairs and IOService with HIDServiceSupport=true). Phone hardware: Goodix/Focaltech touch over I2C/SPI (check live DT `dtb/`), buttons via PMIC (pon) and GPIO keys. Start with a fake HID service (e.g. power button via a timer or boot-arg) to learn the ABI, then real drivers.
2. **Device identity**: MobileGestalt reports iPod + Home button. Add /product node / product-type (iPhone10,3, D22AP), device class iPhone, home-button-less (Face ID) properties in mkadt; find exact MG keys (MGIOMFBSupport.c, `IODeviceTree:/product` lookups seen in backboardd trace).
3. **Battery**: AppleSmartBattery/IOPMPowerSource style service (status bar shows empty red battery).
4. Apply Codex 0058 (UFS speed), consider cpus>1, check whether installcoordinationd/mediaserverd loops are gone, analyse mobileactivationd.
5. Hide kernel console over the GUI when not debugging: boot-arg sweetfb_noconsole=1 (but then panics are not on screen).

- **🎉 MILESTONE: iOS GUI ON THE PHONE - Setup.app "Hello" screen (2026-10-17 ~21:30 UTC, boot 0057u on image v12).** Photo: `/run/media/dipa/android/ios-sweet-work/MILESTONE-setup-hello-2026-10-17.jpg` (animated "dobar d(an)" hello lettering, status bar "iPod" + battery icon, bottom "Pritisnite Home za otvaranje" = "Press Home to open" (locale hr), (i) button). Rendered by iOS 16.7 SpringBoard/Setup through CoreAnimation -> backboardd -> kernel IOSurface (IOCoreSurfaceRoot) -> kernel AppleCLCD swaps -> ABL panel memory. What made it: data migration finally skipped (v12: `LastSystemVersion` 20H392 in the plain `/var/mobile/Library/Preferences/com.apple.migration.plist`; ADT `/chosen/unique-chip-id` + `chip-id` for IOPlatformUUID), 0057 (no ext resolver -> ACL containers work), plus everything before (0046 display/IOSurface, 0050 Sandbox policy, display-scale 3, containers dirs, RENAME_SWAP, AKS 35/101, 10 Hz present).
  **Missing (next work, in rough order):**
  - **Input: no touch, no power button, no volume buttons** (no HID drivers; backboardd looks for IOHIDDevice / HIDServiceSupport services). Setup is stuck on "Hello".
  - **Device identity: it thinks it is an iPod with a Home button** (status bar "iPod", "Press Home to open"): MobileGestalt has no product/model identity (no /product node, product-type, etc.) - give it iPhone10,3 / home-button-less (Face ID class) identity.
  - **No battery detection** (no battery/charger/PMIC service; status bar battery shows empty/red).
  - Locale came up Croatian (hr) - harmless.
  - Performance: cpus=1, polled UFS (Codex UFS patch in progress: `codex/ufs/`), backboardd presents at 60 Hz.
- **README refreshed (2026-10-17):** read the full notes and updated the public overview through patch 0045, v7 hardware observations and prepared v8 diagnostics. Documents real Apple userspace, the missing display/IOSurface GUI work, limited security services, highmem, persistent userdata root, current tooling and build examples. Documentation only; no kernel build, tests, flashing or phone boot performed.

- **v11 still migrated (boot 0056u, 20:32 UTC, `logs/boot-0056u-v11.txt`).** On iOS kCFPreferencesCurrentHost lands in the plain plist: all DMEnvironment setters (setLastBuildVersionPref, setUserDataDispositionPref, ...) use CurrentHost and the phone's `/var/mobile/Library/Preferences/com.apple.migration.plist` holds DMUserDataDisposition; datamigrator's XPC service runs with `_RoleAccount: mobile`. **Image v12** = v11 + `LastSystemVersion` = 20H392 added to that plain `com.apple.migration.plist` (keeps DMUserDataDisposition, 501:501 0600) + `/Library/Audio/Plug-Ins/HAL/VirtualAudio.plugin` moved to `/Library/Audio/Plug-Ins/HAL.disabled/` (Codex: stops the mediaserverd SIGSEGV loop; untested). **installcoordinationd loop explained (Codex `codex/installcoordinationd-report.md`):** os_crash "Failed to create data directory" EACCES for `/private/var/containers/Shared/SystemGroup/systemgroup.com.apple.installcoordinationd/Library/InstallCoordination`: `Library`/`Library/Caches` in the container are ACL-only (uid/gid 0xfffffffe, mode 0000, ACE for group GUID ...012B = gid 299 systemusers); with `config_ext_resolver` the kernel asks an identity resolver (memberd/opendirectoryd) that iOS does not run -> EWOULDBLOCK -> ACE skipped -> EACCES. **Patch 0057**: drop config_ext_resolver from FILESYS_BASE (compatibility UID/GID<->GUID mapping is used instead), likely fixes other ACL-protected containers too. Codex task 3: UFS driver performance design (`codex/ufs-performance.md`).
- **mediaserverd SIGSEGV loop explained (Codex report `/run/media/dipa/android/ios-sweet-work/codex/mediaserverd-report.md`):** the fault (FAR 0x390) is in the HAL plug-in `/Library/Audio/Plug-Ins/HAL/VirtualAudio.plugin/VirtualAudio` (ApplyBeamFormerPreference <- VirtualAudio_PlugIn::SetPropertyData <- HALS_AHPPlugIn::ObjectSetPropertyData <- AudioObjectSetPropertyData <- MediaExperience vaemVADSerializationListener): the default virtual audio device ('vdef', VirtualAudioDevice_Default) does not exist (no audio hardware/driver, no /product/audio). Proposed workaround for GUI bring-up: move VirtualAudio.plugin out of /Library/Audio/Plug-Ins/HAL/ in the next root image (untested). v11 reflashed OK after an interrupted flash (USB unplugged at chunk 25/25). Codex task 2: installcoordinationd crash loop.
- **ROOT CAUSE of the endless migration: no IOPlatformUUID (2026-10-17).** datamigrator's `-[DMMigrator isMigrationNeededWithBuildVersion:lastBuildVersion:clientPID:]` gets lastBuildVersion from `-[DMEnvironment lastBuildVersionPref]` = `CFPreferencesCopyValue("LastSystemVersion", "com.apple.migration", kCFPreferencesCurrentUser, kCFPreferencesCurrentHost)` -> a ByHost file. The phone had `/var/mobile/Library/Preferences/com.apple.migration.plist` (only DMUserDataDisposition) and NO `Preferences/ByHost` directory at all. On arm XNU publishes IOPlatformUUID (gethostuuid) only from `/chosen/unique-chip-id` (8 bytes) + `/chosen/chip-id` (4 bytes) (IOPlatformExpertDevice::generatePlatformUUID, called from IOPlatformExpert::start); the SWEET ADT had neither, so every CurrentHost preference write failed. Fix: mkadt adds `unique-chip-id` = 0x5357454554000001 (synthetic) and `chip-id` = 0x8015 -> UUID `A9683613-3704-53F2-95D0-98A8FB574E78` (same SHA1 namespace computation as the kernel). ADT `shim/out/sweet-0057hi.adt`, boot image `shim/out/shim-boot-0056u.img` (0056 kernel + 0057hi ADT, QEMU OK). **Image v11** = v10 + `Preferences/ByHost/com.apple.migration.<UUID upper and lower>.plist` {LastSystemVersion: 20H392} (501:501, dir 0755 files 0600). Flashing v11 2026-10-17 ~20:10 UTC. Codex (gpt-6.1-sol high) analysing the mediaserverd SIGSEGV loop in `/run/media/dipa/android/ios-sweet-work/codex/` (report `mediaserverd-report.md`).
- **v10 did NOT stop the migration (boot 0056n on v10, 19:18 UTC, `logs/boot-0056n-v10.txt`):** datamigrator + migrationpluginwrapper ran again, backboardd drew the progress UI (13000+ swaps in ~5 min). So `com.apple.DataMigration.plist`/LastSystemVersion is not the deciding input. What is known about the decision (datamigrator XPC service `DataMigration.framework/XPCServices/com.apple.datamigrator.xpc/com.apple.datamigrator`, strings): `Migration sentinel present. Migration necessary.` (sentinel `/private/var/datamigrator/migrate`, created and removed by datamigrator itself; absent in v10), `System build version changed from %@ to %@. Migration necessary.` / `...unchanged... not necessary`, `Disposition dictionary with build version %@ is out of date relative to current build version %@`, `SyntheticDidUpgrade`, DMUserDataDispositionManager; previous build source not found yet (not in the binary's plain strings; likely in DataMigration.framework's DMUserDataDispositionManager / preferences domain `com.apple.migration`). backboardd calls `DMPerformMigrationIfNeeded` and holds SpringBoard in `checkInAndWaitForDataMigration` until it returns. NEXT: find where the previous build version / disposition dictionary is stored (disassemble DataMigration.framework DMUserDataDispositionManager + datamigrator's isMigrationNeeded path), write it into the image; or get datamigrator's os_log out (OS_ACTIVITY_DT_MODE needs a launchd env change).
- **Data migration never records completion -> skip it (image v10, 2026-10-17).** Boot 0056n (18:16 UTC, `logs/boot-0056n.txt`, 30 min): 10 Hz panel copies, backboardd still presents at ~60 Hz (107k swaps), SpringBoard still in `BKSSystemShellService _checkIn` at sample 14. Every migration run takes 1+ hour on cpus=1 and repeats each boot. DataMigration decides from `/var/mobile/Library/Preferences/com.apple.DataMigration.plist` key `LastSystemVersion` (vs ProductBuildVersion 20H392); the pulled phone root (21:01 local) had NO such file. **v10** = that pulled phone state + fsck.hfsplus -fy (volume was marked not cleanly unmounted -> Linux mounts it read-only even with -o force; fsck found only hard-link counts + minor volume header, repaired) + `com.apple.DataMigration.plist` {LastSystemVersion: 20H392} (501:501 0600). `/run/media/dipa/android/ios-sweet-ipsw/ios16-root-20H392-v10.img` (+ .sha256, .simg); v8 files deleted, v9 kept as fallback.
- **Repo made PUBLIC (2026-10-17, user request) so GitHub-hosted macOS runners are free:** the 0056 CI run was refused ("recent account payments have failed or your spending limit needs to be increased"). Checked before: no device dumps, serials, IMEI or Apple binaries in the history (.gitignore keeps backup/, dtb/, recovery/, research/ out); commit author emails are public now. 0056 rerun `39056660104` passed -> `xnu/out-0056`, QEMU OK, image `shim/out/shim-boot-0056n.img` booted 18:16 UTC.
- **Boot 0055n (17:16 UTC, ~65 min, `logs/boot-0055n.txt`): migration bar reached 99% in ~30 min (was ~60), then crawled.** Root cause of the slowness: backboardd presents the progress UI at ~58 Hz (**167,000 swaps in ~48 min**) and AppleCLCD copied the full 10 MB frame into the panel on every swap -> ~600 MB/s memcpy on the single CPU (cpus=1), starving everything (polled UFS I/O too). Sampler (16 frames): **SpringBoard waits in `-[BKSSystemShellService _checkIn]`** (synchronous BSXPC call to backboardd, from FBSystemShellInitialize <- SBSystemAppMain) - backboardd holds the system shell check-in until the data migration ends, so the migration is the gate to SpringBoard UI. **Patch 0056**: swap only records the latest swap record; the vsync timer copies it to the panel every 60/sweetfb_hz ticks (default 10 Hz); `SWEET FB: N swaps` every 1000.
- **Boot 0054n (16:53 UTC, ~12 min, `logs/boot-0054n.txt`, patch 0054 sampler):** the data migration runs AGAIN on every boot (it completed once in the 0053s run) - completion is not being recorded. backboardd keeps swapping the progress UI (3700+ swaps in ~10 min, `SWEET FB: N swaps`). Sample during migration: SpringBoard main thread blocked in a synchronous XPC call (`mach_msg2_trap <- dispatch_mach_send_and_wait_for_reply <- xpc_connection_send_message_with_reply_sync <- -[BSXPCServiceConnectionMessage _sendSynchronously:] <- BSXPCServiceConnectionProxy ...`). Unsupported AKS selectors seen: 101 `aks_assert_consume`, 93 `aks_get_internal_info`, 34 `_aks_stash_load` (datamigrator), **35 `aks_get_extended_device_state`** (SpringBoard, chronod, remindd, searchd, symptomsd...). **Patch 0055**: AKS 35 answered like 17 (same DER device state), 101 succeeds; sampler backtraces 16 frames, 40 samples (~80 min).
- **MILESTONE: FIRST iOS PIXELS ON THE PANEL (boot 0053s long run, 15:33 UTC, ~60 min; photos IMG_20261017_183029/183222/183419; log `/run/media/dipa/android/ios-sweet-work/logs/boot-0053s-long.txt`, 407 KB, 1428 flushes).** The iOS data-migration boot screen (Apple logo + progress bar) was shown and the bar advanced to full in ~60 minutes. It is drawn by **backboardd through our kernel display path**: `SWEET SURF: backboardd create id 2/3 1080x2400 fmt 0x42475241 (BGRA) bpe 4 bpr 4352 size 10452992 keys 11`, IOSurface sels 9, 27, 5, 34 and traps 2/3 (lock/unlock), IOMFB SwapBegin (4) / SwapEnd (5, 1132-byte struct) / GetLayerDefaultSurface (3) / 68 / 55, then `SWEET FB: swap N layer 0 surface 2|3 1080x2400 ... a 0,0 1080x2400 b 0,0 1080x2400` alternating (double buffering; only the first 16 swaps are logged). Triggered by `com.apple.datamigrator` (AKS sels 101/93/34 return unsupported) and `com.apple.migrationpluginwrapper`. Probably ProgressUI-style CoreGraphics drawing into IOSurfaces (no GPU used). After the migration: SpringBoard and backboardd stay up (exec once each, no crash), nothing new drawn; crash loops only for mediaserverd, installcoordinationd, mobileactivationd (~108 each in the hour); bluetoothd and fairplayd.H2 relaunch constantly (no hardware). Kernel console text overlays the image (sweetfb_noconsole=1 would hide it).
- **MILESTONE: SpringBoard and backboardd both stay up (boot 0053s on v9, 15:29 UTC, `logs/boot-0053s.txt`).** With /chosen/display-scale = 3: `exec SpringBoard` once, `exec backboardd` once, no CRASH for either; MobileGestaltHelper reads IOMFB size/dot pitch; backboardd opens AppleCLCD (sels 57,15,22,29,33,79,74 as before). No IOSurface creates and no swaps: backboardd keeps polling `IOProviderClass IOAcceleratorES` (-> 0 found) and AGXAccelerator/IOAcceleratorESLegacy - no GPU, so no CoreAnimation renderer yet. Log goes quiet after ~47 s (only 47 flushes): the system idles. NEXT WALL: CoreAnimation rendering without a GPU (CPU path) so the window server produces frames.
- **SpringBoard's invalid mode = scale 0 (boot 0053n, 15:19 UTC, `logs/boot-0053n.txt`, heap scan):** `FBSDisplayMode cannot be configured as requested : <FBSDisplayMode: ...; infxinf@0x (1080x2400/0) 60Hz sRGB SDR>` - pixel size and 60 Hz are fine, scale is 0. libMobileGestalt (MGIOMFBSupport.c, sub_19c560a54) reads `display-scale` (u32, default 0) and `display-rotation` from **IODeviceTree:/chosen**, pixel size via IOMobileFramebufferGetDisplaySize (MobileGestaltHelper sel 8/28 in the log). mkadt now adds `/chosen/display-scale` = 3 (1080x2400 @3x = 360x800 pt). ADT `shim/out/sweet-0054hi.adt` (QEMU `research/q0054-hi.adt`), image `shim/out/shim-boot-0053s.img` = 0053 kernel + 0054hi ADT. Possible catch: MobileGestalt may have cached scale 0 in `/private/var/containers/Shared/SystemGroup/systemgroup.com.apple.mobilegestaltcache/...`.
- **MILESTONE: backboardd survives and opens the display (boot 0052n on v9, 15:07 UTC, `logs/boot-0052n.txt`).** No `CRASH backboardd`. It walks `IODeviceTree:/arm-io` children, matches IOMobileFramebuffer, `open AppleCLCD type 0 -> 0x0`, calls IOMFB selectors 57, 15, 22, 29, 33, 79 (GetBlock, out 1580/40), 74 (SupportedFrameInfo), 12, 6, 27, 17, 84, 50; opens IOCoreSurfaceRoot (sel 13); looks for AGXAccelerator / IOAcceleratorES / IOAcceleratorESLegacy (none, repeatedly), `IODeviceTree:/product` (none, repeatedly), `/buttons`, aop-smart-cover, IOPMrootDomain. No swaps yet. **SpringBoard now gets past display discovery** and dies (sig 5) in `-[FBSDisplayMode _initWithWidth:height:preferredScale:scaleOverride:refreshRate:gamut:hdr:rotation:virtual:validityCheck:]+580` <- `_initWithCADisplayMode:scale:rotation:` <- `FBSDisplayConfiguration _initWithImmutableDisplay:` <- `FBSDisplaySource initWithDisplay:` <- `FBSDisplayMonitor` (slide 0x14504000): "FBSDisplayMode cannot be configured as requested". Checks: width/height >= 2, preferredScale > 0, scaleOverride >= 0, refreshRate non-zero, valid gamut/HDR/rotation. Suspects: refresh rate 0 (IOMFB timing blocks answered with zeros) and/or scale 0 (MobileGestalt main-screen-scale; no /product node in the ADT). **Patch 0053**: heap text scan also on SIGTRAP and for SpringBoard (default sweetscan list backboardd,SpringBoard) to read the exact mode description.
- **Image v9 (2026-10-17) = v8 + `/private/var/containers/{Bundle,Data/System,Shared/SystemGroup,Temp}` (root:wheel 0755; on iOS these live on the data volume, absent from the rootfs) + launchd.plist with StandardOutPath/StandardErrorPath renamed to ...PatX (the in-place phone fix; daemons' stdout reaches the log via the 0048 /dev/null tee).** `/run/media/dipa/android/ios-sweet-ipsw/ios16-root-20H392-v9.img` SHA256 aa9f9139...6e67, `.simg` 12,145,303,864 bytes; written through `sudo mount -t hfsplus -o loop,force`. **Patch 0052** (`xnu/patches/0052-sweet-hfs-rename-swap.patch`, CI `39042761826` -> `xnu/out-0052`, QEMU OK, image `shim/out/shim-boot-0052n.img`): vn_rename falls back to VNOP_EXCHANGE when VNOP_RENAMEX(RENAME_SWAP) returns ENOTSUP for two regular files on one volume (HFS exchange swaps data and cnode descriptors = swap semantics). Flashing v9 started 2026-10-17 ~15:00 UTC.
- **backboardd EXCEPTION FOUND (boot 0051n, 14:41 UTC, `logs/boot-0051n.txt`, patch 0051 heap scan):** `*** Terminating app due to uncaught exception 'NSInvalidArgumentException', reason: '*** -[NSURL initFileURLWithPath:]: nil string parameter'`. First-throw stack (slide 0x337f0000): `+[NSURL fileURLWithPath:]` <- `-[BSSystemContainerForCurrentProcessPathProvider libraryPath]` <- `cachesPath` <- backboardd main+0x1d858 (StartWindowServer, shader cache path). BaseBoard: libraryPath = `BSSystemSharedResourcesDirectoryForIdentifier` = `BSSystemSharedDirectoryForIdentifier(id)` + "/Library"; that calls `container_system_path_for_identifier` (libsystem_containermanager -> `_container_legacy_lookup` -> containermanagerd XPC), which returned NULL (BaseBoard logs "Error getting shared system container ..."). With 0050 the sandbox denials are gone. containermanagerd.log.0 in the pulled (pre-0050) image: "Did not receive any persona attributes", "Expected to find at least one persona", notify_register_dispatch failed 9; `/private/var/containers` does NOT exist in the root image (on iOS it lives on the data volume). usermanagerd does create kernel personas 99/199/1000, but fails to save `/private/var/keybags/usersession.kb` and `persona.kb`: "Failed to atomically swap writing file: Operation not supported (45)" (HFS has no RENAME_SWAP). NEXT: create `/private/var/containers` (and check what containermanagerd needs for system group containers), fix or emulate RENAME_SWAP on HFS, then re-check backboardd.
- **Disk housekeeping (2026-10-17):** /home was at 4 GiB free. Moved (not deleted) `xnu/out-0010..0044` and old `shim/out/*.img`/`payload-*.bin` (everything before 0046) to `/run/media/dipa/android/ios-sweet-work/archive/{xnu,shim-out}` (6.3 GiB); /home now 8.7 GiB free. Large work files (phone-root.img 16 GiB, logs, tracev3 dumps) live in `/run/media/dipa/android/ios-sweet-work/`. **Patch 0051** (`xnu/patches/0051-sweet-crash-heap-strings.patch`, CI `39041440935`): on SIGABRT of a process in boot-arg `sweetscan` (default backboardd) the crash log prints heap text runs as `STR ...` (to find the NSException reason). Boot 0051n 14:41 UTC.
- **Boot 0049n (14:11 UTC, `logs/boot-0049n.txt`, patch 0049 trace): backboardd's IOKit lookups before it dies** (each run): `IODeviceTree:/arm-io/pearl-sep` -> none, matching ApplePearlSEPDriver -> none, `IOService:/IOResources/AppleKeyStore` open OK, matching IOHIDDevice (DeviceUsagePairs) / `HIDServiceSupport` notifications, `usb-drd,t8027` notification; **never any IOMobileFramebuffer / display lookup** - the exception happens before display detection. launchd (tracev3) shows backboardd's mach lookups denied with `error = 159: Sandbox restriction`: com.apple.mobilegestalt.xpc, com.apple.iohideventsystem, com.apple.system.notification_center, com.apple.logd, containermanagerd, ACCHWComponentAuthService, oscard. libsystem_sandbox uses `__mac_syscall("Sandbox", op, arg)` (ops: 1 init, 2 check, 3 note, 4 container path, 5/6/7/8 extensions, 0x15 check_bulk, ...); with no policy named "Sandbox" every call gets ENOPOLICY. **Patch 0050** (`xnu/patches/0050-sweet-sandbox-policy.patch`): built-in permissive MAC policy "Sandbox" in sweet_amfi.c (mpo_policy_syscall returns 0, container/extension ops ENOENT; logs first use of each op as `SWEET Sandbox: proc op N`).
- **Phone root pulled (16 GiB, 12 min, `adb exec-out dd if=/dev/block/sda34`) to `/run/media/dipa/android/ios-sweet-work/phone-root.img` (loop-mounted ro at /run/media/dipa/iOSRoot).** No .ips crash reports. logd tracev3 (Persist, LZ4 `bv41` blocks, decompressed strings in `ios-sweet-work/tracev3/all.txt`): /private/var/db/uuidtext is EMPTY so only launchd's own messages are readable. Findings: v8 launch failure = `Service could not initialize: posix_spawn(/usr/libexec/backboardd), error 0xd - Permission denied` (xpcproxy exit 78) - /dev/console not openable for the mobile user; backboardd[98] spawned `com.apple.MTLCompilerService` before SIGABRT; **launchd denies many mach lookups with `error = 159: Sandbox restriction`** (mediaserverd -> com.apple.backboard.display.services, remoted, mobiletimerd -> sleepd, identityservicesd -> apsd) and **tccd exits OS_REASON_SANDBOX "profile not found"** - no Sandbox kext/profiles on SWEET; likely cause of many daemon crash loops (next wall after the display). CF's uncaught-exception text never reaches stderr for daemons (no CF handler; libc++abi prints only the type). **Patch 0049** (`xnu/patches/0049-sweet-iokit-trace.patch`): `IOK name: ...` console lines for registry path lookups, child iterators, matching (with result count/class), matching notifications and IOServiceOpen of the processes in boot-arg `sweetiolog` (default backboardd), max 400 lines.
- **CONFIRMED: launchd StandardOut/ErrorPath=/dev/console stops backboardd from launching.** After the in-place rename (boot 0047n-b, log `logs/boot-0047n-b.txt`) backboardd launches again and dies as on v7: sig 6, `___pthread_kill <- abort <- demangling_terminate_handler <- _objc_terminate <- std::terminate <- _dispatch_client_callout <- _dispatch_once_callout <- main+0x9334` (window-server dispatch_once). It never opened AppleCLCD or IOCoreSurfaceRoot (no `SWEET FB/SURF: backboardd` lines) -> throws before/at display detection. **Patch 0048** (`xnu/patches/0048-sweet-devnull-tee.patch`, CI `39037749668` -> `xnu/out-0048`, image `shim/out/shim-boot-0048n.img`): writes to /dev/null by processes named in boot-arg `sweetnull` (default `backboardd,SpringBoard`) are printed as `|name| text`. Boot 0048n (13:48 UTC, log `logs/boot-0048n.txt`): only `|backboardd| libc++abi: terminating due to uncaught exception of type NSException` (CF's reason line goes to os_log, not stderr, despite CFLOG_FORCE_STDERR/OS_ACTIVITY_DT_MODE). Next: pull the whole 16 GiB root from recovery (`adb exec-out dd if=/dev/block/sda34`) to `/run/media/dipa/android/ios-sweet-work/phone-root.img` and read ReportCrash .ips files / logd tracev3 for the exception reason.
- **Persistent log WORKS (boot 0047n on v8, 13:31 UTC; pulled from OrangeFox: 70 KB, 111 flushes, `/run/media/dipa/android/ios-sweet-work/logs/boot-0047n.txt`).** In 3 min **backboardd was never exec'd** (v7 ran it), ~70 bare `exec xpcproxy`, SpringBoard loops on FBSDisplayMonitor (no display), mediaserverd sig 11 loop, locationd, lockdownd sig 5. Suspect the v8 plist (StandardOut/ErrorPath=/dev/console on backboardd). **In-place plist edit from recovery (no reflash):** launchd.plist is one extent at image/partition byte offset 0x1e025f000 (195 blocks; verified bytes identical on phone vs local v8 mount); renamed StandardOutPath->StandardOutPatX and StandardErrorPath->StandardErrorPatX (same length, both jobs) in blocks 68 and 105 via `adb push` + `dd of=/dev/block/sda34 seek=... conv=notrunc,fsync`, read back VERIFIED. Phone now differs from local v8 image in those 2 blocks (files in `/run/media/dipa/android/ios-sweet-work/`). Test boot 0047n 13:38:42 UTC. Recovery kernel has no hfsplus (raw block edits only).
- **Patch 0047: persistent console log (CI `39036478663` -> `xnu/out-0047`, QEMU no panic; phone image `shim/out/shim-boot-0047n.img` = 0047 + sweet-0046hi.adt + 0045n cmdline).** `_cnputs` (all console output: kernel printf + daemons' /dev/console) also appends to a 4 MiB ring in sweet_ufs.c; after the UFS partition is ready and writable (ufsrw=1) a thread writes new ring blocks + header to the LAST 1025 blocks (4 KiB) of userdata every ~1 s and SYNCHRONIZE CACHE (prints `SWEET LOG: console log to the last 4100 KiB ...`). Read: phone to fastboot -> `fastboot boot recovery/recovery.img` (OrangeFox) -> `tools/sweet-log-pull.sh OUT.txt` (adb dd of that area + `tools/sweet-log.py`). Not yet verified on the phone. Panics after the last flush are not in it (screen still shows them). 2x font attempt reverted: XNU's v_scale only scales the progress icon.
- **Boot 0046n on v8 (13:05 UTC, VID_20261017_150522_HSR_120):** phone prints `SWEET SURF: IOCoreSurfaceRoot registered` and `SWEET FB: AppleCLCD 1080x2400 stride 4320 at 0x9c000000, default surface 1` (nubs + match work on hardware). Visible userspace: early boot tasks, launchd_cache_loader, `exec SpringBoard`; no `exec backboardd` / `SWEET FB: backboardd` line seen in the readable frames (video blurry). Frame 00:47: lower half of the screen shows OLDER console text (16:01:12) below newer lines -> unconfirmed hint that a swap copied an old snapshot of the panel (CA reads the default/displayed surface = panel memory). SpringBoard still dies in `-[FBSDisplayMonitor _initWithBookendObserver:transformer:]+1160` (sig 5, slide 0x30960000). **Shim: 2x console font** (`shim/loader.c` Video.v_depth scale field = 1) so phone videos are readable; image `shim/out/shim-boot-0046b.img` = 0046n + 2x font.
- **Patch 0046: built-in IOSurface + IOMobileFramebuffer (2026-10-17, offline, NOT phone-tested).** `xnu/patches/0046-sweet-iosurface-iomfb.patch`: new `iokit/Kernel/arm/SweetSurface.{h,cpp}` (IOCoreSurfaceRoot + IOSurfaceRootUserClient: sel 13/0/4/34/35, traps 0-5, wired buffers mapped into the caller, per-client refs) and `SweetFramebuffer.cpp` (AppleCLCD : IOMobileFramebuffer on /arm-io/disp0: sizes, swap = CPU copy of enabled layers into the ABL panel memory, 60 Hz vsync via sendAsyncResult64WithOptions(CanDrop), panel memory published as the default IOSurface, kernel text console paused on the first swap only with `sweetfb_noconsole=1` (default keeps the console: pausing switches it to serial and would hide panics)); SweetPlatformExpert creates nubs for /arm-io children (not gic) attached to the platform expert (IOPlatformDevice::compareName casts its provider to IOPlatformExpert, so nubs under the arm-io nub never matched - first CI build showed that in QEMU). mkadt: /arm-io/disp0 {device_type display-subsystem, compatible sweet,display, canvas-width 1080, canvas-height 2400}. CI `39021572169` -> `xnu/out-0046`. **QEMU** (`research/q0046-hi.adt`, RAM disk init, msgbuf): `SWEET SURF: IOCoreSurfaceRoot registered`, `SWEET FB: AppleCLCD 1080x2400 stride 4320 at 0x9c000000, default surface 1`, init alive, no panic. Phone image **`shim/out/shim-boot-0046n.img`** (SHA256 9c4d2fe9..., CI `39024108588` with the review fixes: swap bounds check, zeroed 64-bit async ref, port release, 1.5 GiB wired budget, ref leak/race fixes; QEMU re-checked) = 0046 kernel + `shim/out/sweet-0046hi.adt` + the 0045n cmdline; boot it on image v8 (backboardd/SpringBoard log to console) and film. Expected new console lines: `SWEET SURF: <proc> create id ...`, `SWEET FB: backboardd sel N ...`, `SWEET FB: swap ...`. Open question for the next wall: QuartzCore's IOMFB server builds its renderer from Metal first (`CAMetalContextCreate`), GLES only when enabled; how the CPU renderer gets selected on a device without a GPU is not yet established.
- **IOSurface values ABI (offline RE, `/run/media/dipa/android/ios-sweet-work/iosurface-values.md`) - TODO in SweetSurface (0046 only accepts and drops values, so IOSurfaceCopyValue always returns NULL):** sel 9 SetValue in = {u32 id, u32 pad, IOCFSerialize([value, key]) or ([dict] = merge)}, sel 0xb RemoveValue in = {u32 id, u32 pad, key\0} (empty key = remove all); both out 4 bytes = new generation, client accepts only (gen+2)|1. Kernel after each change: gen = (gen+2)|1 (odd, never 0) -> state+0x20, serialized size (>=1) -> state+0x28. sel 0xa in {u32 id, u32 0, u8 0}, out {u32 ?, u32 gen, serialized non-bulk dict}; too small -> 0xe00002db + needed size (client retries x16). sel 0x1b in 0x88: bulk struct 0x70 @0, u64 valid size @0x70, u64 changed mask @0x78, u32 id @0x80 -> copy masked fields into state+0x30 (bit0 32B @0, bit1 16B @0x20, bit2 8B @0x30, bits3-10 1B @0x38..0x3f, bits11-14 24B @0x40/4B @0x58/8B @0x5c/1B @0x64).
- **IOMFB display matching confirmed (offline RE, `/run/media/dipa/android/ios-sweet-work/iomfb-match.md`):** the framework never matches on "AppleCLCD"; any registered IOMobileFramebuffer subclass works. `iomfb_match_callback` reads only `dfr`/`AppleTV`/`external` (CFBoolean, service itself, no parents); internal main display = all absent/false (type 0, name "primary"). Display count = /arm-io children whose device_type starts with "display-subsystem" (count 0 -> CreateDisplayList returns NULL; more nodes than services -> 30 s wait). IOMobileFramebufferOpen fails only on IOServiceOpen failure; canvas-width/height read as 4-byte CFData from the IOService-plane parent (optional). CopyProperty = IORegistryEntrySearchCFProperty on the service only. Patch 0046 (disp0 node, `external`=false, AppleCLCD : IOMobileFramebuffer) fits all of this.
- **IOMobileFramebuffer swap + notification ABI (2026-10-17, offline).** Swap record = fb+0x18, **0x46c bytes**, zeroed by SwapBegin and sent whole by `kern_SwapEnd` = IOConnectCallStructMethod(sel 5, rec, 0x46c, no output). **SwapBegin** = sel 4, no input, 1 scalar out = swap id (stored at rec+0x50). `kern_SwapSetLayer(fb, layer<4, IOSurfaceRef, CGRect a, CGRect b, flags)`: rec+0x54+4*layer = **IOSurface id**; rec+0x104 bit layer = layer enabled (rec+0x108 bit cleared); rect a (int x,y,w,h, scaled) at rec+0x64+16*layer, rect b at rec+0xc4+16*layer; rec+0x114+4*layer = transform from flags&0xf; flag bits 5/31/6/7/8/9 set bytes rec+0x2ca/0x2cc/0x2e3/0x2e5/0x2e6/0x467+layer. A NULL surface only sets the enable bit with zero id. SwapWait = sel 6 scalars [swap id, timeout, 0].
  - **Notifications**: `IOMobileFramebufferScheduleWithDispatchQueue`/`GetRunLoopSource` create an IONotificationPort and `IOConnectSetNotificationPort(conn, type, port, 0)` (kernel `registerNotificationPort`). `kern_EnableNotifications(fb, type, cb, ctx)` = **sel 72 scalars [NotifyCallbackFuncs[type], fb, type, 0]** -> the kernel keeps an async reference {port, func, refcon=fb} per type and fires it with `sendAsyncResult64`. Types: 0 HotPlug, 1 Power, 3 FrameInfo (args[0] = mask of 31-bit keys, args[1] u32, then values), 4 CRC, **5 Vsync**: 6 args, each a 32-bit half in a u64 slot: (ts lo, ts hi), (t2 lo, hi) passed through the time-ingest helper, (t3 lo, hi); the framework then calls the client's vsync callback(fb, ts, t2', t3, ctx). Vsync callbacks are dropped while the notification port has queued messages.

- **IOSurface.framework user-client ABI reversed (2026-10-17, offline, step 2 of the GUI plan).** `ipsw dyld disass research/dsc/dyld_shared_cache_arm64 --image IOSurface` (selector scan script: scratchpad `selscan.py`).
  - Connect (`_iosConnectInitalize`, pthread_once): `IOServiceGetMatchingService(IOServiceNameMatching("IOCoreSurfaceRoot"))`, retried with sleep(1) up to 241 times (a missing service stalls every client ~4 min, no crash); `IOServiceOpen(type 0)`; then **sel 13** (no inputs, struct out 0x18 bytes = `_ioSurfaceLimits`) and requires u16 at out+0x16 == 1 (ABI version); out+0 = offset/plane-base alignment mask, out+4 = bytes-per-row alignment mask (used as (x+m)&~m), +0..+0x14 also copied into IOSurface remote-method init, otherwise logs and closes the connection.
  - **Create = sel 0**: scalar in [parent id or 0], struct in = `IOCFSerialize(props, kIOCFSerializeToBinary)` (OSUnserializeBinary format; keys IOSurfaceWidth/Height/BytesPerRow/BytesPerElement/PixelFormat/AllocSize/PlaneInfo/CacheMode/IsGlobal/...), struct out **0xa68 bytes** ("lock result"). **Lookup = sel 4**: scalar in [id], same struct out. LookupFromMachPort = sel 0x22 (scalar in [port name]); CreateMachPort = sel 0x23 (scalar in [id, options], scalar out [port name]).
  - Lock result (copied to client+0x68, size 0x68 + planes*0x80, min 0xe8): 0x00 u64 base address **mapped in the caller's task**; 0x08 u64 task VA of a per-surface shared state page (+0 u64 registry id, +8/+0xa u16 bound accel ids, +0xc u32 seed, +0x14 u8 tiled, +0x20 u32 value generation, +0x24 YCbCr matrix, +0x28 u32 non-bulk values size, +0x2d u8 displayable, +0x2e u8 sysmem-only, +0x30 0x70 bytes bulk attachments); 0x10 u64 task VA of timestamp page (4 u64 indexed timestamps, +0x20 detach code); 0x18 u32 surface id; 0x1c u32 alloc size; 0x20 width; 0x24 height; 0x28 bytes per row; 0x2c buffer offset; 0x30 pixel format; 0x34 u32 (dcache flush length); 0x38 plane count; 0x40 u16 bytes/element; 0x42 u8 element width; 0x43 u8 element height; 0x44 cache mode; 0x4c u8 subsampling; 0x4d u8 prohibit-use count; 0x50 parent id; 0x54 slice count; 0x58 u64 trace id; 0x60 u64 protection options; planes[n] at 0x68+n*0x80 (+0 width, +4 height, +8 bytes/row, +0xc offset, +0x14 size, +0x18 u16 bpe, +0x1a/+0x1b u8 element w/h, +0x1c u8 component count, +0x1d address format, +0x54 u8 compression type (non-zero -> no CPU base address)).
  - **Traps** (IOConnectTrapN -> `IOUserClient::getTargetAndTrapForIndex`): 0 IncrementUseCount(id, category), 1 DecrementUseCount(id, category), 2 **Lock**(id, options, &seed_out), 3 **Unlock**(id, options, &seed_out), 4 Release(id), 5 Release after a failed create/lookup setup (id).
  - Other selectors: 5 SetYCbCrMatrix, 6 WrapClientImage, 7 WrapClientMemory, 9 SetValue (serialized), 0xa UpdateNonBulkValueCache (struct in 9), 0xb RemoveValue, 0xc BindAccel, 0x11 SetSurfaceNotify (async), 0x12 RemoveSurfaceNotify, 0x13 Log, 0x14 SetPurgeable, 0x15 SetOwnership, 0x16 SetTiled, 0x18 SetTimestamp, 0x19 GetTileFormat, 0x1a CopyDataValueBytes, 0x1b SetBulkAttachments (struct 0x88), 0x1e/0x2e-0x31 (via outlined helpers), 0x1f SetCompressedTileDataRegionMemoryUsed, 0x20 GetGraphicsCommPageAddress, 0x21 SetIndexedTimestamp, 0x24-0x26/0x2d IOSurfaceAccelerator, 0x27-0x29 shared events, 0x2a SignalEvent, 0x2b Set/InitDetachModeCode, 0x2c SetOwnershipIdentity, 0x32-0x34 data properties.
  - => SWEET kernel service: class/name **IOCoreSurfaceRoot** + IOSurfaceRootUserClient; minimum = sel 13, 0, 4, 9/0xa/0xb (values), traps 0-5, 0x22/0x23 later for cross-process surfaces (CA sends surfaces to backboardd by mach port). Memory: IOBufferMemoryDescriptor per surface, mapped into each task with createMappingInTask; ids from a global table.

- **Image v8: daemon logs on the console.** `tools/patch-launchd-plist.py IN OUT LABEL...` rewrites launchd.plist (binary, plistlib): renames every `_PanicOnCrash` to `_PanicOnCrasX` and gives the listed jobs `StandardOutPath`/`StandardErrorPath` `/dev/console` (devfs console is 0622, writable by mobile) plus `OS_ACTIVITY_DT_MODE=YES` (os_log mirrored to stderr) and `CFLOG_FORCE_STDERR=1`. v8 = v7 + that plist for com.apple.backboardd and com.apple.SpringBoard, written through the mount (796310 bytes, root:80 0644), SHA256 in `ios16-root-20H392-v8.img.sha256`, `.simg` ready; boot with `shim/out/shim-boot-0045n.img`. Goal: see backboardd's uncaught exception text and the window server's display probing. ODDITY (unresolved): the v5 raw-image rename at offset 0x1e025f000 is present in the v5-v7 image bytes, but the plist read through a Linux mount of v7 still had the original `_PanicOnCrash` keys; filefrag shows the file as one extent. Never patch file contents through raw offsets again; write through the mount.
- **IOMobileFramebuffer.framework reversed (step 1 of the GUI plan).** `ipsw dyld disass research/dsc/dyld_shared_cache_arm64 --image IOMobileFramebuffer`.
  - Display discovery (`IOMobileFramebufferCreateDisplayList` -> `getDisplayListNumber`): iterates children of `IODeviceTree:/arm-io`, counts nodes whose `device_type` is "display-subsystem" or "ext-display-subsystem" (or `compatible` "paravirtualizedgraphics,gpu"); then `iomfb_populate_display_infos` adds an IOServiceAddMatchingNotification(IOServiceFirstMatch, **IOServiceMatching("IOMobileFramebuffer")**) and runs the run loop up to 30 s until that many services matched. `iomfb_match_callback` reads service properties `dfr`, `AppleTV`, `external` (CFBoolean) and names displays (external ones "%s-%d").
  - `IOMobileFramebufferOpen(service, task, type, &fb)`: `__ioMobileFramebufferAlloc` (CFPreferences com.apple.iokit.IOMobileGraphicsFamily: canvas_width/height, override_display_width/height, override_panel_width/height, benchmark, enable_ktrace), `IOServiceOpen(service, task, type)` (GetMainDisplay passes type 0), `getEDTProperty` reads `canvas-width`/`canvas-height` from the service's IODeviceTree parent, then fills a table of `kern_*` function pointers.
  - User client selectors (`kern_*` -> IOConnectCall*): 3 _kern_GetLayerDefaultSurface[ScalarMethod_stub]; 4 _kern_SwapBegin[ScalarMethod_stub]; 5 _kern_SwapEnd[StructMethod_stub]; 6 _kern_SwapWaitWithTimeout[ScalarMethod_stub] _kern_SwapWait[ScalarMethod_stub]; 7 _kern_GetID[ScalarMethod_stub]; 8 _kern_GetDisplaySize[ScalarMethod_stub]; 10 _kern_SetTVOutMode[ScalarMethod_stub]; 11 _kern_SetWSSInfo[ScalarMethod_stub]; 12 _kern_RequestPowerChange[ScalarMethod_stub]; 13 _kern_EnableStatistics[ScalarMethod_stub]; 14 _kern_SetFlags[ScalarMethod_stub]; 15 _kern_SetDebugFlags[ScalarMethod_stub]; 16 _kern_SetTVOutSignalType[ScalarMethod_stub]; 17 _kern_SetGammaTable[StructMethod_stub]; 18 _IOMobileFramebufferIsMainDisplay[ScalarMethod_stub]; 19 _kern_SetWhiteOnBlackMode[ScalarMethod_stub]; 20 _kern_SwapSignal[ScalarMethod_stub]; 22 _kern_SetDisplayDevice[ScalarMethod_stub]; 23 _kern_SetDigitalOutMode[ScalarMethod_stub]; 24 _kern_GetHDCPDownstreamState[StructMethod_stub]; 25 _kern_GetDigitalOutState[ScalarMethod_stub]; 26 _kern_printDisplayRegs[ScalarMethod_stub]; 27 _kern_GetGammaTable[StructMethod_stub]; 28 _kern_GetDotPitch[ScalarMethod_stub]; 29 _kern_GetDisplayArea[StructMethod_stub]; 30 _kern_EnableDisableDithering[ScalarMethod_stub]; 31 _kern_SetUnderrunColor[ScalarMethod_stub]; 33 _kern_EnableDisableVideoPowerSavings[ScalarMethod_stub]; 34 _kern_SetVideoDACGain[ScalarMethod_stub]; 35 _kern_SetLine21Data[ScalarMethod_stub]; 41 _IOMobileFramebufferEnableMirroring[ScalarMethod_stub]; 42 _IOMobileFrameBufferGetMirroringCapability[StructMethod_stub]; 43 _IOMobileFramebufferSetRenderingAngle[StructMethod_stub]; 44 _IOMobileFramebufferSetMirrorContentRegion[StructMethod_stub]; 47 _kern_HDCPSendRequest[ScalarMethod_stub]; 48 _kern_HDCPGetReply[ScalarMethod_stub]; 49 _kern_SurfaceIsReplaceable[ScalarMethod_stub]; 50 _kern_SetBrightnessCorrection[ScalarMethod_stub]; 51 _kern_SetColorRemapMode[ScalarMethod_stub]; 52 _kern_SwapCancel[ScalarMethod_stub]; 53 _IOMobileFramebufferSetCanvasSize[ScalarMethod_stub]; 54 _IOMobileFramebufferGetMatrix[Method_stub]; 55 _IOMobileFramebufferSetMatrix[Method_stub]; 56 _IOMobileFramebufferKernelTests[StructMethod_stub]; 57 _kern_GetColorRemapMode[ScalarMethod_stub]; 66 _kern_SPLCSetBrightness[ScalarMethod_stub]; 67 _kern_SPLCGetBrightness[ScalarMethod_stub]; 68 _kern_SetParameter[Method_stub]; 69 _kern_SwapSetColorMatrix[StructMethod_stub]; 72 _kern_DisableNotifications[ScalarMethod_stub] _kern_EnableNotifications[ScalarMethod_stub]; 73 _kern_ChangeFrameInfo[ScalarMethod_stub]; 74 _kern_SupportedFrameInfo[Method_stub]; 75 _kern_FactoryPortal[StructMethod_stub]; 77 _kern_GetCurrentAbsoluteTime[ScalarMethod_stub]; 78 _kern_SetBlock[Method_stub]; 79 _kern_GetBlock[Method_stub]; 80 _kern_GetLinkQuality[ScalarMethod_stub]; 81 _kern_SwapCancelAll[ScalarMethod_stub]; 82 _kern_GetProtectionOptions[ScalarMethod_stub]; 83 _kern_CopyLayerDisplayedSurface[ScalarMethod_stub]; 84 _kern_SetContrast[StructMethod_stub]; 85 _kern_GetBufBlock[Method_stub]; 86 _IOMFBGainEncoderFinishEncoding[Method_stub]; UNKNOWN {}
  - => Kernel needs: an `/arm-io` child node with device_type "display-subsystem" (+ canvas-width/height) and an IOService of class **IOMobileFramebuffer** (subclass name match) attached under it, opened with type 0, implementing at least GetDisplaySize(8), IsMainDisplay(18), GetID(7), GetLayerDefaultSurface(3), SwapBegin(4)/SwapEnd(5 struct)/SwapWait(6), Enable/DisableNotifications(72), frame info(73/74), CopyLayerDisplayedSurface(83), plus IOSurface for the swapped buffers. NEXT: CoreAnimation's AppleDisplay/IOMFBDisplay usage of these (constructor, first swap, vsync), then IOSurface.framework's IOSurfaceRoot selectors.
- **GUI PLAN (decided 2026-10-16): CPU rendering + kernel IOMobileFramebuffer.** User: CPU rendering is fine for now (goal = prove the GUI runs), may later research an Apple-style GPU driver for the Adreno 618 -> keep display output and renderer separable. QuartzCore findings (symbols from the cache's .symbols subcache: `ipsw dyld symaddr research/dsc/dyld_shared_cache_arm64 --image QuartzCore`; strings: `ipsw dyld macho ... QuartzCore --strings`):
  - Renderers: `sw_new_context` (CA::OGL::SWContext, full CPU renderer incl. blur, images, IOSurface-backed surfaces, make_buffer_current(WindowServer::Surface)), `gles_new_context`, `metal_new_context`, `new_null_context`. Env knobs include CA_ENABLE_OGL, CA_DISPLAY_TYPE, CA_FORCE_LOCAL_SERVER, CA_FORCE_TIMER, CA_CANVAS_WIDTH/HEIGHT, CA_MAIN_DISPLAY_SCALE/ORIENTATION, CA_DISABLE_RENDER, CA_ALWAYS_RENDER (selection logic not traced yet).
  - `-[CAWindowServer _detectDisplays]` (0x1884e3150) iterates static tables `open_funcs`/`count_funcs` = AppleCLCDDisplay, AppleRGBOutDisplay, AppleWirelessDisplay only; each `count()` = `display_count_of_type(IOMFBDisplayType)` over **`IOMobileFramebufferCreateDisplayList()`**, `open(i)` = `create_display_of_type` -> `CA::WindowServer::AppleDisplay(CFString name, ..., IOMFBDisplayType)` (an IOMFBDisplay driven by IOMFBServer: vsync_callback, frame_info_callback, swaps). `CA::WindowServer::VirtualDisplay` exists but is never auto-detected (explicit API only). => the main display MUST come from an IOMobileFramebuffer kernel service.
  - NEXT: reverse IOMobileFramebuffer.framework: IOMobileFramebufferCreateDisplayList / IOMobileFramebufferOpen (service matching, display type property), the user-client selectors used by IOMFBServer (display size/modes, swap begin/set-layer/end with IOSurface ids, vsync notifications), then the IOSurface kernel side (IOSurfaceRoot user client: create/lookup/lock, memory mapping) that both IOMFB swaps and CA surfaces need. Kernel: SWEET IOMobileFramebuffer service that copies the swapped IOSurface to the 1080x2400 framebuffer at 0x9c000000.
- **logd fixed; backboardd = DISPLAY WALL (boot 0045n on v7, 21:08:57 UTC, frames VID_20261016_230850 00:55-01:28, slide 0x4c3ec000, `research/crash-0045n-v7.txt`).** No `CRASH logd` any more; new daemons run (runningboardd, WirelessRadioManagerd, networkserviceproxy, dasd, cloudpaird, magicswitchd, atc, askpermissiond, ManagedSettingsAgent, containermanagerd uses AKS 0/17). New: locationd sig 11 at CFRunLoopAddSource+132 (NULL source) from its main+0x2af138 in a dispatch_once. **backboardd** sig 6: abort <- std::terminate <- _objc_terminate <- dispatch_once <- main+0x9334 = the "start %{public}@..." wrapper (0x100009264) for **"window server"** (block 0x10000a770 -> dispatch_once body 0x10001d7f0 = StartWindowServer): MTLSetShaderCachePath, `[CAWindowServer serverWithOptions:@{kCAWindowServerDisableUpdatesOnMainDisplay: @YES}]`, `setRendererFlags:`, **`mainDisplay`** -> `displayId` -> `[CADisplay displayWithDisplayId:]`, setWindowServerDisplay:, bounds, pointScale, currentMode, preferredScale, nativeOrientation, touchScales... With no display, mainDisplay is nil and it throws. (HID system and GS start fine before it.) SpringBoard dies on the same missing display (FBSDisplayMonitor). QuartzCore display backends (from the cache's .symbols subcache, `ipsw dyld str`): `CA::WindowServer::AppleCLCDDisplay` (IOMobileFramebuffer hardware) and **`CA::WindowServer::VirtualDisplay`** (open(), new_server, clone_update). `CA_DISPLAY_TYPE` and `CA_FORCE_LOCAL_SERVER` strings exist in QuartzCore but have no direct xref (likely read via a table of CA_* env names). NEXT: find how CA::WindowServer::Server enumerates displays (IOMobileFramebuffer services vs VirtualDisplay / CA_DISPLAY_TYPE) and choose: (a) kernel IOMobileFramebuffer service + IOSurface, or (b) a VirtualDisplay rendered by CA's CPU path (CA::OGL::SW) and copied to the framebuffer.
- **watchdogd + CommCenter + identityservicesd fixed (boot 0045n on v6, 20:41:30 UTC, frames VID_20261016_224133 00:39-01:13, slide 0x20fec000).** `SWEET WDT: watchdogd sel 0 in 0/0 out 1/0 -> ok`, no watchdogd/CommCenter/identityservicesd crashes (CommCenter/identityservicesd now call AKS 0/17/7). usermanagerd boot task runs (UMD_INIT creates primary session uid 501 "mobile", personas 99 System and 199 Default registered with the kernel); `Failed to atomically swap writing file /private/var//keybags/usersession.kb: Operation not supported (45)` (HFS lacks the atomic swap rename; non-fatal so far). Remaining: SpringBoard (FBSDisplayMonitor, no display), backboardd (uncaught exception), mediaserverd, lockdownd (crash inside obfuscated code, main+0x4c1b4?), logd. **logd**: main+0x18160 = `BUG IN LIBTRACE: Failed to migrate directory` from 0x10001801c(dir 0): 0x100016538 requires the dir to exist with uid/gid/mode from the table at 0x10002df14 (0: /private/var/db/diagnostics 272:272 0751, 1: /private/var/db/uuidtext 272:272 0755, 2: /private/var/db/diagnostics/timesync 272:272 0755) plus a `.migrated` file, else XPC "operation 6" to a helper and crash. **Image v7** = v6 + those dirs/markers (also in mkiosroot.sh), SHA256 in `ios16-root-20H392-v7.img.sha256`, `.simg` ready. Boot with `shim/out/shim-boot-0045n.img`.
- **Exit-reason text works (boot 0044n, frames VID_20261016_221726 00:32-00:53, slide 0x22d5c000).** CommCenter/identityservicesd: `couldn't dlopen libobjc-trampolines.dylib: dlopen(/usr/lib/libobjc-trampolines.dylib, 0x0106): tried: '/usr/lib/libobjc-trampolines.dylib' (no such file, not in dyld cache)`: the file only exists in the OS cryptex and dyld does not search cryptexes at ignition_level=1. 19 cryptex files have no root counterpart (OS: DriverKit dyld cache + .symbols, VisualTestKit, libffi-trampolines, libobjc-trampolines, libstdc++ 6.0.9 + 2 symlinks; App: SafariSupport.bundle, AuthenticationServicesAgent, com.apple.Safari.History, passwordbreachd, safarifetcherd, webbookmarksd, webinspectord, webpushd) -> hard-linked (symlinks copied: Linux hfsplus cannot hard-link symlinks); `tools/mkiosroot.sh` does it generically. watchdogd still crashed: the `-wdt_no_pmu` / `/arm-io/wdt no-pmu` check (0x10000a01c) only runs when os_variant_has_internal_diagnostics; otherwise 0x100009b18 looks up IOServiceMatching("IOService") + IOPropertyMatch {IOPMUPrimary: 1} (NSConstantDictionary) and crashes if absent, then IORegistryEntrySetCFProperty(boot stage 0xff) (failure only logged). Patch **0045**: IOWatchdog sets IOPMUPrimary = 1 and accepts setProperties; CI `38961814194` -> `xnu/out-0045`. **Image v6** = v5 + the 19 cryptex links, SHA256 7c610c6a...297a, `ios16-root-20H392-v6.simg` (full flash needed). Boot image `shim/out/shim-boot-0045n.img` (0045 + sweet-0044hi.adt). Still open: SpringBoard (no display), backboardd (uncaught exception, reason none), mediaserverd (Fig NULL dict), logd (main+0x18160), lockdownd (main+0x4c1b4).
- **System survives daemon crashes (boot 0043p, video frames VID_20261016_215006 00:25/00:42/00:54).** With the v5 plist patch no panic: launchd keeps launching (runningboardd, powerd, tccd, healthd, peopled, cryptexd, routined, aksd, mediaremoted, familynotificationd, nanoprefsyncd, navd, cloudpaird, passd, amsaccountsd, accessoryupdaterd, wcd ...). Shared cache slide that boot 0x406b4000 (`research/crash-0043p.txt`). watchdogd still crashed at main+0xb82c from the PMU step: `-wdt_no_pmu` is only honored when os_variant_has_internal_diagnostics; customer builds read `no-pmu` from IODeviceTree:/arm-io/wdt (IORegistryEntrySearchCFProperty) -> mkadt adds /arm-io/wdt {no-pmu}. **cryptexd** sig 6: abort_with_payload <- os_crash_fmt <- `__darwin_arm_secure_boot_chip.cold.7` ("panic: failed to get crypto algorithm") <- `_img4_chip_select_personalized_ap`: reads /chosen use-ddi-secure-boot, allow-ecid-mismatch, crypto-hash-method ("sha1" | "sha2-384"), /chosen/asmb lp-smb0/1 -> mkadt adds crypto-hash-method "sha2-384". **identityservicesd** sig 6 = same `_objc_fatal` in imp_implementationWithBlock as CommCenter (block trampolines; message needed). lockdownd sig 5 at main+0x4c1b4. Patch **0044**: crash report adds `CRASH name reason ns N code X: text` (exit reason description = abort_with_payload text). CI `38959096811` -> `xnu/out-0044`, QEMU OK. Image `shim/out/shim-boot-0044n.img` = 0044 + `shim/out/sweet-0044hi.adt` (wdt no-pmu, crypto-hash-method) + cmdline (wdt=-1, no -wdt_no_pmu).
- **First symbolicated daemon crashes (boot 0043u on journaled v4, 19:38:53 UTC; video frame chat image 36; transcribed in `research/crash-0043u.txt`; shared cache slide 0x40d60000 for every process).** (Gemini's video transcription invented values, use frames only.) `tools/sweet-crash.py research/dsc/dyld_shared_cache_arm64 x research/crash-0043u.txt`:
  - **watchdogd** pc main+0xb82c (`_os_crash` trap helper) from 0x100009bb0 = set PMU boot stage via IORegistry (no PMU) -> fix: boot-args `wdt=-1 -wdt_no_pmu` (Apple's own test mode writes "%s wdt=-1 -wdt_no_pmu"; watchdogd logs "skipping setting PMU boot stage because -wdt_no_pmu found in boot-args or no-pmu found in EDT"). Kernel effect of wdt=-1: sched hygiene debug off, zone_exhausted_timeout -1 (harmless).
  - **SpringBoard** sig 5 in `-[FBSDisplayMonitor _initWithBookendObserver:transformer:]+1160` <- `+[FBDisplayManager sharedInstance]` <- `FBSystemShellInitialize` <- `SBSystemAppMain`: no main display. GUI WALL: display service (IOMobileFramebuffer / CoreAnimation display).
  - **backboardd** sig 6: abort <- std::terminate <- _objc_terminate (uncaught exception; message not shown).
  - **CommCenter** sig 6: `_objc_fatal` in `imp_implementationWithBlock` (from `+[_PFRoutines initialize]`, CoreData): objc block trampolines cannot be allocated -> likely kernel gap (trampoline page remap); will hit many processes.
  - **mediaserverd** sig 11: CFDictionaryGetValue(NULL) in FigNotificationListenerStartNotifications (routing session manager).
  - **logd** sig 5 at its main+0x18160 (bt main+0x9dfc); lockdownd sig 5 (not yet symbolicated).
  - Image v5 = v4 + launchd.plist (`/System/Library/xpc/launchd.plist`, contiguous at image offset 0x1e025f000, 1456980 bytes) with the 7 `_PanicOnCrash` keys renamed `_PanicOnCrasX` in place (raw image patch, no metadata change) -> `diff-v4-v5.simg` = 7 blocks; v5 SHA256 78f96974...185a. Boot image `shim/out/shim-boot-0043p.img` = 0043 + `wdt=-1 -wdt_no_pmu`.
- **0043 console crash reports (QEMU verified); image `shim/out/shim-boot-0043u.img`; NEXT: flash v4 + boot 0043u.** Boot 0042u (video photo IMG_20261016_211646): short exec lines work; watchdogd crashes with NO `SWEET WDT:` line (fails before its first IOWatchdog call: lookup or IOServiceOpen, or elsewhere); lockdownd, SpringBoard, mediaserverd, CommCenter, identityservicesd, backboardd, watchdogd all crash repeatedly ("Too many corpses being created" = corpse limit, no crash reports). AKS callers: lockdownd (0, 7), imagent/sleepd (0, 17, 7), backboardd (0, 17), UserEventAgent (0, 7, 102, 103 -> unsupported). Patch **0043**: `sweet_crash_log` (osfmk/kern/exception.c, called from proc_prepareexit for crash exits on the current proc) prints `CRASH name[pid] sig S code (exc<<32|code) sub X slide SR mh MH`, `CRASH name pc lr sp fp far`, `CRASH name bt` (10 fp frames); AKS sel 103 notify_state_is_set -> 0. CI `38954520419` -> `xnu/out-0043`. QEMU test: init forks, child `brk #1`: `CRASH launchd[2] sig 5 code 0x600000001 sub 0x1000004f0 slide 0x0`, pc correct, parent keeps running (pid 1 crashes panic before proc_prepareexit, so test with a child). `tools/sweet-crash.py CACHE ROOT [report]` symbolicates typed-in CRASH lines (`ipsw dyld a2s` with addr - slide; main binary offsets = addr - mh + 0x100000000).
- **v3 reflashed 18:50-18:55 UTC (`research/flash-userdata-v3b.log`, 24/24 OKAY); 0042u booted 19:01:17 UTC on the clean disk (`research/boot0042u-2.log`), SLOW MO VID pending (watchdogd failure reason).** ABL hangs on the first `fastboot boot` after every big flash; user re-enters fastboot. User gave standing approval to reflash/boot without asking (memory standing-flash-approval). Commits now end with `Co-Authored-By: dipa-studio <183933817+dipa-studio@users.noreply.github.com>` (user request; never a Claude trailer).
  - watchdogd flow: connect_to_kext (0x100005408): IOServiceGetMatchingService("IOWatchdog") fails -> "failed to discover" + _os_crash; IOServiceOpen(type 1) fails -> "IOServiceOpen failed with error : 0x%x" + _os_crash. Then sel 0 (out 1 scalar): 0 -> "userspace monitoring disabled", 0x100009bb0, sleep 2, exit(0); nonzero -> "userspace monitoring enabled", normal operation.
  - **Image v4 (JOURNALED):** `tools/mkiosroot.sh` now does `mkfs.hfsplus -J`, mounts with `-o loop,force`, adds the /System/Library/Caches/com.apple.dyld hard links (44) and /private/var/keybags/systembag.kb (0700/0600 root). Built from the IPSW dmgs (OS 087-86698-044, SystemOS 087-86593-047, AppOS 087-86715-047) -> `/run/media/dipa/android/ios-sweet-ipsw/ios16-root-20H392-v4.img` SHA256 fba4aeae...ec0f9 + `.simg`. Header: attr 0x80002100 (unmounted, journaled), journal info block 129, journal 8 MiB at 532480 flagged need-init. Linux `fsck.hfsplus -n` reports "Volume header needs minor repair" on any fresh journaled volume even after -y (quirk). QEMU: 64 MB journaled test root (`rd=md0 rootrw=1`, 0042 kernel): `hfs: Initializing the journal (joffset 0x3000 sz 0x80000)` -> mounted -> init runs, no panic. NEXT: flash v4 (full), boot 0042u.
- **SPRINGBOARD STARTS (boot 0041u 18:39:53 UTC, photo IMG_20261016_204142).** backboardd, bluetoothd, fairplayd.H2, SpringBoard (pid 111, crashed: "Too many corpses"), xpcproxy run; `SWEET AKS: backboardd sel 0 -> 0`, `sel 17 in 1/0 out 0/4096 -> 0`. Panic: watchdogd[113] exited, namespace 2 subcode 5 (SIGTRAP = its _os_crash): watchdogd crashes on purpose when IOServiceGetMatchingService("IOWatchdog") fails ("connect_to_kext() unexpectedly failed") or IOServiceOpen(type 1) fails ("IOServiceOpen failed with error"); IOWatchdog DOES register (QEMU msgbuf: `SWEET WDT: IOWatchdog registered`), cause not on screen yet -> need video. Note `wdt_test=no_user_checkin` makes watchdogd log "detected testing boot-args to not run, exiting" (path not reached here?). **HFS CORRUPTION:** `hfs_swap_BTNode: offset #0 invalid (0xBC1D) (blockSize 0x2000 numRecords 81)`, `node=19677 fileID=4` (catalog), `hfs_mark_inconsistent` repeated. Likely cause: non-journaled HFS + unclean panics while writing (0038e wrote a 2.7 GB core then panicked; every boot since ends in panic). Plan: reflash v3 (clean), longer term HFS journaling. Patch **0042**: one short `exec NAME` console line instead of the 3-line "Allowing spawn of iOS binary" notice; CI `38949451276` -> `xnu/out-0042`; image `shim/out/shim-boot-0042u.img` (same cmdline as 0041u).
- **LAUNCHD DAEMONS RUN (boot 0039u, 18:29:13 UTC, photo IMG_20261016_203052).** With `launchd_unsecure_cache=1` all boot tasks pass and launchd starts LaunchDaemons (pids > 100: identityservicesd 114 and lockdownd 106 crash, "Too many corpses being created"). Fatal: `watchdogd: ERROR: failed to discover watchdog KEXT service` -> exit (namespace 2 = signal, subcode 5) -> `_PanicOnCrash` panic. watchdogd: IOServiceMatching("IOWatchdog"), IOServiceOpen type 1, IOConnectCallScalarMethod sel 0/1 (check in)/3/4 (disable/enable userspace monitoring)/5, IOConnectCallStructMethod sel 2 (1 KiB in) and 9 (small out); VM path ("detected virtual machine environment and no watchdog KEXT found, exiting...") only when it detects a VM. Console also flooded with `hfs: set hardlink bit on vol=iOSRoot cnid=321318` (Linux-made hard links lack kHFSHasLinkChainBit; repaired only in memory on each lookup). Patches **0040** (`iokit/Kernel/arm/SweetWatchdog.cpp`: IOWatchdog + IOWatchdogUserClient, all selectors succeed with zeroed outputs, each logged once as `SWEET WDT: ...`) and **0041** (sweet_hfs hfs_catalog.c: the three link-repair printfs limited to 8 per boot); CI `38948245372` PASSED -> `xnu/out-0041` (QEMU regression OK). Image `shim/out/shim-boot-0041u.img` (0041 + sweet-0038hi.adt + ufsrw rootrw + launchd_unsecure_cache=1) booted 18:39:53 UTC (`research/boot0041u.log`), photo pending.
- **v3 FLASHED + keybag passes; next wall AMFI (launchd_cache_loader).** User said "flash, nothing to lose": `fastboot -S 512M flash userdata ios16-root-20H392-v3.simg` 17:51:52-17:57:01 UTC, 24/24 chunks OKAY (`research/flash-userdata-v3.log`). userdata = v3 (SHA256 fa84274c...22df) until the next rw boot. ABL fastboot then hung ("Sending" forever, `reboot bootloader` timed out) until the user re-entered fastboot by hand (common Xiaomi ABL crash). Boot 0038e 18:06:15 UTC (`research/boot0038e-3.log`), photos IMG_20261016_200812/200838: keybag OK, then boot tasks tzinit (`Bad zoneinfo link`, resets to system partition, OK), finish-restore, finish-demo-restore, sysstatuscheck, prng_seedctl (`failed to load kernel prng seed`, `failed to load virtual random (-147)`, AllowCrash), auearlyboot, then **launchd_cache_loader: `abort: Unable to find AMFI`** -> 2.7 GB core written to /cores in 91 s -> launchd panic `launchd_cache_loader[22] exited -- exit reason namespace 7 subcode 0x1`. launchd_cache_loader: SecStaticCodeCheckValidity of /System/Library/xpc/launchd.plist with detached .sig, then IOServiceMatching("AppleMobileFileIntegrity") + IOServiceOpen type 0 + IOConnectCallMethod sel 6 (1 scalar = 1, struct in = cdhash) = trust the cdhash, then sends the cache to launchd. Boot-arg `launchd_unsecure_cache=1` skips signature + AMFI ("Using unsecure cache"); the value is parsed with strtoul base 10 (helper 0x100002da8), so a path = 0 = off: boot 0039w (18:17:13 UTC, `=/System/Library/xpc/launchd.plist`, photo IMG_20261016_202008) still aborted `Unable to find AMFI` (core dump now skipped: `Failed to generate core file ... error 14`, so 0039 works). Image `shim/out/shim-boot-0039u.img` uses `launchd_unsecure_cache=1`. Patch **0039**: do_coredump = 0 on SWEET (kern.coredump sysctl still works); CI `38945267341` -> `xnu/out-0039` (_do_coredump now in __common). Image `shim/out/shim-boot-0039w.img` = 0039 + sweet-0038hi.adt + ufsrw rootrw + `launchd_unsecure_cache=/System/Library/xpc/launchd.plist`. TODO later: real AppleMobileFileIntegrity IOService (sel 6 trust cdhash etc.).
- **Image v3 ready, awaiting user "flash".** Boot 0038w 17:38:10 UTC, photo (chat image 30): `SWEET AKS: keybagd sel 0 -> 0x0`, `sel 14 out 1/0 -> 0x0` (x2), `MKB_INIT: mount is with NO CPROTECT ... does not support Data Protection`, `System Keybag loaded`; then keybagd still opens /private/var/keybags/systembag.kb (0x100012d3c, for BackupKeyBagKeys) -> ENOENT, `no-effaceable-storage` not set -> `Can't load the keybag. tears in rain... Time to die` -> `FATAL KEYBAG ERROR: kb_load` -> reboot -> Halt/Restart Timed Out panic. Fix: ADT `/defaults/no-effaceable-storage` (mkadt.py; `shim/out/sweet-0038hi.adt`, `research/q0038-hi.adt`, QEMU OK) + file `/private/var/keybags/systembag.kb` (0600 root, dir 0700; XML plist {KeyBagKeys: data}). **v3 image** `/run/media/dipa/android/ios-sweet-ipsw/ios16-root-20H392-v3.img` = v2 + that file, fsck OK, SHA256 fa84274c...22df; `ios16-root-20H392-v3.simg` (img2simg: zero blocks become FILL chunks, so a full flash overwrites every block the rw boots changed). Flash: `fastboot -S 512M flash userdata ios16-root-20H392-v3.simg`, then boot `shim/out/shim-boot-0038e.img` (0038 + sweet-0038hi.adt + ufsrw=1 rootrw=1).
- **0038 AppleKeyStore (CI 38938744130 PASSED -> `xnu/out-0038`; QEMU msgbuf: `SWEET AKS: AppleKeyStore registered (no passcode, unlocked)`; phone image `shim/out/shim-boot-0038w.img` booted 17:38:10 UTC, `research/boot0038w.log`, photo pending).** QEMU full kernel log trick (fb.txt is only the last screen): `llvm-nm KERNEL | grep _msgbufp` -> `--hmp "x /1gx ADDR"` gives struct msgbuf address (static, 0xfffffe0007b56678 on 0038) -> `--hmp "x /3gx STRUCT"` gives bufc (3rd quad) -> `--hmp "memsave BUFC 0x20000 \"FILE\""` (quote the file name), `tr -d "\0" < FILE`. Same inputs give the same addresses. Boot 0037w 17:08:35 UTC, photo IMG_20261016_191052: bindfs fixed mount; mount-phase-1/2 pass; `cc_fips_test` boot task: all corecrypto FIPS POST tests PASSED in userspace; then keybag boot task `keybagd --init`: `MKB_INIT: FATAL KEYBAG ERROR: failed to load system bag`, `Could not get options entry from the device tree` (x2, IODeviceTree:/options = NVRAM, non-fatal), `REBOOTING INTO RECOVERY MODE` -> reboot -> panic `Halt/Restart Timed Out @IOPlatformExpert.cpp:884` (no restart path on SWEET).
  - keybagd (static libaks): load_devicebag (0x100012c30) calls aks_get_system (sel 14, 0-1 scalar in, 1 out) and loads /private/var/keybags/systembag.kb only if the result is 0xe00002f0 (NotFound); any other error -> fatal; SUCCESS -> skip the file (userspace-reboot path). systembag.kb is a plist {KeyBagKeys}; decrypted with effaceable storage unless IODeviceTree:/defaults has `no-effaceable-storage`. Image has no /private/var/keybags. has_data_protection: statfs of /private/var; no cprotect on our HFS -> device-bag volume mapping skipped.
  - libaks connection: IORegistryEntryFromPath / IOServiceMatching("AppleKeyStore"), IOServiceOpen type 0, then selector 0 (no args) must succeed.
  - **AppleKeyStore selector map (iOS 16.7 AppleKeyStore.framework, via `ipsw dyld disass`):** 0 open, 2 create_bag, 3 save_bag, 4 unload_bag, 5 set_system_with_passcode, 6 load_bag, 7 get_lock_state (1 in, 1 out; bit 2 = unlocked since boot), 9 unlock_device, 10 wrap_key, 11 unwrap_key, 12 unlock_bag/test_stashed_kek, 13 lock_bag, 14 get_system, 15 change_secret_se, 16 internal_state, 17 get_device_state (1 in, struct out <=4K: DER SET of SEQUENCE{UTF8 key, INTEGER}: ss state, sls lock_state (MKBGetDeviceLockState returns it), sb backoff, sbo, sfa failed attempts, sfao, sgs generation, sas assertions, sgpe grace, srcd countdown, sr reserved), 18 recover_with_escrow_bag, 19 obliterate_class_d, 20 drain_backup_keys, 21/22 set/clear_backup_bag, 23 get_bag_uuid, 24 rewrap_key_for_backup, 26/27 assert_hold/drop, 30/31 set/get_configuration, 33-37 stash, 38 auth_token_create, 40 generation, 41 fdr_hmac_data, 42 verify_password, 43 _aks_operation, 44 remote_session, 49/50 signing keys, 51/53/54 stash enable/persist/escrow, 55 unload_session_bags, 57/58 remote peer, 59-62 smartcard, 63 migrate_s_key, 65 set_keybag_for_volume_with_cookie_persona, 66/67 sync bags, 68 copy_volume_cookie_persona, 69-73 se_*, 74-79/84/85/99 fv_* (FileVault/VEK), 80/81 absinthe, 82 make_public_backup_bag, 83 drop_auxiliary_auth, 86 kext get/set options, 87 invalidate_bag, 88-91/94/95/106/107 se_*, 92 lower_iteration_count, 93 get_internal_info, 96-98/117 keybag_persona create/list/delete, 100/101 assert promote/consume, 102/103 notify_state set/is_set, 104 fairplay, 105 change_secret_epilogue, 108 delete_xart_leak, 110-113 backup volume, 114 sealed_hashes_set, 115 prewarm_sps, 118-128 AKSIdentity*/AKSGetLastUser.
  - Patch **0038**: `iokit/Kernel/arm/SweetKeyStore.cpp` (class AppleKeyStore on IOResources, IOUserClientClass AppleKeyStoreUserClient; personality in KernelConfigTables.cpp): 0/4/5/9/12/13/26/27/55/102 success, 14 -> handle 0, 7 -> 0x4, 17 -> DER state (ss 4, sls 0), others kIOReturnUnsupported; logs `SWEET AKS: <proc> sel N arg0 in a/b out c/d -> ret` for every call.
  - Tools: shared cache copied to `research/dsc/` (git-ignored; ipsw needs a writable dir for its .a2s symbol cache); `ipsw dyld disass research/dsc/dyld_shared_cache_arm64 --image AppleKeyStore|MobileKeyBag`; scratchpad `annot2.py BIN DIS FIXUPS` annotates llvm-objdump output with strings and import names (`ipsw macho info --fixups`).
- **0037 bindfs (phone boot 0037w pending photo).** Boot 0036mw 16:57:47 UTC, photo IMG_20261016_190102: WRITABLE ROOT WORKS: `/dev/ufsroot0 on / (hfs, local, noatime)` after mount_hfs update (GetMasterBlock EBUSY harmless), coredump of mount written to /cores (rw). Then `mount: failed to mount /private/preboot/5CBE3601.../usr/standalone/firmware -> ...: Operation not supported by device (19)` -> exit 74 -> launchd panic `mount[2] exited`. Cause: the macOS-derived config had nullfs but no bindfs (ENODEV = unknown fs type). Caller passes env 0 -> bind not required, ENOENT (missing source dir) tolerated. Patch **0037** adds `bindfs` to FILESYS_BASE in MASTER.arm64.sweet; CI `38936550483` -> `xnu/out-0037` (bindfs_vfsops present; QEMU probe regression OK). Image `shim/out/shim-boot-0037w.img` (0037 + sweet-0036hi.adt + ufsrw=1 rootrw=1) booted 17:08:35 UTC (`research/boot0037w.log`). NOTE: userdata has now been modified by rw boots; it no longer equals the v2 image, so sparsediff with v2 as OLD is not safe any more (full reflash or a new baseline needed).
- **0036 phone: launchd boot tasks run; mount -P 1 needs /chosen/boot-manifest-hash.** Boot 0036hr 16:15:32 UTC, photo IMG_20261016_185236: platform check passes; fsck boot task runs (`fsck: not booting main or diagnostic OS. Skipping fsck on OS container`); mount-phase-1: `failed to get filesystem info` x2 (no IODeviceTree:/filesystems/fstab, non-fatal), `mount: data volume missing, but not required in env: 0`, mount_hfs update of /: `GetMasterBlock: Error 16 opening /dev/ufsroot0` (EBUSY, mounted block dev, non-fatal) then mount() EROFS (read-only boot) -> `mount: / failed with 1`; then `failed to get boot-manifest-hash` -> errx exit 66 -> launchd panic `mount[3] exited`. /sbin/mount: fn 0x100005f90 reads IODeviceTree:/chosen boot-manifest-hash (hex), bindfs-mounts /private/preboot/<HEX>/usr/standalone/firmware (ENOENT tolerated unless required). `tools/mkadt.py` now adds `boot-manifest-hash` = SHA-384("sweet boot manifest") (5CBE3601...5205). ADTs `shim/out/sweet-0036hi.adt`, `research/q0036-hi.adt` (QEMU probe OK, csops 0x26000001). Image `shim/out/shim-boot-0036mw.img` (0036 + new ADT + ufsrw=1 rootrw=1), booted 16:57:47 UTC (`research/boot0036mw.log`): FIRST WRITABLE BOOT of userdata (restore source: v2 image on SSD).
- **0036 CS_SIGNED (phone boot 0036hr pending photo).** Phone boot 0035hr 2026-10-16 15:57:02 UTC (`research/boot0035hr.log`, photo IMG_20261016_180249): highmem works on hardware; shared cache maps (trust-cache warnings only), Apple launchd runs (`Darwin Bootstrapper Version 7.0.0`, `entering ondemand mode`), starts boot task fsck, then userspace panic `boot task is not a platform binary (fsck, /sbin/fsck)`. launchd+0x3fea0: `csops(pid, CS_OPS_STATUS)` must have bit 0x04000000. Cause: nothing set CS_SIGNED (AMFI does it in vnode_check_signature), so csproc_get_blob() returns NULL for every process and csops never reports CS_PLATFORM_BINARY (also breaks per-process cdhash/entitlement queries). QEMU probe init (`csops` status printer, scratchpad csq/) on 0035: `0x02000001`; patch **0036** (`*cs_flags |= CS_SIGNED` in the SWEET AMFI hook), CI `38929635791` -> `xnu/out-0036`: `0x26000001`. Images `shim/out/shim-boot-0036hr.img` / `-0036hw.img` (same cmdlines as 0035). 0036hr booted 16:15:32 UTC (`research/boot0036hr.log`). Next launchd boot tasks (embedded __config plist): fsck -qL and mount -P 1/2 (RequireSuccess); no /etc/fstab on the image.
- **0035 ENTITLEMENTS + PLATFORM BINARIES (QEMU verified).** `xnu/patches/0035-sweet-amfi-entitlements-platform-binaries.patch`: new `iokit/Kernel/arm/SweetEntitlements.cpp` (OSObject subclass: OSDictionary from OSUnserializeXML of the signature's XML entitlements + original XML for CS_OPS_ENTITLEMENTS_BLOB); `bsd/kern/sweet_amfi.c` answers queryEntitlementBoolean/String(+WithProc, string also matches array members), copyEntitlementAsOSObject(+WithProc, retained), asdict (retained), get_xml (kalloc_data copy); built-in MAC policy "SWEET AMFI" (registered from bsd_init before vfs/exec) with mpo_vnode_check_signature: every signed binary on the MNT_ROOTFS mount gets CS_PLATFORM_BINARY (stand-in for AMFI's static trust cache: iOS system binaries are ad-hoc, cd_flags 0x2, platform byte 0), and attaches entitlements ONLY for the writable copy (cs_blob != csb_ro_addr; revalidation passes the RO blob). LESSON: first version attached in adjustContextWithoutMonitor -> QEMU `unable to adjust OSEntitlements context without monitor: 53` because ubc_cs_convert_to_multilevel_hash (4K-page signatures on 16K kernel) sets csb_entitlements_blob = NULL; ALL iOS 16 binaries (launchd, backboardd, SpringBoard) use 4K code pages, so this would have broken launchd on the phone. Boot-arg `sweet_amfi_debug=1` logs `SWEET AMFI: <ident>: N entitlements (test: ...)`. `tools/mkinit.py OBJ OUT [ENTS.plist]` adds an XML entitlements blob (special slot -5; default output byte-identical). QEMU `research/q0035-ent` (RAM disk `research/root-hfs-ent.img`, init with 3 test entitlements, highmem): `org.sweet.init: 3 entitlements (test: bool 1 string 1 array 1)` then init PID 1. MAC policies loaded: 0034 = 1, 0035 = 2 (QMP `mac_policy_list`). CI `38909807230` -> `xnu/out-0035`. Phone images: `shim/out/shim-boot-0035hr.img` (highmem, ro), `-0035hw.img` (highmem, +ufsrw=1 rootrw=1), `-0035r.img` (low mem fallback).
- **PHONE TEST ORDER (updated):** 0035hr -> if instant reset, 0035r -> then 0035hw.

- **HIGHMEM: XNU in the upper DDR bank, ~3.95 GiB (was 1.2 GiB).** Live FDT memory = <0x80000000 2G> + <0x1_00000000 0xfcc00000>; all fixed reserved-memory carve-outs are in the low bank (highest: ramdump_fb 0xaf000000, rmtfs ~0xfde01000), dynamic pools have alloc-ranges <= 0xffffffff, UFS node has no `iommus` (Linux DMAs anywhere). `tools/mkadt.py --highmem` sets /chosen dram-base 0x100000000 dram-size 0xfcc00000; `tools/mkpayload.py` now takes phys_base/mem_size from the ADT (default payloads byte-identical, verified); `tools/qemu-sweet.py` sizes -m from the payload (8G for highmem). Patch **0034** (`0034-sweet-ufs-dma-above-4g.patch`): UFS refuses DMA memory above 4G without UFSHCI CAP.64AS (bit 24), logs `DMA at 0x...`. CI `38905889883` success -> `xnu/out-0034`. **QEMU verified** (`research/q0034-hi`, ADT `research/q0034-hi.adt` --qemu --highmem, HFS RAM disk): phys_base 0x100000000, init PID 1 heartbeat, no panic; `max_mem` = `mem_size` = 0xfcc00000 read via QMP (`research/q0034-hi-mem`). Phone images: `shim/out/shim-boot-0034hr.img` (read-only) / `-0034hw.img` (+ufsrw=1 rootrw=1), ADT `shim/out/sweet-0034hi.adt` (asmb SIP + sweet-ufs + highmem). PHONE RISK: unknown runtime TZ/XPU protection in the upper bank would show as an instant reset; fall back to 0033r/w. Watchdog ruled out for the overnight reset: msm-watchdog bark is 20 s (qcom,bark-time 0x4e20) yet panic screens stay up for many minutes.

- **Offline research 2026-10-16 (user away, phone unavailable). Images rebuilt** `shim/out/shim-boot-0033r.img` / `-0033w.img` now also carry `wdt_test=no_user_checkin`. NEXT ON PHONE: boot 0033r (expect past in6_nigroup), then 0033w (first writes: rw root fixes HFS link-chain bits itself and gives /var for launchd sockets /var/run/syslog, /var/run/lockdown.sock).
- **launchd.plist** (`/System/Library/xpc/launchd.plist`, compiled; 532 daemons, 66 RunAtLoad/KeepAlive, list in scratchpad `early-daemons.txt`). `_PanicOnCrash` daemons: containermanagerd/usermanagerd (InternalOnly), lockdownd/remoted/trustd/remotepairingdeviced (AutomationOnly), **watchdogd unconditional** (KeepAlive SuccessfulExit=false). watchdogd needs IOKit `IOWatchdog` kext service; if absent it exits only when `kern.hv_vmm_present` (ADT `/defaults/vmm-present`, hvg_sysctl.c) or with boot-arg `wdt_test=no_user_checkin` ("detected testing boot-args to not run, exiting"; reads kern.bootargs). Using the boot-arg (vmm-present would change many daemons; keep as an option).
- **GUI path research (QuartzCore in the shared cache, `ipsw dyld str CACHE STR`, ~10 s/search):** CA::WindowServer has IOMFBServer/IOMFBDisplay (Apple DCP/IOMobileFramebuffer), AppleCLCDDisplay, AppleRGBOutDisplay, **VirtualServer/VirtualDisplay** and **MemorySurface**, EAGLServer. Renderers: CA::OGL::MetalContext, GLContext and a **CPU software rasterizer CA::OGL::SW** (samplers/blend modes; "image is too large for software renderer"). Env knobs: `CA_ENABLE_OGL`, `CA_DISPLAY_TYPE`, `CA_FORCE_LOCAL_SERVER` (249 CA_* vars). Hypothesis (unverified): backboardd's render server could run a VirtualServer/MemorySurface with the SW renderer and we copy the surface to the ABL framebuffer -> needs disassembly of CA::WindowServer server creation. Expected other GUI walls: IOSurface (closed-source kext; needs a reimplementation), IOMobileFramebuffer user client, IOHID touch events, AppleKeyStore/keybag (SEP) for lock state, MobileGestalt answers (AppleCLCD etc.).

- **0032r RESULT (boot 05:07:50 UTC, `research/boot0032r.log`, photo IMG_20261016_071200): SHARED CACHE MAPPED, LAUNCHD RUNS.** With SIP relaxed (ADT asmb) the `not in trust cache` lines are only warnings for every subcache (.31 ... .42.dyldlinkedit); no SIP rejection; libSystem loads; launchd configures networking (`skip attaching fsw to lo0 using legacy TX model`) -> kernel data abort far 0x28 in `SHA1Init` (symbolized as sha1_init) from `in6_nigroup` (IPv6 on lo0): g_crypto_funcs NULL. Kernel addresses are unslid: `~/swift/usr/bin/llvm-symbolizer --obj=KERNEL ADDR` works directly.
- **0032** BearSSL SHA-1 (`0032-sweet-bearssl-sha1.patch`), **0033** BearSSL SHA-384/512 (`0033-sweet-bearssl-sha384-sha512.patch`, BearSSL ctx stored in SHA512_CTX, static-asserted to fit; ubc_subr.c uses SHA-384 for code directories). `0020-stage-bearssl.sh` now also stages hash/sha1.c, hash/sha2big.c, codec/{dec,enc}{32,64}be.c. CI `38854909053` success (0032-only run `38854802073` superseded). Kernel `xnu/out-0033` (SHA1Init -> _br_sha1_init verified by disassembly; nm symbols have a leading underscore). Images (ADT sweet-0032): `shim/out/shim-boot-0033r.img` (read-only), `shim-boot-0033w.img` (+ufsrw=1 rootrw=1). Still NULL g_crypto_funcs users: des, chacha20poly1305, rsa, aesxts, rand, flow_divert.
- `research/check-patch-order.py` now skips patches touching CI-staged sweet_hfs sources (0031) instead of stopping.

- **0031r RESULT (boot 05:03:52 UTC 2026-10-16, `research/boot0031r.log`, photo IMG_20261016_070508): SHARED CACHE FOUND.** dyld now opens `dyld_shared_cache_arm64` (v2 image hard links), kernel refuses to map it: `shared_region: ... map(...'dyld_shared_cache_arm64'): not in trust cache` -> `vnode is not SIP-protected` (vm_unix.c: macOS arm64 path needs trust cache, else root-owned + SF_RESTRICTED unless CSR_ALLOW_UNRESTRICTED_FS) -> `dyld cache '(null)' not loaded: syscall to map cache into shared region failed` -> libSystem not loaded -> coredump to /cores fails error 30 (EROFS) -> panic initproc failed -> "MACH Reboot" (spins; screen kept). Lots of `hfs: set hardlink bit on vol=iOSRoot cnid=... linkid=...` spam (Linux-made hard links lack the link-chain bit; read-only mount cannot persist the fix). FIX: ADT `/chosen/asmb` with `lp-sip0`=0x6f (u64; incl. CSR_ALLOW_UNRESTRICTED_FS) and `lp-sip1`=1 (unauthenticated root), `tools/mkadt.py` -> `shim/out/sweet-0032.adt`. Images with kernel 0031: `shim/out/shim-boot-0032r.img` (read-only) and `shim-boot-0032w.img` (+ufsrw=1 rootrw=1).

- **2026-10-16 morning:** userdata now = **v2** image (`diff-v1-v2.simg` flashed 21:06:50 UTC 2026-10-15, OKAY, `research/flash-userdata-diff-v2.log`); future diffs use `ios16-root-20H392-v2.img` as OLD. Booted `shim-boot-0029k.img` (ignition_level=1) right after (`research/boot0029k-v2.log`); **no photo** (user asleep). Next morning the phone was in PixelOS recovery = some hardware reset (ABL then booted Android, which cannot use userdata). OBSERVATION: our kernel cannot reset the SoC itself (`PE_halt_restart` is never set; reboot/halt print "MACH Reboot"/"CPU halted" and spin), so the reset came from outside XNU: Qualcomm watchdog or a TZ/XPU violation. Unknown which; re-boot 0029k and watch/video until the reset. Do NOT tap factory reset/format data in recovery (would wipe the iOS image).
- **0030** (`xnu/patches/0030-sweet-ufs-writes.patch`, CI `38852655542`): UFS WRITE(10) + read-modify-write for partial 4 KiB blocks + SYNCHRONIZE CACHE (DKIOCSYNCHRONIZE), only with boot-arg `ufsrw=1`; `ufs_write_blocks` re-checks partition bounds before every write (only place data goes out).
- **0031** (`xnu/patches/0031-sweet-read-write-root.patch`, CI `38852837176`): boot-arg `rootrw=1` clears MNT_RDONLY before the root mount (no data volume on sweet: /private/var is on the root; image has no /etc/fstab); Apple HFS accepts a dirty non-journaled ROOT read-write on SWEET (logs "mounting dirty non-journaled root read-write"). Later: journaled HFS for crash safety. Kernel `xnu/out-0031` (CI `38852837176` success, 5m31s; 0030 run cancelled by the newer push). Boot images (phone ADT `sweet-0028.adt`, ramdisk byte-matched): `shim/out/shim-boot-0031r.img` = 0029k args (read-only, ignition_level=1) and `shim/out/shim-boot-0031w.img` = same + `ufsrw=1 rootrw=1`. PLAN: boot 0031r first and film until the reset (diagnose overnight reset), then 0031w (first ever writes to userdata; v2 image on the SSD is the restore source). `research/check-patch-order.py` cannot check 0031 (staged sweet_hfs files are not in its index); CI stage scripts run first, so CI is the check.

- **ignition_level=1 result** (boot 21:01:39 UTC, `research/boot0029k.log`, photo IMG_20261015_230308): preboot/cryptex stages skipped (need >= 2/3), `dylib_cache: finding shared cache on system volume: ignition level = 1, search root fd = 4, subpath = System/Library/Caches/com.apple.dyld/` -> not found -> `ignition boot failed: 19` -> no shared cache -> libSystem not loaded. FIX IN PROGRESS: image v2 = copy of the flashed image + `/System/Library/Caches/com.apple.dyld/` with HARD LINKS to the 44 cryptex cache files (no extra space; avoids symlink-following doubts), then `tools/sparsediff.py ios16-root-20H392.img ios16-root-20H392-v2.img diff.simg` and flash only the diff. Boot with `ignition_level=1` (shim-boot-0029k.img).
- **ignition_level=0 result** (boot 20:58:07 UTC, `research/boot0029j.log`, photo IMG_20261015_230037): all stages skipped as "ignition level insufficient" (hello/preboot/cryptex1 sniff >= 2, select os cryptex path/graft >= 3, **dyld_cache >= 1**), `ignition boot failed: 89`, "ignition partially disabled", then same `Library not loaded: /usr/lib/libSystem.B.dylib (no such file, no dyld cache)`. => dyld gets the shared cache directory from ignition's dyld_cache stage. Next: `ignition_level=1` (`shim/out/shim-boot-0029k.img`) to skip preboot/cryptex stages but run dyld_cache; its log "finding shared cache on %s ... subpath = %s" will show where it searches. If it searches rootfs /System/Library/Caches/com.apple.dyld, add a symlink there (image rebuild; consider a diff-only sparse flash tool to avoid rewriting 12 GB).
- **APPLE dyld/launchd RUNNING (libignition) with `unentitled_ios_sim_launch=1`** (boot 20:53:24 UTC, `research/boot0029i.log`, photo IMG_20261015_225617): kernel prints "Allowing spawn of iOS binary ... boot-arg set to true"; `shared_region: ... check_np ... vm_shared_region_start_address() failed` (no region yet, normal); dyld's built-in **libignition** (Darwin Ignition Sequence 1.0.0, libignition-51~1974; prints rd=ufsroot0, hardware target sweet, ignition level 0x5, platform 0x2, boot spec local, 7 stages): `hello from launchd.1` -> `preboot: mounting preboot` -> `failed to lookup preboot: 25` (ENOTTY: looks for a separate Preboot volume by role) -> ignition fails -> dyld `Library not loaded: /usr/lib/libSystem.B.dylib ... (no such file, no dyld cache)` -> launchd exit -> panic initproc failed. dyld boot-args found via strings: `ignition_level`, `ignition_force_dylib_root` (forced rootfs/livefs/cryptex fallback), `ignition_halt_after`, `ignition_live_app_graft`; dyld cache search paths include /System/Cryptexes/OS, /System/Volumes/Preboot/Cryptexes/OS/, /private/preboot/Cryptexes/OS/ (present in our image). Next try `ignition_level=0` (`shim/out/shim-boot-0029j.img`).
- **APPLE launchd EXECUTED FROM UFS (2026-10-15).** Flashed iOS image: `img2simg` -> `ios16-root-20H392.simg` (12.1 GB) then `fastboot -S 512M flash userdata ...simg` (24 chunks, 307 s, `research/flash-userdata-ios16.log`; a raw-image flash was killed by earlyoom at 2.6 GB RSS - always flash the sparse image). ABL fastboot hung on getvar after the flash; power+vol-down fixed it. Boot 0029u 20:49:04 UTC (`research/boot0029u-ios16.log`), photo IMG_20261015_225134: `hfs: mounted iOSRoot` -> load_init_program /sbin/launchd -> panic `unexpected SIGKILL of launchd (CS_KILLED) with reason -- namespace 9 code 0xe` = OS_REASON_EXEC / EXEC_EXIT_REASON_WRONG_PLATFORM: our kernel is XNU_TARGET_OS_OSX, iOS-platform binaries are "alien" and refused unless spawn attr platform set or DEVELOPMENT TUNABLE `unentitled_ios_sim_launch`. Next try: same kernel, cmdline + `unentitled_ios_sim_launch=1` (`shim/out/shim-boot-0029i.img`). LONGER TERM: macOS-config kernel marks iOS maps alien (vm_map_mark_alien) and differs from iOS in many policies; an iPhoneOS-config kernel build may eventually be needed.
- **iOS 16 ROOT IMAGE BUILT:** `/run/media/dipa/android/ios-sweet-ipsw/ios16-root-20H392.img` (16 GiB case-sensitive HFS+, label iOSRoot, 12 GB used, fsck OK after `fsck.hfsplus -y` rewrote 32 non-ASCII localized WorkflowKit Shortcut names Linux decomposes differently). Built by `tools/mkiosroot.sh OS.dmg SYSTEMOS.dmg APPOS.dmg OUT.img [SIZE]` (needs sudo; apfs-fuse as root; OS dmg is UDIF -> link must end .dmg). Contents: iPhone X 20H392 OS root + SystemOS cryptex at /private/preboot/Cryptexes/OS (so /System/Cryptexes/OS -> cache, 44 files, dyld_v1 arm64) + AppOS at .../App. /sbin/launchd and /usr/lib/dyld root:wheel 0755. NEXT: (confirm) `fastboot flash userdata ios16-root-20H392.img` (auto-sparse), boot 0029u (rd=ufsroot0) -> Apple launchd attempt.
- **MILESTONE ON HARDWARE: BOOT FROM INTERNAL FLASH.** 0029 CI `38797924912` PASSED, `xnu/out-0029` SHA256 `a68bc847...2a37`. Image `shim/out/shim-boot-0029u.img` (payload-0029u = 0029 kernel + `shim/out/sweet-0028.adt` + `rd=ufsroot0`, NO RAM disk). Boots 20:01:34 and 20:12:37 UTC (`research/boot0029u*.log`), photo IMG_20261015_221403: `SWEET UFS: "userdata" on LUN 0: first block 0x2b8c00, 109643 MiB, read-only` -> `BSD root: ufsroot0, major 1, minor 0` -> `hfs: mounted SweetRoot on device b(1, 0)` -> `SWEET: root volume is not authenticated (error 25); continuing unsealed` -> `load_init_program ... /sbin/launchd` -> `*** SWEET userspace: init running as PID 1 ***` -> heartbeat (ran for minutes unattended). userdata currently holds the 8 MB `research/root-hfs.img`. NEXT: build a multi-GB HFS+ image with the iOS 16 (iPhone X 20H392) userland (OS rootfs + SystemOS cryptex contents incl. dyld shared cache at /System/Library/Caches/com.apple.dyld; preserve modes/owners/symlinks; decompress LZBITMAP via apfs-fuse), flash it to userdata (sparse, needs user OK), then try Apple's dyld/launchd. Driver is read-only (root mounts RDONLY), fine for first launchd attempts.
- **userdata FLASHED with the 8 MB HFS test volume** (user said "flash it", 2026-10-15 19:53:17 UTC, `research/flash-userdata-hfs-test.log`: `fastboot flash userdata research/root-hfs.img` OKAY; pre-checks: one sweet device, partition-size:userdata 0x1AC4BFB000, partition-type f2fs, image fsck OK, SHA256 3626ea69...). Android userdata is now destroyed (expected/approved). Boot 0028u at 19:53:20 (`research/boot0028u-hfs.log`), photo IMG_20261015_215541: `BSD root: ufsroot0` -> **`hfs: mounted SweetRoot on device b(1, 0)` from internal UFS** -> panic `rootvp not authenticated after mounting @bsd_init.c:931` (arm64 macOS-config requires FSIOC_KERNEL_ROOTAUTH sealed root for non-ramdisk roots). Patch **0029** (`dd1c284`): SWEET logs `SWEET: root volume is not authenticated (error N); continuing unsealed` instead of panicking (Apple configs keep the panic; pivot_root still requires auth). CI **`38797924912`** running. Next: download out-0029, phone image with sweet-0028.adt + rd=ufsroot0 (no RAM disk), boot -> expect init from UFS.
- **UFS ROOT DRIVER VERIFIED ON HARDWARE (read-only).** 0028 CI `38796139570` PASSED, `xnu/out-0028` SHA256 `8b981640...9da6`; QEMU HFS RAM-disk regression `research/q0028-hfs` still runs init. Phone boot 2026-10-15 19:50:24 UTC (`research/boot0028u.log`, image `shim/out/shim-boot-0028u.img`, phone ADT `shim/out/sweet-0028.adt` with /sweet-ufs, NO RAM disk, `rd=ufsroot0`), photos IMG_20261015_215151/215220: `SWEET UFS: "userdata" on LUN 0: first block 0x2b8c00, 109643 MiB, read-only` -> `BSD root: ufsroot0, major 1, minor 0` -> `hfs_ValidateHFSPlusVolumeHeader: unknown Volume Signature : f188` (Android-encrypted data, as expected) -> `cannot mount root, errno = 19`, kernel retries mountroot (no panic). Nothing written to flash. NEXT (destructive, needs user confirmation right before): `fastboot flash userdata research/root-hfs.img` (8 MB HFS with test init) then boot rd=ufsroot0 -> expect init from internal flash.
- **PATCH 0028 (`33aceac`): XNU read-only UFS root device**, CI **`38796139570`** running (next artifacts xnu/out-0028, research/bt29, run29.log). `bsd/dev/sweet_ufs.c`: reuses ABL's UFSHCI state (like the shim probe), takes over UTRL at a kmem_alloc_contig region (DMA layout: UTRL 0x0, UCD 0x1000, 1 MiB bounce 0x4000), verifies UTRLBA readback before any doorbell, IE=0 polled, one SCSI cmd at a time on LUN0 (TUR x3, READ(10) via bounce, PRDT 256 KiB chunks), flush_dcache64 by PA around each command (host not dma-coherent per DT), finds GPT partition by name (`ufsroot=` boot-arg, default `userdata`), exposes `/dev/ufsroot0`/`rufsroot0` (512-byte logical sectors, physical 4 KiB, DKIOC* ioctls), refuses writes (EROFS). IOKitBSDInit: `rd=ufsroot0` -> sweet_ufs_rootdev() (lazy init) else panic. ADT: `tools/mkadt.py` adds `/sweet-ufs` reg <0x1d84000 0x3000> for the PHONE only (not --qemu). Local compile OK, imports resolve. Sandbox research/bt28 (pre0028 originals). FIRST PHONE TEST PLAN (non-destructive): boot 0028 with phone ADT + `rd=ufsroot0` and NO RAM disk: expect `SWEET UFS: "userdata" on LUN 0: first block 0x2b8c00, 109643 MiB` + `BSD root: ufsroot0`, then root mount failure (userdata is still Android-encrypted) -> panic. That validates the driver before flashing an HFS image into userdata (needs explicit user confirmation at that time).
- **SUPERSEDES the 64 GiB iosroot GPT plan: user said "u can delete android" (2026-10-15).** Use the existing `userdata` partition (LUN0 sda34, 4K LBA 0x2B8C00, 0x1AC4B MiB ~107 GiB) directly as the iOS root: NO GPT changes. Keep bootloaders, recovery (OrangeFox), modem/persist/fsg/modemst untouched. Write the HFS image later with `fastboot flash userdata` (sparse, auto-split under the 768 MiB limit). Android will no longer boot normally (expected; reinstallable). Order: XNU UFS driver first, read-only against the current GPT; flash only once it can locate userdata. Nothing erased yet.
- **DECIDED (user, 2026-10-15): 64 GiB `iosroot` on LUN0 (sda), taken from userdata (wipes Android user data; Android/super kept).** Planned GPT (4K LBAs): userdata 0x2B8C00..0xD7D6FF (~43 GiB, keep type/unique GUIDs and attributes); iosroot 0xD7D700..0x1D7D6FF (0x1000000 blocks = 64 GiB, 1 MiB aligned); backup GPT area unchanged. Procedure: user backs up phone data -> boot OrangeFox recovery (adb) -> back up GPT (sgdisk --backup + raw dd of LBA 0-5 and last 6 blocks) to research/ -> sgdisk edit -> Format Data -> verify Android boots to setup. NOT EXECUTED YET.
- **INTERNAL UFS WORKS FROM THE SHIM (read-only), user authorized internal-UFS approach incl. flashing (2026-10-15, "i allow everything").** Shim probe `shim/ufs.c` (commit `12ed3ed` + filter): ufshc@1d84000 is UFSHCI 2.1 (ver 0x210, cap 0x1587031F, 32 slots), ABL leaves HCE=1, HCS=0x10F (device present, lists ready, UIC ready); probe takes over UTRL at its own buffer (verifies UTRLBA readback before any doorbell), TEST UNIT READY/READ CAPACITY/READ(10) all succeed. LUN0 = 0x1D7D800 x 4 KiB (~126.6 GB), valid GPT (64 entries at LBA 2). Photos IMG_20261015_212916/213325/213429. Big LUN0 partitions (start in 4K LBAs / MiB): super 0xCA00/0x2200 (8.5 GiB), logdump 0x22CA00/64, minidump 0x230A00/128, rawdump 0x238A00/128, recovery 0x240C00/128, cache 0x248C00/384 ext4, exaid 0x260C00/384, cust 0x278C00/1024 ext4, **userdata 0x2B8C00/0x1AC4B MiB (~107 GiB), fs unreadable = encrypted (metadata encryption)**. cache..cust contiguous = only 1.75 GiB (too small for iOS ~10+ GiB). Plan needing user consent: shrink userdata in GPT (wipes Android data) and add an `iosroot` partition at the end of LUN0. LUNs 1-5 not listed yet (sdb..sdf backed up in backup/lun).
- **fastboot limit measured (2026-10-15, read-only getvar):** `max-download-size: 805306368` (768 MiB); `max-fetch-size` unsupported; `is-userspace: no` (ABL fastboot). A `fastboot boot` image (shim+kernel+RAM disk) must be < 768 MiB, so the 2.5 GiB iOS shared cache cannot ride in the boot RAM disk even if XNU gets all RAM. Real userland needs storage access (UFS driver, or USB host) or a much smaller cache. Unlocking full RAM is still needed later (GUI).
- **iOS 16 USERLAND SOURCE (Claude, 2026-10-15).** Chose **iPhone X (iPhone10,3/10,6, D22/D221AP)** iOS **16.7.16 (20H392)** over iPhone 8: same A11 (no PAC -> plain arm64, runs on Kryo 470/ARMv8.2), last iOS for A11; X userland is home-button-less and tall-screen (1125x2436 vs sweet 1080x2400), better fit for later GUI. Note the X has its OWN SystemOS cryptex (different digest from iPhone 8's). IPSW URL in `research/ipsw-x/URL.txt` (+ BuildManifest). Images on the user's external SSD (NOT in git, do not format that disk: it holds the user's photos): `/run/media/dipa/android/ios-sweet-ipsw/iPhone10,3_16.7.16_20H392/` — `087-86593-047.dmg` = Cryptex1,SystemOS (2,743,074,816 B), `087-86698-044.dmg` = OS rootfs (4,730,814,044 B), both zip CRC-32 verified, plus Firmware/*.root_hash/.trustcache/.mtree. AppOS cryptex is 087-86715-047.dmg (10 MB, same as iPhone 8).
  - Images are raw APFS; files use LZBITMAP (decmpfs type 14). 7z cannot decode. Tools: `ipsw` 3.1.738 (AUR ipsw-bin, user-approved) needs apfs-fuse on Linux; **apfs-fuse** built in user space (system cmake broken: cmake 4.4.4 wants libjsoncpp.so.27, jsoncpp 1.9.6 installed = partial upgrade, NOT fixed) with pip cmake + `-DCMAKE_POLICY_VERSION_MINIMUM=3.5 -DCMAKE_CXX_FLAGS="-include cstdint"`, installed to `~/.local/bin/apfs-fuse` (+apfs-dump-quick). Mount via a comma-free symlink (apfs-fuse splits options on ',' in `iPhone10,3`; exFAT has no symlinks -> put link elsewhere): `apfs-fuse LINK/087-86698-044.dmg MNT` -> `MNT/root/...`; unmount `fusermount3 -u MNT`.
  - Verified from headers: `dyld_shared_cache_arm64` magic `dyld_v1   arm64`; `/sbin/launchd`, `/usr/lib/dyld` = cputype 0x100000c subtype 0 (plain arm64). libSystem exists only inside the cache.
  - **BLOCKER for real userland via RAM disk:** shared cache = 3.10 GiB in 44 files (~2.5 GiB without the 592 MB `.symbols`), but the kernel manages only 1.20 GiB (0xb0000000..0xfd000000). Options: (A) give XNU the phone's full ~6 GB (banks 0x80000000+2G and 0x100000000+0xfcc00000, carve-out holes need pmap support) AND check fastboot max-download-size for a multi-GB boot image; (B) storage driver (Qualcomm UFS) to read a root from flash (no flashing allowed: would need a file/partition strategy); (C) run against individual dylibs extracted from the cache (uncertain).
- **MILESTONE ON HARDWARE: HFS+ ROOT FILESYSTEM -> PID 1.** Boot 2026-10-15 18:22:12 UTC (`research/boot0027b.log`, image `shim/out/shim-boot-0027b.img`), photo `IMG_20261015_202334.jpg`: `BSD root: md0` -> `hfs: mounted SweetRoot on device b(1, 0)` -> `load_init_program: attempting to load /sbin/launchd` -> `*** SWEET userspace: init running as PID 1 ***` -> repeated `SWEET init: still alive`, no panic. Kernel 0027 (built-in Apple OSS HFS + BearSSL MD5), init with SP alignment fix. NEXT: real iOS 16 userland on the HFS image (dyld, libSystem/dyld shared cache, launchd). Known gaps: entitlements (none granted), SHA-1/SHA-384/512 providers, no storage driver (RAM disk only), root mounted read-only.
- **PHONE HFS ROOT (0027) + SIGBUS ROOT-CAUSED.** Phone boot 2026-10-15 17:49:06 UTC (`research/boot0027.log`, photo `IMG_20261015_200031.jpg`): `hfs: mounted SweetRoot on device b(1, 0)` (HFS works on hardware), init printed its first line, then `pid 1 exited -- exit reason namespace 2 subcode 0xa` = SIGNAL/SIGBUS -> `initproc failed to start` panic. Diagnostic boot 18:08:13 UTC (`research/boot0027d.log`, image `shim/out/shim-boot-0027d.img`, diag init `research/diag-init` from scratch diag-init.S with [a][b][c] markers, `cs_debug=1`; photo `IMG_20261015_201547.jpg`): output `PID [a][b]` then SIGBUS -> fault at first `strb w21,[sp]`; no code-signing messages. Cause: kernel enters a static binary with sp at argc, not necessarily 16-aligned (depends on arg/apple string lengths, differs mockfs vs HFS); EL0 SP alignment check -> EXC_ARM_SP_ALIGN -> SIGBUS (sleh handle_sp_align). QEMU does not enforce SP alignment. NOT a kernel bug: real binaries start in dyld which aligns. Fix `1a8fc15`: sweet-init aligns sp at entry. Rebuilt `research/root-hfs.img`, QEMU `research/q0027-hfs2` OK. Phone image `shim/out/shim-boot-0027b.img` SHA256 `098ba46c...c5c` (payload-0027b, ramdisk match check-0027b) ready, awaiting FASTBOOT. Lesson: Assembly `;` is a comment in Apple arm64 asm (use .macro, not ;-joined #define).
- **HFS ROOT WORKS (QEMU).** 0027 CI `38779441895` PASSED, `xnu/out-0027` SHA256 `a8643886...5f6a`. QEMU `research/q0027-hfs` (RAM disk = `research/root-hfs.img`, rd=md0): `BSD root: md0` -> `hfs: mounted SweetRoot on device b(1, 0)` -> `load_init_program: attempting to load /sbin/launchd` -> `*** SWEET userspace: init running as PID 1 ***` + heartbeat, no panic. Phone image `shim/out/shim-boot-0027.img` (payload-0027 = 0027 kernel + sweet-0021.adt + root-hfs.img + rd=md0, ramdisk byte-match check-0027) ready; awaiting FASTBOOT for phone test.
- **HFS ROOT WORK (Claude), patches 0026-0027.**
  - 0026 (`f0e990c` + link fix `64c96f4`): Apple OSS **hfs-627.100.6** (commit `31d5ec238dfab485e78a9a30b8b92d13e8914f03`, paired with xnu-8796.141.3 in macos-135 release.json) staged by `xnu/patches/0026-stage-hfs.sh` into `bsd/sweet_hfs` (core + hfs_encodings; AppleKeyStore include/key prototypes guarded by CONFIG_PROTECT; SDK TargetConditionals copied). New config option `sweet_hfs` (MASTER + MASTER.arm64.sweet); 40 `optional sweet_hfs` files; Makefile.template foreach adds `_CFLAGS_ADD = -include sweet_hfs_compat.h -I...` (MUST come after kernel -D flags; compat undefs BSD/XNU_KERNEL_PRIVATE and the CONFIG_* HFS tests so kext-config.h decides: macOS profile, no content protection). `sweet_hfs_iokit.c` replaces hfs_iokit.cpp/hfs_encodings_kext.cpp: `sweet_hfs_register()` called in bsd_init after vfsinit (encodings init, vfs_fsadd VFS_TBLCANMOUNTROOT, zones, sysctls); is_ejectable 0, iterate_media none, serial KERN_NOT_SUPPORTED, OSKextGetCurrentLoadTag -> kOSKextInvalidLoadTag (renamed via compat macro). hfs_encodings' own `hfs_allocated` renamed per object (separate kexts on Apple; first CI `38777325964` failed on that duplicate at link). mockfs now validates Mach-O magic (its TODO) so non-Mach-O roots fall through to HFS (new fs entries come AFTER mockfs in vfsconf). CI `38778133720` PASSED, `xnu/out-0026` SHA256 `0b49170c...701a`, prints `SWEET HFS: hfs-627.100.6 registered`.
  - HFS+ image: `research/root-hfs.img` (8 MB, mkfs.hfsplus from AUR hfsprogs installed with user approval; loop-mounted with sudo; /sbin/launchd = research/sweet-init, /dev; fsck.hfsplus OK). QEMU `research/q0026-hfs`: `BSD root: md0` then data abort in MD5Init from hfs_getvoluuid (mount computes volume UUID).
  - 0027 (`14bf2b7`): 0020 stager also copies BearSSL hash/md5.c + codec/dec32le.c/enc32le.c; `corecrypto_md5.c` SWEET branch converts MD5_CTX <-> br_md5_context around br_md5_* calls; wrappers sweet_md5.c/sweet_dec32le.c/sweet_enc32le.c. Host test 40/40 match md5sum. CI **`38779441895`** running.
  - Local tooling: `tools/xnu-cc.py` has `XNU_CC_POST` (flags after logged ones). Sandbox `research/bt28/xnu` = 0025 CI tree + 0026/0027 edits; originals `research/pre0026`, `research/pre0027`. HFS local objects `research/hfs-objs`. Checker entries updated to bt28.
  - SHA-1 / SHA-384/512 still have no provider.
- **MILESTONE ON HARDWARE: USERSPACE PID 1 RUNS ON THE PHONE.** Boot 2026-10-15 17:16:00 UTC (`research/boot0025.log`: send OKAY0.410s, boot OKAY0.135s), image `shim/out/shim-boot-0025.img` SHA256 `9dbfa0b1...89db0`. Photo `IMG_20261015_191733.jpg`: `BSD root: md0` -> `load_init_program: attempting to load /sbin/launchd` -> `*** SWEET userspace: init running as PID 1 ***` -> repeated `SWEET init: still alive` (5 s heartbeat), no panic. Kernel 0025 + mockfs RAM disk + built-in no-entitlements AMFI. No flashing performed.
- **NEXT (toward real iOS userland):** real root filesystem with real binaries. Options: (a) build Apple OSS `hfs` (macOS 13.5 tag `hfs-627.100.6`) into SWEET like libpthread, then an HFS RAM disk image; (b) iOS 16 dyld + libSystem/dyld shared cache from the IPSW (needs APFS or repacking onto HFS). Expected hurdles: entitlements (sweet_amfi grants none), SHA-1/MD5/SHA-384/512 providers (BearSSL), missing kexts/daemons. Current init is a static test program, not launchd.
- **MILESTONE: USERSPACE RUNS (QEMU).** 0025 CI `38774788048` PASSED, `xnu/out-0025` SHA256 `5496069b...4877`. QEMU `research/q0025-rd` (150 s, no panic): `BSD root: md0` -> `load_init_program: attempting to load /sbin/launchd` -> `*** SWEET userspace: init running as PID 1 ***` -> `SWEET init: still alive` every 5 s. Exec, ad-hoc SHA-256 code signature, syscalls, devfs /dev/console, select timeouts all work. Phone image prepared: `shim/out/shim-boot-0025.img` 16,515,072 bytes SHA256 `9dbfa0b15140c0bd733a16c4f727f6a7df44a8741f98d8e266d5f2fa4f689db0` (payload-0025 = 0025 kernel + sweet-0021.adt + research/sweet-init + rd=md0; ramdisk byte-match check-0025). Waiting for user to put phone in FASTBOOT.
- **0024 CI `38773277811` PASSED**, `xnu/out-0024` SHA256 `a0ba964b...4348`. QEMU `research/q0024-rd` and **PHONE (boot 2026-10-15 17:05:55 UTC, `research/boot0024.log`, image `shim/out/shim-boot-0024.img` SHA256 `cf3dac86...6964`, 16,510,976 bytes, payload `shim/out/payload-0024.bin` = 0024 kernel + `shim/out/sweet-0021.adt` + RAM disk `research/sweet-init` + rd=md0; ramdisk byte-match `check-0024`)** agree: `Added memory device md0`, `BSD root: md0`, `load_init_program: attempting to load /sbin/launchd`, then data abort in accelerate_entitlement_queries (PC 0x...77d2458, FAR 0x1a0) = NULL AMFI interface. Photo `IMG_20261015_190715.jpg`. RAM disk root is physically verified.
- **0025 (`2518c79`)**: new `bsd/kern/sweet_amfi.c` registers a built-in AMFI interface at EARLY_BOOT/MIDDLE: no entitlements (adjustContextWithoutMonitor succeeds without creating a context, queries KERN_DENIED, copies NULL/KERN_NOT_FOUND, get_xml/transmuted false); WithMonitor KERN_NOT_SUPPORTED; OSEntitlements_query and query_context_to_object panic explicitly (CoreEntitlements closed; no kernel caller); TrustCache version 0 (0015 keys on trust_cache_rt==NULL, img4 absent -> still unavailable); CoreEntitlements table zero (PMAP_CS only). Compiles locally; checker updated (bt27 entries). CI **`38774788048`** running. Next artifacts `xnu/out-0025`, `research/bt29`, `research/run29.log`. Real iOS binaries will need real entitlements later (no OSS CoreEntitlements exists).
- **0021-0024 RAM-disk-root iteration (Claude), QEMU only so far, no new phone boot since 0020.** Each kernel tested with `tools/mkpayload.py KERNEL research/q0021.adt OUT --ramdisk research/sweet-init --cmdline "debug=0xc serial=3 cpus=1 keepsyms=1 -enable_kprintf_spam -noprogress rd=md0"` then `tools/qemu-sweet.py OUT DIR --secs 150 --kernel KERNEL --fail-on-panic` (PATH needs ~/swift/usr/bin for llvm-nm). Fresh ADTs: `research/q0021.adt` (QEMU), `shim/out/sweet-0021.adt` (phone).
  - 0021 CI `38769532000` PASSED, `xnu/out-0021` SHA256 `2b7500a1...962e`, `research/bt25`/`run25.log`. QEMU `research/q0021-rd`: md0 root, then assert `iomediaClass` in IOService::publishHiddenMedia.
  - 0022 (`20ece9c`, publishHiddenMedia without IOMedia class) CI `38770666158` PASSED, `xnu/out-0022` SHA256 `a4d0e787...30c5`, `research/bt26`/`run26.log`. QEMU `research/q0022-rd`: data abort in SHA256_Init (NULL g_crypto_funcs) from vm_kernel_addrhash_internal.
  - 0023 (`c8089d1`, libkern SHA256_Init/Update/Final use built-in ccsha256_ltc_di + ccdigest_init/update on SWEET; also serves code-signing SHA-256; SHA-1/MD5/SHA-384/512 still have NO provider - BearSSL from 0020 could supply them later) CI `38771876423` PASSED, `xnu/out-0023` SHA256 `d763fed7...1003`, `research/bt27`/`run27.log`. QEMU `research/q0023-rd`: **mockfs mounted md0, `load_init_program: attempting to load /sbin/launchd`**, then panic `mockfs_fsnode_vnode failed to create fictitious pages ... rvalue = 5` (mockfs.c:351).
  - 0024 (`3293c80`): mockfs used memdev mi_base (4K page number of a VIRTUAL kernel address for IOKit RAMDisk, truncated to 32 bits) << PAGE_SHIFT as a physical address. Now zero-copy pager mapping only when mi_phys (with 4K units); virtual md uses pagein/blockmap/strategy -> memdev bcopy. memdev's own mdPhys path assumes 4K ppnums (unsafe on 16K arm64), so do NOT switch the RAMDisk to physical. CI **`38773277811`** running. Next artifacts `xnu/out-0024`, `research/bt28`, `research/run28.log`.
  - Sandboxes: bt25/bt26/bt27 contain the next patch's edited files; pristine copies in `research/pre0022`..`pre0024`.
- **PATCH 0021 (Claude): RAM disk root via mockfs -> first userspace program.** Commits `9c37771` (initial; CI `38768500280` FAILED: mockfs_fsnode.c kfree_type(mockfs_fsnode_t) typed-alloc static assert; local xnu-cc stubs `__builtin_xnu_types_compatible` so it can't catch this) and `193772f` (fix), CI **`38769532000`** running: https://github.com/dipa-studio/ios-sweet/actions/runs/38769532000. Next artifacts: `xnu/out-0021`, `research/bt25`, `research/run25.log`.
  - Kernel: `config/MASTER.arm64.sweet` FILESYS_BASE += `mockfs` (XNU's built-in FS: root device is itself a Mach-O, served as /sbin/launchd, plus /dev for devfs). Upstream mockfs bit-rot fixed: kalloc_type/kfree_type used the POINTER typedef mockfs_fsnode_t (nodes were 8 bytes) -> `struct mockfs_fsnode`. `IOService::setRootMedia` asserted IOBlockStorageDriver class exists (IOStorageFamily absent): SWEET-only, a missing class means root=NULL (same as IOSetImageBoot); Apple path keeps assert. All 21 patches apply (`research/check-patch-order.py`); 5 TUs compile locally with -DMOCKFS (`research/mockfs-objs`), imports resolve vs 0020 kernel. Sandbox `research/bt24/xnu` now holds 0021 versions of those 3 files; pristine 0020 copies in `research/pre0021`.
  - Tools: `tools/mkpayload.py --ramdisk IMAGE` appends IMAGE as an extra payload segment right after the kernel, moves kernel_end past it (shim unchanged: ADT+boot_args follow it, image stays below topOfKernelData), and adds ADT `/chosen/memory-map` `RAMDisk`=<phys,size>. Boot with `rd=md0`. Without --ramdisk output is byte-identical to existing 0020 QEMU and phone payloads (verified). `tools/sweet-init.S` + `tools/mkinit.py`: PIC static init (open /dev/console, print PID, heartbeat every 5 s via select, never exits) wrapped into a static arm64 Mach-O (__PAGEZERO, __TEXT@0x100000000, LC_UNIXTHREAD, ad-hoc SHA-256 CodeDirectory v0x20400, 4K pages). Build: `~/swift/usr/bin/clang -target arm64-apple-ios16.0 -c tools/sweet-init.S -o X.o && tools/mkinit.py X.o research/sweet-init` (ld64.lld cannot link static iOS). Signature not verified by a real codesign; the kernel will tell.
  - QEMU with 0020 kernel + RAM disk (`research/q0020-rd.bin`, rd=md0, 150 s `research/q0020-rd150`): `Added memory device md0`, **`BSD root: md0, major 1, minor 0`** (plumbing works), then the setRootMedia assert (now fixed in 0021). NOTE: QEMU needs >60 s to reach IOFindBSDRoot (60 s run showed nothing after stf0; likely RTC/inittodr wait), so use --secs 150.
  - NEXT: download 0021, QEMU 150 s with ramdisk; expect mockfs mount then init exec -> `*** SWEET userspace: init running as PID 1 ***`. Then phone boot with same payload (phone ADT shim/out/sweet-0020.adt pattern + --ramdisk + rd=md0).
- **0020 PHONE RESULT (user transcription of screen, 2026-10-15): KERNEL INIT COMPLETE, WAITING FOR ROOT.** After Skywalk self-tests PASSED, kminit, ifnet_attach lo0/gif0/stf0, screen prints `BSD`, then `Waiting on <dict><key>IOProviderClass</key><string>IOMedia</string><key>Content</key><string>Apple_HFS</string></dict>` and `Failed to write boot-picker-bringup-reason to NVRAM.` No panic. This is IOFindBSDRoot waiting for a root device (none exists); NVRAM warning is expected (no NVRAM driver). QEMU `cpu_idle` snapshot is presumably the same wait (not GDB-confirmed; milestone GDB run was cancelled by user since phone answered it). Draft `research/check-milestones20.gdb` (hbreaks inittodr/vfs_mountroot/IOFindBSDRoot/bsd_utaskbootstrap) left uncommitted/ignored.
- **NEXT MILESTONE: root filesystem -> launchd.** Plan: (1) RAM disk: shim places an image in RAM, ADT /chosen/memory-map `RAMDisk` entry, boot-arg `rd=md0` (XNU md driver). (2) HFS is a separate kext on Apple; build Apple OSS `hfs` (tag paired with macOS 13.5 in distribution-macOS macos-135 release.json) into SWEET like libpthread 0019. APFS is closed. (3) Minimal HFS image with iOS 16 launchd (later: dyld/shared cache; AMFI/code-signing absent will be a later hurdle). User's end goal is full iOS GUI.
- **0020 (AES) VERIFIED + PHONE BOOTED (Claude took over after Codex usage limit).** Actions `38765422261` (`ab9e23f`) PASSED; kernel `xnu/out-0020/kernel.development.sweet` checksum OK; buildtree `research/bt24`, log `research/run24.log`. Actual-kernel AES checks PASS (`research/check-aes20.gdb` / `.log`, 12 extra CBC cases match OpenSSL). 45s QEMU `research/q0020`: no panic, zero unknown glyphs, past old TCP/AES panic -> Skywalk self-tests PASSED -> bsd_autoconf kminit -> ifnet_attach lo0/gif0/stf0; final snapshot PC in `cpu_idle` (idle or waiting; NOT yet diagnosed, could be root-device wait). Image `shim/out/shim-boot-0020.img` 16,461,824 bytes SHA256 `775200cb02d95fc750981516b79d91dcdc96184bbe67a38f9d57c59b4a391828`, ramdisk byte-matches `payload-0020.bin` (`check-0020`). **Phone temporarily booted 2026-10-15 16:10:00 UTC**: one FASTBOOT product sweet, send OKAY0.407s, boot OKAY0.134s, total0.549s, exit0 (`research/boot0020.log`). Awaiting user photo; do not reboot the phone before it. NEXT: read photo; diagnose what QEMU waits on after stf0 (GDB backtrace of threads / longer run). Codex's STOP request below is complete.
- User requests STOP after completing the current0020 AES iteration (Actions/QEMU/phone), then leave a precise committed handoff for another AI. User says FASTBOOT ready again after0019 photo. Do not start a new blocker fix after this iteration.
- Goal: iOS16-generation XNU on Redmi Note10Pro sweet/SM7150. Always commit, use gh/Actions for kernel builds, keep this handoff current. Temporary fastboot boot only; preserve Android/backups. No userland/root filesystem boot yet.
- **Patch0020 update:** initial `e71098d` / Actions `38765012466` superseded by scalar-only compile flags. Added -mgeneral-regs-only to all six provider/BearSSL TUs and corecrypto_aes.c; object disassembly now confirms no SIMD. Updated implementation `ab9e23f`, Actions `38765422261` queued/running: https://github.com/dipa-studio/ios-sweet/actions/runs/38765422261. Do not launch another run. portable BearSSL AES CBC and legacy one-block ECB wired directly into SWEET corecrypto_aes.c. Genuine bitslice implementation, no CPU AES/SIMD requirement, heap or fake global crypto table. Source fetched by `0020-stage-bearssl.sh` from official BearSSL git at immutable `7bea48e5e850ab4cafbe68d3765cdaba13a86d6f`; MIT license retained, downloaded source stays out of git. Kernel limits include adapter only. All128/192/256-bit keys, CBC encrypt/decrypt, copied contexts, in-place/out-of-place; zero block count and size overflow handled, invalid keys clear context. Seven TUs compile to arm64 objects (`research/aes-objs`), imports resolve, all20 patches apply and sources match (`research/patch0020-check.log`). Sandbox `research/bt23/xnu`, originals `research/pre0020`. NEXT: Actions then actual-kernel NIST/random CBC/ECB checks and >=45s QEMU before another phone boot. Next artifacts out-0020 / bt24 / run24.log. 0020 updated CI pending. Local sources/checks match the scalar-only patch.
- **Latest built kernel0019**, implementation `256d3f0`, patches0001-0019. Actions `38763072907` PASSED (4m5s): https://github.com/dipa-studio/ios-sweet/actions/runs/38763072907. Kernel `xnu/out-0019/kernel.development.sweet`, SHA256 `a27df7568f03fb541cf0e8024c0a594fa178a85054fcf9eba29158cbd4c5ecc0`; checksum verified. Log/source `research/run23.log` / `research/bt23` (no nested .git). Seven pthread source/build/header files and staged adaptations byte-match local compile inputs.
- **0019 hardware photo received** `IMG_20261015_175306.jpg`: pthread registration visible, passes mbinit and DLIL checksum/scheduling, same AES fault as QEMU: PC`0xfffffe00079174e0` (`aes_encrypt_key128`), LR`0xfffffe000767c3a4` (`tcp_init`), FAR0x78, x8=0. Disassembly proves NULL g_crypto_funcs->ccaes_cbc_encrypt. Photo processed; no more0019 observation pending. General crypto table remains absent, other hash/mode operations may still fault after0020. DO NOT bypass TCP or install fake crypto. XNU already contains SHA256/HMAC implementations; AES source there is a dispatch wrapper. Full future provider interface libkern/libkern/crypto/register_crypto.h. Apple/corecrypto default README describes evaluation-only licensing, so no external corecrypto was fetched or staged; BearSSL selected for this portable AES integration.
- **0019 pthread FIXED in QEMU and observed beyond its init on phone**: 45s QEMU `research/q0019`, zero unknown glyphs, then AES panic. Actual-kernel API checks PASS `research/check-pthread19.gdb` / `.log`, guest `research/q0019-api`: function/callback table identity, actual provider pthread_init returns, locks/global hash/threadcall/typed zones initialized, thread_selfid via syscall shim + buffer bounds, process hash init/delete via shims restores NULL. Monitor quit prints expected remote-disconnect after PASS. All fixture guests stopped.
- **0019 provider**: genuine Apple libpthread-514.100.2 commit `a6c70ca0e544347a0377babf748f831577ec24f9`, exact paired release with xnu8796.141.3 in distribution-macOS/macos-135/release.json (`research/macos-135-release.json`). 0019 shell stage runs before patches (workflow copies *.sh); three SWEET wrapper TUs use kext BSD header view, vm_fault_external, renamed provider-side pthread_kern/current_uthread; register real function table at EARLY_BOOT SECOND, real pthread_init later. Stager applies bounded address casts, zero user addresses, proper panic format. SWEET opaque ksyn storage enlarged48->56 for trailing kwe_uth, checked with provider static assertion. Local pre-CI TargetConditionals fixture was syntax-only; artifact bt23 carries actual SDK header and CI is authoritative.
- **Phone0019 temporarily booted** 2026-10-15 15:51:36 UTC: exactly one FASTBOOT/product sweet verified; send OKAY0.406s, boot OKAY0.134s, total0.546s, exit0 (`research/boot0019.log`). Image `shim/out/shim-boot-0019.img`, 16,457,728 bytes, SHA256 `19429a57e486b856880df9e27327ed488e0139345311fdb0350974e72103a9a1`. Phone ADT/payload `shim/out/sweet-0019.adt` / `payload-0019.bin` timer19, unpacked ramdisk byte-match (`check-0019`). EntryPA0xb146b488, kernelendPA0xb2000000, boot_argsPA0xb2004000/top0xb2008000. Last user FASTBOOT+USB reply preceded this boot; do not assume phone is still in FASTBOOT.
- **CPU0018 physically verified** by `IMG_20261015_173951 (2).jpg`: boot CPU0 registered, real SGI1 verified, initialization complete -> BSD/MAC/mbinit -> old pthread-table panic. SweetCPU uses legacy IOCPU, ml_processor_register/processor_start/initCPU, real SGI1 clears SIGPdisabled before max CPUs completion; no forced flags/skipped waits. CPU APIs and two-CPU rejection passed (`research/check-cpu18.gdb`, `q0018-api`, `q0018-smp`). Single core; SMP/suspend unsupported. CURRENT SWEET has NO USE_APPLEARMSMP.
- QEMU next run: generate fresh `tools/mkadt.py research/q0020.adt --qemu` (timer27), mkpayload with `debug=0xc serial=3 cpus=1 keepsyms=1 -enable_kprintf_spam -noprogress`, then `tools/qemu-sweet.py PAYLOAD OUT --secs 45 --kernel KERNEL --fail-on-panic`. 12s can miss later panics because IORTC waits30s. Runner snapshot only: panic exit2, blank/incomplete exit3; absence of panic does not mean complete boot. Qualcomm XPU/ABL/panel and phone SMC PSCI require hardware checks.
- Local checker `tools/xnu-cc.py research/run23.log research/bt23 FILTER --per-file`, XNU_CC_OBJDIR for objects. For new BearSSL TUs add XNU_CC_EXTRA with -I bt23/xnu/libkern/crypto/sweet_bearssl/{inc,src}. Patch checker `research/check-patch-order.py` uses temporary upstream index; source fixtures/artifacts ignored under research. GDB mask registers to unsigned64, use function-entry manual-call return traps, discard manipulated guests. No QEMU guest intentionally left running.

## Session log and earlier handoffs (superseded by the active summary above)

### Prior 0019 transition notes (superseded)

- Goal: iOS 16 generation XNU on sweet. Always commit completed work, use gh/Actions for kernel builds, keep this handoff current. Temporary fastboot boot only; preserve Android/backups.
- **0019 build PASSED** Actions `38763072907` (4m5s), implementation `256d3f0`. Kernel `xnu/out-0019/kernel.development.sweet`, SHA256 `a27df7568f03fb541cf0e8024c0a594fa178a85054fcf9eba29158cbd4c5ecc0`; checksum verified. Log/source `research/run23.log` / `research/bt23`; all seven patched files and staged provider adaptations match local compile inputs. Prefer bt23 as the next baseline.
- **0019 pthread FIXED in QEMU**: 45s run `research/q0019` registers provider, passes mbinit, DLIL SUM16 checks and DLIL thread scheduling. Actual-kernel GDB checks `research/check-pthread19.gdb` / `.log` PASS: function/callback table identity, real _pthread_init returns, locks/global hash/cleanup threadcall/typed zones non-NULL, thread_selfid via actual syscall shim with output bounds, process hash init/delete through actual shims restores NULL. Guest stopped after tests; no fixture left running. GDB monitor quit prints expected remote disconnect after PASS.
- **Current next blocker:** QEMU0019 panic data abort FAR0x78 at `aes_encrypt_key128` PC`0xfffffe00079174e0`, called by `tcp_init` LR`0xfffffe000767c3a4`. Disassembly confirms `g_crypto_funcs == NULL`, loading ccaes_cbc_encrypt at+0x78. General crypto registration is still absent; DO NOT bypass TCP or supply fake crypto. Next integrate a genuine compatible crypto implementation/provider (AES first needed here, other digest/mode APIs also used). XNU contains SHA256/HMAC but no AES implementation; its corecrypto_aes.c is a dispatch wrapper. Full crypto table is in libkern/libkern/crypto/register_crypto.h.
- **0019 phone image prepared and verified**, user reports FASTBOOT+USB again; exactly one device/product sweet verified. `shim/out/shim-boot-0019.img`, 16,457,728 bytes, SHA256 `19429a57e486b856880df9e27327ed488e0139345311fdb0350974e72103a9a1`; unpacked ramdisk matches phone payload (`shim/out/check-0019`, `payload-0019.bin`, `sweet-0019.adt`, timer19). EntryPA0xb146b488; kernelendPA0xb2000000; boot_argsPA0xb2004000/top0xb2008000. Usual debug cmdline cpus=1/-noprogress. **Temporarily booted 2026-10-15 15:51:36 UTC**: send OKAY0.406s, boot OKAY0.134s, total0.546s, exit0 (`research/boot0019.log`). User asked for photo after45s. Await the photo; DO NOT reboot again before observation. Bootloader acceptance only; no0019 physical progress observed yet.
- **Hardware photo confirms 0018 progress** (`IMG_20261015_173951 (2).jpg`): real phone prints `SWEET CPU: boot CPU 0 registered, SGI1 verified, initialization complete`, enters BSD/MAC, reaches `mbinit: done`, then the same missing-pthread-function-table panic as QEMU at pthread_shims.c:318. CPU completion/interrupt delivery is now physically observed. The photo was received; no further phone boot performed yet.
- **Patch0019 committed/pushed `256d3f0`; Actions `38763072907` queued/running:** https://github.com/dipa-studio/ios-sweet/actions/runs/38763072907. Do not launch a duplicate. genuine Apple OSS libpthread-514.100.2 provider (immutable commit `a6c70ca0e544347a0377babf748f831577ec24f9`), paired with xnu-8796.141.3 by Apple's `distribution-macOS/macos-135/release.json` (`research/macos-135-release.json`). `0019-stage-libpthread.sh` fetches/stages it before patches; workflow now copies shell scripts too. SWEET-only wrappers compile all three real kernel sources, rename provider-side symbols, use kext header view and vm_fault_external, register the real function table at EARLY_BOOT SECOND. Existing pthread_init then runs the actual provider initialization. No pthread wait/syscall is bypassed. Source staging includes bounded explicit address casts/zero user addresses and panic-format fixes. SWEET kernel opaque ksyn storage enlarged from48 to56 bytes to contain this provider's trailing kwe_uth, with a provider size assertion. Local compile of three provider TUs plus pthread_shims/kern_fork passed; imports resolve and provider exports do not collide with existing kernel symbols. All19 patches apply and changed sources match (`research/patch0019-check.log`). Source sandbox `research/bt22/xnu`, originals `research/pre0019`, objects `research/pthread-objs`. Local TargetConditionals fixture only has target macros for syntax; CI stages the real macOS SDK header and is authoritative. Next Actions artifacts: out-0019 / bt23 / run23.log; run QEMU >=45 seconds. 0019 CI is pending; no 0019 QEMU run yet.
- **Latest kernel implementation `e7d9550`, patches0001-0018; CI `38760004398` PASSED (3m56s)**: https://github.com/dipa-studio/ios-sweet/actions/runs/38760004398. No build is pending. Kernel `xnu/out-0018/kernel.development.sweet`, SHA256 `b3c8d59acc88f93a2c836eb2527a05ed4fbaac7c580a2ea8c3b795137f4aadf1`; checksum verified. Source/log `research/bt22` / `research/run22.log` (baseline for patch0019; no nested .git). New driver/config sources match CI exactly.
- **CPU wait FIXED in QEMU**: SweetCPU uses legacy IOCPU, validates single boot CPU, ml_processor_register -> processor_start -> initCPU real SGI1 -> scheduler/IOKit completion -> ml_set_max_cpus. It does NOT force a flag or skip a wait. CPU APIs passed: Running CPU0, processor_array[0] association, SGI signalling enabled, name, unsupported secondary-start error (`research/check-cpu18.gdb` / `.log`, `research/q0018-api`). Single-core only; SMP and suspend unsupported. Two-CPU topology fails explicitly (`research/q0018-smp`).
- **Next blocker reproduced in 45s QEMU** (`research/q0018-long`, zero unknown glyphs): BSD initialization reaches MAC framework, network mcache and `mbinit: done`, then **`pthread kernel extension not loaded (function table is NULL). @pthread_shims.c:318`**. Do not bypass pthread_init: find/integrate the matching open-source libpthread kernel implementation and register its real function table. A 12s run `research/q0018` looked panic-free before the 30s IORTC wait elapsed; use >=45s or GDB checkpoints for the next iteration. No userland/root filesystem boot yet.
- **Phone 0018 TEMPORARILY BOOTED** 2026-10-15 **15:31:15 UTC**: exactly one FASTBOOT device verified product sweet; send OKAY0.400s, boot OKAY0.134s, total0.539s, exit0. Local log `research/boot0018.log`. This confirms bootloader acceptance only. User was asked for a photo; await it, DO NOT reboot the phone again before their observation. No flashing performed.
- Current hardware image `shim/out/shim-boot-0018.img`, **16,437,248 bytes**, SHA256 **`b7a23595d143a76c72c9fe2cfcc5d77a8f16987b5af1a2703bbffdfa6922908c`**. Phone ADT/payload `shim/out/sweet-0018.adt` / `shim/out/payload-0018.bin` (timer19), unpacked ramdisk exactly matches payload (`shim/out/check-0018`). EntryPA0xb146b488; kernelendPA0xb1ffc000; boot_argsPA0xb2000000/top0xb2004000. Command line `debug=0xc serial=3 cpus=1 keepsyms=1 -enable_kprintf_spam -noprogress`.
- QEMU payload/ADT `research/q0018.bin` / `research/q0018.adt` (timer27). Run `python3 tools/qemu-sweet.py research/q0018.bin research/NEW-OUT --secs 45 --kernel xnu/out-0018/kernel.development.sweet --fail-on-panic`; fresh ADT seed for a new payload. Output fb.png/fb.txt/regs.txt/qemu.log/result.json. Visible panic exit2; blank/incomplete decode exit3; no_panic_observed is snapshot-only, not successful boot. -noprogress prevents the graphical indicator corrupting console text. Qualcomm XPU/bootloader/panel and SMC PSCI still need physical validation.
- Patches0014-0017 fixed PRNG registration/direct SHA256, explicit unavailable trust-cache service with rejected loads/no matches, built-in SweetPlatformExpert, and timer PPI from ADT (phone19/default19, QEMU27). All their checks/artifacts are preserved in the history below. CURRENT SWEET has NO USE_APPLEARMSMP; do not assume gCPUIC/gAIC/gPMGR AppleARMSMP globals exist.
- Local single-file checker: tools/xnu-cc.py research/run22.log research/bt22 FILTER --per-file, output via XNU_CC_OBJDIR. Patch checker `research/check-patch-order.py` applies all18 via temporary index, matches sandbox sources. Sandbox for0018 `research/bt21/xnu`, originals `research/pre0018`, objects `research/cpu-objs`. First compiler issues were missing machine/atomic.h and nonexistent getNameSymbol; fixed and both TUs compiled successfully before CI. Fixtures/artifacts under research are local-only/ignored.
- GDB: mask int(register)&((1<<64)-1) for unsigned kernel pointers; use function-entry manual-call return traps, discard manipulated guests. No QEMU fixture is intentionally left running.

### Earlier active handoff snapshot (superseded)


- **0018 milestone:** Actions `38760004398` PASSED (3m56s), checksums passed, new CPU/build files byte-match CI tree. Kernel `xnu/out-0018/kernel.development.sweet`, SHA256 `b3c8d59acc88f93a2c836eb2527a05ed4fbaac7c580a2ea8c3b795137f4aadf1`; log/tree `research/run22.log` / `research/bt22`. QEMU `research/q0018` 12s: boot CPU registered, SGI1 verified, CPU initialization complete, **BSD initialization entered** (copyright, MAC framework, buffer headers), no panic/zero unknown glyphs. Direct CPU API checks PASS (`research/check-cpu18.gdb`, `.log`, `research/q0018-api`): CPU0 Running, processor matches processor_array[0], real SGI enabled, CPU name correct, secondary-start returns KERN_NOT_SUPPORTED. Two-CPU ADT correctly panics before registration (`research/q0018-smp`). Longer 45s run `research/q0018-long` still running; next BSD wait/fault not yet identified.
- **Prepared 0018 phone image:** `shim/out/shim-boot-0018.img`, 16,437,248 bytes, SHA256 `b7a23595d143a76c72c9fe2cfcc5d77a8f16987b5af1a2703bbffdfa6922908c`. Phone ADT/payload `shim/out/sweet-0018.adt` / `shim/out/payload-0018.bin`, usual debug args with cpus=1 and -noprogress. Unpacked ramdisk byte-compared (`shim/out/check-0018`). Entry PA remains 0xb146b488; kernel end PA 0xb1ffc000, boot_args 0xb2000000/top0xb2004000. User reports FASTBOOT+USB ready; read-only check found exactly one product sweet. NEXT: temporary fastboot boot of this verified image, record send/boot results, then await hardware photo without rebooting again.
- Patch 0018 committed/pushed **`e7d9550`**; Actions **`38760004398`** queued/running: https://github.com/dipa-studio/ios-sweet/actions/runs/38760004398. Do not launch a duplicate run.
- Active continuation: patch **0018** implemented in `iokit/Kernel/arm/SweetCPU.cpp` + arm64 source list + exact qcom,kryo470 personality. Keeps legacy IOCPU, accepts ONLY the single boot CPU, fills ml_processor_info from parsed topology with CPU object as cpu_id, calls ml_processor_register and processor_start. initCPU sends SGI1 via ICC_SGI1R_EL1 and waits (1-second deadline) for real cpu_signal_handler to clear SIGPdisabled. Only after successful startup calls ml_cpu_init_completed/cpusRunning and publishes completion/max CPUs. Secondary startup/suspend are explicitly unsupported. Local C++ compile passed for both TUs (`research/cpu-objs`), all imports resolve, object contains dsb ishst / ICC_SGI1R / isb; all18 patches apply in order and match sources. Sandbox `research/bt21/xnu`, originals `research/pre0018`; next CI artifacts should use `xnu/out-0018`, `research/bt22`, `research/run22.log`. User has the phone available; first run QEMU, then prepare/temporarily boot useful hardware progress.
- Goal: iOS 16 generation XNU on Redmi Note 10 Pro / sweet. User wants persistent progress, commits, kernel builds via `gh` Actions, and this handoff kept current across agent switches. Temporary `fastboot boot` only; preserve Android and backups.
- Latest kernel implementation: **`aa3f991`**, patches **0001-0017**. All four new Actions builds PASSED: 0014 `38748543058` (4m0s), 0015 `38749549779` (4m3s), 0016 `38750733996` (4m3s), 0017 **`38751507437` (4m7s)**. Latest: https://github.com/dipa-studio/ios-sweet/actions/runs/38751507437. No build is pending.
- **Current blocker: CPU initialization has no SWEET CPU driver.** QEMU registers SweetPlatformExpert, then kernel_bootstrap_thread waits in **kperf_init_early -> ml_wait_max_cpus**. Confirmed via actual-kernel GDB call stack (`research/locate-cpu-wait2.log` / `.symbols`) and normal-run `max_cpus_initialized == 2` (MAX_CPUS_WAIT). Do not force the flag or remove the wait. Next implement real CPU registration and completion using XNU's CPU/processor interfaces. CURRENT SWEET uses legacy IOCPU (`USE_APPLEARMSMP` is absent); enabling AppleARMSMP is a separate architectural change requiring GIC/PMGR services. No userland/root filesystem boot yet.
- Fixed this session: PC=0 unregistered PRNG callback (0014, built-in HMAC-SHA256 provider + direct entropy/write_random hashing); absent Image4/AMFI trust-cache service (0015, unavailable runtime, loads rejected and queries no-match); missing platform driver (0016, SweetPlatformExpert exact personality); incorrect QEMU timer IRQ (0017, validated ADT PPI property, phone default19/QEMU27).
- **Latest kernel** `xnu/out-0017/kernel.development.sweet`, SHA256 `055a80190ab998b4df9203f1102072dcc78faad1779a537a514e522b682b582f`. Buildtree/log **`research/bt21` / `research/run21.log`**; all nine changed C/C++/header/config files byte-match local checked sources. Checksums passed. Entry PA `0xb146b488`, kernel end PA `0xb1ff4000`. Preferred baseline for patch 0018: `research/bt21/xnu` (no nested .git).
- **QEMU verified**: `research/q0017-noprogress` ran **30 seconds**, no visible panic, **zero unknown glyphs**, IRQ exceptions returned normally (4 IRQs, tickless idle). It still waits for CPU completion, so this is NOT a completed boot. Earlier 15s run `research/q0017` captured 122 IRQs, timer value27, GICR_ISENABLER0 `0x08000002`, and CPU WAIT; graphical progress overlay corrupted 13 glyphs. Add **`-noprogress`** to keep the console readable. New runner classifies incomplete/blank decoding explicitly (exit3 with --fail-on-panic), visible panic exits2. Snapshot-only; use regs/GDB to diagnose stalls.
- Current QEMU payload/ADT: **`research/q0017-noprogress.bin` / `research/q0017.adt`**. Run: `python3 tools/qemu-sweet.py research/q0017-noprogress.bin research/NEW-OUT --secs 30 --kernel xnu/out-0017/kernel.development.sweet --fail-on-panic`. Generate fresh seed with mkadt for a new payload. QEMU virt models generic ARM execution, not Qualcomm XPU/bootloader/panel or the phone's SMC PSCI conduit.
- **Prepared phone image**: **`shim/out/shim-boot-0017.img`**, 16,416,768 bytes, SHA256 `51ff7fe30b4a6668c3452ffe1da922c5ac30cb8de60625c2a652587ecbd0ec92`. Phone ADT/payload `shim/out/sweet-0017.adt` / `shim/out/payload-0017.bin` (timer19). Unpacked ramdisk exactly matches payload (`shim/out/check-0017`). Command line **`debug=0xc serial=3 cpus=1 keepsyms=1 -enable_kprintf_spam -noprogress`**. NOT sent to phone this session: known CPU-driver wait should be addressed in QEMU first. Last actual phone boot remains 0013; user's latest photo `IMG_20261015_160033.jpg` confirmed the old PRNG PC=0 panic.
- Direct QEMU/GDB API checks: PRNG 600-byte chunking, buffer bounds, changing output, zero-length reads/writes, user reseed, contended refresh, generator1 init/output PASS again on latest0017 (`research/check-prng17.gdb` / `.log`, guest `research/q0017-api`). Trust-cache unavailable-service/argument/output cases PASS on0015 (`research/check-trustcache.gdb` / `.log`). Platform registration + target/product normal/truncated/zero/null/bounds PASS on0016 (`research/check-platform.gdb`, `research/check-platform3.log`). Different platform ID correctly retains IOPanicPlatform fallback (`research/q0016-negative`). Timer PPI32 and size2 correctly panic (`research/q0017-badppi`, `research/q0017-badsize`); omitted property selects19 (`research/q0017-default`). These are API/bring-up checks, not crypto certification or SMP scheduling validation.
- Local checker **`research/check-patch-order.py`** verifies all17 patches and changed source equality using a temporary upstream git index. Fixtures/logs/artifacts under research are local-only and ignored. For GDB unsigned kernel pointers, mask `int(register_value) & ((1<<64)-1)`; x30/x29 may be rendered signed. Stop at a function entry for manual-call return traps, and discard each manipulated guest after API tests. All fixture QEMU guests have been stopped.


- User wants persistent progress toward iOS 16, commits for completed changes, builds through `gh` / GitHub Actions.
- Keep this file current at every milestone so another agent can resume immediately, including when usage limits interrupt a session.
- Patch 0017 committed/pushed `aa3f991`, Actions `38751507437` running: https://github.com/dipa-studio/ios-sweet/actions/runs/38751507437. Next artifacts: xnu/out-0017, research/bt21, research/run21.log. Do not duplicate.
- Patch 0016 kernel downloaded/checksum verified: SHA256 `d06336c54baa06e0df6561a8bd7df98a9b9f7502c9381c62d1a44c045cd1ce46`, `xnu/out-0016/kernel.development.sweet`; buildtree/log `research/bt20` / `research/run20.log`. QEMU `research/q0016` (10s) prints platform expert registered, zero unknown glyphs, no panic observed BUT stalls (timer mapping still wrong until 0017). Direct actual-kernel GDB tests passed for registered instance and target/product names, including maxLength=1/0 and NULL, sentinels intact (`research/check-platform.gdb`, `research/check-platform3.log`, `research/q0016-api3`). First two fixture attempts used premature/wrong return breakpoints; discarded, corrected fixture uses start-return observation then a function-entry return trap. No phone boot yet.
- Patch 0016 CI `38750733996` PASSED (4m3s); artifacts not yet downloaded/booted. Patch 0017 prepared to fix QEMU timer fidelity BEFORE interpreting future no-panic/stall runs: actual `qemu-system-aarch64 -M virt,gic-version=3,dumpdtb=research/qemu-virt.dtb ...` timer property has virtual PPI 11 => INTID 27, while phone uses INTID 19. Kernel formerly hardcoded 19. New optional /arm-io/gic virtual-timer-intid property selects the PPI (validate exact u32 and 16..31); missing property retains phone default 19. One RO-late global drives GIC enable and sleh_irq dispatch. tools/mkadt.py emits phone19/QEMU27. Both C TUs compile (`research/timer-objs`), ADT serialize/parse checks confirm values/addresses, all 17 patches apply and match. Sandbox `research/bt19/xnu`, originals `research/pre0017`; initial local sleh compile failed due read-only exported header not updated, fixed export and BOTH recompiled successfully. CI exports normally.
- Architecture correction for next agent: CURRENT SWEET board_config does NOT define USE_APPLEARMSMP; it compiles the legacy IOCPU path, not cpu_boot_thread/IOPMGR AppleARMSMP. Existing roadmap mentions AppleARMSMP as a future approach. Do not look for gCPUIC/gAIC/gPMGR globals in the current kernel: they are absent. Determine the actual CPU-init wait after platform registration before choosing the next driver architecture.
- Patch 0016 committed/pushed as `0dcdf5c`; Actions `38750733996` running: https://github.com/dipa-studio/ios-sweet/actions/runs/38750733996. Next artifacts: `xnu/out-0016`, `research/bt20`, `research/run20.log`.
- Patch 0016 implemented: new `iokit/Kernel/arm/SweetPlatformExpert.cpp`, arm64 source list, built-in personality in KernelConfigTables.cpp guarded by ARM64_BOARD_CONFIG_SWEET. Matches only xiaomi,sweet at score 10000, keeps IOPanicPlatform fallback for other hardware. Uses IODTPlatformExpert base initialization/power domain and createNubs CPU logical-ID annotation; overrides top-level publishing because base requires nonexistent Apple NVRAM /options. Publishes real CPU/top-level nodes, provides bounded target/product names, and registers the platform service. GIC/PMGR and arm-io child-bus drivers remain separate work. Both C++ TUs compile (`research/platform-objs`), all imports resolve against 0015/own objects, all 16 patches apply and sources match. Sandbox `research/bt19/xnu`; originals `research/pre0016`. NEXT: full Actions/QEMU; inspect CPU boot waits after the platform registers, do not equate absence of panic with successful boot.
- Patch 0015 CI `38749549779` PASSED (4m3s), checksum verified. Kernel `xnu/out-0015/kernel.development.sweet`, SHA256 `ca1b424a596c7058550ad1659080a333e7643270f019656401d80bf2b876645f`; buildtree/log `research/bt19` / `research/run19.log`. QEMU `research/q0015` (10s, zero unknown glyphs) passes trust-cache handling and machine lockdown, then panics `Unable to find driver for this platform: "xiaomi,sweet" @IOPlatformExpert.cpp:2319` (IOPanicPlatform fallback). Next concrete work: add a built-in SWEET IODTPlatformExpert personality/class; keep the fallback for mismatched platforms. No phone boot yet.
- Direct trust-cache API checks PASSED in the actual 0015 kernel under QEMU/GDB (`research/check-trustcache.gdb`, `research/check-trustcache.log`, `research/q0015-api`): runtime pointers NULL, hash/UUID queries return NOT_FOUND, typed/untyped/legacy loads return NOT_SUPPORTED, capabilities outputs zero and bounds preserved, invalid-argument cases still reject. Second PRNG check also verifies contended refresh returns immediately (`research/check-prng2.log`, `research/q0014-api2`).
- Patch 0015 committed/pushed `8f851d4`, Actions run `38749549779` running: https://github.com/dipa-studio/ios-sweet/actions/runs/38749549779. Do not duplicate.
- Direct PRNG API checks passed in the REAL 0014 kernel under QEMU/GDB, stopped before trust-cache init (`research/check-prng.gdb`, log `research/check-prng.log`, guest `research/q0014-api`). Invoked read_random for 600 bytes (chunking and buffer sentinel intact), repeated output differed, zero-length read/write succeeded, write_random(64-byte input) succeeded, secondary generator 1 initialized and generated distinct output. QEMU log has no exceptions during these checks; guest was discarded after the tests. This tests API behavior, not a cryptographic certification or SMP scheduling.
- Patch 0015 implemented in `bsd/kern/kern_trustcache.c`: SWEET with missing Image4/AMFI marks both runtime pointers NULL and logs service unavailability. Existing static loader handles NULL. Public load APIs return KERN_NOT_SUPPORTED; hash/UUID queries return KERN_NOT_FOUND; capabilities outputs are zero with KERN_NOT_SUPPORTED. Invalid-input checks remain, and Apple paths/available-provider initialization retain existing behavior. No trust is granted. Local arm64 compile passed (`research/trustcache-objs`), all 15 patches apply and sources match. Sandbox `research/bt18/xnu`, baseline `research/pre0015`. Next: Actions/QEMU and direct unavailable-service API checks using GDB.
- Patch 0014 CI `38748543058` PASSED (4m0s), artifact checksum passed. Kernel `xnu/out-0014/kernel.development.sweet`, SHA256 `741de20c851755d333759d7e668346f3edb4f325efac4cc7c142d80d1f5ff75c`; buildtree/log `research/bt18` / `research/run18.log`. QEMU run `research/q0014` (10s, zero unknown glyphs) prints `SWEET PRNG: HMAC-SHA256 registered`, passes commpage initialization, loads vnguard policy, THEN panics `image4 interface not available @kern_trustcache.c:253`. PC=0 fault FIXED IN QEMU. No new phone boot performed.
- Next work: SWEET currently has neither AppleImage4 nor AMFI. `trust_cache_runtime_init` unconditionally requires both; unlike BCM2837, SWEET enters this startup path. Investigate an explicitly unavailable trust-cache runtime with rejected loads/no query matches while providers are absent; preserve all Apple-platform checks. Merely skipping the startup call would leave later AMFI/IMG4 dereferences unsafe. Existing load_static_trust_cache already handles trust_cache_rt == NULL.
- QEMU runner now supports `--kernel MATCHING_KERNEL --fail-on-panic`: runtime font extraction from the payload produces exact `fb.txt`, plus `result.json`; a visible panic returns 2. Baseline 0013 re-run `research/q0013-text` detects the same NULL callback panic with zero unknown glyphs. Synthetic glyph roundtrip (including literal `?`) and invalid-VA rejection passed. Screen rows remain circular, not a full log; `no_panic_observed` does not prove successful boot. README has the invocation.
- Patch 0014 committed/pushed as `be61f99`; Actions run `38748543058` is running: https://github.com/dipa-studio/ios-sweet/actions/runs/38748543058. Do not start a duplicate build.
- 2026-10-15 active: hardware photo `IMG_20261015_160033.jpg` confirms the same PC=0 instruction-fetch abort as QEMU (LR `0xfffffe0007443fe4` = read_random). Independently reproduced with kernel 0013 in `research/q0013` (8-second run); prior allocator fix works. Latest tooling commit reviewed: `8d66d2d`.
- Patch 0014 implemented: registers a built-in HMAC-SHA256 DRBG provider at EARLY_BOOT/FIRST, before commpage creation. A shared mutex serializes output/reseed across CPUs (correctness first; no per-CPU scaling yet), initgen validates CPU identities, refresh uses try-lock and the existing entropy filter/health tests. SWEET entropy accumulation and write_random now use the built-in SHA256 directly; no incomplete g_crypto_funcs table is registered. The existing bootloader-seed requirement remains enforced.
- Local validation: both PRNG translation units compile to arm64 objects in `research/prng-objs`; no SHA256 wrapper imports remain. All 14 patches apply in CI order and resulting PRNG sources match local inputs. Sandbox `research/bt17/xnu`, originals `research/pre0014`, checker `research/check-patch-order.py`. NEXT: Actions kernel build, download to `xnu/out-0014`, run the QEMU payload before requesting another phone boot. Baseline QEMU ADT/payload are `research/q0013.adt` / `research/q0013.bin`.
- 2026-10-15 08:15 QEMU EMULATION WORKS (`tools/qemu-sweet.py`, see "QEMU emulation" below). Patch 0013 VERIFIED in QEMU: boot passes kmem_crypto_init and ulock_initialize. NEXT BLOCKER (reproduced in QEMU, expected on hardware too): `pmap_create_commpages -> random() -> RandomULong -> read_random -> prng_funcs.refresh == NULL` (instruction fetch abort at pc 0, lr read_random+0x34). Nobody calls `register_and_init_prng` (closed corecrypto kext does it on Apple). Fix = patch 0014: SWEET-registered cckprng_funcs provider (osfmk/prng/prng_random.c); note random_cpu_init also panics while !prng_ready. The 07:26 hardware boot of 0013 will most likely show this same panic.
- Previous hardware boot: patch 0013 (`a3a46e2`) CI `38686345689` PASSED (3m44s), image `shim/out/shim-boot-0013.img` was temporarily booted on 2026-10-15 at 05:26 UTC: send OKAY (0.407s), boot OKAY (0.134s), total 0.546s. Superseded by the hardware/QEMU PC=0 observation and patch 0014 work above.
- Latest kernel implementation commit: `8f851d4`. Latest successful kernel CI: `38749549779` (patch 0015), https://github.com/dipa-studio/ios-sweet/actions/runs/38749549779.
- CURRENT image: `shim/out/shim-boot-0013.img`, 16,412,672 bytes, SHA256 `110d1c46aee4b60253db24b6535e9781c4cf0fd25ca2a70e9016cf81378cea25`. Kernel `xnu/out-0013/kernel.development.sweet`, SHA256 `f0b1d375995316c550ce7014ff234d8271e9b9ac2857795ceff41b76ba2cd740`, plain arm64. CI log confirms 0013 applied; checksums passed. Entry PA `0xb146b488`, kernel end PA `0xb1ff4000`.
- Current log/buildtree: `research/run17.log`, `research/bt17` (extracted, no nested .git; preferred baseline for patch 0014). Payload/ADT: `shim/out/payload-0013.bin`, `shim/out/sweet-0013.adt` (includes /defaults). Unpacked ramdisk byte-compared with payload in `shim/out/check-0013`.
- Patch-0012 original image: `shim/out/shim-boot-0012.img`, 16,412,672 bytes, SHA256 `cf4b8ec4a65a51888d71c17d09cd0831d6b761b90e2531fdb8e575c32f4fd24a`. Kernel `xnu/out-0012/kernel.development.sweet`, SHA256 `69b78f49f6459cc63a0af44e7cf73c1779ef72130ef72b12ae86c88183ffc742`; checksums passed and sweet_early_relocate symbol present. Entry PA remains `0xb146b488`, kernel end PA `0xb1ff4000`.
- Patch-0012 log/tree: `research/run16.log`, `research/bt16` (extracted, no nested .git; preferred baseline for next patch). CI log confirms 0012 applied. Payload `shim/out/payload-0012.bin`, ADT `shim/out/sweet-0012.adt`; packed ramdisk byte-compared with payload in `shim/out/check-0012`.
- Active payload command line: `debug=0xc serial=3 cpus=1 keepsyms=1 -enable_kprintf_spam`.
- Latest observed photo: `/home/dipa/Downloads/IMG_20261015_071346.jpg` (local only). Stages 9 (kernel framebuffer VA), 10 (TTBR0 off/TLB flush), 11 (physmap table pointers) and 12 (calling pmap_bootstrap) all visible. Persistent diagnostics are VERIFIED ON HARDWARE.
- pmap.c:1987 is the assert after SecureDTLookupEntry(NULL, "/defaults", &entry). The pmap-max-asids property itself is optional; an empty /defaults uses XNU's MAX_ASIDS. Do not bypass the assertion or guess an ASID limit.
- Previous payload-only fix image: `shim/out/shim-boot-0012-defaults.img`, SHA256 `3ff61a268853c6ea7cbf284833f1346a1d791980ca366b6e1a215a86e040512b` (16,412,672 bytes). Same kernel/CI as 0012; ADT 2516 bytes (`shim/out/sweet-0012-defaults.adt`), root /defaults present with no ASID override. Payload `shim/out/payload-0012-defaults.bin`; unpacked ramdisk exactly matches payload (`shim/out/check-0012-defaults`). This boot reached the allocator crypto NULL-pointer fault below.
- Latest hardware photo: `/home/dipa/Downloads/IMG_20261015_071608.jpg` (local only). Normal serial framebuffer console works. VM bootstrap/zone initialization, logging, scheduler, IPC, KDP and ulock_initialize print before the kmem_crypto_init data abort. gPanicBase warnings are expected because PLATFORM_PANIC_LOG_DISABLED is configured, and are not the faulting call.
- Faulting instruction: `ldr x0, [x8, #0x150]` in crypto_random_kmem_ctx_size; x8 = NULL g_crypto_funcs. Source: libkern/crypto/corecrypto_rand.c and osfmk/vm/vm_kern.c:2448. rand.h explicitly permits NON-cryptographic kmem RNGs, but requires no locking in generation and context size <=256. Do not substitute read_random here: the global PRNG provider is also unregistered and kmem generation must remain lock-free. early_random may seed contexts during single-CPU bootstrap; it uses the built-in HMAC-SHA256 DRBG with the host-generated ADT seed.
- Patch 0013 keeps the replacement entirely private to vm_kern.c: SplitMix64 state is 8 bytes per CPU/sizeclass, initialized using early_random. Uniform selection uses rejection sampling to avoid modulo bias. Other platforms retain the original corecrypto calls; SWEET's generic crypto APIs/registration remain untouched. Reference: https://prng.di.unimi.it/splitmix64.c (Sebastiano Vigna, public domain).
- Validation: vm_kern.c compiles to arm64 (`research/kmem-rng-objs`, using `research/run16.log` + `research/bt16`). Undefined symbols include early_random and NO crypto_random_* references. All 13 patches apply in CI order and match the checked source. Original saved as `research/vm_kern.pre0013.c`.
- RNG host checks: extracted actual new helper in `research/kmem-rng-check.c`; 16,384 outputs match the author's downloaded reference (`research/splitmix64-reference.c`), 147,456 bounded outputs satisfy their limits (including 1 and UINT64_MAX), and a forced rejection advances correctly. Full kernel crypto services and the registered kernel PRNG provider remain future work; this patch only supplies the allocator RNG contract.
- Patch-0011 artifacts: kernel `xnu/out-0011/kernel.development.sweet`, log `research/run15.log`, extracted buildtree `research/bt15` (no nested .git). CI log confirms patch 0011 applied; artifact checksums passed. Kernel is plain arm64, entry VA `0xfffffe000746b488` -> PA `0xb146b488`, kernel end PA still `0xb1ff4000`.
- Patch-0011 image: 16,412,672 bytes, SHA256 `29ad5cbfc752473de4af2c471a24a8b34f92da4bff5afec65c614b90cd3ad53a`. Kernel SHA256 `8ac3a956894b09f7bd0d890de8c5de38c65513287feb1e1bcd12db8ca772ee5c`. Payload/ADT in `shim/out/payload-0011.bin`, `shim/out/sweet-0011.adt`. Header unpacked/checked in `shim/out/check-0011`.
- First patch-0011 attempt timed out waiting for FASTBOOT; superseded by the successful send/boot recorded above. Do not repeat the boot before the user reports the current screen.
- Patch-0011 photo: `/home/dipa/Downloads/IMG_20261015_070218.jpg` (local only). Visible stages 1-8 and old red shim text; entry PA B146B488, boot args PA B1FF8000 / top B1FFC000. No evidence yet locating execution after stage 8.
- Patch-0012 sandbox: `research/bt15/xnu` (NO nested .git). Proposed permanent debug VA: VM_MIN_KERNEL_ADDRESS + ARM_TT_L2_SIZE, in the reserved gap below gVirtBase and above low globals; map the same PA framebuffer as Normal-NC in the final TTBR1 before arm_vm_physmap_init changes phystokv(). Keep the early panic sink until normal kprintf startup.
- Patch 0012 validation: all 4 changed C translation units compiled to arm64 objects in `research/post-ttbr0-objs`; internal header export added to osfmk/arm64/Makefile and recreated locally in EXPORT_HDRS for pe_serial.c. All 12 patches apply in CI order and match all 6 edited files. Baselines are saved under `research/pre0012/`.
- Actual mapping-helper host model (`research/early-map-check.c`, barrier stubbed only for host compilation) confirms: VA `0xfffffe0002000000`, L1 index 2016, L2 index 1; descriptor `0x006000009c000605` = framebuffer PA, Normal-NC, outer-shareable, EL1 RW, PXN+UXN. All other L2 entries preserved. The gap is excluded by ARM_LARGE_MEMORY's pmap_virtual_region(0).
- Next boot command line MUST add `-enable_kprintf_spam`: DEVELOPMENT disables kprintf_output by default even when DB_KPRT is set (`pexpert/arm/pe_kprintf.c`). Planned command line: `debug=0xc serial=3 cpus=1 keepsyms=1 -enable_kprintf_spam`.

### Patch 0012 screen legend (after original stages 1-8)
- 9: kernel framebuffer VA live; 10: TTBR0 off / TLB flushed; 11: physmap pointers rebound.
- 12: calling pmap_bootstrap; 13: pmap_bootstrap returned; 14: early I/O page tables ready; 15: arm_vm_init returned.
- 16: calling serial_init; 17: fbcon config read / mapping; 18: fbcon mapping returned; 19: serial_init returned; 20: kprintf startup complete.
- Normal serial initialization clears the screen, so earlier stages may disappear before 19. If serial exists, early console disables after 20; otherwise early panic output stays enabled.
- Local source sandbox: `research/bt13/xnu` (git baseline `623b060`, patches 0001-0008 already in baseline; uncommitted export edits correspond to patch 0009). Preserve those edits when producing patch 0010.
- Previous compile log/tree: `research/run13.log`, `research/bt13`; previous kernel: `xnu/out/kernel.development.sweet`. New successful log/tree: `research/run14.log`, `research/bt14`; new kernel: `xnu/out-0010/kernel.development.sweet`.
- Current device access: patch-0012 image was temporarily started from FASTBOOT; no adb connection is expected. Never flash partitions for bring-up; use `fastboot boot` with the shim image.
- Patch `0010` lives in `xnu/patches/0010-sweet-early-framebuffer-debug.patch`. Its exact compiled sources are under `research/bt13/xnu`; generated objects are in `research/early-objs`.
- Local checks passed: all 5 changed/new translation units compiled to arm64 Mach-O objects; new console only imports `_doprnt` and `iso_font` (both exist in the previous kernel). All 10 patches applied to a temporary upstream git index in CI order, and all 7 resulting changed source files matched the local compile inputs.
- Reproduce changed-file compilation: `XNU_CC_OBJDIR="$PWD/research/early-objs" python3 tools/xnu-cc.py research/run13.log research/bt13 arm_init.c arm_vm_init.c kern/debug.c arm64/start.s osfmk/arm64/sweet_early.c --per-file` (create the output directory first). The helper now accepts explicit new source paths absent from the old artifact's Makefiles and rejects empty selections.
- Device command result: `adb reboot bootloader`, then `timeout 30s fastboot boot shim/out/shim-boot-0010.img`: send OKAY (16028 KB), boot OKAY, total 0.541s. This confirms bootloader acceptance only, not XNU progress.
- The successful boot above was on 2026-10-14. On 2026-10-15, `timeout 45s fastboot boot ...` timed out waiting for a device; no image was sent. Boot image SHA256 rechecked and unchanged. No new build is needed to repeat the trial.
- Earlier retry: `timeout 90s fastboot boot shim/out/shim-boot-0010.img` timed out (exit 124). This is superseded by the successful 2026-10-15 repeat boot recorded above; do not repeat it until the user reports the screen.
- User observation confirms MMU-on C entry, platform expert, CPU topology/bootstrap, startup bootstrap and cpu_init all complete. Failure is within arm_vm_physmap_init (non-XNU_MONITOR branch), before stage 8 / TTBR0 teardown. Old red shim text remains behind the early console; this is expected because only written rows are cleared.
- New edit/compile sandbox is `research/bt14/xnu` (extracted artifact, NO nested .git; `git diff` there would act on the parent project). Use a saved baseline file / generated unified diff, or explicitly initialize a local baseline before editing. `research/bt13/xnu` does have its own baseline git repo.
- Exact user-reported panic: `arm_vm_init.c:1606 Assertion failed: (temp_ptov_table[ptov_index - 1].va + temp_ptov_table[ptov_index - 1].len) <= physmap_end`.
- Root cause: MacOSX build sets `ARM_LARGE_MEMORY=1`; `XNU_MONITOR` is off. Block alignment in arm_vm_physmap_slide can add gaps, but the non-PPL large-memory physmap_end omitted the padding already present in the small-memory branch. Patch 0011 reserves PTOV_TABLE_SIZE*ARM_TT_TWIG_SIZE (8*32MB) in both the aperture bound and its L1 allocation; monitor/PPL builds retain zero padding. The assertion is preserved.
- Validation: `arm_vm_init.c` compiled to an arm64 object using `research/run14.log` + `research/bt14` (object in `research/physmap-objs`). All 11 patches apply in CI order and produce exactly that source. Host harness `research/physmap-check.c` extracts the real XNU slide function with page-table-write stubs: all 65,536 page-aligned slides within 1GB checked against the current kernel memory layout; old bound fails 65,504 cases, padded bound fails zero; worst overrun 0x1ffc000 bytes. Baseline source saved as `research/arm_vm_init.pre0011.c`.
- CI: https://github.com/dipa-studio/ios-sweet/actions/runs/38638702083 (success; artifacts and full log downloaded).
- New image: `shim/out/shim-boot-0010.img` (16,412,672 bytes, SHA256 `ed2c270e0081bad5ff517be415f9bfe8805463aea7866732203fa97ac737e64e`). Previous image preserved as `shim/out/shim-boot-pre0010.img`.
- New kernel SHA256: `3ee05270cc291c49589a101678f904b1b69cb2f2575e05398bce8a4e052f409a`. Artifact checksums passed; arm64 (not arm64e), early-console symbols present. Payload entry VA `0xfffffe000746a488` -> PA `0xb146a488`; kernel end PA `0xb1ff4000`. Command line remains `debug=0xc serial=3 cpus=1 keepsyms=1`.

### Patch 0010 screen legend
- Bottom-left white 64x32 tile: assembly entered `start_first_cpu`, before page tables/MMU.
- Text `SWEET EARLY 1`: entered `arm_init` with MMU on; 2: platform expert done; 3: CPU topology done; 4: CPU bootstrap done; 5: startup bootstrap done; 6: CPU init done; 7: entering `arm_vm_init`; 8: leaving bootstrap TTBR0.
- `SWEET EARLY PANIC:` prints a copy of panic arguments before normal panic handling needs per-CPU/thread state.
- In patches 0010/0011 the console disabled before TTBR0 invalidation; patch 0012 replaces that with a persistent kernel VA alias and diagnostics through normal serial/kprintf startup (see its legend above).
- Screen contents require a physical observation from the user: adb cannot capture a framebuffer after Android has been replaced by a bare-metal kernel.

## QEMU emulation (2026-10-15)
- `tools/mkadt.py OUT.adt --qemu` = same ADT with QEMU virt GICD 0x08000000 / GICR 0x080a0000 / CNTFRQ 62.5 MHz.
- `tools/qemu-sweet.py PAYLOAD OUTDIR [--secs N] [--hmp "x /8gx ADDR"] [--gdb]`: host-side copy of shim/loader.c
  (segments + ADT + boot_args at their PAs, 6-instruction stub sets x0 and jumps), `-M virt,gic-version=3 -cpu cortex-a76`
  (same ID_AA64MMFR0 as Kryo 470), 4G RAM so 0x9c000000 fb and 0xb0000000 kernel are plain RAM.
  Outputs `fb.png` (the screen), `regs.txt`, `qemu.log` (exceptions with ESR/FAR/ELR). `--gdb` halts with a stub on :1234
  (system `gdb` + `set architecture aarch64`, `hbreak *VA` works with the MMU on).
- Not emulated: Qualcomm XPUs, ABL, real panel, PSCI conduit (QEMU virt uses hvc). Hardware still decides those.
- Example: `python3 tools/mkadt.py /tmp/q.adt --qemu && python3 tools/mkpayload.py xnu/out-0013/kernel.development.sweet /tmp/q.adt /tmp/pq.bin --cmdline 'debug=0xc serial=3 cpus=1 keepsyms=1 -enable_kprintf_spam' && python3 tools/qemu-sweet.py /tmp/pq.bin /tmp/q`

## Layout
- `backup/`  partition dumps + full sdb..sdf LUNs, `SHA256SUMS` (all verified on-device == local)
- `dtb/`     live FDT (from OrangeFox), PixelOS boot.img dtb, dtbo, dts versions
- `shim/`    bare-metal boot shim (`./build.sh` -> `out/shim-boot.img`)
- `research/` mainline sm7150 dts, XNU pe_fiq.c etc, PocketDarwin patches
- `tools/unpack_bootv2.py`

## Device access
- No root in PixelOS 17 (user build, adb root disabled). Root = `fastboot boot recovery/recovery.img` (OrangeFox R12.0_2, temp boot, not flashed).
- `fastboot boot` works for stock boot.img, OrangeFox, and our shim.
- Shim resets itself via PSCI SYSTEM_RESET; IMEM restart_reason 0x77665500 is seen
  (bootreason=bootloader) but ABL still boots Android, so it does not stop in fastboot.

## Hardware facts (live DT + shim measurements)
- Framebuffer (ABL cont splash): 0x9c000000, 1080x2400, stride 4320, a8r8g8b8, panel is DSC *video* mode (no kick needed).
- RAM: 0x80000000+2G, 0x100000000+0xfcc00000. Live reserved-memory = PixelOS base dtb + sweet dtbo fixups.
- GICv3: GICD 0x17a00000, GICR 0x17a60000 (stride 0x20000, 8 PEs). GICD_TYPER 0x007B041D: SecurityExtn=1 (DS=0).
  ABL leaves GICD_CTLR = 0x10 (ARE_NS on, groups off). Writing 0x13 reads back 0x12: EnableGrp1A (bit1) is the one that matters.
- GIC Group 1 VERIFIED (shim 2c): vtimer INTID 19 = 30 IRQs/300ms, ptimer INTID 18 = 30, SGI 1 to self = 10/10.
  ICC_SRE=1 already, ICC_CTLR 0x8440, priority/enable writes stick. GICR_IGROUPR0 and GICD_IGROUPRn read 0 from NS
  even though Group 1 delivery works (RAZ in NS view) - do not use them as a health check.
  INTID 28 shows pending constantly (unknown PPI 12).
- Timer 19.2 MHz. Qualcomm PPI numbering: secure-phys/phys/virt/hyp = PPI 1/2/3/0 -> vtimer INTID 19, ptimer 18 (NOT 27/30).
- PSCI 1.1 via SMC, SMCCC 1.1. CPU_ON ok; SYSTEM_SUSPEND and SYSTEM_RESET2 unsupported.
- SMP: CPU_ON works for all 7 secondaries (MPIDR 0x81000n00).
- Entry EL1, MMU off, x0 = DTB (magic ok). ID_AA64MMFR0 = ...101122: 16K granule YES, 4K YES.
- No serial console: debug UART SE is in SPI mode on sweet. Screen is the only debug channel.

## XNU implications
- XNU GICv3 path (pexpert/arm/pe_fiq.c, VMAPPLE) puts the timer (PPI 27) in Group 0 = FIQ. With SecurityExtn=1,
  Group 0 is secure -> impossible from NS EL1. Need: Group 1 IRQ, ICC_IGRPEN1, INTID 19, and the timer handled in the IRQ path.
- XNU VMAPPLE PSCI uses `hvc`; sweet needs `smc`.
- PocketDarwin NonAppleGenericCpu.patch only swaps -mcpu=apple-h7 for -march=armv8-a.

## Milestone 3 (2026-10-14): 16K MMU verified
- ABL loads the Image at 0x80080000 (base 0x80000000 + 0x80000) regardless of text_offset=0.
- 16K granule, T0SZ=28 (L2 start, 32MB blocks), MAIR 0x44ff00, TCR 0x1409CB51C, PARange=2 (40-bit PA).
- Only own image pages WB (Qualcomm XPUs: never map carve-outs cacheable); fb Normal-NC; rest Device.
- AT S1E1R checks all as expected; unmapped -> translation fault L2.
- Fill fb: 110 ms (MMU off) -> 3.5 ms (NC). Memory loop 70 ms -> 0.7 ms. vtimer + SGI IRQs still fine with MMU on.

## XNU loader design notes (xnu-8796)
- Entry: `_start` -> `start_first_cpu`, x0 = boot_args (PA), MMU off, EL1. boot_args: Revision/Version 2,
  virtBase/physBase/memSize/topOfKernelData, Boot_Video (fb 0x9c000000, rowBytes 4320, 1080x2400, depth 32),
  deviceTreeP/Length (ADT), CommandLine[608], bootFlags, memSizeActual.
- start.s maps [kernel mach header .. physBase+memSize) with cacheable BLOCKS. On Qualcomm every XPU carve-out
  must therefore lie below the kernel: use physBase = 0xb0000000 (above ramdump_fb 0xaf000000+16M,
  cdsp_sec, qseecom), end before rmtfs 0xfde01000 -> memSize ~0x4d000000 for bring-up.
- Base ADT: iPhone 8 d20ap DeviceTree from iOS 16.7.16 IPSW (tools/remotezip.py + tools/adt.py; LZFSE payload).
  Template values are empty: the loader must fill chosen/*, memory-map, cpu*/reg etc. like iBoot.
- XNU build: GitHub Actions (dipa-studio/ios-sweet, xnu.yml) via blacktop/darwin-xnu-build, MACOS_VERSION=13.5.
  New-clang fixes in xnu/patches; Xcode 16 iig is incompatible (IORPC.kernelContent) -> macos-14 runner, oldest Xcode.

## Kernel architecture plan (SWEET machine config)
- First stock build (VMAPPLE) is arm64e (PAC). Kryo 470 = ARMv8.2, no PAC -> SWEET must build plain arm64
  (HAS_APPLE_PAC is only defined for __arm64e__, so arm64 drops PAC automatically).
- Template: VMAPPLE (16K pages, GICv3 code in pe_fiq.c) minus APPLEVIRTUALPLATFORM hypercalls/paravirt PAC,
  plus BCM2837 (generic ARM: no APPLE_ARM64_ARCH_FAMILY Apple sysregs). Do not link the KDK lib<cfg>.os.*.a.
- Timer: XNU expects it on FIQ (sleh_fiq -> rtclock_intr). SWEET: GIC Group 1, so sleh_irq must ack ICC_IAR1,
  route INTID 19 to the same timer path, SGIs to cpu_signal_handler, EOI via ICC_EOIR1.
- SMP/interrupts: open-source AppleARMSMP (USE_APPLEARMSMP) needs an IOInterruptController (AIC role) and an
  IOPMGR (CPU power -> PSCI CPU_ON via SMC). Plan: built-in IOKit classes (SweetGIC, SweetPMGR, platform
  expert) compiled into the kernel and matched via iokit/KernelConfigTables.cpp -> no closed kexts needed.
- Debug: xnu patch 0003 sweet-fbcon = kprintf drawn on the framebuffer (ADT node "sweet-fbcon").
- ADT /arm-io ranges must not map to parent 0 (pe_arm_get_soc_base_phys()==0 disables serial): use parent 0x1000000.

## Status 2026-10-14 late: first XNU boot attempt
- SWEET kernel builds (CI run 38635343732, patches 0001-0009). Verified offline: arm64, no PAC, no >v8.2 code,
  70300 classic relocs all in range (slide 0 = no loader work), entry = __start.
- Boot: shim loader worked (initrd 0x846F0000-0x855FE3E0, BOOTARG 0xB1FF8000, JUMP 0xB146A488) but screen stayed
  red -> xnu died/hung before serial_init (fbcon). kprintf is a no-op before STARTUP_SUB_KPRINTF.
- Historical next-step plan (patch 0010, now implemented and built; see active handoff above): early fb debug channel
  1. start.s start_first_cpu (after mov x20,x0 / mov x21,#0): PA marker band (MMU off, direct store to 0x9c000000).
  2. start.s after both create_bootstrap_mapping calls: add ONE block entry to the existing V=P L2 table
     (x25 + 2*PGBYTES; do NOT call create_bootstrap_mapping again: fb and RAM share L1 entry 0, it would replace
     the L2 table). Entry = TYPE_BLOCK|VALID|SH(OUTER)|ATTRINDX(CACHE_ATTRINDX_WRITECOMB=1)|AF|PNX|NX|0x9c000000,
     index = (va & ARM_TT_L2_INDEX_MASK) >> ARM_TT_L2_SHIFT.
  3. new osfmk/arm64/sweet_early.c (+files.arm64 entry): sweet_early_mark(n) colored bands at screen bottom and
     sweet_early_putc using iso_font via VA=PA while the bootstrap TTBR0 is live; disable before
     arm_vm_init's set_mmu_ttb(invalid_ttep) (arm_vm_init.c:2148).
  4. markers in arm_init after PE_init_platform, ml_parse_cpu_topology, cpu_bootstrap, kernel_startup_bootstrap,
     cpu_init, before arm_vm_init.
  5. panic hook at top of panic_trap_to_debugger: va_copy + _doprnt(fmt, &copy, sweet_early_putc, 16).
  Verify with tools/xnu-cc.py (compile+symbols) and patch-order simulation before the single CI run.

## Touch supply probe, 2026-10-26 (patches 0112-0120)

The chip is silent for a reason on the PMIC side, but the PMIC access layer is
only half-trusted yet. Facts, in order of confidence:

**SPMI now works from XNU, but only just.** The old observer path in
`bsd/dev/sweet_spmi.c` (core `0x0c440000`, observer `0x0e600000`, 0x80 per APID)
is for another SoC: its arbiter version reads 2 on matisse, so it never
initialised. Added a PMIF backend at `0x1c015000` using the mt8195 register
table (`PMIF_INIT_DONE 0x0`, `INF_EN 0x24`, `ARB_EN 0x150`,
`CMDISSUE_EN 0x3b8`, SWINF channel 2 at `0x880`/`0x884`/`0x894`/`0x8a4`/`0x8a8`)
and the upstream command encoding
`(1 << 30) | (sid << 24) | ((len-1) << 16) | addr`, write adds `BIT(29)`.
Reads work: `init_done=1`, `INF_EN=0x1fbfff`, `ARB_EN=0x1ebfff`,
`CMDISSUE_EN=1`, first SWINF state `0x8441` (IDLE) then `0x2844d`
(WFVLDCLR, no error bit).

**Bug still open:** the channel does not return to IDLE after a few reads.
`VLD_CLR` is written at `0x8a4`, yet `SWINF_STA` still shows WFVLDCLR
(`0x2844d`), and later reads time out and return -1. Confirmed in the
`addrcheck` boot: reads at marks 162/165 succeed, the batch at marks 168/169
fails. Any conclusion drawn from a read must be checked against the error
byte; a value of `0xff` with err `0xff` is a failed read, not data.

**MT6373 rails (SID 5), while reads still worked:**
- `0x1bbf` (VRF18_AIF enable) = `0x00` before any write, on every boot. The
  bootloader leaves the touch 1.8 V rail off, which is consistent with the chip
  never answering.
- `0x1d23` (VTP enable) = `0x03` (EN + LP).
- `0x1e8d` (VRF18 vosel) = `0x07`, `0x1e35` (VTP vosel) = `0x75`. These do not
  match Recovery's 1.8 V / 3.3 V for the documented tables, so the address or
  field mapping is not yet proven. Treat the enable bits as probable and the
  vosel bytes as unverified.

**Writing the enable bit: only the base register is safe.** Writing 1 to the
buck-style `SET` alias `0x1bc0` crashed or wedged two consecutive boots
(`power`, `power2`: marks stop at 101/88, no panic record). The vendor LDO path
uses `regmap_update_bits` on the base register, so writing `0x01` to `0x1bbf`
is the correct form; that write returns 0, reads back `0x01`, and the system
survives. `sweet_spmi_write` is restricted to `0x1bbf` and `0x1d23` only.

**Chip still does not answer with the rail on.** Three boots with
`sweettouchpower=1` ran: rails enabled (`0x00 -> 0x01`), reset pulsed low 20 ms
then high (`dir=1, din=1`, i.e. released), and a 120 ms settle. Chip ID stayed
`00:00` (`mark 96`, `a=0`). Adding the driver's first real command, a one-byte
system reset `0x81` followed by 20 ms, also left the ID at `00:00`
(`mark 167`), and the SPI-level bit-bang still reads eight zero bytes.

**Recovery dmesg (`[ FTS ]`) shows what a working init looks like:** openChannel
(SPI mode 0, 12 MHz, CS0) -> `System resetting...` -> 23 ms -> `System reset
DONE!` -> `FW VER 0020`, `SVN REV 6160`, `Protocol 06`, screen 3199x1439. It
also logs `fts_enable_reg: Failed to enable vadd`, so even there the avdd
enable call reports an error while the rail is on, i.e. that rail is already
powered by someone else.

**Next:** fix the PMIF VLD_CLR handshake first (either the clear offset for
channel 2 or a required read of RDATA before the clear), because without a
reliable read the rail question cannot be closed. Then re-run the SID 0
control read (`0x4804` must be `0x0d`, `0x4808` bit0 set) as the addressing
proof before trusting `0x1bbf`. If addressing is confirmed and VRF18 is really
on, the remaining candidates are the display-side rail the panel needs or a
chip held in download mode, and the next probe should sample `PIO DIN` for
SCK/CS during a long transfer instead of guessing at commands.

Artifacts: `matisse-xnu-touch-{supply,pmifread,power,power2,ldoen,idonly,idreset,sysrst,addrcheck}.{img,json,payload}`
in `research/matisse/20261025-touch/`, with `*-after-marks.{bin,txt}` for each.
Every trial restored the full `boot_a` backup; on-device `sha256sum` was
`2931647a56...86b1` after every restore.

### Follow-up, same day (patches 0121-0126)

**PMIF reads are now reliable.** The failure mode was self-inflicted: a command
that returned an error left the channel in WFVLDCLR because the error path never
wrote VLD_CLR, and every later transfer timed out on the IDLE wait. `sp_pmif_read`
now retries the whole sequence three times, clears the flag on every path, and
polls for IDLE after the clear. `sweet_spmi_sta3()` reports the state before,
after and post-clear so a stuck channel shows up in the marks.

**SID 0 does not exist on matisse.** The device tree puts the primary PMIC at
`pmic@4`; `second_pmic@5` is the MT6373. Reads to SID 0 fail with the error bit
set, which is expected. The control read was moved to SID 4:
`0x4804` returns `0x00` with err 0 (no charger attached, so 0x0d is not
expected here) and the channel returns to `0x8441` (IDLE) afterwards, so the
16-bit PMIF address does reach the intended byte. MT6373 (SID 5) reads:
`0x1bbf = 0x00`, `0x1d23 = 0x03`, `0x1e8d = 0x07`, `0x1e35 = 0x74`.

**Drive strength and pad watch.** `SWEET_MARK_MAX` was raised from 96 to 160
(the block is still one 4 KiB UFS block). A 64-byte transfer now samples the
PIO DIN word back to back instead of once per microsecond (`mark 175`). Result:
CLK (pin 167) toggles, MOSI (pin 166) toggles, CSB (pin 165) stays asserted for
the whole transfer, and MI (pin 164) never leaves 0. So the controller drives
all three outputs onto the pads correctly and the chip never drives MISO. The
64-byte frame also exceeds the 32-entry FIFO, so that transfer stalls with CS
low; later transfers reset cleanly.

**Two PMIC writes are now characterised by their blast radius.**
- `0x1bbf <- 0x01` (VRF18_AIF enable, base register): returns 0, reads back
  `0x01`, system healthy. This is the only rail write that is safe so far.
- `0x1d23 <- 0x01` (VTP, clearing the bit the vendor header calls LP): returns
  0 but the boot dies immediately afterwards (`vtpnlp`: last mark 163, no panic
  record). Either bit 1 is not LP on this board or switching that rail out of
  LP mode collapses something else. **Do not write 0x1d23 again** without a
  schematic.
- Earlier, `0x1bc0 <- 1` (the buck-style SET alias) also wedged two boots.

**Still no chip response with VRF18 on.** Boots `idonly`, `idreset`, `sysrst`,
`fwver`, `padwatch` all had VRF18 enabled, reset asserted before power and
released 15 ms after, a 120 ms settle, and (in the later ones) the driver's
first command 0x81 plus 20 ms. Chip ID stayed `00:00` and the FW VER read at
`0x20000004` (Recovery reports `0x0020` there) returned eight zero bytes.
Touch INT (GPIO8) reads 0 in all 64 samples while Recovery reports the same pin
as `in hi`; base 11 for its IES is `0x11f10000` + 0x60 bit 16 and that bit was
already set, so the reading is real.

**Where this leaves it:** controller, mux, IES, bias, CS/CLK/MOSI signalling and
the 1.8 V enable bit are all verified, and the chip still behaves as if it has no
power. The unexplained part is whether `0x1bbf` actually closes the LDO switch
on this board, and which rail the controller's core runs from. The next step
needs board-level information (schematic or a rail measurement), or a read-only
look at the MT6373 LDO status/OCP registers to see whether VRF18 reports a
normal output after the enable write. Do not write `0x1d23`.

## Golden PMIC state from Recovery, 2026-10-26 (patches 0127-0131)

The TWRP device tree at `/Users/xiaohuasheng/Documents/twrp` and a leftover
`ramoops.txt` gave two facts that closed the "is it powered" question:

1. `mt6373-regulator.ko` logs `mt6373_vtp: Bringing 1800000uV into
   3300000-3300000uV` at module load: the hardware VTP selector is **1.8 V** at
   boot and the Recovery kernel raises it to **3.3 V** because the device tree
   pins it (`regulator-min/max-microvolt = 3300000`). Nothing in XNU ever did
   that. Same for VRF18_AIF, pinned at 1.8 V (`ldo_volt_table3[12]`).
2. `/sys/kernel/debug/regmap/0-05/registers` is readable on this kernel, so the
   **full MT6373 register file can be dumped from Recovery**. The working state
   (touch alive, `input2 = fts`) is:

   | register | meaning | working value |
   |---|---|---|
   | `0x1bbf` | VRF18_AIF enable | `0x01` |
   | `0x1e8d` | VRF18_AIF VOSEL | `0x0c` = 1.8 V |
   | `0x1d23` | VTP enable / LP | `0x01` (EN=1, LP=0) |
   | `0x1e35` | VTP VOSEL | `0x0d` = 3.3 V |

   Saved as `research/matisse/20261025-touch/recovery-mt6373-regs.txt`
   (65536 lines, addresses `0000..ffff`). XNU at boot has `0x00`/`0x07` and
   `0x03`/`0x74`, i.e. both rails off-or-low and VTP in LP mode.

**Every write that actually changes a rail kills the SoC.** Measured, with marks
written straight after each write:

| write | result |
|---|---|
| `0x1bbf <- 0x01` (VRF18 enable) | safe, reads back `0x01`, boot completes |
| `0x1e8d <- 0x7c` (VOSEL keep high nibble) | safe, but chip still silent |
| `0x1e8d <- 0x0c` (real 1.8 V selector) | **boot dies** right after the write |
| `0x1e35 <- 0x0d` (real 3.3 V selector) | **boot dies** |
| `0x1d23 <- 0x01` (clear LP, VTP stays on) | **boot dies** |
| `0x1d23 <- 0x00` (disable VTP) | **boot dies** |

The high nibble of the VOSEL registers reads back as `0x7`, so writes that
preserve it (0x7c/0x7d) are survivable but evidently do not move the rail; the
values Recovery reports (0x0c/0x0d) do move it and take the SoC down within a
few milliseconds. That means VTP — and probably VRF18_AIF — also feeds something
the XNU boot needs, and the change has to happen in the same quiet window the
vendor kernel uses (module init at ~1.2 s, before storage and display are up),
not from a worker thread two seconds in.

**Next:** move the rail setup out of the touch worker into the earliest board
hook available (the UFS init path in `bsd/dev/sweet_ufs.c` runs before the root
mount), gated by its own boot argument, so the selectors are programmed and the
rails sequenced before any driver is using those supplies. Keep the order
`vdd (VRF18) -> avdd (VTP)`, keep LP cleared, and re-read `0x1bbf`/`0x1d23`/
`0x1e8d`/`0x1e35` afterwards to compare against the golden table above. If that
still panics, the remaining explanation is that these two LDOs also supply a
SoC subsystem and the change belongs in the bootloader.

## Session closed, 2026-10-26 08:40

Full write-up of the touch bring-up effort (patches 0101-0137) is in
`docs/matisse-touch-report.md`. Short version: the SPI6 controller, its pads,
pinmux/IES/bias, the reset line and the SPMI/PMIF write path are all verified
correct; both MT6373 rails can now be raised to the device-tree voltages with a
100 mV/5 ms stepped ramp without upsetting the SoC; the controller still never
drives MISO or INT. The only remaining known difference from the working
Recovery state is VTP's LP bit (0x03 here, 0x01 there), and every attempt to
change 0x1d23 kills the SoC - in the worker, in the pre-mount window, at 1.8 V
and after the 3.3 V ramp. Do not write 0x1d23. Do not step a VOSEL in one go.
Device left in Recovery with boot_a restored to 2931647a56...86b1.
