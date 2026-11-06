# Matisse GPU: the MCU wall is a data read of unfetched code

Status: 2026-11-06, trials 2321-2371. Everything below is device evidence unless
marked as inference. Source of truth for the instrument specs is the
`TRACE_PROBE` table in `tools/matisse-shim-gpu-image.py`; this document explains
what those probes found.

## 1. What is already proven on hardware

| Capability | Trial | Evidence |
| --- | --- | --- |
| GPUEB INIT / POWER_ON, single power reference | 2321 | `INIT 0`, `POWER_ON 1`, `POWER_OFF 0` |
| MFG power domain up | 2321 | SPM `0x1c001f3c/40` `0x3 -> 0x7` |
| GPU identity and reset | 2321 | `GPU_ID 0xa8620004`, `GPU_STATUS 0x100`, `AS_PRESENT 0xff`, reset RAWSTAT `0x100` |
| GPU clock and DVFS | 2338 | `freq 610000 kHz`, `oppidx 2/5`, `power_count 1`, commit accepted and observed |
| MCU executes code we write | 2340/2341 | shared words change from the reset-entry stub |
| MCU core free-runs | 2363 | 406,670,326 loop turns inside the 1 s poll window |
| GPU translation reaches the arena | 2332/2337 | code word `d00cf8df` at PA `0x40080000`; entry PTE and backing word match |

Not proven: CSF firmware readiness (`GLB_VERSION != 0` + fresh global-interface
IRQ), GPU MMU operation, shader execution, Vulkan/Metal.

## 2. The measurement had to be fixed twice

The 2351-2357 ladder concluded "the MCU stops at 0x01001914" but two layers of
instrument error sat behind it:

1. **The stack.** The stub pushed to PSP `0x0203f000` and popped `{r0,r1,r2,pc}`.
   If PSP is not writable RAM, the pop loads garbage into `pc` and the core dies
   at the first entry no matter what the firmware does. 2358 removed the stack
   (return address kept in `lr`, only `r3`/`r12` clobbered, S-less 32-bit forms)
   and the ladder immediately advanced to rung 2 with count 2.
2. **The dead word.** 2339-2341 showed the only unwritable word in the shared
   page is `+0xffc`; every checkpoint that used it was blind.

Both are now excluded from the instrument.

## 3. The three results that localise the wall

**2363 - the core runs.** The reset vector was replaced with
`ldr r3,=shared+0x10 / ldr r2,[r3] / adds r2,#1 / str r2,[r3] / b .-8` and nothing
else. Count: 406,670,326 in one second. Clock, fetch path, shared-page writes and
the core itself are all healthy.

**2367/2368 - distance matters, not the code.** The same loop byte-for-byte turned
406 million times with its literal 12 bytes away and 0 times with the literal 520
bytes away. 2369 then built the counter pointer from `movs/lsls/adds` and read the
far word once into a register nothing consumes: still 0. The read is the fault,
not a corrupted pointer.

**2370 - the edge sits inside a single 4 KiB page.** A sweep of
`ldr r2,[addr]; adds; str` over 0x01001900, 0x01001a00, ... advanced while the
probe address was inside the loop's own fetched bytes and hung on the first
address outside them. Same page, same leaf descriptor, same attributes.

## 4. What that implies

Reads stop 0x100 above the base the loop starts on, inside a page that the leaf
covers completely. In a normal stage-1 mapping that is impossible: once a 4 KiB
leaf is valid, every byte in it is equally readable. So the leaf built for the
code section in `xnu/gpu/mali_csf_memory.c` must be routing data accesses
somewhere the MCU cannot complete them - or the limit is not the mapping at all
and the last section of this document is the honest answer.

Relevant facts about the current leaves (`mali_csf_memory.c:116-125`):

- descriptor type page `|3`, `AF` set, `nG` set
- `AP[2]=1` (bit 6) on every section, i.e. read-only
- `AttrIndx` from the section flags: cached sections get `0x304` (AttrIndx 1, inner
  shareable), everything else `0x200` (AttrIndx 0, outer shareable)
- `PXN`/`UXN` from flags bits 1/2
- bits 59..62 carry the Mali memory-group tag 6

None of that obviously forbids a data read. The open questions, in the order they
should be answered:

1. Does `AttrIndx 1` resolve to a MEMATTR entry the MCU can use for data? The
   driver programs `AS_MEMATTR` `0x2408 = 0x4c4c884c / 0x240c = 0x4c4c4c4c`
   (index 0 byte `4c`, index 5 byte `4c`, index 1 byte `88`). If index 1 is a
   cacheable attribute and the GPU L2 is not serving that region for the MCU's
   data port, a read could stall instead of faulting.
2. Should the code section be mapped with the shared/unindexed attribute
   (index 0) instead of index 1? This is a one-variable change and is exactly what
   the `vendor_cached_memattr` knob already isolates for one byte.
3. Does the memory-group tag (bits 59..62 = 6) apply to data accesses on this
   implementation, or only to instruction fetches?

## 5. 2371 ran, and the answer was not the one either hypothesis predicted

2371 repeated the 2370 sweep with a 0x10 step between 0x01001900 and 0x01001a00.
Image SHA256 `f4d107102129a8a6e6ca6f3adb2cb9f0593b9215ee02e36f066cf1d5c6ba76af`,
26,714,112 B; the journal records `complete-restored-Recovery` and `boot_a`
verified back to `2931647a...86b1`.

`groups = 24`, so 16 probes returned: 0x01001900, 0x01001910, ... 0x010019f0 all
read fine and the read at **0x01001a00** stopped the core. The rest of the report
is the familiar failure (`csf stage 4`, `error -53`, `version 0`, `mcu_status 1`).

That rules out both candidates the build was designed to separate:

- not "only fetched bytes", which would have stopped after the loop's own last
  byte, i.e. one or two probes;
- not the 4 KiB page, because 0x010019f0 and 0x01001a00 are in the same page with
  the same leaf and the same backing.

The window is 0x01001900..0x010019ff: 256 bytes, ending on a 0x100 boundary, in
the middle of a mapped page. The reading that fits the earlier trials is a
512-byte aligned fetch window at 0x01001800..0x010019ff: 2363's literal at
0x010018f8 and 2365's at 0x010019fc are inside it (2365 turned exactly once, at
the last four bytes of the window), while 2368's and 2369's at 0x01001af8 are
outside and died with no count at all. 2366 is the one trial it does not explain:
its loop sat at 0x010019ee with the literal at 0x010019f8, both inside the window,
and it still turned only once.

So the honest state is: the boundary is measured and reproducible, but the shape
is not settled. Before touching any attribute, the next probe should run the same
loop from a different base - 0x01001a00 and 0x01002000 - which separates "a window
that follows the executing code" from "an absolute limit at 0x01001a00".

## 6. Driver work in the same round

`xnu/gpu/mali_csf_boot.c` started the MCU with a bare `wr(MCU_CONTROL, 2)`
(AUTO only) and no explicit halt step. Vendor `kbase_csf_firmware_enable_mcu`
writes `ENABLE|AUTO = 3`. The driver now runs an explicit state machine
(halt -> poll `MCU_STATUS == 0` -> start with the configured value -> poll and
classify), with the written/read-back pair recorded in `platform_reserved` so the
696-byte report ABI is unchanged. The value is a config knob so a trial changes
only that one number.
