# V89: classify root-created DSC cache entries

The subsequent v87 capture shows the same6199-page main DSC file and a1970-page
temporary copy owned by UID0 during early boot. The global8192-page quota is
full, zero pages are unlinked, and file_limit_hits is0. The earlier UID272-only
policy therefore fails to cover the phase before ownership changes. No pkd/lsd
crash appears in this early excerpt; it does not establish their stability.

Patch0168 retains the existing opt-in per-file limit and additionally recognizes
regular entries in /db/uuidtext/dsc within the /var RAMFS. The canonical three
directory levels receive sticky role bits at namespace insertion. Classification
propagates through a prepopulated tree moved into that location, follows at most
three canonical levels and scans direct DSC entries only. File classification
persists for the inode's lifetime across hard links, moves and UID changes.
Replacement and swap rename paths classify their changed entries under the same
mount lock. No regular-file parent pointer or unbounded full-filesystem scan is
needed. Directory identity keeps its role after a move.

The existing locked store/setattr/write guards now use the inode classification
or UID272. Thus root-created main and temporary DSC files get the same8MiB bound
before data allocation, while unrelated root-owned files retain the global
limit. Namespace classification during an unlocked user copy is rechecked by
the store path. Existing oversized files moved into the cache retain their data;
they are never deleted or silently truncated. This remains a per-file bound,
not an aggregate cache reservation. Missing/invalid configuration disables it.
Pressure records add dsc=1 for a classified inode; all previous budgets remain.

Local UBSan passes1,120,194 checks across28 actual functions. Namespace tests pass
75 checks, including actual swap/replacement renames. Root ownership, temp files,
unrelated directories, prepopulated moves, chown, classification during uiomove,
default-off and trace-off behavior are covered. ARM64, noLSE/PAN and exact replay
pass. Removing root recognition or swap classification compiles then fails a
functional check. Full workflow41346137446 passed all27 steps, including these
1,120,194 ASan+UBSan checks and75 namespace checks. The pinned legacy0145 test
also passed66 checks. Authenticated v89 packaging retains USB1299 and idle799;
real logd/container behavior remains pending the next boot-partition test.

--- Earlier UID-only implementation and evidence ---

# V87: bound the observed logd cache file

The later v85 UART includes a damaged prefix of the actual largest TOP row:
6199 resident pages, logical size101,564,195 bytes, UID272, directory dsc. TOP
ranks start at zero; the initially supplied rank1 was the second-largest file.
That largest file consumes96.86MiB,75.7% of the128MiB quota. Its name matches the
main installed dyld cache UUID. The preserved System account table identifies
UID272 as _logd. The following rank1/rank2/rank3 files total only7.52MiB; the
previous inference from those three alone was incomplete.

The user subsequently recovered the complete pressure record id16384. Its cause
is data-quota: pages8192/limit8192, hash_pages8192 and added10657-freed2465=8192.
Only4 resident pages are unlinked. Rank0 explicitly confirms the6199-page DSC
file; the namespace scan selected4 entries without reaching its name budget.
This independently confirms the quota/large-named-file interpretation.

The same run records containermanagerd failing a556-byte atomic staging-metadata
write with ENOSPC. Pkd repeats its earlier container-related SIGABRT stack.
Fairplayd.H2 and bluetoothd instead exit normally with code0; suggestd exits2
without a signal. Their early-exit causes and the fresh lsd class-metadata fault
remain unresolved. No additional older UART is required.

Patch0166 adds a development/debug opt-in `whyred-logd-file-mb=N`. Values1..64
bound the logical size of each regular file owned by the confirmed UID272;
invalid/missing values disable it. The effective bound also respects the mount's
existing limit. V87 will try8MiB: the observed97MiB DSC-format cache cannot be
materialized, while the observed4.6MiB individual UUID file fits. The global
128MiB quota and its quarter-of-memory guard stay unchanged. This is a per-file
policy, not an aggregate UID reservation, deletion policy or job restart change.

Buffered writes reject a request crossing that file-size bound with EFBIG before
copying data or allocating pages. The locked store path rechecks the owner/limit
for pageout and concurrent owner changes. A partial write committed before an
owner change returns its actual byte count. Truncate and combined UID/size
changes check the final state before mutating attributes; transferring an already
oversized file to UID272 fails, while truncating it into range and transferring
ownership together succeeds. Existing files are never evicted or silently
truncated. Other owners retain the previous limits.

`logd-file-limit` pressure records identify EFBIG from this policy and show UID,
file_limit bytes and file_limit_hits. The existing sampling/output budget and
outside-lock printer are retained. Default-off behavior is tested. The real
logd response to a refused DSC cache must be checked on the phone; this may
reduce symbol information available to unified-log readers and does not claim
that logd handles every failure gracefully. Kernel UART/UDP console capture uses
its existing independent ring. V86 USB diagnostics and v85 idle/service changes
are retained in the next candidate.

Local UBSan passes1,120,166 checks across25 actual functions, including configured
bounds/invalid values, rejecting the101MiB truncate without page allocation,
full-request EFBIG/residuals, rewrites at the bound, owner-transfer atomicity,
combined truncate/chown, default-off behavior and an owner change after write
preflight. All66 namespace/readdir/sync checks pass. ARM64 compilation, noLSE/PAN
and exact patch replay pass. Disabling the size policy or its owner-transfer
check fails functional assertions after successful compilation. Full CI41342210494
passed all27 steps, including these1,120,166 checks with ASan+UBSan. Both ZIP
provenance/digests/CRC, exact sources/fixtures and linked ISA/cache/idle/loader/
layout guards passed. V87 boot was flashed and rebooted successfully; physical
cache/container behavior remains to be checked with the new manual UART.

--- Earlier diagnostic implementation and history ---

# Volatile RAMFS pressure diagnostics

Patch 0158 adds `whyred-ramfs-trace=1` to development/debug kernels. It is off by
default. It diagnoses failed writes to the volatile filesystem; it does not
increase quotas, change allocation flags, alter permissions or substitute syscall
results. Existing container syscall tracing can remain enabled for path context.

`WHYRED RAMFS PRESSURE` has three lines sharing an ID. The cause is the branch
that returned the existing error:

| Cause | Existing result | Meaning |
| --- | --- | --- |
| `data-quota` | ENOSPC | A new file page would exceed the mount page quota. |
| `data-page` | ENOSPC | A new page is needed, the quota has room, and the caller has no spare page. `kr` records its VM allocation result. |
| `slots-nowait` | ENOSPC | The nonwaiting file page-pointer-array allocation failed. |
| `getxattr-nowait` | ENOMEM | The nonwaiting attribute-value snapshot allocation failed. |
| `listxattr-nowait` | ENOMEM | The nonwaiting attribute-name snapshot allocation failed. |

If both quota and spare-page availability fail, `data-quota` takes precedence.
`kr` is meaningful for `data-page` only. For slots, `length` is the requested
pointer-array size and `off` is the start of the indexed page. For other causes
they describe the data operation or attribute-copy size.

The record includes used/limit/peak file pages, nodes, xattr bytes, cumulative
file-page additions/frees and zero-link vnode reclamations. `hash_pages` sums
file pages on all nodes while holding the mount lock. `unlinked_pages` and
`unlinked_nodes` count nodes with zero links. Open-unlinked files legitimately
retain data until reclaim; these counts alone do not establish a leak.
Global free/wired VM page counts are approximate samples, not a coherent VM
snapshot. An allocation failure does not by itself identify global RAM exhaustion.

There are at most 32 records per mount. The first 16 failures are recorded, then
power-of-two failure numbers. Cause counters continue after the output budget is
exhausted. The bounded hash walk happens only when producing a record, under the
existing mount lock. A scalar snapshot is copied before unlocking; printing is
outside that lock and performs no path lookup or file-data copy. Pageout keeps
its nonwaiting allocation behavior. No node/vnode pointer is used by the printer.

`tools/test-whyred-ramfs-pressure.py` extracts the actual declarations and 21
functions into a host fixture. It injects each allocation failure, exercises
quota-limited short writes and residual counts, verifies default-off behavior,
fills the output budget with 1.1 million failures and churns 10,000 file lifetimes.
It checks truncate, open-unlinked retention, named-vnode reclaim, attribute error
propagation and balanced page counters. Host locks/allocators/uio/vnodes are
adapters; kernel scheduling, UBC, memory pressure and VFS reference counts are
not emulated. CI also runs the existing namespace/directory/sync tests and the
full ARM64 kernel build. These checks do not emulate runtime behavior; the
hardware observation below identifies the sampled failure branch.

## Observed v81 quota failure (2026-11-01)

The user's photograph shows `pkd` SIGABRT, a container-manager write returning
ENOSPC, and pressure record 1024 with `cause=data-quota`, `pages=8192`,
`limit=8192` and `hash_pages=8192`. With this kernel's 16 KiB pages, that is the
128 MiB mount quota. The additions/frees in the same record are 9623/1431,
whose difference is also 8192. The failure branch is now observed on hardware.

Zero-link nodes account for 67 pages, approximately 1.05 MiB. Most of the sampled
usage belongs to linked nodes. These coherent counters do not rule out semantic
retention or excessive writes. The largest files, writers and full causal chain
to each daemon's termination remain unknown. Approximate global VM samples do
not establish a safe larger quota. The next measurement is a bounded snapshot
of the largest resident file owners/names; no quota or return-value change has
been made from this observation.

## Bounded resident-owner follow-up

Patch 0161 adds `whyred-ramfs-top=1`, also requiring `whyred-ramfs-trace=1`.
It extends sampled quota failures with the four largest resident file-page
owners, sorted by pages and then inode. Each record contains copied inode,
allocated pages, logical size, link count, UID, writable-mapping flag, one name
and the parent directory's name/inode. The failed caller and last writer are
not inferred from a file's UID. Hard links yield one sampled alias; no full
canonical path is promised. Zero-link owners and unresolved names remain marked
by link count/zero parent, rather than a guessed name.

The snapshot lives under the existing mount lock. The top-four selection shares
the existing hash walk; all name searches share a 65,536-entry budget. Only fixed
metadata and bounded character arrays leave the lock. No file content is read,
no VFS path lookup/allocation is performed and no node/vnode pointer is retained
by the printer. Control, quote and backslash bytes become `?`; name and directory
limits are 47/31 bytes with truncation flags. A name-budget flag discloses an
incomplete search. The event is under 1 KiB in the host ABI check. Each selected
record adds at most five lines to the existing bounded 32-record policy.

Local UBSan passes 1,120,134 checks; the wake-independent namespace suite retains
all 66 passing cases. Ownership tests cover ties, unlinked retention, truncated
and control-byte names, printing after node reclamation, the entry-walk budget
and default-off/other-failure behavior. The disabled-collector negative control
fails. Full [CI 41325125813](https://github.com/timosid/ios-sweetwhyred/actions/runs/41325125813)
passed all 26 steps, including these 1,120,134 checks with ASan+UBSan. Physical
owner output remains pending. No quota, allocation,
error-return, namespace or service-restart policy changes are included.
