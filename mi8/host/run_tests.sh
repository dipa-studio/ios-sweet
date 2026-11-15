#!/bin/bash
# Host tests for shim/mi8.c (no hardware): (1) probe against the fake SoC + FTS slave model, (2) same with the firmware
# burn enabled on a synthetic .ftb, plus the iOS-boot bring-up path in both builds, and the burn's I2C write stream compared against ref_burn.py (an independent
# re-implementation of ST's flash_burn). Usage: run_tests.sh <shim dir> <out dir>
set -euo pipefail
shim="$1"; out="$2"
here="$(cd "$(dirname "$0")" && pwd)"
mkdir -p "$out"
CF="-O1 -Wall -Wextra -DMI8_HOST -DTARGET_MI8 -I$shim -I$here"
gcc $CF -o "$out/test_mi8" "$here/test_mi8.c" "$shim/mi8.c"
"$out/test_mi8"
BRINGUP=1 "$out/test_mi8"
# the XNU-side touch driver (mi8/xnu/mi8_touch.c) against a simulated FTS chip on a simulated bit-banged bus
gcc -O1 -Wall -Wextra -DMI8_TOUCH_HOST -I"$here" -o "$out/test_xnu_touch" "$here/test_xnu_touch.c"
"$out/test_xnu_touch"
python3 "$here/gen_ftb.py" "$out/test.ftb"
cp "$out/test.ftb" "$out/test.ftb.bak"
gcc $CF -DMI8_FTS_FW -I"$out" -o "$out/test_mi8_burn" "$here/test_mi8.c" "$shim/mi8.c" "$here/fwblob.S"
BURN_LOG="$out/burn_actual.txt" "$out/test_mi8_burn"
BRINGUP=1 "$out/test_mi8_burn"
python3 "$here/ref_burn.py" "$out/test.ftb" > "$out/burn_expected.txt"
python3 - "$out/burn_actual.txt" "$out/burn_expected.txt" <<'PY'
import sys
act = [l.strip() for l in open(sys.argv[1]) if l.strip()]
exp = [l.strip() for l in open(sys.argv[2]) if l.strip()]
n = len(exp)
if not any(act[i:i + n] == exp for i in range(len(act) - n + 1)):
    sys.exit("burn write stream differs from the reference")
print("burn stream matches the reference (%d transactions)" % n)
PY
