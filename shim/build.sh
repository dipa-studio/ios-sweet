#!/bin/bash
# Build the shim and wrap it in an Android boot image.
#
#   build.sh [PAYLOAD] [--template STOCK_BOOT_IMG] [--dtb DTB] [--v2] [--v4]
#
# PAYLOAD        xnu payload from tools/mkpayload.py; boot v4 embeds it in
#                the kernel Image (v2 still uses the legacy ramdisk channel)
# --template     copy the header shape (and boot signature) from this image
# --dtb          boot image v2 only: append the device tree (sweet)
# --v2 / --v4    force the header version (default: the template's, else v4)
#
# Works with an aarch64-linux-gnu cross toolchain or with clang + lld.
set -euo pipefail
cd "$(dirname "$0")"

SRCS="start.S shim.c console.c display.c diag.c mmu.c fdt.c board.c loader.c ufs.c str.c logstore.c"
PAYLOAD=""
TEMPLATE=""
DTB=""
HV=""
RAW=""
KICK=""

while [ $# -gt 0 ]; do
	case "$1" in
	--template) TEMPLATE=$2; shift 2 ;;
	--dtb) DTB=$2; shift 2 ;;
	--v2) HV=2; shift ;;
	--v4) HV=4; shift ;;
	--raw) RAW=1; shift ;;
	--kick) KICK=1; shift ;;
	*) PAYLOAD=$1; shift ;;
	esac
done
[ -n "${KICK:-}" ] && SRCS="$SRCS entryprobe_display.c"

# On boot v4, keep boot.img's generic ramdisk byte-for-byte intact; the
# recovery ramdisk resides separately in vendor_boot. A raw payload appended
# to the generic ramdisk's compressed LZ4 stream has unverified parsing; the old
# 1,250,233-byte stream put SWEETXNU at an unaligned address that the loader
# never scanned. Carry the payload in the kernel Image instead.
EMBED_PAYLOAD=""
if [ -n "$PAYLOAD" ] && [ -n "$TEMPLATE" ]; then
    template_hv=$(${PYTHON:-python3} - "$TEMPLATE" <<'EOF'
import struct, sys
with open(sys.argv[1], 'rb') as f:
    f.seek(40)
    print(struct.unpack('<I', f.read(4))[0])
EOF
)
    if [ "$template_hv" -ge 4 ]; then
        EMBED_PAYLOAD="$PAYLOAD"
        payload_bytes=$(${PYTHON:-python3} -c 'import os,sys; print(os.path.getsize(sys.argv[1]))' "$PAYLOAD")
        EXTRA_CFLAGS="${EXTRA_CFLAGS:-} -DEMBEDDED_XNU_BYTES=$payload_bytes"
    fi
fi

# XNU_DIAG_KERNEL=<Mach-O next to the payload> adds the stage trace and the
# sentinel addresses derived from that exact kernel and payload. Never guess
# them: a stale address would write into unrelated DRAM.
if [ -n "${XNU_DIAG_KERNEL:-}" ]; then
    if [ -z "$PAYLOAD" ]; then
        echo "error: XNU_DIAG_KERNEL set but no PAYLOAD" >&2
        exit 1
    fi
    mkdir -p out
    ${PYTHON:-python3} ../tools/diag_syms.py "$XNU_DIAG_KERNEL" "$PAYLOAD" > out/diag_syms.h
    EXTRA_CFLAGS="${EXTRA_CFLAGS:-} -DXNU_DIAG -Iout"
fi

if command -v aarch64-linux-gnu-gcc >/dev/null 2>&1; then
	CC=aarch64-linux-gnu-gcc
	OBJCOPY=aarch64-linux-gnu-objcopy
	NM=aarch64-linux-gnu-nm
	READELF=aarch64-linux-gnu-readelf
	CFLAGS="${EXTRA_CFLAGS:-} -O2 -ffreestanding -nostdlib -fno-pic -mgeneral-regs-only -mstrict-align -fno-stack-protector -fno-builtin -Wall -Wextra"
	LDFLAGS="-Wl,--build-id=none -Wl,--no-warn-rwx-segments -Wl,-N"
else
	CC=${CC:-clang}
	OBJCOPY=${OBJCOPY:-llvm-objcopy}
	NM=${NM:-llvm-nm}
	READELF=${READELF:-llvm-readelf}
	CFLAGS="${EXTRA_CFLAGS:-} --target=aarch64-none-elf -O2 -ffreestanding -nostdlib -fno-pic -mgeneral-regs-only -mstrict-align -fno-stack-protector -fno-builtin -Wall -Wextra"
	LDFLAGS="-fuse-ld=lld -Wl,--build-id=none"
fi

mkdir -p out
OBJS=""
COBJS=""
for f in $SRCS; do
	$CC $CFLAGS -c "$f" -o "out/${f%.*}.o"
	OBJS="$OBJS out/${f%.*}.o"
	[ "$f" = start.S ] || COBJS="$COBJS out/${f%.*}.o"
done

# The image runs wherever the bootloader puts it with no relocation pass: only
# the header's image_size (start.o, linked at 0) may be an absolute address.
abs=$($READELF -r $COBJS | grep -c ABS64 || true)
[ "$abs" = 0 ] || { echo "error: $abs absolute relocations in C objects" >&2; exit 1; }

$CC $CFLAGS -static -T shim.ld $LDFLAGS $OBJS -o out/shim.elf
$OBJCOPY -O binary out/shim.elf out/Image
# The bootloader copies the file; pad to image_size so .bss/stacks exist as
# zeroed bytes.
end=$($NM out/shim.elf | awk '$3=="_end"{print $1}')
[ -n "$end" ] || { echo "error: _end not found" >&2; exit 1; }
size=$((0x$end))
truncate -s "$size" out/Image

if [ -n "$EMBED_PAYLOAD" ]; then
    # Measured matisse LK loads the Image at 0x40000000; DTB starts at
    # 0x47c80000. Do not let an embedded payload overwrite the live DTB.
    ${PYTHON:-python3} ../tools/embed_payload.py out/Image "$EMBED_PAYLOAD" --max-image-size 0x7c80000
fi

# Ramdisk: an xnu payload if given, else a tiny newc cpio (some bootloaders
# dislike a zero-size ramdisk).
if [ -n "$PAYLOAD" ]; then
	cp "$PAYLOAD" out/ramdisk.bin
else
	(cd out && rm -rf rd && mkdir rd && cd rd && find . | cpio -o -H newc --quiet | gzip -9 > ../ramdisk.bin)
fi

if [ -n "$TEMPLATE" ]; then
	# Only the legacy boot v2 path appends a payload to the ramdisk. Boot v4
	# keeps the stock ramdisk unchanged and uses the embedded kernel payload.
	RAMDISK_PAYLOAD="$PAYLOAD"
	[ -z "$EMBED_PAYLOAD" ] || RAMDISK_PAYLOAD=""
	${PYTHON:-python3} - "$TEMPLATE" out/ramdisk.bin "$RAMDISK_PAYLOAD" <<'EOF'
import struct, sys
tpl, dst, payload = sys.argv[1], sys.argv[2], sys.argv[3]
b = open(tpl, 'rb').read()
ks, rs = struct.unpack_from('<2I', b, 8)
hv, = struct.unpack_from('<I', b, 40)
page = 4096
off = page + (ks + page - 1) // page * page
rd = b[off:off + rs]
if payload:
    rd += open(payload, 'rb').read()
open(dst, 'wb').write(rd)
print(f'ramdisk: stock {rs} bytes + payload {len(rd) - rs}')
EOF
fi

# MediaTek LK inflates a gzip kernel (the stock boot.img is gzip too); Qualcomm
# ABL takes the raw Image. Follow the template's shape when there is one.
KERNEL=out/Image
if [ -n "$RAW" ]; then
	echo "kernel: raw Image (--raw)" >&2
elif [ -n "$TEMPLATE" ]; then
	KERNEL=$(${PYTHON:-python3} - "$TEMPLATE" out/Image out/Image.gz <<'EOF'
import gzip, struct, sys
tpl, src, dst = sys.argv[1], sys.argv[2], sys.argv[3]
b = open(tpl, 'rb').read()
ks, = struct.unpack_from('<I', b, 8)
hv, = struct.unpack_from('<I', b, 40)
k = b[4096:4096 + ks]
if hv >= 3 and k[:2] == b'\x1f\x8b':
    with gzip.GzipFile(dst, 'wb', 9, mtime=0) as g:
        g.write(open(src, 'rb').read())
    print(f'kernel: gzip (template kernel is gzip, {ks} bytes)', file=sys.stderr)
    print(dst)
else:
    print(src)
EOF
)
fi

ARGS="--kernel $KERNEL --ramdisk out/ramdisk.bin --out out/shim-boot.img"
[ -n "$TEMPLATE" ] && ARGS="$ARGS --template $TEMPLATE"
[ -n "$DTB" ] && ARGS="$ARGS --dtb $DTB"
[ -n "$HV" ] && ARGS="$ARGS --header-version $HV"
${PYTHON:-python3} ../tools/mkbootimg.py $ARGS

# Host render of the console layout.
gcc -O1 -Wall -o out/host_test console.c host_test.c 2>/dev/null && ./out/host_test || true
ls -l out/Image out/shim-boot.img
