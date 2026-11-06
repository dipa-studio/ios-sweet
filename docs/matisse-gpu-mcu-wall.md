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
verified back to `2931647a...86b1`. The boot itself did not come back to Recovery
on its own - XNU reached `mount-phase-1` and then failed into fastboot - so the
restore ran through the `restore-only` path.

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

## 7. 2373: the region limit is dead, and the shape is a touched 512-byte block

2372 built the whole-section map and started the MCU with the vendor
`ENABLE|AUTO` (3). `MCU_STATUS` stayed 0 for the entire budget: the MCU was never
enabled, so no probe ran and the image proved nothing. That is worth keeping as a
hardware fact of its own - on this SoC `ENABLE|AUTO` does **not** start the core,
while AUTO alone (2) reaches `MCU_STATUS == 1` through the same code path.

2373 repeated the identical map with 2. Image SHA256
`7ef7c11f26d10fb28dd89d95ed694968cc4d32d925e7196070f6f9b85091de8e`, 26,714,112 B,
journal `complete-restored-Recovery`, `boot_a` verified back to `2931647a...86b1`.
Only the start word and the kernel build id differ from 2372.

- `input_va = 0x01000000`: the marker is stored into shared+0x08 before the first
  probe, so the loop provably started even though it never finished.
- `groups = 10`. The field is `rd(shared+0x10)`, seeded 8 by the firmware template
  and incremented once per probe, so **two** probes returned: 0x01000000 and
  0x01000100. The probe at **0x01000200** stopped the core.

The "readable prefix ending at 0x1a00" reading predicted all 256 blocks would
return, or at worst that everything below 0x1a00 would. 0x01000200 returned
nothing, and it is 0x1800 below that supposed limit, so that reading is dead.
The "only near the executing code" reading is dead too: 0x01000000 is 0x18ec away
from the loop at 0x010018ec.

What survives both runs is one rule: **an aligned 512-byte block becomes readable
as data once the core has touched it.** Exactly two blocks qualify in these
boots - `0x01000000..0x010001ff`, whose first word the reset sequence reads, and
`0x01001800..0x010019ff`, the block the replacement loop executes from. All
sixteen of 2371's returning probes (0x01001900..0x010019f0) sit inside the second
block; 0x01001a00 is the first address of the next one, which is why it hung. The
"256-byte window" was the tail of a 512-byte block whose head is the code the core
was running.

2366 is still the one datum this does not explain: its loop sat at 0x010019ee
with its literal at 0x010019f8, both inside the executing block, and it turned
once. Either the rule has a second condition, or 2366's stall was a different
event. Do not write an attribute on the strength of the rule until 2374 has run.

## 8. 2374: does fetch prime the block, or are these two blocks special

Same loop, same marker, one new idea. Instead of reading a fresh block, the probe
branches into 0x01000200, executes a few instructions there so the core has to
fetch it, and only then data-reads that block:

- `groups = 8` - even the branch/fetch into a fresh block hangs. Then the wall is
  translation on any first touch, the reset block was primed by hardware, and no
  driver-side attribute fixes it: the firmware has to live in a region that was
  primed, or in one that is mapped as data from the start.
- `groups = 9` - the fetch landed, the data read of a block the core just fetched
  still hung. Then fetch does not prime the data path and the two readable blocks
  are special for another reason.
- `groups = 10` - fetch primes the block for data reads. The rule the driver has
  to live with is then "the MCU can only data-read what it has already fetched",
  and the fix is to stop making the EB data-read unfetched code at all.

The marker is written before the branch, so all three outcomes are distinguishable
from one boot.

## 9. 2374: shareability is not the wall

The vendor loader derives page-table attributes from the section flags in the
firmware image, not from a single guess for the whole image. `convert_mem_flags()`
in `mali_kbase_csf_firmware.c` turns `CSF_FIRMWARE_ENTRY_READ/WRITE/EXECUTE` into
`KBASE_REG_GPU_RD/WR/NX` and the cache-mode field into a `MEMATTR` index;
`get_mmu_flags()` in `mali_kbase_mmu_mode_aarch64.c` emits `ENTRY_SHARE_BITS` only
when `KBASE_REG_SHARE_BOTH` is set, and only a section carrying
`CSF_FIRMWARE_ENTRY_SHARED` sets it.

Parsing the pinned container gives ten sections, of which exactly one is shared:

```
R-- cached shared=0   0x00000000..0x00001000
R-X cached shared=0   0x01000000..0x01010000   <- the code section
RW- cached shared=0   0x02000000..0x02040000   <- stack and heap
R-- cached shared=0   0x02800000..0x02840000
RW- cached shared=0   0x03000000..0x03040000
RW- cached-coherent shared=1  0x04000000..0x04094000
```

This port mapped every cached section `SH=11` (inner and outer shareable) while
configuring the page-table walker non-shareable - the two disagreed about which
domain owns the transaction. Fixing it to the vendor rule is a one-line change,
and 2374 ran the 2373 map with only that change:

- image `e4fab071...`, 26,714,112 B, `boot_a` verified back to `2931647a...86b1`
- `input_va = 0x01000000` (the loop started), `groups = 10` - **identical to 2373**

Same two probes, same hang at 0x01000200. Shareability is not the cause, and the
PTE attribute line of investigation is now closed rather than merely doubted.

## 10. What the negative result reframes

Line 2374 up with 2358 and the pattern is no longer about code:

- instruction fetch to 0x010018ec reaches DRAM and runs 406 million times a second
  (2363), so the DRAM path and the MMU walk work;
- a data read at 0x01000200 never returns (2373, 2374);
- a data write into the stack at 0x0203f000 never lands (2358).

Every data access that has to leave the GPU hangs; fetch does not. The addresses
that do read are exactly the lines the core has already pulled in - the reset
vector at 0x01000000 and the block it executes at 0x01001800. That is the shape of
a broken **data path**, not of a wrong code mapping, and it explains why four
attribute experiments in a row changed nothing.

Two candidates, both visible in the OEM tree: the GMPU that
`gpu_protected_memory_allocator` in `mt6983.dts` describes (`gmpu_table_size =
0x400000`, `protected_reserve_size = 0x1000000`, table address handed to the EB
through GPR 6 at `0x13c5fd1c`), which by design filters data accesses and not
instruction fetches; and the `MEMATTR` index the data path uses.

## 11. 2375: probe one address per section

Same loop, five probes, one per section, each incrementing the counter:

```
0x01001900  code, known good (control)
0x02000000  stack
0x02800000  read-only data
0x03000000  heap
0x04000000  shared
```

`groups - 8` says how many returned, so the first hang localises itself. If
0x02000000 already hangs, the wall is the data path and the code-section mapping
was never the subject; if all five return, the wall is specific to the code region
and `MEMATTR` is the remaining difference. Either answer removes a whole line of
work, which is what 2371-2374 could not do.

## 12. 2375: data reads work, and the hang is not a permission fault

Five probes, one address per section, in the order code (control), stack,
read-only data, heap, shared, each followed by its own counter increment. Image
`54d732cd...`, `boot_a` verified back to `2931647a...86b1`. `groups = 11`:

| probe | section | flags | result |
|---|---|---|---|
| 0x01001900 | code | R-X cached | returned |
| 0x02000000 | stack | RW- cached | returned, never touched before |
| 0x02800000 | read-only data | R-- cached | returned, never touched before |
| 0x03000000 | heap | RW- **protected** | stopped the core |
| 0x04000000 | shared | RW- coherent | never reached |

Two things fall out of this at once.

**The data path is fine.** The stack and read-only pages had never been fetched or
read by this core and both returned, so the "every data access that leaves the GPU
hangs" reading of 2374 is dead. Only the RX page hangs.

**The heap probe proves the difference between a fault and a hang.** 2375 ended
with `error = -54` (FAULT), `mmu_raw = 1`, `as_fault = 0x7cd002c2`. 2373 and 2374
ended with `error = -53` (TIMEOUT) and `mmu_raw = 0`. The 0x03000000 sections are
`CSF_FIRMWARE_ENTRY_PROTECTED` and `sweet_csf_memory.c` skips protected sections,
so that address is unmapped and the MMU faults immediately. An unmapped read
faults; the RX read does not fault, it never completes. Two mechanisms that the
earlier reports could not tell apart, now separable by `error` and `mmu_raw`.

**Which narrows the wall to one property.** Between 0x01000200 (hangs) and
0x02000000 (returns) the leaves differ only as the section flags dictate: the code
page is read-only (`AP[2]=1`) and executable (`XN=0`); the stack page is read-write
and `XN`. Since a permission violation faults, and the RX read does not fault, the
difference is not permission. It is that a read of an RX page only completes while
its line is already resident - exactly what 2371 measured, and 2373/2374 could not
change by touching shareability.

## 13. 2376: stop probing, boot the firmware

Every trial from 2363 to 2375 replaced the reset vector, so the probe reads code as
data - an access pattern the vendor firmware never performs. Whether this GPU
supports it is a property of the hardware, not of our driver, and nothing in the
OEM tree asks it.

The driver now has the explicit halt/start state machine, the section-ABI share
bits and the measured-good `MCU_CONTROL` value. What has not been asked since 2358
removed the stack is the only question that matters: **does the unpatched firmware
boot?** 2376 therefore carries no trace probe and no entry patch - it runs the
normal power-on path and reads `firmware_ready`, `version` and the interface
handshake. A firmware that reports ready makes the RX read property a curiosity; a
firmware that does not boot with every other variable now measured is worth far
more than a sixth attribute guess.
