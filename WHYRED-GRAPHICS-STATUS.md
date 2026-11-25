# whyred graphics: measured boundary and next experiment

Updated2026-11-04 Minsk. Phone DISCONNECTED by user; offline work only.
Installed boot98/System95, iOS20F66. In fresh
ordinary-reboot run98b, exact kernel UUID and helper uploads/readbacks passed.
The user watched the repeated real-frame test and explicitly confirmed a white
Apple logo on black on the phone. Capture-to-panel delivery therefore has a
physical visible result. A functioning SpringBoard interface is still pending.

In later98b, lsd reached its ordinary event loop and SpringBoard advanced from
store acquisition to an IconServices request for application icon images. This
is startup progress, not a proved permanent deadlock or a ready interface.
Fresh98c separately showed the earlier CoreServices wait. Its retained SSH shell
must not be reused after disconnect/storage fallback; startup monitoring stopped.
The earlier guarded identity-cache experiment failed its actual answer probe
and was rolled back byte-for-byte. It was not repeated in98b.

Both98b and98c later hit CMD17 incomplete with a full512-byte FIFO and the clean
second CMD13 check from0175, then restored the slow baseline clock. SSH stalled.
This physically exercises0175 but does not prove the late-ready hypothesis or
constitute a kernel panic. Boot99 adds one bounded final data-ready recheck;
full CI/4826 host checks/package verification passed, but it is NOT flashed.

Latest98c screen retry: the new explicit `whyred-display-wake panel-on` passed
exact v98 UUID/display-ID/logical-dimension checks, requested our AppleCLCD
selector12(1), and produced a new `display on` record. Fresh capture reached the
panel through84 successful submissions before the30s child deadline. The user
confirmed the Apple logo on black during this exact retry. This verifies the
direct panel wake and visible real-frame path; it does not establish stock UI.

Offline automatic-output candidate: `live` captures a fresh real LCD scene into
new immutable IOSurface storage for each submission, at most once per second.
Its actual speed, changing-scene delivery and memory lifetime still need a finite
device pilot. `prepare-whyred-display-image.py` prepares a System95 descendant
with a supervised mobile launchd job, retaining all531 existing jobs and SSH.
The completed System100 image passed independent comparison of8614114504 old
logical bytes, with exactly3 additions and1 separately checked cache change.
Private manifest/offline-readiness receipts retain the image SHA. The process
log is bounded to1MiB. No automatic panel power override is added.
No continuous job has been installed or tested on the phone. Candidate preparation
is useful offline; flashing that enabled image requires the exact-binary pilot.

## Actual physical results

| Path | Observed result | What it establishes |
| --- | --- | --- |
| CALayer into CPU bitmap | Exact 192 red / 64 green pixels | Simple CPU layer drawing works. |
| Same tree into own IOSurface | Pixels survive unlock/relock | Own CPU surface mapping works. |
| Two-process IOSurface IPC | All 512 shared bytes pass in both directions | Tested cross-process surface delivery works on whyred. |
| EAGL API 2 and 3 | Neither context created | No demonstrated GL renderer. |
| CoreImage software option | NULL indirect callback, also seen in mediaserverd | This particular fallback is unusable. |
| Entitled named LCD marker | Exactly 1,024 red marker pixels reach capture | Server CPU composition and remote context routing work for this test. |
| Entitled LCD PNG capture | White Apple boot logo on black, 1125 by 2436 | The server has a real boot scene. This is not a working SpringBoard interface. |
| Stock framebuffer swaps | Surface 3 contains zero RGB and alpha and is copied to the panel | Captured server scene and stock scanout contents differ. |
| Earlier97d one-frame presentation | Source/panel nonempty; user later reported backlit black | Submission and memory content did not establish visible output. |
| Earlier98a repeated real-frame presentation | 101/101 successful queues; source RGB25,430, panel RGB21,674; 2,332,800 pixels copied | User missed this window; no visible result for98a. |
| Fresh98b repeat watched by user | Same real logo captured and copied;99 successful queues before30s child deadline | User explicitly confirms Apple logo on black: this capture-to-panel path produces a visible image. |
| Fresh98c direct panel-on and real-frame repeat | Exact guarded driver power request, new display-on record,84 successful queues before child deadline | User confirms logo; direct panel wake and captured-frame display work in this run. |

Earlier captures and marker tests lacked the QuartzCore displayable-context and
global-capture entitlements. Their transparent results were superseded by the
entitled test; they do not establish a broken or empty compositor. The temporary
marker was invalidated. No invented GPU capabilities or fake interface were added.

The named LCD marker changed RGB pixel count from 25,430 to 26,454, including
all 1,024 marker pixels. The successful PNG is a private audit artifact and is
not committed. Stock panel source measurements were zero, while a later panel
measurement also contained console text. No exact timestamp correlation between
every user-observed black clear and those swaps has been established.

## Current finite presentation experiment

`whyred-render-probe present-once` captures the actual LCD scene into its own
IOSurface and submits it once through our existing AppleCLCD user client. It
checks the exact installed v97/v98 kernel UUID, display ID 0 and logical size
1125 by 2436 before calling the custom swap selectors. The driver retains the
queued surface. It changes neither daemon configuration nor renderer flags.

The optional `present-window` repeats the same captured frame101 times at
100ms intervals, then exits. It changes neither compositor settings nor daemon
configuration. Earlier98a completed all101 submissions with exit0; user missed
that window. In98b, CPU contention extended the test to its30s child deadline:
99 successful submissions were recorded before SIGTERM/exit124. During this
exact repeat the user confirmed the visible logo. Do not report101 completions
or exit0 for98b, or reinterpret that deadline as a failure to display the image.

These are finite tests of capture-to-panel delivery, not a continuous
rendering solution. A successful submission alone does not establish visible
panel output or a repaired interface. In fresh run 97d the driver measured the
expected source contents and copied the frame, and the panel measurement became
nonempty. Console writes raced with that measurement. The user later reported a black screen with backlight. Subsequent stock blank
swaps and display-off/on were also recorded, so that delayed report does not
uniquely establish a scanout failure. No repaired SpringBoard interface is claimed.

The initial iOS build failed because `mach_task_self` depended on a transitive
header available only in the desktop build. An explicit Mach header fixes it.
Source `b03952a947f529f7f0b009535e221d2efdf76b47` passed every step of CI
[41653213351](https://github.com/timosid/ios-sweetwhyred/actions/runs/41653213351).
Artifact digest, length, ZIP CRC, report source, binary digest, iOS platform,
ISA, strict signature and the exact two-entitlement set were checked locally.
The signed binary is 93,760 bytes, SHA256
`9b0a77d5394de0987aa0313ee3a0d63578b9d1318ebd37e4f00aec4640fb7091`.
Physical helper execution completed in run 97d: exit 0, surface 5, swap 5, expected source
RGB count and full-panel copy. This is a one-frame result.

## SpringBoard startup is a separate remaining blocker

The preserved 97c main-thread sample waits through CoreServices while
ControlCenterServices resolves `initWithBundleIdentifier:allowPlaceholder:error:`.
Another thread makes a synchronous NSXPC request with the exact selector
`getServerStoreBlockingWithCompletionHandler:`. The main thread waits on the
corresponding CoreServices store lock. These selectors were decoded from the
exact cache stubs, not inferred from a distant nearest exported symbol.

This identifies a LaunchServices database-store acquisition wait. It does not
yet identify why the server has not supplied that store, prove a permanent
seeding loop, or establish a new lsd crash. Fresh lsd/SpringBoard samples reproduced the store wait. lsd subsequently
advanced from a UserManagement query to a MobileGestalt hardware lookup, so the
samples do not establish a permanent IPC deadlock.

## Earlier97 read-only server inspection

Determine the task's actual cache identity and slide before interpreting a
read. All addresses below are canonical addresses in the preserved 20F66 cache,
not live addresses or instructions to write memory.

In physical run 97c, the actual LCD had two render clients, nonzero root layer
IDs/cached roots and a constructed CPU renderer. Its concrete server vtable was
`0x1d5b45c68`; render-to-target first attempts GPU setup and has a verified CPU
fallback. Thus an empty LCD list is ruled out for that snapshot.

The capture request 40221 reaches display-server event 20 and a renderer with
vtable `0x1d5b3d618`, allocation `0x4fe0`. Capture acceptance alone is insufficient:
the event marks the request handled before checking render-client count, and a
zero-client path can return without drawing. The entitled pixel result, rather
than API acceptance alone, establishes drawing in the successful physical test.

Display inventory entries visited by `_detectDisplays` are display types, not
three established rendering engines. The factory's LCD/TVOut choice uses type
bit 8 at display `+0x9f2`; this is not a software-renderer switch.
`beginExternalUpdate:usingSoftwareRenderer:` changes bit `0x80` at display
`+0x251` through the concrete external-update method. That fact does not by
itself establish a persistent software-compositor configuration.

Stock backboardd initially passes true for
`kCAWindowServerDisableUpdatesOnMainDisplay`, then sets renderer flags to 3.
Overlay handling later enables and disables updates. The actual getter tests bit 8 of the 16-bit field at display `+0x251`. In run
97d all four display gates were false; LCD flags were `0x12ec`, with the separate
software-capture bit `0x80` set. A forgotten update-disable gate does not explain
the blank stock swaps in this snapshot. No gate was changed.

## Earlier MobileGestalt sample

The saved lsd return chain identifies an IONetworkController match whose
callback accepts `sdio`, `wlan` or `marconi-wifi`. That caller supplies a five
second run-loop timeout. The outer semaphore wait synchronizes the worker; it
is not evidence of an infinite query. The missing ADT product/options nodes
were not the target of that sampled match. Do not fabricate a Wi-Fi or Apple GPU
service to satisfy this observation.

Private task snapshots, disassembly, PNGs, logs, keys and downloaded Apple bytes
remain outside Git. Exact source/CI/artifact history is retained in NOTES.md.

## Identity dependency and rejected cache experiment

Read-only lsd stack constants identify `UniqueDeviceID` / `UniqueDeviceIDData`
calling through `WifiAddress` / `WifiAddressData`. Each obfuscated key was
matched against its exact MD5-derived key. In the earlier97d run, the volatile MobileGestalt cache
existed with version20F66 and33 extra answers, but none of these four keys.
The port has no functioning Wi-Fi driver. Repeated hardware-query waits are a
concrete dependency to investigate; they have not yet been proved to be the only
reason the store has not been supplied.

Queue diagnostics found 120 queued messages among 512 of launchd's 514 receive
rights, and 36 in lsd. They were not the reply port on which SpringBoard was
waiting: its actual mach_msg2 receive name was `0x4303`, whose queue was empty.
The earlier queued-reply hypothesis was rejected. Counts alone must not be called
a lost-wakeup bug or a broken IPC implementation.

`whyred-gestalt-cache` is an explicit, reversible RAMFS experiment. It requires
root, the exact v97 kernel UUID, the fixed existing cache on `whyredramfs`, a
single-link regular file, version 20F66 and the current SHA256 supplied by the
caller. It adds only two development-identity answers derived from the existing
IOPlatformUUID. It creates an original backup, replaces atomically and restores
ownership and permissions. Probe verifies the actual MobileGestalt answers
without printing identity values. Rollback restores the original bytes. No Wi-Fi
service or physical network address is invented, and no persistent partition is
written. A successful probe is required before restarting lsd.

The final candidate source `b242eb47248d501fde328370c226dc1858f8a38e` passed CI
[41660019245](https://github.com/timosid/ios-sweetwhyred/actions/runs/41660019245).
The signed binary is 90,512 bytes, SHA256
`3356f566f223beca159668fbe2f216c4eeefb2f80a1d1f52ae22daacefc95119`.
Provenance, archive integrity, iOS platform, ISA and exact signature rights were
verified. The final candidate was uploaded and read back in97e, but the fixed
existing-cache guard could not be satisfied because the path was absent. No
cache write or lsd restart occurred. Fresh SpringBoard independently reached its
main event loop; do not assume the earlier sampled store wait persists.

## Late storage failure can invalidate graphics observations

After the earlier clean checkpoint,97d failed eMMC recovery on single-block
CMD17 reads. Both recovery attempts saw failed CMD12 and status00400900. APFS
then reported EIO and many tasks received SIGBUS. This is a demonstrated storage
blocker, not proof that all earlier blank frames have the same cause. Candidate
0175 requires a clean second card status and a fresh reread. Full CI and source/
artifact/linked-code checks passed; boot98 is installed. No physical recovery
has yet occurred in the observed98 run, so this branch remains unexercised.

## Fresh97e display power boundary

SpringBoard26 main now runs CFRunLoop/GSEventRunModal and lsd95 is idle in its
run loop. The LCD has six render clients and a CPU renderer. Both mobile and
root captures have zero RGB with full alpha while the last display state is OFF.
The actual button driver is wired through SWEET/UFS initialization and does not
start on the whyred eMMC path; the user's power press produces no logged key.
A guarded one-shot SBSUndimScreen request returns status0 but neither produces
a display-on record nor changes the capture. Separate BackBoard unblank testing
is pending. These results do not establish visible UI or a scanout fix.

## Actual HID wake and next boot98

A guarded single diagnostic power-key pair, dispatched through the existing
HID buttons service, produced `display on` and renewed framebuffer swaps. The
user still saw console clears and no interface. The following capture died with
SIGBUS after the same fatal eMMC STOP/status recovery failure. No image or
presentation success is claimed from that capture. Physical button polling is
still absent; remote HID input is a diagnostic workaround.

Boot98 with0175 passed full CI and artifact/source/linked-code/boot-layout
verification, was flashed and its actual running UUID was verified. Actual recovery and visible UI remain
unverified. The next fresh run should use the new UUID-guarded helpers and
capture promptly after a single remote wake, while storage remains healthy.

## Actual98 identity-cache outcome

The named cache appeared later in98. A guarded seed added exactly two development
identity answers and preserved all other fields and an exact original backup.
The actual mobile MGCopyAnswer probe returned matches0 after10,121ms. The original
cache was restored and re-read byte-for-byte; no daemon was restarted. Do not
repeat this rejected experiment or infer that arbitrary CacheExtra insertion can
override these runtime hardware questions.

A warm PNG retry succeeded in under a second after the initial30s child timeout;
the image is byte-for-byte the earlier white Apple logo. SpringBoard26 still has
five sampled threads, main on the CoreServices store lock, while lsd95 is in a
MobileGestalt query. This identifies a remaining dependency, not its final fix.
