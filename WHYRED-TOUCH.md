# whyred touch bring-up

Installed boot98/System95 has a registered digitizer HID service, but no confirmed
physical touch input. The sweet hardware driver targets SM7150 GENI/GT9896/FTS;
its initialization is reached through sweet UFS startup, not whyred eMMC startup.
It must not be enabled on whyred with its original MMIO, GPIO or power settings.

Xiaomi's whyred-o-oss board DTS includes synaptics-dsx-i2c.dtsi, which declares
both Synaptics DSX at0x20 and Novatek at0x62 on i2c_1, with interrupt GPIO67 and
Novatek reset GPIO66. These are alternative supported configurations, not proof
of the controller fitted to this particular handset. Novatek runtime firmware
reads use address0x01, distinct from the DT hardware address. Its report payload
is65 bytes after the register prefix, ten6-byte contact records and metadata;
Xiaomi sets the coordinate bounds1080x2160 and ten fingers.

Primary references:
- https://github.com/MiCode/Xiaomi_Kernel_OpenSource/blob/whyred-o-oss/arch/arm/boot/dts/qcom/sdm636-mtp_whyred.dts
- https://github.com/MiCode/Xiaomi_Kernel_OpenSource/blob/whyred-o-oss/arch/arm/boot/dts/qcom/synaptics-dsx-i2c.dtsi
- https://github.com/MiCode/Xiaomi_Kernel_OpenSource/blob/whyred-o-oss/drivers/input/touchscreen/nvt_touch/nt36xxx.c
- https://github.com/MiCode/Xiaomi_Kernel_OpenSource/blob/whyred-o-oss/drivers/input/touchscreen/nvt_touch/nt36xxx.h

## Offline candidate0177

The existing HID geometry still used sweet's2400-pixel height and centered its
coordinates in the logical canvas. Whyred's framebuffer instead scales the full
1125x2436 canvas into1080x2160. The patch makes whyred normalized touch coordinates
cover that same full panel, adjusts the lower edge classification and native
height, and preserves the last position on release. Legacy sweet math remains.

A transport adapter `whyred_hid_novatek_frame` accepts a complete Novatek payload
only for whyred. It validates the entire packet before sending any HID events;
truncation, duplicate active IDs, invalid coordinates and recovery/erased patterns
leave HID state intact. Missing contacts in a valid packet release previous ones.
A caller must serialize reports and first confirm that its controller is Novatek.
The adapter does not select a controller or read registers by itself.

Local2356 checks pass with UBSan and strict compiler warnings: panel midpoint,
endpoints, monotonic mapping, ten fingers/IDs, down/move/up states, truncated
packets, malformed bounds, duplicate IDs, recovery and empty release frames.
The patch replays exactly against the authenticated99 build source. Kernel CI
includes the new check. No boot image containing0177 is packaged or flashed yet.

## Remaining physical path

The actual fitted controller, powered state and QUP I2C handoff must be identified
before implementing/enabling its bus driver. Synaptics requires its own RMI
function discovery and report decoder; it must never be fed to the Novatek parser.
The candidate currently has NO whyred I2C polling/IRQ input producer, no power/reset
writes and no firmware upload. Physical taps therefore remain unimplemented.
When the phone returns, obtain its actual touch-controller identity from a stock
Android/recovery input inventory or a bounded, board-correct bus identification
probe. Then implement the matching transport/decoder and verify tap, drag,
multitouch, release and coordinate edges on hardware. Do not call touch working
from HID registration, packet fixtures or synthetic input alone.

## Full kernel build result

CI41817694238/job126532556668 from source6ebc9fe6ca8228e1649f08159f86f13207b2558c
passed all steps, including kernel compilation and digitizer checks. The earlier
41816371836 attempts failed before compilation because BearSSL upstream returned
HTTP502. Dependency staging now retries finitely and accepts a mirror only at
the same pinned commit. Physical touch transport remains the open task above.
