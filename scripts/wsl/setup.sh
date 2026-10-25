#!/bin/bash
# ios-sweet / HackiOS WSL2 build workstation setup.
#
# WSL2 is the build/reverse-engineering environment only: source audit, image
# building, fsck, file operations and kernel-patch validation. QEMU is NOT run
# here; the guest is booted from Windows (scripts/windows/boot-hackios.ps1).
#
# Detects the distro and toolchain, then installs the packages the local stages
# need. Idempotent: safe to re-run.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"

log()  { printf '\033[1;32m[setup]\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m[setup]\033[0m %s\n' "$*" >&2; }
die()  { printf '\033[1;31m[setup]\033[0m %s\n' "$*" >&2; exit 1; }

# --- environment -----------------------------------------------------------
if ! grep -qi 'microsoft' /proc/version 2>/dev/null; then
	warn "not running under WSL2 (missing 'microsoft' in /proc/version)"
fi

arch=$(uname -m)
log "architect = ${arch} (kernel $(uname -r))"

if [[ -f /etc/os-release ]]; then
	# shellcheck disable=SC1091
	. /etc/os-release
	log "distro = ${PRETTY_NAME:-${NAME:-unknown}}"
else
	die "cannot read /etc/os-release"
fi

# --- package manager -------------------------------------------------------
install_apt() {
	log "installing packages with apt"
	sudo apt-get update
	sudo apt-get install -y --no-install-recommends \
		build-essential clang lld python3 python3-pip git curl wget \
		rsync xz-utils perl hfsprogs file p7zip-full \
		cmake ninja-build libfuse3-dev liblzfse-dev
}

case "${ID:-}" in
	ubuntu|debian) install_apt ;;
	*) die "unsupported distro '${ID:-unknown}'; add a package branch for it" ;;
esac

# --- apfs-fuse --------------------------------------------------------------
# Needed by tools/mkiosroot.sh to read the IPSW APFS images. Not packaged for
# Ubuntu in the required version, so it is built from source when missing.
if command -v apfs-fuse >/dev/null 2>&1; then
	log "apfs-fuse: $(command -v apfs-fuse)"
else
	log "apfs-fuse not found; build it with tools/mkiosroot.sh expectations"
	APFS_SRC="${APFS_SRC:-$HOME/apfs-fuse}"
	if [[ ! -d "$APFS_SRC/.git" ]]; then
		git clone --recursive https://github.com/sgan81/apfs-fuse.git "$APFS_SRC"
	else
		git -C "$APFS_SRC" submodule update --init --recursive
	fi
	mkdir -p "$APFS_SRC/build" && cd "$APFS_SRC/build"
	cmake -DCMAKE_POLICY_VERSION_MINIMUM=3.5 \
		-DCMAKE_CXX_FLAGS="-include cstdint" \
		-DCMAKE_INSTALL_PREFIX="$HOME/.local" ..
	cmake --build . -j"$(nproc)"
	cmake --install .
	cd "$REPO_ROOT"
	log "apfs-fuse installed to $HOME/.local/bin/apfs-fuse"
fi

# --- toolchain report ------------------------------------------------------
log "toolchain report"
for tool in clang clang++ ld.lld python3 git hfsplus.newfs hfsplus.fsck hfsplus.mount mkfs.hfsplus fsck.hfsplus; do
	if command -v "$tool" >/dev/null 2>&1; then
		printf '  %-20s %s\n' "$tool" "$(command -v "$tool")"
	else
		printf '  %-20s MISSING\n' "$tool" >&2
	fi
done

if [[ -n "${THEOS:-}" ]]; then
	log "theos detected at ${THEOS} (HackiOS Linux kernel build reference)"
else
	warn "THEOS is not set; the HackiOS reference kernel build (xnu-8796.121.2) will be skipped"
fi

log "setup complete"
