
#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

CC=aarch64-linux-gnu-gcc
OBJCOPY=aarch64-linux-gnu-objcopy
NM=aarch64-linux-gnu-nm

mkdir -p out

FLAGS=(
    -O2
    -ffreestanding
    -fno-builtin
    -fno-stack-protector
    -fno-pic
    -fno-pie
    -nostdlib
    -mgeneral-regs-only
    -mstrict-align
    -Wall
    -Wextra
)

echo "[1/4] Compiling..."

"$CC" "${FLAGS[@]}" -c start.S -o out/start.o
"$CC" "${FLAGS[@]}" -c main.c -o out/main.o
"$CC" "${FLAGS[@]}" -c ../console.c -o out/console.o

echo "[2/4] Linking..."

"$CC" "${FLAGS[@]}" \
    -static \
    -no-pie \
    -Wl,--build-id=none \
    -Wl,-T,start.ld \
    out/start.o out/main.o out/console.o \
    -o out/shim.elf

echo "[3/4] Generating Image..."

"$OBJCOPY" -O binary out/shim.elf out/Image

END_HEX=$("$NM" -n out/shim.elf |
    awk '$3 == "_end" { print $1; exit }')

if [[ -z "$END_HEX" ]]; then
    echo "Missing _end symbol" >&2
    exit 1
fi

IMAGE_SIZE=$((16#$END_HEX))
truncate -s "$IMAGE_SIZE" out/Image

echo "[4/4] Checking..."

aarch64-linux-gnu-readelf -h out/shim.elf
aarch64-linux-gnu-nm -n out/shim.elf | grep -E '(_head|_start|_stack_top|_end)$'

echo
echo "Image: $PWD/out/Image"
echo "Size:  $IMAGE_SIZE bytes"
echo
xxd -l 64 out/Image
