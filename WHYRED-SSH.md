# SSH over USB Ethernet

Installed is boot v89 / System v91. The phone accepts root SSH commands at
192.168.7.2:2222 using a dedicated Ed25519 key. Host identity is pinned on the
Mac; private keys and device logs stay local. Password/PAM authentication,
forwarding and SFTP are omitted. The Mac USB service now persists192.168.7.1/24
without a router, and kernel UDP logs continue to the existing Mac receiver.

Actual phone checks passed root identity, uname, process/filesystem inspection,
remote shell exit status, an exact65536-byte binary round trip, rejection of an
unrelated key and reading the server log. The first20-second handshake timed out
while userland was still loading; a90-second connection deadline succeeded.
The listener was first observed331 seconds after the boot observer started.
These are observations from this boot, not startup performance guarantees.

V90 installed the new job in /Library/LaunchDaemons. Static inspection of the
exact installed launchd showed that directory is absent from its embedded
Bootstrap/Paths. V91 moves both the standalone job and cache key to
/System/Library/LaunchDaemons. The builder checks the actual embedded paths and
rejects the previous v90 location. All530 original jobs and the SSH program/key
bytes are retained. All81 sparse sends/writes and reboot returned OKAY.

The v91 System image is5386170368 bytes, SHA256
fa356fa4a02ae74fff9dbc674336f52f9754560767ee3c88ca3579629905ebe0.
Before transfer, XNU's APFS reader passed64 complete file comparisons including
all43 active cache members;17 inode/owner/mode checks and full sparse payload
coverage/digest verification passed. The old /Library SSH job is absent. The
baseline catalog45734 files/16600 directories/671 symlinks is reproduced without
host metadata. The original System v70 and boot v89 rollback digests passed.

The package builds [Dropbear2026.94](https://github.com/mkj/dropbear/releases/tag/DROPBEAR_2026.94)
and dash0.5.13.5 from pinned upstream sources. The Dropbear archive matches its
published SHA256. Dash uses upstream commit037bbdfd330017c368caf6242f977974123239b5
through the kernel Gitiles mirror. Regenerated archive metadata varies, so every
member's path/type/mode/link target and complete content is authenticated by a
canonical tree digest. Production client/host keys were generated on the Mac.
No private keys are included in source or CI artifacts.

Darwin lacks setresgid, so Dropbear's optional early privilege-drop feature is
disabled while ordinary authenticated session UID handling remains enabled.
Account, shell, key ownership and signature checks remain active. The iOS build
uses the official SDK, minimum16.4 and generic+crypto without outline atomics.
The first shell build imported strchrnul, absent from the exact16.5 cache; it
was rejected. The corrected configure cache selects dash's portable version.
Every packaged binary matches installed-cache exports, bound to its SHA256.

Userland source b5b9b074c51e3b676928ced77a3b1b7c565ff600 passed all9 steps in
CI41350694615/job124979995276. Artifact13101197811 ZIP SHA256 is
dec89a1c4bddd17ba2f5204f383a50d5fce230938fe2dcc6fae6a97805fe1b18.
Provenance, complete archive CRC, signatures/platform/dependencies, detected-LSE
checks and native authentication/command/1MiB transport tests passed. V91's
bootstrap-directory packaging correction is source73572a42a155bc3a8b26911a7d7fd430f95c3065.

`whyredctl` provides ps, fs, du, ls, stat, cat, readlink, uname and id and reports
actual syscall errors. The shell supplies commands, pipes and redirection.
Kernel UDP capture is best effort and a final panic may interrupt delivery.
SSH now enables direct runtime diagnosis; pkd/lsd, container/RAMFS behavior and
other daemon exit causes remain open.

## Live service diagnostics

The next System v92 candidate includes `whyreddiag memory`, `threads PID`, and
`selftest`. Thread sampling reads registers and at most24 frame pairs for at
most256 threads, without suspension or target memory writes. Live frame chains
can change during the sample. `run-mobile /absolute/program [args]` launches a
separate mobile-user child, captures its standard streams and imposes a30-second
limit; it does not reproduce launchd's complete bootstrap context.

The iOS server mirrors its existing log messages over nonblocking UDP to the
existing USB log destination192.168.7.1:5140. Messages are sanitized and capped at
1023 bytes, with512 attempts per process. This best-effort diagnostic channel
preserves errno and does not change authentication results. Missing account and
authorized-key metadata/open failures include errno. Account/shell/ownership/
key/signature checks remain enabled. The server binary contains no device keys.

Early physical v91 SSH tests passed, but later sessions rejected the same key
before signature submission while the kernel stream continued. A later common
SIGBUS/KERN_MEMORY_ERROR crash storm affects multiple processes. The v92 changes
are diagnostic tools; their build success is not evidence of a device fix.
