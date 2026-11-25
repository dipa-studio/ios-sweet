## Active103/UI: REAL LOCK SCREEN OBSERVED;103 boot candidate NOT FLASHED (2026-11-04 Minsk)

- User's latest 'делай' asks to continue UI. Current installed STILL boot99/
  System102. At about39m43s device uptime SpringBoard26 actually built its UI.
  USER then saw lock screen; three photos show wallpaper, camera, home indicator,
  red/orange top banner and incomplete large pale upper rectangle. UI appears
  briefly, then BLACK WITH BACKLIGHT between flashes. Actual photos privately
  retained graphics-v103/user-photos. This supersedes 'only Apple logo' above.
  Full/stable UI and touch still NOT established. Do not reflash without readiness.
- Fresh102 read-only UI sample owner36808 FINISHED; slide4e4b8000, SpringBoard26
  LS store wait and lsd93 MobileGestalt Wi-Fi matching wait at that EARLIER sample.
  UI later progressed without MG cache mutation; do not call the old wait permanent.
- Important new disk bug: d_psize returns sector CAPACITY, while exact XNU8796
  specfs set_blocksize consumes BLOCK BYTES. Persist32MiB gets65536-byte v_specsize
  and spec_read rejects above16KiB. Source0178 now returns512; real specfs/driver
  host harness PASS29 checks+3HFS; unmodified driver NEGATIVE fails512-unit check.
- Experimental local signed iOS helper f6c879b9 attempted bounded read-only
 16KiB persist probe after upload/readback/selftest PASS. VFS explicitly forbids
  user SETBLOCKSIZE: gotEPERM,0bytes. No media writes/no valid factory dump/MAC.
  Helper source cleaned to GET/read-only and locally rebuilt/signed, SHA
  dca4981a92e74c8a65fbc922b8e854b2e5a83af0ca6dd3c2946a7da4995cad6f.
  Final helper is NOT yet uploaded/tested on corrected kernel. NEVER bypass
  VFS policy or use fake MAC.
- Prepared pinned layout-preserving backport builder + source0178. PRIVATE FINAL
  graphics-v103/boot-v103-candidate image22347776B SHA
 69422ec4e548fe51391829559bba76a38024f92a7359f5f8b0c3ad7109fb72c1.
  Kernel SHA7809054ed5e0965d2950086d7dc317b510958bcb7d5995e881b9b02b54545a52.
  Changes ONE instruction atfffffe000795ec3c (csinc->movw0,512), Android header
  ID and append sweetnull=-; all old args/addresses/shim/ADT unchanged. Kernel99
  layout UUID intentionally PRESERVED for installed102 display ABI; this IS a
  modified kernel identified by SHA, not an unchanged99/full newCI build.
  Earlier geometry-only ab6fac candidate moved to DO-NOT-FLASH directory.
- sweetnull default tees backboardd/SpringBoard /dev/null writes synchronously
  to UART. Current UI produced a flood of AppleM2ScalerCSCDriver matching errors.
  New sweetnull=- disables that DEBUG TEE, preserving kernel USB/panic logs.
  CPU starvation/frame overwrite explanations remain hypotheses, not proven fixes.
- Held31558 currently NOT FREE: lockscreen snapshot owner40440 exited after
 110s timeout reading display log. First ps completed (SpringBoard26,lsd93,
  backboard55,display114 alive). Held log57BEGIN/56END, pending CAT since17:28:09Z;
  do not queue commands. Its planned invalid 'hid' mode was NEVER reached, so no
  HID event sent. Correct mode is power-key; prefer non-toggle wake if state unknown.
- Separate single wake attempt41268 via new SSH ended255 BANNER TIMEOUT; no
  request delivery proven. Current receiver9727 still logs. Last observed eMMC
  errors/fallbacks0; searchd235 SIGABRT seen later; no kernel panic. New GUI
  screenshot cannot yet be read because SSH is stalled. No manual presenter added.
- Candidate independent byte/opcode/ID checks,4 packaging refusal tests,
  GET/read-only helper native tests and files-only guard now PASS;
  guard rejects flash without readiness. PRIVATE tools/flash_kernel103.py sealed
  to69422ec4 image. See WHYRED-BOOT103.md for exact scope and limits. Retain
  full99 rollback and System102. Preserve evidence; user has NOT approved103
  flash/readiness yet. After concrete reviewable103 ready, request Fastboot for
  BOOT-ONLY test; then prepared ssh-v90/check_boot103.py --start verifies
  authoritative103 flash + ABI and exports bounded private factory data via
  GET/read-only helper (selftest/probe/full32MiB, no SET ioctl), fresh held only.
  Then parse REAL metadata and check
  quiet logging/GUI stability. Boot103 alone does not promise complete UI fix.

## Active102: INSTALLED + LIVE PROFILE/DISPLAY PASS (2026-11-04 Minsk)

- Completed latest startup-optimization request: installed boot99/System102,
  all81System writes+reboot independently confirmed. Source implementation
  dd1013a. No boot/GPT/other partition writes. NEVER rerun completed102 installer.
  Image5386178560B SHA6e6851e0f9789de382d38bfa3a113030bfb47b05969ce2ce68397295b958a912.
  Native19-job list, exact offline proofs and scope: WHYRED-BOOT-PROFILE.md.
- Actual102 device readbacks PASS: exact99 UUID, unchanged display27b binary,
  unchanged native128MiB display policy, entire expected launchd cache and ALL19
  native hardware plists. ALL19 selected hardware processes absent in FOUR
  process snapshots; SpringBoard/backboardd/dropbear/display remain present.
  Bluetoothd/FairPlay remain disabled from95. No fake services or deleted binaries.
- Automatic display PID114 UID501 persisted across100/110/120/140 frames,
  errors0 throughout, hashc3d72fb8 (Apple logo). Captures~3.7..8.3s while cold
  IO continued; do not claim1fps. USER physically confirmed automatic102 Apple
  logo on black. No manual presenter/marker. Full SpringBoard UI still UNPROVED;
  no physical touch producer,0177 kernel remains unflashed. No long-run leak proof.
- Currentboot through1133740032 I/O bytes: errors0/fallbacks0, no observed panic,
  CRASH or RAMFS PRESSURE. Ordinary FSERR traces still exist; do NOT claim all
  filesystem/API problems fixed. Source99 single-block PIO remains~1.3MiB/s.
- First successful rootSSH observed533.528s (~8m54s) after explicit reboot result
 16:44:55.396Z. Prior101 host log/login-file mtime proxy727.314s (~12m07s).
  About194s faster in this ONE run; polling/host-mtime proxies and differing
  process-sample boot ages mean no controlled/repeated speedup or RAM-savings proof.
  Private baseline101-host-timing.json +102 runtime-acceptance.json retain limits.
- LIVE held31558: audit/graphics102-device-20261104T164514Z/held. Observer29161,
  validator29546 and installer29160 all FINISHED. Held shell FREE. Never reuse
  obsolete101 held17333. Passive timing observer29277 stopped after acceptance;
  invalid launchd_cache_loader substring marker discarded, no fake PID1 timing.
- UDP listener9727 remains running. audit/current-whyred-usb.log ->
  graphics100-usb-session.log; isolate102 using graphics102-boot-boundary.json.
  ExactUSB en1/192.168.7.1 restored automatically, no OS-admin prompt/UART needed.
  Private flash/transfer/runtime/physical receipts retained; valid101 raw rollback,
 95/100/boot backups/keys unchanged. Complete102 raw+81sparse packets retained.
- Additional render CI41869522922 (dd1013a) finished run=failure, job
 126712462849=cancelled with EMPTY steps/runner_name;16:39:22..16:54:24Z.
  No code/build step ran and no new CI-pass claim; cancellation cause unknown.
  Installed102 reuses prior CI/physically verified27b binary. Actual local
  builder/comparator/fixtures and hardware checks above PASSED.
- NEXT: startup profile work is complete. Continue actual SpringBoard UI beyond
  the boot logo if requested;101's earlier LS/MobileGestalt Wi-Fi wait is only
  a historical snapshot, NOT a new102 diagnosis. Preserve the working102 setup
  and inspect current state via the FREE held shell before changing anything.

## Active102: INSTALLED81/81 + reboot PASS; automatic boot checks running (2026-11-04 Minsk)

- Fresh user Fastboot answer authorized concrete102. Guarded installer29160
  FINISHED all81System writes/rebootOKAY, independently reviewed ALL81 transfer
  results. Private audit/display102-flash.json and transfer-review.json. ONLY
  System written; boot99 retained. Installed now boot99/System102. DO NOT rerun
  installer. Exact102 SHA6e6851e0f9789de382d38bfa3a113030bfb47b05969ce2ce68397295b958a912.
- Before-write graphics102-boot-boundary.json retained; isolate newboot log at
  that offset. UDP listener9727 continues graphics100-usb-session.log via alias
  current-whyred-usb.log. Old101 held17333 is OBSOLETE after reboot.
- SOLE observer29161 waits freshUDP then check_graphics102.py --start; new
  timestamped graphics102-device-* status/held will own new SSH commands.
  SOLE validation follower29546 waits observer's installed cache/19native job/
  absence proofs before automatic frame/memory samples. Do NOT queue parallel
  held commands. Passive log observer29277 records1s host observation times.
- Reboot confirmed2026-11-04T16:44:55Z. No new102 SSH/service/display or speedup
  proof yet. Source implementation/offline checks commitdd1013a. No manual
  renderer; no new kernel. Full SpringBoard UI and physical touch remain unproved.
- NEXT: confirm USB address/fresh logs; follow observer and validator through
  actual102 disabled-process/critical-job/automatic-frame checks. No UART.

## Active102: AUTHORIZED INSTALL RUNNING; do not start another flasher (2026-11-04 Minsk)

- User freshly confirmed Fastboot for concrete System102. Exact private baseline
  device matched. Guarded detached flasher29160 started with --flash --ready-answer;
  audit/display102-flash-process.json and graphics-v102/flash-system102.log.
  It rehashes candidate/rollback/packets before writing ONLYSystem,81packets.
  Boot99 retained. DO NOT start a second installer even before first receipt.
- BEFORE-write graphics102-boot-boundary.json preserved current USB file offset.
  Existing bounded UDP listener9727 retained. Old101 heldSSH17333 OBSOLETE.
  Sole observer29161 waits for confirmed81/reboot/freshUDP before starting
  check_graphics102.py with fresh held shell. Passive host timing observer29277
  writes graphics-v102/boot-log-observations.json (1s host observation resolution).
- Source profile/tests/full-image/sparse/preflight completed in dd1013a; exact
  imageSHA6e6851e0f9789de382d38bfa3a113030bfb47b05969ce2ce68397295b958a912.
  No102 device behavior or startup speedup proved yet. No manual presenter.
- NEXT: confirm ALL81 writes + reboot from receipt, restore exact USB address
  only if necessary, follow sole102 observer, then automatic display/service
  checks. Never queue a command into any held shell while its owner runs.

## Active102: READY hardware-profile candidate; fresh Fastboot answer pending;101 installed (2026-11-04 Minsk)

- Latest user requested startup optimization by disabling unused Wi-Fi/Bluetooth/
  camera/NFC services. Implemented explicit19-job minimal-hardware profile in
  tools/whyred_boot_profile.py, integrated opt-in System102 builder/comparator.
  Changes ONLY Disabled=true in BOTH native plist and embedded cache; preserves
  all532 jobs, other fields, working101 display client/native128MiB budget,
  SSH/USB/UI/API/security/logging providers. No fake processes/IPC. Default100/
 101 behavior unchanged. Exact list and acceptance: WHYRED-BOOT-PROFILE.md.
- Actual101 snapshot found active radio coexistence, bluetoothuserd,nfcd,
  wifianalyticsd,awdd; camera and several Wi-Fi jobs were dormant. CPU profiler
  FAILED BEFORE first CPU result (threads40 command timeout). Do not claim CPU
  savings or measured startup gain. Single-block boot99 PIO~1.3MiB/s remains a
  separate bottleneck. Physical Apple logo confirmation for101 now recorded.
- IMPORTANT: held17333 still has outstanding framed BEGIN67d2c2309faca3ddf2b3541bb85b6979
  and NO END. Do NOT queue more commands. profiler23067 EXITED; private status
  boot-service-profile.json=failed-review-required. No phone configuration changed.
  Last read-only UI snapshots: SpringBoard waits LaunchServices store, lsd worker
  waits inside MobileGestalt's Wi-Fi lookup. Not proof of permanent deadlock.
  chosen lacks mac-address-wifi0. Factory persist cat attempt returnedEINVAL/
  zero bytes, no writes; empty dump is INVALID. No fake identity/cache seed added.
- Local4 profile tests PASS incl7 refusal cases and exactC/Python path parity;
  strict C compilation PASS;6 hardware comparator positive/negative cases +9
  retained display/budget fixtures PASS. Actual full-source overlay previewPASS.
- FULL102 IMAGE PASS: graphics-v102/system-v102-candidate,5386178560B,
  SHA6e6851e0f9789de382d38bfa3a113030bfb47b05969ce2ce68397295b958a912.
  Independent95 comparison63022nodes/45744files/16607dirs/671symlinks,
 8613999393 unchanged old bytes;3additions/21explicit exceptions. All24 overlay
  byte/metadata checksPASS. Actual101->102 cache comparison:19Disabled fields,
 513otherjobs equal. ALL81 sparse packets and exact payload
  reconstruction PASS. build-status.json=offline-ready. See finish.log and
  system-v102-candidate/offline-readiness.json. Private flash_display102.py is
  sealed to exact102 SHA/size, rejects --flash without fresh readiness; file-only
  preflight28531 FINISHED exit0 (files-preflight-status.json/log), no device
  writes. Fastboot scan0devices. Concrete102 installation readiness PENDING.
  Initial foreground build disappeared without manifest; incomplete spool was
  discarded, plan/log retained under interrupted-do-not-flash. Detached build
 26521 now owns the successful complete pipeline. No duplicate build started.
  Installed phone remains boot99/System101. NO102 flash/physical test/readiness.
  Reclaimed ONLY81 reproducible101 sparse transport packets after rehashing
  raw101+allpackets and validating confirmed81/reboot receipt. Valid raw101,
 95/100/boot backups/keys retained. Private audit/display102-space-reclaimed.json.
- NEXT: obtain fresh Fastboot readiness for the concrete102 System-only test. Prepared ssh-v90/check_graphics102.py authenticates
  actual99 UUID/binary/budget/cache/19native files and absence of19processes;
  checks essential UI/SSH/display presence. No manual renderer; no kernel build.
  Isolate new boot log with a fresh graphics102-boot-boundary.json BEFORE flash;
  use fresh held shell only. Preserve101 rollback; never rerun101 flasher.

## Active101: AUTOMATIC FRAME OUTPUT + SCENE CHANGE PASS (2026-11-04 Minsk)

- Installed boot99/System101, all81 writes+reboot confirmed earlier. Exact99 UUID,
  installed27b executable and native128MiB D22 table readback PASS. Current held
  SSH17333: audit/graphics101-device-20261104T153514Z/held. Observer13898,
  validator14610 and scene exec85413 all FINISHED. Later CPU profiler timed
  out after framed BEGIN of diag threads40: held shell is NOT FREE; see top.
- Actual automatic launchd process119 UID501, no manual presenter started.
  Four samples across120s: frames20/30/40/60, errors0/0/0/0, samePID. Wired pages
 12456/13353/13994/14253, compressor0 while cold boot kept loading; this is NOT
  a long-run leak proof. Capture samples~2..8.4s during heavy single-block PIO;
  do not claim1fps achieved. Early attempts exited after3 capture errors before
  display server readiness; launchd retried and final instance stayed alive.
- Stronger actual AUTO scene proof: exact previously signed marker a1279cc5
  uploaded/readback. Created a temporary named-LCD red layer for10s, no manual
  presentation loop. Marker capture0->1024pixels, normalchildexit0/timeout0,
  context INVALIDATED. Automatic process119 stayed unchanged, its journal
  frames130->160/errors0/changes0->2 and logo hashc3d72fb8 restored. Thus current
  autostart captures real scene changes. Private autostart-scene.json/acceptance.json.
- USER physically confirmed automatic101 Apple logo on black background.
  Private acceptance.json and physical-observation.json record this. This
  confirms panel output; ready SpringBoard UI remains UNPROVED. No marker
  remains running. Later warm samples through650 frames retained0errors.
- Current detached UDP listener9727, log audit/current-whyred-usb.log ->
  graphics100-usb-session.log. Isolate101 with graphics101-boot-boundary.json.
  No observed fresh storage failure/fallback/panic. No UART required.
- The optional runtime-budget diagnostic experiment was NEVER deployed/used;
  its queued CI runs were cancelled before steps. Restored tools/whyreddiag.c
  and its workflow EXACTLY to previously verified65bb011 baseline. Direct
  Jetsam ips established the cause; final fix uses native per-job policy only.
- Technical automatic-output milestone PASS. NEXT: incorporate user's physical
 101 screen answer when provided, then diagnose actual SpringBoard startup/UI
  and finish real touch bus work separately. Do not reflash a working101 or run
  another live presenter merely to keep output going. Physical input producer
  remains absent;0177 touch kernel still unflashed.

## Active101: INSTALLED81/81; automatic boot validation running (2026-11-04 Minsk)

- User freshly confirmed Fastboot. Exact file/sparse reconstruction, rollback95+
 100/boot99, private device identity/geometry PASS. ALL81 confirmed System writes
  and reboot OKAY. ONLYSystem written; installed phone nowboot99/System101.
  SHAac49c87fb422b11cc9fc03f201db2c80eb457f91efad6a04e65a16743f392ff1,
  5386182656B. PRIVATE audit/display101-flash.json and transfer-review.json.
  DO NOT rerun installer. Installer13830 finished; oldSSH7448 obsolete.
- Fresh USB/en1 address restored and new UDP confirmed. Same detached listener
 9727 and audit/current-whyred-usb.log -> graphics100-usb-session.log retained;
  isolate101 via audit/graphics101-boot-boundary.json BEFORE-write offset.
- SOLE observer13898 now check_graphics101.py --start; fresh timestamped
  audit/graphics101-device-* status/held. Waiting for SSH, then actual99 UUID,
  exact installed27b binary and D22 budget-file readbacks. No manual renderer.
- SOLE validation follower14610 waits until observer releases new held shell,
  then runs verify_graphics101_autostart.py. It checks singlemobilePID501,
  counter progress/0errors over40s, memory and only fresh101 storage records.
  See audit/graphics101-validation.stdout and newdevice/autostart-check.json.
  Do NOT issue another held command while either observer or validator runs.
- All offline101 proofs/current failure cause below remain valid. Budget128MiB
  is INSTALLED but actual automatic frames/visible result/long-run behavior
  still PENDING. No user panel observation for101 yet. Optional C diagnostic
  CI41854513477/41855581854 CANCELLED before build; unchanged27b used instead.
- NEXT: follow new101 status/validation, inspect increasing clean automatic
  counters, request physical panel observation only after actual frames/power
  state are known. No UART; no0177 touch kernel/I2C producer; UI still unproved.

## LIVE101 INSTALL IN PROGRESS; DO NOT START ANOTHER FLASHER (2026-11-04 Minsk)

- User freshly answered Already in Fastboot for the concrete System101/System-only
  test. Detached guarded installer13830 now running, graphics-v101/flash-system101.log;
  audit/display101-flash-process.json. It first rehashes allfiles, then verifies
  private device identity/geometry, writes81 packets, reboots only afterALL81.
  No duplicate invocation, even before audit/display101-flash.json first appears.
- Current100 heldSSH7448 is OBSOLETE after user's Fastboot transition. Boundary
  audit/graphics101-boot-boundary.json saved BEFORE install. Listener9727 stays
  bound/appending graphics100-usb-session.log; current alias unchanged.
- Sole detached observer wrapper13898 waits for confirmedALL81/reboot and new
  UDP bytes, then execs check_graphics101.py/new timestamped held shell. See
  audit/graphics101-observer-process.json/.stdout. Never start a second observer.
- Optional new diagnostic CI41854513477 and41855581854 were CANCELLED before
  any steps. No iOS compile/pass claim for that helper. This does not change
 101 image proof: it retains the old full-CI/physically-tested27b binary; native
  builder/policy/comparator/full-image checks above passed independently.
- NEXT: follow installer record; on full success await new observer and run only
  prepared read-only automatic progression check. On any error inspect exact
  attempted/confirmed packet counts; NEVER blindly retry or claim full install.

## Active101: complete verified candidate; fresh Fastboot answer PENDING (2026-11-04 Minsk)

- Installed phone STILL boot99/System100, iOS running with held SSH7448;101 NOT
  flashed. User last confirmed TEXT. Actual JetsamEvent ips read over SSH proves
  whyred-display per-process-limit, rpages719/page16384 (~11.2MiB); configured
  exact limit is NOT included. PRIVATE100-device/display-jetsam-evidence.json.
  This direct OS report replaces waiting for the optional new diagnostic merely
  to establish the failure cause. No runtime memory-budget mutation performed.
- System101 FULL IMAGE VERIFIED, PRIVATE graphics-v101/system-v101-candidate:
  5386182656B SHAac49c87fb422b11cc9fc03f201db2c80eb457f91efad6a04e65a16743f392ff1.
  Exact same signed/live-tested27b binary and launchd job as100; only add own
  org.whyred.display Active/InactiveHardMemoryLimit128 in native D22 table.
  All530 old overrides/other policy fields preserved; cache byte-equivalent100.
  Independent full comparison8614013385 old bytes,63022nodes/45744files/
  16607dirs/671symlinks;3added/2explicitexceptions;5 exact byte+metadata checks
  PASS. Finite128MiB budget is a hardware candidate, NOT proved working yet.
- ALL81 private sparse slices generated and files-only guarded preflight EXIT0:
  raw/sparse exact reconstruction, rollback95+100, boot99, binary pilot proofs
  PASS. audit/display101-files-verified.json. tools/flash_display101.py sealed
  to exact101 SHA/size; refuses any preexisting101 flash record. Do not use100
  flasher again. Its reproducible slices were reclaimed AFTER full100 success.
- Disk headroom restored by discarding only agent-generated explicitly
  DO-NOT-FLASH interrupted92 raw/spool and reproducible100 sparse packets.
  Retained valid92/95/100 raw images, keys/backups/receipts unchanged. Private
  audit/display101-reclaimed-* receipts. Current101 raw/slices remain private.
- No new C helper delivered: diagnostic CI41854513477 Intel and41855581854 ARM
  remain QUEUED; neither failed nor passed. Builder/native/comparator/full-image
  tests above are actual local proofs. New helper is not needed for101 image,
  which keeps previously authenticated27b signed executable unchanged.
- Prepared101 observer/check_graphics101.py validates new flash81/reboot,
  exact99 UUID and both installed live binary/native memory-policy readbacks;
  verify_graphics101_autostart.py checks single UID501 process, increasing
  automatic frame counter/0errors, VM snapshots and only fresh boot storage log.
  Neither started. Current listener9727 appends graphics100-usb-session.log;
  current-whyred-usb.log alias correct. Preserve boundary BEFORE101 flash/reboot.
- Asked fresh physical readiness for SYSTEM101 after concrete preflight PASS:
  user must put currently-running phone in Fastboot. Await actual answer; no
  timeout implies approval. Once ready, guarded101 flasher --flash --ready-answer,
  confirmALL81/reboot, new held SSH only, check autostart WITHOUT manual renderer.
  No UART; no real touch producer; full SpringBoard UI still unverified.

## Active100 memory correction: native policy proof; signed helper queued (2026-11-04 Minsk)

- Actual held SSH7448 remains accessible. Current display log: repeated begin,
  no first frame, SIGKILL reason1/7 per-process memory limit; not a working job.
- Old foreground receiver2635 ended between turns without final status. Confirmed
  no listener, started detached bounded append receiver9727; same graphics100
  log/alias preserved. Gap approximately15:02:52..15:08:34 UTC, so no claim of
  uninterrupted coverage. New datagrams verified; no UART. Current storage has
  no failures/fallbacks in observed records through>1.5GB.
- Diagnostic source a3dd836 CI41854513477/job126659373169 remains QUEUED in Intel
  pool. Native strict compile/retainedselftest/11 refusals PASS. Retrying through
  generic ARM64-host macos15 runner; target remains genericARM64/iOS16.4, same
  actual source logic and signed rights. No budget mutation yet.
- Verified exact launchd binary selects com.apple.jetsamproperties.D22.plist;
  Daemon/Override holds530 entries. Added opt-in101 builder --display-memory-mb
  128: add only own label with Active/InactiveHardMemoryLimit128. All existing
  dictionary fields deeply preserved, job/live binary/rights unchanged.
  Native full D22 merge/collision/invalid checks PASS. Independent comparator
  strictcompile and4 budget opt-in/path/other-bytes/mode cases +6 retained
  positive/negative fixtures PASS. Private graphics-v101 receipts/preview.
- System101 NOT built/flashed. Need signed diagnostic actual limits/footprint
  and current-process128MiB experiment first; then build101 and full metadata/
  old-bytes comparison. Available disk ~7GiB: do not start full image before
  reclaiming only proven disposable intermediates; keep95/100 raw rollback,
  keys/backups/flash receipts. No physical touch producer yet.

## Active100: autostart memory-limit failure; diagnostic candidate (2026-11-04 Minsk)

- System100 full81-slice install/reboot confirmed, boot99 retained. Fresh observer
  FINISHED; exact99 UUID,3 helpers and installed display readback PASS. Current
  held SSH7448: PRIVATE audit/graphics100-device-20261104T144954Z/held. Only this
  shell is current; old99 held97326 died with Mac reboot. Observer is NOT running.
- Automatic display log contains repeated live-begin records, no first frame.
  UDP confirms whyred-display SIGKILL, OS_REASON_JETSAM1/code7: exact XNU8796
  JETSAM_REASON_MEMORY_PERPROCESSLIMIT. USER sees TEXT. Finite manual pilots
  inherited a different budget; they did not test launchd's own process limit.
  Global VM snapshot free23945/wired12190/compressor0 pages; not system OOM proof.
  No storage errors/fallbacks through998920192 bytes this boot.
- Preparing explicit whyreddiag memlimits PID (read-only) / display-budget PID:
  fixed finite128MiB experimental floor, root+exact99 UUID+mobile/name/installed
  path/starttime checks, preservefatal flags and unlimited/larger limits,
  readback required. Applies only current process, not persistent or a global
  override. Native strict compile/retainedselftest/11 invalid/physical refusals
  PASS; signed iOS CI/artifact/device budget readback still PENDING.
- Actual launchd binary indicates legacy JetsamMemoryLimit is ignored and own
  JetsamProperties job dictionary maps to a no-op. Do not guess a job key or
  disable global jetsam. Inspect actual limits, test addressed runtime floor,
  then choose persistent integration backed by the measured footprint.
- UDP receiver2635/current-whyred-usb.log stays on graphics100-usb-session.log.
  NEXT: obtain signed updated diagnostic, readback/inspect actual display budget,
  apply explicit current-process experiment and verify fresh frames before any
  further flash. No UART needed; physical touch still absent.

## Active100: System installed; first automatic boot verification pending (2026-11-04 Minsk)

- After a Hackintosh crash user returned the phone in Fastboot. Revalidated exact
  System100/raw/sparse reconstruction, System95 rollback, boot99, private device
  identity/product/unlocked/System geometry and matched finite display pilot.
  ALL81 System transfers/writes and reboot are confirmed OKAY; only System was
  written, boot99 retained. PRIVATE audit/display100-flash.json is authoritative;
  never repeat the flasher or overwrite this record without reviewing it.
- Installed System image5386194944B SHA622ca50416c4d296f846cd7d4e754ca2f1d87a8bfe122010fb588ef6eb40e5c8.
  Added mobile launchd whyred-display live job uses the exact tested27b343c3
  signed binary. Automatic startup, whole UI and long-run stability still PENDING.
- Fresh bounded UDP receiver2635 writes audit/graphics100-usb-session.log;
  audit/current-whyred-usb.log now selects that file. Prior97d log retained.
  Mac exact en1 address192.168.7.1 restored from persistent configuration.
  No UART. Boot reached launchd/fsck/mount/data-protection; no storage errors yet.
- Sole observer5105, exec24895, PRIVATE audit/graphics100-device-20261104T144954Z:
  waiting-for-ssh; allows30s handshake/30min boot, will create a NEW held shell,
  require exact99 UUID and installed display readback, then read automatic log.
  Do NOT reuse old held97326 or start another observer/manual display loop.
  First automatic job log: /private/var/mobile/Library/Logs/whyred-display.log.
- Before crash, same live27b binary passed3 finite40s rounds38/39/39 frames,
  0errors, wired15966/16001/16042 pages. Final scene-window39frames/40.16s,
  0errors/2changes; USER explicitly confirmed RED SQUARE. Marker signed CI
  41824794100/job126556665184 passed; temporary marker binarya1279cc5 is separate
  and is NOT installed as the permanent display job. Private99 acceptance/window
  and memory receipts retained. Short pilot is not long-run memory/UI signoff.
- NEXT: wait for this observer, inspect automatic frame progression/process UID,
  memory/storage and panel state. No manual renderer invocation before checking
  autostart. Kernel0177 touch candidate remains unflashed; real I2C input absent.

## Active99: fresh-frame and changing-scene pilots PASS (2026-11-04 Minsk)

- Exact99 UUID verified over new held SSH97326, PRIVATE
  audit/graphics99-device-20261104T113603Z/held. Observer FINISHED, all3 signed
  helper uploads/readbacks PASS. This is the only current held shell; never98.
- First live-window:11 fresh frames/43.45s,0 errors,0 changes,normal exit0,
  parent timeout0. Direct panel-on0/new display-on observed. USER explicitly
  confirms Apple logo on black during this test. Not a ready SpringBoard UI.
- Scene pilot used same permanent-candidate live binary27b343c3e92384be4b7e2c0a50de32d228c1424865a4648e647f5c76eb28e4d1
  concurrently with existing temporary named-LCD marker, each under bounded
  mobile diagnostic runner.22 frames/42.9s,0 errors,2 hash changes; marker
  baseline0/after1024,context invalidated,both exits0. No storage fallback.
  USER saw a brief top-left change/blink but did NOT confirm red color.
  Private scene-pilot.json/visible-observations.json retain actual results.
- Observed rates0.25/0.51fps during cold boot, NOT1fps achieved. First capture
  451.8ms, later2.8-6.8s; boot still performs heavy PIO. No speed or leak claim.
- Stability script now SOLE owner of held97326:3 finite40s rounds with VM samples,
  status stability.json. Do NOT send held commands until finished; on timeout
  inspect framing. No continuous daemon installed or System100 flashed.
- Preparing optional remote-layer-lcd-window marker mode: keep the validated
  temporary marker10s for clearer user observation; old modes unchanged.
  Native strict compile/new physical-target refusal PASS; signed CI pending.
  Permanent System100 candidate and tested live binary remain27b343c3 unchanged.

## Active boot99 first physical test (2026-11-04 Minsk)

- User returned phone in Fastboot. Fresh private identity/productwhyred/unlocked/
  64MiB boot geometry, exact99 image/kernel/flags and verified98 rollback PASS.
  Boot99 send/write/reboot ALL OKAY; ONLY boot written. System95 unchanged.
  Installed boot image now99 (expected UUID2ED4E8A4-6D1C-3C3C-980B-8533C25978D1);
  actual UUID over SSH still pending. No0177 touch kernel or System100 flashed.
- PRIVATE audit/kernel99-flash.json, graphics99-reboot.json boundary and
  audit/graphics99-device-20261104T113603Z/status.json. Observer/check_graphics99.py
  started once (held session not created yet), waiting-for-ssh. Do NOT start a
  second observer or reuse98 shells. observer exec session96666 is running.
- USB enumerated, exact Mac en1/MAC02:00:5e:77:ee:01 auto-restored192.168.7.1.
  Sole logger2488 receives fresh99 output into audit/current-whyred-usb.log.
  Boot passed launchd/keybag/usermanager tasks; early67MB IO has0 errors/fallbacks,
  cmd17 only as intended. This is early boot, not a long-run stability result.
- NEXT: await observer's exact UUID/upload/readback checks and retained new shell;
  run finite pilot_graphics99.py on its status. Require measured frames/memory,
  real scene changes and visible proof before enabling System100 display job.

## Kernel CI network blocker and bounded BearSSL fallback (2026-11-04 Minsk)

- User reported kernel build failure. CI41816371836 attempts1/job126528026791
  and2/job126530569522 BOTH stopped in0020-stage-bearssl.sh before kernel compile:
  bearer upstream https://www.bearssl.org/git/BearSSL returned HTTP502 (git128).
  No touch C++ compiler error was reported by either CI attempt.
- Updated ONLY dependency fetch: at most2 upstream attempts, then2 GitHub mirror
  attempts, keeping exact7bea48e5e850ab4cafbe68d3765cdaba13a86d6f FETCH_HEAD/HEAD
  verification. No branch/version change or skipped staging on failure.
- Local actual staging with injected upstream failure PASSED via status-im mirror;
  all30 staged files are byte-identical to verified baseline. All-remotes-fail
  negative control rejects after4 attempts, creates no staged target. bash -n PASS.
  Private touch-whyred/bearssl-{fallback,reject}-check receipts.
- FIXED full kernel CI41817694238/job126532556668 from source6ebc9fe6ca8228e1649f08159f86f13207b2558c
  ALL steps SUCCESS, including kernel compile/link and new digitizer checks.
  Touch2356 host checks, retained eMMC/APFS/RAMFS/USB/framebuffer/AKS/idle checks
  passed. Authoritative kernel artifact13316395983 ZIP79410894B SHA
  0cc68ef3a4625a09fb68ebe0cd0c97811e51a5b1fc45b67ab1a5007bf4a75829;
  buildtree13316162052 ZIP25440738B SHA
  fa709f740b0eda8d1f869d2ebb6afd0a2e2fb90c54a5c10c3e6c7929be578cdf.
  Artifacts not downloaded/packaged/flashed yet; installed98/System95 unchanged.
  PRIVATE touch-whyred/fixed-final-jobs.json retains step receipts.
- Full CI now supersedes the incomplete local C++ header experiment (its reused
  BSD flags/header subset did not compile). Do not describe that local attempt
  as a pass. No physical I2C input producer or touch hardware test yet.

## Touch requested; offline0177 candidate (2026-11-04 Minsk)

- User asks to implement touchscreen; phone remains disconnected. Installed
  boot98/System95 unchanged; ready boot99/System100 display work retained.
- Registered HID is not hardware input. sweet_touch.c targets the other board's
  GENI/GT9896/FTS and is initialized through sweet UFS, not whyred eMMC. Do not
  enable it on whyred. Xiaomi whyred DTS supports alternative SynapticsDSX0x20
  and Novatek0x62 on i2c_1/GPIO67 IRQ/GPIO66 Novatek reset. Actual IC unknown.
-0177 fixes actual whyred HID geometry2400->2160, full-panel normalization to
  match framebuffer scaling, lower-edge detection and release parent location.
  Adds bounded65-byte/10-contact Novatek frame-to-HID adapter ONLY; no I2C
  producer/power/reset/firmware operations. It does NOT make physical taps work.
- Local2356 strict-warning/UBSan geometry/packet checks PASS; exact patch replay
  against authenticated99 source PASS. CI test integrated; full kernel build
  CI41816371836 started from beadd14e9afdc7c45ab311e3470baff6dcc346d0;
  failed on upstream HTTP502; source6ebc9fe/fullCI41817694238 now passed above.
  See WHYRED-TOUCH.md. Private references/baseline/candidate/checks
  are in touch-whyred; original vendor files and source dumps stay out of git.
- NEXT: identify actual fitted controller and QUP powered handoff when phone is
  available; implement matching board-correct bus transport and Synaptics decoder
  if needed. Verify real taps/drags/multitouch/releases/edges before claiming
  touchscreen readiness. Do not replace verified99 boot with unverified0177.

## Phone disconnected; offline automatic-display integration (2026-11-04 Minsk)

- Final live signed artifact13297982482/run41778268151/job126403582532:
  ZIP122127B/b1d3f181d1eafbd451a5ee405bdc858316ee81845829b102aec0f01bcb033dc6;
  binary94544B/27b343c3e92384be4b7e2c0a50de32d228c1424865a4648e647f5c76eb28e4d1.
  Sourcee1dd981edfe172a7bbca703d523b175bb6c5eea7. Final diagnostic source
  df007761d1f16887ebd9cbfdba4baf006a7819a4 passed ALL CI41778450154/
  job126404186157. ZIP73337B/aab7397a5fdf1c338701760836096cb6bda206c9d2686118a190734d6af8ec86;
  binary73632B/23ec1e2eb0cbe918adef1daa466e6a71b6be4c8eb47b5da90826e1b86c378746.
  All final archive/source/CRC/size/signature/exact-rights/platform2/noLSE proofs
  passed; PRIVATE graphics-v100/provenance.json and diag-provenance.json.
- Independent final comparator passes BOTH compressed/plain positive fixtures
  and5 negative controls (extra/deleted file, old bytes/mode, new mode). It permits
  only UF_COMPRESSED on new files and strict old BSD flags. Private final results
  graphics-v100/comparator-final-tests.json. Own C unit warning-clean -Werror.
- PRIVATE ssh-v90/check_graphics99.py and pilot_graphics99.py prepared/syntax
  checked. Default observer does LOCAL validation only (PASS); --start requires
  completed boot99 flash receipt, creates NEW session and verifies exact UUID
  and upload readbacks. Pilot requires matching receipts; explicit --run only,
  fixed finite40s capture/mobile90s parent, memory before/after and actual counters.
  It never marks deployment ready or changing-scene/visible proof automatically.
- System100 FULL IMAGE VERIFIED, PRIVATE graphics-v100/system-v100-candidate:
  whyred-system-ios165-v100-live-display.apfs,5386194944B, SHA256
  622ca50416c4d296f846cd7d4e754ca2f1d87a8bfe122010fb588ef6eb40e5c8.
  Independent reader compared8614114504 old logical bytes,63022 old nodes,
  45744 old files/16607 directories/671 symlinks; exactly3 additions and1 cache
  content exception. All4 changed/new file byte+mode/UID/GID checks PASS.
  Separate complete-cache comparison preserves every prior field and all531 jobs.
  SSH/keys and disabled Bluetooth/FairPlay are in the unchanged byte-checked set.
  Writer/comparator sources match committed65b1e97fbd6389fbeecf6d675649b8477c9b5555;
  final CI41781693532/job126414466903 ALL steps PASS. Spool removed after success.
  manifest.json/offline-readiness.json: offline_ready=true, deployment_ready=false,
  hardware_verified=false, pilot_required_before_flash=true. Image fits the
  existing System partition. No device access or flash occurred during this work.
- NEXT when user reconnects: ask actual Fastboot readiness only then, flash ONLY
  verified boot99 against existing System95 using private flash_kernel99.py;
  fresh check_graphics99.py --start and exact-binary finite pilot_graphics99.py
  after reviewing the fresh session receipt. Do NOT flash the enabled System100
  until real finite capture, changing-scene/visible delivery and memory checks
  pass. See WHYRED-DISPLAY-AUTOSTART.md. No continuous daemon installed yet.

- User explicitly disconnected the phone and asks for offline work. Do not ask
  Fastboot now or reuse held98c SSH. Installed boot98/System95 unchanged.
- Both matched99 helpers from sourcea330a8b118d389cda7fae1ab93e516cf78567c4e
  passed all CI steps: render41698260722/job126134429664, wake41698260835/
  job126134430599. Artifact digests/CRC/provenance/platform2/signature/rights/
  ISA/99UUID passed locally. Private graphics-v99/live99 and wake99. No device
  live pilot; do not claim automatic rendering fixed from these offline checks.
- Preparing System100 from verified System95: add only live/wake binaries and
  org.whyred.display job, modify only launchd cache; preserve all531 old jobs,
  disabled Bluetooth/FairPlay and SSH/keys. Supervise as mobile,30s restart throttle,
  fresh immutable capture each iteration, max1fps, no permanent power override.
  Process RLIMIT_FSIZE1MiB bounds regular logs. Updated sourcee1dd981 passed
  all renderCI41778268151/job126403582532 steps; signed archive fully verified.
- New tools/prepare-whyred-display-image.py validates old jobs/base/provenance,
  executable rights/ISA/platform, embedded bootstrap path and independent APFS
  file checks. tools/whyred-display-image-compare.c independently compares all
  old bytes/metadata, permits exactly3 additions and1 cache exception. Native
  renderer guard/layer/surface checks PASS; independent reader rejects an
  unchanged95 image as the100 overlay. System100 is now fully verified above;
  installed boot98/System95 remains unchanged. Exact live-binary finite pilot remains
  required BEFORE deploying the enabled automatic launchd image.
- Corrected pilot runner mismatch: general run-mobile remains30s; new explicit
  run-mobile-display accepts ONLY finite live-window, fixed90s bound. Native
  argument/continuous-mode/root refusals PASS. No automatic or device invocation;
  signed diagnostic rebuild and artifact verification now PASS (see above).

## Boot99 packaged and matched tools compiling (2026-11-03 Minsk)

- Full package authentication PASSED, including authoritative run/jobs/digests,
  ZIP CRCs/kernel SHA, all retained source/body/test proofs, exact new0176 source,
  4826 host checks, linked no-LSE/no-PAN, USB cache barriers, masked idle, foreground
  setter, boot-art and payload bounds. Runtime-source delta versus98 is ONLY
  bsd/dev/whyred_emmc_pio_probe.c; framebuffer ABI/boot args unchanged.
- PRIVATE port/out/whyred-ios-root-v99-late-ready-41692808789: image
  e2c8a0066f8b651d79e7d8e158d57a0806a53e16421c4d80c39e8633c05e28ff, 22347776B;
  kernel961ee9a4f92e4fd595c3825ffa470a5efed1604ad7ba819fa6cadff879adfc1c;
  UUID2ED4E8A4-6D1C-3C3C-980B-8533C25978D1. Manifest has bounded FIFO-ready
  recheck flag/max1; payload21537520B. No flash/hardware99 test yet.
- Prepared PRIVATE tools/flash_kernel99.py: exact image/kernel/source/flags,
  verified98 rollback image, installed System95/81-slice proof, private identity,
  whyred/unlocked/64MiB boot guards. Requires fresh physical Fastboot-ready answer.
  NOT run yet. Matched live/wake99 UUID guards native compile/refusal PASS;
  signed builds pending. Finish them and ask Fastboot only when concrete retry
  is ready. User's goal remains automatic fresh-frame output, not just a logo.

## Active98c second storage fallback; boot99 and matching live tools preparing (2026-11-03 Minsk)

- User supplied fresh CMD17 incomplete LBA3068157/int20/present01f80af6/FIFO512.
  Same clean second CMD13 prior00400900 ->00000900/recheck1, followed by baseline
  clock restore. This is NOT kernel panic. Current98c graphics pilot is deferred
  while this read fallback can stall SSH. No99 flash happened; no live daemon
  installed. Last display-off was logged separately, not a proven read-failure cause.
- Automatic new-frame helper source dd7ab3f5130589a0551886a421a99b1f5cadd797
  passed ALL CI41697274483/job126131003017 build/native refusal/signature/audit
  steps. Not uploaded or physically tested yet. Fresh new IOSurface per frame,
  no reused screenshot/unsafe rewrite; live-window40s and explicit live1fps modes.
- Kernel0176 source5b7e210a8c96eceecff8b4b9f95c24ea22d68a73 now passed ALL full
  CI41692808789/job126115470445 steps (incl4826 eMMC checks and all retained
  framebuffer/APFS/RAMFS/USB/AKS/idle checks). Authoritative kernel artifact
  13260537519 ZIP79279001B SHA209d91b3449941b1d0a29f1d16075696691e0a7760382d6eaef3316f667947b7.
  Buildtree13262505066 ZIP25442046B SHA3111327d764921a79a9d9d68148d5f068028f53ed09cd7ba25fc692151141bc9.
  Both downloaded privately to kernel-v99-late-ready/artifact. Kernel ZIP digest/
  CRC passed; embedded UUID2ED4E8A4-6D1C-3C3C-980B-8533C25978D1 and kernel SHA
  961ee9a4f92e4fd595c3825ffa470a5efed1604ad7ba819fa6cadff879adfc1c.
- Added ONLY this exact99 UUID to wake and BOTH present/live guards; API remains
  same ID0/1125x2436. Rebuilt signed matching tools pending. Boot99 packaging
  reuses all98 source/artifact/layout/rollback checks, updates4826 and requires
  new0176 patch/coverage/source match. Not ready for flash until packaging passes.
- NEXT: finish verified boot99 package and matching signed helpers BEFORE asking
  user to enter Fastboot. Only boot flash needed to test new polling logic; keep
  System95. Then fresh99 observer and actual finite live pilot; require measured
  fresh frame changes/performance/memory before persistent automatic integration.

## Active98c automatic CPU display bridge candidate (2026-11-03 Minsk)

- User explicitly asks to FIX display output. Stopped read-only monitor46870 via
  graphics98c-memory-stop; phase stopped verified. Held46379 is now free after
  fresh read-only threads26/95/57 and actual cache-slide38248000. SpringBoard26
  still has5 threads in earlier CoreServices store wait; do NOT reuse late98b
  IconServices progression as if it were current98c. lsd95 has8 sampled threads.
  Private98c-device/output-fix-*-threads-*.stdout and cache snapshot.
- Preparing explicit live-window / live modes in existing entitled render helper.
  Each iteration obtains a NEW real LCD capture in fresh own IOSurface memory,
  queues it once and drops userspace reference. Driver0150 retains pending and
  workloop surface objects; never rewrite a queued surface. Per-frame autorelease
  pool bounds temporary objects. At most1new frame/sec; sparse summaries/hash
  counts; no stored PNG, test content, guessed renderer flags or fake GPU.
- Opaque black captures are valid in LIVE modes; untouched transparent surfaces
  are rejected. Existing finite probes remain strict. Exact97/98 UUID and ABI
  guard remains before live capture/presentation. Signal stop;45s per-capture
  watchdog; stop after3consecutive failures. Finite pilot40s requires3clean frames;
  continuous mode only explicit invocation, no power-state override/autostart yet.
- Native warning-clean compile, physical-target refusals for new/retained modes
  and retained CPU CALayer/IOSurface tests PASS. iOS CI/upload/live performance,
  memory/visible changing-scene proof and persistent integration PENDING. This is
  functional CPU fallback plumbing, not a claim that stock GPU path is repaired.
- Primary next: signed CI artifact verification/readback, finite live pilot via
  current held shell, measure capture latency/surface lifetime and frame changes.
  Only after real pilot success start supervised automatic updates. No extra
  phone reboot or flash requested at this stage. Kernel0176 CI separate/offline.

## Active98c: direct panel-on and visible real logo CONFIRMED (2026-11-03 Minsk)

- Fresh observer44399 finished after64 login attempts (~13min cold startup).
  New retained SSH46379 at PRIVATE audit/graphics98c-device/held. Exact98 UUID,
  diag2a276d3f/window9a1d6053/new wake17f8f28e uploads/readbacks all PASS.
  Installed boot98/System95 unchanged. No flash/UART/new approval required.
- User repeated request to send frame; notified immediately before explicit
  show_graphics98c.py. Actual new guarded panel-on root tool exits0 in1.65s;
  display-ID/dimensions/kernel guards pass; selector12 request0 and NEW
  SWEET FB: display on observed. This IS physical use of tool17f8f28e from
  sourcecf254ab/CI41691099406/job126109597215, not merely a candidate anymore.
- Actual mobile fresh capture accepted1 RGB25430/alpha2332800;84 successful
  queues of surface5. Run-mobile30s child bound then sendsSIGTERM/exit124 at
  30.4s BEFORE all101 queues. Do NOT report101/101 or normal exit. User explicitly
  confirmed “Логотип Apple на чёрном фоне” during this exact98c attempt. Captured
  actual scene -> driver -> visible panel path works. Stock continuous rendering
  and normal SpringBoard UI are STILL NOT established; no stale PNG injection.
  Private audit/graphics98c-show.json and98c-device/requested-*.stdout retain
  exact results. No synthetic HID pair needed for this successful direct request.
- After show, retained shell still answers immediately. VM16KiB free20879,
  active33261/inactive13417/wired12239/compressor0/no swap. Verified actual live
  PIDs SpringBoard26/lsd95/backboard57 (PRIVATE graphics98c-live-pids.json).
- Read-only monitor46870 now SOLE owner of held46379: VM + threads26/95 once/min,
  max30 rounds. Status audit/graphics98c-memory-monitor.json; samples
  graphics98c-memory-samples.log. To use shell create graphics98c-memory-stop
  and wait phase stopped; if timeout/failed, inspect exact framing before reuse.
  No automatic wake/capture/presentation. Passive UDP2488 unchanged.
- Candidate0176/source5b7e210a8c96eceecff8b4b9f95c24ea22d68a73 remains OFFLINE,
  full kernel CI41692808789/job126115470445 currently building. Local4826 checks,
  exact negative control and actual ARM64 compile passed. No99 image/flash or
  hardware-fix claim. Next inspect CI/checks; preserve current98c graphics run.
- PRIMARY requested action is achieved: direct screen-on + new actual captured
  frame shown and confirmed by user. Next UI work: inspect LaunchServices/Icon-
  Services progression on current98c; do not reuse98b37904 or old waiting state.

## Active98c ordinary reboot for requested screen retry; late-ready candidate (2026-11-03 Minsk)

- User CONFIRMED ordinary reboot after98b stall; no flash/UART. Recorded fresh
  audit/graphics98c-reboot.json boundary3617040. Started PRIVATE
  ssh-v90/check_graphics98c.py PID44399, status graphics98c-check.json, outputs
  graphics98c-device. It waits for cold root SSH, NEW held shell, exact98 UUID,
  full uploads/readbacks of diag2a276d3f/window9a1d6053/new wake17f8f28e, then
  stops prepared-shell-retained. No automatic display request yet. USB2488 live.
  Early fresh98c telemetry errors0/XO1/multi0. Installed boot98/System95 unchanged.
- NEXT PRIMARY ACTION: when observer prepared, use NEW held shell only. Notify
  user immediately; run new wake tool panel-on and verify display-on, then mobile
  renderer present-window for actual current scene. If RGB0, no real image can
  be claimed. Request actual user observation. Do NOT reflash merely for this.
- While waiting, investigated98b FIFO512/int20/present01f80af6 read-ready failure.
  This is consistent with descheduling after an empty readiness sample and
  before deadline check; not uniquely proved on hardware. Existing0170 rechecks
  command/DATA_END completion, but CMD17 FIFO-readiness loop lacked that guard.
- Candidate0176 re-samples INT_STATUS/PRESENT_STATE ONCE when FIFO readiness
  wait expires. Only clean freshly ready FIFO proceeds through existing full
  512-byte drain/DATA_END/no-inhibit/empty-FIFO checks. Still-unready or hardware
  error rejects. No wait extension, clock change, fabricated data or media write.
- New deterministic model reenacts ready arriving after empty sample while CPU
  exceeds its deadline; requires full byte-exact sector, guards intact, no CMD12/
  CMD13/recovery. Additional late hardware-error and still-unready cases reject
  without modifying output. Patched actual driver functions PASS4826 checks;
  unmodified98 fails specifically clean late-ready case (negative control direct
  exported-function line verified). Patch applies cleanly to98. Actual full
  driver ARM64 compile with98 generated headers passes; private
  kernel-v99-late-ready/{checks,negative-old,compile.json}. This is a candidate,
  NOT a proven physical cause/fix or an installed kernel. Full CI pending.

## Current98b screen retry blocked by storage; ordinary reboot requested (2026-11-03 Minsk)

- Direct panel-on source cf254ab165f0f3750364facd4494db9bc6ecba1f passed ALL CI
  41691099406/job126109597215 steps. Artifact13257233536 ZIP24542B SHA
  e9f660b954bfcaeae6103332c94fb107b4ed4336aee3d665ca9b0a17eddb5e6d.
  Binary69984B SHA17f8f28e6f9205ec0f480270cc9263d9f823b8a13bb7df5ead5176889637ba20.
  Source/report/archive/platform/ISA/strict signature/exact2HID rights checks PASS.
  Private graphics-v98/panel-on98. Fresh SCP upload and exact full readback PASS
  to /private/var/tmp/whyred-panel-on-17f8f28e. This is NOT device execution proof.
- Attempted direct wake/presentation after user asked. Before direct tool ran,
  retained shell37904 stalled on read-only exact-kernel diagnostic for85s.
  Last token WHYRED_SESSION_5cc88b57f38de68ed6a15b8a8a2c25c4_BEGIN with NO END.
  Parent exited; NO later panel/present command was enqueued on this FIFO.
  Fresh independent SSH with guarded panel-on && present-window failed255 with
  connection timeout before output,0 queues. No confirmed direct wake/new frame.
  Private audit/graphics98b-wake-present.json and requested-*.stdout/.stderr.
- Fresh UDP reveals FIRST physical98b CMD17/PIO incomplete atLBA12620940,
  int20/present01f80af6/fifo200. CMD12 failed int18000; DATA reset completed.
  Recovery attempt1 stop=-1 status0 r1=00000900 prior00400900 recheck1, FIFO0:
  0175 clean-second-status branch IS NOW EXERCISED and accepted the ready card.
  Then WHYRED CLOCK restored baseline was logged. Fresh reread/overall recovery
  completion NOT established; no recovery-failed line or kernel panic observed.
  Root reads/SSH stalled afterwards. Prior “unexercised/no-read-errors” notes are
  historical, no longer current. Exact private graphics98b-first-recovery.log.
- One separate mediaserverd28 SIGSEGV atPC0/lr1deb2c58c occurred before read
  recovery; matches earlier CoreImage NULL-callback class by canonical address
  but needs exact current symbolication for attribution. It restarted. Do not
  call this a kernel panic or attribute it to the later storage failure.
- Old memory/followup monitors are STOPPED/failed; no active FIFO writer now.
  USB receiver2488 continues; log alias unchanged. No successful wake/present
  from this retry, no flash/UART/cache/daemon change, no stale logo injection.
- Asked user for ordinary reboot with USB, NO Fastboot/UART. Pending reply.
  Prepared PRIVATE ssh-v90/check_graphics98c.py (syntax checked, NOT started):
  fresh root SSH/NEW held shell, exact98 UUID, upload/readback diag2a276d3f,
  window renderer9a1d6053 and NEW panel-on wake17f8f28e. It stops at prepared-
  shell-retained without automatic display work. After reboot confirmation:
  create fresh audit/graphics98c-device, new log boundary; start observer and
  wait. NEVER reuse98b held37904 after reboot. Notify user immediately before
  actual panel-on + fresh present; no new permission/flash required.

## Active98b requested screen wake: guarded panel-on candidate (2026-11-03 Minsk)

- Pending prior capture LATER completed END1: accepted1 RGB0/full alpha, no PNG;
  display had gone OFF. Held37904 framing is COMPLETE, no monitor owner now.
  User explicitly asked to turn screen on and submit a frame. Exact98 UUID passes.
- Sent ONE diagnostic power-key pair while last state OFF: helper/child exit0,
  but no ON within8s. Then idempotent BackBoard unblank request exited0, no ON
  within15s. No repeated toggle, frame or visible-image success claimed.
  Private audit/graphics98b-wake-present.json and98b-device/requested-*.stdout.
- Added explicit whyred-display-wake panel-on mode: exact97/98 UUID guard,
  AppleCLCD service, displayID0 and1125x2436 checks BEFORE own driver scalar12(1).
  It changes driver power state only; does not unlock iOS, invent pixels, change
  renderer flags or imply compositor wake. ABI checked against installed patches
  0079 and0150. Native warning-clean compile and4 physical-target refusals plus
  invalid-argument cases PASS. Added new mode to existing CI refusal/provenance
  checks. iOS build/upload/actual panel-on still PENDING. No flash required.
- NEXT: authenticate signed CI artifact, exact upload/readback; exact98 kernel,
  panel-on once, require new display-on record, then fresh capture/presentation.
  A blank captured scene is not proof of working stock UI. No stale-logo injection.

## Active98b: LaunchServices wait PASSED; IconServices now sampled (2026-11-03 Minsk)

- User supplied new installd/PosterBoard, SpringBoard privilege1007 denied and
  display-off records. Fresh read-only exact98 UUID passes. SpringBoard26 now
  has13 threads; its main no longer waits for CoreServices store acquisition:
  synchronous Foundation/XPC through IconServices -> SBHGetApplicationIconImage
  -> SpringBoardHome. lsd95 has2 threads and main CFRunLoopRun. This establishes
  progress past the old store wait; NOT a proved permanent IconServices deadlock
  or a ready UI. Same cache slide4a018000. Exact fresh symbolication privately in
  graphics-v98/26-98b-progress-symbols.json and95 counterpart; source snapshots
  audit/graphics98b-device/progress-*-threads-26/95.stdout. Initial symbolication
  accidentally selected older post-threads inputs; corrected filenames and
  regenerated. Only corrected13-thread/2-thread result above is current.
- Fresh process list includes pkd253 STILL RUNNING, suggestd256, PosterBoard324,
  installd318. The earlier pkd /dev UUID EINVAL did not immediately abort this
  instance. No fake replacement or service restart was performed.
- PRIV1007 is PRIV_DARKBOOT (bsd/sys/priv.h): sysctl_darkboot writing checks this
  privilege. A denied change to kern.darkboot does not itself prove a process
  crash or explain normal display timeout. Do NOT grant all privileges or equate
  darkboot with this separate display-off record. No kernel modification yet.
- Monitor41907 stopped at sample2 memory timeout20s. That command LATER completed
  END0; exact framing verified before reuse. Late VM:16KiB pages, free4540,
  active31176/inactive29001/wired15019/compressor0. Free alone not OOM proof.
  Retained shell37904 then served exact kernel, threads and ps in1.86/8.54/2.66/
  16.17s. Fresh SSH root identity also eventually returned successfully; no reboot
  or lost transport conclusion. NO monitor now owns the held shell.
- Last display transition is ON (OFF followed by ON). No synthetic power toggle
  was sent. Fresh capture request exceeded local45s deadline BEFORE initial
  renderer text arrived. Command framing token is
  WHYRED_SESSION_517979235c7fedfc5d4a9cdece3282fb; outstanding until matching END.
  Do NOT send another FIFO command until its completion is verified. Bounded
  late watcher is collecting this same response, not issuing a second capture;
  outputs audit/graphics98b-device/late-progress-capture.stdout/.png if complete.
- Passive UDP receiver2488 stays live. Observed current98b stream has no CRASH,
  panic, fatal recovery or RAMFS pressure so far. Do not claim a fresh screenshot
  or visible UI until the pending capture/user observation provides it. No UART,
  flash, MG cache edit, daemon restart or permanent presentation loop this turn.

## Current98b live boot-status check: still Apple logo (2026-11-03 Minsk)

- User asked whether UI has loaded. Stopped monitor38947 through its stop file;
  confirmed phase stopped and completed framing before sole-shell use.
- Live exact98 UUID still passes. Fresh capture-png exits0 in1.84s, accepted1,
  RGB25430; viewed PNG is still white Apple logo on black, byte-identical to
  earlier real scene (SHA d56ea3fea7985a580332da2a7e0cda48a43d84fc866880d324e6ab851a675789).
  PRIVATE audit/graphics98b-device/now-capture.png and now-capture-png.stdout. No normal UI yet.
- Latest thread monitor sample7 still has SpringBoard store-lock/syncXPC wait;
  lsd95 worker continues hardware-query/traversal path with advancing counters.
  Current USB segment has no CRASH/panic/fatal recovery/RAMFS pressure; eMMC
  bytes1304526848/errors0. No new stable-recovery claim.
- VM sample7 free7119/active30890/inactive25897/wired15896 pages (16KiB each),
  compressor0. This decrease in FREE alone is not an OOM diagnosis; inactive
  pages exist. No purge or daemon/cache mutation.
- Resumed read-only collection with NEW followup monitor40151, sole owner of
  SAME held98b shell37904. Status audit/graphics98b-followup-monitor.json,
  samples graphics98b-followup-samples.log, maximum20 rounds. Stop/release with
  audit/graphics98b-followup-stop and wait for stopped before shell commands.
  Old memory monitor38947 is stopped. Passive USB receiver2488 still live.

## Current98b pkd EINVAL /dev probe classified (2026-11-03 Minsk)

- User pasted pkd253 getattrlist common0x6/volume0x80060000/buffer64/options0,
  FSERR78 errno22. Exact masks decode to DEVID+FSID and VOL_INFO+CAPABILITIES+UUID.
  Stock devfs_vfs_getattr supplies capabilities but not f_uuid; getvolattrlist
  returns EINVAL for unsupported requested attrs without RETURNED_ATTRS.
- Native Mac comparison using the same masks and64-byte buffer reproduces22.
  Removing ONLY VOL_UUID (volume0x80020000) succeeds errno0. Private probe/output
  audit/devfs-attr-probe.{c,stdout}. This is expected unsupported devfs UUID,
  not demonstrated eMMC/RAMFS corruption or a new kernel regression.
- At inspection current98b has only pkd253 spawn and this query failure, no
  matching CRASH/exit record. Do not infer pkd abort from FSERR alone or suppress
  EINVAL globally. No kernel/daemon/cache change. Read-only monitor38947 still
  owns held FIFO; release via stop file per next section before commands.

## Active98b: visible Apple logo CONFIRMED by user (2026-11-03 Minsk)

- User confirmed ordinary reboot; NO flash or UART this turn. Fresh worker35028
  completed pinned root SSH, exact98 kernel UUID and full upload/readbacks of
  diag2a276d3f, renderer9a1d6053 and wake449eed2f. Worker is FINISHED. Installed
  baseline remains boot98/System95. Fresh held SSH37904 at PRIVATE
  audit/graphics98b-device/held; passive UDP receiver2488 remains live.
- After notifying user immediately before presentation, repeated the real LCD
  scene. Actual capture accepted1, RGB25430, alpha2332800. Driver source and
  panel samples match earlier actual Apple-logo capture: panel RGB21674,
  bbox429,820..609,1006; copied2332800 pixels. User responded “да есть же”, then
  explicitly selected “Логотип Apple на чёрном фоне”. This IS physical visible
  output evidence for this exact98b test. It does NOT establish stock UI or
  continuous compositor presentation. Old98a window was missed, not a failure.
- Exact repeat:99 successful queues, then run-mobile's30s child deadline sent
  SIGTERM; exit124 after31.408s, no101 completion. Do not report101/101 or exit0
  for98b. This timeout does not undo user's visible result. Private
  audit/graphics98b-window-test.json and98b-device/present-window.stdout retain
  exact counts and observation. Last display state was ON, so no power toggle
  was sent. No permanent screenshot loop, daemon setting or renderer flag change.
- Fresh read-only snapshots: shared-cache slide4a018000; SpringBoard26 remains
  on CoreServices store lock plus sync NSXPC. lsd95 changed from InstalledContent
  directory traversal/open to later MobileGestalt query; CPU counters advance.
  MobileGestaltHelper96 writes its cache; backboard57 has13 sampled threads in
  runloops/render IPC. This is startup dependency/progress, NOT a proved permanent
  deadlock. No identity cache edit or daemon restart in98b. Prior failed cache
  experiment stays rejected; do not seed it again.
- Post-test VM:16KiB pages, free37656 (~588MiB), active30541/inactive673/wired10897,
  compressor0, no swap. Observed stream at~983MiB eMMC reads has errors0, no fatal
  recovery/CRASH/panic/RAMFS pressure. FSERR records still include unsupported
  /dev volume-attribute probe EINVAL and startup missing-path probes; do not call
  all logged errors fatal or all filesystem issues fixed.0175 recovery remains
  physically UNEXERCISED in98b. No late-stability claim.
- PRIVATE read-only monitor38947 now owns the held FIFO: samples VM, threads26
  and95 once/minute, maximum30 rounds. Status audit/graphics98b-memory-monitor.json;
  raw samples graphics98b-memory-samples.log; worker log has same monitor prefix.
  To take the shell: create audit/graphics98b-memory-stop, wait for phase stopped;
  if failed-shell-review-required inspect final framing before reuse. Never send
  commands concurrently. Monitor does NOT wake/capture/present/restart anything.
- NEXT: inspect startup samples for LaunchServices completion, then capture the
  current real scene and trace why stock swaps differ from the working explicit
  capture-to-panel path. Visible logo now rules out a universally broken panel
  mapping for this test; it does not fix stock rendering. No new kernel needed
  merely to repeat this successful display path.

## Earlier98b ordinary reboot for a repeat the user can watch (2026-11-03 Minsk)

- User missed the prior101-frame test while away; this is NOT a negative visible
  result. Asked to repeat after returning. At ~17:26Z old98 held shell27053
  accepted BEGIN but kernel-uuid command never completed within20s. Fresh SSH
  banner timed out8s. USB heartbeat still arriving; observed stream has no fatal
  eMMC/SIGBUS/CRASH records. Cause of lost userspace access remains unproved.
  Do NOT reuse98-device/held: outstanding command framing is incomplete.
- User confirmed ordinary reboot, no new flash/UART. Prepared/started PRIVATE
  ssh-v90/check_graphics98b.py PID35028. Status audit/graphics98b-check.json,
  log graphics98b-check.log, outputs graphics98b-device. Fresh boundary in
  audit/graphics98b-reboot.json. Installed boot98/System95 unchanged.
- Fresh worker waits for cold SSH, opens NEW retained shell, verifies exact98
  UUID, uploads/readbacks GPR diag, window renderer9a1d6053 and final wake449eed2f.
  It STOPS at prepared-shell-retained, NO automatic wake/capture/presentation.
  Notify user with “смотри сейчас” immediately before running the ~10s window.
  Check last current display ON/OFF and only send a power event if OFF.
- Prior98 repeated-frame success is memory/submission evidence only; physical
  output still unknown. No repeat succeeded in this turn yet. Cache experiment
  remains reverted; do not seed it again or restart lsd based on its failed probe.

## Active98: real repeated frame completed; identity cache experiment rejected (2026-11-03 Minsk)

- Installed boot98/System95 confirmed by actual SSH kernel UUID
 936C980F-9428-33A1-B076-CDB09ABDC855. Cold root SSH became available around
 13min, observer24959 attempts65. Current retained shell27053 at PRIVATE
  audit/graphics98-device/held. Passive receiver2488 remains live. Worker has
  finished, not running in background; protocol framing currently complete.
- Final wake/render helper uploads and exact readbacks PASS. Initial diagnostic
  HID pair returned normally; latest display state already ON, no new ON/OFF
  transition observed from this pair. Do not blindly toggle a screen already ON.
  Physical whyred keys still unsupported. Earlier97e OFF->ON remains actual
  successful remote wake proof. Subsequent98 test checked last display state
  and only sends a key if OFF; no additional toggle was needed.
- Initial capture-png emitted accepted1 RGB25430 alpha2332800 of2740500, then
  hit the30s run-mobile child limit (SIGTERM/124) BEFORE PNG output. Thus the
  actual capture produced pixels; timeout does not establish capture failure.
  Later warm retry returned0 in<1s and exported62639B PNG1125x2436. Viewed:
  white Apple boot logo on black, EXACT byte match to prior97c capture; SHA
  d56ea3fea7985a580332da2a7e0cda48a43d84fc866880d324e6ab851a675789.
  PRIVATE audit/graphics98-device/capture-lcd-warm.png. No normal UI yet.
- New finite present-window source87bf4ee564853b6c72dd46c91f0e87537f8379b9,
  CI41674768570/job126052329724 ALL steps PASS. Artifact13248659353 ZIP112045B
  SHAe8d091a772bb3aea9b984db91cbbb20ae0aa8e60313d6a6106f7d219bd324faf;
  signed binary93664B SHA9a1d6053ede2813f8d53d269a87dabde8d3ac00373a7c01c011a788b95bbe131.
  All provenance/archive/platform/ISA/signature/exact2rights checks and upload/
  readback/exact98 UUID PASS. Actual mobile present-window EXIT0,101/101 queues,
  same captured surface8 repeated100ms intervals (~10s). Driver source RGB25430;
  panel RGB21674, bbox429,820..609,1006, copied2332800 pixels. These are memory/
  submission results, NOT visible display proof. User screen-observation question
  for this exact window is still pending; never reuse97d black-screen answer.
  Private graphics98-window-test.json and present-window.stdout. No test art,
  renderer flags, daemon configuration or kernel changes in this helper.
- Health readback after first capture: page16KiB, free22687 (~354.5MiB), active
 32774/inactive11921/wired12349, no swap. Per-directory RAMFS allocation read
  totals recorded privately; examples db3489792B, mobile8306688B, root4538368B,
  Keychains2490368B. This early snapshot is far below128MiB and is NOT long-run
  quota proof. No purge/quota change. Fresh full usage script completed safely.
- Current98 exact cache slide1c6c4000. SpringBoard26 has5 threads: main waits
  on CoreServices store lock, another sync NSXPC; lsd95 has8 threads, worker in
  MobileGestalt hardware query. backboard57 has13 sampled threads. This repeats
  earlier startup dependency;97e eventually reached main run loop without an
  identity workaround, so do not call this uniquely proved permanent deadlock.
  PRIVATE graphics-v98/*-98-symbols.json, exact live samples in98-device.
- Named MobileGestalt cache now exists6838B (was absent early97e). Added98 UUID
  ONLY to guarded experiment; sourcebc325f71090ccdfe788876b3cde751d09cb88458,
  CI41677592018/job126062268344 ALL PASS. Artifact13251861348 ZIP36640B
  SHA589fafec719f3103c94ab70e03e1822094787f74c672bb68c1a1e796d52a348e;
  binary90512B SHA8caef2f4f9b1411ca8c8af6b91cafddaeb604b4f2bc199d048b5bd9a4d3abe7c.
  All artifact/source/platform/ISA/strict signature/exact2protected-keys checks,
  upload/readback/kernel guard PASS. Actual platform UUID provider works.
- Actual guarded seed succeeded; exact2-key delta/types and original backup
  verified. Actual mobile MGCopyAnswer probe FAILED (matches0,10121.445ms).
  CacheExtra insertion did not supply these runtime answers. AUTOMATIC rollback
  succeeded and exact original bytes re-read. Original SHA
 5b1dd09b0b74f4046c9ef7a14bb5378d3d7b912519d46bd43cd0d26e3f1f9d37,
  temporary SHA5bac2dbf516afd7f9c38f70f8b5427aa3d85f05fc3c153198d49cab1b54be635.
  Private graphics98-gestalt-check.json phase rolled-back-shell-retained,
  cache_written=false/restored_exactly=true/daemon_restarted=false. Backup remains
  for audit; helper deliberately refuses overwriting an existing backup. Do NOT
  repeat this unsuccessful seed or restart lsd on its basis. No persistent write.
- At latest checkpoint ~24min: eMMC bytes1316016128/requests32185/errors0,
  no fatal recovery/common SIGBUS/CRASH/pressure records in observed98 segment.
  No recovery has occurred, so0175 extra-status branch remains physically
  UNEXERCISED. Do not claim a long stability proof or a demonstrated repair.
- Sole shell27053 is free after warm PNG retry. Next: obtain user's actual panel
  result for101-frame test; distinguish mapping/visibility from startup state.
  Cache experiment is rolled back. No lsd restart, extra flash or UART this turn.

## Boot98 flashed; cold SSH/graphics observer running (2026-11-03 Minsk)

- User confirmed Fastboot. PRIVATE tools/flash_kernel98.py --flash --ready-answer
  rechecked image/kernel hashes, rollback, System95 completion, exact private
  identity/product/unlocked64MiB boot. Boot SEND and WRITE each OKAY; reboot OKAY.
  Installed baseline is NOW boot98/System95. No System or other partition write;
  no UART. Private audit/kernel98-flash.json, boundary graphics98-boot-boundary.json.
- Image SHA b3d6440ff1e050c52fa325dd88543965a23217fc33da27fa2287a8a505527473;
  expected running UUID936C980F-9428-33A1-B076-CDB09ABDC855. Fresh USB datagrams
  observed after reboot; early snapshot starts mid-record (best-effort UDP).
  Exact running UUID and recovery behavior await SSH; no graphics claim.
- Started PRIVATE ssh-v90/check_graphics98.py PID24959, phase waiting-for-ssh.
  Status audit/graphics98-check.json, private log audit/graphics98-check.log,
  outputs audit/graphics98-device. Sole old receiver2488 continues unchanged,
  logfile audit/graphics97d-usb-session.log/current-whyred-usb.log alias.
  Worker flashed=false means observer itself does no flash; actual flash above
  completed. Typical current CMD17 cold startup takes10..15min. Keep active
  observer; never start a second worker or reuse97e shell14309.
- Next inspect observer until actual kernel guard/uploads/wake/capture result.
  On real-frame submission promptly request visible screen confirmation.
  If capture nonzero, do not substitute test art or call CPU submission working UI.
  Need fresh RAMFS directory accounting while transport healthy. Previous98-tool
  artifacts below are authenticated; no new permission needed for this test.

## Ready for user Fastboot:98 tools and next observer prepared (2026-11-03 Minsk)

- Source ae72123da7f607e6e4ade37696192ca8f6be04b2 adds verified97/98 UUID
  allowlists to wake/render tools. Wake CI41672463674/job126044141756 all PASS;
  render CI41672463382/job126044138478 all build/test/upload steps PASS.
  Authenticated artifacts, CRC, exact source/report/binary digests, iOS platform,
  ISA, strict signatures and exact rights checked. Private audit/graphics98-final-tools.json.
- Wake artifact13248562336 ZIP21654B SHA630de17baedebcc0846d41dd2d0f82ef011cbfcc3f9f4f35d90f2db3b1dd119d;
  binary69920B SHA449eed2ffc3e7399a4f3f4b14fd7d4ac103565ab25e14f1593f9f6bf26863977,
  PRIVATE graphics-v98/wake98-final/whyred-display-wake.
  Render artifact13247629259 ZIP111894B SHA3c494265fa581f867bf8bf561c90f89ce3dc048ce49a04ae2ca1c01c38c15547;
  binary93760B SHA3d49e9f4e279c15676ac234bc8cc865f8bfa20679f78d39e987ed4797d6adae4,
  PRIVATE graphics-v98/render98-final/whyred-render-probe. Neither final98 tool
  uploaded yet; old97 HID result below is the actual observed wake.
- Verified98 linked recovery disassembly contains the concrete function and
 3 command callsites (STOP, first CMD13, optional clean recheck); private
  kernel-v98-recovery/linked-recovery-disassembly.txt. Complete kernel run is
  SUCCESS; boot98 image ready as recorded below. No flash has occurred.
- PRIVATE ssh-v90/check_graphics98.py syntax checked, NOT started. After verified
  boot98 flash/reboot: mkdir audit/graphics98-device and start this worker with
  private log redirection. It waits for cold SSH, retains fresh shell, verifies
  exact98 UUID, uploads/authenticates diag and both FINAL98 tools, sends ONE
  diagnostic HID wake, captures actual PNG then presents once only if capture
  succeeds. No cache writes/daemon restarts. On timeout review outstanding FIFO
  framing before reuse. Screen confirmation remains required after any present.
- User Fastboot-ready question pending; latest scan sees no Fastboot. All boot
  preparation is complete. Only boot is authorized for next flash; System95
  remains installed. UART unnecessary. Do not use97e shell for a new boot.

## Boot98 authenticated and ready;97e storage failure after HID wake (2026-11-03 Minsk)

- Installed still boot97/System95. User reports console clears, no interface
  after test. Do NOT claim working visible logo/UI. Physical key still unsupported.
- Actual guarded HID helper ba80a653c024407b3dfab8cd25101ccf9b5e7d18,
  CI41671434692/job126040535199 ALL steps PASS. Artifact13248107726 ZIP21230B
  SHAa58a8cb5c97aa2ddec611453224540096a88efd84c44aab42b171a367aff15ed;
  binary69920B SHA3fe413a4713d96637c8dfd8294900f3134d4310197954dc9f273cfda30c89015.
  Provenance/archive/platform/ISA/strict signature/exact2 HID rights verified;
  upload/readback/exact97 kernel PASS. ONE diagnostic power down/up100ms through
  existing SweetHIDButtons sender produced actual SWEET FB: display on. Public
  Apple IOHIDFamily monitor/entitlement examples and exact20F66 ABI reviewed.
  This is remote diagnostic input, not an implemented physical key driver.
- Earlier unblank helper3975952 source CI41670889270/job126038611872 all PASS,
  artifact13247038757 ZIP15022B SHA17b91583e2a896d402c64edae40651712a8adacbbd96d6da884e56a5415d36a9,
  binary68976B SHA8972b230f771e8660b8ebcd96b6b3e32740e6f565fe61c86714c85d35988e8f0.
  Verified/uploaded/read back; unblank returned but NO display-on, flags16ec and
  opaque black unchanged. Only HID pair actually changed display state.
- During capture AFTER actual wake,97e repeated the fatal CMD17 recovery:
  incomplete lba6974501, FIFO512, both CMD12 error00018000 and CMD13=00400900,
  then transport rejection/APFS EIO/mass SIGBUS. Capture command exit138, no PNG,
  no present submitted. Private storage-failure-context.txt in97e-device.
  Current held shell14309 has completed framing, but failing disk means do not
  rely on further process samples/uploads. HID worker complete-shell-retained
  means protocol complete only; last display-flags command ALSO exit138.
- RAMFS pressure also recurred:8192/8192 pages,128MiB, low free-page samples.
  Read-only usage before disk failure: diagnostics6176768B, uuidtext25182208B,
  mobile Library/Caches5799936B, root Library/Caches8683520B. This is incomplete
  directory accounting, not sole quota ownership. No purge/quota change done.
- Full0175 kernel source4878ce141d4ccd692024584000b2e463c7c73089,
  CI41669886409/job126035105627 ALL steps success, including4819 eMMC checks
  and retained ASan+UBSan/USB/RAMFS/graphics/etc. Both artifact length/digest/CRC,
  run/source identity, all reviewed runtime sources and reports, applied0175,
  linked new diagnostics, zero LSE/PAN, cache clean/idle/commpage disassembly,
  loader/stock DTB/ADT/layout/size guards PASS. Physical recovery still UNTESTED.
  Kernel artifact13247418940 ZIP79480813B SHA6cf40da1cdd1ab20a3bda891ce7a29730db55616c4eff2f266905cd0b5624f97;
  tree13247259365 ZIP25439713B SHA211b3400716592f0d56920c8fda998280171034eccdf62609404f5dab58f30cd.
- Packaged PRIVATE port/out/whyred-ios-root-v98-status-recheck-41669886409:
  boot22347776B payload21537520B, image SHA
  b3d6440ff1e050c52fa325dd88543965a23217fc33da27fa2287a8a505527473;
  kernel SHAf1f2eb6f474027931d0cb88ebaf07716e1b0131973509f8576f9ea9616edf770,
  UUID936C980F-9428-33A1-B076-CDB09ABDC855. Keeps XO CMD17 and installed System95;
  only bounded clean second status/fresh reread candidate changes kernel behavior.
- PRIVATE tools/flash_kernel98.py prepared, syntax checked; image/System95 proof,
  v94 rollback hash and manifest checks pass. Read-only Fastboot scan did NOT
  find target; no flash. User asked to enter Fastboot (pending response).
  Run ONLY after ready: python3 tools/flash_kernel98.py --flash --ready-answer.
  It verifies exact private serial/product/unlocked64MiB boot before boot-only
  flash/reboot. No UART. Never print private identity/keys.
- Pending tool-source update adds ONLY verified98 UUID to wake/render allowlists
  (97 retained), because framebuffer ABI/System95 are identical. Gestalt mutator
  remains97-only and is NOT needed; no cache write. Need signed new builds and
  exact upload/readback after98 cold startup before any new present attempt.
- Passive USB receiver2488 remains live. Current logfile/private key path and
  old97e artifacts retained. Next reboot needs NEW boundary/shell; NEVER reuse
 97d5106. No98 hardware boot or successful graphics claimed yet.

## Fresh97e reaches SpringBoard run loop; physical key path missing (2026-11-03 Minsk)

- Actual97e read-only samples, exact shared-cache slide2fefc000: SpringBoard26
  main is now CFRunLoop/GSEventRunModal/UIKit, rather than the earlier
  LaunchServices store wait. lsd95 main is idle in CFRunLoopRun. Thus the old
  MobileGestalt workaround is NOT required to reach this state. Fixed named
  cache path is still absent, no cache mutation or lsd restart performed.
- Authenticated present helper9b0a77d5 uploaded/read back. Actual root and mobile
  captures accepted1, RGB0, alpha2740500/2740500. No PNG exported, no new present
  submitted. Last logged display transition is OFF. Read-only backboard57 LCD
  has6 clients, CPU renderer/wrapper nonzero, flags16ec, disablesUpdates false.
  Private audit/graphics97e-device/backend2.json. A black sleeping scene is not
  evidence by itself of broken scanout or compositor.
- User short-pressed power with no reaction. Source confirms sweet_keys_init
  is called only from sweet_ufs.c; whyred uses the eMMC path instead. Current
  stream has no SWEET KEYS or HID key events. No physical whyred button polling
  implemented. Do not request repeated button presses as if wake were supported.
- Added exact97 physical-target guarded whyred-display-wake. Native refusal/
  argument checks PASS. Source7f66eb5f0024afddec72d0d216da4d1ee0b1559b,
  CI41670478848/job126037193120 all PASS. Artifact13247607554 ZIP14200B
  SHAa7b2ccc9637510ca9565f454ba2e310d65f7e79cf0a9ba92e2ad9f592529cfc8,
  binary68976B SHAeb0e0755e1398266ba6f9c9a1e364c0f515ab2986878a90d044009f6aad32a6d.
  Exact provenance/digest/length/CRC/platform/ISA/strict signature/no-rights
  checks PASS. Upload/readback/exact97 UUID PASS. Actual mobile SBSUndimScreen
  returns request_status0, but NO display-on event; capture remains opaque black.
  This is a request result, not successful wake. Retained97e shell14309 is free.
- Source3975952da98472d2e7eff55be7b062c8b83e4a42 adds separate explicit unblank
  via exact20F66 BKSDisplayServicesSetScreenBlanked(false). Does not interpret
  its unspecified C return as success; require observed display/capture change.
  Native guards PASS; signed iOS CI41670889270 pending, not tested yet.
- Recovery0175 source4878ce141d4ccd692024584000b2e463c7c73089 full kernel
  CI41669886409/job126035105627 building. Local exact current C/header ARM64
  compile passes with generated79 headers; zero disallowed LSE/PAN instructions,
  no >4KiB frame warning. Expected legacy declaration warnings retained. First
  invocation used wrong cwd and failed meta_features.h; corrected BSD generated
  cwd compile passed. Private kernel-v98-recovery/emmc98-compile.json.
- Current97e observed stream has no common SIGBUS or fatal eMMC recovery so far.
  Actual mediaserverd null-PC crashes symbolize to CoreImage via CMCapture,
  separate from storage. Known CoreImage null callback remains unresolved;
  searchd SIGABRT also retained. No hardware/software renderer success inferred.
- Installed boot97/System95 unchanged. Logs continue privately, no UART/flash.

## Active97e and late97d storage failure; recovery candidate0175 (2026-11-03 Minsk)

- User confirms backlit BLACK after the actual one-frame97d experiment. Nonempty
  source/panel measurements are not visible display success. Later stock swaps
  and display-off/on occurred, so the delayed report alone does not uniquely
  identify scanout/cache failure. Graphics remains unresolved; no synthetic UI.
- Full retained97d USB stream later records fatal eMMC recovery, despite CMD17
  baseline: last good telemetry bytes1302032384, requests32736, cmd17=2543032,
  cmd18=0, errors0, elapsed_us1826742065. Then two CMD12 errors int00018000,
  each followed by CMD13 r1=00400900 (ILLEGAL_COMMAND, TRAN, READY), final read
  rejection, APFS EIO and mass SIGBUS. Prior ~18min clean checkpoint was limited.
  Private audit/graphics97d-storage-errors.txt and first-sigbus-context preserved.
- Patch0175 permits one additional CMD13 only after failed STOP, sole
  ILLEGAL_COMMAND error, TRAN/READY and no inhibit. It NEVER masks the error:
  final status must have zero R1 errors, safe state, zero pending interrupts/FIFO
  before a fresh byte-exact reread. Persistent/error/unsafe responses still fail
  closed. Hypothesis: STOP introduced a consumable status flag; physical effect
  remains UNTESTED. No clock or storage-write policy change.
- Exact patch replay against current late-patched source matches reviewed header.
  4819 actual extracted-function MMIO model checks PASS, also UBSan. Added clean
  second-status/fresh reread, failed recheck, persistent/distinct card errors,
  unsafe READY/state/inhibit, stale FIFO and failed reread coverage. Old0172
  driver fails the new fixture. Local results do not establish hardware recovery;
  full ARM64 CI pending. Private kernel-v98-recovery/final-local-checks.json.
  Repository validator Python47/shell7 syntax checks pass; its patch-number
  check fails on pre-existing sweet/whyred duplicate numbers and0082..0099 gap.
  This candidate adds0175 after0174 and does not renumber historical patches.
- User ordinary-rebooted; configd restored static en1 IPv4 without admin prompt.
  Passive receiver2488 continues graphics97d-usb-session.log; fresh97e notification
  boundary1572317. Fresh SSH root recovered, retained shell14309 at private
  audit/graphics97e-device/held, installed exact97 UUID verified. Authenticated
  GPR helper and FINAL gestalt-path98 helper uploaded and byte-exact read back.
  Worker stopped BEFORE cache mutation: fixed volatile cache path ENOENT, also
  absent on later read/list. cache_written=false; no seed/rollback/lsd restart.
  Fresh SpringBoard26/lsd95 read-only thread samples obtained. Inspect current
  cache/process dependency before attempting another guarded experiment.
- Installed boot97/System95 unchanged. No flash or UART this turn. Sole current
  held shell is97e; never reuse97d shell5106 (unfinished SCP state before reboot).

## Current stop: phone access stalled, no identity-cache change (2026-11-03 Minsk)

- Final tool source b242eb47248d501fde328370c226dc1858f8a38e CI41660019245 /
  job126000441380 ALL steps pass. Artifact13242030669 ZIP36123B
  SHA9b16cd30f08a1bd754cc8aa8c9e73752f25d3577fbd66ec0cbf0ea1d7aec9546;
  binary90512B SHA3356f566f223beca159668fbe2f216c4eeefb2f80a1d1f52ae22daacefc95119.
  All archive/provenance/report/platform/ISA/signature/exact rights checks passed.
  Native final path build and host refusal pass. Candidate PRIVATE graphics-v98/
  gestalt-path98. NOT uploaded/run; cache remains byte-for-byte unmodified.
- Fresh login with ConnectTimeout60 failed255 before root identity. Original
  SCP attempt failed at banner before payload. Retained-shell tiny SCP test
  waited150s without its FIRST acknowledgment: no C record or file payload sent.
  audit/graphics97d-held-transfer.json is failed-protocol-review-required.
  Last session-log suffix is WHYRED_SCP_e9ce42d320f3d80db2d3ed525ddce07f_BEGIN only.
  Do NOT issue framed shell commands into this session while sink state is
  uncertain. No successful phone use of persistent_scp.py claimed.
- User asked for ordinary reboot, USB attached, UART unnecessary. Await answer;
  no second reboot/flash performed. Earlier optional visible-logo question also
  unanswered. USB receiver2488 continues audit/graphics97d-usb-session.log.
- Prepared PRIVATE ssh-v90/check_graphics97e.py, syntax checked, NOT launched:
  create fresh audit/graphics97e-device before launch; fresh pinned root shell,
  exact97 UUID, authenticated GPR diag and FINAL gestalt-path98 tool uploads,
  fresh original cache read/hash, guarded seed, exact2-key delta/backup check,
  actual mobile MG probe; automatic exact rollback on a completed failed probe.
  It deliberately does NOT restart lsd: inspect passing result first, then use
  freshly verified PID. On timeout, review outstanding command before any reuse.
- Next after user's ordinary reboot (or verified Fastboot reboot, NO flash):
  record new log boundary, launch fresh97e worker, inspect MG probe. Only after
  it passes, restart actual lsd and observe SpringBoard/real server capture and
  physical presentation. Prior cache/graphical scene not a final UI repair.
- Updated WHYRED-GRAPHICS-STATUS.md to reflect actual one-frame presentation,
  false update gates, rejected queued-reply guess and exact identity dependency.

## Retained-shell transfer prepared; exact IOKit cache path corrected (2026-11-03 Minsk)

- Source721de172968684e14bf53159dfbf752334dd2012 CI41658918789 all steps PASS;
  artifact13240003682 ZIP36116B SHA50a4042d1dd82a3b28f264c090b81aa69e6511db26c7de73c8ae57c75629e8c5,
  binary90512B SHA4d0debc184754959b6aeba8d802e8703ad36ea7536e22a24f98350854c81f3ab.
  Digest/length/CRC/source/platform/ISA/signature/exact entitlements verified.
  NOT uploaded: fresh SSH stalled at banner exchange, SCP refused before data.
  Cache remains unchanged, no lsd restart. Actual retained kernel read still works.
- Exact preserved cache inventory uses IOKit.framework/Versions/A/IOKit; corrected
  explicit dlopen path before testing, rather than assuming the unversioned alias.
  Signed rebuilt tool pending. Root stat command exceeded60s but eventually
  completed both ENOENT results and its end marker; shell is not abandoned.
- Private persistent_scp.py transfers through existing shell using SCP C/E records,
  checked exact Dropbear sink behavior. Actual native dash+scp/FIFO test PASS on
 131106 bytes including binary and shell-looking text, mode0755 and exact bytes;
  subsequent framed shell command succeeds. No phone transfer with this utility
  yet. This avoids requiring new root authentication, not a general SSH fix.

## Development identity tool iOS SDK correction (2026-11-03 Minsk)

- Candidate f8bb612af48e7953b65d2ada7c9cae340e8bd505 CI41658525007 /
  job125995235395 FAILED: gethostuuid unavailable on iOS. No candidate uploaded
  or cache written. Replaced that SDK-disallowed API with read-only IOKit
  IOPlatformExpertDevice.IOPlatformUUID, then NSUUID validation. This is the
  existing generated platform UUID (local XNU IOPlatformExpert.cpp), not a new
  device identity source or simulated network service. Missing value fails closed.
- Native warning-clean compile and all3 physical target guards retested. Actual
  cache write, MG probe, lsd restart and UI improvement remain UNTESTED.

## IPC correlation rejects queued-reply guess; actual missing identity keys (2026-11-03 Minsk)

- GPR helper02b54fd6983d8744c88cabcd1b20bc85e411a2d8 CI41656697790 /
  job125988798863 all steps pass. Artifact13240720530 ZIP72878B
  SHA1d5ac22ba4bd60396ac14a3dd15ebea9874ac7b7e6133fe23e31158405790d22;
  binary73504B SHA2a276d3f3a3b60e9773f0e51482ad8137e61521b1d1afb00efbbdd217791e8d8.
  Provenance/platform/ISA/signature/rights/upload/readback verified. Actual ARM64
  GPR samples correlate x5>>32 with local mach_msg2 ABI: SpringBoard thread1
  waits on0x4303, EMPTY; its queued0x2803 is NOT that port. No lost reply wakeup
  proved. lsd advanced from UserManagement request to MG hardware lookup; CPU
  counters and later worker exit demonstrate progress. Do not call it deadlocked.
- Bounded read-only lsd stack constants decode exactly (MD5 MGCopyAnswer prefix,
  checked against each actual hash): WifiAddressData/WifiAddress and
  UniqueDeviceIDData/UniqueDeviceID. This is the actual hardware-query dependency.
- Existing volatile systemgroup MobileGestalt cache is6838B, CacheVersion20F66,
  CacheData5337B/CacheExtra33 entries. Both UniqueDeviceID keys and Wi-Fi address
  keys absent. Original bytes preserved privately; no cache mutation yet.
- Added explicit whyred-gestalt-cache seed/probe/rollback experiment. Exact97 UUID,
  root identity, fixed path on whyredramfs, regular single-link file, version and
  caller-supplied current SHA256 are required before seed. Adds ONLY2 development
  identity answers derived from existing platform host UUID, preserves other
  fields, creates original backup, atomic replace and restores owner/group/mode.
  Rollback verifies current digest and restores original bytes. Probe prints only
  match/timing, never identity values. No fake Wi-Fi service or partition write.
  Native warning-clean build/all3 physical-target refusals pass; signed iOS build
  and actual cache behavior pending. User informed of temporary experiment.

## Actual97d queued Mach messages; register sample candidate (2026-11-03 Minsk)

- Ports helper838548e1694f3e53f148eaca4c621e6912c36dbb CI41656099646 /
  job125986682704 all steps PASS. Artifact13240205870 ZIP72280B
  SHA1dca11e6566a1ef3d031f6c0a407009bb08e1c7f1ad9fb489aa09f04b5589092;
  binary73504B SHA95489d3da45535d70dbba405ab3b214cd63b6c31b89016196a73e6cca155e005.
  Provenance/platform/ISA/signature/rights/upload/readback checked. Actual phone
  selftest PASS: own queued message preserved, no receive performed.
- Physical queue snapshots: launchd has514 receive rights,512 queried with0
  errors,55 nonempty queues/120 messages (LIMITED, not the whole task). lsd94 has
 133 receive rights, all queried:36 nonempty/36 messages. usermanagerd85 and
  notifyd89 receive queues all empty. SpringBoard26 has46 receive rights,2
  nonempty, including0x2803 limit1/msg1/seq0. Read-only unsuspended snapshots,
  not proof of which port the blocked caller waits on or a unique kernel defect.
- Added optional registers PID to existing bounded thread sampler, exposing ARM64
  x0..x28 only on explicit request; native builds report unsupported GPR format.
  Purpose: correlate actual mach_msg2 receive port with queued-port name, using
  local XNU trap ABI. No task suspend/write. Native warning-clean/selftest passes;
  signed iOS build and physical correlation pending.
- Private audit/graphics97d-ports-check.json complete; retained SSH shell5106 free.
  Post-reboot observed stream still no common SIGBUS or eMMC errors at ~18min.
  User confirmation of visible one-frame boot-logo presentation remains pending.

## Actual97d capture-to-panel passes; port-queue diagnostic prepared (2026-11-03 Minsk)

- After requested ordinary reboot, root SSH recovered at14:36Z; retained shell
  PID5106, private audit/graphics97d-device/held. Exact97 UUID and both helper
  upload/readbacks passed. Present-once exit0, capture RGB25430 alpha2332800,
  surface5/swap5 requested successfully. Driver source exact25430 RGB and
 2332800 copied pixels; panel RGB40113 (console raced), nonzero output verified.
  User screen confirmation pending. This is one real boot-scene frame, NOT
  repaired SpringBoard or continuous presentation. No flash/UART this turn.
- Fresh backboard57 read-only inspection:4 displays, LCD2 render clients, same
  concrete vtable, flags3 and CPU renderer. LCD flags12ec: disablesUpdates FALSE,
  software-capture flag TRUE. All4 update gates false. Startup gate hypothesis
  does not explain current blank stock swaps. Actual current cache slide2b788000.
- Fresh SpringBoard26 reproduces database-store wait. lsd94 thread1 goes through
  InstalledContentLibrary to listAllPersonaAttributesWithError: on UMUserManager;
  it waits inside xpc_connection_resume. usermanagerd85/launchd1/notifyd89 thread
  samples obtained read-only. No unique IPC failure cause established yet.
  Bounded SpringBoard stack search found no NSXPCConnection among11 selected
  low-heap candidates; absence is not evidence of no connection.
- Added explicit whyreddiag ports PID: up to512 receive-right status queries,
  <=16384-name guard, reports nonempty queues without receiving/extracting any
  message or stopping tasks. Native warning-clean build/selftest proves one
  own queued message remains after inspection. Cleanup only own test rights.
  iOS build/phone port-queue measurements pending. Need distinguish server-side
  queued messages from clients waiting for replies before proposing IPC fixes.
- Old pre-reboot SIGBUS preserved separately. Fresh observed segment has no
  common SIGBUS or eMMC read errors at this checkpoint; not a long stability proof.

## Presentation probe authenticated; LaunchServices wait identified (2026-11-03 Minsk)

- Source b03952a947f529f7f0b009535e221d2efdf76b47 CI41653213351 /
  job125976558662 ALL steps pass. Artifact13239250056 ZIP111473B
  SHA888e8523f14bbadb4eb043c913eaeb70803ae840f12472d853e240d3bcb1a6a8.
  Signed binary93760B SHA9b0a77d5394de0987aa0313ee3a0d63578b9d1318ebd37e4f00aec4640fb7091.
  Source/report/digest/length/CRC/platform/ISA/signature/exact2rights checked.
  No physical present result yet: ordinary reboot confirmed; cold CMD17 startup
  still underway. Private serially coordinated restore/present/sample/backend
  workers wait for one retained shell; no concurrent commands on its FIFO.
- Exact97c CoreServices stubs resolve synchronousRemoteObjectProxyWithErrorHandler:
  and getServerStoreBlockingWithCompletionHandler:. ControlCenter caller uses
  initWithBundleIdentifier:allowPlaceholder:error:. Main waits on shared store
  lock while another thread requests database store over NSXPC. Why the server
  has not supplied it remains unresolved. No new lsd diagnosis claimed.
- Decoded actual CAWindowServerDisplay disablesUpdates getter1884deb74: follows
  native server+60 to display, tests bit8 of unaligned16bit field+251. Setter
 1884deae8 changes bit0x100; external software/capture path uses separate0x80.
  Prepared bounded read-only measurement, not a live flag change. Previous
  direct-load scan found no references because access uses add+ldrh; corrected
  scan and exact ObjC method list resolve the getter. Private cache bytes kept.
- Rewrote WHYRED-GRAPHICS-STATUS.md so superseded unentitled empty-capture results
  are clearly distinguished from actual entitled marker/Apple-logo successes.
  Post-reboot observed log segment has no CRASH records or eMMC errors so far;
  early pre-USB boot was not captured. Pre-reboot SIGBUS lines kept separately.

## Resumed after Mac crash; present helper compile fix (2026-11-03 Minsk)

- User reports Mac crash and asks to continue graphics. Source HEAD4f15ca8a and
  private prior PNG/audits survived. Old retained SSH process and UDP receiver
  are gone. USB en1 still configured; a single pinned login rejects publickey.
  Requested ordinary reboot, no UART. Restored passive UDP to a NEW private
  audit/graphics97d-usb-session.log; old logs preserved. Current stream has
  repeated xpcproxy SIGBUS, not attributed to a new cause yet.
- Prior present-once CI41650225641/job125966097273 FAILED during iOS compile:
  mach_task_self undeclared. Added explicit mach/mach.h rather than depending on
  transitive desktop SDK includes. Native warning-clean fallback-declaration
  compile and present-once host refusal pass. Signed iOS/phone test pending.
- Installed boot97/System95 unchanged; no flash or serial access this turn.

## Actual server PNG shows Apple boot logo; one-shot CPU presentation prepared (2026-11-03 Minsk)

- User reports console text with occasional clears to backlit black. Existing
  current97c FB logs independently show source3 RGB0/alpha0 copied to panel on
  swaps4/7/10/13. No exact timestamp match to each user observation claimed.
- PNG helper source98d9a5b946ac3d8de4a3776f9b252317274fed89, CI41649429775 /
  job125963367270 all steps pass. Artifact13236617252 ZIP106157B
  SHAa404d52c692bd7c12a2781fb1adcefa6fbc8d5b779498b1576381ff8fea08e84;
  binary93488B SHAa21e48060343da4613c758e4af3c075c7245a128f8308049908c916d53547531.
  Source/digest/length/CRC/platform/ISA/signature/entitlements and exact upload
  readback verified. Physical capture-png exit0:62639B PNG1125x2436, viewed locally:
  real WHITE APPLE BOOT LOGO on black, not console or a synthesized test image.
  Private audit/graphics97c-device/capture-lcd.png, do not commit image/bytes.
- Actual SpringBoard thread sample still main CoreServices/ControlCenter wait,
  another syncXPC through CoreServices/Foundation. Backboard render/MIG/runloops
  present. No proved identity of waited-on service. Private corrected97c cache
  slide symbolication saved; large nearest-export offsets NOT treated as names.
- Added explicit present-once, only for exact running97 UUID, using PUBLIC IOKit
  C ABI and our custom framebuffer selectors4/5/7/8 (layout source-reviewed).
  Captures real LCD into own IOSurface, verifies displayID0 and1125x2436, queues
  it as layer0 with full source/destination rects. Driver retains surface. No
  invented UI, renderer flags, daemon changes or partition writes. This is only
  a one-frame test, not continuous UI rendering. Native warning-clean build and
  host refusal pass; signed iOS CI/physical presentation pending.

## Entitled remote marker PASSES on phone97c; image export prepared (2026-11-03 Minsk)

- Corrected ONLY diagnostic signature with2 exact QuartzCore entitlements.
  Source396c0b1fc2bcb2d3c860df8fa5c828e872e74292, CI41648826350/job125961234726
  ALL steps pass. Artifact13236571718 ZIP102903B SHA843341b770effa2228efdefe31115d7176f59ca5ec8c858379330ae561f29639.
  Renderer92672B SHA27e49395e0d36b1d18eef32a91779858828d100393d284f5abb8c16b3c2e387a.
  Digest/length/CRC, exact signed entitlement set, source/platform/ISA/signature
  verified; exact upload/readback pass. Private graphics-v98/rights98.
- ACTUAL mobile entitled test exit0: baseline RGB25430 alpha2332800, after RGB26454
  alpha2332800, red marker EXACT1024px, context1156270260. Finally invalidated.
  Same source previous unentitled capture was allzero; previous empty captures
  are NOT reliable evidence of failed compositor. No GPU fabricated or daemon/
  System/kernel changed. CPU server composition and own marker capture now proved;
  stock UI/panel presentation still NOT established. User informed and screen
  appearance question pending. Private audit/graphics97c-rights-check/device.
- Corrected private rights status inherited old worker PID/time fields: retained
  as initial-probe metadata, not fresh worker identity. Evidence/output unchanged.
- Added capture-png: captures own surface and exports PNG as base64 stdout,
  no phone file or display mutation. Uses ImageIO and locked BGRA mapping lifetime.
  Native warning-clean build, all4 host capture/remote refusals pass. iOS build
  pending. Next inspect actual image before proposing framebuffer changes.

## Fresh97c physical checks; diagnostic renderer rights missing (2026-11-03 Minsk)

- User returned phone in Fastboot. Verified exact private baseline identity and
  whyred product; fastboot reboot OKAY, NO partition write. Private immutable
  audit/graphics97c-reboot.json boundary9705721. Cold CMD17 startup took ~13min
  before pinned SSH accepted commands; observed eMMC errors0/fallbacks0 throughout.
- Worker72449/held shell74871 completed new audit/graphics97c-device checks.
  Actual kernel UUID97 and sessionflags1f5/multiuser0 verified. All3 reviewed
  helper uploads byte-for-byte verified. Actual mobile two-process IOSurface
  test PASSES all512 shared bytes, lookup1, child exit0. This is a phone result.
- Named LCD remote-layer still transparent before/after, contextID833566179,
  exit1 without crash, context invalidated. No visible marker claimed.
- Bounded read-only backboard57 snapshot: actual slide4ea3c000, server exists,
 4 displays. Verified NSArrayM metadata/layout in exact preserved cache. First
  expected-vtable guard stopped: real class vtable1d5b45c68, NOT guessed oldbase.
  Decoded its slot180 ->18835cc54 with CPU fallback1884ebcc0, then separate
  backend2 snapshot supports this verified subclass. Original stopped outputs kept.
- LCD (exact nameCFString1d5b59178) has2 render clients, flags3, nonzero cached
  software renderer/wrapper; both contexts have nonzero rootIDs/cached roots.
  Other3 displays each have1 client. This rules out empty LCD list in this snapshot.
- Crucial probe limitation: stock backboardd signature has QuartzCore
  displayable-context/global-capture entitlements; previous helper had neither.
  BOTH exact key strings exist in preserved QuartzCore. Prior marker/capture
  results cannot yet exclude authorization filtering. Updated diagnostic workflow
  grants ONLY these2 keys to render helper, verifies signed entitlements exactly.
  No daemon/System/kernel change. Rebuild/retest pending; shell remains usable.

## Surface IPC candidate authenticated; empty-list capture can succeed (2026-11-03 Minsk)

- Source d3b8f817c6f496df8d2bcd875c1bfb4b1a64e104, CI41622795476 /
  job125872489652 ALL steps passed, including actual two-process IOSurface data
  assertion on native CI runner and signed arm64 iOS build/platform/ISA checks.
  Artifact13224571482 ZIP101869B SHAd3b4f8d6a9052901d8afe8ff073735e124ed369bff2d2b7eb6642879f758db46.
- Download length/digest/CRC, report source/both binary digests/lengths, platform,
  ISA checked; new IPC strict signature verified locally. Private graphics-v98/ipc98.
  IPC binary88176B SHA18d9f84e8e443985c277663aa2d65bf7da8d942e79b49f862fa3894fd6d9484e.
  Bundled named-render binary92080B SHA8afa15198474c715fae0318e3bbf4a741e616585eb9636d38f4c7ab602b17052.
  Native CI record: child registered_ports3, lookup1 initial_pixelsPASS, parent
  shared_pixelsPASS512B. NOT a phone result. No upload/flash/SSH/serial calls.
- Offline capture-event1884ee784 FIRST sets request+60 bit8 (handled/success),
  THEN tests concrete server+80 render-client count. Zero branches to unlock/return
  at1884ee830 WITHOUT renderer construction/drawing. Work188469360 returns0
  on the set bit; MIG reply succeeds and public wrapper normalizes nonzero
  result to accepted1. Thus an empty display client list can produce our exact
  accepted-but-transparent result. This is a demonstrated code path, not an
  observation that the phone's list was actually empty.
- Prioritize bounded read-only concrete display-server+70 list/+80 count alongside
  context routing and cached software renderer+c0/c8. Do not infer GPU failure
  or clear update gates before checking this. Presentation gate effect on capture
  still unproven. Kernel GetID0 supports, but doesn't prove, original context route.
- Existing framebuffer callbacks were reviewed: notification arrays are per user
  client and VSYNC type5 matches stock wrapper. No claimed new driver fix from
  those checks. Graphics remains unresolved; prepared tests require returned phone.

## CPU capture path traced; cross-process surface test added offline (2026-11-03 Minsk)

- Exact capture IPC40221 (reply40321) resolves from QuartzCore MIG subsystem
  40200..40281 at1d5b34750, routine21 stub1885423ec ->1884691ac ->188469360
  ->event20. CADisplayServer registers event20 callback1884ee784. Its concrete
  virtual render-to-target slot180 ->1884ebcc0 ->1884ebd68 allocates software
  renderer4fe0 with EXACT SAME vtable1d5b3d618 as software callback constructor.
  Thus lack of EAGL alone DOES NOT explain the measured empty capture. Private
  capture-event/renderer/MIG disassembly remains outside Git. Update gate still
  unresolved; no proof that a startup presentation gate blocks this capture path.
- Existing framebuffer GetID returns0; the earlier ID0 route is plausible, not
  a proven defect. Named LCD comparison remains useful for actual identity proof.
- Added tools/whyred-surface-ipc.m: parent creates own8x8 stride64 surface, passes
  its Mach send right to separately spawned executable, child looks it up and
  validates/replaces512 bytes, parent validates all changes. No display/service/
  filesystem modifications. Child-only registered port via exact local XNU spawn
  declaration; real bootstrap untouched. All IPC and child waits bounded.
- Native warning-clean fallback-declaration build and actual two-process test
  PASS. Initial bootstrap-channel prototype and incorrect count==1 assumption
  failed locally; final uses registered ports (mach_ports_lookup returns3) and
  accepts slot0 while releasing remaining lookup rights. These failures are host
  helper development results, not handset/kernel failures. CI/iOS build pending.
- Native CI adds actual cross-process pixel assertion, signed iOS helper,
  platform/ISA/signature/digest report. No phone commands; user has the handset.

## Signed named-route candidate ready; startup update gate found (2026-11-03 Minsk)

- Public source54bf682ba00e66c770d885e4d2ce5eb8853fc353, CI41581070859 /
  job125735783858 all steps passed, including host display refusals and CPU tests.
  Artifact13206296406 ZIP63005B SHA31ab4e7bf2e15576c864cafaa26b831a93ea2c2b1790037aebb645c2d2cf8ac0.
  Binary92080B SHAfd68b46a56e827ef05655046c6bc255388e9d9668f9d6407c436275c1afe601a.
  ZIP digest/length/CRC, report source/binary digest/length, iOS platform, ISA and
  strict signature verified. Private graphics-v98/named98. NO upload/device test.
- Offline stock backboardd path10001d8ec passes true for exported
  kCAWindowServerDisableUpdatesOnMainDisplay to serverWithOptions:, then sets
  rendererFlags3. Exact ObjC stub selectors verified from preserved binary:
  10009c360=serverWithOptions:,10009e440=setRendererFlags:,
  10009cfc0=setDisablesUpdates:,1000978c0=disablesUpdates.
- Overlay handling around1000825d8/1000826d0 logs disabling/enabling framebuffer
  changes and calls setDisablesUpdates:. Thus startup deliberately gates updates;
  actual current gate state is UNKNOWN. It may explain no presentation, but has
  not been shown to explain empty server captures. Do not blindly clear it or
  claim renderer/GPU diagnosis from this path. Next read-only server snapshot
  should include the real display's update gate and display/context identity.
- User's offline-only constraint remains active; installed boot97/System95
  unchanged. Source/native/CI checks do not establish a physical graphics repair.

## Named LCD context comparison prepared offline (2026-11-03 Minsk)

- Still no phone commands; user retains the handset. Original remote marker used
  display ID0, while capture targets LCD by name. Their equivalence was never
  measured; an empty marker capture cannot by itself prove renderer failure.
- Added remote-layer-lcd with exact exported kCAContextDisplayName and LCD,
  retaining remote-layer ID0 for controlled comparison. Both now verify the
  runtime contextId ABI and print actual context ID. Finally invalidation remains.
  No renderer flag, daemon, System or boot changes. This is a diagnostic candidate,
  NOT an observed graphics repair or proof that ID0 was wrong.
- Native and simulator capture/remote commands now refuse before accessing a
  display. Warning-clean native build with iOS IOSurface declaration fallback,
  all3 host refusals and exact CPU layer/surface preservation checks pass.
  CI workflow now executes those checks. Signed iOS build/device execution pending.
- Further offline investigation: no direct intra-QuartzCore callers to exported
  CARenderOGLNew/_New_ or software callback constructor were found (except wrapper
  forwarding); this limited scan does not prove absence of indirect/cross-image
  use. Private context-init and renderer-caller slices retained outside git.

## Offline graphics investigation; phone taken by user (2026-11-03 Minsk)

- User explicitly requested work without the phone. No subsequent phone commands,
  SSH uploads or flashes. Local observer25904/shell27792 were already gone when
  checked. Latest97b status: failed, samples27, last state0, SSH exit255. This
  coincides with user taking the device; do not classify it as a new spontaneous
  kernel/storage fault or a completed65min test. Passive UDP receiver may stay.
  Private graphics-v98/user-offline-request.json preserves the boundary.
- Authenticated read-only diag source4ead866d66553908e9f02f314441489832c9db48:
  CI41531195903/job125571544548 all steps passed. Artifact13181273512 ZIP62132B
  SHA2780c262495e7f7d6e092a28fbe864e29de9889fd8a20395118f0fc1c7f764e1;
  binary72960B SHAa9ebd0d26b2f36a34ee28b8b53c4cafe457661a8d9e28e77f9a813fd10993c5c.
  ZIP length/digest/CRC, report source/binary digest/length and strict signature
  verified locally. Prepared graphics-v98/diag-region98; NOT uploaded/run on phone.
- Offline display-discovery decode found exactly3 type-specific inventory paths,
  not3 established renderer engines. Factory1883a3320 chooses LCD/TVOut using
  display+9f2 bit8, set by display type; not a software bit. Concrete external-
  update vtable slot58 ->1884f7d38 toggles display+251 bit80. Base slot is no-op.
  No supported persistent software-server configuration has yet been established.
- Exact saved lsd return chain19c54d6e4/d910/d320 ->19c547214 identifies an
  IONetworkController wait, names sdio/wlan/marconi-wifi, caller timeout5seconds.
  CFRunLoop imports resolved exactly, not nearest redacted export. The outer
  semaphore wait is worker synchronization, not proof of an infinite MG query.
  Missing ADT product/options are NOT the matching target of this saved sample.
- Added WHYRED-GRAPHICS-STATUS.md with measured boundaries, guarded backend paths
  and next bounded read-only experiment. No graphics fix claimed and no new
  image built. Next actual hardware step only after user returns the phone:
  cache identity/slide -> actual server global/object/vtable -> backend/context
  routing, before proposing state mutation. Private disassembly remains outside git.

## Remote marker failed to reach server capture; read-only backend inspection prepared (2026-11-03 Minsk)

- User explicitly requested continued graphics work. Exact remote-layer probe
  source056181479a063781a173918ad829bd7ec6a59be1 from CI41530546994/artifact13182076347
  ZIP66842B SHA56ae641531f7026fd9a9027c8e92990db4a414d031b482851826fae4bc577b1c;
  binary92048B SHA2a22ff0b9e96451dad0c21cf3d0cb801f9a62999fd4ce770f409a87baefa9904.
  Signature/iOS/ISA/CRC/length and exact upload/readback verified. Worker29221
  complete21:42:29Z: CAContext created,32x32 red layer submitted, before/after
  capture accepted1 but RGB/alpha/marker all0. Context invalidated in finally.
  No rendered marker or stock UI repair claimed. audit/remote98-check/device.
- Runtime method ABI checks passed for factory/setLayer/invalidate; setLevel
  called ONLY for verified float ABI. No guessed renderer flags or server memory
  writes. Actual new context failing to appear suggests server remote composition
  path needs investigation; empty capture alone doesn't prove a unique cause.
- Read-only unsuspended SpringBoard26/Backboard57/lsd96 thread samples private.
  SpringBoard main waits through CoreServices; another thread waits synchronously
  on XPC from CoreServices/Foundation. No identity of the waited-on service yet.
  Correct shared cache slide30728000 confirmed by TWO exact kernel anchors:
  workq_kernreturn+8 and ulock_wait+8. Earlier hand-calculated30628000 was wrong
  and discarded before any claimed diagnosis; corrected private symbolication.
- CAWindowServer serverIfRunning is an exact load from shared global1dcf3c160;
  planned inspection reads the actual backboardd task/global/object/vtable only.
  Added bounded read-only whyreddiag cache PID and region PID ADDRESS LENGTH<=4096,
  no task suspend/write. task_cache reads actual dyld all-image-info shared slide
  before using addresses. Native warning-clean build, actual self task-cache/read
  and7 malformed/overflow/negative/size cases pass. Signed iOS CI/device pending.
- Current installed97/System95 and observer25904/shell27792 untouched. Graphics
  remains active. Next authenticate helper, inspect server backend pointers/flags
  from read-only snapshots, then decode actual backend choice. Don't fabricate
  accelerator support, blindly switch bits, or present a test marker as iOS UI.

## Actual97b server capture completed: accepted but transparent/empty (2026-11-03 Minsk)

- User asked to act now. TCP was initially refused while cold CMD17 startup read
  ~803MB. Once available, pinned SSH authenticated on first attempt. Running97
  UUID/sessionUID501 and75 xattrs verified again; observer25904/shell27792 active.
- Stopped ONLY waiting capture worker25936 before it performed any upload, then
  started worker27563/check_capture98c.py after verified97 UUID, without waiting
  for duplicate file controls. Distinct audit/capture98c outputs preserved.
- Actual signed upload/readback pass. Methods command returns0 with runtime
  signatures/implementation offsets; capture returns1 only because pixels empty:
  CARenderServerRenderDisplay accepted=1, RGB0/alpha0 of2740500. No crash/timeout,
  no screen mutation. Completed21:34:50Z. Existing CPU layer/surface proofs pass.
- Runtime method offsets(relative QuartzCore base18827b000) now resolve exact
  setters: CAWindowServer setRendererFlags25f430 ORs caller flags with3 and copies
  to each CADisplayServer+0xb8. This is not yet a decoded software-switch bitmask;
  do not write guessed bits. beginExternalUpdate:usingSoftwareRenderer:264b88
  dispatches bool through server vtable+0x58, then update throughvtable+0x10.
  Private disassembly graphics-v98/server-flags,display-flags,external-update.
- Empty accepted server capture localizes the observed empty frame before panel
  copying, but doesn't alone distinguish empty context tree from unavailable
  renderer. No stock UI repair claimed. Next decode actual server backend/context
  selection with new method addresses and inspect UI context availability.
- No flash/System/driver/framework bytes changed; graphics task continues.
  Prior97 SSH hang separate. Read97b observer/capture98c results before more work.

## User confirmed ordinary reboot; distinct97b observers running (2026-11-03 Minsk)

- User rebooted phone normally. No flash. New observer25904 uses existing97
  manifest and distinct audit/kernel97b-observer.json/log/device, confirmation
  audit/kernel97b-user-reboot.json. Log boundary9537568 preserved before reboot;
  fresh reset I/O counters/early foreground success observed. Old97 failed
  outputs remain immutable. No duplicate old observer or concurrent FIFO use.
- Renderer capture worker25936 ssh-v90/check_capture98b.py waits for new97b
  baseline then uploads verified source96ece6f4 capture helper and runs methods/
  capture commands as mobile. Existing graphics-v98/capture98 artifact unchanged.
  Status audit/capture98b-check.json/log/device. Do not duplicate this worker.
- Through early new boot~21:25Z,302MB errors0/fallbacks0, foreground setter works.
  SSH still starting; no UUID/session/read baseline or capture result from this
  new run yet. Continue reading both statuses before action; no new reboot
  needed while startup progresses. Previous ordinary97 watch failed before65min.
- Graphics remains an active repair task: CPU layer and IOSurface proved, real
  display/server capture pending. Do not call offscreen test rectangles a working
  stock interface. No System/driver/framework modifications deployed for graphics.

## Current97 SSH hang blocks next graphics probes; ordinary reboot requested (2026-11-03 Minsk)

- ACTUAL IOSurface CPU probe passed at21:09:23Z: create16x16/stride64, lock/map,
  CALayer192red+64green exact pixels, unlock/relock preserve all1024 bytes. Worker
 23548 complete; audit/surface98-check.json/device. No screen/server mutation.
- Next capture helper source96ece6f4d80dfd0ff230c47a00fc1c353cf7dae4, CI41525632566,
  artifact13178494206 ZIP57570B SHA40a2b30b897969082e3ede619219268261fa2d51e2d5be0e245057c067a29298;
  binary91168B SHA52d964f0ed119d16d3053b63466380023caf8293e3583cb1c76ae530e336ecd7.
  Signature/iOS/ISA/CRC/length verified under graphics-v98/capture98. Its upload
  NEVER received first SCP acknowledgement; worker24031 failed before payload,
  so neither methods nor capture command ran. No device graphics result here.
- New SSH probe establishes TCP but times out BEFORE server version/banner,
  before key offer/auth. Thus this is not a measured bad-key rejection. Original
  observer17023 ALSO ended phase failed: retained-shell command got BEGIN but
  no END within180s, samples28. Last complete state21:10:04Z: VMfree1802 pages,
  wired16099/compressor384; RAMFSfree3500/8192, not data quota. No concurrent FIFO
  commands were issued. Held SSH shell19005 may retain a stuck remote child.
- UDP still supplies SpringBoard/USB lines. No current EMMC recovery/APFS/EIO/
  RAMFS pressure/panic captured. Last I/O1.388GB errors0/fallbacks0. Separately,
  genuine mediaserverd28 again hit the known NULL CoreImage callback; distinguish
  it from diagnostic process185. Do not claim storage fully fixed or attribute
  this new hang to the old CMD12 latch without evidence.65min watch incomplete.
- Private immutable cut audit/kernel97-full-review/ssh-hang-summary.json/log,
  graphics-v98/restart-request-boundary.json and ssh-login-check stderr stages.
- Asked user for an ordinary power reboot to continue graphics checks (or report
  Fastboot if already there). Await actual reply; no new flash is required to
  run the existing97 kernel. Do not restart old observers/overwrite old outputs.
  Prepare distinct97b output/baseline only after user confirms the new boot.
- Graphics still open: real CPU layer and owned IOSurface work; need server
  snapshot/root-layer composition and framebuffer delivery. No fake GPU, service
  disable, System rewrite, framework byte patch or guessed renderer flags made.

## Graphics server capture investigation (2026-11-03 Minsk)

- Read actual /usr/libexec/backboardd over pinned SSH to private graphics-v98;
  no device writes. Its screenshot call at0x10001e974 invokes the exact imported
  CARenderServerRenderDisplay with port0/display name/ownIOSurface/int0/int0,
  between lock/unlock. QuartzCore wrapper at0x188470e40 returns normalized bool.
- Added explicit capture diagnostic with that five-argument ABI, own1125x2436
  BGRA surface, no display swap. Reports accepted/RGB/alpha counts only. Native
  warning-clean compile; NOT run against the Mac display. iOS CI/device pending.
  Root/mobile privilege differences and server renderer capabilities remain open.
- Added read-only renderer methods diagnostic (source32fcf2a): runtime signatures
  and implementation offsets for CAWindowServer/CAWindowServerDisplay/CARenderer,
  bounded128 matches/class. No guessed private setters invoked. CI41525363634
  produced artifact13178913579, not yet downloaded/physically tested.
- Surface helper corrected-header CI41525233629 artifact13179636649 ZIP46978B
  SHAabad646e2d0c8e9c7f8afc53c0abf63906b9e1d47f5e7178f49762b0eb036752;
  binary90240B SHA6c03f65739617cbb734cafc98bf0cc25b3b46af1f51ceaff7071635f57052cb0.
  Signature/iOS/ISA/CRC/length verified, worker23548 currently uploads exact helper,
  audit/surface98-check.json/device. Await actual result, don't duplicate it.
- No repair of the stock graphical scene claimed. Keep97 observer17023 and shell
  19005 untouched while separate bounded diagnostic SSH commands run. Current
  source capture addition is separate from already installed kernel97/System95.

## IOSurface diagnostic SDK declaration fix; not a device result (2026-11-03 Minsk)

- Surface CI41524953675/job125550177453 failed before linking: iPhoneOS SDK has
  IOSurface dylib but no IOSurface/IOSurface.h. Native headers exist. Added a
  minimal ABI declaration fallback for the exact used C calls/keys. Forced
  fallback native build passes warnings-as-errors and actual surface/pixel/
  relock checks; no device/header failure has been hidden as a passing test.
- Rebuild signed surface helper next. No new kernel/System/phone reboot. Actual
  layer98 result remains passed; surface result still pending. Keep97 observer.

## Actual QuartzCore CPU layer probe passed on97; shared-surface probe next (2026-11-03 Minsk)

- Signed layer diagnostic source8bb6b3ed2ef832f0a17d93d25621600f80de0c4e,
  CI41524505780/job125548647347, artifact13177959738 ZIP40576B
  SHA f0fccf3599fa03a1acd4ab2b313591b4bc26467afafa52fd9afbe5210459d0a0.
  Binary89040B SHA517df605372eb54fca576639d7705fcc4f60f46dec1bb313a68c847a8cecc4d0.
  Archive/signature/iOS/ISA/size verified, exact upload/readback pass. Worker22527
  complete at21:02:15Z: ACTUAL97 CALayer CPU drawing returns0,192red+64green pixels
  exactly match. audit/layer98-check.json/device. No display/System mutation.
- This proves the real QuartzCore CPU layer rasterizer works on this phone,
  independently of unavailable EAGL/CoreImage. Stock SpringBoard scene/display
  still unconfirmed/unfixed. Must bridge real compositor updates to framebuffer,
  not substitute test rectangles and call that a working iOS interface.
- Added explicit surface probe to create its own16x16 IOSurface, lock/map it,
  render identical CALayer tree into it, unlock/relock and require preserved
  bytes. No display swap, shared server mutation or file writes. Native exact
  pixels and preserved1024 bytes pass, warning-clean. Signed CI/device pending.
- Exact software destination ABI investigated privately: renderer vtable+0x3d0
  reaches CPU implementation0x18843cbfc, storing destination/stride/bpp/second
  buffer/offset/size fields. No guessed private ABI invoked on phone. Quartz
  renderer-info error path is server IPC, not automatically IOMFB selector57.
  Keep observations separate; do not alter selector contracts speculatively.
- Installed97/System95, observer17023/held shell19005/UDP47443 unchanged. At
  21:01:41Z sample18 and3 direct health checks pass;1.382GB errors0/fallbacks0,
  no RAMFS pressure/APFS/panic/latch, only the earlier explicit CI diagnostic
  crash. System target PIDs stable; trial65min not yet complete.

## Graphics work: exact renderer selection and QuartzCore CPU path (2026-11-03 Minsk)

- User explicitly requested graphics repair while97 longrun continues. No reboot,
  new image or framebuffer overwrite. Observer17023 still monitoring; read status.
- Exact CoreImage initWithOptions removes UseSoftwareRenderer on this iOS path,
  tries Metal then falls back into EAGL context creation. No working CPU CoreImage
  selection established. CA_NO_ACCEL only controls backing allocation; do not
  mistake it for a proven server software-compositor switch. CA_ENABLE_OGL is
  renderer capability state, not yet a validated fallback repair. No system env
  changes or binary/framework patches made based on these names.
- QuartzCore exports real kCARenderSoftwareCallbacks/CARenderSoftwareSetDestination;
  software constructor allocates0x4fe0 bytes and installs its own vtable. This
  is a separate implementation worth testing, not a fake accelerator. Exact
  cache analysis/disassembly remains private under graphics-v98.
- Extended explicit render helper with layer command: public CALayer renderInContext
  into16x16 CPU CGContext, red parent/green child. Native compile warning-clean;
  192red+64green exact pixels pass using shared sRGB. Device test pending. No
  window/server mutation or writes in this command. CI links QuartzCore explicitly.
- Next validate same signed layer probe on97. If actual CPU layer drawing works,
  investigate bridging the real software compositor to display/context updates.
  A successful local layer bitmap alone is not repaired SpringBoard or CoreImage.

## Actual97 session/xattrs/read controls pass; isolated graphics failure reproduced (2026-11-02)

- Running97 UUID1444AADE-E57B-3F55-88A9-866FFA6086A0 matches packaged kernel.
  Real iOS session getters BOTH return0; raw flags0x1f5=UID501, multiuser0.
  This plus early usermanagerd success physically validates the0174 setter fix.
  All75 actual xattr checks and12 cached/F_NOCACHE/mmap length/hash controls pass;
  all3 installed95 job/cache files read back exactly. No forbidden job spawns.
- Observer17023 is now phase monitoring, held shell19005. Keep65min natural
  observation; don't issue concurrent FIFO commands. Current early success is
  not proof the previous38/44min eMMC failures are fully fixed. CMD17-only trial
  remains a mitigation, batching still disabled. Read current observer first.
- Renderer worker17947 COMPLETE at20:48:17Z, exact signed upload/readback pass.
  EAGL2 AND EAGL3 both return nil/current0. Explicit CoreImage software request
  SIGSEGVs before context creation returns: output only software context begin,
  status139. Its own process whyred-render-f4 PID185 has pc0/lr0x1961ec58c,
  slide0x16d8000 -> exact same CoreImage0x194b1458c NULL callback as mediaserverd.
  Thus the software option did not avoid the unavailable GL dispatch in this
  iOS build; do not recommend a simple software-renderer toggle as a fix.
- This crash was the explicit diagnostic, not evidence of a new arbitrary
  system-daemon crash. No SpringBoard/mediaserverd disable, fake GPU, framework
  binary patch, System write or UART. Actual graphical scene remains unfixed.
  Need a supported renderer/context path; native Mac software256-pixel success
  does not establish the iOS path. Private audit/render97-device and status.
- Public source8c929fb is diagnostic-only after97 kernel source47524; installed
  kernel remains97/System95. NOTES-only source0c5745 recorded the earlier wait.
  Raw logs/Apple bytes/helpers/private keys stay outsideGit. Current log remains
  audit/current-whyred-usb.log, summary audit/kernel97-full-review/current-summary.
- Next: preserve longrun97; inspect new genuine system crashes/storage/pressure.
  Foreground fix,75 xattrs and initial read/config proofs are complete. Graphics,
  Data Protection, early notifyOPT_DISABLE8, legacy Jetsam command6, fresh boot
  entropy/reseed and persistent platform support remain separate open work.

## Boot97 early foreground success; renderer helper verified and waiting (2026-11-02)

- Actual97 USB early boot reports Set Foreground ID + multiuser in commpage
  successfully; prior FAILED line is absent. This confirms the setter path,
  but real userspace session flag readback/UUID are still pending SSH. Through
  20:41:43Z eMMC503.7MB/errors0/fallbacks0, no APFS/PRESSURE/crash/panic/latch.
  TCP reaches the phone but2222 currently refuses; dropbear exec was logged.
  Do not reset it during this baseline or interpret normal startup as a repair.
- Renderer diagnostic source8c929fb58ca5d64d13166fc1c73091ddddf21c76,
  CI41520788443/job125535941232 all7 steps pass. Artifact13176484526 ZIP31522B
  SHAf37e83fa127523bb15564ef554436f3d653e221063ae1d80f9da61ab9f1d9c09;
  binary88096B SHAf49cf77fdca5adb0d0bf6eb24b2b0257831194f20127a1bbfa2558b5a22276b8.
  Signature/iOS/ISA/length/CRC verified, kernel-v97-draft/render97. No claim of
  iOS software rendering success yet. Native256-pixel proof is separate.
- ONLY renderer worker17947 ssh-v90/check_render97.py waits for existing97
  observer17023 phase monitoring/verified UUID/config. It then uploads the
  reviewed helper to volatile tmp, verifies bytes and runs explicit software
  andEAGL probes as mobile through the reviewed30s-bounded helper. Uses its own
  SSH commands, never the observer FIFO. audit/render97-check.json/log/device.
  No partition changes or UART. Read both status files before continuing.
- Current read-only summary tool tools/summarize_kernel97.py records the exact
  original boot interval and header-only FSERR errno, without contacting phone.
  Output audit/kernel97-full-review/current-summary.json; UDP47443 unchanged.
- Next: verify actual97 UUID/session flags (UID501),75 xattrs,12 read controls,
  retained disabled jobs; inspect renderer results and preserve natural longrun.
  Remaining Data Protection/notify/Jetsam/PRNG/platform/UI issues remain open.

## Boot97 flashed after user ended96 trial; USB/SSH validation pending (2026-11-02)

- User reported a manual reboot to Fastboot and requested repairs. Exact phone
  readiness/product/unlocked/64MiB boot, source/kernel/System95 and rollback94
  guards passed. Actual sending/writing boot97 and reboot all returned OKAY at
  ~20:35:08Z. No System write. Installed now boot97/System95; do not ask again
  for the already consumed readiness answer or reflash this same image.
- Full97 CI41515301290/job125517210664/source47524d521237e9d50d84ba9d1b5e72806c5e13cd
  ALL27 steps succeeded. ZIP SHA/length/CRC, exact reviewed sources including
  host.c/commpage.c,960 actual host/updater checks and linked call/NULL rejection,
  retained ASan/UBSan suites, ISA/bootstrap/cache/idle/ADT/layout guards passed.
- Image port/out/whyred-ios-root-v97-foreground-41515301290/
  shim-boot-whyred-uartdm-debug.img,22347776B, SHA
  ebbcb2a0f159d89b1996c7471d8e0bf86976ac8645310b9428c769986db0da00;
  kernel SHAe6fd653a89391f50e58bc4a1edaece06c9022429877c87b0b8af9cc8bcebc4f3,
  expected UUID1444AADE-E57B-3F55-88A9-866FFA6086A0. XO/CMD17 only retained.
- ONLY new observer17023 ssh-v90/observe_kernel97.py, original offset9345783,
  audit/kernel97-observer.json/log/device. Requires97 UUID, reads session flags
  via real iOS getters,75 xattrs,12 read/mmap controls, actual95 job files then
  65min watch. Do not issue concurrent FIFO commands. UDP47443 unchanged; no UART.
- Signed session diagnostic CI41516654602/job125521825902 all7 steps pass.
  Artifact13174284723 ZIP54600B SHA3fdfbae3b1f8d4d9eca0609836f8259cc902c248ffd9bb4bfb3bdc7cc5d086a1;
  binary72592B SHAe74cdb1526999c8acbbb5ea698b6d31b4d60336c700129ea2d20b04e8c0d7130.
  Signature/iOS/ISA/imports verified; private kernel-v97-draft/diag97. Device
  session readback is pending, so don't claim foreground repaired on hardware yet.
- Final96: user interrupted before65min completion. Observer4706/shell7488 ended
  withSSH255 after reboot, not a captured storage latch. Final snapshot private
  audit/kernel96-full-review/final-summary.json/log/termination.json:32 samples,
  6 true direct health reads passed,1.318GB errors0/fallbacks0, no APFS/PRESSURE/
  panic/latch/recovery record. lsd94/pkd257/suggestd265 persisted. No target two
  job spawns. One mediaserverd28 NULL-PC graphics crash; replacement372 observed.
  Latest successful sample20:31:15Z, last IO report~30min after I/O startup. This
  incomplete exposure does NOT close the earlier38/44min physical eMMC failures.
- Exact CoreImage tracing now names _wrapEAGLContextCreate and _wrapGetMacroContext:
  API3 thenAPI2 context creation; a missing GL context leaves the zeroed callback
  table, later called unchecked. No GPU/service/binary workaround applied.
- Added explicit render probe: process-local16x16 red bitmap through requested
  CoreImage software renderer, separate EAGL2/3 creation/status command. No window,
  daemon change or files written by helper. Native warning-clean compile and all
  256 expected RGBA pixels pass. Signed iOS helper CI/device test pending; native
  success is not proof that iOS has a software renderer or SpringBoard fallback.

## Read-only session diagnostics prepared while boot96 observation continues (2026-11-02)

- Added whyreddiag session: uses real iOS libsyscall host_get_multiuser_config_flags
  and host_check_multiuser_mode getters, which read the commpage; no privileged
  setter, guessed-address access, process suspension or device write. Prints
  raw return codes/flags/mode so a97 device test can verify actual session state.
- Native helper compiles with warnings-as-errors, selftest/kernel and all75
  temporary-file xattr cases pass. Native macOS correctly reports NOT_SUPPORTED
  for both session getters; this is not an iOS/device success claim. Signed iOS
  helper CI and eventual on-device check remain pending.
- Kernel97 CI41515301290/source47524 remains building; installed boot96 watch4706
  continues undisturbed. No fresh partition write, reboot or UART. Private97
  packager prepared with exact0174 source/report and linked setter-call guards,
  retaining all96 packaging checks. No97 image has yet been packaged or flashed.

## Kernel97 foreground API candidate; installed96 still under observation (2026-11-02)

- ACTUAL boot96 validation through20:02:41Z: running UUID matches packaged
  BC9C2211-0018-3824-BC73-06DAAB42E274; all75 device xattr cases pass, all12
  cached/direct/mmap controls match expected bytes/hashes, all3 installed95
  job/cache files match. Zero forbidden job spawns. ~1.03GB CMD17 reads,
  errors0/fallbacks0; no current APFS/PRESSURE/recovery-latch record. This is
  early evidence only. Observer4706 now monitoring, held shell7488, samples2;
  raw/diag uploads verified. Read current status before any further action.
- SDK-isolation fix source47524d521237e9d50d84ba9d1b5e72806c5e13cd retriggers97
  CI41515301290. Candidate97 is NOT installed. Do not reflash96/97 merely because
  a new artifact appears; preserve this natural96 long-run exposure first.
- Copied96 observer initially reused the95 bootstrap-probe filenames; current
  probe metadata was archived under audit/kernel96-ssh-probe-*.json and the disk
  script corrected. Earlier95 state/control/config/device-failure proofs are
  intact, but do not use root-level system95-ssh-probe files for historical95
  attribution now. Main96 outputs were always separate in kernel96-device.
- Initial97 CI41514102825/job125513096438 failed BEFORE kernel compilation:
  the native pre-build test inherited the kernel-only SDKROOT and could not
  find stdio.h. No97 kernel was produced/deployed. The test now explicitly
  selects the native macOS SDK and clears inherited SDK/deployment variables,
  matching the existing eMMC host runner. Rebuild after this environment fix.
- Boot96 diagnostic now captured MCM's exact /dev query: common6, volume80060000,
  count5,64-byte buffer/options0 = DEVID/FSID/capabilities/UUID. Upstream devfs
  provides no volume UUID, so generic getattrlist returns EINVAL for it. Native
  macOS reproduces22 with this exact query; removing UUID succeeds. This specific
  /dev probe is expected unsupported behavior, not a container write/crash cause.
  Other EINVAL calls, e.g. /tmp, must still be evaluated on their own masks.
- User's repair work continues while the actual boot96/System95 observation
  runs. Patch0174 narrowly enables the real host_set_multiuser_config_flags
  implementation on SWEET despite the macOS target configuration. Preserves
  NULL privileged-host rejection and writes the real commpage flags through
  the existing updater; other macOS boards/SWEET=0 keep NOT_SUPPORTED.
- Local ARM64 host.c compile with the actual authenticated96 compile command
  passes. New actual-function/updater host suite passes960 checks across5
  target configurations with UBSan; old source fails the SWEET/macOS case.
  Private kernel-v97-draft. This is not deployed or physically validated yet.
- Full kernel CI will include this check before compilation and preserve its
  report. No new device write/reboot, no new observer: boot96 watch4706 and
  UDP47443 continue. The new candidate retains all96 fixes; do not replace the
  running96 trial prematurely or claim the session failure fixed on hardware.
- Actual96 UUID/xattr/direct-read results are still pending at this milestone.
  Next inspect audit/kernel96-observer.json before any further physical action.

## Boot96 flashed, System95 retained; automated validation pending (2026-11-02)

- User freshly confirmed Fastboot. Exact-device/product/unlocked/boot64MiB,
  image/kernel/source/System95 proof and rollback94 guards passed. Actual
  fastboot flash boot AND reboot returned OKAY at~19:48:30Z. No System write.
  Private audit/kernel96-flash.json and audit/kernel96-preflight.json.
- Final kernel source b9e8aa455053478c4c785610e632a746b16c419c, full CI41509382660
  /job125499618939 ALL27 steps successful including ASan/UBSan. Initial8a95 CI
 41508019427 was superseded. Downloaded ZIP SHA256s match official artifact
  digests and exact build source, retained suites, ISA/no-LSE/no-PAN, bootstrap,
  cache/idle paths, splash, ADT/payload/stock DTB/layout guards all pass.
- Boot image port/out/whyred-ios-root-v96-xattr-recovery-41509382660/
  shim-boot-whyred-uartdm-debug.img,22347776 bytes SHA
  8680c3993b2cb8935377c18410479ffba4c7668c70430da1ecd553c83f510f24.
  Kernel SHA fc0536cc2c98e952fb334e15a1d4ad38e63695d9e2228cb26c3013ab35709649;
  expected running UUID BC9C2211-0018-3824-BC73-06DAAB42E274.
- IMPORTANT trial policy: whyred-emmc-fast=1 BUT whyred-emmc-multi=0. Both
  natural boot94 failures began with batch read failure, so next stability test
  retains validated XO frequency with CMD17 only. New STOP recovery is tested
  in the model, not yet physically proven; avoiding batches is a mitigation,
  not evidence that the entire hardware fault was repaired. System95 stays.
- New ONLY observer4706 (ssh-v90/observe_kernel96.py), audit/kernel96-observer
  .json/.log, offset9153114, output audit/kernel96-device. It requires actual
  UUID match, then75+ opt-in temporary-file xattr checks,12 cached/direct/mmap
  controls, installed95 configurations and prolonged65min observation. Do not
  issue simultaneous FIFO commands or duplicate it. UDP47443 still collects
  audit/dsc89-usb-session.log; UART never opened. Prior95 observer finished
  captured-first-error-session-retained at39samples and is not still monitoring.
- Signed diagnostic25c9d22 source from CI41508866433/job125495161075 ALL7 steps
  pass; ZIP SHA a76092c5fce79252cc1a2bb9362e23156c73508cb631008fe1a44bff1fbe307f,
  binary kernel-v96/diag96/whyreddiag SHA
  25bd35333ea3fe8c5553e6ea0eb4f8b44d43f67041f64a8095e4c65884b895ce.
  Native75 xattr cases pass, iOS signature/platform/ISA verified. Not yet a
  device test result. Private readiness/packager/proofs under kernel-v96.
- Independent next findings: host_set_multiuser_config_flags in host.c returns
  NOT_SUPPORTED in this macOS build; real commpage updater exists. Private
  kernel-v97-draft contains a narrow SWEET-gate draft and4-config UBSan checks,
  not shipped/committed. Exact launchd disassembly calls legacy memory command6
  (fatal task limit), excluded with CONFIG_JETSAM0, not merely command5 soft HWM.
  Review actual ledger/PID1 consequences before exposing it. Do not enable
  global jetsam or fabricate success just to silence this message.
- Next: read kernel96 observer first. Confirm UUID/xattrs/reads/95 jobs, preserve
  first recovery snapshot if storage fails, collect attrlist masks. Only then
  proceed with session/graphics/container work. Do not reflash System95 or ask
  the same Fastboot readiness again for this already completed boot96 flash.

## Kernel96 candidate: xattr snapshots, STOP timeout recovery, attr masks (2026-11-02)

- System95 naturally reproduced the storage failure at19:17:51Z (~44min boot),
  after39 samples: CMD18 failed, first recovery passed, baseline clock restored,
  CMD17 PIO stayed incomplete with DATA_AVAILABLE, second STOP timed out, then
  permanent EIO and mass SIGBUS. All4 F_NOCACHE controls fail; several cached
  controls still pass. Observer finished captured-first-error-session-retained,
  shell90517 retained, no new dynamic SSH probes needed. Evidence is private
  audit/system95-device and kernel-v96/system95-transport-first-error.txt.
  Neither disabled daemon launched; their removal did not repair lower I/O.
- Following that new evidence, final0172 also preserves pre-reset Qualcomm
  FIFO route/data counters/clock/DLL snapshots (at most8 recovery entries).
  An alternative FIFO-route reset is only a hypothesis; no unproven register
  policy is changed. Rebuild is necessary to retain the state before erasure;
  the initial CI below is superseded by this final kernel source update.
- Kernel source8a95ca56679e8be290c6119fb31820b9b64efbc0 is building in full CI
 41508019427/job125492212913, required pre-build source checks passed. Private
  v96 packager retains all prior guards and requires System95; artifact/device
  validation pending. Later NOTES/diagnostic-only commits do not replace the
  exact kernel build commit or cancel its workflow.
- Diagnostic helper adds read-only kern.uuid for matching the actually running
  image and explicit xattrs DIRECTORY probe (one mkstemp file, max16KiB values,
  removes it afterwards). Native75 set/size/read/list/shrink/remove/ERANGE checks
  pass, normal sampler remains read-only. Separate signed iOS helper CI pending;
  no helper/device probe has been deployed during the current observation.
- Exact-cache symbolication of the later mediaserverd failures places the
  NULL indirect call in CoreImage, reached from CMCapture. Disassembly loads a
  zero callback from a stack dispatch table while preparing GL state. This is
  evidence for a graphics-context/dispatch problem, not a proven Bluetooth or
  FairPlay dependency. Local IDA HTTP endpoint is currently unavailable; local
  cache bytes/disassembly and decoded frames remain private under kernel-v96.
- User authorized proceeding with repairs after the current-run audit. Candidate
  kernel96 changes ONLY kernel source/tests; installed boot94/System95 remains
  running under the original observer/UDP collector, no new flash or UART.
- Patch0171 removes nonblocking snapshot allocation under the RAMFS mutex from
  getxattr/listxattr. Allocate with waiting allowed outside the lock, re-find and
  re-size under it, copy a stable private snapshot, free by allocation capacity.
  Handles growth/shrink/replacement/removal and copyout faults without holding
  the mutex over allocation/user access. Quota and honest protection policy stay.
- Patch0172 resets CMD+DATA again after STOP timeout before attempting status;
  prior recovery ignored STOP failure then waited on latched CMD_INHIBIT. At
  most2 stop/status attempts, require clean R1/READY/TRAN plus idle host/FIFO,
  then reread. No failed bytes accepted or media/config writes introduced.
  This repairs a reproducible recovery defect, not yet the entire physical-I/O
  root cause. Actual long-run hardware verification is still required.
- Patch0173 adds bounded best-effort24-byte attrlist masks/options/length to
  existing EINVAL trace for get/fget/getat/bulk. Copy failures print zero masks
  plus their own copy error; no syscall result or user output buffer changes.
  Needed to establish the unexplained /dev and later /tmp EINVAL branch.
- Local checks pass1120236 RAMFS cases with UBSan and4792 modeled eMMC cases;
 144 trace checks/90 syscall descriptors/2 return hooks. New fixtures fail on
  old RAMFS/eMMC source. ARM64 RAMFS/eMMC single-file compiles pass with actual
  generated headers; all3 patches replay exactly with fuzz0. Private kernel-v96.
  Local ASan runtime traps before main even for an empty program; plain/UBSan
  work. Full CI's ASan checks must still pass before packaging kernel96.
- Current observer reached32samples with no storage latch/APFS failure; later
  current log now contains a mediaserverd NULL-PC SIGSEGV, plus SpringBoard
  layer/layout warnings and unsupported AKS selector8. Preserve these as new
  follow-on evidence; prior audit was a timestamped earlier slice. Do not claim
  current whole-run crash-free or diagnose the NULL-PC callback without symbols.
- Next: full kernel CI and authenticated packaging, then new-boot validation
  when physically ready. Keep65min existing observation until it completes or
  captures first storage failure; do not prematurely reset to shorten testing.

## Current boot94/System95 log audit and repair queue (2026-11-02)

- User requested a complete current-run error review/list, not another fix or
  flash. Reviewed all1826 available USB lines through18:55:41Z (21:55 Minsk),
  157892 bytes from original offset7987522. Pre-USB kernel startup is unavailable
  without UART; UDP/interleaved text is not lossless proof. Also read the entire
  current MCM text log and both OTA reports, plus18 process/memory samples.
  Private report audit/system95-full-review/REPAIR-LIST.md, immutable log/hash,
  all78 FSERR events, state summary and additional logs. No raw logs committed.
- Current confirmed RAMFS event is one68-byte getxattr NOWAIT allocation failure,
  not data quota: event resident578/8192 pages, prior peak1064, quota/page/slot
  failures0. Code allocates the xattr snapshot under rm_lock with Z_NOWAIT and
  returns ENOMEM on failure. Need safe allocation/revalidation outside the lock;
  do not use waiting allocation under it or raise quota based on this event.
  Add bounded caller/xattr identity; global OOM and affected client are unproven.
- MCM log contains99 repeated unsupported container Data Protection errors.
  Eight FSERR45 calls (MCM6/calaccessd2) really request F_SETPROTECTIONCLASS64;
  current RAMFS has no CPROTECT/SEP. Need a truthful unprotected-mode contract
  and client container tests; never claim encryption or fake successful class
  support. Two profiled AKS selector31 unsupported results remain to interpret.
- Graphics: repeated absent accelerator/scaler/backlight matches; ALL3 submitted
  source surfaces have zero RGB/alpha, final panel zero too. Copying frames is
  insufficient: investigate compositor rendering/fallback and advertised caps.
  Additional open checks: exact devfs attrlist masks for3 EINVAL calls; early
  foreground/commpage + persona notifications; launchd Jetsam request EINVAL;
  PRNG seed/reseed interfaces; specific privilege denials, not blanket grants.
- Storage/platform update path is incomplete: volatile Data, absent expected
  options/storage IORegistry nodes and Preboot mount cause two OTA restore
  diagnostic reports, not two application crashes. Prioritize core storage/UI
  before OTA; trust-cache development warnings and duplicate gamepad classes
  are separate limitations/noise, not current crash proof. Most FSERRs are
  startup probes:54 ENOENT/10 EEXIST/8 ENOTSUP/3 EINVAL/3 EPERM. Temp/Data paths
  now exist; cleanup completed, so those transient path failures are not proven
  persistent defects. Parse errno only in the header, never copy_errno fields.
- Current slice has no crash/panic/APFS error/permanent-I/O latch/ENOSPC;
  eMMC1.297GB errors0/fallbacks0, all12 early controls plus3 later direct health
  reads pass. Latest RAMFS3501/8192 pages, VM free7191 pages; growth alone does
  not establish a leak. MCM/lsd/pkd/suggestd PIDs persist; disabled two jobs
  remain absent. This22-minute observation DOES NOT close the previous boot94
  CMD12 recovery failure at~38min. That is still the P0 prior-run blocker.
- No new device writes/reboot/UART. Original observer88567, shell90517, UDP47443
  continue, phase monitoring at18samples; do not start duplicate collectors.
  Next: inspect their final/current evidence, then repair eMMC recovery based on
  its first failure, RAMFS xattr, container contract and rendering in that order.
  Commit ae87319 is the audit's source baseline; this milestone changes NOTES
  only, so no new build or tests are warranted. Installed boot94/System95 stay.

## System95 policy verified on phone; MCM EINVAL checked (2026-11-02)

- Installed boot94/System95, all81 System transfers/reboot OKAY. Pinned root SSH
  works (held shell90517). Reviewed volatile raw/diag uploads and full readbacks
  pass. All12 early cached/direct/mapped controls pass. ALL3 actual installed
  plist/cache files read back byte-for-byte equal to the verified95 overlays.
- Through18:44:28Z, zero exec/spawn records for bluetoothd or fairplayd.H2, and
  neither process appears in3 consecutive PS samples. Both requested jobs are
  disabled, no fake processes/endpoints. Private audit/system95-policy-result.json.
  Other529 cached job definitions and all unchanged System91 bytes preserved.
- User asks about containermanagerd errno22: current first trace is getattrlist
  on /dev with64-byte result buffer/options0, not a container metadata write.
  Same process65 continues subsequent calls and is alive in all3 samples; no
  MCM crash captured. Exact attribute masks are NOT in the current trace, so
  the particular EINVAL branch/cause remains unknown. Do not suppress EINVAL or
  fabricate successful attributes. Future diagnosis can capture the24-byte
  attrlist plus options at the existing bounded syscall-return hook, if needed.
- First current memory sample set ends free17374/wired12774/compressor0,
  RAMFS free6648/8192. No current APFS error captured. This is EARLY health only;
  the previous boot94/System91 failed its long run at a second CMD12 recovery
  after baseline-clock fallback. That lower-I/O defect remains unresolved and
  disabling these jobs is not proof it is fixed or all dependencies work.
- ONLY observer88567 is active in monitoring phase; retained shell90517, UDP47443.
  audit/system95-observer.json/log, audit/system95-device, original boot offset
  7987522. It continues65min after baseline and captures first storage/policy
  failure. Do not duplicate collectors, reopen UART or send concurrent commands
  into its FIFO. No further flash is needed for the completed disable request.
- Next on resume: read this observer's final phase/proofs and fresh UDP first.
  If storage fails, preserve first CMD18/CMD12/recovery/clock sequence and static
  controls, then repair based on that evidence. If only MCM EINVAL is at issue,
  acquire masks/branch before changing VFS behavior. System91 rollback and all
  protected partitions remain intact; System92 and deferred exit tracing unused.

## System95 completely written; new-boot validation pending (2026-11-02)

- Fresh System95 file/device guards passed. Sending/writing ALL81 sparse slices
  and final reboot returned OKAY; audit/services95-flash.json completed_slices81,
  written_partitions[system], boot_writtenfalse, no error. Known installed NOW
  boot94/System95. Original System91 rollback and protected partitions untouched.
- User's Fastboot-ready message was consumed for this authorized System95 update;
  do not request it again for this same completed action. No new write is needed
  merely to inspect the boot. Root startup/SSH/control tests are still pending.
- Observer88567 remains active from before reboot, offset7987522, private
  audit/system95-observer.json/log/device. It checks actual installed plist/cache
  bytes,12 file/mmap controls and absence of either target process/spawn, then
  prolonged storage behavior. UDP47443 remains; UART never opened. Do not launch
  another observer or send concurrent commands into its retained shell.
- System95 SHA6d8da8962b0cb6e40d329e2050ce9f57bb02bae417e26b17ba3ff8259324b99f,
  5386170368 bytes; full63k-object/8.6GB unchanged-file comparison and81-slice
  reconstruction passed. Only the requested two jobs have Disabled=true in the
  physical plist and cached launchd definition. This is not yet hardware proof
  of stopped launches or fixed dependencies. V94 CMD12/eMMC issue remains open.

## System95 offline-ready; user ready and System installation in progress (2026-11-02)

- System95 image5386170368 bytes SHA
  6d8da8962b0cb6e40d329e2050ce9f57bb02bae417e26b17ba3ff8259324b99f.
  Exact66 critical file checks pass. Independent dual-image APFS comparison
  passes63022 nodes:45744 files/16607 dirs/671 symlinks;8614112801 unchanged
  logical file bytes are identical to91. All paths/modes/owners/flags/times/link
  targets compare; exactly3 file-content exceptions have separate byte/semantic
  checks. Only Disabled=true for the two specified plist/cache definitions;
  other529 jobs, SSH and existing keys preserved. All81 sparse slices reconstruct
  the exact verified image. Readiness/metadata/comparison under candidate folder.
- User spontaneously confirmed Fastboot after being informed System95 is being
  prepared. This is current physical readiness for the requested configuration
  change; do not ask again. Full file guards/rollback91/boot94 and fresh private
  baseline identity/product/unlocked/System geometry/download guards pass.
  tools/flash_services95.py --flash --ready-answer is currently writing ONLY
  system, audit/services95-flash.json; wait for all81 write confirmations/reboot.
  At this note first11 are confirmed; not yet an installed/booted claim.
- Current System95 observer88567 started BEFORE writing/reboot18:30:15Z with
  offset7987522; audit/system95-observer.json/log and audit/system95-device.
  It waits through System transfer and startup, authenticates pinned root SSH,
  verifies volatile tools and12 read controls, then reads back all3 actual
  installed config files byte-for-byte. Checks logs and PS for forbidden job
  spawns/processes; records first I/O error separately. UDP47443 retained, no UART.
- After boot: confirm all81/reboot, new System config and no bluetoothd/fairplayd
  job launches, then inspect pkd/suggestd/lsd and storage health. Boot94 remains;
  its second CMD12 recovery failure is unresolved. Do not claim disabling two
  jobs fixes the global read failure or all dependencies. System91 rollback,
  original protected partitions and unused System92 reserve remain intact.

## System95 disabling the two jobs is building; v94 long test failed (2026-11-02)

- User's explicit disable request supersedes the optional exit-stack diagnostic.
  A restricted live-control helper reached launchd but read requests returned154;
  host xpc_strerror maps154 to Requestor is not a platform binary, consistent
  with this kernel AMFI marking only ROOTFS executables as platform binaries.
  Do not weaken platform policy or inject into another process to work around it.
  No disable/bootout succeeded, and no fake process was started.
- Modern helper sourceb98fc2b6/CI41496403618/job125452412560 all7 passes. Artifact
  13166771893 ZIP16226 SHA9e05c12bdbba119e247744412810d571797757b82c60643160dae9bdf92becde,
  signed binary76ee28ad580d4e96731a63577caa4b2fcc0edc6215a44dd4663dd5053deaf2b0.
  Offline provenance/signature/34-import checks pass. Live transfer/read probe
  did not complete; fresh SSH timed out. The existing held shell still served
  the observer. No successful second-helper RPC or policy change is claimed.
- Preparing System95 from the exact System91 base/keys/userland. Set Disabled=true
  in ONLY the two physical LaunchDaemons plists and their cached definitions in
  System/Library/xpc/launchd.plist. All other529 jobs/catalog metadata/SSH must
  compare unchanged. tools/prepare-whyred-disabled-services.py rebuilds with the
  already verified v70 APFS builder, replays verified91 changes and rechecks every
  retained critical file and both new plist bytes/metadata. No phone writes.
- Detached offline builder86458, audit/system95-build.json/log, output
  ssh-v90/system-v95-candidate; at this note it passed tree/config diff guards and
  is compressing/layouting. No final manifest or readiness yet. Independent
  service-control-v95/compare-images uses the preserved APFS reader to compare
  the entire catalog, metadata, symlinks and all unchanged file bytes against91,
  with exactly3 content exceptions that require separate semantic/byte checks.
  After these pass, generate/reconstruct every sparse slice before any flash.
- V94 observation FAILED at18:13:17Z (sample33, about38min after boot). First
  lower block read EIO then shared-cache page-in errors and permanent I/O reject.
  Sequence: CMD18 failure, initial recovery/DATA reset, inherited baseline clock
  restored, then second abort CMD12 reports command-timeout error, driver latches
  failed. This is additional unresolved recovery behavior; patch0170 is not a
  complete physical fix. Do not suppress errno or attribute this to daemon exits.
- All true uncached controls now EIO; cached .17/.27 still match exact bytes;
  shell-list/passwd normal reads EIO and mapped reads SIGBUS. Private
  audit/emmc-v94-device/transport-all.txt, first-error-context.txt and12 failure
  controls preserved. Observer81246 finished captured-first-error-session-retained;
  held shell81341 and UDP47443 remain. No UART. Stop further fresh SSH probes
  against this degraded run. Installed is still boot94/System91; System95 is
  not built/verified/flashed yet. No job-policy change occurred before failure.

## Service-control helper live read probe; modern query update (2026-11-02)

- Helper sourcef0ffa4b4, CI41496018797/job125451054330 all7 steps success.
  Artifact13165154529 ZIP15918 SHA
  93333c714f5207fbbf7d49f4765435c0447c060fa683c1412161e082b62e364b;
  signed binary19516e716f83d4e1db4ede921ddbdf3f9182ee5d2ec4557bb2f8bd15b8c39ec6.
  Provenance/CRC/digest/IOS/ISA/signature and34 exact16.5 imports pass; both
  dynamically resolved bootstrap symbols are exported by the exact cache.
- Volatile SCP0755 and complete byte readback pass. Read-only named LIST815
  calls reach launchd but return154 in system domain; no mutation attempted.
  Switching read probe to the same modern712 named-service query used by pinned
  Procursus domain discovery, plus xpc_strerror text for failures. New CI pending.
  Current helpers/attempt evidence under service-control-v95/ and audit/services-v94/.
- No job disable/bootout or partition write yet. Boot94/System91 observer remains
  active with zero captured lower-read/APFS/panic failure; do not claim services
  disabled until RPC responses AND subsequent spawn/PID checks confirm it.

## User requests disabling Bluetooth/FairPlay jobs; restricted control preparing (2026-11-02)

- User explicitly requests removing bluetoothd/fairplayd.H2 launches (or fake
  processes), to prevent their restart loops and test dependent services. Choose
  genuine launchd disable/bootout, without fake Mach-service endpoints. Current
  exits are clean0, not demonstrated causes of other services' crashes.
- Fresh v94 manual mobile Bluetooth child confirms missing marconi-bt/bluetooth
  IORegistry services, invalid/missing address and No bluetooth on this device,
  then exit0. IORegistry bluetooth query is empty. Private audit/services-v94/.
  FairPlay's exact normal-exit cause remains unresolved. Long eMMC observer is
  still running; no APFS/permanent-read/panic failure yet. Service policy changes
  will be timestamped separately from the preceding storage baseline.
- System image has no launchctl. New whyredsvc source uses pinned Procursus
  launchctl protocol22906f7d, allowing ONLY the two exact labels in explicit
  system/user501 domains. Root whyred boot gate prevents RPC on host macOS;
  dry-run validates27 label/action/domain/host guards without sending RPC.
  Query first, then disable and bootout only an identified target/domain.
  Replies/error dictionaries must succeed; inverse enable/bootstrap is retained.
- iOS helper CI pending. No helper upload, live disable, System/boot write or
  fake process has occurred. First aim is a reversible live RAMFS-backed launchd
  change; persistence across /var reset needs a separate verified seed change.
- Earlier optional pre-exit stack tracing work is deferred, NOT compiled or
  committed. Private service-exit-v95/ holds it and deferred-tools; no0171 patch
  exists. Its initial BSD compile lacks private task/region layouts; do not use
  it as a candidate. Current installed stays boot94/System91; UART unopened.

## V94 early pinned SSH and all read controls pass; long test active (2026-11-02)

- Boot94/System91 remains installed. Pinned root SSH authentication and held
  shell81341 work. Both reviewed tools uploaded only to RAMFS0755; entire raw
  35056-byte and diag70752-byte readbacks equal their reviewed signed binaries.
  All8 cached/F_NOCACHE reads plus4 mapped reads pass status/length and exact
  original-file FNV checks. Diag selftest and first2 VM/fs/ps samples pass.
- Initial sample: page16KiB/free30508/active33667/inactive4342/wired11250,
  compressor/pageouts0; RAMFS free7103/8192 pages. At1.04GB kernel root reads,
  errors0/fallbacks0/XO1/multi1. No APFS error/common memory-error SIGBUS/permanent
  rejection/panic captured yet. These are early controls, not sustained recovery
  or proof that all individual service/hardware problems are fixed.
- First local SSH attempt raced early server readiness and timed out; its local
  SSH child had exited. Observer79898 was stopped before any tool upload, all
  attempt files archived in audit/emmc-v94-bootstrap-attempt-1. Added bounded
  pinned-command readiness and local-child exit detection. Root probe succeeds
  without auth-policy changes. Current ONLY observer81246 retains original
  boot offset7104825; status audit/emmc-v94-observer.json, device directory
  audit/emmc-v94-device, log audit/emmc94-observer.log. UDP47443 stayed active.
- Collector now monitors65min after the early baseline, recording VM/fs/ps and
  periodic true uncached reads. Do not reboot/start duplicate shell commands or
  use the unused pressure helper during this window. Read its final phase and
  first-failure controls before claiming stability; if clean, verify fresh root
  auth and service lifetimes after the window. UART remains unopened. Latest
  user questions concern WHYRED FSERR: errno0 is specifically a short successful
  write, accompanied by same-id requested/returned diagnostics; it is not a new
  read-error or memory-corruption result.

## Boot v94 physically installed; early validation running (2026-11-02)

- User confirmed fresh Fastboot availability for v94. Private baseline identity,
  product/unlock/64MiB boot geometry, exact candidate and verified boot93 rollback
  passed. Boot send/write and reboot all OKAY (audit/emmc94-flash.json). Installed
  NOW boot94/System91. No System/other partition write; System92 reserve unused.
- Existing UDP receiver47443 stayed active; new boot offset7104825. Observer79898
  started BEFORE flash/reboot17:35:31Z (audit/emmc-v94-observer.json and
  audit/emmc94-observer.log), captures into audit/emmc-v94-device. No UART.
  USB console works; port2222 appeared and pinned-shell initialization is now
  running. At604MB of root reads the kernel reported errors0/fallbacks0; no
  new APFS error/permanent-I/O rejection/panic captured. This is only startup.
- Early cached/direct/mapped read checks and tool full readbacks are pending.
  Do not launch a second observer or commands into its shell while it uploads.
  Monitor65min after baseline, including uncached shell-list checks; retain
  first-failure evidence and the one shell. No sustained/device recovery result
  claimed yet. Bounded private-memory helper is still unused on phone.

## Boot v94 offline-ready; physical test pending (2026-11-02)

- Kernel source3b180816fc9ca0c615404d1bf0ce484bce1b08b5, full CI
  [41482862184](https://github.com/timosid/ios-sweetwhyred/actions/runs/41482862184),
  job125405454088: all27 steps succeeded, including4769 actual-function eMMC
  model checks and both new old-code regression cases. These model checks do
  not emulate physical SDCC timing. Exact no-fuzz replay and ARM64 compile pass.
- Kernel ZIP79355972 bytes SHA
  fb2f557a82364f2748cebdcf8fbcf06df257dba4aca5ba91d369cf55af2369d0;
  buildtree ZIP25434691 bytes SHA
  e046f477def1d3902baee1057b437237fbf6373cb318603219a70588d4593d5f.
  GitHub digest/size/CRC/provenance, patch0170 replay, exact reviewed runtime
  sources, retained suites, linked ISA/cache path, artwork, loader/ADT/stock DTB,
  layout and image guards pass. No failed-build artifact is used.
- Candidate port/out/whyred-ios-root-v94-emmc-recovery-41482862184/:
  boot22347776 bytes SHA
  cfd40e726b1d9b2fac7d8015bd503ffbd329110dbc38980cc6c5a6fc53c9b27c;
  kernel1de821211845980d0e176f042704a8e1e0b489c44e2953941783b9692002f4dc.
  Same581-byte command line/System91 contract as93. v94 only changes two driver
  recovery/polling sites; no error suppression, quota increase or IRQ masking.
- Current installed remains boot93/System91. v94 has NOT been flashed or
  physically validated. Fastboot currently absent. Boot-only flash helper pins
  image/kernel/source/System91 and verified boot93 rollback. Fresh physical
  Fastboot readiness is required; previous answer was consumed for boot93.
- Existing UDP receiver remains active; UART never opened. Prepared observer
  ssh-v90/observe_emmc94.py is NOT started: start once before the next flash,
  capture early cached/direct/mapped baselines through pinned root SSH, retain
  one shell and monitor65min. Every fifth sample now verifies a true uncached
  shell-list read. Stop/capture first lower-I/O/APFS/common-SIGBUS failure.
  System92 reserve and private-memory pressure helper remain unused.

## eMMC failure localized; baseline recovery and deadline fixes preparing (2026-11-02)

- V93 reproduced the global failure naturally after prolonged observation.
  Observer ended captured-exec-failure-session-retained, sample38/status138;
  held static SSH shell60796 and UDP receiver47443 remain. No synthetic memory
  test was run on phone. Earlier strong-pressure8-read/fresh-auth checks passed;
  this was a baseline, not a root-cause repair or sustained stability result.
- First APFS failure is lower block-device read completion EIO with partial
  residual, then page-in failure for a shared-cache member. Preceding sequence:
  a CMD18 batch fails, card recovery completes, inherited baseline clock is
  restored, then a CMD17 timeout is reported with an old zero status while the
  next actual snapshot shows command response and data-ready bits. Driver then
  permanently rejects every subsequent media read. Full logs/IDs are private.
  True F_NOCACHE returns EIO for all tested files; some cached reads still match
  source bytes. This localizes the origin below APFS/UPL and explains SIGBUS and
  invalid-shell SSH rejection. RAMFS quota is not the originating read error.
- Patch0170 addresses two specific code defects: resample interrupt completion
  once at the deadline (CPU may have been descheduled after the first sample),
  and recover/reread a failed CMD17 in baseline as well as XO mode. Restore
  inherited clock only when XO is still active. CMD12/CMD13 READY/TRAN checks,
  one-retry bound, readonly/LBA/partial-data guards and permanent rejection after
  genuinely failed recovery/retry remain. No IRQ masking/timing-rate policy added.
- Exact authenticated v93 driver/header extracted. Deterministic actual-function
  host regressions BOTH fail on old code: late completion after counter jump and
  baseline CMD17 recovery. Patched tests pass4769 cases, including batch failure
  followed by baseline transient failure, late hardware-error rejection, and
  persistent errors with exact residual/at-most-two attempts. Local ARM64 compile
  and exact no-fuzz patch replay pass. Full kernel CI/device test still pending.
- Current installed remains boot93/System91; System92 reserve unused. No new
  partition write or UART. Next candidate is boot94 after full CI/provenance/
  runtime-source/loader/image checks, then fresh physical Fastboot readiness.
- Independent static private-memory helper source55970a81 / CI41478637167,
  job125390794509 all6 succeeds; artifact13159040562 ZIP12117 SHA
  06e9f6eaae260a680b71a5703a30c669b83b95d002a42952cd076efe095f0f1b.
  It was NOT downloaded/uploaded/executed: natural VM pressure was sufficient.

## Bounded private-memory reproduction helper preparing (2026-11-02)

- Boot93/System91 still running with one observer59812 and held shell60796.
  Atstate021, free7292/wired14708/compressor0; RAMFS4382/8192 free. pkd296,
  suggestd300 and lsd96 retain PIDs, no APFS error/panic captured yet. Initial
  stacks resolve with slide0x1e1f8000, validated by mach_msg2/kevent/ulock/stat
  trap offsets. Eight VM/UPL/pager source files match authenticated v93 exactly.
- Static probe gains an explicit pressure MIB SECONDS mode, hard bounds96MiB/
  15s, only its own anonymous private pages. Deterministic incompressible fill,
  before/after full digest, select timeout and munmap; any process exit releases
  the region. Native4MiB/1s allocation/fill/hold/verification/free and invalid
  bounds pass. Existing file-only mode/collector binary is unchanged on phone.
- New signed artifact CI pending; no memory-pressure test ran on phone. Prepare
  this for a short64MiB test only if normal observation does not reproduce the
  previous roughly33-minute failure. Check live memory/first-error status first;
  do not compound an already-occurring failure. No filesystem/partition writes
  or service-policy changes, no UART. Exact root cause remains unproven.

## Boot v93 physically installed; early SSH/read baseline passes (2026-11-02)

- User confirmed fresh Fastboot. Exact private baseline/product/unlocked/64MiB
  boot geometry and candidate/boot89 rollback guards passed. Boot send/write
  and reboot all OKAY (audit/apfs93-flash.json); only boot changed. Installed
  NOW boot93/System91. No UART opened. New bootargs/USB logs confirm profile.
- Existing UDP receiver47443 stayed alive, new boot stream observation starts
  at byte4926436. Detached observer59812 started15:40:07Z BEFORE flash/reboot;
  audit/apfs-v93-observer.json/log and audit/apfs-v93-device hold private results.
  Do not start duplicate collectors or reboot during this observation.
- Early pinned root SSH works, held shell60796. Static raw3996342f and task/VM
  helperc1a356f4 uploaded only to RAMFS0755; complete file readback equals each
  reviewed binary. Raw cache17/27 cached+F_NOCACHE reads match expected original
  FNV d58f5b0f9afadca0/b9b23f3a46fd0825; all8 initial file-read cases and mapped
  reads pass. Prior-failing shells/passwd and0xa59cd80 range currently read.
  This establishes baseline after reboot, NOT a sustained root-cause fix.
- First VM sample: page16KiB, free40521/active29619/inactive709/wired8875,
  compressor/pageouts0. RAMFS free7574/8192 pages. Initial SpringBoard25,
  backboardd105, lsd96, containermanager65 have bounded read-only thread stacks;
  pkd/suggestd not yet in initial sample. Continue observing to first failure.
- Observer monitors65min after baseline for first WHYRED APFS ERROR or common
  memory-error SIGBUS; normal/direct/mmap comparisons reuse retained shell.
  Host reader separately walked63022 image objects and saved private inode/path
  index for matching the first error to exact file. No phone media writes from
  these diagnostics. System92 reserve remains unused. Kernel5f63e7c9 build
 41471287807 and boot5a29f651 are retained; earlier failed CI stays rejected.

## Boot v93 offline-ready; physical Fastboot readiness requested (2026-11-02)

- Kernel source5f63e7c9e9e2fb776e74324a62c82ce3592a15ab,
  CI41471287807/job125365226436: all27 steps success. New actual-function
  fault-injection/UBSan test also passes in Build before kernel compile and
  its report is retained. Earlier SDK-inheritance failure remains rejected.
- Authenticated kernel ZIPa05fd85b5e95ce2b90bc3a60d059d1c9eac44b81df69924730642d06361748b5,
  buildtree ZIP37126b09ed1d00742af2a50e4014220a67528ff91992b546b25893429b21ab88.
  ZIP size/CRC/provenance, all retained checks, exact reviewed APFS3 files and
  other runtime source, linked diagnostic markers, no-LSE disassembly, boot
  artwork, loader ABI/layout and stock-image contract pass.
- Candidate port/out/whyred-ios-root-v93-apfs-errors-41471287807/:
  boot22347776 bytes SHA5a29f651144b546e030db6376cac4daee5f78eb94c5a52f18f5bc6987f0ba37f,
  kernel58c8ad2ecb6005a641720cceacfd84529dee52917628857ae8eecbe76f886213.
  Command581bytes adds only whyred-apfs-errors=1 to v89 profile; global RAMFS
  quota/AKS/USB/storage policy retained. New API behavior is explicit IO_NOCACHE
  direct read, for cache-vs-parser comparison. It is not a verified root fix.
- Current boot89/System91 remains installed. No new flash/UART this run.
  Boot-only helper is pinned to image/kernel/source/System91 contract and known
  boot89 rollback. Fastboot devices currently returns none. Physical Fastboot
  readiness question is pending; ordinary reboot reply was not flash readiness.
  Do not write System92 reserve, GPT, recovery, bootloaders or other partitions.
- Once user confirms Fastboot, freshly verify private baseline/product/unlock/
  boot geometry; start prepared ssh-v90/observe_apfs93.py BEFORE flash/reboot
  (not against old running boot), then guarded tools/flash_apfs93.py. Existing
  UDP receiver47443 stays; never open UART/duplicate receiver. Observer uploads
  signed raw3996342f/helperc1a356f4 only into volatile RAMFS using pinned SSH,
  exact full readback, retains one shell, and captures early/first failure with
  normal-vs-F_NOCACHE/mmap comparisons. It is prepared, not started/tested yet.
- Later old-boot sample: .27 header reads correctly while0xa59cd80 returns EIO;
  shell/server headers and .17 retained bytes also read. Corrected raw mapped
  faults are confirmed sig10/code0x10000000a at valid file mappings. Thus failure
  is per-page, not whole-file disappearance. Exact originating layer is unproven.
  Private audit evidence and keys remain outside Git.

## Full CI test SDK correction (2026-11-02)

- Initial kernel run41470349414/job125361960778 stopped BEFORE kernel compile:
  the new host test inherited build.sh SDKROOT and could not find assert.h.
  No failed-run boot artifact is eligible. Patch0169 applied and APFS source
  read-only guards passed; this is not a device/kernel result.
- Host test now removes inherited SDKROOT and explicitly chooses macOS SDK,
  matching the existing eMMC contract-test pattern. A deliberately invalid
  SDKROOT local run passes. CI also retains its report in the kernel artifact.
- New raw F_NOCACHE probe source78fde09d / CI41470349071 all6 passed, binary
  3996342f804590682d77e2bb4da2dbfabaa9666ebd9449a907a03a8ab7edea43,
  ZIP8d237575107f8c98a0cbd83b7274eb0d5cf931fd7c65368e3ef6eeed68d4ddd7.
  Complete volatile self digest passed. Current boot89 ignores IO_NOCACHE in
  VNOP_READ: pread still EIO with fcntl success, as expected from exact source.
  Signed probe remains usable despite broken dyld. No new boot/System flash.

## Read/mmap failure confirmed; bounded APFS diagnostics preparing (2026-11-02)

- Corrected raw helper cc0ab5c / CI41468481553/job125355507394 passes all6
  steps. ZIP49e05ae3ee299910feb47b63c22aa56d9cbe339437e6bc3f82d6d8cb2a9bfac3,
  binary97db040f25f6faaef038229892af6b6dc3a3aa5bddd1934f05ba74cf3c87b490.
  Signature/platform/no imports validated, volatile complete self digest passes.
  It now starts on every tested argument layout. Shells/passwd/.27 fault-page
  pread EIO, then mmap succeeds but actual mapped read SIGBUS138. Cache .17
  pread/mmap still give the exact expected512-byte digest. These are genuine
  memory-error faults after entering main, distinct from the fixed SP bug.
- Patch0169 adds default-off whyred-apfs-errors=1 tracing at transport, cached
  read/fill and page-in failures. Preserves original errno/UPL abort behavior,
  records original mapping KR, file inode/offset/size and free/wired counters.
  At most32 records, no allocation or pathname lookup. It also honors existing
  IO_NOCACHE read requests through the already implemented direct path; this
  enables a controlled cache-vs-parser comparison, not a claim of root repair.
- Both changed C units compile locally for ARM64 with authenticated v79
  generated headers. Exact no-fuzz patch replay on authenticated v89 passes.
  Host fault injection extracts the actual kernel functions and checks17
  read/page-in/transport fault cases, cleanup, EOF zeroing, direct dispatch and
  default-off/32-record logging budget. Undefined-behavior sanitizer passes.
  Local ASan runtime itself traps in libpthread initialization before main;
  that attempted run is not counted as a kernel/test result.
- Raw helper adds optional bounded F_NOCACHE toggle; native syscall test passes.
  Full kernel CI/new signed raw artifact pending. Boot89/System91 is still
  installed, verified System92 reserve unused, held SSH shell/UDP log alive.
  No UART or partition access added. User's ordinary reboot is not a new flash
  readiness answer. Prepare a verified boot-only candidate before next test.

## First common SIGBUS captured; read-only APFS files return EIO (2026-11-02)

- The ordinary reboot reproduced the common failure at14:46:27Z (~33 minutes
  into boot). VM pressure/compression began first: free about2094 pages,
  compressor753/pageouts31 at the last complete sample; a later partial sample
  shows free2345/wired18089/compressor2374/pageouts39. RAMFS still had2838 free
  pages (~44MiB), so this failure is not its128MiB data quota. Earlier
  mediaserverd NULL-call SIGSEGV is distinct from subsequent common SIGBUS.
- Automatic first-failure collector completed. Freshly executing dynamic probes,
  whyredctl and whyreddiag all die before main in dyld at the same writable
  shared-cache address0x2120e4d80 (unslid0x1e1eb0d80/.27.dylddata offset0xa59cd80).
  Held raw SSH shell PID40269 survives. New server2223 rejects valid auth because
  User root has invalid shell, rejected; auth/key checks stay unchanged.
- Critically, built-in shell reads of /etc/shells and passwd produce no bytes.
  A signed freestanding ARM64 probe (no dyld/imports) was transferred using only
  shell printf into the no-longer-running volatile probe's0755 inode. It starts
  in the broken state, and complete self-file digest matches the reviewed Mac
  binary. This modifies only /var/tmp, not System or any partition.
- Raw syscalls prove: /etc/shells open/fstat succeed, UID0/mode100644/size8,
  but pread=-5(EIO). Passwd has correct2795-byte size and also pread EIO. The
  critical .27.dylddata file has correct189300736-byte size but that offset
  returns EIO. The old .17 literal's512 bytes still read correctly with expected
  FNV d58f5b0f9afadca0. Mounted root block-device open is EBUSY, not a transport
  test. eMMC counters last report0 errors; failures before hardware accounting
  and UBC/page-in failures remain possible. APFS pread uses its custom UBC path;
  these results do NOT prove whether parser, UBC, mapping or transport is root.
- Raw first version CI41466390673/job125348296582 passed all6 steps; zero imports,
  LC_UNIXTHREAD/no dylinker, iOS platform, code signature and ISA checked. Binary
  bf775bbf07bc8023c9b5a83342a954275e4685d65bce6b42ce4983bd8520722e,
  ZIP2f3472292b39b3e9b79387d086524014b1c16b9464f6005995d685bfb23850e9.
  Earlier CI41465971269 failed because static ld omits platform metadata; the
  build now inserts the correct iOS16.4 declaration in reserved padding BEFORE
  signing. No wrong-platform artifact was deployed.
- Some first raw runs hit our own initial-SP alignment bug (exception0x103,
  not the common memory-error0xa). Confirmed via stack address/PC; argument
  padding allowed immediate EIO measurements. Source9e897dea85c8345a8650ae09a47cc02257b3b133
  aligns SP while retaining argv pointer. Its new CI and improved mmap-after-
  pread-error diagnostic are pending. Do not confuse probe alignment with root.
- Next: finish signed raw probe update/read-vs-mmap comparison, then prepare
  narrowly bounded kernel error diagnostics/repair based on actual failure.
  No boot/System flash since v91; v92 is still an unused verified reserve.
  Native collector37864 failed at the common SIGBUS; cold watcher45132 completed.
  Old watcher42713 was superseded for a5-minute pause in new auth requests.
  Kernel UDP receiver47443 and held shell40269 remain; no UART opened.

## Volatile diagnostics verified after user reboot (2026-11-02)

- User confirmed ordinary reboot. Existing USB/host address and UDP receiver
  survived. Installed stays boot89/System91; no partition write or UART access.
  Early pinned root SSH succeeded, and one persistent raw shell remains alive.
- Reviewed v92 helperc1a356f4/server5f1f16a4 were uploaded only into /var/tmp via
  SCP0755 and complete readback equality. On-phone helper self-test, cross-task
  registers/frame reads and VM statistics succeed. A diagnostic server on2223
  uses the existing pinned System host/authorized keys; actual root login passed
  and server messages arrive in the existing USB UDP log. Original2222 job stays.
- Manual mobile-user Bluetooth child prints missing marconi-bt/bluetooth service,
  invalid/missing device address and No bluetooth on this device, then exit0.
  This confirms its missing-device exit branch in that run, consistent with
  stock clean exits; manual execution does not reproduce all launchd context.
  FairPlay mobile child also exits0 but supplies no stderr cause. No DRM or
  anti-debug behavior was bypassed; Bluetooth hardware functionality is unported.
- Current samples show pkd305/suggestd314/lsd96 alive, with task frames captured;
  no new target crash yet in this boot. Initial VM free37944 pages fell to about
  7700, inactive about25500, wired15400; compressor/pageouts/swap stay0. RAMFS
  free about4700/8192 pages. This is not a long-run stability or repair claim.
- Added bounded read-only file/pread/mmap/task-memory probe source
  c99b6ccf444e2c82f600135fc981fa81cb3ab34f. Full CI41462202753/job125333835496
  all7 steps pass. Artifact13149202188 ZIP16978 bytes, SHA256
  48bfefb53548365ace93ca7e85a8405b142f280e0a43ea7add23b5e8f6ba1bc4;
  binaryd47c8b9e1206ae4b4c99f69ec3536fd4e968200047a8a1899ecd732ae34e9b4a.
  Signature/platform/ISA and31 exact16.5 imports pass. Volatile SCP/readback and
  physical baseline pass: root lookup succeeds, the old fault's cache .17
  literal returns identical512 bytes by pread/mmap/remote suggestd VM read, and
  the old writable cache-page address is readable in launchd. No target writes.
- Read-only baseline VM slide0x30234000 is inferred from mach_msg2_trap return
  and validated by identical literal bytes. Local symbol helper's old100-load-
  command cap was raised to1000 (same64KiB bound) for legitimate SpringBoard
  224 commands; Apple/cache bytes and analysis remain private.
- Native collectors: PID37864 samples VM/fs/PIDs/new target stacks until14:47Z;
  persistent shell PID40269/FIFO is retained afterward. PID42713 watches first
  SIGBUS or fresh2223 auth failure until about15:01Z, then reads account/file/
  mapped-page/VM/server evidence through that held shell. Do not duplicate them.
  Private audit/services-volatile-v91/ and monitor JSON hold current status.
  The earlier v91 common SIGBUS and MCM lack of Data Protection remain unresolved.

## Ready v92 reserve; preferred next test is volatile upload after reboot (2026-11-02)

- Detached v92 build completed all offline checks at14:09:00Z. Image size
  5,386,178,560 bytes, SHA256
  0357bf46dc72f5c957ce7725d18952f7d31063e564681734c5d75bd44131bc28.
  All65 exact file comparisons,18 metadata checks and81 sparse full-payload
  reconstruction checks pass. Prior531 launchd jobs/keys are unchanged; only
  the server changes and a diagnostic helper is added relative to v91.
  Packager SHA4850cf670c08d38c5f28654ee3b074d38fcc1135184c62766fec02efb3ed32df.
  No new flash occurred; installed remains boot89/System91. The first,
  interrupted candidate remains quarantined and is not eligible.
- Faster next action: user was asked to reboot normally, or enter Fastboot for
  host reboot only. Once early SSH returns, use the reviewed v92 binaries in
  volatile /private/var/tmp through the existing v91 server. This does not
  require another System write. Do not treat this reboot-readiness answer as
  authorization to flash the reserve v92 image.
- Private detached monitor PID37864/script ssh-v90/observe_volatile_diag.py
  started14:07:15Z, waits for TCP disconnect/reappearance, then opens a single
  pinned persistent raw shell. It uploads/checks complete helper/server bytes,
  starts the diagnostic server on2223 with existing System keys, and samples
  VM/fs/process/thread state. It expires40 minutes after startup. Check status
  audit/services-volatile-v91-monitor.json before starting anything else. It
  was still waiting for physical reboot; no device tool upload or runtime
  helper test has happened. No UART was opened; existing UDP capture continues.
- Additional host-only investigation executes the exact authenticated boot89
  APFS reader core against System91:4096 namespace probes,512 partial shared-
  cache reads,133 cfile resets,33 metadata flushes pass with exact source bytes.
  This does not test device eMMC, kernel UPL or VM pressure behavior and does
  not establish a fix for the common SIGBUS/KERN_MEMORY_ERROR failure.

## V92 userland verified; image write restarted after interruption (2026-11-02)

- Full v92 userland source838c644feea10ac38578c14b8aedadb0e22bab4b,
  CI41454271748/job125307206157: all10 steps success. ZIP SHA256
  f4f12a56ebe68c0ab18970972807c68b7a979aef11777e2b4e31fbe8bbb23adb,
  artifact13144949733/573129 bytes, exact file set/CRC/provenance and every
  binary digest pass. All six binaries match installed16.5 cache imports.
  Dropbear5f1f16a4d23d3019a8cd3a799514f13cc5db7b838bd0be59c3ea7184e31c9ab1;
  diagnostic helperc1a356f4fae9537a0336e2aedef465ed9cf248d2a99c369a3bfa210c18f10fa9.
- Native authentication/transport5 checks and USB mirror512-budget/1023-byte/
  sanitization/errno-preservation checks pass. Separate final sampler workflow
  41454271609 also passes, including VM counter self-test. First full v92 build
  failed because -g created a dSYM directory in the binary inventory; fixed by
  omitting that debug bundle. No failed-build artifact was used.
- First local v92 container write was interrupted before completed file checks.
  /bin/sh comparison reports resource-fork EIO. It is quarantined privately in
  system-v92-interrupted-ineligible with DO-NOT-FLASH marker; no successful
  manifest exists and it must never be flashed. A separate detached build/
  complete verification pipeline restarted; image results remain pending.
- Later v91 USB capture reveals a system-wide SIGBUS/KERN_MEMORY_ERROR storm.
  The first captured SIGBUS is SpringBoard25, followed by xpcproxy737; suggestd
  later faults in strlen/strdup/xpc string creation reading a valid original
  cache string. Shared-cache and private-data ranges both appear. Transport
  counters last showed zero eMMC errors, which does not prove VM/page data
  correctness. This supersedes the earlier short-run absence-of-crash sample.
  Do not claim filesystem encryption or any daemon repair. Root cause remains
  unproven; distinguish VM/resource, pager and file-read failure paths.
- V92 retains boot89/kernel policy and every existing531 launchd job/key. It
  changes the SSH server only to mirror bounded diagnostics and add failure
  errno, plus installs the read-only task/VM helper. A persistent remote shell
  collector is prepared so later diagnostics reuse one authenticated session;
  loopback-only FIFO framing/exit7/next-command tests pass. No new phone write
  or UART access happened. New candidate needs complete offline verification
  before requesting fresh physical Fastboot readiness.

## SSH long-run authentication failure; v92 diagnostics preparing (2026-11-02)

- After several successful read-only sessions, SSH began rejecting the same
  pinned production public key before the signed-key step. Private/public/
  authorized local key correspondence still passes. TCP/host identity and live
  kernel UDP continue. No cause is proven: account lookup, shell checks, file
  lookup/permissions and resource pressure must remain distinct possibilities.
- The standalone sampler passed full CI41452473934/job125300803642 on source
  231eafc514f11e9f71d3bfc6b3309e30c0eb53fc. ZIP SHA256
  0658c018c635099c69e7e20ce4b93f55e83748da5f9e0ed3cb9860284cf65c1f,
  binary d2193f8a6d79b5ac416744bb4d5d832edcba298039ca1495f862509f6c2335fb;
  signature/platform/ISA and37 exact installed-cache imports passed. Upload
  stopped at SSH authentication, before any file payload; no sampler executed
  on the phone. Initial sampler CI failed on unsupported SDK mach_vm.h; the
  reviewed correction uses the supported64-bit vm_read_overwrite interface.
- Latest linked allocations are distributed: /var/mobile43.3MiB,
  /var/db24.9MiB (uuidtext21.8MiB), /var/containers16.8MiB. No new quota-pressure
  or pkd/lsd/suggestd crash was in the captured v91 segment at this checkpoint.
- V92 candidate adds bounded nonblocking SSH-server log mirroring to the same
  fixed USB destination192.168.7.1:5140 and includes the live sampler in System.
  It also records errno on failed account/authorized-key metadata/open lookup.
  Account/shell/ownership/key/signature decisions and job activation are intact.
  Native UDP delivery/budget512/max1023/sanitization/errno tests and all exact
  upstream patch contexts pass. New full userland CI/package are still pending.
  No new flash was performed. UART stays unopened; existing receiver stays alive.

## Live SSH service diagnostics in progress (2026-11-02)

- Boot v89 / System v91 stays installed; no additional partition writes. Root
  SSH and the existing single UDP receiver are working; UART is not opened.
- Across the first roughly half-hour, pkd280/suggestd283/lsd95 retain their PIDs
  and no pkd/lsd crash appears in the v91 capture. This is an observation, not a
  long-run stability claim. Bluetooth/fairplay continue clean status0 exits.
- RAMFS free pages fell from7198 shortly after SSH to2214/8192. The root DSC
  temporary file disappeared; the remaining DSC file is about1.2MB. Thus the
  original bulk DSC footprint is absent at the sample, but other growth still
  needs attribution; global quota128MiB remains unchanged.
- The private MCM log repeatedly reports unsupported class2 Data Protection;
  exact local cache code checks statfs MNT_CPROTECT. RAMFS does not implement
  per-file keys. Do not blindly advertise encryption to hide this error.
- A bounded live thread sampler and mobile-user child runner are being built
  as a standalone signed iOS helper. It reads registers/frames without target
  suspension or memory writes; child diagnostics have a30s timeout. Upload
  through SSH into volatile /var/tmp, not a new System flash. CI/device results
  are pending. Device logs/cache bytes and keys remain outside Git.

## System v91 SSH verified on the phone (2026-11-02)

- Installed is boot v89 / System v91. The user returned the intentionally powered
  off phone to Fastboot and requested continuing the repair. Fresh identity,
  whyred/unlocked/System geometry/download guards passed. All81 sparse sends/
  writes and final reboot returned OKAY; only System was written.
- V91 image5,386,170,368 bytes, SHA256
  fa356fa4a02ae74fff9dbc674336f52f9754560767ee3c88ca3579629905ebe0.
  All64 complete XNU-reader file comparisons,17 metadata checks, obsolete job
  ENOENT and81 sparse coverage/payload checks passed. The v90/v91 caches differ
  only by the SSH job key. Programs/keys and original530 jobs are unchanged.
  Packaging source73572a42a155bc3a8b26911a7d7fd430f95c3065. Existing authenticated
  userland CI41350694615/b5b9b074 source is retained; no new kernel/SDK build.
- V90's /Library/LaunchDaemons job was outside this exact launchd's embedded
  Bootstrap/Paths. V91 uses /System/Library/LaunchDaemons for the standalone job
  and cache key, and the builder validates the actual embedded search paths.
  The old v90 mistake is rejected by a functional negative check.
- The Mac OS administrator confirmation persisted only the exact USB service's
  Manual192.168.7.1/24 without a router. This returned automatically after reboot.
  Actual new kernel UDP logs resumed in the same detached receiver. UART was
  not opened and no second5140 listener was started.
- TCP2222/Dropbear2026.94 was first observed331s after the boot observer started.
  The first20s SSH attempt timed out during startup. Retrying with90s confirmed
  the pinned Ed25519 host and authenticated root, then returned actual Darwin
  22.6.0/iPhone10,3 and uid/gid/euid/egid0. Subsequent full device checks passed
  ps/fs, shell exit7, exact65536-byte binary round trip, unrelated-key rejection
  and reading the server log. Production keys remain local; client timeout90s.
- Read-only SSH health snapshot: RAMFS free6581/8192 pages (~102.8MiB of128MiB).
  DSC files occupy6471680 allocated bytes at this snapshot; a5.25MB temporary
  main-cache file is still being materialized. This does not yet establish the
  physical8MiB cap or long-run quota behavior. PluginKitPlugin data directory
  is absent at this point. Bluetoothd restarted between snapshots; backboardd
  nil URL exception and container ENOENT/EPERM appear in the new UDP log.
  Original pkd/lsd/other daemon and container/RAMFS goals remain open.

## System v90 flashed; initial host address pending (2026-11-02)

- User explicitly authorized adding SSH, then said to flash the concrete System
  v90 candidate. Fresh private-baseline identity, whyred/unlocked, exact System
  geometry6,700,000,256 bytes and512MiB download limit passed. All81 sparse
  sends/writes and final reboot returned OKAY. Installed is boot v89 / System
  v90. Only System was written; no separate format/GPT command was used.
- System image5,386,170,368 bytes, SHA256
  60b6411a89b72d3452e6bcde01e2f6589c48bfa106aa3ad82cb2778dc46a5464.
  XNU APFS reader passed64 complete byte comparisons, including all43 active
  cache members;17 inode/owner/mode checks and all81 sparse payload coverage/
  digest checks passed. Original System v70 and preserved boot v89 hashes pass.
- The baseline catalog45734 files/16600 directories/671 links is reproduced
  without host metadata. Added Dropbear, dash, scp, whyredctl, private local
  host/authorized keys and one job to the530 preserved decoded launchd jobs.
  Keys were generated on the Mac and the host identity pinned; no private keys
  or Apple bytes were uploaded. See WHYRED-SSH.md for exact source/options.
- Corrected userland source b5b9b074c51e3b676928ced77a3b1b7c565ff600,
  CI41350694615/job124979995276 passed all9 steps. Artifact13101197811 ZIP
  SHA256dec89a1c4bddd17ba2f5204f383a50d5fce230938fe2dcc6fae6a97805fe1b18
  passed provenance/digest/length/CRC and all binary digests. All five binaries
  match exact installed16.5 cache exports, with proofs bound to binary SHA256.
  Native key acceptance/rejection, command status,1MiB transport, shell builtins
  and diagnostic commands passed. The earlier41349937032 shell imported absent
  strchrnul; it was rejected and is not installed.
- After the new reboot, the exact-MAC USB Ethernet interface returned. macOS
  DHCP had removed the temporary192.168.7.1 alias; the host now has link-local
  only. A guarded SystemConfiguration helper is ready to persist only this USB
  service's192.168.7.1/24 without a router. OS administrator authentication timed
  out without confirmation. A user question about the OS window is pending.
  Restore this host address before testing SSH or inferring a phone crash.
- The detached USB UDP receiver remains alive and retains its prior private log;
  no second listener or UART was opened. Actual device SSH authentication and
  commands remain UNVERIFIED. pkd/lsd, container/RAMFS behavior and other daemon
  exit causes remain open; installing SSH does not establish their repair.

## V89 USB Ethernet and live kernel logs verified on device (2026-11-01)

- User confirmed Fastboot with UART open. Fresh single private-baseline device,
  whyred/unlocked/boot64MiB and image/kernel/source/version/v87 rollback checks
  passed. Boot send/write and reboot returned OKAY at2026-11-01T20:38:05Z.
  Installed is now boot v89 / System v70; only boot was written.
- UART confirms UTMI TESTMUX release: before35353535/40404040, after00000000,
  release1/changed1. DWC3 receives connect/setup traffic and configures ECM.
  Mac found the exact host MAC02:00:5e:77:ee:01 on en1 after10.078 seconds;
  its USB inventory identifies the1209:0001 whyred Ethernet gadget.
- After OS administrator authentication, the guarded helper added192.168.7.1/24
  as an alias only on that exact interface, retaining its link-local address.
  Ping to192.168.7.2 passed5/5, zero loss,2.118..10.564ms (average5.154ms).
  The Mac receives actual phone kernel WHYRED IO/exec bytes on UDP5140. Thus
  enumeration, bidirectional IP and live kernel-log transport are established.
  SSH is outside this image. Reconnect/long-run throughput remain untested.
- Continued live capture is checking root DSC limits, container creation and
  service exits. Those outcomes are still pending; USB success does not establish
  pkd/lsd/daemon stability. UART remains manual; device dumps/serials/logs private.

## Verified v89 build and package (2026-11-01)

- Final build source `f375a2f8cc2b9b29b08f19357dfdd5606969fcca`, full workflow
  [41346137446](https://github.com/timosid/ios-sweetwhyred/actions/runs/41346137446),
  job124966434206: all27 steps passed. RAMFS1,120,194/28 functions, USB1299/28
  driver functions plus4 board helpers, idle/service799 passed ASan+UBSan.
  Current namespace suite passed75 checks. Legacy0145 regression41346137417/
  job124966245310 passed66 checks/all8 steps after test-generator compatibility
  was retained. Earlier side41346036895 failed before compile on a missing new
  helper in its pinned old source; this was corrected without kernel changes.
- Both final ZIP provenance/SHA256/length/CRC, exact reviewed sources/fixtures/
  board helper bodies, linked ISA/cache/idle instructions and trusted loader/
  ADT/stock-DTB/layout/size guards passed. Combined0167+0168 replay also matches
  the authenticated v87 buildtree. Superseded v88 run41344572473 was cancelled;
  earlier v89 source036f6ad/run41346036804 supplies no candidate artifacts.
- V89 boot:22,331,392 bytes, payload21,520,992; image SHA256
  `668b16beddb2be2765b01ae6137b6bfc6b907072bca66d83a07ab65cf1becea1`.
  It retains the8MiB opt-in, USB snapshots and idle/service diagnostics and was
  flashed as recorded above.
- Next: dsc=1 file-limit/pressure/container/service evidence from continued live
  capture and manual UART. Logd/cache/container behavior remains unverified.

## V89 root DSC cache correction plus USB (2026-11-01)

- New v87 UART proves patch0166's UID-only bound is insufficient at early boot:
  DSC main6199pages plus temporary1970pages are owned by root, total8169 of8192.
  Pressure is data-quota, uid0 and file_limit_hits0. Later UID272 ownership had
  hidden this initialization phase. No pkd/lsd crash is present in this excerpt;
  its early cutoff does not establish service stability. The repeated attachment
  has identical bytes and adds no further outcome evidence.
- Patch0168 classifies /db/uuidtext/dsc entries inside the /var RAMFS, independent
  of owner, at insertion and replacement/swap rename. Classification remains with
  inodes and cache directory identities across moves/aliases/UID changes. Existing
  data is not evicted; the opt-in8MiB per-file bound and UID272 bound both apply.
  Unrelated root files and the global128MiB quota retain their limits.
- Local1,120,194 UBSan checks/28 actual functions plus75 namespace/rename checks
  pass, including root-created cache/temp, unrelated files, owner/namespace races,
  prepopulated directory insertion and actual replacement/swap renames. ARM64,
  noLSE/PAN and exact replay pass. Removing root or swap classification compiles
  then fails functional checks. See WHYRED-RAMFS-PRESSURE.md.
- V89 combines0168 with v88 USB0167, retained idle repair and lifecycle trace.
  Full CI/package/device results pending. Do not flash the USB-only v88 as a
  combined resource fix. Installed remains boot v87 / System v70, UART manual.

## V88 USB override release implementation (2026-11-01)

- V87 boot/System v70 is installed. New manual snapshots show UTMI1 low byte35,
  UTMI2 low byte40: MiCode's FS/non-drive signature plus TEST_MUX. PLL low-byte
  lock remains set; one event processed, raw value not supplied. No exact-MAC
  Ethernet interface appeared in90 seconds. New RAMFS/daemon outcomes pending.
- Patch0167 releases only TEST_MUX after controller halt and before DMA. It
  preserves CTRL1/interface-select/other CTRL2 bits, verifies the byte and restores
  the owned bit on failure. Unknown active override signatures stop safely.
  No new PLL/tune/power/reset/PMIC/TCSR/SMMU writes. See WHYRED-USB.md.
- Local1299 UBSan checks (28 driver/ring functions plus4 board helpers), two ARM64
  units, noLSE/PAN and exact replay pass. Both no-release/interface-clobber negative
  controls compile then fail functional assertions. Full CI/package/device test
  next. Keep the v87 cache bound, idle repair and service trace in the candidate.
- UART remains manual. Boot-only workflow authorized; obtain fresh physical
  Fastboot readiness once the next image is verified. No other partition writes.

## V87 boot flashed; hardware results pending (2026-11-01)

- The user recovered the complete v85 pressure record: data-quota, 8192/8192
  pages, hash8192 and added10657-freed2465=8192; only4 pages are unlinked.
  Rank0 confirms the UID272 DSC file uses6199 pages. This supports the v87
  resource policy; it does not establish a daemon or USB fix.
- After the user said they were rebooting into Fastboot, the exact private
  baseline device appeared. Fresh whyred/unlocked/boot64MiB/image/kernel/source/
  version and v85 rollback checks passed. Boot send/write and reboot returned
  OKAY at2026-11-01T19:54:28Z. Installed is now boot v87 / System v70.
- Read-only Mac Ethernet observation and new manual UART are pending. No other
  partition or host network configuration was changed. New USB snapshots,
  logd-file-limit/pressure and pkd/lsd records are needed. UART stays manual.
- Exact bluetoothd static analysis finds an exit0 path when its UART device
  and both Bluetooth IOKit matches are absent; the runtime branch remains
  unconfirmed. Do not equate clean exits with crashes or claim Bluetooth works.

## V87 cache-bound implementation (2026-11-01)

- New v85 UART recovers the damaged largest TOP row: logd's DSC cache is6199
  pages/96.86MiB,75.7% of128MiB. Its filename matches the main dyld cache UUID.
  TOP ranks are zero-based; the earlier rank1-largest interpretation was wrong.
  Containermanagerd then fails556-byte container metadata writes with ENOSPC.
- Patch0166 adds default-off whyred-logd-file-mb=N (1..64MiB per UID272 regular
  file). Next v87 tries8MiB. Oversized writes/truncate return EFBIG before page
  allocation; locked stores and final owner/size checks cover races/pageout and
  owner transfer. No global quota increase, file deletion or job policy change.
  Physical logd behavior and unified-log symbol availability need testing.
- Local UBSan1120166/25 actual functions,66 namespace checks, ARM64/noLSE/PAN,
  exact replay and functional limit/owner negative controls pass.
  See WHYRED-RAMFS-PRESSURE.md. This is a candidate resource fix; daemon exit
  causes/lsd faults and successful container creation remain open.
- V86 USB snapshot source1ebb9427e50bf5ff0cbd5e641849b7baa38beea7, CI41338911774
  job124944527693: all27 steps passed (USB637/RAMFS1120134/idle799 ASan+UBSan).
  Provenance/digests/CRC, exact sources/fixtures, linked ISA/cache/idle and loader/
  layout guards passed. Image SHAa3f3bd6839ac59ad8c86f8e0707253ba1aa08a46f0d8e4e186042cf7422cd260,
  22,331,392 bytes; unflashed. V87 combines those snapshots with the cache bound.
- Actual service traces: fairplayd.H2/bluetoothd spawn succeeds then exit0;
  suggestd exit2/reason0; pkd SIGABRT same stack; lsd SIGSEGV still reproduces.
  Services remain enabled. No more lost old UART can be supplied. Installed
  installed state is superseded by the v87 flash milestone above.

## Verified v87 image (2026-11-01)

- Build source `0e0895bd4709eb645dde32806d3876a969c86172`, workflow
  [41342210494](https://github.com/timosid/ios-sweetwhyred/actions/runs/41342210494),
  job `124954436881`: all 27 steps passed. RAMFS 1,120,166 checks across 25
  actual functions, USB 637 and idle/service 799 passed ASan+UBSan.
- Both final ZIPs passed source/run provenance, SHA256, byte length and CRC.
  Exact reviewed runtime sources/fixtures, linked ISA/cache/idle instructions,
  trusted loader/ADT/stock DTB, reserved layout and size checks passed.
- Packaged v87 boot is 22,331,392 bytes, payload 21,520,912; SHA256
  `60a583a1c4a2f2d0f89cf436333406f9e970c30c38b5d6d2ab6c660060c66f9e`.
  It enables the 8 MiB per-file UID272 bound and retains USB snapshots, owner
  tracing and idle/service changes. It was flashed as recorded above.
- Physical USB enumeration, logd behavior, container creation and daemon/lsd
  stability remain unverified. No further older UART is required.

## Active v86 USB connection diagnosis (2026-11-01)

- Installed remains boot v85 / System v70. User reports no new USB lines on
  cable connect/disconnect, but sees ue0 rx0/tx0 heartbeat. Thus the event thread
  runs; no frame exchange, Mac gadget enumeration or Ethernet link is established.
- Patch0165 adds read-only register snapshots before takeover, after endpoint/
  VBUS setup and from the event thread at one-second intervals. Runtime output
  requires a state change, ignoring DSTS frame-number-only differences. Maximum
  32 four-line records, then no more sampler MMIO reads. No controller/PHY policy,
  event ACK, DMA ownership, clock/reset/PMIC/PLL or charger-state changes.
- Samples cover UTMI test/control/line state, DWC3 status/event-ring/endpoint
  commands, QSCRATCH mux/VBUS, bus errors/timing and hardware parameters. MiCode's
  PHY high-impedance override is a possible distinguishable state, not an observed
  cause. See WHYRED-USB.md. Service causes remain pending separate UART output.
- Local actual28-function USB suite passes637 UBSan checks, including timing,
  raw output, change filtering, cap and read-only behavior. Both ARM64 units,
  zeroLSE/PAN audits and exact patch replay pass. Both dedup/cap negative controls
  fail their functional assertions after successful compilation. Full CI next; v86 retains v85's
  idle repair, service tracing and RAMFS owners. No new image/flash yet.

## V85 USB hardware observation (2026-11-01)

- User UART confirms powered-PHY wake and EP0 STARTTRANSFER command/result0x6
  with resource0. The driver passes its former guard, applies VBUS override
  and reaches controller RUN. No reset/connect/event lines were supplied yet.
- The Mac found no matching Ethernet interface during a 90-second observation;
  its USB device inventory also had no phone gadget at the sampled time. No
  host network changes were made. Controller RUN does not establish USB
  enumeration, working Ethernet or console delivery. Cable-reconnect feedback
  and further manual UART are pending; no subsequent register change is justified
  by this excerpt alone. Service exit causes and idle stability remain open.

## V85 boot flash milestone (2026-11-01)

- User confirmed Fastboot readiness for the verified v85 test. Fresh private
  identity, whyred product, unlocked state, 64MiB boot geometry, image/kernel and
  v82 rollback hashes passed. Boot send/write and reboot returned OKAY.
- Installed state is now boot v85 / System v70. No other partition was written.
  Device boot progress, idle stability, USB enumeration and service exit causes
  await user-supplied UART and host observation. UART capture remains manual.

## Active v85 follow-up (2026-11-01, idle panic and daemon exit causes)

- Installed phone remains boot v82 / System v70. User supplied an actual kernel
  panic: kernel_task tid102, preemption count1 in ARM64 user return; exact v82
  UUID/symbols verified. This differs from the separate lsd userspace SIGSEGV.
- Found an unsafe interrupt-stack path introduced by patch0120: proximate timer
  wait unmasks IRQs after Idle_context switches to CPU_ISTACKPTR, while the IRQ
  handler resets SP to that same top. Patch0163 uses masked pending-IRQ/WFI wait
  instead. This repairs a concrete overlap defect consistent with the panic;
  physical wakeup/panic absence still need testing. The assertion stays enabled.
- Patch0164 adds default-off whyred-service-trace=1: bounded PID, exec/spawn errno,
  activation state, exit wait status and OS reason for bluetoothd, fairplayd.H2,
  suggestd, lsd and pkd. No daemon cause/fix is yet proven. No jobs disabled.
  See WHYRED-IDLE-SERVICES.md for semantics, limits and evidence.
- Local UBSan799 checks pass, including 8000 concurrent report attempts. Changed
  cpu.c/kern_exec.c/kern_exit.c compile for ARM64; zero LSE/PAN audit, exact replay
  and both negative controls pass. Full CI will retain all v84 tests and add this
  suite. Verified v85 below combines these with USB and RAMFS owner tracing.
- V85 source `276c34608544fa2e3e1874f57500e8befccef022`, workflow
  [41329547329](https://github.com/timosid/ios-sweetwhyred/actions/runs/41329547329),
  job124916560517: all27 steps passed. New799, USB614 and RAMFS1120134 checks pass
  ASan+UBSan. Both ZIP provenance/digests/length/CRC and exact reviewed runtime/
  test sources pass. Linked cpu_idle contains pending-IRQ/DSB/WFI with no DAIFClr;
  linked ISA/cache, trusted loader/ADT/DTB/layout and size guards pass.
- Packaged v85 image SHA256
  `ed46661c5641b49bc59a79fe71df2c2bd8ce87070830de489699d80d89c707d8`,
  22,315,008 bytes, payload21,504,496. Boot args enable service trace, RAMFS owners
  and USB. It is unflashed; next step is physical Fastboot readiness followed by
  fresh device/product/unlock/64MiB/image/rollback checks and boot-only testing.
  No physical USB link, daemon exit cause or panic-resolution claim yet.
- V84 source d4ba66b3b00832f7610a6bd24887f2396d0694d8, CI41327819130/job124911379642:
  all26 steps pass, USB614 and RAMFS1120134 ASan+UBSan. Authenticated/package
  image SHA12e1b309a8f7af21fc4f079541943efb42faf603aef577fdf32595150305e8f8.
  It is unflashed and lacks the new idle fix/daemon trace; prefer v85 next.
- Full UART's first data-quota failure precedes first pkd attempt; Bluetooth/
  FairPlay restart attempts already precede quota exhaustion. Largest RAMFS owners
  remain unknown until TOP output. Preserve quotas and installed System v70.

## Active whyred follow-up (2026-11-01, EP0 activity plus RAMFS owners)

- V82 boot flash/reboot succeeded after the user's Fastboot-ready answer.
  Installed phone is now boot v82 / System v70. User UART confirms PHY wake,
  PLL lock, DWC3 ID 0x5533300a and ue0 address setup. Startup then stopped at the
  driver's strict missing-transfer-index guard before USB RUN; no host link yet.
- Patch 0162 follows Linux EP0's separate BUSY/activity tracking: successful
  EP0 STARTTRANSFER is not rejected solely for a zero resource index. Activity
  and HWO guard DMA reuse; data endpoints still require a nonzero resource.
  The resource result is read separately, with a bounded settle window and
  status/active checks. First control starts and failures log raw command results.
- A mid-control reset with active EP0 and no retirement index stops the controller
  and retains DMA rather than reusing it. This conservative limitation still
  needs device testing; it is not a full USB compliance claim.
- Local UBSan passes 614 actual USB checks. The model completes CDC setup with
  zero control indices, rejects active DMA reuse and missing data resources,
  and covers late result errors/reactivation. Restoring the old zero-index guard
  or removing the new activity guard fails the respective negative control.
  Both ARM64 compiles, exact patch replay and zero LSE/PAN object audits pass.
- Next full candidate v84 retains the v83 ownership diagnostics below. No v84
  image has been flashed. USB Ethernet and console delivery remain unconfirmed.

## Verified v83 RAMFS ownership diagnostic candidate

- Patch 0161 adds default-off `whyred-ramfs-top=1`, requiring the existing trace
  flag, to diagnose the observed 128 MiB quota exhaustion. On sampled quota
  failures it selects the four largest resident file-page owners and snapshots
  inode/pages/logical size/link count/UID/mapped-write state plus one bounded name
  and parent-directory name. It does not identify a last-writer process.
- Selection reuses the coherent locked hash walk; namespace searches share a
  65,536-entry budget. Fixed metadata/name arrays are copied under the mount lock
  and printed after unlocking, with no node pointers escaping. Names are bounded,
  printable and explicitly marked when truncated; a missing alias stays unknown.
  Existing 32-record sampling limits and quota/error/allocation policy are retained.
- Local UBSan passes 1,120,134 checks, including ordering/ties, linked/unlinked
  owners, name truncation/control-byte filtering, snapshot lifetime, the name-walk
  budget and default-off behavior. Disabling collection fails the new cases.
  The retained 66 namespace/readdir/sync checks pass. ARM64 compilation passes
  without a >4 KiB frame warning; object LSE/PAN audit is zero.
- Source `f3c036f56057ea4e162d2aeb975e717c2fa7ba69`, workflow
  [41325125813](https://github.com/timosid/ios-sweetwhyred/actions/runs/41325125813),
  job `124903349713`: all 26 steps succeeded, including 1,120,134 pressure/owner
  ASan+UBSan checks and 601 retained USB checks. ZIP provenance/digests/CRC,
  reviewed sources, linked ISA/cache path, loader and layout guards passed.
- Packaged v83 image SHA256
  `90bb7b1a1871c1d1e91a7da83be0b7f2351509a9631f3063758f3ce88982685d`.
  It has not been flashed and retains the old EP0 check; v84 supersedes it for
  the next combined USB/ownership test. Physical owner output is still pending.

## Verified v82 USB PHY shutdown-resume candidate

- User-supplied v81 UART identifies handoff status 6 before any DWC3 register
  access. Domain/clocks passed, while the legacy PHY POWER_DOWN bit remained set
  and PLL lock was absent. The ID/GCTL zeros were unsampled, not proof of a bad
  controller. Current installed phone remains boot v81 / System v70.
- Patch 0160 adds a narrow exit from the exact major-rev=1 shutdown low-byte
  state 0x23, using MiCode's 0x22 enable value. Mode 2 additionally requires the
  reference gate on and QUSB/AHB2PHY resets deasserted. It waits 150 us and polls
  for at most another 1000 us. Failure restores 0x23 before undoing new clock
  votes; status 8 distinguishes an attempted wake timeout. Mode 1 stays read-only.
- This retains bootloader tuning and requires powered rails. It adds no PMIC,
  PLL tuning, reset-controller or SMMU writes and is not full cold PHY init.
  Expanded diagnostics report before/after, attempt/polls/restore and explicitly
  distinguish an unsampled controller from register values actually read.
- Local UBSan passes 601 checks, including delayed/failed PLL, rejected writes,
  missing reference gate, held resets, wrong PHY states and ordered rollback.
  Disabling the new wake branch is rejected by the strengthened tests. Exact
  patch replay and both ARM64 compiles pass; LSE/PAN object audits find zero.
- Source `c6826995ba8de977d97f4e53e1d908d18f664ca1`, full workflow
  [41323121100](https://github.com/timosid/ios-sweetwhyred/actions/runs/41323121100),
  job `124897356634`: all 26 steps succeeded, including 601 USB ASan+UBSan checks.
  Final ZIP provenance/digests/length/CRC, exact sources, linked ISA/cache path,
  trusted loader/ADT/DTB, layout and size guards passed.
- Boot v82 is 22,315,008 bytes, payload 21,504,080 bytes; SHA256
  `55c6a5471135fd1594d9fcc96a9ca94b6246d8e50f268ba5932aeb06f913fb9c`.
  V82 was subsequently flashed as recorded above; installed state is v82/System v70.
- The user's v81 photograph now identifies the RAMFS failure as `data-quota`:
  8192/8192 pages, matching the hash sum and additions minus frees, i.e. 128 MiB.
  Zero-link pages are only 67. See `WHYRED-RAMFS-PRESSURE.md`; largest file owners
  remain unknown. Preparing bounded ownership diagnostics; quotas are unchanged.
- The user also observes repeated `exec bluetoothd` / `exec fairplayd.H2`.
  Each name already has 11+16 occurrences in the preserved v79 fragments.
  Authenticated System v70 config has fairplayd KeepAlive=true and bluetoothd
  KeepAlive SuccessfulExit=false; neither redirects stdout/stderr to console.
  The kernel's exec line precedes completion and has no PID/result. No target
  termination cause is recorded, so failed exec, self-exit and crash/kill remain
  unresolved. No services or restart policies were changed.

## Verified v81 USB baseline and hardware observation

- The user resumed USB work and selected Ethernet plus live logs first. SSH is
  outside this candidate. Patch 0159 ports the existing CDC-ECM driver to the
  whyred SDM660 registers and powered bootloader handoff; see `WHYRED-USB.md`.
  `whyred-usb=2` explicitly enables the gadget; the default remains off.
- Startup runs after network initialization, independently of UFS. The existing
  in-memory console ring feeds bounded nonblocking UDP to 192.168.7.1:5140.
  No System image changes or persistent storage writes are added.
- Local UBSan passes 566 checks executing 27 actual kernel functions with
  modeled MMIO/kernel services. The two changed ARM64 units compile, with zero
  LSE/PAN instructions. Exact late-patch replay matches all three reviewed files;
  the UFS source remains unchanged. The macOS interface helper self-test passes.
- Initial DMA cache publication is checked before event-ring installation or
  STARTTRANSFER. The strengthened harness rejects the previous missing-clean
  version; the corrected driver passes. Physical cache coherence remains untested.
- Source `7ccdf8dda98cdc2ead91f171c51607ddcae29890`, full workflow
  [41319898167](https://github.com/timosid/ios-sweetwhyred/actions/runs/41319898167),
  job `124888314335`: all 26 steps succeeded, including 566 USB checks with
  ASan+UBSan, the full linked ARM64 kernel and all retained checks. Earlier USB
  run 41319155786 was superseded and cancelled; it supplies no candidate artifacts.
- Both final ZIPs match GitHub SHA256/length and pass CRC. All four USB/ring/init
  sources match the reviewed buildtree and test report. Linked-code audit found
  zero LSE/PAN instructions; the linked cache-maintenance path includes physical
  translation, `dc civac` and `dsb sy`. Loader/ADT/stock DTB, layout and size guards
  passed. Boot v81 retains the v80 diagnostics below and installed System v70.
- Boot v81: 22,315,008 bytes, payload 21,504,080 bytes, 496-byte command line with
  `whyred-usb=2`; image SHA256
  `8b1300ed5f5c9524bc5b61722479a5f363b8df4391b8b71b06a10130f1706b41`.
- Temporary `fastboot boot` returned OKAY, but the phone remained in Fastboot;
  the user confirmed this command does not work on this handset. The user then
  explicitly authorized flashing boot. Identity/product/unlocked/64-MiB partition,
  v81 SHA256 and the preserved v79 rollback image passed fresh checks.
- Sending/writing boot v81 and reboot each returned OKAY. The installed baseline
  is now boot v81 / System v70; System was not written. Fastboot disappeared after
  reboot. No CDC Ethernet interface or UDP console bytes have yet been observed;
  enumeration, ping and actual delivery remain unconfirmed.
- The user's UART confirms stop at PHY preflight (status 6), powered-down legacy
  PHY and no sampled controller. v82 above addresses this observed shutdown
  state. Physical wake, DMA visibility and host compatibility remain unconfirmed.
- macOS 26 exposes USB via IOService IOUSBHostDevice / SPUSBHostDataType. The
  legacy IOUSB-plane/SPUSBDataType query returned empty even with Fastboot present;
  use the current inventory. Raw UART/serials remain private and user-supplied.

## Retained v80 RAMFS diagnostics

- Boot v79 and System v70 are the inherited hardware baseline. Filesystem
  tracing reproduced container metadata write ENOSPC; the quota versus
  allocation/reclamation cause is unresolved. A working graphical scene is
  unconfirmed. USB Ethernet/live console work is active as described above.
- Patch 0158 adds default-off development diagnostics for data quota, missing
  data pages, nonwaiting page-array allocations and attribute snapshot failures.
  It retains the existing quotas, allocation flags, operation results and storage
  write policy. See `WHYRED-RAMFS-PRESSURE.md` for record semantics and limits.
- Local host checks pass with UBSan: five injected failure branches, short-write
  residuals, open-unlinked and named-vnode reclamation, 1.1 million failures for
  the output budget and 10,000 allocation/reclaim lifetimes. Existing 66 namespace,
  readdir64 and sync checks pass on the candidate. The changed C unit compiles to
  ARM64 using the authenticated v79 generated headers.
- Local AddressSanitizer cannot run in the current host environment: even a
  standalone hello-world sanitizer binary exits with SIGILL before main. This
  is not a passing local ASan result. Both ASan and UBSan passed on the CI runner.
- Source `2e17298133f5639668ce5366f99b7334bdc01e11`, full workflow
  [41314180439](https://github.com/timosid/ios-sweetwhyred/actions/runs/41314180439),
  job `124870632893`: all 25 steps succeeded. This includes the full linked ARM64
  kernel, the new pressure suite and all retained storage/graphics/AKS checks.
- Both downloaded CI ZIPs matched their GitHub SHA256 digests. Exact RAMFS source
  and all retained reviewed runtime files match the buildtree. Linked-code audit
  found zero LSE/PAN instructions. Boot v80 was packaged with the proven loader,
  ADT and stock DTB tail; layout and payload guards passed.
- Boot v80: 22,310,912 bytes, payload 21,503,680 bytes; image SHA256
  `a52274cdec6a8afbb0f2f7564ac6a1548925edc4137165fd202e3de63664367a`.
  It enables `whyred-ramfs-trace=1`. No phone command, flash or v80 hardware test
  has occurred; the inherited installed System v70 remains required.
- Next: obtain RAMFS pressure records during an explicitly authorized boot-only
  test. The observed ENOSPC cause and the relation to container crashes/empty
  frames remain unresolved. Private manifests, UART, decompilation and transfer
  verification remain outside this repository.
