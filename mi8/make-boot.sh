#!/bin/bash
# Build the Mi 8 XNU boot image locally (Linux). Needs gcc-aarch64-linux-gnu + python3 and, for the home screen,
# research/ipsw-x/d22ap.adt (the iPhone X /product node, see mi8/INSTALL-IOS.md).
#   bash mi8/make-boot.sh xnu/out/kernel.development.sweet ["boot-args"]
# -> mi8/out/mi8-xnu-gz.img (try first) and mi8/out/mi8-xnu-ucomp.img. RAM boot only: fastboot boot <img>.
set -euo pipefail
cd "$(dirname "$0")/.."
kernel="${1:?usage: make-boot.sh KERNEL [boot-args]}"
# Default = first iOS boot: root on userdata (read/write), one core, touch on (shim brings the chip up, XNU polls it),
# buttons off (no Mi 8 driver yet), cpus=4 is worth trying once it boots (the 4 efficiency cores work),
# kernel text kept on screen so a hang or panic is visible.
cmdline="${2:-debug=0xc serial=3 cpus=1 keepsyms=1 -enable_kprintf_spam -noprogress rd=ufsroot0 unentitled_ios_sim_launch=1 ignition_level=1 wdt_test=no_user_checkin ufsrw=1 rootrw=1 launchd_unsecure_cache=1 wdt=-1 sweetkeys=0 sweetfb_noconsole=0 sweetfb_hz=30}"
mkdir -p shim/out
python3 tools/mkadt.py shim/out/mi8.adt --highmem --board mi8
python3 tools/mkpayload.py "$kernel" shim/out/mi8.adt shim/out/payload.bin --cmdline "$cmdline"
MI8_PAYLOAD=shim/out/payload.bin bash mi8/build-mi8.sh
