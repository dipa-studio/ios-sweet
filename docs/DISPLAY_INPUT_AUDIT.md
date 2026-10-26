# Offline display and input audit — 2026-10-25

## 2026-10-25 input fix and bounded smoke test

`tools/qemu-sweet.py:qmp_wake_tap` now validates x/y as integers in 0–32767,
and `press_ms` as an integer in 1–5000. It sends ABS_X, ABS_Y and button down
in QMP request 1, waits the configured press interval, then sends button up
in request 2. Both replies are checked. If request 1 or the interval fails,
it attempts release and propagates the original failure; a failed release
also propagates. The runner exposes `--wake-press-ms` (default 100).
The control helper already calls `qmp_wake_tap` and inherits this behavior.

Mock QMP regression `tools/test-qmp-input.py` verified packet separation,
coordinate order, response errors for capabilities/down/up, invalid input
rejection and both call sites. `py_compile`, the manifest regression and
WSL repository validator passed (89 patches, 19 Python tools, 7 shell
scripts). No kernel, root image or nested repository was edited.

One smoke run used 0086, `root-0084i.img` with `snapshot=on`, one vCPU,
`--input`, `--trace errors`, a 240-second host deadline, four scheduled taps
and a 150 ms press. Run directory:
`research/vm/run20h-0086-input-smoke-20261025/`.
Manifest state is `finished`, duration 240.501 s; runner exited 0 and QEMU
was stopped. Wake log records **4 successful taps = 8 accepted QMP input
packets**. Deduplicating overlapping msgbuf snapshots gives **4 guest
touch-down and 4 guest touch-up edges**, all at panel 540,1200. Guest times:
89.786/89.938, 134.668/134.819, 179.600/179.748 and 224.469/224.622 s.
Thus QMP acceptance and SweetHID processing both succeeded for all four
smoke taps. This verifies the input protocol fix in a booted guest; it does
not assess SpringBoard navigation or GTK. The run was headless and logged
that no RAMFB device was attached. The source root image retained its size
17,179,869,184 bytes and mtime_ns 1792875241146249200.

`tools/capture-display.py` now prepares a separate GTK comparison capture:
it identifies the QEMU process/window from a run manifest, records a GTK
window screenshot, pauses QEMU, saves retained guest raw framebuffer and
QMP screendump, captures msgbuf display/swap/touch lines, then resumes QEMU.
`capture.json` records timestamps, window identity and image hashes.
This tool passed syntax/import help checks but was **not run** during the
headless input smoke. The captures are close in time, not an atomic three-way
frame; timestamps must be checked when comparing them.

## Previous offline audit

No QEMU was launched during this earlier audit, and no kernel or image was changed. No commit/push was
made. Existing uncommitted work was retained.

## Historical image provenance

The original PNGs, not only contact-hour.png, were inspected:

| run20h-hour capture | Visible content | Last msgbuf timestamp (not capture time) | PNG SHA-256 prefix |
| --- | --- | ---: | --- |
| snap011 | Home Screen | 2596.740321 | 1ab4a2f96738fadc |
| snap015 | Settings | 2881.854848 | 555ad2c1f97943c2 |
| snap016 | Same Settings image | 2900.418281 | 555ad2c1f97943c2 |
| snap017 | Transition into General | 2917.165223 | 04c379af235526dc |
| snap018 | General | 3112.013503 | 5b1b9ddf5f4ba007 |
| snap019 | General, About selected | 3124.277322 | 2bdebf63fd625052 |
| snap020 | About, iOS 16.7.16 / iPhone X | 3258.392237 | 0a7807ece5684513 |
| snap021 | About, clock advanced | 3511.353585 | 5f7ded0f749ac0fb |

All are 1080x2400. Logs corroborate the sequence: touches at panel 148,571
at guest 2661.50/2662.75, exec Preferences at 2663.969849, General tap at
481,1799 at 2910.453481, and About tap at210,414 at 3119.767291. These are
strong evidence of historical guest rendering and interaction. They are
not proof of a matching host-window presentation or sustained stability.

`research/snapshot-qemu.py` identifies QEMU using the run's ram.bin path,
pauses it, calls QMP pmemsave at 0x9c000000 for 4320*2400 bytes, then invokes
`tools/qemu-sweet.py:write_png`. The writer converts B,G,R,X bytes to PNG RGB;
it does not draw UI or fetch external images. The raw file is then deleted.
The runner's final fb.png follows the same physical-memory path.

Neither audited run directory contains retained fb.raw, PPM screendumps,
or identified GTK-window captures. The historical run also lacks a manifest.
Thus original raw-to-PNG equality and simultaneous raw/screendump/GTK
equality cannot be verified retrospectively. Current scripts explain the
capture method; they are not an immutable per-capture provenance record.

## Display contract

The source chain is IOSurface -> AppleCLCD::present -> boot framebuffer
memory -> QEMU RAMFB surface -> GTK. Snapshot capture branches off at guest
memory, before RAMFB and GTK.

The inspected SweetFramebuffer source uses boot video address/stride and
copies IOSurface rows into it. It presents logical 1125x2436 coordinates
cropped to the physical 1080x2400 panel. That explains cropping at the edges;
it does not establish a raw-versus-GTK mismatch.

`sweet_ramfb.c` configures address 0x9c000000, 1080x2400, stride 4320,
DRM_FORMAT_XRGB8888, using a packed 28-byte big-endian fw_cfg descriptor.
The PNG reader uses the same address/shape/stride and little-endian BGRX
layout. Both run logs report successful RAMFB configuration with selector 37:
historical guest 31.224268; control guest 33.413716.

Upstream [QEMU RAMFB source](https://github.com/qemu/qemu/blob/master/hw/display/ramfb.c)
decodes these big-endian fields, maps guest physical memory as its surface,
and requests a full display update. No static address/stride/format mismatch
was found. A successful fw_cfg write log does not independently prove GTK
painted a frame. The exact control executable reports
11.1.0/v11.1.0-12130-ge470268ff4; the corresponding short-revision raw GitHub
URL returned 404. Upstream source is a reference, not verified source for
that Windows executable.

The control's later black frames have a direct guest-side explanation:
display-off at 2677.178789, followed by no captured display-on.
Patch 0079 makes AppleCLCD fade/zero the framebuffer and suppress presentation
while off. Black memory snapshots therefore do not require a GTK failure.

`sweet_fb_swaps_logged` caps swap diagnostic output at 16 records; msgbuf is
also circular. The last captured swap log at859.414372 is not a reliable
timestamp for the final actual framebuffer update. GTK's missing theme SVG
warning is present in runner-console.log, but no evidence links it to lost
guest pixels.

## Concrete input defect in the host helper

`tools/qemu-sweet.py:qmp_wake_tap` sends x,y,button-down,button-up in one
input-send-event request. `research/vm/control-3000-monitor.py` uses this
same helper for Settings taps, and the runner uses it for scheduled wakes.

Upstream [QEMU input handling](https://github.com/qemu/qemu/blob/master/ui/input.c)
sends the complete event list then calls qemu_input_event_sync once.
The [virtio input handler](https://github.com/qemu/qemu/blob/master/hw/input/virtio-input-hid.c)
turns that sync into EV_SYN/SYN_REPORT. In SWEET's 0082 input driver,
EV_KEY only updates pressed; EV_SYN compares pressed with touching and
then calls sweet_hid_touch. For an initially released finger:

```text
ABS_X, ABS_Y, DOWN, UP, SYN -> pressed=false, touching=false -> no touch
ABS_X, ABS_Y, DOWN, SYN; UP, SYN -> down then up
```

An offline replay using the actual helper event list reproduced exactly
these state transitions: zero touch events for the current batch and two
edges for separate batches. No socket, VM or guest code was executed.
This is a concrete protocol mismatch against the inspected QEMU source and
guest driver, with the exact Windows QEMU revision caveat noted above.

SweetHID logs contact-state changes (`was != down`), not every movement;
there is no time-based 491-second log cutoff in the inspected path. The 29
early control touch records demonstrate earlier functioning input. Absence
of later logs does not prove the virtio polling thread died: the automatic
tap helper supplies a separate explanation. QMP success means request
acceptance, not delivery of a meaningful touch to iOS.

## Minimal next change and verification design — not implemented

1. Fix only the host tap helper first: send position+down as one request,
   then up as another request, with a short explicit dwell. Ensure release
   is attempted if the second stage fails. Preserve command errors and
   timestamps. Rollback is restoring the helper; no kernel rebuild needed.
2. Add a simultaneous capture mode using a fresh directory: retain physical
   raw bytes and metadata/hash, QMP screendump from the identified RAMFB
   console, and a host GTK screenshot with window/console identity. Let
   RAMFB refresh complete before judging a frozen guest's screenshot;
   pausing can otherwise introduce a stale host frame.
3. Interpret comparisons: raw UI but screendump differs -> inspect RAMFB
   configuration/console/update; raw and screendump agree but GTK differs
   -> inspect GTK console selection/scaling/paint; all show logo/black ->
   investigate guest initialization/power state first.
4. On a separately authorized bounded run, verify an early down/up pair
   appears in SweetHID, then repeat after 491 seconds and after display-off.
   Require a visible wake and navigation in GTK, not just a QMP success.
   Use the same kernel and disposable storage. A persistent disposable
   image may avoid repeated cold LaunchServices rebuilds, but is a separate
   experiment and is not created by this audit.

The offline evidence establishes historical UI in guest memory and an
actionable host-input defect. It does not establish a RAMFB/GTK root cause
or prove that fixing input alone makes SpringBoard boot quickly/stably.

## Workspace review

Reviewed git status/diff, current NOTES and HACKIOS_20H392_PORT, the full
runner diff, new p0-preflight.py/test-qemu-manifest.py, and the control
monitor/analysis artifacts. The tracked diff is primarily manifest/lifecycle
recording, boot-argument factoring and documentation; no tracked kernel
patch is modified. No staged changes were present. The single-packet tap
helper predates those manifest changes; it is not attributed to DeepSeek.
Untracked github-clone and all pre-existing edits remain intact. Attribution
of every ignored research file to an individual agent is not recoverable
from git alone.
