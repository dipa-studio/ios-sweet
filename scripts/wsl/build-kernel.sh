#!/bin/bash
# Validate the ios-sweet XNU patch series and run whatever compile checks are
# possible on Linux/WSL.
#
# The full SWEET kernel links on macOS CI (blacktop/darwin-xnu-build + Xcode's
# iig); that is .github/workflows/xnu.yml, not this script. Linux/WSL can only:
#   1. validate the patch series (tools/validate-repo.py),
#   2. compile single TUs from a downloaded CI build tree (tools/xnu-cc.py),
#   3. build the HackiOS *reference* kernel (xnu-8796.121.2) on Linux, when
#      THEOS is available, for comparison -- it is a different XNU release and
#      is not the delivered kernel.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"

log()  { printf '\033[1;32m[build-kernel]\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m[build-kernel]\033[0m %s\n' "$*" >&2; }

usage() {
	sed -n '2,14p' "$0"
	exit 2
}

BUILDLOG=""
BUILDTREE=""
REFERENCE=0
while [[ $# -gt 0 ]]; do
	case "$1" in
		--buildlog)  BUILDLOG="$2"; shift 2 ;;
		--buildtree) BUILDTREE="$2"; shift 2 ;;
		--reference) REFERENCE=1; shift ;;
		-h|--help)   usage ;;
		*) echo "unknown argument: $1" >&2; usage ;;
	esac
done

# --- 1. patch-series validation --------------------------------------------
log "validating patch series and scripts (tools/validate-repo.py)"
python3 -X utf8 tools/validate-repo.py --verbose

# --- 2. single-TU compile check (optional) ----------------------------------
if [[ -n "$BUILDLOG" && -n "$BUILDTREE" ]]; then
	log "single-file compile check against CI log"
	log "  buildlog : $BUILDLOG"
	log "  buildtree: $BUILDTREE"
	# Compile the SWEET-specific driver files most likely to be touched by a
	# kernel port. tools/xnu-cc.py replays the CI compile command per file.
	for f in \
		bsd/dev/sweet_virtio_blk.c \
		bsd/dev/sweet_virtio_input.c \
		bsd/dev/sweet_ramfb.c \
		bsd/dev/sweet_ufs.c \
		bsd/kern/sweet_amfi.c; do
		if [[ -f "$BUILDTREE/xnu/$f" ]]; then
			python3 tools/xnu-cc.py "$BUILDLOG" "$BUILDTREE" "$f" || warn "compile check failed: $f"
		else
			warn "skipping missing $f (not in build tree)"
		fi
	done
elif [[ -n "$BUILDLOG" || -n "$BUILDTREE" ]]; then
	echo "pass both --buildlog and --buildtree to enable single-TU checks" >&2
	exit 2
fi

# --- 3. HackiOS reference kernel (optional, Linux-only) ---------------------
if [[ "$REFERENCE" -eq 1 ]]; then
	if [[ -z "${THEOS:-}" ]]; then
		warn "THEOS is not set; run scripts/wsl/setup.sh and set THEOS first"
	else
		HACKIOS="github-clone/hackios-xnu-kernel"
		log "building HackiOS reference kernel (xnu-8796.121.2) on Linux"
		(
			cd "$HACKIOS"
			xnu/apply.sh
			xnu-deps/setup.sh
			./xnu-build.sh -j"$(nproc)" -k || true
		)
		ref="$HACKIOS/xnu-src/xnu-8796.121.2/BUILD/obj/DEVELOPMENT_ARM64_BCM2837/mach.development.bcm2837"
		if [[ -f "$ref" ]]; then
			log "reference kernel: $ref"
			file "$ref"
			sha256sum "$ref"
		else
			warn "reference kernel not produced (expected: make exits non-zero after linking)"
		fi
	fi
fi

log "build-kernel validation complete"
