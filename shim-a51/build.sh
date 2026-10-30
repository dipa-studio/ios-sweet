#!/bin/bash
# Build the A51 probe shim and wrap it in a boot.img v2 that copies the
# header of the phone's own boot.img (backup/a51/boot.img, not in git).
# Toolchain: clang targeting aarch64 ELF. Links with ld.lld if present,
# otherwise with tools/minild.py (same layout as shim/shim.ld). Set CC/LD to
# an aarch64-linux-gnu gcc toolchain to use binutils instead.
set -euo pipefail
cd "$(dirname "$0")"
CC=${CC:-clang}
LD=${LD:-$(command -v ld.lld || true)}
TEMPLATE=${TEMPLATE:-../backup/a51/boot.img}
CFLAGS="--target=aarch64-linux-gnu -O2 -ffreestanding -nostdlib -fno-pic -mgeneral-regs-only
	-mstrict-align -fno-stack-protector -fno-jump-tables -Wall -Wextra -I../shim
	-DFB_BASE=0xca000000UL -DFB_W=1080 -DFB_H=2400 -DFB_STRIDE=4320"
mkdir -p out
$CC $CFLAGS -c start.S -o out/start.o
$CC $CFLAGS -c shim.c -o out/shim.o
$CC $CFLAGS -c ../shim/console.c -o out/console.o
$CC $CFLAGS -c ../shim/loader.c -o out/loader.o
$CC $CFLAGS -c ../shim/fdt.c -o out/fdt.o
# The image runs wherever S-Boot puts it with no relocation pass: only the
# header's image_size (start.o, linked at 0) may be an absolute address.
python3 ../tools/check-abs-relocs.py out/shim.o out/console.o out/loader.o out/fdt.o
OBJS="out/start.o out/shim.o out/console.o out/loader.o out/fdt.o"
if [ -n "$LD" ]; then
	$LD -static -T ../shim/shim.ld --build-id=none -N $OBJS -o out/shim.elf
	python3 ../tools/elf2bin.py out/shim.elf out/Image
else
	python3 ../tools/minild.py out/Image --map out/shim.map $OBJS
fi
# Ramdisk: an xnu payload (tools/mkpayload.py) if given as $1, else empty -> probe.
python3 ../tools/mkbootimg_v2.py "$TEMPLATE" out/shim-a51-boot.img --kernel out/Image \
	${1:+--ramdisk "$1"} --cmdline "console=null"
ls -l out/Image out/shim-a51-boot.img
