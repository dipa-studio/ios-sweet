#!/bin/bash
# Build the Mi 8 (dipper, SDM845) diagnostic shim and pack it into fastboot-bootable boot images.
#   needs: aarch64-linux-gnu-{gcc,objcopy,nm,readelf} (apt: gcc-aarch64-linux-gnu), python3
#   MI8_RESET=android (default) | bootloader : where the shim resets to when it is done
# Output: mi8/out/mi8-diag-gz.img (try first) and mi8/out/mi8-diag-ucomp.img (fallback).
# Never flash these: `fastboot boot <img>` only.
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
shim="$here/../shim"
out="$here/out"
CROSS="${CROSS:-aarch64-linux-gnu-}"
CC="${CROSS}gcc"; OBJCOPY="${CROSS}objcopy"; NM="${CROSS}nm"; READELF="${CROSS}readelf"
# Same flags as shim/build.sh, plus: no vectorizer (it turns constant string pointers into data) and no unwind
# tables (shim.ld discards them anyway). Nothing here changes what the code does.
CFLAGS="-O2 -ffreestanding -nostdlib -fno-pic -mgeneral-regs-only -mstrict-align -fno-stack-protector \
	-fno-tree-vectorize -fno-tree-slp-vectorize -fno-asynchronous-unwind-tables -fno-unwind-tables \
	-Wall -Wextra -DTARGET_MI8 -I$shim"
if [ "${MI8_RESET:-android}" = bootloader ]; then CFLAGS="$CFLAGS -DMI8_RESET_BOOTLOADER"; fi
rm -rf "$out"; mkdir -p "$out"
# Host tests first: shim/mi8.c against a fake SoC + FTS slave model, and the touch firmware burn against ST's command stream.
bash "$here/host/run_tests.sh" "$shim" "$out/host"
# Optional touch firmware (mi8/fw/st_fts_e1.ftb): embedded in the shim, the touch probe burns it if the chip's version differs.
FTS_OBJ=""
if [ -f "$here/fw/st_fts_e1.ftb" ]; then
	cp "$here/fw/st_fts_e1.ftb" "$out/st_fts_e1.ftb"
	CFLAGS="$CFLAGS -DMI8_FTS_FW"
	FTS_OBJ="$out/ftsfw.o"
	echo "touch firmware embedded: $(stat -c %s "$here/fw/st_fts_e1.ftb") bytes"
else
	echo "no mi8/fw/st_fts_e1.ftb: building without the touch firmware burn"
fi
for f in start.S shim.c console.c mmu.c fdt.c loader.c ufs.c mi8.c; do
	$CC $CFLAGS -c "$shim/$f" -o "$out/${f%.*}.o"
done
if [ -n "$FTS_OBJ" ]; then $CC $CFLAGS -I"$out" -c "$shim/ftsfw.S" -o "$FTS_OBJ"; fi
# The image runs wherever ABL puts it with no relocation pass, so no object may carry an absolute (ABS64)
# relocation in a section that ends up in the image. Report every offender, not just a count.
bad=0
for o in shim console mmu fdt loader ufs mi8; do
	hits=$($READELF -rW "$out/$o.o" | awk -v f="$o.o" '/^Relocation section/{sec=$3; gsub("\047","",sec)} /R_AARCH64_ABS64/ && sec !~ /eh_frame|debug|note|comment/ {print "  " f " " sec ": " $0}')
	if [ -n "$hits" ]; then echo "absolute relocations in $o.o:" >&2; echo "$hits" >&2; bad=1; fi
done
[ "$bad" = 0 ] || { echo "error: absolute relocations in C objects (see above)" >&2; exit 1; }
$CC $CFLAGS -static -T "$shim/shim.ld" -Wl,--build-id=none -Wl,--no-warn-rwx-segments -Wl,-N \
	"$out"/{start,shim,console,mmu,fdt,loader,ufs,mi8}.o $FTS_OBJ -o "$out/shim.elf"
$OBJCOPY -O binary "$out/shim.elf" "$out/Image"
size=$((16#$($NM "$out/shim.elf" | awk '$3=="_end"{print $1}')))
truncate -s "$size" "$out/Image"
python3 - "$out/Image" <<'PY'
import struct, sys
img = open(sys.argv[1], "rb").read()
assert img[0x38:0x3C] == b"ARM\x64", "arm64 Image magic missing"
text_off, image_size, flags = struct.unpack("<QQQ", img[8:32])
assert text_off == 0x80000, "text_offset %#x" % text_off
assert image_size == len(img), "image_size %#x != file size %#x" % (image_size, len(img))
print("Image ok: %d bytes, text_offset %#x, flags %#x" % (len(img), text_off, flags))
PY
# MI8_PAYLOAD=path/to/payload.bin: carry the XNU payload as the ramdisk (mi8-xnu-*.img); otherwise the diagnostic only.
prefix=mi8-diag; extra=()
if [ -n "${MI8_PAYLOAD:-}" ]; then prefix=mi8-xnu; extra=(--ramdisk "$MI8_PAYLOAD"); fi
for mode in gz ucomp; do
	python3 "$here/mkimg_v1.py" --image "$out/Image" --dtb "$here/fdt/mi8-dipper-mp-v2.1.dtb" \
		--mode "$mode" "${extra[@]}" --out "$out/$prefix-$mode.img"
done
ls -l "$out"/Image "$out"/mi8-*.img
