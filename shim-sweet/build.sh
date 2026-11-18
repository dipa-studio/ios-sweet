
#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Toolchain
CC="${CC:-aarch64-linux-gnu-gcc}"
OBJCOPY="${OBJCOPY:-aarch64-linux-gnu-objcopy}"
READELF="${READELF:-aarch64-linux-gnu-readelf}"
NM="${NM:-aarch64-linux-gnu-nm}"
HOST_CC="${HOST_CC:-gcc}"

# Build configuration
CFLAGS=(
    -O2
    -ffreestanding
    -nostdlib
    -fno-pic
    -mgeneral-regs-only
    -mstrict-align
    -fno-stack-protector
    -Wall
    -Wextra
)

mkdir -p out

# Check required build tools.
for tool in "$CC" "$OBJCOPY" "$READELF" "$NM" "$HOST_CC"; do
    command -v "$tool" >/dev/null 2>&1 || {
        echo "error: missing build tool: $tool" >&2
        exit 1
    }
done

echo "[1/5] Compiling ARM64 sources..."

SOURCES=(
    start.S
    shim.c
    console.c
    mmu.c
    fdt.c
    loader.c
    ufs.c
)

OBJECTS=()

for f in "${SOURCES[@]}"; do
    obj="out/${f%.*}.o"
    echo "  $f"
    "$CC" "${CFLAGS[@]}" -c "$f" -o "$obj"
    OBJECTS+=("$obj")
done

echo "[2/5] Checking relocations..."

# C objects must not contain absolute 64-bit relocations.
if "$READELF" -rW \
    out/shim.o \
    out/console.o \
    out/mmu.o \
    out/fdt.o \
    out/loader.o \
    out/ufs.o |
    grep -q 'R_AARCH64_ABS64'; then

    echo "error: absolute 64-bit relocation found in a C object" >&2
    exit 1
fi

echo "[3/5] Linking shim..."

"$CC" "${CFLAGS[@]}" \
    -static \
    -T shim.ld \
    -Wl,--build-id=none \
    -Wl,--no-warn-rwx-segments \
    -Wl,-N \
    "${OBJECTS[@]}" \
    -o out/shim.elf

echo "[4/5] Generating ARM64 Image..."

"$OBJCOPY" -O binary out/shim.elf out/Image

# Obtain _end without relying on non-portable awk strtonum().
END_HEX=$("$NM" -n out/shim.elf |
    awk '$3 == "_end" { print $1; exit }')

if [[ -z "$END_HEX" ]]; then
    echo "error: linker symbol _end not found" >&2
    exit 1
fi

IMAGE_SIZE=$((16#$END_HEX))

if (( IMAGE_SIZE == 0 )); then
    echo "error: invalid image size" >&2
    exit 1
fi

# Include .bss and stack storage in the image.
truncate -s "$IMAGE_SIZE" out/Image

echo "  Image size: $IMAGE_SIZE bytes"

echo "[5/5] Testing host console..."

"$HOST_CC" -O1 -Wall \
    -o out/host_test \
    console.c host_test.c

./out/host_test

echo
echo "Build successful."
echo "  ELF:   $SCRIPT_DIR/out/shim.elf"
echo "  Image: $SCRIPT_DIR/out/Image"

# ---------------------------------------------------------
# Optional boot image packaging.
#
# Do not assume PixelOS/Qualcomm boot parameters.
# Supply verified Angelican parameters through environment
# variables after inspecting the stock boot image.
# ---------------------------------------------------------

if [[ -n "${ANGELICAN_DTB:-}" ]]; then
    echo
    echo "Packaging Angelican boot image..."

    : "${BOOT_HEADER_VERSION:?Set BOOT_HEADER_VERSION}"
    : "${BOOT_BASE:?Set BOOT_BASE}"
    : "${BOOT_KERNEL_OFFSET:?Set BOOT_KERNEL_OFFSET}"
    : "${BOOT_RAMDISK_OFFSET:?Set BOOT_RAMDISK_OFFSET}"
    : "${BOOT_TAGS_OFFSET:?Set BOOT_TAGS_OFFSET}"
    : "${BOOT_DTB_OFFSET:?Set BOOT_DTB_OFFSET}"
    : "${BOOT_PAGE_SIZE:?Set BOOT_PAGE_SIZE}"

    command -v mkbootimg >/dev/null 2>&1 || {
        echo "error: mkbootimg is not installed" >&2
        exit 1
    }

    command -v cpio >/dev/null 2>&1 || {
        echo "error: cpio is not installed" >&2
        exit 1
    }

    if [[ ! -f "$ANGELICAN_DTB" ]]; then
        echo "error: DTB not found: $ANGELICAN_DTB" >&2
        exit 1
    fi

    # Use supplied ramdisk, or generate an empty diagnostic ramdisk.
    if [[ -n "${ANGELICAN_RAMDISK:-}" ]]; then
        [[ -f "$ANGELICAN_RAMDISK" ]] || {
            echo "error: ramdisk not found: $ANGELICAN_RAMDISK" >&2
            exit 1
        }
        cp "$ANGELICAN_RAMDISK" out/ramdisk.bin
    else
        mkdir -p out/rd
        (
            cd out/rd
            find . -print0 |
                cpio --null -o -H newc --quiet |
                gzip -9
        ) > out/ramdisk.bin
    fi

    mkbootimg \
        --header_version "$BOOT_HEADER_VERSION" \
        --kernel out/Image \
        --ramdisk out/ramdisk.bin \
        --dtb "$ANGELICAN_DTB" \
        --base "$BOOT_BASE" \
        --kernel_offset "$BOOT_KERNEL_OFFSET" \
        --ramdisk_offset "$BOOT_RAMDISK_OFFSET" \
        --tags_offset "$BOOT_TAGS_OFFSET" \
        --dtb_offset "$BOOT_DTB_OFFSET" \
        --pagesize "$BOOT_PAGE_SIZE" \
        --cmdline "${BOOT_CMDLINE:-}" \
        -o out/angelican-shim-boot.img

    echo "Boot image: $SCRIPT_DIR/out/angelican-shim-boot.img"
else
    echo
    echo "Skipping boot image packaging."
    echo "Set ANGELICAN_DTB and verified boot parameters to enable it."
fi

echo
echo "Done."
