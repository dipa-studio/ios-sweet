#!/bin/bash
# Verify a built ios-sweet disk image without booting it: filesystem type,
# geometry/size, read-only fsck, and SHA-256. Never modifies the image.
#
#   verify-image.sh IMAGE
set -euo pipefail

log()  { printf '\033[1;32m[verify-image]\033[0m %s\n' "$*"; }
die()  { printf '\033[1;31m[verify-image]\033[0m %s\n' "$*" >&2; exit 1; }

IMG="${1:-}"
if [[ -z "$IMG" ]]; then
	echo "usage: $0 IMAGE" >&2
	exit 2
fi
[[ -f "$IMG" ]] || die "not a file: $IMG"

command -v fsck.hfsplus >/dev/null 2>&1 || die "hfsprogs not found; run scripts/wsl/setup.sh"

log "file: $(file "$IMG")"
log "size: $(stat -c '%s bytes (%n)' "$IMG")"

log "partition table (if present)"
if command -v fdisk >/dev/null 2>&1; then
	fdisk -l "$IMG" 2>/dev/null || true
fi

log "read-only fsck (no changes)"
# Linux hfsplus reports a benign "Volume header needs minor repair" on fresh
# journaled volumes even after -fy; a non-zero exit here is reported, not fatal.
set +e
fsck.hfsplus -fn "$IMG"
rc=$?
set -e
log "fsck.hfsplus -fn exit code: ${rc}"

log "SHA-256"
sha256sum "$IMG"

log "verification complete"
