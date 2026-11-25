# Container filesystem diagnostics

The current experimental userspace reaches launchd, SpringBoard execution and
backboardd framebuffer transactions. A later pkd abort reports a container API
failure. In the matching iOS library, that top-level error denotes a general
filesystem failure; the failed operation, pathname and nested POSIX errno are
not printed by the daemon. The source frames inspected so far remain empty.
This change diagnoses filesystem compatibility and does not claim to fix UI
rendering or the daemon abort.

Patch 0157 adds `whyred-container-trace=1`. It is disabled by default and
observes filesystem syscall errors and successful short writes from the exact
process names `containermanagerd`, `pkd` and `calaccessd`. The ARM64 normal and continuation return paths
call it before preparing user return registers. It never substitutes a return
value, changes filesystem permissions or accepts unsupported operations.

`WHYRED FSERR` records share an ID across these short lines:

- Process, PID, operation, syscall number, POSIX errno and saved user PC.
- The first seven actual syscall argument words; unused words are zero.
- Best-effort pathname(s), or descriptor-to-vnode path, and the diagnostic
  copy/path lookup error. Paths are copied after the syscall, so another thread
  can have changed them. Relative paths retain the directory descriptors in the
  argument record. Truncation is explicit; control characters are sanitized.

Successful short `write`/`pwrite` calls carry `errno=0` and a separate
`reason=short-write` record with requested/returned byte counts. Normal short
reads (including EOF) and full writes are not reported. A quota-limited write
can legitimately return a partial success; this trace preserves it and does
not manufacture an errno. Calendar's supplied crash follows a NULL timezone
name read from its occurrence-cache database property. Its relationship to
the container failure is unconfirmed; its file failures are included so the
next capture can investigate both paths.

There are at most 256 records per boot, with separate 64-record lookup-miss and
192-record other-error budgets and separate key-table halves. Each process /
syscall / errno key keeps its first four occurrences, then powers of two.
If the short diagnostic lock is busy or a key table is full, that observation
is skipped. There is no wait on the diagnostic lock, and no lock is held while
copying a user string, resolving a vnode path or printing. Descriptor/vnode
references are dropped on success and failure paths. These limits make the
trace intentionally incomplete; it is not an audit log. It logs no file data.

Local checks execute the actual helper against mocked copyin/vnode services:
default-off and process/ARM64 gates, both return hooks, syscall ABI argument
positions, invalid and long paths, sanitization, descriptor cleanup, sampling,
budget isolation, saturation and busy-lock skipping. Full kernel CI is still
required. Keep device traces and any downloaded/decompiled Apple code local.

Keep the current handset boot running while preparing this candidate. The
next explicitly authorized boot-only test can enable the flag and correlate
the returned `WHYRED FSERR` operation/errno/path with the later exception.
No new storage timing, media writes, partition layout, protection policy or
graphics behavior is introduced by this patch.
