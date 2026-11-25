# Read-only APFS port — patch 0135

The last handset-validated image is v49: read-only GPT/BSD block registration,
then the existing mockfs test PID 1 from md0. v50 is built and not flashed.
No iOS filesystem has been written to system or another data partition.

Patch 0135 adds an APFS format reader, VFS registration, vnode operations,
compressed-file decoders and a bounded BSD strategy transport to
xnu-8796.141.3. The source is adapted from HakiOS commit
`88513176b1e96ecf0b764cd62c6f4e6ac71345e3`; original Git object hashes were
checked against GitHub, including both decoder dependency trees. APSL and MIT
notices are retained. No HakiOS UFS, resident UEFI, platform driver, write/store
module, scheduler hook or thread pool is imported.

The mount is always read only. Root selection requires `whyred-apfs-root=1`;
without it APFS declines mountroot and the current md0/mockfs path continues.
The block reader checks alignment, device/partition capacity, errors and short
I/O. The port uses the existing 512-byte BSD block units and integer-only
compilation. Metadata cache is reduced to 256 blocks; I/O buffers are 64 KiB
with two retained buffers. Vnode creation is serialized to avoid duplicate
vnodes for the same inode during concurrent lookups.

Reader fixes made during this port: container-size multiplication overflow,
bounded checkpoint scanning, revalidation of selected checkpoint geometry and
incompatible features, strict zlib completion, file-size error propagation and
signed-size limits, and pagein offset overflow. Encryption, snapshots and an
authenticated external sealed-root hash are not supported.

## Checks completed locally

- Patch replay reproduces every candidate file. The five APFS C units and
  vfs_conf.c compile with v49 CI headers/flags. Local LLVM needs metadata
  builtin shims for the two VFS units; these local objects are diagnostics,
  not production kernel inputs. The subsequent full Apple-clang CI link passed.
- The new objects have no unresolved symbols when combined with the v49
  kernel's symbols. All five APFS objects have zero LSE and PAN instructions.
- A native host executable built from the exact C parser reads a synthetic
  APFS image: directory entries, symlink, uncompressed data, inline zlib,
  resource-fork zlib, unaligned reads across compressed-piece boundaries, EOF,
  and injected device failure. Seven corrupt/truncated image variants are
  rejected, including checksummed checkpoints with invalid geometry.
- A 4 MiB diagnostic APFS root image can be built on Windows with the Python
  builder. It contains the project's existing test PID 1 at /sbin/launchd,
  directories for devfs/var, and a marker. It contains no Apple iOS userland.

## CI and hardware boundary

The workflow now runs the APFS source guard before compiling, the host parser
cases after linking, and builds a small diagnostic APFS root beside the kernel.
Actions [run 41048205578](https://github.com/timosid/ios-sweetwhyred/actions/runs/41048205578)
passed all steps at code commit `1f1ca0d7444c13abb7f77ccefc1031076c1a9af1`.
The downloaded artifact's SHA-256 matched GitHub; the final linked kernel has
zero LSE/PAN instructions. v51 was packaged with the 4 MiB diagnostic APFS md0;
its image SHA-256 is `79b4b69a190971ca15c43cd8b360aa6a9c2dcac3ca21f49aaa91539c48f5bc06`.
Kernel SHA-256: `d1e8598a74d11422b7b064f055e241ad44b0a0c20ad260cf030b1837499d9155`.
Boot-layout and trusted bootstrap/ADT checks passed. No phone operation was
performed; a real-kernel APFS mount and exec remain untested.

The original iOS 16.5 (20F66) root/OS/App images were downloaded locally from
Apple's public IPSW with exact-range, size and ZIP CRC checks. The same C reader
opened the real AppCryptex and read `/usr/libexec/webbookmarksd`; its extracted
arm64/arm64e binary passed 76 CodeDirectory page-hash checks. This checks file
content integrity, not the CMS signing identity. 7-Zip 26.02 could list that
image but could not extract the LZBITMAP-compressed file, so byte comparison
against 7-Zip was unavailable. None of these Apple images or files are published.

This does not yet install iOS launchd, dyld, backboardd or SpringBoard. A full
iOS root still requires preparation from the downloaded IPSW/cryptex inputs, a writable
runtime /private/var solution, and subsequent userspace/platform adaptation.
