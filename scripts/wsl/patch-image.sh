#!/bin/bash
# Build a new iOS 16.7.16 (20H392) disk image that integrates the HackiOS
# userland hooks, and output it under output/ as a separate image. The source
# IPSW-derived images are never overwritten: this always produces a new file.
#
# WSL2/local only: this stage needs apfs-fuse (raw APFS), hfsprogs, sudo and
# the Apple IPSW, none of which belong on GitHub Actions.
#
#   patch-image.sh [--ipsw IPSW] [--dmg-dir DIR] [--redwood-dylibs DIR] [--name N] [--size S] [--outdir DIR]
#
# Defaults: the repo-root IPSW, research/ipsw-x for extracted DMGs, 16G, and
# output/ios16-20H392-hackios-xnu-v1.img.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"

log()  { printf '\033[1;32m[patch-image]\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m[patch-image]\033[0m %s\n' "$*" >&2; }
die()  { printf '\033[1;31m[patch-image]\033[0m %s\n' "$*" >&2; exit 1; }

IPSW="$REPO_ROOT/iPhone10,3,iPhone10,6_16.7.16_20H392_Restore.ipsw"
DMGDIR="$REPO_ROOT/research/ipsw-x"
REDWOOD_DIR=""
NAME="ios16-20H392-hackios-xnu-v1"
SIZE="16G"
OUTDIR="$REPO_ROOT/output"

usage() { sed -n '2,18p' "$0"; exit 2; }

while [[ $# -gt 0 ]]; do
	case "$1" in
		--ipsw)           IPSW="$2"; shift 2 ;;
		--dmg-dir)        DMGDIR="$2"; shift 2 ;;
		--redwood-dylibs) REDWOOD_DIR="$2"; shift 2 ;;
		--name)           NAME="$2"; shift 2 ;;
		--size)           SIZE="$2"; shift 2 ;;
		--outdir)         OUTDIR="$2"; shift 2 ;;
		-h|--help)        usage ;;
		*) echo "unknown argument: $1" >&2; usage ;;
	esac
done

OS_DMG="087-86698-044.dmg"
SYS_DMG="087-86593-047.dmg"
APP_DMG="087-86715-047.dmg"

# --- pre-flight ------------------------------------------------------------
command -v apfs-fuse >/dev/null 2>&1 || die "apfs-fuse not found; run scripts/wsl/setup.sh"
command -v mkfs.hfsplus >/dev/null 2>&1 || die "hfsprogs not found; run scripts/wsl/setup.sh"
[[ -x tools/mkiosroot.sh ]] || die "tools/mkiosroot.sh missing"

# --- extract IPSW components if needed -------------------------------------
mkdir -p "$DMGDIR"
for dmg in "$OS_DMG" "$SYS_DMG" "$APP_DMG"; do
	if [[ ! -f "$DMGDIR/$dmg" ]]; then
		log "extracting $dmg from IPSW"
		[[ -f "$IPSW" ]] || die "IPSW not found: $IPSW"
		command -v 7z >/dev/null 2>&1 || die "7z (p7zip-full) required to extract the IPSW"
		7z e -y -o"$DMGDIR" "$IPSW" "$dmg" >/dev/null
	fi
done

# --- build the base HFS+ image ---------------------------------------------
mkdir -p "$OUTDIR"
BASE="$OUTDIR/${NAME}-base.img"
log "building base image -> $BASE"
tools/mkiosroot.sh "$DMGDIR/$OS_DMG" "$DMGDIR/$SYS_DMG" "$DMGDIR/$APP_DMG" "$BASE" "$SIZE"

# --- mount, apply tweaks, install HackiOS hooks -----------------------------
MNT="$OUTDIR/mnt"
mkdir -p "$MNT"
log "mounting base image at $MNT"
sudo mount -t hfsplus -o loop,force "$BASE" "$MNT"
trap 'sudo umount "$MNT" 2>/dev/null || true' EXIT

log "applying bring-up tweaks"
sudo python3 tools/sweet-root-tweaks.py "$MNT"

if [[ -n "$REDWOOD_DIR" ]]; then
	log "installing HackiOS Redwood dylibs from $REDWOOD_DIR"
	sudo mkdir -p "$MNT/redwood/lib" "$MNT/private/etc"
	for dylib in libredwood.dylib libredwood-sb.dylib; do
		[[ -f "$REDWOOD_DIR/$dylib" ]] || die "missing $REDWOOD_DIR/$dylib"
		sudo cp "$REDWOOD_DIR/$dylib" "$MNT/redwood/lib/$dylib"
		sudo chmod 0755 "$MNT/redwood/lib/$dylib"
	done
else
	warn "no --redwood-dylibs given; image will lack the injected HackiOS libraries"
fi

sudo sync
sudo umount "$MNT"
trap - EXIT

# --- finalize ----------------------------------------------------------------
FINAL="$OUTDIR/${NAME}.img"
cp --sparse=always "$BASE" "$FINAL"
log "fsck (repair) on the copy"
sudo fsck.hfsplus -fy "$FINAL" || true

log "checksums"
( cd "$OUTDIR" && sha256sum "${NAME}.img" > "${NAME}.img.sha256" )
sha256sum "$FINAL"
ls -l "$FINAL"

log "image built: $FINAL"
log "boot it with: scripts/windows/boot-hackios.ps1 -Image '$FINAL'"
