#!/bin/bash
# Build the SWEET iOS root: one case-sensitive HFS+ image holding an iOS OS
# root filesystem plus its cryptexes, for the userdata partition (rd=ufsroot0).
#
#   mkiosroot.sh OS.dmg SYSTEMOS.dmg APPOS.dmg OUT.img [SIZE]     (SIZE default 16G)
#   SWEET_HFS_BACKEND=auto|native|guestmount (default auto)
#   SWEET_ROOT_TWEAKS=1 also applies the existing 20H392 bring-up tweaks.
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
root_tweaks=${SWEET_ROOT_TWEAKS:-0}
[[ $root_tweaks == 0 || $root_tweaks == 1 ]] ||
	{ echo "SWEET_ROOT_TWEAKS must be 0 or 1" >&2; exit 1; }
tweaks_tool="$(dirname "$0")/sweet-root-tweaks.py"
[[ -f $tweaks_tool ]] ||
	{ echo "missing existing root tweaks tool: $tweaks_tool" >&2; exit 1; }

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
probe_image=''

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
	if mountpoint -q "$point"; then
		echo "mount is still present: $point" >&2
		return 1
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
		if [[ -n $probe_image && -f $probe_image ]]; then
			echo "closed failed probe retained for inspection: $probe_image" >&2
		fi
		rm -f "$work"/*.dmg "$work"/*.files "$work"/*.fsck.log "$guest_pidfile"
		rmdir "$work"/* "$work" 2>/dev/null || true
	else
		echo "could not confirm all mounts are released under $work: left in place" >&2
		[[ -z $probe_image ]] || echo "probe image closure unconfirmed: $probe_image" >&2
		# A successful build must also release its source mounts. Preserve an
		# earlier failure code, but report cleanup failure after success.
		[[ $original_status != 0 ]] || exit 1
	fi
}
trap cleanup EXIT

hfs_mount() {
	local image=$1 point=$2 access=${3:-rw} guest_access mount_options native_options
	case $access in
		rw) guest_access=--rw; mount_options=rw,force; native_options=loop,force ;;
		ro) guest_access=--ro; mount_options=ro; native_options=loop,ro ;;
		*) echo "unknown HFS access mode: $access" >&2; return 1 ;;
	esac
	# Track even a partly failed mount so the EXIT trap can release it.
	mounts+=("$point")
	if [[ $backend == guestmount ]]; then
		guest_mount=$point
		# guestmount escapes commas inside each -o value. Keep just the
		# required FUSE access option; current guestmount rejects use_ino.
		sudo env LIBGUESTFS_BACKEND=direct LIBGUESTFS_BACKEND_SETTINGS=force_tcg \
			guestmount "$guest_access" --format=raw -a "$image" \
			-m "/dev/sda:/:$mount_options:hfsplus" --pid-file "$guest_pidfile" \
			-o allow_other "$point" || return
	else
		sudo mount -t hfsplus -o "$native_options" "$image" "$point" || return
	fi
	mountpoint -q "$point" || { echo "HFS mount did not appear: $point" >&2; return 1; }
}

hfs_check() {
	local image=$1 repair_status=0 readonly_log="$work/readonly.fsck.log" live_log="$work/live.fsck.log"
	[[ -z $guest_mount ]] || { echo "refusing fsck while guest writer is unconfirmed" >&2; return 1; }
	# Only newly created probe/output images reach this helper. Fresh journaled
	# HFSX and Linux's name tables may need repair; the strict second pass decides.
	fsck.hfsplus -f -y "$image" || repair_status=$?
	if [[ $repair_status != 0 ]]; then
		echo "HFS repair returned $repair_status; requiring clean read-only check" >&2
	fi
	if fsck.hfsplus -d -f -n "$image" > "$readonly_log" 2>&1; then
		cat "$readonly_log"
		return 0
	fi
	cat "$readonly_log"
	# fsck 540.1-Linux can retain its primary-header cache buffer during
	# IsJournalEmpty, then report EDEADLK (35) as a damaged volume header.
	# On an unmounted regular file, -l still checks every tree, bitmap and
	# volume header without writing, but skips that journal reader. Only use
	# it for this exact failure after independently checking the new journal.
	python3 - "$image" "$readonly_log" <<'PY_HFS_JOURNAL' || return 1
import os, re, stat, struct, sys
image, log_path = sys.argv[1:]
with open(log_path, encoding="utf-8", errors="replace") as source:
    log = source.read()
if "version 540.1-Linux" not in log or not re.search(r"invalid primary VHB at 2 result 35\b", log):
    sys.exit("HFS read-only check failed; journal-cache workaround does not apply")
if not re.search(r"VIStat = 0x8000, ABTStat = 0x0000 EBTStat = 0x0000\s+CBTStat = 0x0000 CatStat = 0x00000000", log):
    sys.exit("HFS check reported additional damage; refusing journal-cache workaround")
with open(image, "rb") as source:
    info = os.fstat(source.fileno())
    if not stat.S_ISREG(info.st_mode):
        sys.exit("journal-cache workaround requires a closed regular image")
    headers = []
    for offset in (1024, info.st_size - 1024):
        source.seek(offset)
        header = source.read(512)
        if len(header) != 512:
            sys.exit("short HFS volume header")
        signature, version, attributes, _, jib = struct.unpack_from(">HHIII", header)
        block_size, blocks = struct.unpack_from(">II", header, 40)
        if (signature, version) != (0x4858, 5) or block_size < 512 or block_size & (block_size - 1) or block_size * blocks != info.st_size:
            sys.exit("invalid HFSX header geometry")
        if attributes & 0x2100 != 0x2100 or attributes & 0x800:
            sys.exit("HFSX image must be cleanly unmounted and journaled")
        headers.append((block_size, blocks, jib))
    if headers[0] != headers[1]:
        sys.exit("HFSX headers disagree about journal or geometry")
    block_size, _, jib = headers[0]
    if jib < 1 or (jib + 1) * block_size > info.st_size:
        sys.exit("invalid HFS journal info block")
    source.seek(jib * block_size)
    journal_info = source.read(52)
    flags = struct.unpack_from(">I", journal_info)[0]
    offset, size = struct.unpack_from(">QQ", journal_info, 36)
    if flags != 5 or offset < block_size or offset % block_size or size < 512 or size % block_size or offset + size > info.st_size or offset < (jib + 1) * block_size and jib * block_size < offset + size:
        sys.exit("workaround requires an internal journal marked needsInit with valid bounds")
    source.seek(offset)
    remaining = size
    while remaining:
        chunk = source.read(min(remaining, 1024 * 1024))
        if not chunk or any(chunk):
            sys.exit("journal contains data; refusing journal-cache workaround")
        remaining -= len(chunk)
print("HFS new journal independently verified empty; using fsck cache workaround")
PY_HFS_JOURNAL
	fsck.hfsplus -d -l -f -n "$image" > "$live_log" 2>&1 || { cat "$live_log"; return 1; }
	cat "$live_log"
	python3 - "$live_log" <<'PY_HFS_COMPLETE'
import sys
with open(sys.argv[1], encoding="utf-8", errors="replace") as source:
    log = source.read()
stages = ("extents overflow file", "catalog file", "multi-linked files",
          "catalog hierarchy", "extended attributes file", "volume bitmap",
          "volume information")
if "(NO WRITE)" not in log or "appears to be OK." not in log or any(
        "Checking " + stage + "." not in log for stage in stages):
    sys.exit("HFS workaround did not complete every read-only filesystem check")
print("HFS complete read-only filesystem check passed")
PY_HFS_COMPLETE
}

image_resolve() {
	local result_var=$1 relative_path=$2 image_root=${3:-$work/root} resolved_image_path
	# A trailing NUL preserves names containing newlines. A failed resolver
	# produces no terminator, so read fails before any mkdir/cp/ln can run.
	if ! IFS= read -r -d '' resolved_image_path < <(
		python3 -c 'import os,runpy,sys; resolve=runpy.run_path(sys.argv[1])["image_path"]; os.write(1,os.fsencode(resolve(sys.argv[2],sys.argv[3]))+b"\0")' \
			"$tweaks_tool" "$image_root" "$relative_path"
	); then
		echo "cannot resolve path within root image: $relative_path" >&2
		return 1
	fi
	printf -v "$result_var" '%s' "$resolved_image_path"
}

# Exercise the actual mount backend before allocating the output image or
# opening the Apple volumes. HFSX case handling and Unix metadata are required.
echo "checking HFSX backend: $backend"
mkdir "$work/probe"
probe_image=$(mktemp "${out}.probe.XXXXXX")
truncate -s 64M "$probe_image"
mkfs.hfsplus -s -J -v HFSXProbe "$probe_image" >/dev/null
hfs_mount "$probe_image" "$work/probe"
printf 'HFSX probe\n' | sudo tee "$work/probe/file" >/dev/null
sudo chown 501:20 "$work/probe/file"
sudo chmod 0640 "$work/probe/file"
sudo ln "$work/probe/file" "$work/probe/hardlink"
sudo ln -s file "$work/probe/symlink"
# Finish every mutation before checking through a fresh read-only mount.
# FUSE can cache separate size/data attributes for two hardlink paths.
printf 'hardlink update\n' | sudo tee "$work/probe/hardlink" >/dev/null
printf 'upper\n' | sudo tee "$work/probe/Case" >/dev/null
printf 'lower\n' | sudo tee "$work/probe/case" >/dev/null
unmount_one "$work/probe"
hfs_check "$probe_image"
hfs_mount "$probe_image" "$work/probe" ro
sudo python3 - "$work/probe" <<'PY_PROBE'
import os, stat, sys
root = sys.argv[1]
expected = (501, 20, 0o640, 2)
payload = b"hardlink update\n"
errors = []
for name in ("file", "hardlink"):
    path = os.path.join(root, name)
    info = os.lstat(path)
    actual = (info.st_uid, info.st_gid, stat.S_IMODE(info.st_mode), info.st_nlink)
    print(f"HFSX probe metadata {name}: {actual[0]}:{actual[1]}:{actual[2]:o}:{actual[3]}")
    if not stat.S_ISREG(info.st_mode) or actual != expected:
        errors.append(f"{name}: expected regular file with 501:20:640:2, got {actual!r}")
    with open(path, "rb") as source:
        data = source.read()
    if data != payload:
        errors.append(f"{name}: expected {payload!r}, got {data!r}")
link = os.path.join(root, "symlink")
if not os.path.islink(link) or os.readlink(link) != "file":
    errors.append("symlink target is not file")
else:
    with open(link, "rb") as source:
        if source.read() != payload:
            errors.append("symlink does not resolve to updated file contents")
for name, wanted in (("Case", b"upper\n"), ("case", b"lower\n")):
    with open(os.path.join(root, name), "rb") as source:
        actual = source.read()
    if actual != wanted:
        errors.append(f"{name}: expected {wanted!r}, got {actual!r}")
if errors:
    for error in errors:
        print("HFSX persisted probe failed: " + error, file=sys.stderr)
    sys.exit(1)
print("HFSX persisted metadata, hardlink, symlink and case checks passed")
PY_PROBE
unmount_one "$work/probe"
rm -f "$probe_image"
probe_image=''
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
	mounts+=("$work/$2")
	sudo "$(command -v apfs-fuse)" "$work/$2.dmg" "$work/$2"
	mountpoint -q "$work/$2" || { echo "APFS mount did not appear: $2" >&2; return 1; }
}
apfs_mount "$os" os
apfs_mount "$sysos" sysos
apfs_mount "$appos" appos

cache_rel=System/Library/Caches/com.apple.dyld
for source in os sysos appos; do
	sudo test -d "$work/$source/root" ||
		{ echo "missing APFS root directory: $source" >&2; exit 1; }
done
sudo test -s "$work/os/root/sbin/launchd" || { echo "missing source launchd" >&2; exit 1; }
sudo test -s "$work/sysos/root/$cache_rel/dyld_shared_cache_arm64" ||
	{ echo "missing source primary arm64 dyld cache" >&2; exit 1; }
if [[ $root_tweaks == 1 ]]; then
	python3 - "$work/os/root/System/Library/CoreServices/SystemVersion.plist" <<'PY_TWEAK_VERSION'
import plistlib, sys
with open(sys.argv[1], "rb") as source:
    version = plistlib.load(source)
if (version.get("ProductVersion"), version.get("ProductBuildVersion")) != ("16.7.16", "20H392"):
    sys.exit("existing root tweaks require iOS 16.7.16 / 20H392")
PY_TWEAK_VERSION
fi
# Enumerate immutable sources, not the just-populated destination FUSE cache.
# Save NUL-delimited lists first so find failures propagate before allocation.
for c in OS App; do
	if [[ $c == OS ]]; then source="$work/sysos/root"; else source="$work/appos/root"; fi
	(cd "$source" && sudo find . ! -type d ! -path './System/Library/Caches/com.apple.dyld/*' -print0) > "$work/$c.files"
done

# Atomically claim a new regular output. A concurrent build must fail rather
# than truncate or format the image another build has already started writing.
python3 -c 'import os,sys; os.close(os.open(sys.argv[1], os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600))' "$out"
truncate -s "$size" "$out"
mkfs.hfsplus -s -J -v iOSRoot "$out"
mkdir "$work/root"
hfs_mount "$out" "$work/root"

copy() {
	local destination
	image_resolve destination "$2"
	echo "copying $1 -> /$2"
	sudo mkdir -p "$destination"
	sudo rsync -aH --numeric-ids --info=progress2 "$1/" "$destination/"
}
copy "$work/os/root" .
copy "$work/sysos/root" private/preboot/Cryptexes/OS
copy "$work/appos/root" private/preboot/Cryptexes/App

# Bind the cryptexes to this single-volume layout. Relative links also resolve
# within the image when host tools inspect them before installation.
image_resolve cryptex_links System/Cryptexes
sudo mkdir -p "$cryptex_links"
for c in OS App; do
	# Compute an equivalent relative link from the physical parent directory.
	image_resolve cryptex_target "private/preboot/Cryptexes/$c"
	cryptex_link=$(python3 -c 'import os,sys; print(os.path.relpath(sys.argv[1],sys.argv[2]))' "$cryptex_target" "$cryptex_links")
	sudo ln -sfn -T "$cryptex_link" "$cryptex_links/$c"
done

# Shared cache where dyld looks at ignition level 1: hard links, no extra space.
dsc=private/preboot/Cryptexes/OS/$cache_rel
image_resolve cache_parent System/Library/Caches
cache_directory="$cache_parent/com.apple.dyld"
if sudo test -L "$cache_directory"; then sudo rm "$cache_directory"; fi
sudo mkdir -p "$cache_directory"
image_resolve cryptex_cache_directory "$dsc"
for f in "$work/sysos/root/$cache_rel"/*; do
	sudo test -f "$f" || { echo "unsupported dyld cache entry: $f" >&2; exit 1; }
	name=${f##*/}
	[[ $cryptex_cache_directory/$name != "$cache_directory/$name" ]] || continue
	if sudo test -L "$f"; then
		sudo cp -pP -T "$f" "$cache_directory/$name"
	else
		sudo ln -f -T "$cryptex_cache_directory/$name" "$cache_directory/$name"
	fi
done

# dyld does not search the cryptexes at ignition level 1: hard-link every
# cryptex file that has no counterpart in the OS root (libobjc-trampolines,
# libffi-trampolines, libstdc++, ...) to its root path.
declare -A linked_cryptex_files=()
for c in OS App; do
	if [[ $c == OS ]]; then source="$work/sysos/root"; else source="$work/appos/root"; fi
	while IFS= read -r -d '' f; do
		f=${f#./}
		if [[ $f == */* ]]; then parent=${f%/*}; else parent=.; fi
		image_resolve original_parent "$parent" "$work/os/root"
		original_target="$original_parent/${f##*/}"
		if ! sudo test -e "$original_target" && ! sudo test -L "$original_target" &&
		    [[ ! ${linked_cryptex_files["$f"]+present} ]]; then
			image_resolve target_parent "$parent"
			target="$target_parent/${f##*/}"
			# OS directory symlinks can already expose the copied cryptex file.
			if sudo test -e "$target" || sudo test -L "$target"; then continue; fi
			image_resolve src "private/preboot/Cryptexes/$c/$f"
			[[ $src != "$target" ]] || continue
			sudo mkdir -p "$target_parent"
			# Linux hfsplus cannot hard-link symlinks: copy those.
			if sudo test -L "$source/$f"; then sudo cp -pP -T "$source/$f" "$target"; else sudo ln -T "$src" "$target"; fi
			linked_cryptex_files["$f"]=1
			echo "linked $c:/$f"
		fi
	done < "$work/$c.files"
done

# logd's log stores, normally made at restore: it checks owner _logd (272)
# and mode, plus a .migrated marker, else asks a helper and crashes
# ("BUG IN LIBTRACE: Failed to migrate directory").
for d in diagnostics uuidtext diagnostics/timesync; do
	image_resolve log_directory "private/var/db/$d"
	if [[ $d == diagnostics ]]; then log_mode=0751; else log_mode=0755; fi
	sudo install -d -o 272 -g 272 -m "$log_mode" "$log_directory"
	image_resolve log_marker "private/var/db/$d/.migrated"
	sudo install -o 272 -g 272 -m 0644 /dev/null "$log_marker"
done

# System keybag for the built-in AppleKeyStore (no passcode).
image_resolve keybags private/var/keybags
sudo install -d -m 0700 -o 0 -g 0 "$keybags"
image_resolve keybag_file private/var/keybags/systembag.kb
printf '%s\n' '<?xml version="1.0" encoding="UTF-8"?>' \
	'<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">' \
	'<plist version="1.0"><dict><key>KeyBagKeys</key><data>U1dFRVQ=</data></dict></plist>' |
	sudo install -m 0600 -o 0 -g 0 /dev/stdin "$keybag_file"

if [[ $root_tweaks == 1 ]]; then
	for directory in private/var/mobile private/var/mobile/Library private/var/mobile/Library/Preferences; do
		image_resolve mobile_directory "$directory"
		sudo install -d -o 501 -g 501 -m 0755 "$mobile_directory"
	done
	sudo python3 "$tweaks_tool" "$work/root"
fi
df -h "$work/root"
unmount_one "$work/root"
hfs_check "$out"
hfs_mount "$out" "$work/root" ro
sudo python3 - "$work/root" "$work/os/root" "$root_tweaks" "$tweaks_tool" <<'PY_ROOT'
import os, plistlib, runpy, stat, struct, sys
root, original, tweaks, tool = sys.argv[1:]
resolve_image = runpy.run_path(tool)["image_path"]

def in_image(path):
    return resolve_image(root, path)

def metadata(path, wanted):
    info = os.stat(in_image(path))
    actual = (info.st_uid, info.st_gid, stat.S_IMODE(info.st_mode))
    if actual != wanted:
        raise ValueError(f"{path}: metadata {actual!r}, expected {wanted!r}")
    return info

try:
    for path, filetype in (("sbin/launchd", 2), ("usr/lib/dyld", 7)):
        info = os.stat(in_image(path))
        if not stat.S_ISREG(info.st_mode) or info.st_size == 0 or info.st_uid != 0 or not info.st_mode & 0o111:
            raise ValueError("missing root-owned executable: " + path)
        with open(in_image(path), "rb") as source:
            header = source.read(32)
        if len(header) != 32 or struct.unpack_from("<I", header)[0] != 0xfeedfacf or struct.unpack_from("<I", header, 4)[0] != 0x100000c or struct.unpack_from("<I", header, 12)[0] != filetype:
            raise ValueError("invalid ARM64 Mach-O executable header: " + path)
    for name in ("OS", "App"):
        path = "System/Cryptexes/" + name
        target = in_image("private/preboot/Cryptexes/" + name)
        if in_image(path) != target or not os.path.isdir(target):
            raise ValueError("missing cryptex contents: " + path)
    caches = ("System/Library/Caches/com.apple.dyld/dyld_shared_cache_arm64",
              "private/preboot/Cryptexes/OS/System/Library/Caches/com.apple.dyld/dyld_shared_cache_arm64")
    cache_paths = tuple(in_image(path) for path in caches)
    minimum_links = 1 if cache_paths[0] == cache_paths[1] else 2
    sizes = []
    for path in caches:
        info = os.stat(in_image(path))
        with open(in_image(path), "rb") as source:
            magic = source.read(16)
        if info.st_size == 0 or info.st_nlink < minimum_links or len(magic) != 16 or magic.rstrip(b"\0").split() != [b"dyld_v1", b"arm64"]:
            raise ValueError("invalid or unlinked primary arm64 cache: " + path)
        sizes.append(info.st_size)
    if sizes[0] != sizes[1]:
        raise ValueError("cache aliases have different sizes")
    with open(os.path.join(original, "System/Library/CoreServices/SystemVersion.plist"), "rb") as source:
        expected_version = plistlib.load(source)
    with open(in_image("System/Library/CoreServices/SystemVersion.plist"), "rb") as source:
        version = plistlib.load(source)
    for key in ("ProductVersion", "ProductBuildVersion"):
        if not version.get(key) or version[key] != expected_version.get(key):
            raise ValueError("root version differs from source: " + key)
    metadata("private/var/keybags/systembag.kb", (0, 0, 0o600))
    metadata("private/var/keybags", (0, 0, 0o700))
    metadata("private/var/db/diagnostics", (272, 272, 0o751))
    for name in ("uuidtext", "diagnostics/timesync"):
        metadata("private/var/db/" + name, (272, 272, 0o755))
    for name in ("diagnostics", "uuidtext", "diagnostics/timesync"):
        metadata("private/var/db/" + name + "/.migrated", (272, 272, 0o644))
    if tweaks == "1":
        metadata("private/var/mobile/Library/Preferences/com.apple.migration.plist", (501, 501, 0o600))
        with open(in_image("private/var/mobile/Library/Preferences/com.apple.migration.plist"), "rb") as source:
            if plistlib.load(source).get("LastSystemVersion") != version["ProductBuildVersion"]:
                raise ValueError("root migration tweak is missing")
    print("iOS persisted root checks passed: " + version["ProductVersion"] + " / " + version["ProductBuildVersion"])
except (OSError, ValueError, plistlib.InvalidFileException) as error:
    sys.exit("iOS persisted root check failed: " + str(error))
PY_ROOT
unmount_one "$work/root"
echo "iOS root image verified and closed: $out"
