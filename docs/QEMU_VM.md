# Running the iOS root in QEMU (VM mode)

This is the VirtualBox-shaped path: the iOS root filesystem is a raw HFS+
image on the host, and QEMU attaches it to the guest as a virtio-blk disk.
The runner loads the kernel separately and attaches the image as a writable
disk. Use a copy of the root image for guest writes.

Status: patch `0082-sweet-qemu-vm.patch` adds the disk, input and display
devices. This is desktop QEMU first. It does **not** produce an Android APK
yet.

## Windows host setup

The [official QEMU download page](https://www.qemu.org/download/#windows)
links to Stefan Weil's Windows builds. Use the 64-bit package containing
`qemu-system-aarch64.exe`. An extracted package can live in the ignored
`research/qemu/` directory. In PowerShell, add it to the current session:

```powershell
$env:PATH = "$PWD/research/qemu;" + $env:PATH
python tools/qemu-sweet.py --check-env
```

The runner uses a loopback TCP QMP monitor on Windows and Unix sockets on
Linux/macOS. Windows paths are converted to forward slashes for QEMU.
The disk is still a raw HFS+ image; downloading QEMU does not supply the
iOS root. Prepare and check a copy on Linux/macOS as described below,
then transfer that copy to the Windows host. Use one-line commands in
PowerShell instead of the shell `\` continuations in the examples below.
Check available display backends with `qemu-system-aarch64 -display help`.
On 2026-10-24, QEMU 11.1.0 on Windows ran the 0082 kernel with a low-memory
QEMU ADT, one Cortex-A76 CPU and a 128 MiB TCG cache. A 30-second run
captured CPU/framebuffer/IOKit initialization. A 60-second run with
`--input --display none` reached root selection and panicked with
`IOFindBSDRoot: SWEET virtio-blk root vblk0 unavailable: 6`, because no disk
was attached. QMP register and framebuffer capture worked; `serial.txt`
was empty. These runs verify initial kernel execution, not an iOS boot
or working input/display interaction. Those smoke tests had no root disk.

A subsequent Windows test with a 16 GiB root built from the iPhone X
20H392 IPSW mounted `/dev/vblk0` read-write, ran Apple launchd and the boot
tasks, and displayed the Apple boot logo through backboardd/ramfb. The
first 30-minute TCG run did not reach the lock screen. A boot logo is not
evidence of a completed GUI boot; keep the framebuffer and kernel log.

For building the image in WSL, check `grep hfsplus /proc/filesystems`
before running `mkiosroot.sh`. The stock WSL 6.18.54.1 kernel lacks HFS+;
this test used the matching Microsoft kernel source with
`CONFIG_HFSPLUS_FS=y`. Follow Microsoft's
[custom WSL kernel instructions](https://github.com/microsoft/WSL2-Linux-Kernel)
if your kernel lacks the driver. apfs-fuse reads the IPSW components;
hfsprogs and the HFS+ driver create and populate the destination image.
The repository keeps shell scripts in LF format so WSL can execute a
Windows checkout. No phone flashing is needed for this VM workflow.

## What the virtual machine uses

| Part | QEMU device / guest name |
| --- | --- |
| Machine | `qemu-system-aarch64 -M virt,gic-version=3 -cpu cortex-a76` |
| Root disk | `virtio-blk-device` -> `/dev/vblk0` (block) and `/dev/rvblk0` (char) |
| Display | `ramfb` -> the same panel memory at `0x9c000000` |
| Touch | `virtio-tablet-device` -> SweetHID finger 0 |
| Buttons | `virtio-keyboard-device` -> L/H/Up/Down and the real power/volume/home keys |
| Console | `serial.txt` (and `--live-serial` on stdout) |

The kernel still drives the iPhone display path itself. `ramfb` only makes
that panel memory visible in a QEMU window, so the iOS screen is the real
screen iOS draws, not a second implementation.

## 1. Get the kernel

Every push that touches `xnu/patches/` builds the kernel in GitHub Actions:

```sh
gh run list --workflow=xnu.yml --limit 1
mkdir -p vm/ci
gh run download RUN_ID -n xnu-kernel -D vm/ci
ls vm/ci                      # kernel.development.sweet
```

The workflow artifact is named `xnu-kernel`; the file is
`kernel.development.sweet` for the default `DEVELOPMENT` / `SWEET` build.
The artifact must include patch `0082`; an older kernel boots without the
virtio-blk/input and ramfb drivers, so check for the `virtio-blk:` lines in
the boot log.

Build the QEMU device tree and payload (`--qemu` is required: the GIC
addresses and timebase are QEMU's, not the phone's):

```sh
python3 tools/mkadt.py vm/qemu.adt --qemu --highmem
python3 tools/mkpayload.py vm/ci/kernel.development.sweet vm/qemu.adt vm/payload.bin \
  --cmdline 'debug=0xc serial=3 cpus=1 keepsyms=1 -noprogress \
rd=vblk0 rootrw=1 virtio_blk=1 virtio_input=1 ramfb=1 \
unentitled_ios_sim_launch=1 ignition_level=1 \
wdt_test=no_user_checkin wdt=-1 launchd_unsecure_cache=1 \
sweetfb_hz=30'
```

The boot args that matter here:

| Boot arg | Why |
| --- | --- |
| `rd=vblk0` | Root on the virtio disk instead of `userdata` (UFS) |
| `rootrw=1` | Mount the HFS+ root read-write |
| `virtio_blk=1` | Enable the virtio-blk driver (the bus address is QEMU's) |
| `virtio_input=1` | Enable the tablet/keyboard driver |
| `ramfb=1` | Publish the panel through QEMU's fw_cfg ramfb device |
| `cpus=1` | The QEMU ADT has one CPU (QEMU MPIDRs differ from sweet) |

Add `-enable_kprintf_spam` if you want every kernel print. Add
`sweetfb_noconsole=1` once the screen works, to stop the console text
covering the GUI (panics are still drawn). Leave it out for the first boot so
the window shows how far the kernel got.

## 2. Prepare the disk (a copy)

Use the **raw** HFS+ image, not the Android `.simg` sparse image:

```sh
ROOT=/path/to/ios16-root-20H392-v15.img
mkdir -p vm
cp --reflink=auto "$ROOT" vm/root.img     # reflink where the filesystem allows it
sudo fsck.hfsplus -fy vm/root.img         # hfsprogs; macOS: fsck_hfs -fy
```

The image is about 16 GB and proprietary. Keep it outside git, keep the
original, and let QEMU write only to the copy. Do not run QEMU against the
image while the phone is using it.

`fsck` is not optional after an unclean phone shutdown: HFS+ will replay its
journal during the QEMU mount, which writes to the image.

## 3. Run with a window

```sh
python3 tools/qemu-sweet.py vm/payload.bin vm/run \
  --disk vm/root.img --input --display gtk,zoom-to-fit=on \
  --wait --live-serial
```

* `--display gtk,zoom-to-fit=on` opens the QEMU window and adds
  `-device ramfb`; use `sdl` or `cocoa` if your QEMU has no GTK.
* `--input` adds the virtio tablet and keyboard. The mouse with the left
  button held is a finger; dragging moves it. Keys: `L` is the power button,
  `H` is Home, `Up`/`Down` are the volume buttons.
* `--wake-every 300 --wake-start 300` sends a blank-center tablet tap every
  five host minutes, beginning five minutes after QEMU starts. This is useful
  when iOS dims or sleeps the display during a long boot; each sent tap is
  recorded in `wake-events.log`. It requires `--input` and does not unlock the
  device or launch an app.
* On Windows, `--sample-every 300 --kernel xnu/out-0086-trace/kernel.development.sweet`
  captures the guest framebuffer, registers, and kernel msgbuf every five
  host minutes into `snapNNN/`. Capture status is appended to
  `snapshot-capture.log`. It pauses the guest briefly while copying memory.
* `--wait` keeps the VM running until QEMU exits. Without it the default
  `--secs 20` stops QEMU after twenty seconds.
* `--live-serial` prints the kernel console in the terminal; the same text
  is in `vm/run/serial.txt`.
* `--smp N` selects 1-8 QEMU vCPUs and sets the matching XNU `cpus=N` boot
  argument. Above one CPU, the runner enables multi-threaded TCG. For `N > 1`,
  build the ADT with `mkadt.py ... --qemu --qemu-cpus N` and use a kernel with
  patch 0087; otherwise QEMU and XNU will see different CPU topologies.
* Close the window, or press Ctrl+C in the terminal, to stop. The copy of
  the root keeps whatever the guest wrote.

The first boot under TCG is slow: by default it uses one emulated CPU and
there is no KVM for an ARM guest on an x86 host. Expect tens of minutes, not
the phone's four to five. After building a matching SMP kernel and ADT,
`--smp 4` is an experimental option to give LaunchServices and other first-
boot jobs more CPU time.
On Apple Silicon, `--accel hvf --cpu host` is worth trying, but the ADT and
the kernel's CPU setup were made for TCG/QEMU's Cortex-A76 and are not
validated with HVF.

## 4. Headless run and screenshot

For a CI-style run, or a machine without a desktop:

```sh
python3 tools/qemu-sweet.py vm/payload.bin vm/run \
  --disk vm/root.img --input --secs 3600
```

At the end `vm/run/fb.png` is the exact 1080x2400 panel image, and
`serial.txt`, `regs.txt` and `qemu.log` are beside it. With `--wait` there is
no final screenshot; the window is the output.

## 5. What a healthy boot prints

Early lines to look for:

```text
virtio-blk: /dev/vblk0 in slot 0, 16384 MB, read-write
virtio-input: device in slot 1
virtio-input: device in slot 2
ramfb: 1080x2400 at 0x9c000000, selector N
BSD root: vblk0, major N, minor 0
```

Later, the normal iOS bring-up appears: HFS+ mount, launchd, the shared
cache, backboardd and SpringBoard. The QEMU window should show the Apple
logo/progress first, then the lock screen.

## 6. Troubleshooting

| Log line | Fix |
| --- | --- |
| `virtio-blk: slot N is a legacy transport` | The runner adds `-global virtio-mmio.force-legacy=false`; if invoking QEMU by hand, add it |
| `virtio-blk: no block device on the bus` | `--disk` was not passed, or QEMU has no `virtio-blk-device` |
| `ramfb: QEMU has no ramfb device` | Use `--display` (adds `-device ramfb`) or add `-device ramfb` |
| `ramfb: no QEMU fw_cfg at ...` | The machine is not QEMU's `virt` at the expected fw_cfg address |
| `IOFindBSDRoot: SWEET virtio-blk root vblk0 unavailable` | The disk driver did not find the device; check the two lines above |
| Panic or read-only root | Is the copy writable? Is it the raw `.img`, not `.simg`? Did `fsck` run? |
| Black window | Check for `ramfb: 1080x2400`, then inspect the framebuffer and SpringBoard/LaunchServices logs; a black screen can occur after the kernel and display driver have started |

The QEMU window is a 1080x2400 surface; on a smaller host display use
`gtk,zoom-to-fit=on` and resize the window.

## 7. Limits and next steps

* QEMU TCG is the current speed limit. The runner defaults to one CPU; SMP
  requires kernel patch 0087 plus an ADT generated with matching `--qemu-cpus`.
  Its stability and performance on Windows have not yet been measured.
* There is no GPU: iOS draws with the CPU copy path already used on the
  phone.
* The desktop VM is the bring-up vehicle. An Android APK would need a QEMU
  build packaged into the app and an external root image the user supplies;
  that is a later phase. The image must stay outside the APK.
* The input and ramfb drivers are behind boot args (`virtio_input=1`,
  `ramfb=1`) and do nothing on the phone.
