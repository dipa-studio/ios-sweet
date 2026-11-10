#!/bin/bash
# Build the SM-A510F probe as a Samsung recovery image plus an Odin tar.
#
# Needs (Ubuntu): gcc gcc-aarch64-linux-gnu device-tree-compiler libfdt-dev
#                 libssl-dev cpio git
# Output: a510f/out/recovery.img, a510f/out/a510f-probe-recovery.tar
set -euo pipefail
cd "$(dirname "$0")"

OUT=out
CC=aarch64-linux-gnu-gcc
OBJCOPY=aarch64-linux-gnu-objcopy
# LineageOS exynos7580-common kernel: source of the a5xelte device trees.
KREPO=https://github.com/Exynos7580/android_kernel_samsung_exynos7580-common
KSHA=5a9711eabaa7df7a1136ccddc2b14b668ba657a4	# lineage-15.1

rm -rf "$OUT/dtb" "$OUT/probe"
mkdir -p "$OUT/dtb" "$OUT/probe"

# --- 1. device trees -------------------------------------------------------
# S-Boot only boots images whose dt.img has an entry for this board, so we
# ship the same a5xelte EUR-open device trees LineageOS ships.
K="$OUT/kernel"
if [ ! -d "$K/.git" ]; then
	git init -q "$K"
	git -C "$K" remote add origin "$KREPO"
	git -C "$K" config core.sparseCheckout true
	printf '%s\n' /arch/arm64/boot/dts/ /include/dt-bindings/ > "$K/.git/info/sparse-checkout"
	git -C "$K" fetch -q --depth 1 --filter=blob:none origin "$KSHA"
	git -C "$K" checkout -q FETCH_HEAD
fi
DTS="$K/arch/arm64/boot/dts"
n=0
for f in "$DTS"/exynos7580-a5xelte_eur_open_[0-9][0-9].dts; do
	b=$(basename "$f" .dts)
	cpp -nostdinc -undef -D__DTS__ -x assembler-with-cpp \
		-I "$DTS" -I "$DTS/include" -I "$K/include" "$f" \
		| dtc -q -I dts -O dtb -i "$DTS" -o "$OUT/dtb/$b.dtb" -
	n=$((n + 1))
done
[ "$n" -gt 0 ] || { echo "error: no a5xelte_eur_open device trees found" >&2; exit 1; }
echo "built $n device trees"

# --- 2. Samsung boot image tool (LineageOS hardware/samsung/dtbhtool) ------
gcc -O2 -Wno-deprecated-declarations -I tools/dtbhtool -I tools/dtbhtool/libdtbimg \
	tools/dtbhtool/mkbootimg.c tools/dtbhtool/dtbimg.c -lfdt -lcrypto \
	-o "$OUT/mkdtbhbootimg"

# --- 3. probe image ---------------------------------------------------------
CFLAGS="-O2 -ffreestanding -nostdlib -fno-pic -mcmodel=tiny -mgeneral-regs-only \
	-mstrict-align -fno-stack-protector -fno-builtin -Wall -Wextra"
for f in start.S probe.c; do
	$CC $CFLAGS -c "probe/$f" -o "$OUT/probe/${f%.*}.o"
done
# The image runs wherever S-Boot puts it with no relocation pass: only the
# header's image_size (start.o, linked at 0) may be an absolute address.
abs=$(aarch64-linux-gnu-readelf -r "$OUT/probe/probe.o" | grep -c ABS64 || true)
[ "$abs" = 0 ] || { echo "error: $abs absolute relocations in probe.o" >&2; exit 1; }
$CC $CFLAGS -static -T probe/probe.ld -Wl,--build-id=none -Wl,--no-warn-rwx-segments -Wl,-N \
	"$OUT/probe/start.o" "$OUT/probe/probe.o" -o "$OUT/probe/probe.elf"
$OBJCOPY -O binary "$OUT/probe/probe.elf" "$OUT/probe/Image"
# Pad to image_size so .bss and the stacks exist as zeroed bytes.
size=$(aarch64-linux-gnu-nm "$OUT/probe/probe.elf" | awk '$3=="_end"{print strtonum("0x"$1)}')
truncate -s "$size" "$OUT/probe/Image"

# Empty newc ramdisk: bootloaders tend to dislike a zero-size one.
(cd "$OUT/probe" && rm -rf rd && mkdir rd && cd rd && find . | cpio -o -H newc --quiet | gzip -9 > ../ramdisk.gz)

# --- 4. recovery.img, same layout as LineageOS a5xeltexx -------------------
"$OUT/mkdtbhbootimg" --kernel "$OUT/probe/Image" --ramdisk "$OUT/probe/ramdisk.gz" \
	--dt_dir "$OUT/dtb" --base 0x10000000 --pagesize 2048 \
	--kernel_offset 0x00008000 --ramdisk_offset 0x01000000 --tags_offset 0x00000100 \
	--board SRPOJ08A000KU --cmdline "" -o "$OUT/recovery.img"
printf 'SEANDROIDENFORCE' >> "$OUT/recovery.img"

# Sanity: header magic, non-empty DT section with a DTBH table.
python3 - "$OUT/recovery.img" <<'EOF'
import struct, sys
d = open(sys.argv[1], 'rb').read()
assert d[:8] == b'ANDROID!', 'bad boot magic'
ks, ka, rs, ra, ss, sa, ta, ps, dts = struct.unpack_from('<9I', d, 8)
pg = lambda n: (n + ps - 1) // ps * ps
off = ps + pg(ks) + pg(rs) + pg(ss)
assert dts > 0 and d[off:off + 4] == b'DTBH', 'no DTBH dt section'
ver, cnt = struct.unpack_from('<2I', d, off + 4)
revs = [struct.unpack_from('<8I', d, off + 12 + 32 * i)[3] for i in range(cnt)]
print(f'recovery.img: kernel {ks} B, page {ps}, dt.img v{ver} with {cnt} entries, hw_rev {revs}')
EOF

# --- 5. Odin tar (flash in the AP slot) ------------------------------------
(cd "$OUT" && rm -f a510f-probe-recovery.tar && tar -H ustar -cf a510f-probe-recovery.tar recovery.img)
ls -l "$OUT/probe/Image" "$OUT/recovery.img" "$OUT/a510f-probe-recovery.tar"
