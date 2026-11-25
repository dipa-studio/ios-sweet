# V89 physical USB result

The verified v89 boot was flashed and rebooted successfully. Its UART records
TESTMUX release from CTRL2=0x40404040 to0, release1/changed1, followed by connect,
setup and ECM configuration. The Mac detects the1209:0001 gadget and exact host
MAC02:00:5e:77:ee:01 on en1. After assigning192.168.7.1/24 only to that interface,
ping to192.168.7.2 succeeds5/5 with zero loss,2.118..10.564ms. Actual new kernel
WHYRED IO and exec log bytes arrive at the Mac on UDP5140. This verifies the
requested Ethernet and live kernel-console transport on this boot.

The earlier no-enumeration state is resolved in this test after releasing the
observed override. Reconnect, sustained throughput and long-term idle behavior
have not been tested. Container/daemon fixes remain separate pending runtime
evidence; SSH is not included. UART capture remains manual. Raw logs stay private.

# V88/V89: release the observed UTMI non-drive test override

The same USB change is retained in the combined v89 candidate. New v87 RAMFS
evidence requires a separate root-created DSC correction before the next combined
test; v88 alone does not contain it. An early capture also supplies event0x00000101
decoded as bus reset, confirming one event-ring delivery. Successful enumeration
and data transfers remain unconfirmed.

V87 boot was flashed and rebooted successfully. Its manual UART snapshots10..22
and27..32 show UTMI_CTRL1=0x35353535, UTMI_CTRL2=0x40404040, powered PHY, low-byte
PLL lock and controller RUN. The event counter stays1 in those samples and the
sampled bus-error addresses are zero. No exact-MAC Ethernet interface appeared
during a90-second read-only Mac observation. One processed event does not prove
a successful USB connection; its value was not supplied.

The pinned MiCode QUSB driver defines CTRL2 bit6 as TEST_MUX and uses CTRL1's
TERM_SELECT/FS/non-drive signature0x15 to override controller outputs during its
charger high-Z path. V87's CTRL1 low five bits match that signature; bit6 is set
in CTRL2. The authenticated stock DT binds this DWC3 to the major-rev1 PHY at
0xc012000 and requests UTMI. The sampled interface-select bit is retained.

Patch0167 clears only TEST_MUX after RUN_STOP is cleared and DEVCTRLHLT is
acknowledged, before allocating or installing gadget DMA. CTRL1, interface-select
and all other low-byte CTRL2 bits remain unchanged. Byte data is used for the
major-rev1 register because word reads can replicate its byte. The helper checks
the full low-byte result. On failure it restores only the owned mux bit and stops
before DMA/thread creation, recording restoration success or failure. An active
override with a different low-five-bit CTRL1 signature is rejected. Already
automatic PHY state is left untouched; USB mode1 remains read-only. There are no
additional power, PLL, tune, reset, PMIC, TCSR or SMMU writes.

Local UBSan passes1299 checks using28 actual driver/ring functions and4 actual
board helpers. Cases cover the observed replicated bytes, preservation of all128
possible combinations of other CTRL2 bits, refused writes, unexpected readback,
restoration, unfamiliar overrides, controller halt ordering and mode1. Two ARM64
units, zeroLSE/PAN object audits and exact late-patch replay pass. Removing release
or clobbering interface-select compiles but fails functional assertions. The
combined v89 workflow41346137446 passed all27 steps, including USB1299 with
ASan+UBSan and4 exact board-helper bodies. Authenticated packaging retains the
root DSC correction and idle/service changes. Physical enumeration is now
verified as recorded above.

--- Earlier RUN-without-enumeration diagnostics ---

# V86/V87 read-only snapshots

User v85 UART reaches RUN after EP0 STARTTRANSFER returns command/result0x6 and
resource0. A later ue0 rx0/tx0 heartbeat proves the event thread continues to run.
Cable reconnect produces no new USB lines; the Mac observes no gadget or exact-MAC
Ethernet interface. No successful enumeration, data transfer or UDP logging is
established. Service exit causes and the earlier idle panic remain separate
open observations; no new service output has been supplied.

Patch0165 adds read-only bounded register snapshots within explicit USB mode2.
Stage0 precedes controller takeover; stage1 follows endpoint/VBUS configuration
before event-thread creation; stage2 is the event thread's later sampling. Samples
are read sequentially, not atomically. Runtime sampling uses a one-second deadline,
with output only on change. DSTS frame/microframe bits alone do not trigger a
record. After32 records the helper stops reading as well as printing. Each record
has four lines and a shared ID. No new boot argument is required.

The snapshots include DWC3 control/status/speed, event-ring address/size/raw count,
endpoint commands, PHY power/PLL/test/UTMI control/line state, QSCRATCH mux/VBUS,
NoC bus configuration/error addresses, reference timing and hardware parameters.
Bus-error addresses can be historical; nonzero values alone do not prove a new
DMA fault. The sampler does not acknowledge events, issue commands, synchronize
DMA buffers or change clocks, resets, PMIC, PLL tuning, test controls or charger
state. It runs before thread creation and then only on the event thread, avoiding
concurrent mutation of its fixed previous-sample/output counters.

The pinned MiCode PHY driver has a high-impedance charger-detection path that
sets UTMI_CTRL1/2 to override controller outputs. PLL lock and controller RUN
alone do not exclude such an override. UTMI1/UTMI2/LINE must be observed before
claiming that as this phone's cause or changing those registers. Register sources
are the pinned [QUSB driver](https://github.com/MiCode/Xiaomi_Kernel_OpenSource/blob/efbbb9cce47475c49f28d227b2a52eca6f0d02a7/drivers/usb/phy/phy-msm-qusb.c)
and [DWC3 definitions](https://github.com/MiCode/Xiaomi_Kernel_OpenSource/blob/efbbb9cce47475c49f28d227b2a52eca6f0d02a7/drivers/usb/dwc3/core.h).

Local UBSan passes637 checks executing28 actual driver/ring functions. New cases
cover raw-field output, no event ACK or hardware writes, line/link/bus-error
changes, frame-only suppression, stable-state suppression, saturation with no
further MMIO reads, mode-off behavior and one-second scheduling. Both ARM64
compiles, noLSE/PAN object audits and exact patch replay pass. Physical register
values and the missing connection cause still require the next device run.

--- Earlier implementation and hardware history ---

# whyred USB Ethernet and console candidate

Patch 0159 ports the existing polled DWC3 CDC-ECM gadget to whyred. The first
candidate includes Ethernet and a best-effort kernel console stream. It does
not install SSH or require changes to the installed System v70 image.

Patch 0160 adds the v82 powered-shutdown PHY resume. V82 full CI passed all 26
steps and 601 USB ASan+UBSan checks. After an authorized boot flash, the user's
UART confirmed PLL lock, a readable DWC3 ID and ue0 IP setup. Startup then stopped
at the strict missing-transfer-resource check, before USB RUN.

Patch 0162 is the next EP0 follow-up. The pinned Linux
[EP0 code](https://github.com/MiCode/Xiaomi_Kernel_OpenSource/blob/efbbb9cce47475c49f28d227b2a52eca6f0d02a7/drivers/usb/dwc3/ep0.c)
tracks BUSY independently and does not reject a successful control start solely
for index zero. The driver now separates activity from index, retains HWO checks,
reads the resource result separately with bounded polling, and still rejects
missing data-endpoint resources. Raw initial control command/results are logged
within a fixed budget. An active unindexed control transfer cannot be safely
retired by this implementation during a mid-control reset, so that path stops
the controller with DMA retained. Full v84 CI/hardware validation is pending.

The driver is off by default. `whyred-usb=1` takes a read-only handoff snapshot;
`whyred-usb=2` attempts the gadget. Startup runs once after `net_init_run`, before
root discovery, independently of UFS initialization. It never starts the UFS
driver or persistent log writer. eMMC/APFS read-only policy is retained.

## Hardware basis and limits

The active board device tree and Xiaomi's
[whyred-o-oss source](https://github.com/MiCode/Xiaomi_Kernel_OpenSource/tree/efbbb9cce47475c49f28d227b2a52eca6f0d02a7)
agree on the controller and legacy PHY. Clock offsets come from
[gcc-sdm660.c](https://github.com/MiCode/Xiaomi_Kernel_OpenSource/blob/efbbb9cce47475c49f28d227b2a52eca6f0d02a7/drivers/clk/qcom/gcc-sdm660.c),
PHY power/lock from
[phy-msm-qusb.c](https://github.com/MiCode/Xiaomi_Kernel_OpenSource/blob/efbbb9cce47475c49f28d227b2a52eca6f0d02a7/drivers/usb/phy/phy-msm-qusb.c),
and the USB2 PIPE mux/VBUS fields from
[dwc3-msm.c](https://github.com/MiCode/Xiaomi_Kernel_OpenSource/blob/efbbb9cce47475c49f28d227b2a52eca6f0d02a7/drivers/usb/dwc3/dwc3-msm.c).

| Component | Whyred value |
| --- | --- |
| DWC3 | `0x0a800000` |
| QSCRATCH | `0x0a8f8800` |
| QUSB2 major 1 | `0x0c012000`, size `0x180` |
| PHY power / PLL status | `0xb4` / `0x38`, lock bit 5 |
| GCC USB30 GDSCR / reset | `0xf004` / `0xf000` from GCC `0x00100000` |
| Master / sleep / UTMI clocks | `0xf008` / `0xf00c` / `0xf010` |
| Config-NoC / aggre2 / AHB2PHY | `0x5018` / `0xf03c` / `0x6a004` |
| QUSB2 / AHB2PHY resets | `0x12000` / `0x6a000` from GCC |

This initial port takes over the bootloader's powered, calibrated PHY. It
requires GDSC on and resets deasserted. Patch 0159 required an already locked,
unclamped PHY. Patch 0160 can release the exact legacy shutdown low-byte state
`0x23` to `0x22`, as used by `qusb_phy_shutdown` and `qusb_phy_init` in the pinned
[MiCode PHY driver](https://github.com/MiCode/Xiaomi_Kernel_OpenSource/blob/efbbb9cce47475c49f28d227b2a52eca6f0d02a7/drivers/usb/phy/phy-msm-qusb.c).
It requires the existing reference gate on, retains tuning, waits 150 us and
polls at most another 1000 us for power readback plus PLL lock. A failed preflight
restores the PHY shutdown state before undoing introduced branch votes. It does
not attempt other PHY states or analog power-up. Cold PHY power-up,
PMIC supplies and clock-source/PLL programming are not implemented. Mode 2 can
vote the six confirmed branch enable bits with bounded polls; preflight failure
undoes only votes introduced by that attempt. It does not read gated DWC3/PHY
blocks or copy another SoC's SMMU SID/configuration. DMA below 4 GiB assumes the
bootloader's direct USB DMA path; physical DMA visibility still needs testing.

`WHYRED USB: handoff=N` reports 0 ready, 2 map failure, 3 power domain off,
4 reset asserted, 5 clock unavailable, 6 PHY not ready, 7 invalid/held-reset
core, or 8 attempted PHY wake failed. The snapshot includes clocks, PHY values
before/after, wake attempt/polls/rollback and QUSB/AHB reset states. The driver
explicitly says when the controller was never sampled. A failed handoff
stops before gadget startup; setting the boot flag alone does not prove a link.

The gadget halts the bootloader controller before installing its own DMA area.
The whole zeroed DMA area is cache-cleaned before installing the event ring;
TRBs and buffers use separate 128-byte cache-maintenance granules. Transfer
ownership, command timeouts/status, resource indices, RX lengths and event-ring
counts are checked. Failure stops the controller; DMA memory remains pinned
for the boot, including failed startup, rather than being freed while a device
could still access it. There is no automatic retry/reinitialization loop.

USB2 full/high-speed configuration descriptors and packet sizes are selected
from the negotiated speed. Data endpoints run only on data-interface alternate
setting 1. Reset/disconnect/alternate-setting changes retire transfers and free
queued packets. Host requests outside the implemented standard/ECM subset stall;
this is an experimental gadget, not a complete USB class implementation.

## Host connection

The phone interface is `ue0`, `192.168.7.2/24`. The shared development host MAC is
`02:00:5e:77:ee:01`; the phone uses the same prefix ending in `02`. These are test
identities, not handset serials. VID/PID remain the inherited `1209:0001` test ID.

After booting an explicitly enabled candidate on macOS:

```sh
python3 tools/whyred-usbnet.py --connect --log whyred-usb.log
```

Without `--connect` the helper only lists matching interfaces. The connection
command waits up to 30 seconds for one exact MAC match, assigns only that
interface `192.168.7.1/24` with `ifconfig` (sudo may be needed), then receives
UDP port 5140 bound to the USB address. Ambiguous matches or an already-used
USB subnet stop the helper. It changes no DNS/default-route settings. Received
data must come from `192.168.7.2`; the optional local log is created mode 0600.
Ctrl-C stops the receiver. Keep raw logs private.

The memory console ring is replayed from up to 64 KiB before the log thread's
start, subject to its 4 MiB retention. At most eight 1400-byte chunks are sent
per 100 ms interval, with nonblocking socket calls. Failed/short sends keep the
cursor for retry. UDP, queue drops, ring overwrite and concurrent console writes
can still lose bytes; this is not a lossless or panic-safe transport. An earlier
failure before the gadget starts still needs another capture path.

## Validation status

V84 local UBSan passes 614 USB checks, including CDC setup with zero EP0 indices,
delayed result indices, result errors/reactivation and safe rejection of active
DMA reuse or missing bulk resources. Both negative controls fail. ARM64 compile,
exact late-patch replay and zero LSE/PAN object audits pass. V83 ownership
diagnostics are retained; full v84 CI and physical enumeration remain pending.

v82 local UBSan passes 601 checks including the PHY shutdown case, delayed and
failed lock, rejected writes, reference/reset guards and ordered rollback.
The wake-disabled negative control fails. ARM64 compiles, exact incremental patch
replay and zero LSE/PAN object audits pass. V82 hardware wake passed as above.

Local checks execute 27 actual kernel functions plus the board helper, with
modeled MMIO, mbufs, sockets and thread waits. They cover default-off/read-only
behavior, every clock and rollback, PHY/core rejection, cache-granule separation,
descriptors/control stages, FS/HS, data/filter gating, reset/reconnect, queue
cleanup, stale DMA ownership, timeouts, bounded event counts and UDP cursor retry.
The macOS interface parser has separate selection/ambiguity checks. Local UBSan
passes 566 checks. The initial DMA-clean check rejects the previous missing-clean
version before any event ring or transfer is installed. Both changed ARM64 compilation units pass with zero LSE/PAN
instructions. Exact patch replay matches all three reviewed files.
Full [CI 41319898167](https://github.com/timosid/ios-sweetwhyred/actions/runs/41319898167)
for source `7ccdf8dda98cdc2ead91f171c51607ddcae29890` passed all 26 steps, including
566 USB ASan+UBSan checks and all retained checks. Both ZIPs matched GitHub
digests; exact built sources, linked cache instructions, LSE/PAN, reserved memory
layout and trusted loader/ADT/stock-DTB checks passed. Boot v81 is 22,315,008 bytes;
SHA256 `8b1300ed5f5c9524bc5b61722479a5f363b8df4391b8b71b06a10130f1706b41`.
The user authorized a boot-partition flash after temporary `fastboot boot`
returned OKAY but left this handset in Fastboot. Sending/writing boot v81 and
reboot returned OKAY; System v70 was preserved. Fastboot disappeared afterward,
but no CDC network interface or UDP bytes have been observed. UART/screen evidence
is needed to locate the failure. No physical Ethernet enumeration, ping, console
delivery, cache coherence, SMMU behavior or host-driver compatibility is established yet.
