#!/bin/bash
# Build the SWEET iOS root: one case-sensitive HFS+ image holding an iOS OS
# root filesystem plus its cryptexes, for the userdata partition (rd=ufsroot0).
#
#   mkiosroot.sh OS.dmg SYSTEMOS.dmg APPOS.dmg OUT.img [SIZE]     (SIZE default 16G)
#   SWEET_HFS_BACKEND=auto|native|guestmount (default auto)
#   The guestmount backend requires root, guestmount/guestunmount and a guest
#   Linux kernel with HFS+ support; it also works when the host kernel lacks HFS+.
#
# The IPSW images are raw APFS with LZBITMAP-compressed files: they are read
# through apfs-fuse (decompressing), so the HFS+ copy is uncompressed. On a
# device /private/preboot is its own volume holding the cryptexes, which
# /System/Cryptexes/{OS,App} link to; here they live inside the one volume.
# Owners, modes, symlinks and hard links are preserved (rsync -aH as root).
#
# The volume is journaled (XNU replays the journal after a panic; Linux only
# mounts it read-write with -o force and leaves the journal empty). SWEET
# additions: /System/Library/Caches/com.apple.dyld hard-links the SystemOS
# cryptex shared cache (ignition_level=1 looks there), and
# /private/var/keybags/systembag.kb is the plain-plist system keybag that
# keybagd reads with /defaults/no-effaceable-storage (tools/mkadt.py).
set -euo pipefail

[[ $# -ge 4 ]] || { sed -n '2,12p' "$0"; exit 2; }
os=$(realpath "$1") sysos=$(realpath "$2") appos=$(realpath "$3")
out=$(realpath -m "$4") size=${5:-16G}
[[ ! -e $out ]] || { echo "refusing to overwrite $out" >&2; exit 1; }

backend=${SWEET_HFS_BACKEND:-auto}
case $backend in
	auto)
		if grep -qw hfsplus /proc/filesystems ||
		    { command -v modinfo >/dev/null && modinfo hfsplus >/dev/null 2>&1; }; then
			backend=native
		else
			backend=guestmount
		fi ;;
	native|guestmount) ;;
	*) echo "unknown HFS backend: $backend" >&2; exit 1 ;;
esac
if [[ $backend == guestmount && $EUID != 0 ]]; then
	echo "run the guestmount backend as root (sudo env SWEET_HFS_BACKEND=guestmount bash ...)" >&2
	exit 1
fi

# Pre-flight tool check
missing_tools=()
required_tools=(apfs-fuse mkfs.hfsplus fsck.hfsplus rsync python3)
[[ $backend != guestmount ]] || required_tools+=(guestmount guestunmount)
for tool in "${required_tools[@]}"; do
	command -v "$tool" >/dev/null 2>&1 || missing_tools+=("$tool")
done

if [[ ${#missing_tools[@]} -gt 0 ]]; then
	echo "Error: missing required host utilities: ${missing_tools[*]}" >&2
	echo "  Install instructions:" >&2
	echo "    Arch Linux:    sudo pacman -S apfs-fuse hfsprogs rsync" >&2
	echo "    Ubuntu/Debian: sudo apt install apfs-fuse hfsprogs rsync" >&2
	echo "    Fedora:        sudo dnf install apfs-fuse hfsplus-tools rsync" >&2
	exit 1
fi

work=$(mktemp -d)
mounts=()
guest_mount=''
guest_pidfile="$work/guestmount.pid"

wait_guest_exit() {
	local pid
	[[ -f $guest_pidfile ]] || { echo "missing guestmount PID file; cannot confirm image is closed" >&2; return 1; }
	pid=$(cat "$guest_pidfile")
	[[ $pid =~ ^[1-9][0-9]+$ ]] || { echo "invalid guestmount PID file" >&2; return 1; }
	for ((attempt=0; attempt<300; attempt++)); do
		if ! kill -0 "$pid" 2>/dev/null; then
			rm -f "$guest_pidfile"
			guest_mount=''
			return 0
		fi
		sleep 0.1
	done
	echo "guestmount is still running; image must not be checked or reused yet" >&2
	return 1
}

unmount_one() {
	local point=$1
	if [[ $point == "$guest_mount" ]]; then
		if mountpoint -q "$point"; then
			sudo guestunmount "$point" || return 1
		fi
		wait_guest_exit || return 1
	elif mountpoint -q "$point"; then
		sudo umount "$point" || return 1
	fi
	return 0
}

cleanup() {
	local original_status=$? busy=0 m
	for ((i=${#mounts[@]}-1; i>=0; i--)); do
		m=${mounts[i]}
		unmount_one "$m" || busy=1
		mountpoint -q "$m" && busy=1
	done
	# Never recurse into a directory that is still mounted (the root is writable).
	if [[ $busy == 0 ]]; then
		rm -f "$work"/*.dmg "$work/probe.img" "$guest_pidfile"
		rmdir "$work"/* "$work" 2>/dev/null || true
	else
		echo "could not confirm all mounts are released under $work: left in place" >&2
		# A successful build must also release its source mounts. Preserve an
		# earlier failure code, but report cleanup failure after success.
		[[ $original_status != 0 ]] || exit 1
	fi
}
trap cleanup EXIT

hfs_mount() {
	local image=$1 point=$2
	# Track even a partly failed mount so the EXIT trap can release it.
	mounts+=("$point")
	if [[ $backend == guestmount ]]; then
		guest_mount=$point
		# guestmount escapes commas inside each -o value. Keep just the
		# required FUSE access option; current guestmount rejects use_ino.
		sudo env LIBGUESTFS_BACKEND=direct LIBGUESTFS_BACKEND_SETTINGS=force_tcg \
			guestmount --rw --format=raw -a "$image" \
			-m /dev/sda:/:rw,force:hfsplus --pid-file "$guest_pidfile" \
			-o allow_other "$point"
	else
		sudo mount -t hfsplus -o loop,force "$image" "$point"
	fi
}

# Exercise the actual mount backend before allocating the output image or
# opening the Apple volumes. HFSX case handling and Unix metadata are required.
echo "checking HFSX backend: $backend"
mkdir "$work/probe"
truncate -s 64M "$work/probe.img"
mkfs.hfsplus -s -J -v HFSXProbe "$work/probe.img" >/dev/null
hfs_mount "$work/probe.img" "$work/probe"
printf 'HFSX probe\n' | sudo tee "$work/probe/file" >/dev/null
sudo chown 501:20 "$work/probe/file"
sudo chmod 0640 "$work/probe/file"
sudo ln "$work/probe/file" "$work/probe/hardlink"
sudo ln -s file "$work/probe/symlink"
expected_probe_metadata=501:20:640:2
# FUSE may briefly cache attributes from before chown/chmod/link. Re-read for
# at most three seconds; every accepted result must still match exactly.
for ((probe_attempt=0; probe_attempt<4; probe_attempt++)); do
	probe_metadata=$(sudo stat -c '%u:%g:%a:%h' "$work/probe/file")
	if [[ $probe_metadata == "$expected_probe_metadata" ||
	      $backend != guestmount || $probe_attempt == 3 ]]; then
		break
	fi
	sleep 1
done
printf 'HFSX probe metadata: %s (expected %s)\n' "$probe_metadata" "$expected_probe_metadata"
if [[ $probe_metadata != "$expected_probe_metadata" ]]; then
	sudo stat -c '%n: uid=%u gid=%g mode=%a links=%h type=%F' \
		"$work/probe/file" "$work/probe/hardlink" >&2
	echo "HFSX probe ownership, mode or hardlink count failed" >&2
	exit 1
fi
# FUSE can present inode numbers independently from the backing filesystem.
# Require actual shared writes through the hardlink, not inode presentation.
printf 'hardlink update\n' | sudo tee "$work/probe/hardlink" >/dev/null
[[ $(sudo cat "$work/probe/file") == 'hardlink update' ]] ||
	{ echo "HFSX probe hardlink does not share file contents" >&2; exit 1; }
[[ $(sudo readlink "$work/probe/symlink") == file ]]
printf 'upper\n' | sudo tee "$work/probe/Case" >/dev/null
printf 'lower\n' | sudo tee "$work/probe/case" >/dev/null
[[ $(sudo cat "$work/probe/Case") == upper && $(sudo cat "$work/probe/case") == lower ]]
unmount_one "$work/probe"
fsck.hfsplus -f -n "$work/probe.img"
rm -f "$work/probe.img"
rmdir "$work/probe"
mounts=()
echo "HFSX backend probe passed"

# apfs-fuse splits its options on ',' (e.g. in iPhone10,3 paths): use links.
# Keep the .dmg name: apfs-fuse only parses UDIF images (the OS one is UDIF,
# the cryptexes are raw APFS) when the file name ends in .dmg.
apfs_mount() {
	ln -s "$1" "$work/$2.dmg"
	mkdir "$work/$2"
	# As root: a user's FUSE mount is unreadable to the root rsync below.
	sudo "$(command -v apfs-fuse)" "$work/$2.dmg" "$work/$2"
	mounts+=("$work/$2")
}
apfs_mount "$os" os
apfs_mount "$sysos" sysos
apfs_mount "$appos" appos

# Atomically claim a new regular output. A concurrent build must fail rather
# than truncate or format the image another build has already started writing.
python3 -c 'import os,sys; os.close(os.open(sys.argv[1], os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600))' "$out"
truncate -s "$size" "$out"
mkfs.hfsplus -s -J -v iOSRoot "$out"
mkdir "$work/root"
hfs_mount "$out" "$work/root"

copy() {
	echo "copying $1 -> ${2#"$work/root"}"
	sudo mkdir -p "$2"
	sudo rsync -aH --numeric-ids "$1/" "$2/"
}
copy "$work/os/root" "$work/root"
copy "$work/sysos/root" "$work/root/private/preboot/Cryptexes/OS"
copy "$work/appos/root" "$work/root/private/preboot/Cryptexes/App"

# Shared cache where dyld looks at ignition level 1: hard links, no extra space.
dsc=private/preboot/Cryptexes/OS/System/Library/Caches/com.apple.dyld
sudo mkdir -p "$work/root/System/Library/Caches/com.apple.dyld"
for f in "$work/root/$dsc"/*; do
	sudo ln "$f" "$work/root/System/Library/Caches/com.apple.dyld/${f##*/}"
done

# dyld does not search the cryptexes at ignition level 1: hard-link every
# cryptex file that has no counterpart in the OS root (libobjc-trampolines,
# libffi-trampolines, libstdc++, ...) to its root path.
for c in OS App; do
	(cd "$work/root/private/preboot/Cryptexes/$c" && sudo find . ! -type d ! -path './System/Library/Caches/com.apple.dyld/*') |
	while IFS= read -r f; do
		f=${f#./}
		if ! sudo test -e "$work/root/$f" && ! sudo test -L "$work/root/$f"; then
			sudo mkdir -p "$work/root/$(dirname "$f")"
			src="$work/root/private/preboot/Cryptexes/$c/$f"
			# Linux hfsplus cannot hard-link symlinks: copy those.
			if sudo test -L "$src"; then sudo cp -P "$src" "$work/root/$f"; else sudo ln "$src" "$work/root/$f"; fi
			echo "linked $c:/$f"
		fi
	done
done

# logd's log stores, normally made at restore: it checks owner _logd (272)
# and mode, plus a .migrated marker, else asks a helper and crashes
# ("BUG IN LIBTRACE: Failed to migrate directory").
db="$work/root/private/var/db"
sudo install -d -o 272 -g 272 -m 0751 "$db/diagnostics"
sudo install -d -o 272 -g 272 -m 0755 "$db/uuidtext" "$db/diagnostics/timesync"
for d in diagnostics uuidtext diagnostics/timesync; do
	sudo install -o 272 -g 272 -m 0644 /dev/null "$db/$d/.migrated"
done

# System keybag for the built-in AppleKeyStore (no passcode).
sudo install -d -m 0700 -o 0 -g 0 "$work/root/private/var/keybags"
printf '%s\n' '<?xml version="1.0" encoding="UTF-8"?>' \
	'<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">' \
	'<plist version="1.0"><dict><key>KeyBagKeys</key><data>U1dFRVQ=</data></dict></plist>' |
	sudo install -m 0600 -o 0 -g 0 /dev/stdin "$work/root/private/var/keybags/systembag.kb"

sudo test -s "$work/root/sbin/launchd"
sudo test -s "$work/root/usr/lib/dyld"
cache="$work/root/System/Library/Caches/com.apple.dyld/dyld_shared_cache_arm64"
sudo test -s "$cache" || { echo "missing primary arm64 dyld shared cache" >&2; exit 1; }
sudo python3 -c 'import sys; magic=open(sys.argv[1],"rb").read(16); fields=magic.rstrip(b"\0").split(); sys.exit(0 if len(magic)==16 and fields==[b"dyld_v1",b"arm64"] else "invalid primary arm64 dyld cache magic")' "$cache"
df -h "$work/root"
unmount_one "$work/root"
# Linux hfsplus decomposes some non-ASCII names (localized Shortcuts examples)
# differently from Apple's tables; let fsck_hfs rewrite them, then verify.
fsck.hfsplus -f -y "$out" | grep -v 'Illegal name' || true
fsck.hfsplus -f -n "$out"
