#!/bin/bash
# Build the M30s shim and wrap it in an Odin-flashable tar.md5 or Android boot.img v4
set -euo pipefail
cd "$(dirname "$0")"

CC=aarch64-linux-gnu-gcc
OBJCOPY=aarch64-linux-gnu-objcopy
CFLAGS="-O2 -ffreestanding -nostdlib -fno-pic -mgeneral-regs-only -mstrict-align -fno-stack-protector -Wall -Wextra"

mkdir -p out

for f in start.S shim.c console.c mmu.c fdt.c loader.c font.c; do
	$CC $CFLAGS -c $f -o out/${f%.*}.o
done

# Check for absolute relocations
abs=$(aarch64-linux-gnu-readelf -r out/shim.o out/console.o out/mmu.o out/fdt.o out/loader.o out/font.o 2>/dev/null | grep -c ABS64 || true)
[ "$abs" = 0 ] || { echo "error: $abs absolute relocations in C objects" >&2; exit 1; }

$CC $CFLAGS -static -T shim.ld -Wl,--build-id=none -Wl,--no-warn-rwx-segments -Wl,-N \
	out/start.o out/shim.o out/console.o out/mmu.o out/fdt.o out/loader.o out/font.o -o out/shim.elf

$OBJCOPY -O binary out/shim.elf out/Image

# Pad to image_size so .bss/stacks exist as zeroed bytes
size=$(aarch64-linux-gnu-nm out/shim.elf | awk '$3=="_end"{print strtonum("0x"$1)}')
truncate -s "$size" out/Image

# Ramdisk: an xnu payload (tools/mkpayload.py) if given as $1, else an empty newc cpio
if [ -n "${1:-}" ]; then
	cp "$1" out/ramdisk.bin
else
	(cd out && rm -rf rd && mkdir rd && cd rd && find . | cpio -o -H newc --quiet | gzip -9 > ../ramdisk.bin)
fi

# Samsung S-Boot expects boot.img header v2/v4 with specific load addresses
# Kernel load address for Exynos: typically 0x80000000 or 0x40008000
KERNEL_ADDR=0x80000000
RAMDISK_ADDR=0x84000000
DTB_ADDR=0x83000000
PAGE_SIZE=4096

# Build Android boot.img v4 (for TWRP - modern, supports separate DTB)
mkbootimg --header_version 4 \
	--kernel out/Image \
	--ramdisk out/ramdisk.bin \
	--dtb /dev/null \
	--base 0 \
	--kernel_offset $KERNEL_ADDR \
	--ramdisk_offset $RAMDISK_ADDR \
	--dtb_offset $DTB_ADDR \
	--pagesize $PAGE_SIZE \
	--os_version 14.0.0 \
	--os_patch_level 2024-01 \
	--cmdline "console=null" \
	-o out/shim-boot.img

# Also build boot.img v3 with DTB appended to kernel (legacy TWRP compatibility)
# Extract stock DTB if available
if [ -f "../../dtb/m30s_unpacked/dtb" ]; then
	cat out/Image ../../dtb/m30s_unpacked/dtb > out/Image-dtb
	mkbootimg --header_version 3 \
		--kernel out/Image-dtb \
		--ramdisk out/ramdisk.bin \
		--base 0 \
		--kernel_offset $KERNEL_ADDR \
		--ramdisk_offset $RAMDISK_ADDR \
		--pagesize $PAGE_SIZE \
		--os_version 14.0.0 \
		--os_patch_level 2024-01 \
		--cmdline "console=null" \
		-o out/shim-boot-v3.img
	echo "Built legacy boot.img v3 with appended DTB: out/shim-boot-v3.img"
fi

# Also create Odin-flashable tar.md5 (for Samsung Odin tool)
cd out
tar -cf shim-boot.tar shim-boot.img
md5sum shim-boot.tar > shim-boot.tar.md5
cat shim-boot.tar.md5 >> shim-boot.tar
mv shim-boot.tar shim-boot.tar.md5
cd ..

# Host render of the console layout
gcc -O1 -Wall -o out/host_test console.c ../host_test.c && ./out/host_test

ls -l out/Image out/shim-boot.img out/shim-boot.tar.md5