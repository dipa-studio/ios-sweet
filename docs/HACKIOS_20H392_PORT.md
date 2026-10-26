# HackiOS and 20H392 integration audit

Offline audit, 2026-10-25. No new VM was launched. Source images and historical
captures were preserved. This is a port design, not a claim of stable boot.

## Matched components

| Contract | HackiOS reference | Current ios-sweet reference |
| --- | --- | --- |
| Source | kernel `d82c64a3a31cd27a0a0afbf6e213e467e44b1b4c`, userland `a79ff0772a3454fd1ef127e181e5b3bce6c9ce18` | kernel artifact 0086; 20H392 userland overlay |
| XNU | 8796.121.2 | 8796.141.3 |
| Loader | EFI, XNUP named payload entries | direct boot stub, SWEETXNU v1 |
| Root | APFS memory disks, system plus bootstrap image | HFS image through virtio-blk |
| Writable data | RAMFS mounted on `/private/var`, populated from skeleton | Existing HFS `/private/var`; RAMFS mount fails |
| QEMU | virt, GICv3, cortex-a76, one CPU, TCG | Same defaults |
| Input polling | 8 ms | 8 ms |
| Exception tracing | Not enabled by reference shell runner | Enabled by default; now selectable |

References: `github-clone/hackios-xnu-kernel/xnu/README.md`,
`qemu/run-ios.sh`, `qemu/run.sh`, `xnuloader/loader.c`,
`xnu/files/osfmk/arm64/gic_v3_irq.c`, and
`github-clone/hackios-xnu-userland/userland/src/init.c`.
The local userland clone has edits in inject.c/inject_sb.c; its HEAD alone
does not identify those working-tree files. The committed overlay is
`userland/patches/20H392-redwood.patch`.

The kernel binary and loader cannot be exchanged independently. Importing
the full redwood.patch would also cross XNU versions and duplicate existing
SWEET changes. A successful 16.5 setup is a reference contract; it does not
establish compatibility of its private framework offsets with 20H392.

## What the stopped run actually establishes

The `/sbin/launchd` extracted from root-0084i is HackiOS init, UUID
`ED425049-F08B-3ABE-A0CB-6884982F60D1`, not Apple's launchd. Its non-PIE
text begins at 0x100000000. The repeated ELR 0x100003288 is a store in its
64 MiB anonymous-memory test. The instruction following its syscall is
0x100006934; that return PC alone does not identify a syscall number.

The latest trace contains 783 unique store-page faults at 16 KiB spacing,
covering 12.234375 MiB of pages. The final fault returns to EL0. Successful
historical runs complete 4096 such faults and start launchd.ios. Therefore
this signature is demand paging, not evidence of a fatal exception loop.
The incomplete test is the last observed userspace stage, not a proven
permanent deadlock or a demonstrated VM fault implementation bug.

Comparing identical progress (782 complete gaps between the first 783
store faults), the IRQ counts are:

| Run | IRQs in complete gaps | Median per gap | Maximum per gap |
| --- | ---: | ---: | ---: |
| run20h-hour | 4 | 0 | 2 |
| run20h-0086-repeat-wake-interactive | 17 | 0 | 1 |
| run20h-0086-repeatable-wake-1h | 1076 | 1 | 43 |

Derived data: `research/offline-0086-irq-comparison.json`. These counts show
different interrupt activity per unit of userspace progress. They do not
identify interrupt IDs or establish whether interrupts cause slow progress
or accumulate because emulation is slower. The exception log has no time
stamps. Last guest msgbuf time is not the exact guest time of a host snapshot.

The latest CPU samples at `_ml_get_timebase+0x18` return to
`_sched_clutch_processor_enqueue+0x9c` and
`_ledger_entry_check_new_balance+0x12c`. They show scheduler/accounting
contexts, not proof of idle or a timer worker monopolizing the CPU.

The successful run mounts HFS at guest 31.201541 seconds and starts
launchd.ios at 32.668098. The latest mounts at 32.545890, reaches
load_init_program at 59.381416, and attempts /sbin/launchd at 74.193185.
Delay already appears before the memory test; skipping the test would not
by itself demonstrate that the underlying performance problem was fixed.

## Minimal port design and rollback

1. Keep 0086/HFS as the control. Retain its kernel, payload, image and raw logs.
   Do not add RAMFS merely to remove a diagnostic FAIL line: a successful
   mount would hide the existing migration plist, containers and other data.
2. For the HFS route, design an explicit init data-volume mode that verifies
   the existing writable `/private/var` without mounting RAMFS or restoring
   a phone partition. Preserve ownership, skeleton and 20H392 migration
   state. Build a separate init artifact; install only in a disposable image.
   Default HackiOS behavior should remain unchanged. Rollback uses original
   init and the existing source image.
3. For a fully matched HackiOS route, retain its EFI/XNUP loader, APFS drivers,
   system/bootstrap disks and RAMFS population together. Port the 20H392
   framework hooks and data skeleton to that route. This is a separate
   experiment, not a replacement for the HFS control or a small kernel patch.
4. Audit GIC before proposing a kernel fix: HackiOS drains pending IARs and
   masks unknown IRQs; SWEET handles one IAR per entry. Collect the actual
   interrupt IDs and scheduling progress before deciding which behavior
   needs changing. Both acknowledge the timer in broadly the same order.
   Do not import heterogeneous-core scheduler changes to explain a single
   vCPU problem without evidence.

The three strongest unresolved hypotheses are host/emulation throughput
variation (including trace overhead), excessive guest interrupt/scheduling
work, and a guest scheduling/VM progress defect during init. Missing RAMFS
is a proven compatibility gap but cannot alone explain the difference
between runs using the same recorded image and kernel. Later SpringBoard
service failures are a separate stage.

## Prepared verification, not executed

### P1: reproducible run manifest

`tools/qemu-sweet.py` writes `run-manifest.json` before launching QEMU and
finalises it from a `finally` block, including failure and interrupt paths.
It records:

- `schema_version`, `state`, `host_started`/`host_finished` in local ISO-8601
  with UTC offset, matching Unix epochs and `duration_secs`;
- `qemu_binary` and the first line of `qemu-system-aarch64 --version`;
- the full QEMU `argv`;
- payload path, size and SHA-256;
- `kernel` and `sample_kernel` objects with absolute path, size and streamed
  SHA-256 (the same file is hashed once per manifest);
- the exact effective `boot_args` after `cpus=` replacement and extra
  arguments, before NUL padding;
- `extra_cmdline`, `trace`, `disk_snapshot`;
- disk absolute path, size and `mtime_ns` (not a content hash);
- on exit, `stop_reason`, `timed_out`, `qemu_returncode`, `runner_exit_code`,
  `result_status` and any runner `error`.

`--trace errors` omits per-exception logging while retaining
guest_errors/unimp. Default `--trace exceptions` preserves historical
behavior. This reduces trace volume; a boot-speed improvement is unmeasured.
Use a fresh output directory for each comparison.

Static checks, none of which starts QEMU:

```
python tools/test-qemu-manifest.py     # manifest fields, SHA, boot args, finalisation
python tools/p0-preflight.py           # payload/kernel/sampler prerequisites
python -m py_compile tools/qemu-sweet.py tools/test-qemu-manifest.py tools/p0-preflight.py
python tools/validate-repo.py          # run under WSL on this host if bash differs
```

### P0: PID 1 diagnostic, run 2026-10-25 (900 s)

The prepared payload changes only the 608-byte boot-args field of the existing
0086 payload. It keeps the external HFS root and adds PID 1's pre-handoff
process name to the sampler:

```
sweetsample=launchd,SpringBoard,backboardd,lsd,iconservicesagen
```

The 0086 kernel contains `_sweet_sample_names`, `_sweet_sample_task`,
`_sweet_sample_start`, `_initproc`, `_proc_struct_size` and
`_kernel_stack_size`. Disassembly of its virtio-blk init path shows
`PE_parse_boot_argn("sweetsample", ..., 0x80)` followed by a call to
`_sweet_sample_start`; this is the QEMU `/dev/vblk0` path, not the phone UFS
path. The sampler matches `proc_name()` (`p_comm`, the executable basename)
against the comma-separated list, iterates all processes, and reads each
thread's saved user state through `find_user_regs()`. The historical
`run0084b/snap006` capture already shows the sampler emitting a
`sweet_sample` header and a user stack for `launchd.ios[1]` after handoff.
The pre-handoff name is `launchd` by construction; static preflight passed,
but the P0 run did not demonstrate it. The first sampler sample occurs after
handoff, and `proc_name()` is by then `launchd.ios`, so the exact `launchd`
entry does not match.

Authorised bounded command:

```
python tools/qemu-sweet.py research/vm/payload-0086-launchd-sample.bin research/vm/run20h-0086-launchd-stack --secs 900 --disk research/vm/root-0084i.img --disk-snapshot --input --display gtk --sample-every 60 --sample-kernel xnu/out-0086-trace/kernel.development.sweet --trace errors
```

`--disk-snapshot` is mandatory; the source image is never written. Kernel and
root are held fixed relative to the stalled run; the P0 payload differs only
in its boot-args field. `--sample-every 60` captures `regs.txt`, `fb.png`,
`msgbuf.bin` and `msgbuf.txt`; the kernel sampler waits 90 s after virtio-blk
attach (guest ~121 s), then samples every 120 s, at most 10 times. A 900 s run
can contain samples 0 through 5 if the scheduler continues to service the
sampler thread; P0 captured exactly those six.

P0 result, `research/vm/run20h-0086-launchd-stack`:

- Manifest: kernel 0086 SHA-256 `11bb2b36...`, payload SHA-256
  `0f31237b...`, `root-0084i.img`, `--disk-snapshot`, 900.751 s,
  `stop_reason=deadline`, QEMU return 1, runner return 0, `not_decoded`.
  `serial.txt` and `qemu.log` are empty; 14 snapshots were captured.
- PID 1 reached Apple launchd: `exec launchd.ios` at 33.071560 s,
  `exec launchd_cache_loader` at 49.876722 s, `exec SpringBoard` at
  54.048638 s, `exec backboardd` at 95.920103 s, `exec lsd` at 103.384173 s,
  `SWEET FB: display on` at 154.799706 s. New `exec ...` records continue to
  guest 837.365 s. `launchd.ios:1` owns the listening sockets logged near
  52.5 s. This is a live PID 1, not a memory-test stall.
- No `SMP launchd[1]` or `SMP launchd.ios[1]` appears. Sample markers are at
  121.191808, 241.236065, 375.822697, 501.719598, 621.738712 and 741.763652 s.
  The sampler sleeps 90 s from virtio-blk attach, so sample 0 is after the
  33.07 s handoff. The payload targets `launchd`; after handoff the exact
  `proc_name()` is `launchd.ios`. The absence is an instrumentation mismatch,
  not evidence that PID 1 is dead. The older stalled run did not request PID 1
  at all: its `ram.bin` contains
  `sweetsample=SpringBoard,backboardd,lsd,iconservicesagen`.
- `test_memory()` returned. The custom `/sbin/launchd` calls it before
  `run_rc()`; `/etc/rc` is `exec /sbin/launchd.ios`, which occurred at
  33.071560 s. P0 used `--trace errors`, so no per-fault count or FAR series
  exists; the older 783-of-4096 series is not comparable and does not justify
  a memory-test skip.
- Scheduler: the sample intervals are 120.044, 134.587, 125.897, 120.019 and
  120.025 s. The SpringBoard header inside sample 1 is delayed to 255.816412 s
  (14.58 s after the marker), but later markers still advance. Snapshot PCs
  are mostly `_ml_get_timebase`/`el0_irq_vector_64_long`; `snap014` is EL0
  `libsystem_malloc._tiny_malloc_from_free_list`; final `regs.txt` is EL0
  `libobjc.sidetable_clearDeallocating` (slide 0x7d6c000). This is not a
  global scheduler deadlock, but those PCs are not PID 1-attributable.
- The remaining UI blocker is LaunchServices/lsd, not PID 1. At 741 s:
  SpringBoard t0 -> `_LAUNCH_SERVICES_WAS_ASKED_TO_PERFORM_BLOCKING_IO_ON_THE_MAIN_QUEUE`
  -> `_LSCopyServerStore` -> synchronous XPC wait; `lsd` ->
  `performJournalRecovery`; `iconservicesagen` ->
  `_LAUNCH_SERVICES_IS_RESEEDING_ITS_DATABASE_AND_MAY_BLOCK`. The final frame
  is the Apple logo. This is the known slow lsd recovery path; 900 s ended
  before it cleared.
- The older PID 1 stall did not reproduce. Root/kernel match, but boot args,
  trace mode and wake/sample options differ, and the older command line was
  not captured. The old `qemu.log` has 9,767 exception records (1,175,320
  bytes); P0's `--trace errors` log is empty. The strongest remaining
  hypothesis for the old stall is run-environment/TCG or fault-handling
  nondeterminism, not a deterministic init bug; confidence is medium-low.
- Source images were not written: `root-0084i.img` remains 17,179,869,184
  bytes with mtime `2026-10-24T20:54:01.1462492Z`, and the base image is
  unchanged. The snapshot overlay was discarded; no QEMU process remains.

Inspect each snapshot in order:

```
Get-ChildItem research/vm/run20h-0086-launchd-stack -Recurse -Filter msgbuf.txt |
  Select-String 'SMP (--- sample|launchd)'
Get-Content research/vm/run20h-0086-launchd-stack/snap006/regs.txt
```

Expected sampler shape only if the exact name and timing matched (not observed
in P0):

```
SMP --- sample 0
SMP launchd[1] slide 0x... mh 0x...
SMP launchd t0 pc 0x... lr 0x... sp 0x... bt 0x... 0x... ...
```

Actual P0 output contains only the sample markers plus `lsd`, `backboardd`,
`SpringBoard` and `iconservicesagen` headers; no PID 1 header or stack.

Symbolicate the user PC against the deployed init and a kernel PC against
0086:

```
research/ipsw-tools/bin/ipsw.exe macho a2s github-clone/hackios-xnu-userland/prebuilt/userland/init 0x100003288
research/ipsw-tools/bin/ipsw.exe macho a2s xnu/out-0086-trace/kernel.development.sweet 0xfffffe...
```

Known mapping: `0x100003288` is `_main + 8376`, the 64 MiB memory-test store
that generated the repeated ELR. `0x100006934` is `_mini_syscall + 32`, the
return PC after a syscall. `_main` starts at `0x1000011d0`; `_run_rc` at
`0x1000040a8`.

Interpretation, in order of evidence:

| Observation | Conclusion |
| --- | --- |
| PID 1 `pc` stays in `_main` around `+0x20b8`, and `regs.txt` PC is the same EL0 address | PID 1 is still executing the userland memory test; not a kernel deadlock at that instant. |
| PID 1 `pc` is in `_main`, while `regs.txt` PC resolves to `_vm_fault`, `_pmap_enter` or `_vm_page_*` | The current vCPU is servicing a demand fault for PID 1; compare fault progress and IRQ counts. |
| PID 1 `pc` is at `_mini_syscall`/`_mmap`, and the current PC resolves to `_machine_idle`, `_sched_*`, `_thread_block` or a wait queue | PID 1 is blocked/waiting; the kernel is scheduling or idle rather than running its store loop. |
| Current PC resolves to `_sleh_*`, `_gic_*`, `_exception_*` or timer interrupt code | The sample landed in interrupt/exception handling; check whether IRQ work dominates progress. |
| `SMP --- sample` markers stop advancing while msgbuf otherwise grows | The sampler thread is starved too; suspect kernel/scheduler starvation rather than a PID 1-only user loop. |
| Sample markers advance but no `SMP launchd[1]` ever appears | Process-name or sampler plumbing mismatch. Do not infer PID 1 is dead; inspect `proc_name` and the boot-arg list. |

The sampler prints PID 1's saved user state, not its kernel stack. `regs.txt`
shows only the single running vCPU at snapshot time. If those two views do not
settle the category, use the existing kernel-stack inspection scripts as a
reference and update their hard-coded QMP port/kernel before relying on them;
do not treat a user PC alone as proof of the kernel wait site.

Comparison anchors from the preserved runs:

- `run20h-hour/snap001`: HFS mount 31.201541 s, `/sbin/launchd` load
  31.297430 s, `exec launchd.ios` 32.668098 s, `exec SpringBoard`
  59.823064 s. The full trace completes 4096 store faults at ELR
  `0x100003288` and the one-hour run eventually reached the Home Screen.
- `run20h-0086-launchd-stack/snap001`: HFS mount 31.264200 s,
  `/sbin/launchd` load 31.384985 s, `exec launchd.ios` 33.071560 s,
  `exec SpringBoard` 54.048638 s, display on 154.799706 s; final frame at
  900 s is the Apple logo. This run did not capture a PID-1 stack; see the
  instrumentation explanation above.
- `run20h-0086-repeatable-wake-1h/snap002`: HFS mount 32.545890 s, load
  59.381416 s, `/sbin/launchd` attempt 74.193185 s, no `exec launchd.ios`
  through the captured msgbuf. Samples 0-3 are at 143.227269, 351.848390,
  477.208572 and 597.241322 s. That payload did not include `launchd`, so
  the absence of a PID 1 sample is expected and is not evidence of a dead
  process. The sample intervals were 208.621, 125.360 and 120.033 seconds
  against a nominal 120 seconds; the sampler thread itself was delayed, so
  sample spacing is also evidence about scheduler progress.

The old stalled run diverged before the memory test: its `load_init_program`
was 28.084 s later and HFS mount 1.344 s later than the successful run. P0
did not reproduce that divergence; it mounted at 31.264200 s, loaded
`/sbin/launchd` at 31.384985 s, and completed the handoff at 33.071560 s.
Therefore there is no evidence for a `test_memory()` skip, and none should be
added to the boot path.

If a pre-handoff PID 1 stack is still required, the smallest change is
instrumentation-only: parse an opt-in first-sample delay (default 90 s,
unchanged when absent) and include both `launchd` and `launchd.ios` in the
payload's `sweetsample` list. This needs separate approval and a new bounded
run; the kernel boot path must remain unchanged when the argument is absent.

On a later authorised bounded test, hold payload, disk snapshot, CPU,
memory, input and capture intervals fixed. Compare trace modes separately
from userland/kernel changes. Require init completion, launchd.ios, cache
mapping, SpringBoard/backboardd and visible menu interaction. For the present
UI blocker, target lsd/LaunchServices journal recovery rather than PID 1, and
allow more than 900 s or capture a targeted lsd trace.

## LaunchServices database audit (2026-10-25)

Read-only inspection of `root-0084i.img` found no LaunchServices store. The
lsd data container is
`/private/var/mobile/Containers/Data/InternalDaemon/777AD767-B07D-4928-B178-4C6F0FE3C1B0`;
its metadata identifies `com.apple.lsd` with uid/gid 501. `Library/Caches` is
empty, and `find /private/var -iname '*.csstore'` returns nothing.
`/private/var/db/lsd` is empty too. Container and cache directories are 0755
501:501, with no symlinks; the lsd launch daemon runs as `mobile` (501), so the
missing store is not a Unix-permission failure.

LaunchServices' string table contains `LS_DATABASE_DIR`,
`_LSDefaultsBaseSystemContainerURL`, `Library/Caches`,
`LS_NAME_PREFIX=com.apple.LaunchServices`, and
`%s-%03llu-v2.csstore`. The expected store is therefore in the lsd container's
cache, not in `/private/var/db/lsd` (that directory holds the schemes and
identifier plists). Its absence triggers the first-boot rebuild.

`--disk-snapshot` maps to QEMU `snapshot=on`: the base image is unchanged and
guest writes are discarded. Because the base contains no store, every
snapshot-backed boot repeats the cold rebuild. The historical `run20h-hour`
also used `--disk-snapshot`; it completed the rebuild after about 30-34
minutes. Snapshot mode is not itself a corruption source; it prevents the
rebuilt store from persisting.

The historical lsd t2 stack at guest 2065.556906 s is:

```text
_semaphore_wait_trap
  -> _dispatch_semaphore_wait_slow
  -> __LSServer_LSEnumerateAndRegisterAllBundles_block_invoke.773
  -> -[LSRebuildStatisticsGatherer performContainerizedContentScan:]
  -> -[LSRebuildStatisticsGatherer performRebuild:]
  -> __LSServer_LSEnumerateAndRegisterAllBundles
  -> __LAUNCH_SERVICES_IS_REBUILDING_THE_DATABASE_BECAUSE_IT_DID_NOT_EXIST
```

lsd t0 is simultaneously parked in `performJournalRecovery` ->
`dispatch_sync_f_slow`. By sample 17 at guest 2185.577083 s lsd is back in the
normal `CFRunLoop`. `exec installd` is at 2041.870202 s; display off at
2083.424946 s, on at 2501.397564 s; the first Home Screen snapshot is at guest
2528.230459 s. The rebuild completion window is therefore 2065.556906 to
2185.577083 s.

P0 sample 5 at 741.763652 s shows the same phase: lsd t2 is in
`MIInstalledInfoGatherer _fixUpForBuiltInAppParallelPlaceholder` waiting for
the container XPC, while historical sample 5 at 745.284743 s is in
`MIInstalledInfoGatherer _populatePlaceholderRecordValues` waiting on the
installation-identity semaphore. P0 t0 has the same `performJournalRecovery`
stack as historical samples 1-16. P0 stopped at guest 837.365 s, before the
historical completion window. Its lsd `fsync` was observed at 375.822697 s and
had completed by 501.719598 s.

HFS source audit: Apple hfs-627.100.6 is built in; the only SWEET changes are
the dirty-root mount allowance, hardlink log throttling, and the VFS
`RENAME_SWAP` -> `VNOP_EXCHANGE` fallback. `hfs_vnop_fsync`/`hfs_fsync` are
implemented, `hfs_vnop_renamex` accepts only `VFS_RENAME_EXCL`,
`hfs_vnop_mmap` returns `ENOTSUP` intentionally so the UBC cluster layer
performs the mapping, and the locking/journal code is unmodified. The boot log
shows `jnl ... reset` and `hfs: mounted`, with no HFS/EIO/ENOTSUP/fsync/rename/
mmap failure. No syscall failure was found to attribute the delay to HFS.

Conclusion: this is a slow first-boot LaunchServices rebuild, not a proven lsd
deadlock or failing HFS I/O. The 900 s P0 deadline was too short. A minimal
control run should use the same 0086 inputs, `--disk-snapshot`, a 3,000 s host
limit and 300 s captures, with a wake at 2,300 and 2,500 s; the historical lsd
completion window is 2,065.6-2,185.6 s and the first Home Screen is at
2,528.23 s. Do not patch lsd or delete the database. A persistent disposable
clone is only needed if the rebuild must be paid once rather than every
snapshot boot.

## 0086 3,000 s control run (2026-10-25)

The single authorized control run is
`research/vm/run20h-0086-control-3000/`. It used the prepared 0086 payload
(`0f31237b...`), kernel `xnu/out-0086-trace/kernel.development.sweet`
(`11bb2b36...`), `root-0084i.img`, one vCPU, `--disk-snapshot`,
`--trace errors`, and 300 s snapshots. Host duration was 3,000.611 s;
`stop_reason=deadline`, QEMU return 1, runner return 0, `not_decoded`. No panic
was found and no QEMU process remained. The base image stayed
17,179,869,184 bytes with mtime `2026-10-24T20:54:01Z`.

| Event | `run20h-hour` | Control run | Shift |
| --- | ---: | ---: | ---: |
| `exec installd` | 2041.870202 | 2633.344571 | +591.47 |
| display off | 2083.424946 | 2677.178789 | +593.75 |
| observed lsd normal | 2185.577083 | 2832.950107 | +647.37 |
| display on | 2501.397564 | none | none |
| first Home Screen | 2528.230459 | none | none |

The control's last captured guest time was 2,882.845565 s. `home-check` at
guest 2,596.712297 s still showed the Apple logo, and the last framebuffer
swap in the captured ring was at 859.414372 s. `display off` at
2,677.178789 s had no matching `display on`; `settings-check-1`,
`settings-check-2` and the final frame are black. This is a panel-off state,
not evidence of a visible Settings app.

LaunchServices did finish, later than historical: lsd t0 was still in
`performJournalRecovery`/`dispatch_sync_f_slow` at 2,591.159060 s, was logging
an `NSError` redacted description at 2,712.910249 s, and was in the normal
`CFRunLoop` by 2,832.950107 s. All captured lsd worker threads were idle at
that point. SpringBoard moved from `_LSCopyServerStore` at 2,591.166561 s to
`CHSChronoServicesConnection descriptors:` at 2,712.928808 s and IconServices
`-[ISDefaults init]` at 2,832.961794 s. `iconservicesagen` was decoding an
`_LSCopyServerStore` XPC reply at 2,832.946198 s. This is post-recovery
initialization, not an unchanged deadlock.

The historical lsd-to-Home interval was 342.653376 s. Applying it to the
control's lsd completion window (2,712.91-2,832.95 s) gives an expected Home
time of 3,055.6-3,175.6 s, while the host deadline was 3,000.611 s. The run
was therefore about 55-175 s short, assuming the historical interval held.
The control is **not reproduced**, but it is not `INCONCLUSIVE` under the
stated 2,600 s rule and it does not establish a new root cause.

The QMP Settings taps at host 2,650.067/2,650.888 and
2,820.198/2,821.017 (`qmp 4492,7795` -> panel `148,571`), and the wake taps,
produced no `SWEET HID: touch` records. The last captured guest touch is at
491.508128 s; the early 424-491 s burst shows the HID path had worked. The
later input failure is a separate test limitation and was not investigated
further because the Home Screen result does not depend on it. Do not start
another QEMU run without explicit approval; if one is approved, use a
3,300-3,600 s limit or a persistent disposable clone, and diagnose the input
path separately.

REA native decompilation is unavailable in this Windows session (Ghidra
unconfigured and this provider's Windows target support excludes Mach-O).
Findings here use local source, Mach-O inspection/disassembly with ipsw,
read-only image extraction and captured traces; they are not REA decompiler
output. No new engine was installed.
