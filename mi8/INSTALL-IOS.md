# Installing iOS 16 on the Mi 8 (milestone 2: iOS boots to the lock screen)

Status: the kernel boots on the Mi 8 and reads `userdata` (it rejected Android's ext4 as "not HFS+"). Next: put the iOS
root on `userdata`. **This erases Android's user data.** Bootloader, modem, persist and recovery are not touched.
Touch works (see below); the buttons have no Mi 8 driver yet.

## 0. What you need
- Ubuntu 22.04/24.04 (a VirtualBox/VMware VM is fine), 80 GB free, 8 GB RAM. WSL2 does not work (no HFS+ loop mount).
- Your fork of the repo with the Mi 8 overlay, and a successful **xnu** run (artifact `xnu-kernel`).
- The iPhone X (iPhone10,3) iOS 16.7.16 (20H392) IPSW from Apple, about 7 GB.

## 1. Back up first (Windows cmd, phone in TWRP: `fastboot boot twrp.img`)
```
for %p in (persist modemst1 modemst2 fsg fsc boot dtbo vbmeta) do adb exec-out "dd if=/dev/block/bootdevice/by-name/%p 2>/dev/null" > %p.img
for %d in (sda sdb sdc sdd sde sdf) do adb exec-out "dd if=/dev/block/%d bs=4096 count=6 2>/dev/null" > gpt_head_%d.bin
for %d in (sda sdb sdc sdd sde sdf) do adb exec-out "dd if=/dev/block/%d bs=4096 skip=$(( $(cat /sys/block/%d/size) / 8 - 6 )) count=6 2>/dev/null" > gpt_tail_%d.bin
```
Check `dir`: persist.img must be exactly 33554432 bytes and boot.img 67108864. Also keep a stock Mi 8 fastboot ROM so you can restore Android.

## 2. Linux tools
```
sudo apt install git python3 gcc-aarch64-linux-gnu binutils-aarch64-linux-gnu hfsprogs hfsplus android-sdk-libsparse-utils
```
Build `apfs-fuse` (github.com/sgan81/apfs-fuse, cmake) and install `ipsw` (github.com/blacktop/ipsw).
`git clone` your fork; put the kernel artifact in `xnu/out/` (so `xnu/out/kernel.development.sweet` exists).

## 3. Root image (from the repo README, section 2; the commands are the same for every phone)
```
tools/mkiosroot.sh OS.dmg SystemOS.dmg AppOS.dmg ios16-root.img 16G     # dmg names: see the IPSW's BuildManifest.plist
sudo fsck.hfsplus -fy ios16-root.img
sudo mkdir -p /mnt/iosroot && sudo mount -t hfsplus -o loop,force ios16-root.img /mnt/iosroot
sudo python3 tools/sweet-root-tweaks.py /mnt/iosroot
sudo umount /mnt/iosroot
img2simg ios16-root.img ios16-root.simg
```
## 4. The /product device-tree node (needed for the home screen)
```
python3 tools/remotezip.py IPSW_URL DeviceTree.d22ap.im4p research/ipsw-x/dt
ipsw img4 im4p extract research/ipsw-x/dt/Firmware/all_flash/DeviceTree.d22ap.im4p -o research/ipsw-x/d22ap.adt
```
Keep `research/` and the root image out of git and off GitHub (Apple's files).

## 4b. Touch firmware (needed for touch)
The touch chip only behaves with the right firmware (stock Android reloads it on every boot; the chip's built-in image reports
ghost touches). Put your working `st_fts_e1.ftb` (FW 0x45, config 0x19, 108968 bytes: it is one of the four images inside the ROM kernel,
`mi8-ftb-candidates.zip`, candidate 2) at `mi8/fw/st_fts_e1.ftb` **on the Linux machine only** (`.gitignore` keeps it out of git; do not
push it to a public repo). `make-boot.sh` embeds it; the shim burns it into the chip when iOS boots (about 40 s, with a progress
screen), then XNU's driver (`mi8/xnu/mi8_touch.c`, from patch 0099) polls the chip.

## 5. Boot image, flash, boot
```
bash mi8/make-boot.sh xnu/out/kernel.development.sweet           # -> mi8/out/mi8-xnu-gz.img
fastboot -S 512M flash userdata ios16-root.simg                  # ~7 min, do not unplug
fastboot boot mi8/out/mi8-xnu-gz.img
```
If fastboot hangs after the flash, power off and re-enter fastboot (Vol-down + Power). Expect minutes on one core
(`cpus=1`); try `cpus=4` first with the mi8-image workflow (SMP check, needs no root image).

## 6. Back to Android
TWRP -> Wipe -> Format Data (or `fastboot -w` with a stock ROM), then boot. Restore the backups only if something
device-specific (modem/persist) got damaged.
