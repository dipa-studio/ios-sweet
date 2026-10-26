# HackiOS repository audit (relationship and relevance)

Audit of the local HackiOS clones against the ios-sweet tree, 2026-10-25.
No image was modified and no VM was launched. This answers which repositories
exist, how they relate, and what is actually relevant to the 20H392 build.

## Which repositories exist

There is exactly one `hackios-xnu-kernel` checkout in this workspace, at
`github-clone/hackios-xnu-kernel`. An earlier untracked root-level
`hackios-xnu-kernel/` (and `hackios-xnu-userland/`) recorded in `NOTES.md` was
consolidated under `github-clone/`; no root-level copy remains.

| Local path | Remote | Branches |
| --- | --- | --- |
| `github-clone/hackios-xnu-kernel` | `oosexgang/hackios-xnu-kernel` | `main`, `metal` |
| `github-clone/hackios-xnu-userland` | `oosexgang/hackios-xnu-userland` | `main`, `metal` |

The two directory names in the request (`github-clone/hackios-xnu-kernel` and
`hackios-xnu-kernel`) therefore resolve to the **same** kernel repository; the
two genuinely distinct repositories are the **kernel** and **userland** halves
of the HackiOS project by OOSEX GANG.

## Relationship to ios-sweet

The ios-sweet tree (`zaidanfaiz/ios-sweet` fork of `dipa-studio/ios-sweet`) is a
separate XNU port. The two projects target different XNU releases and different
hardware, so they cannot be merged wholesale:

| Axis | HackiOS kernel | ios-sweet |
| --- | --- | --- |
| XNU | `8796.121.2` (iOS 16.5, Darwin 22.5.0) | `8796.141.3` (iOS 16.7.16 / 20H392, Darwin 22.6.0) |
| Config base | `BCM2837` | `SWEET` (arm64) |
| Hardware | POCO X5 Pro 5G (`redwood`, SM7325) | Redmi Note 10 Pro (`sweet`, SM7150) |
| Root FS | APFS (+ ramfs `/private/var`) | HFS+ via virtio-blk / UFS |
| Loader | EFI / XNUP | direct boot stub (`SWEETXNU v1`) |
| Crypto | minicrypto (corecrypto-free) | BearSSL-backed SHA/MD5/AES |
| Display | MiniIOMobileFramebuffer | AppleCLCD / SweetFramebuffer |

The kernel binary and the loader are not independently exchangeable: importing
the full `redwood.patch` would cross XNU versions and duplicate the existing
SWEET patch series (0001-0089). The HackiOS repos are therefore a **reference
implementation and source of components**, not a drop-in kernel.

## What is relevant to 20H392

The genuinely reusable pieces, and their current ios-sweet status:

| HackiOS component | Relevance | ios-sweet status |
| --- | --- | --- |
| `userland/src/inject.c`, `inject_sb.c` | ObjC hook library injected into SpringBoard/backboardd | Adapted for 20H392 in `userland/patches/20H392-redwood.patch`; built by `redwood-userland.yml` |
| `xnu/files/bsd/miscfs/ramfs/ramfs.c` | Writable `/private/var` overlay | Not ported; `HACKIOS_20H392_PORT.md` recommends against it for the HFS route |
| `xnu/files/osfmk/arm64/gic_v3_irq.c` | GICv3 IRQ handling | SWEET has its own GIC path; audit only |
| `xnu/files/bsd/dev/redwood_virtio_*.c` | QEMU virtio drivers | SWEET already has `sweet_virtio_*.c` (patch 0082) |
| APFS driver | System volume | SWEET uses HFS+; APFS is not a drop-in |

The existing `docs/HACKIOS_20H392_PORT.md` concludes that no kernel change is
justified by the current boot evidence (the blocker is LaunchServices rebuild
slowness under one-vCPU TCG, not a kernel defect). This audit does not change
that conclusion.

## Provenance and licenses

- HackiOS kernel: derivative of XNU, APSL 2.0 (`LICENSE`), with third-party
  sources (ath11k BSD-3-Clause-Clear, LinuxKPI BSD-2-Clause, libzbitmap MIT,
  libdeflate MIT).
- HackiOS userland: `LICENSE`, same family.
- No Apple firmware, IPSW payloads, or iOS binaries are committed in either
  HackiOS repository; `ios165/fetch.sh` downloads the IPSW from Apple's CDN.
