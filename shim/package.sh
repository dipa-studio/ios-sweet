
#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
MINIMAL="$ROOT/shim/minimal"
ORIGINAL="$ROOT/original/unpacked"
OUT="$MINIMAL/out"

# Verified stock boot-image parameters.
BASE=0x40000000
KERNEL_OFFSET=0x00080000
RAMDISK_OFFSET=0x11B00000
TAGS_OFFSET=0x07880000
DTB_OFFSET=0x07880000
PAGE_SIZE=2048

HEADER_VERSION=2
OS_VERSION="13.0.0"
OS_PATCH_LEVEL="2024-04"

for tool in mkbootimg gzip; do
    command -v "$tool" >/dev/null 2>&1 || {
        echo "Missing tool: $tool" >&2
        exit 1
    }
done

# Check all inputs.
for f in \
    "$OUT/Image" \
    "$ORIGINAL/ramdisk" \
    "$ORIGINAL/dtb"; do
    [[ -f "$f" ]] || {
        echo "Missing input: $f" >&2
        exit 1
    }
done

mkdir -p "$OUT"

echo "[1/4] Compressing minimal shim..."
gzip -n -9 -c "$OUT/Image" > "$OUT/kernel.gz"

echo "[2/4] Preserving original ramdisk and DTB..."
cp "$ORIGINAL/ramdisk" "$OUT/ramdisk.gz"
cp "$ORIGINAL/dtb" "$OUT/dtb"

echo "[3/4] Building boot image..."

mkbootimg \
    --header_version "$HEADER_VERSION" \
    --kernel "$OUT/kernel.gz" \
    --ramdisk "$OUT/ramdisk.gz" \
    --dtb "$OUT/dtb" \
    --base "$BASE" \
    --kernel_offset "$KERNEL_OFFSET" \
    --ramdisk_offset "$RAMDISK_OFFSET" \
    --tags_offset "$TAGS_OFFSET" \
    --dtb_offset "$DTB_OFFSET" \
    --pagesize "$PAGE_SIZE" \
    --os_version "$OS_VERSION" \
    --os_patch_level "$OS_PATCH_LEVEL" \
    --cmdline "bootopt=64S3,32N2,64N2 androidboot.selinux=permissive androidboot.init_fatal_reboot_target=recovery kpti=off buildvariant=userdebug" \
    -o "$OUT/angelican-shim-boot.img"

echo "[4/4] Finished."

echo
echo "Output:"
stat -c '%n: %s bytes' "$OUT/angelican-shim-boot.img"
echo
echo "Original boot image was not modified."
