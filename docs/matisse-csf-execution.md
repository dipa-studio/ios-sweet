# MT6983 / Mali-G710 CSF execution — 2026-11-09

The port now executes CSF commands and a Valhall compute shader on the phone.
This establishes hardware execution. The resident XNU driver and a hardware-only
Mesa CSF transport now exist; hardware-rendered system UI is not yet verified.

## Hardware results

| Trial | Result | Observation |
| --- | --- | --- |
| 2433 | Failed | AS1 UPDATE produced MMU bit17; the queue wrongly classified this completion event as a fault and stopped at poll1. |
| 2434 | Failed | After fixing the mask, CSG START acknowledged, then AS0 fault bit0 appeared. CS had not started. |
| 2435 | Passed | Moving queue interfaces from `0x08000000` to `0x06000000` removed the failure. The GPU wrote `0x2433c5f1`; insert/extract were both32 bytes. |
| 2436 | Passed | A four-instruction Valhall compute shader wrote `0x2436c5f1`; insert/extract were both192 bytes. Queue completion used a separate memory location. |

2435 completed in10 polling iterations and2436 in18. These counts are not
performance measurements. Both had zero CS fault/fatal and AS fault status,
matched CSG/CS state ACKs, terminated the group, disabled the MCU, and completed
the outer GPU reset with cleanup_error0. MMU RAWSTAT0x20000 is AS1 request
completion, not a page fault. All four captures have independently checked
trial boot arguments, changed persistent logs, image readback and kernel mark.

All four trials restored the full64MiB boot_a backup. Its independently checked
SHA256 is `2931647a56039722ea2585990b8ef3b1a2daf4c9b990231879f753049eaf86b1`.
2434 required the user to enter Fastboot;2433/2435/2436 returned automatically.
No filesystem/root edits were needed for these tests.

## Implemented path

`xnu/gpu/mali_csf_queue.c` owns queue, IO, completion and suspend memory in
the unused tail of the shim firmware arena. It programs AS1 and CSG0/CS0,
submits commands, checks actual memory/extract/ACK results, and terminates.
The existing outer boot transaction resets the GPU before releasing power.
Firmware and its established boot mapping/power sequence are unchanged.

For2436, one page is read-only executable shader memory; other new pages are
noncacheable RW/XN. The command stream requests compute resources, sets the
shader/local-storage descriptors and a1x1x1 workgroup/grid, runs the shader,
waits, flushes caches and records a separate queue completion. The shader alone
writes the compute witness. Its four words were checked against Mesa25.0.7's
Valhall assembler.103 host tests pass, including actual C under ASan/UBSan,
command/shader decoding, injected faults and rejection of incomplete evidence.

## Sources and next integration

The Linux reference is commit7475ea8b58616b33c04afb976cf0fbaad9dd63fb;
Xiaomi r32p1 is270b84910b941bf75490fccdb5fb2b3021dd7cbf. Panthor's MCU shared
window is `[0x04000000,0x08000000)`. Its MMU fault mask uses only bits0..15.
Xiaomi's CSF scheduler and interface definitions supplied the CSG/CS register
layout; Mesa25.0.7 `v10.xml`, `pan_csf.c` and Valhall assembler supplied the
command, descriptor and shader encodings. Locally pinned source hashes are in
the ignored `research/matisse/20261109-gpu-sources/sources.json`.

Keep GLES as the working frontend and connect Mesa's v10 CSF backend. HakiOS's
v7/JM Darwin backend is not a G710 submission driver. The next concrete work is
resident XNU GPU ownership, separate application VM/BO mappings, a userspace
submission/completion interface, then Mesa BO/group/heap/fence integration.
The current shim always resets and drops power at return; it must not be
represented as a resident driver or hardware-accelerated backboardd.

Implementation commits: c034b5b,2e5c0eb,560f3d0,8faebd9. These trials reused
kernel2431; no new kernel build or CI run. Final image2436 SHA256:
`d5468945fe4eb1df16d7682a474308cdbd6213b10c957662a0e198afbaf0d435` (26718208B).
Exact manifests, logs and decoded results are under ignored
`research/matisse/20261109-gpu/`; `queue-compute-verified.json` indexes the four
verified captures. No downloaded firmware, device dumps or serials are in git.

## Normal UI and userspace integration (2442–2443)

2442 restores service registration immediately after the three proven resident
compute submissions. The later VM stress test now requires
`sweetgpuvmtest=1`. Normal UI boots also retain the writable root needed for
HFS journal replay; the diagnostic read-only configuration logged journal
replay failures. The phone displayed an interactive UI in2442, with nine GPU
status samples reporting MCU1, three submissions and zero failures. This
proves coexistence of the UI and resident GPU, not accelerated UI rendering.

The Darwin transport implements BO allocation/mapping, separate address
spaces, persistent CSF groups, synchronous submissions and timeline fences.
Fences are signalled only after the kernel observes GPU-written completion.
`tools/build-sweet-panfrost.py` builds pinned Mesa25.0.7 with the HakiOS GLES
bridge, v10 CSF backend and the actual G710 product ID. The hardware profile
returns failure if GPU screen creation fails; it cannot fall back to softpipe.
Its VA range excludes SweetGPU's low128MiB firmware/queue aperture.

`sweetgles=2` enables the hardware library path, exec injection, AMFI90 dyld
permissions and IOSurface BGRA negotiation. Mode1 remains the prior software
validation profile. The first integration uses `glcopy=1`: shaders and
rasterization are intended to execute on the GPU, with CPU readback/copy for
IOSurface presentation. Direct IOSurface import and cross-process fences are
not implemented, and those transport requests return unsupported.

2443 started the hardware-required GLES program and reached GPU user-client
creation. Persistent checkpoints show a16KiB page-table allocation at physical
address0x108fe0000, zeroing and successful AS1 root binding. The last durable
record is the bind return; no user-client return, renderer string, graphics
submission or pixel result was captured. The phone showed black and needed
manual Fastboot. A checkpoint flush stall is a hypothesis, not an established
cause. Both2442 and2443 restored and independently verified the full boot_a
backup. Evidence and root-delta preimages stay in ignored research directories.

2444 disabled synchronous allocation checkpoints and installed the G710
product-table entry. Hardware Mesa opened the GPU and reached its first CSF
submission, which timed out with extract0/128, no CS fault/fatal, and only
MMU request-completion bit17. Context creation failed; no pixels were drawn.
The full boot_a backup was restored and independently rehashed.

2445 rings the user doorbell selected by CS_CONFIG after publishing INSERT,
matching the pinned Panthor queue_run_job path. The global doorbell remains
for firmware interface requests. The host model now distinguishes these
paths and checks100 submissions/ring wraps and timeout/fault handling.
The PID1 probe waits for the diagnostic recovery timer after success/failure
to keep its result from being overwritten by a second boot. Hardware testing
is pending. Next verify real draws/pixels, then backboardd completed frames.
Neither a registered service nor a renderer string alone proves accelerated
system UI. Source milestones:9f6c6cb,b8b99be,e04725b. Full local kernel builds
passed; GitHub Actions dispatch returned HTTP422 because the fork's Actions
are disabled, so these milestones have no new CI run ID.

## Resident XNU handoff (2437)

Commit1960662 retains the firmware arena and acquired power reference, passes
an explicit128-byte handoff through the ADT, and installs SweetGPU in XNU.
The2437 hardware boot completed three independent compute submissions inside
XNU; all returned stage7, shader witness2436c5f1,192-byte extract/insert and
no AS fault. SweetGPU registered its IOService; two later status records showed
MCU1 with three successes and zero failures. The full boot_a backup was
restored and rehashed. This proves resident ownership/execution, not Mesa
hardware rendering. The remaining work is BO/VM, persistent command-stream
submission, synchronization, and Mesa v10 integration. Kernel/image manifests
and fresh console evidence are under20261109-resident-gpu.
