# Matisse GPU: the MCU wall is a data read of unfetched code

Status: 2026-11-06, trials 2321-2390. Everything below is device evidence unless
marked as inference. Source of truth for the instrument specs is the
`TRACE_PROBE` table in `tools/matisse-shim-gpu-image.py`; this document explains
what those probes found.

**Read `docs/matisse-gpu-csf-status.md` first.** It is the consolidated summary:
what is proven, which earlier conclusions were retracted, what is still open, and
how to resume.  This document is the chronological evidence behind it, and several
of its sections contain readings that a later trial disproved - the retractions are
recorded where they happened rather than edited away.

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

## 14. 2376: the unpatched firmware runs, faults nothing, and never says ready

No trace probe, no entry patch. The embedded container is byte identical to the
vendor file (`de22d2fc...`), 0x010018ec still holds `72b62648`, and the manifest
carries neither `trace_probe` nor `fault_vector_probe`. Image `ab6c5fc0...`,
`boot_a` verified back to `2931647a...86b1`.

| field | value | meaning |
|---|---|---|
| `mcu_status` | 1 | the MCU is enabled - halt/start and `MCU_CONTROL=2` work |
| `mmu_raw` | 0 | no GPU MMU fault |
| `as_fault` | 0 | none either |
| `version` | 0 | the firmware never wrote the output page |
| `features` | 0 | same |
| `firmware_ready` | 0 | never signalled |
| `error` | -53 | timeout |

`version` and `features` are `rd(shared)` and `rd(shared+4)`, the words the
firmware publishes when it is up. Zero says it never got that far. So the firmware
starts, runs, does not fault, and stops somewhere in its own initialisation.

## 15. What that does to the previous thirteen trials

All of 2363-2375 ran a probe loop we had written into the reset vector. The
"unfetched RX line" property those trials measured is real, and 2375 showed it is
not a permission fault - but it belongs to an access pattern the firmware never
performs. It was never why the port is stuck, and no further page-table work on it
will boot anything.

What the port actually has, measured rather than assumed, is: power and clocks
(2338), EB handshake and MCU start (`MCU_CONTROL=2` reaches `MCU_STATUS=1`), a page
table the MMU walks without faulting, and a firmware that runs and then goes quiet.

## 16. 2377: put a trap on the firmware's own path

The reset vector must stay untouched, so the instrument has to sit on an
instruction the firmware executes later. Pick a word inside the init path, replace
it with a marker store and a park, and leave the entry vector and the section table
alone. The marker's value is the instruction address, so the report says exactly
where the firmware was.

Walking that trap forward a few words at a time converts "it does not reach ready"
into a PC, which is the first thing this port has needed since 2358 and the first
thing the probe loop could never provide.

## 17. 2377: the page takes writes

Two pages in the RW section, one pattern, DSB after each store, read back and
restored. The counter steps after each stage so it names the stage that stopped:

```
A  0x02000000  write, dsb, read back
B  0x0203f000  read, write, dsb, read back
```

Image `c63f4c12...`, `boot_a` verified back to `2931647a...86b1`, `groups = 11` -
the value reserved for "both pages held a write". 9 would have meant B stalled on
its read, 10 on its store, 24/26 would have meant a page returned the wrong value.

So **2358's conclusion was an inference, not a measurement**, and it was wrong.
2358 ran a stub that pushed to a PSP stack, saw the ladder die, and reasoned that a
stack in a hole would explain it. Removing the stack made the ladder advance, which
confirmed the reasoning as a story but never tested a store. The store lands.

## 18. What actually stops the firmware - and it is the wall we already measured

Disassembling the reset handler at 0x010018ec and following its literal loads:

| instruction | literal | literal block | same block as the code? |
|---|---|---|---|
| 0x010018ee .. 0x01001964 | 0x01001988 .. 0x010019ac | 0x01001800 | yes |
| **0x010019dc** | **0x01001bc4** | **0x01001a00** | **no** |
| **0x010019ee** | **0x01001bc8** | **0x01001a00** | **no** |
| **0x010019f2** | **0x01001bcc** | **0x01001a00** | **no** |

The first ten literal loads are inside the 512-byte block the core is executing
from, which is why execution gets that far. The three in the cache helper load from
**0x01001a00** - the block 2370, 2371 and 2373 each measured as stopping the core.

That is 2376, exactly: the firmware runs, reaches 0x010019dc, issues
`ldr r0, [pc, #0x1e4]`, and hangs on a data read of an RX page whose line is not
resident. A store or load that never completes raises no fault, so the report shows
`mcu_status = 1`, `mmu_raw = 0` and nothing else.

It also re-reads 2359-2362. That ladder kept dying at rung 2, 0x010019e2, inside
this same cache helper; the experiments there nop'd ICIALLU and the CCR store and
blamed the CCR read, because the ladder could not see a stall one instruction
earlier. The stall was always this literal load.

## 19. 2378: the one leaf field left

The measured facts now line up without a gap:

- reads of RW pages complete (2375), writes to RW pages complete (2377);
- reads of RX pages complete only while the line is resident (2371, 2373, 2374);
- the firmware's stop address is a read of an RX page whose line is not resident.

Between the code leaf and the stack leaf the only two differences are `AP[2] = 1`
(read-only) and `XN = 0` (executable). 2378 boots the unpatched container with
`AP[2]` cleared on the sections the firmware declares read-only - one variable, no
probe, `version` / `features` / `firmware_ready` as the answer.

- reaches ready -> the read-only attribute was the wall, and the driver change is
  the fix;
- still stops at the same place -> `XN` or the cache mode is next, and the search is
  cheap because 0x010019dc is already the address.

## 20. 2378: read-only was not it, and no leaf field is left

Same container, byte for byte, no probe, no entry patch. The only change is that
the sections the firmware declares read-only are mapped writable:

```
code leaf  before 0x0000000090009cc7   AP[2]=1
           after  0x0000000090009c47   AP[2]=0
stack leaf        0x0060000090019c47   (unchanged)
```

The low twelve bits are now **identical** for the code page and the stack page. The
trial still returns `mcu_status = 1`, `mmu_raw = 0`, `as_fault = 0`, `version = 0`,
`features = 0`, `firmware_ready = 0`, `error = -53` - the 2376 result field for
field.

So the descriptor is not the difference. AttrIndx, share bits, AP, XN, AF and nG are
now the same on a page whose cold data read returns (the stack) and a page whose
cold data read hangs (the code). Every attribute explanation is spent.

Two smaller things from the same run:

- 2373, which hung on its own data read, cleaned up with `disable_status = 1`,
  `reset_completed = 0`, `reset_raw = 0x200`; 2376 and 2378 end with exactly those.
  Probe builds that reach their own `b .` park end with `reset_completed = 1`. The
  firmware boot ends in the same wedge as a hung data read.
- 2356 had already nop'd `79 48 01 60` at 0x010019dc - the literal load and the
  device write - and the ladder still did not advance. That was inconclusive, not
  negative: the ladder's own return path was under suspicion, and it could not
  distinguish a stall at that instruction from a stall in its own epilogue.

## 21. 2379: does fetch prime a block

No attribute can be blamed any more, so the next question is about the access
pattern itself. The probe writes its marker, steps the counter, then branches into
block 0x01000200 - a block none of these boots has ever fetched - executes two
instructions there, returns, and only then data-reads 0x01000210 in that same
block.

```
9   the branch into a fresh block hung        -> even the fetch path fails there
10  the fetch landed, the data read still hung -> residency is not the rule
11  the data read completed                    -> fetch primes the block
```

Answer 11 would explain the firmware's death exactly: at 0x010019dc it reads a
literal 0x1e4 bytes ahead of the instruction pointer, which lands in the next
512-byte block, and that block has not been fetched. Answer 10 would say the model
built from 2371-2375 is wrong and the search has to start over from the raw
addresses rather than from a residency theory.

## 22. 2379 ran: the counter stopped at 9

The trial ran 2026-11-06 14:18 against image `9dc4467d...df6c` (26,714,112 B,
partition `aead007c...f415` read back before boot). Journal
`complete-restored-Recovery`; the phone did not return to a fresh Recovery, it
fell to fastboot after 84.56 s and the raw prefix restore brought it back with
`restored_sha256 = 2931647a...86b1`, i.e. the partition is byte-identical to the
baseline again.

```
groups / fetch_prime_counter   9
fetch_prime_outcome            fetch-call-incomplete
stage / error                  4 / -53
mcu_status, mmu_raw, as_fault  1, 0, 0
version / firmware_ready       0 / 0
memattr                         0x4c4c884c / 0x4c4c4c4c
reset_raw / cleanup_error      0x200 / -53
```

So the branch into 0x01000200 never returned. That is narrower than "the data
read hung" and wider than "fetch is broken":

- the counter proves the stub stored 9, so the reset vector, the marker store and
  the counter update all executed;
- it does not prove the fetch faulted, because a lost return and a hanging fetch
  are indistinguishable from a counter that stops;
- it does not prove fetch *primes* a block, which was the question 2379 was built
  to answer - that would have been 11.

Combined with 2376 the useful part is: an RX block that has never been touched is
not reachable, by either path, on this mapping. 2366 (the loop that turned once
with its literal 12 bytes inside the executing block) still does not fit any
512-byte model, so the block size is not settled.

## 23. 2380: the two leaf facts that were never varied

2378 made the code leaf's low twelve bits identical to the stack leaf's, which
removed AP, XN, share bits, AF and nG from the search. Two differences to the
vendor driver were still unvaried, because nobody had read them out of the
blob:

1. **AttrIndx numbering.** `mali_csf_memory.c` put a cached section on index 1.
   The vendor `convert_mem_flags()` puts `CSF_FIRMWARE_CACHE_MODE_CACHED` on
   `AS_MEMATTR_INDEX_IMPL_DEF_CACHE_POLICY`, which is **0**.
2. **Share bits on the shared section.** This port set SH=3 (`0x300`) on the
   leaf whose section declares `CSF_FIRMWARE_ENTRY_SHARED`. The vendor sets
   share bits only for `KBASE_REG_SHARE_BOTH`, and on a `COHERENCY_NONE` SoC
   `convert_mem_flags()` downgrades CACHED_COHERENT to UNCACHED_COHERENT and
   then to CACHE_MODE_NONE before that branch is reached - so the shared leaf
   carries **no** share bits and selects index 5.

Both are now proven from the pinned `mali_kbase_mt6983.ko`, not inferred:
`mmu_update` (text 0x4708C) and `kbase_mmu_get_as_setup` (text 0x47998) each
build `0x00084C8D888D8F88` with a `mov/movk` chain;
`kbase_mmu_hw_configure` stores that field to GPU+0x2408. Bytes are
`[0]=88 [1]=8f [2]=8d [3]=88 [4]=8d [5]=4c [6]=08`, so index 0 is the cached
byte and index 5 the non-cacheable one.

What that means for reading the result: the *selected bytes* stay 0x88 for a
cached section and 0x4c for the rest, so 2380 is really a test of the share
bits, the index numbering and MEMATTR[0]. If it returns the 2376/2378 signature
unchanged, the honest conclusion is "shareability and index numbering are not
the wall", not "cacheability is not the wall".

Readiness rules for this build, in the order the decoder applies them:

| result | meaning | next |
|---|---|---|
| stage 7, error 0, version != 0, `mmu_raw & 0xffff == 0` | the firmware reached its interface | 2381: global input page + doorbell |
| stage 4, error -53, `mcu_status 1`, version 0 | same as 2376/2378 | 2382: move the code section's PA, keep VA and attributes |
| error -54, or `mmu_raw & 0xffff`, or `as_fault` | the vendor pairing faults translation | revert the leaf encoding first |
| stage 8/9/10, or `cleanup_error != 0` | transaction incomplete | inconclusive, do not stack a variable |
| `memattr` pair not `0x888d8f88`/`0x00084c8d` | not this image | discard the report |

## 24. 2380 ran: the vendor MemAttr pairing maps, boots, and changes nothing

Corrected image `0f21ee93...e77bc`, 26,714,112 B, partition
`78a91de6...a9511` written and read back, kernel build mark `0x2380` decoded
from a fresh marks block, `boot_a` restored to `2931647a...86b1`. The first two
attempts of this build produced no evidence at all - they embedded
`xnu/out/local/kernel.development.sweet`, a stale Oct 25 file, instead of
`build/xnu.obj/DEVELOPMENT_ARM64_SWEET/kernel.development.sweet`; their notes
are kept under `shim2380-vendormemattr-trials/`.

The image did what it was built to do: `memattr_lo = 0x888d8f88`,
`memattr_hi = 0x00084c8d` read back from the GPU, so the vendor table really was
programmed and the leaf encoding really was index 0 / index 5 with no SH bits.

```
stage / error / cleanup_error   4 / -53 / -53
mcu_status, mmu_raw, as_fault   1, 0, 0
version, features               0, 0
firmware_ready                  0
groups, group_stride            8, 0xa0   (template seeds; no probe ran)
memattr_lo / memattr_hi         0x888d8f88 / 0x00084c8d
transcfg_lo                     0x42000006
reset_raw                       0x200
```

That is the 2376/2378 signature field for field, with a different leaf encoding.
So the two facts that had never been varied - the AttrIndx numbering and the
share bits on the shared section - are **not** the wall. The cold code-page
access pattern remains the suspect, and the attribute line is now closed from
both ends: 2378 removed the descriptor bits, 2380 removed the index/share
difference.

Next single variable: what the hang follows. 2373/2379 measured a 512-byte
granularity inside the code section while the stack and read-only sections read
cold without trouble; nothing so far separates "this physical range" from "this
virtual range". 2382 moves the code section's pages inside the arena - same VA,
same attributes, same descriptors, different PA - and reads the same addresses
through a second mapping of the same bytes.

## 25. 2382: move the code section's PA and change nothing else

2380 closed the attribute line: the vendor AttrIndx numbering and the shared
leaf's SH bits were the last two facts that had never been varied, and varying
them produced the 2376/2378 report field for field. What remains is the shape of
the hang itself. 2373/2379 localised it to 512-byte granularity *inside the code
section*, while the stack and the read-only section read cold without trouble.
Nothing so far has separated "these physical pages" from "this virtual range",
because every build moved both together or neither.

2382 moves one of them:

```
VA                 0x01000000..0x01010000   unchanged
leaf encoding      index1 cached / index0 other, SH=3 on shared   unchanged
descriptor bits    AF, AP[2], XN, nG, memory group 6              unchanged
container          byte-identical to 2379 (sha 367eb386)           unchanged
RO leaves          writable (--ro-as-rw)                           unchanged
MCU_CONTROL        2                                               unchanged
section PA         0x40080000 -> 0x401a4000                        MOVED
```

The mechanism is a second pass in `sweet_csf_memory_plan()` behind
`SWEET_CSF_RELOCATE_CODE` (default 0): every section gets the offset it always
had, then the one section that is both at VA 0x01000000 and executable is
re-appended at the offset the layout ends at, and its old slot is left as
padding. The arena grows by exactly that section's size, 65,536 B, and stays
inside the 2 MiB BSS (1,298,432 B used).

Two build-time refusals keep the claim honest. `relocation_evidence()` in the
builder compiles the same container twice and raises unless the section count is
the same, every other section's `{va,bytes,flags,arena_offset,data_start,
data_bytes}` is identical, and the code section landed at or after the old plan's
end; that proof is stored in the manifest as `csf_relocated_code`. The unit test
`test_relocated_code_moves_only_that_section` walks the built tables and asserts
that the code leaf differs only in bits 12..47 and that no other leaf changed at
all.

Why it is a probe build and not a clean boot: the clean-boot signature is a
timeout, and a timeout cannot say *where* the MCU stopped. 2382 therefore reuses
2379's container patch byte for byte, so `groups` is comparable with 2379's 9.
That is the whole design - one number moved, one number read.

The honest limit: `groups=9` on this build means the call still does not return,
and a lost return is still indistinguishable from an MCU fault that entered the
vendor handler, because the vendor vectors are deliberately untouched and an
MCU-side fault does not set `AS_FAULT`. If 2382 reads 9, the next instrument must
be the fault vector on this path, not another mapping change.

## 26. 2382 ran: the code section moved 1.2 MB and stopped at the same counter

Trial 2026-11-06 20:57. Image `2a85005b...51ad`, partition `47dc4e1d...8b57`
written and read back, kernel mark `0x2382` decoded from a fresh block, `boot_a`
restored to `2931647a...86b1`. The phone went to fastboot at 83.56 s; the run
produced 153 marks, so for the first time in three attempts the shim really
reached `shim_gpu_publish`.

The build did what it was built to do, and the report proves it in band:

```
kernel_build            0x2382
firmware_probe_pa       0x401a4000     (was 0x40080000 in 2379)
transtab_lo             0x40077000     (the arena did not move)
relocation_observed     true
groups                 9              (2379: 9)
stage / error          4 / -53
mcu_status, mmu_raw, as_fault   1, 0, 0
version, features      0, 0
memattr                0x4c4c884c / 0x4c4c4c4c   (2379's pair, on purpose)
```

So the fresh-block call still does not return when the section it calls into is
1,196,032 bytes further into the same arena, with the same VA, the same leaf
bits, the same descriptor, the same container bytes and the same start word. The
conclusion is narrow and it is the one the build was designed to produce:

**the hang does not follow the physical pages this port can move it to.** It is
not "the MCU cannot reach 0x40080000..0x40090000": that range was never the
problem, because leaving it changed nothing.

What this does not say: that PA placement can never matter anywhere. The move
stayed inside one 2 MiB carve-out of the shim's BSS. A hang caused by something
specific to that 2 MiB region, by the GMPU window over it, or by a fetch path
that ignores the GPU MMU entirely is still consistent with this result.

The ambiguity that is left is no longer about memory attributes: a counter of 9
means "the call did not come back", and that covers both a fetch that never
completes and a fault that entered the vendor handler at 0x010019b1 - the handler
parks, and an MCU-side fault does not set `AS_FAULT` (which reads 0). Four builds
(2376, 2378, 2380, 2382) now share that signature while varying descriptors,
attributes and PA. The next instrument has to distinguish those two mechanisms
instead of moving memory again.

## 27. 2383: ask the fault entry whether the fetch faulted or never finished

2382 closed every memory-side explanation and left exactly one question: when
the call into 0x01000200 does not return, did the MCU **fault** or did the fetch
simply never complete? A counter of 9 cannot tell, because the vendor handler at
0x010019b1 parks silently and an MCU-side fault never sets `AS_FAULT`.

2383 changes one thing on top of 2382: the 40 bytes at 0x010019b0, the address
the vendor vector table actually branches to (`0x010019b1` with the Thumb bit).
The stub is `tools/matisse-csf-fault-entry.S`, assembled and compared against the
pinned bytes by a unit test:

```
mov  r3, lr            ; EXC_RETURN
tst  r3, #4            ; bit2 = which stack the frame is on
ite  eq
mrseq r0, msp
mrsne r0, psp
ldr  r1, [r0, #0x18]   ; stacked PC
movs r2, #1
lsls r2, r2, #26       ; 0x04000000
str  r1, [r2, #12]     ; shared+12  -> reported as output_va
ldr  r1, =0xE000ED28   ; SCB->CFSR
ldr  r0, [r1]
str  r0, [r2, #20]     ; shared+20  -> reported as group_stride
movs r1, #20
str  r1, [r2, #16]     ; shared+16  -> reported as groups
1: b 1b
```

`20` is chosen so it cannot collide with the probe's 9/10/11, and the two words
it repurposes (`output_va`, `group_stride`) are only read, never validated, on
the timeout path - the interface gate that would care about them sits behind a
successful IRQ that this build cannot produce.

Everything else is 2382: the same relocated code section, the same 2379
container patch at 0x01000200 and 0x010018ec, the same writable RO leaves, the
same `MCU_CONTROL=2`. The unit test `test_2383_changes_only_the_fault_entry_on
_top_of_2382` diffs the two embedded containers and allows changes only inside
those 40 bytes; the built containers differ at exactly 0x2844..0x286b.

Reading it:

| counter | meaning | consequence |
|---|---|---|
| 20, CFSR != 0 | a fault was taken; `output_va` is the faulting instruction and CFSR names the class (IACCVIOL/IBUSERR/PRECISERR) | the access is *refused*, not starved: go at the permission/attribute the walker enforces for that access |
| 20, CFSR == 0 | a fault was taken but escalated to a hard fault | HFSR was not captured; a 2384 must record 0xE000ED2C before any mechanism claim |
| 9 | the handler never ran | no fault: the cold fetch genuinely never completes, so the wall is the MCU-side fetch/ready path, not translation |
| 10 / 11 | the call returned | the fetch completes at this target after all, and the read is the broken half |

Image `27b14944...1f7c`, 26,714,112 B, kernel `0c8d67a7` (18 bytes from 2382),
partition prediction `e3398237...2858`. Built offline and reproduced to the same
sha; `boot_a` untouched at `2931647a...86b1`.

## 28. 2383 ran: no fault was taken

Trial 2026-11-06 21:04. Image `27b14944...1f7c`, kernel mark `0x2383`, 153 marks,
fastboot at 90.82 s, `boot_a` restored to `2931647a...86b1`.

```
groups / fault_entry_counter   9      -> the handler never ran
fault_taken                    false
relocation_observed            true   (probe PA 0x401a4000)
input_va                       0x1000200   (the marker: the probe reached the call)
output_va                      0x4002000   (template seed, never written by the stub)
group_stride                   0xa0        (template seed, never written by the stub)
stage / error / cleanup        4 / -53 / -53
mcu_status, mmu_raw, as_fault  1, 0, 0
```

The two words the stub would have written still hold the template's seeds, which
is the in-band proof that the exception entry never executed: had a fault been
taken, `output_va` would hold the stacked PC and `group_stride` the CFSR.

Why that negative is trustworthy, given the instrument is new:

- all five fault vectors are 0x010019b1, checked by the builder on every
  trace-probe build, so any fault - including a HardFault escalation - reaches
  the stub;
- the stub lives at 0x010019b0, inside the block 0x01001800..0x010019ff that
  this same run executed (the patched entry at 0x010018ec wrote the marker and
  the counter), so the block was already fetched when the call was made;
- the marker 0x01000200 is present, so the probe really got to the `bl`.

So the fresh-block call into 0x01000200 stops the MCU **without raising an
exception**. That is not a translation refusal. A walker that rejected the
access would raise IACCVIOL/IBUSERR/PRECISERR and the stub would have recorded
it; instead the instruction never completes and nothing is signalled.

What that leaves: the fetch of a cold 512-byte block stalls in a way that never
reports. Together with 2373/2375 the picture is now:

- data reads of cold pages in other sections: fine (2375);
- data read of the second block of the code section: hangs (2373);
- fetch of that block: hangs, no exception (2379, 2382, 2383);
- moving the block's PA by 1.2 MB: no change (2382);
- descriptor, attributes, index, share bits: no change (2378, 2380).

A stall with no fault, tied to the block and not to its PA or attributes, points
at the MCU-side access path itself (a fill/ready handshake that never returns),
not at the page tables.

One honest caveat before that conclusion is treated as final: the fault-entry
stub has never been seen to fire. Its correctness is argued from the vector
table, the block being warm and the marker being present - all offline-checkable
facts, but not a measurement. A deliberate fault (2384) is the control that turns
"the handler did not run" into "the handler cannot run, or would have".

## 29. 2384: the control that proves the fault entry works

2383's "no exception was taken" is only worth the instrument behind it, and that
instrument had never been seen to fire. 2384 is 2383 with the entry program
replaced by a deliberate fault: write the marker, read the protected section at
0x03000000 that the plan never maps, then write 30 and park.

```
0x010018ec  cpsid i / r4 = 0x01000200 / r3 = 0x04000000
            str r4,[r3,#8]      ; the marker
            r0 = 0x03000000
            ldr r1,[r0]         ; the deliberate fault
            r1 = 30 / str r1,[r3,#16] / b .
```

Everything else is inherited from 2383: same relocated code section, same probe
patch at 0x01000200, same 40-byte fault entry at 0x010019b0, same writable RO
leaves. Built from 2383's spec by replacing only the entry window, so the two
containers differ at 0x2790..0x27a5 and nowhere else.

The counter now has three meanings and no fourth:

| counter | what it means for 2383 |
|---|---|
| 20 | the stub fired - the fault entry works, and 2383's 9 is a real measurement: the cold fetch raises nothing |
| 30 | the read of the unmapped section completed - the reachable space is bigger than the built tables, and 2383's 9 has to be re-read |
| 8 (the template seed) with the marker set | the read neither faulted nor completed - a stall is indistinguishable from a silent refusal, and 2383's result loses its diagnostic value |

Image `be2c5cdb...393d`, 26,714,112 B, kernel `44180108` (19 bytes from 2383),
partition prediction `786879f2...7839`, reproduced to the same sha. Built and
preflighted offline; `boot_a` untouched at `2931647a...86b1`.

## 30. 2384 ran: the refusal is visible to the MMU and invisible to the MCU

Trial 2026-11-06 21:14, image `be2c5cdb...393d`, fastboot at 81.32 s, `boot_a`
restored to `2931647a...86b1`.

```
control_counter                8      the template seed: the entry program stopped
control_marker_present         true   ...after writing the marker, before writing 30
positive_control_outcome       refusal-not-signalled
error / mmu_raw                -54 / 1
AS_FAULT                       0x7cd002c2
AS_FAULT_LO / HI               0x3000000 / 0
relocation_observed            true   (probe PA 0x401a4000)
```

The counter says the intended control - 20, the fault entry - did not fire. The
MMU words say why, and they say it in the same encoding 2375 recorded when its
probe read the same unmapped address:

| trial | access | `error` | `mmu_raw` | `as_fault` | `as_fault_lo` |
|---|---|---|---|---|---|
| 2375 | MCU reads 0x03000000 | -54 | 1 | 0x7cd002c2 | 0x03000000 |
| 2384 | MCU reads 0x03000000 | -54 | 1 | 0x7cd002c2 | 0x03000000 |

So the read was issued, walked and refused, and the refusal was latched against
the exact address. What did not happen is delivery: the entry program never
advanced past the `ldr`, and the stub at 0x010019b0 never wrote its 20. An AS
refusal reaches the MCU as a transaction that never completes, not as a bus error
that would raise a PreciseBusFault.

There is a second reason the stub could not have fired in this build, and it is
worth naming before anyone builds on it: the entry program replaces the reset
handler's prologue, so it runs with SP never loaded. An exception entry has
nowhere to stack its frame. The 2383 negative therefore never rested on the stub
being able to run.

**What survives, and on what evidence.** 2383 read `as_fault = 0` and
`mmu_raw = 0`, and this trial shows those two words are set by a refusal at this
very AS. The cold fetch was not refused. The 2383 conclusion - a fetch that
stalls without a fault, tied to the block and not to its PA or its attributes -
now rests on the MMU words instead of on an exception that could not have been
taken. The instrument changed; the measurement did not.

**What it corrects.** 2375 was read as "the heap probe faults, the RX read hangs,
and `-54` vs `-53` separates the two". The `-54`/`-53` split is real, but it is
the *shim's* observation of `mmu_raw`/`AS_FAULT`, not a statement about what the
core did. In 2375 the core hung on that read exactly as it hung in 2384.

**What is left.** Every fetch that has been measured completing came from a block
that was already resident: the reset target 0x010018ec sits inside 0x01001800,
which the core fetched at reset, and the read of 0x01001900 (2375) came from that
same warm block. The only cold targets ever tried are the ones that hang. The next
question is therefore the primitive one: does the MCU ever complete a fetch of a
block that is not already resident - at reset, where the very first fetch must be
cold by definition?

## 31. 2385 ran: a cold fetch completes - the wall is the running core

Trial 2026-11-06 21:33, image `c7e3e01d...d9eb`, fastboot at 85.64 s, `boot_a`
restored to `2931647a...86b1`.

```
input_va (shared+8)            0x100e000  the marker: the block was fetched and run
groups (shared+16)             8          the program writes only the marker
mmu_raw, as_fault              0, 0       nothing was refused
mcu_status, relocation         1, true
error                           -53        the shutdown probe timing out, as always
```

2385 changed one word: the reset vector at VA 0x4 moved from `0x010018ed` to
`0x0100E001`. At 0x0100E000 - 56 KB into the 64 KB code section, in a block no
access had ever reached - sits 20 bytes: `cpsid i`, build `0x0100E000`, write it to
shared+8, park. No stack, no literal pool, no branch. The core can only get there
by fetching that block on its first cycle.

It got there. **A cold fetch completes.**

That retires the reading the last six trials were built on. "Only a resident block
works" was never a property of the memory path: it was a property of *who* asked.
The fetch the core issues from reset reaches a block nothing has touched; the
fetch it issues from a running program - `bl 0x01000200` in 2379/2382/2383 - does
not. The same is true of data: the only cold data reads ever attempted
(2370/2371/2373, the `ldr` at 0x010019dc) were issued by a running program too.

So the wall narrows to a difference of state, not of mapping:

| who fetches | cold block | result |
|---|---|---|
| the core at reset, target 0x010018ec | warm (it is the reset target) | runs - 2376 onward |
| the core at reset, target 0x0100E000 | cold | runs - 2385 |
| a running program, `bl` 0x01000200 | cold | hangs, no fault - 2383 |
| a running program, `ldr` 0x01001a00 | cold | hangs, no fault - 2373 |

Nothing about the page tables differs between rows three and four and rows one and
two: same section, same leaves, same PA base, same plan. What differs is that the
first two happen before any state was established on the core.

One defect in this run's provenance, recorded so it cannot be mistaken for a
match: the kernel was built without bumping `SWEET_BUILD_ID`, so the SWEETMRK
records carry `0x2384`. The report ABI is identical, the image sha identifies the
run, and the capture decodes with `--build 0x2385 --mark 0x2384` - the new
`--mark` option exists for exactly this case.

The next question is no longer "can a cold block be reached". It is whether the
block the running core could not reach - `0x01000200` - is reachable at all when
the reset word asks for it. Same 20 bytes, vector word `0x0100E001` -> `0x01000201`.
If it runs, the discriminator is reset-versus-running and the block was never
special; if it does not, page 0 differs from page 14 somewhere the plan does not
show, and that is an offline question about descriptors, PA and container bytes.

## 32. 2386 ran: the block is the wall, not the core's state

Trial 2026-11-06 21:38, image `e0e8933c...797b`, kernel `46743d03` (`SWEET_BUILD_ID`
0x2386, so this capture tags itself correctly), fastboot at 120.97 s, `boot_a`
restored to `2931647a...86b1`.

```
input_va (shared+8)      0x04000200   the template seed: the marker was never written
groups (shared+16)       8           the program never started
mmu_raw, as_fault        0, 0        nothing was refused
mcu_status, relocation   1, true
error                    -53
```

One word changed against 2385: the reset vector target, `0x0100E001` ->
`0x01000201`. Nothing else - same program, same mapping, same relocation, same
fault entry. 2385 ran, 2386 did not.

That kills 2385's reading. The wall is not reset-versus-running core state: the
reset fetch reaches `0x0100E000` and does not reach `0x01000200`. The block is
what matters, and every entry path into it has now failed the same way:

| entry | block | result |
|---|---|---|
| reset fetch | 0x01000200 | stalls, no fault - 2386 |
| `bl` from a running program | 0x01000200 | stalls, no fault - 2379/2382/2383 |
| data read from a running program | 0x01000200 | stalls, no fault - 2373/2375 |
| reset fetch | 0x0100E000 | runs - 2385 |
| fetch, executed at reset | 0x01001800 | runs - every build since 2376 |

The offline audit the 2385 verdict asked for was run before proposing another
build, and it removes the remaining structural explanations:

| VA | leaf | PA |
|---|---|---|
| 0x01000000 | `0x30000000401a4cc7` | 0x401a4000 |
| 0x0100E000 | `0x30000000401b2cc7` | 0x401b2000 |

Same attributes (AttrIndx 1, AF, read-only, XN=0), same memory group 6, same
tables, and the only difference is the physical page. The container in the shipped
`csf.bin` holds the program at 0x01000200, and the CPU's own read of the section
base matches the container's first word, so the bytes are where the tables say.

So the failure is a property of the block, and the plan does not show a reason. A
page-granular story (page 0 unreachable, page 14 fine) is still possible, and it
would explain a detail the port has never accounted for: the vendor's own entry
veneer at 0x01000000 - `ldr r0,[pc,#0]` / `bx r0` into 0x010002ec - has never been
observed to run.

The bisect that separates the two: keep everything and move the reset word to
`0x01000601`, block 3 of the same page, a block no build has ever patched. A
marker there means the damage is confined to block 1; an absent marker means the
whole of page 0 is unreachable, which is a page-granular fault in the memory path
and a different investigation.

## 33. 2387 ran: page 0 cannot be fetched at all

Trial 2026-11-06 21:51, image `9cca6494...95dd`, kernel `5172beb0` (`SWEET_BUILD_ID`
0x2387), fastboot at 83.48 s, `boot_a` restored to `2931647a...86b1`.

```
input_va (shared+8)      0x04000200   the template seed: no marker
groups (shared+16)       8           the program never started
mmu_raw, as_fault        0, 0        nothing was refused
mcu_status, relocation   1, true
error                    -53
```

Same 20-byte program as 2385, reset word moved to `0x01000601` - block 3 of the
page that holds 0x01000200, and a block no build has ever patched. It did not run.

So the damage is page-granular. 2386's "the block is the wall" was one level too
small; 2385's "the running core is the wall" was one level too big. The reachable
set is now:

| page | VA | entry | result |
|---|---|---|---|
| 0 | 0x01000200, 0x01000600 | reset fetch | stalls, no fault - 2386, 2387 |
| 0 | 0x01000200 | `bl` from a running program | stalls - 2379/2382/2383 |
| 0 | 0x01000200 | data read from a running program | stalls - 2373/2375 |
| 1 | 0x010018ec | reset fetch (vendor's own reset) | assumed, never proven |
| 14 | 0x0100E000 | reset fetch | runs - 2385 |

The page tables were re-checked from the real C this time. A host harness built
from `mali_csf_memory.c` with the production flags, walking the arena it produces:

```
0x01000000  ...401a4cc3  PA 0x401a4000    0x0100e000  ...401b2cc3  PA 0x401b2000
0x01001000  ...401a5cc3  PA 0x401a5000    0x0100f000  ...401b3cc3  PA 0x401b3000
```

Sixteen leaves, identical in AF, AP, SH, AttrIndx and memory group, one L3 table,
no duplicate mappings, differing only in PA. The Python replica quoted in ## 32
says `...4cc7` and is wrong about AttrIndx; it is a mirror, not the implementation,
and should not be cited as evidence again.

One operational defect is worth recording because it cost a restore. `pyusb` was
missing on the python in `PATH`, so the runner's raw restore fell back to the
`fastboot` CLI - the transport this LK breaks with `could not clear input pipe;
e0005000`, which is why `tools/fbraw.py` exists. The stock prefix was written,
then the run was interrupted with the device sitting in fastboot and `boot_a`
half-restored. It was recovered with `pyusb 1.3.1` installed, the raw channel
rebooting into recovery, and the runner's `restore-only` phase, which captured
`after` before rewriting the partition - so the marks survived and the baseline
finished verified.

Next: prove whether page 1 executes at all (reset word -> `0x01001201`), and in the
same build read the live leaf descriptors out of the arena the MMU walks. The
second is passive - it changes no mapping - and it is the instrument this port has
never had: every mapping argument so far has compared plans, never the table the
MCU actually uses.

## 34. 2388 ran: the table is right, and still nothing executes

Trial 2026-11-06 22:12, image `549b62a3...c429`, kernel `86d908a1` (`SWEET_BUILD_ID`
0x2388), fastboot 89.65 s, `boot_a` restored to `2931647a...86b1`.

```
input_va (shared+8)      0x04000200   the template seed: no marker
groups (shared+16)       8           the program never started
mmu_raw, as_fault        0, 0        nothing was refused
mcu_status, relocation   1, true
error                    -53
```

The active change was one word - the reset target, `0x01000601` -> `0x01001201`,
page 1, block 1, a block no build had patched. Page 1 is where the vendor's reset
handler lives at 0x010018ec. It did not run.

**The passive half is the more important result.** The shim now reads the four
leaf descriptors straight out of the arena it hands the AS and publishes them in
their own 32-byte ADT property (`sweet-csf-leaf`, marks 420..423; the 300..313 GPU
and 320..406 CSF blocks are untouched). The capture therefore carries the table
the MCU walks, not a re-derivation of it:

```
leaf 0x01000000  0x30000000401a4c47  PA 0x401a4000
leaf 0x01001000  0x30000000401a5c47  PA 0x401a5000
leaf 0x0100e000  0x30000000401b2c47  PA 0x401b2000
leaf 0x0100f000  0x30000000401b3c47  PA 0x401b3000
```

Four adjacent entries of one L3 table, identical flags (`0xc47` = valid, page,
AttrIndx 1, AF, RW - this build is `--ro-as-rw`), PAs exactly as the relocated
plan says. No stale entry, no second table, no shadowing.

| question | answer |
|---|---|
| does the MCU walk our table? | yes - read from the arena it was given |
| is page 0's leaf wrong? | no, `0x401a4000` |
| is page 1's leaf wrong? | no, `0x401a5000` |
| do the failing pages differ in attributes? | no, all four are `0xc47` |

Every mapping explanation in ## 22-33 is retired by that. The table is right and
the fetch still does not happen, so the wall is not translation.

What is left is a plain contradiction: same program, same leaf shape, same reset
path - 0x0100E000 runs (2385), and 0x01000200 / 0x01000600 / 0x01001200 do not
(2386/2387/2388). The only structural difference is alignment: 0xE000 is 4 KB
aligned, the other three are 512-byte aligned. A masked reset vector would be
strange - the vendor's own vector is 0x010018ed - but that path has never been
observed to run here either, so it is not evidence against it.

Operationally this run is also the first in three that completed cleanly: the raw
USB transport did the whole restore through `tools/fbraw.py` now that `pyusb` is
installed, and the readback matched.

Next: 2389 - the same program at 0x01001000, reset word -> `0x01001001`. That
separates "page 1 does not execute" from "the 0x1200 offset does not execute".

## 35. 2389 ran: only a page-aligned start executes

Trial 2026-11-06 22:19, image `607d911d...662d`, kernel `a9c0c9c7`
(`SWEET_BUILD_ID` 0x2389), fastboot 85.51 s, `boot_a` restored to
`2931647a...86b1`.

```
input_va (shared+8)      0x01001000   the marker, written by the program itself
groups (shared+16)       8           the program writes only the marker
mmu_raw, as_fault        0, 0
mcu_status, relocation   1, true
error                    -53
```

The twenty bytes that did nothing at 0x01001200 one build earlier ran at
0x01001000. Five builds with one variable each now line up:

| build | target | page offset | result |
|---|---|---|---|
| 2385 | 0x0100E000 | 0 | runs |
| 2389 | 0x01001000 | 0 | runs |
| 2386 | 0x01000200 | 0x200 | nothing |
| 2387 | 0x01000600 | 0x600 | nothing |
| 2388 | 0x01001200 | 0x200 | nothing |

2388 and 2389 differ by one word - the target inside page 1 - and only one of
them runs. Both use the same leaf, read back from the arena in 2388. So the wall
is not translation, not the block, not the page: **the low 12 bits of the reset
vector are ignored and the core begins at the page base.**

Page 0 falls out of that for free. 0x01000200 and 0x01000600 both resolve to
0x01000000, and 0x01000000 is the vendor's own entry veneer - `ldr r0,[pc,#0]`
then `bx r0` into 0x010002ec. Our program never ran there; the veneer did, and it
hangs. The veneer read as dead code because it needs the boot ROM's register
state, which only a real reset entry carries.

The vendor source confirms the frame it sits in. `MiCode/Xiaomi_Kernel_
OpenSource`, branch `rubens-s-oss` (Redmi K50, MTK tag
`t-alps-release-s0.mp1.tc8sp2-mt6983-V1.0.1`), `mali-r32p1`:

```
kbase_csf_firmware_enable_mcu()   MCU_CONTROL = MCU_CNTRL_AUTO (2), then wait
                                  for the global interface interrupt
convert_mem_flags()               cached -> index 0, everything else -> 5,
                                  SH only for KBASE_REG_SHARE_BOTH
load_fw_image_section()           copies each section page by page from its
                                  data start, zero-fills when ZERO is set
```

No function in the driver writes the reset vector. The vendor firmware relies on
the same word we do, and that word is 0x010018ed - page base 0x01001000. So the
vendor's real entry is the page base, and `SWEET_CSF_RESET_ENTRY_VA` (0x010018ec)
has been 0x8ec past the actual entry since 2376.

That leaves one question open: if the vendor entry is 0x01001000, why has the
unmodified vendor path never reported ready here (`version` 0,
`firmware_ready` 0)? Either the AS still hands it something it rejects, or the
entry expects the boot ROM's argument registers and our programming loses them.
Instrumenting the entry's own first stores is the way to settle it - after 2390,
which only moves the vector word from 0x01001001 to 0x01001201 with the program
left at 0x01001000.

Provenance defect in this image: the builder's leaf-property gate was written as
`build_id == 0x2388`, so 2389 shipped without `sweet-csf-leaf` and the decoder
refused the capture. The gate now covers both builds; `--allow-missing-leaf`
decodes this one capture, whose marker was read out before that flag existed.

## 36. 2390 ran: the vendor entry executes, and the mask reading is dead

Trial 2026-11-06 22:41, image `9051fedf...5fff3e`, kernel `1760629a`
(`SWEET_BUILD_ID` 0x2390), fastboot 111.67 s, `boot_a` restored to
`2931647a...86b1`.

```
input_va (shared+8)      0x010018ec   the marker at the vendor's own entry
groups (shared+16)       8           the program writes only the marker
mmu_raw, as_fault        0, 0
mcu_status, relocation   1, true
cleanup_error            0
leaves                   401a4000 / 401a5000 / 401b2000 / 401b3000
```

One word was deliberately not touched: VA 0x4 still reads `0x010018ed`. Two marker
programs sat in the code section, at the address that word names (0x010018ec) and
at the page base below it (0x01001000). The core wrote 0x010018ec.

**So the vendor entry is reachable here.** `SWEET_CSF_RESET_ENTRY_VA` was right,
and the firmware does start; `version = 0` / `firmware_ready = 0` mean it starts
and then hangs, not that it never starts.

It also retracts ## 35. "Only a page-aligned start executes" cannot hold: 0x18ec is
neither 4 KB nor 512-byte aligned. 2385 and 2389 both pointed at addresses that
happen to be page bases, which is why a two-point sample could not separate
"honoured as written" from "masked to the page". 2390 separated them, and the
masked reading lost.

| build | vector | target | aligned | result |
|---|---|---|---|---|
| 2385 | 0x0100E001 | 0x0100E000 | 4 KB | runs |
| 2389 | 0x01001001 | 0x01001000 | 4 KB | runs |
| 2390 | 0x010018ed (vendor) | 0x010018EC | none | runs |
| 2386 | 0x01000201 | 0x01000200 | 512 B | nothing |
| 2387 | 0x01000601 | 0x01000600 | 512 B | nothing |
| 2388 | 0x01001201 | 0x01001200 | 512 B | nothing |

The three failures are real non-starts rather than stale evidence: their
`cleanup_error` is -53, meaning the MCU never reached a state the halt handshake
could stop, while all three successes report 0. And a container-level audit of all
six images against `vendor_a-mali_csffw.bin` puts every changed byte inside the
intended ranges - vector low halfword, one program, the fault entry - so no image
was contaminated by the build.

What 2390 cannot do is separate two readings that both fit all six rows:

- **exact** - the vector is used as written, and 0x200 / 0x600 / 0x1200 fail for a
  reason of their own
- **fallback** - a vector that is not page aligned is ignored and the core starts
  at the vendor entry regardless, which is exactly what 2390 would look like

Only a non-aligned vector pointing somewhere *else* separates them. 2391 does that:
vector to 0x01001A01, the same program at 0x01001A00, and 2390's program left at
0x010018EC as the control. 0x1A00 is inside the code section, 512-byte aligned, not
page aligned, and nothing has ever executed there.

Offline, and worth recording because it removes an alternative: the extracted
`mali_csffw.bin` and `mali_csffw_reload.bin` are the same 258,048 bytes with sha
`de22d2fc...`, so the device cannot be booting a different CSF blob than the one
this port patches.

One build defect was caught before the flash and is worth keeping in the record.
The ADT property gate still read `build_id in (0x2388, 0x2389)` while the spec
declared `leaf_probe` for 2390, and the shim macro gate still read
`build_id == 0x2388`. The first image of this build therefore carried no
`sweet-csf-leaf` and no leaf reader - the same drift that cost 2389 its leaves.
Both gates now read one list (`LEAF_PROBE_BUILDS`) and a test asserts the two
cannot separate again.

## 37. 2391 ran: the word is not a fallback, and four 512-byte boundaries fail

Trial 2026-11-06 23:27, image `372fb8ea...d3dc24`, kernel `8df00489`
(`SWEET_BUILD_ID` 0x2391), fastboot 89.65 s, `boot_a` restored to
`2931647a...86b1`.

```
input_va (shared+8)      0x04002000   the seed, untouched by any landing
groups (shared+16)       8            the counter seed; no program wrote
mmu_raw, as_fault        0, 0
mcu_status, relocation   1, true
cleanup_error            -53
leaves                   401a4000 / 401a5000 / 401b2000 / 401b3000
```

The word at VA 0x4 was changed to `0x01001A01`. Three twenty-byte programs were
in place: at `0x01001A00` where the word taken literally lands, at `0x01001000`
where masking it to the page base would land, and at `0x010018EC` where falling
back to the vendor entry would land. None of them wrote. `cleanup_error = -53`
puts this with 2386/2387/2388 - a real non-start, not a stale capture.

**The fallback reading is dead.** If a non-page-aligned word were ignored and the
core fell back to the vendor entry, `0x010018EC` would have marked. It did not.
So 0x18EC is not a default entry: it ran in 2390 because the vendor word names
it. Whether 2391 stalled at `0x1A00` or refused to start cannot be separated by
this build alone, but the literal reading is the only one still standing.

**All four failures are 512-byte aligned.** With 2391 added, the six earlier rows
and this one form one table:

| build | word | target | 4 KB aligned | 512 B aligned | result |
|---|---|---|---|---|---|
| 2385 | `0x0100E001` | `0xE000` | yes | yes | runs |
| 2389 | `0x01001001` | `0x1000` | yes | yes | runs |
| 2390 | vendor `0x010018ed` | `0x18EC` | no | no | runs |
| 2386 | `0x01000201` | `0x200` | no | yes | nothing |
| 2387 | `0x01000601` | `0x600` | no | yes | nothing |
| 2388 | `0x01001201` | `0x1200` | no | yes | nothing |
| 2391 | `0x01001A01` | `0x1A00` | no | yes | nothing |

Page 1 is the controlled case. `0x1000` (offset 0), `0x1200` (offset 0x200),
`0x18EC` (offset 0x8EC) and `0x1A00` (offset 0xA00) are in the same 4 KB page,
the same L3 leaf `0x401a5000`, with the same flags `0xc47`. Two run and two do
not, and the only property that separates them is whether the offset is a
multiple of 512:

```
0x1000  offset 0x000  runs
0x1200  offset 0x200  nothing
0x18EC  offset 0x8EC  runs
0x1A00  offset 0xA00  nothing
```

That is not a page, leaf, flag or Thumb-bit story. It is a reset-entry address
rule: a 512-byte aligned target that is not also a 4 KB page base does not
start. 2391 adds the fourth failure and the first one at an address this port
chose on a page that is known to execute at its base.

Two caveats belong with the table. The rows are cross-build - 0x1000 and 0x18EC
ran under different words - so the rule is a fit, not a controlled experiment;
2392 repeats the test inside the known-good `0xE000` page at offset `0xA00`.
And `0x1A00` is the middle of a vendor function (`isb; bx lr` then the next
prologue), so "no marker" cannot distinguish a fetch that stalls from a core
that never accepted the word; it does show that overwriting those twenty bytes
does not by itself prevent a start, because no start happened to run them.

What this changes:

- **A** is no longer "three cursed addresses". A single 512-byte rule fits all
  seven data points, including 0x1A00.
- **B** is answered: no fallback. The vendor entry is reachable only when the
  vendor word names it.
- **C** is unchanged and still the goal, but if the rule is about the fetch path
  then the handler may be hanging on the same mechanism; instrumentation along
  it should record the first 512-byte aligned fetch target it reaches.

One repository defect was found while backfilling the patch series: `xnu/patches`
stopped at 0182 (0x2384), and the 2388 leaf-descriptor consumer in `sweet_ufs.c`
was never recorded. Patches 0183-0188 now carry both - 2385 is skipped because
its kernel is byte-identical to 2384 - and replaying 0001-0188 reproduces the
local build tree byte for byte.

## 38. 2393 ran: vendor page attributes do not move the 512 wall

Trial 2026-11-06 23:59, image `b6c4efa3...e077`, kernel `475a9a4c`
(`SWEET_BUILD_ID` 0x2393), fastboot 86.5 s, `boot_a` restored to
`2931647a...86b1`.

```
input_va (shared+8)      0x04002000   the seed, untouched by any landing
groups                   8            the counter seed; no program wrote
mmu_raw, as_fault        0, 0
mcu_status, relocation   1, true
cleanup_error            -53
leaf flags (code)        0x4c3        AttrIdx 0, no nG, read-only, AF
```

2393 repeats 2391's question with the page encoding the vendor driver actually
produces: `AttrIdx 0` for cached sections and 5 for the rest, no `nG` bit,
read-only code, and the vendor `AS_MEMATTR` table. The compiler confirms the
change: 2391 emits `mov w15, #0xc43` and then ORs AttrIdx 1; 2393 emits
`mov w12, #0x443`, `mov w14, #0x4c3` and selects 0x4c3 for the read-only code
page, with no `0x800` anywhere. At runtime the leaf readback is `0x4c3`, so the
encoding travelled with the image.

The word at VA 0x4 was `0x0100EA01`; programs sat at `0x0100EA00`, `0x01001000`
and `0x010018EC`. None wrote.

**So the 512 wall is not an attribute artefact.** Changing AttrIdx, the nG bit,
the code-page permission and the MEMATTR table did not move it by a byte.

What this does not prove yet is that the rule survives the vendor encoding,
because no positive control has run under the same encoding: if the vendor leaf
bits themselves stopped the image from starting anywhere, 2393 would look
exactly like this. 2394 is that control - vendor encoding, vector `0x0100E001`,
program at `0x0100E000`, an address that ran under the shim encoding in 2385.
If 2394 runs, 2393 closes the attribute question and the rule is below the
driver; if 2394 also stalls, the vendor encoding broke the start and 2393 says
nothing about 512.

## 39. 2394 ran: 0xE000 starts under the vendor encoding, 0xEA00 does not

Trial 2026-11-07 00:07, image `c46bb200...bee7`, kernel `6930a140`
(`SWEET_BUILD_ID` 0x2394), fastboot 83.81 s, `boot_a` restored to
`2931647a...86b1`.

```
input_va (shared+8)      0x0100E000   the positive control's marker
groups                   8
mmu_raw, as_fault        0, 0
mcu_status, relocation   1, true
cleanup_error            0
leaf flags (code)        0x4c3        AttrIdx 0, no nG, read-only
```

2394 is 2385's positive control under 2393's vendor page encoding. Its container
is byte-identical to 2385's (vector `0x0100E001`, program at `0x0100E000`); only
the shim compile flags differ. The marker appeared, and `cleanup_error = 0` is
the same signature as 2385/2389/2390.

| build | page encoding | target | cleanup_error | result |
|---|---|---|---|---|
| 2393 | vendor | `0xEA00` | -53 | nothing |
| 2394 | vendor | `0xE000` | 0 | runs |

Same build flags, same container layout, same leaf bits; only the low nine bits
of the target differ. So 2393's no-marker is not an attribute artefact: the
512-byte rule survives the vendor page encoding and lives below the driver.
2392 and 2395 are unnecessary. The next instrument is C - place markers along
the vendor handler that starts at `0x010018EC` and find where it stops.

## 40. C, answered from evidence already on disk: the rule is bit 9

C asks where the vendor handler stops after it starts at `0x010018EC`. The
answer was already in the 2376 report; nobody had read it against the right
rule.

**2376's stop instruction, decoded.** The unpatched container runs, faults
nothing and never reports ready. Disassembling from `0x010018EC` puts the stop
at the third literal load of the cache helper:

```
0x010019d8  mov.w r1, #0
0x010019dc  ldr   r0, [pc, #0x1e4]    @ 0x01001BC4   <- stops here
0x010019de  str   r1, [r0]
0x010019e0  bx    lr
```

The load reads `0x01001BC4`, and 2371/2373 already measured that a read in that
block never completes. The same helper's next two literals are `0x01001BC8` and
`0x01001BCC`. Nothing in the firmware can get past them.

**The rule was stated one bit too wide.** "512-byte aligned but not a 4 KiB page
base" fits the entry experiments, but two data-read hangs it cannot explain:

- 2369/2370 hung reading `0x01001AF8` - not 512-byte aligned;
- 2376 hung reading `0x01001BC4` - not 512-byte aligned.

Both are 512-byte aligned **plus 0x200**: bit 9 is set. One rule covers every
access this port has ever made, fetch and data alike:

> an MCU access hangs iff bit 9 of the address is set.

**Correction (2396, section 42):** this holds for the code section, which is
where all twenty-one points below were taken. A bit-9 read in the shared and
stack sections returns. Read the table as evidence about R-X pages, not about
addresses in general.

| addr | bit 9 | offset | kind | observed | build |
|---|---|---|---|---|---|
| `0x01000000` | 0 | `0x000` | read | ok | 2373 |
| `0x01000100` | 0 | `0x100` | read | ok | 2373 |
| `0x01000200` | 1 | `0x200` | read | hang | 2373 |
| `0x01001900` | 0 | `0x900` | read | ok | 2375 |
| `0x010019f0` | 0 | `0x9f0` | read | ok | 2371 |
| `0x01001a00` | 1 | `0xa00` | read | hang | 2371 |
| `0x010019f8` | 0 | `0x9f8` | read | ok | 2370 |
| `0x01001af8` | 1 | `0xaf8` | read | hang | 2369 |
| `0x01001bc4` | 1 | `0xbc4` | read | hang | 2376 |
| `0x02000000` | 0 | `0x000` | read | ok | 2375 |
| `0x02800000` | 0 | `0x000` | read | ok | 2375 |
| `0x02000000` | 0 | `0x000` | write | ok | 2377 |
| `0x0203f000` | 0 | `0x000` | write | ok | 2377 |
| `0x01001000` | 0 | `0x000` | fetch | runs | 2389 |
| `0x010018ec` | 0 | `0x8ec` | fetch | runs | 2390 |
| `0x0100e000` | 0 | `0x000` | fetch | runs | 2394 |
| `0x01000200` | 1 | `0x200` | fetch | nothing | 2386 |
| `0x01000600` | 1 | `0x600` | fetch | nothing | 2387 |
| `0x01001200` | 1 | `0x200` | fetch | nothing | 2388 |
| `0x01001a00` | 1 | `0xa00` | fetch | nothing | 2391 |
| `0x0100ea00` | 1 | `0xa00` | fetch | nothing | 2393 |

21 points, no exception, across six different page encodings and two access
kinds. The "touched 512-byte block" reading of 2373 needed 2366 as an admitted
exception; it was fitting the block index, which is bit 9 divided by two.

**What this rules out.** `as_fault` is 0 on both sides of the wall - 2394 (runs)
and 2391/2393 (nothing) report `as_fault = 0`, `mmu_raw = 0`, and 2376 does too.
A translation that produced no valid entry would fault, as the unmapped heap
probe in 2375 did. So the walk succeeds and the transaction stops after it. That
is why nine attribute experiments changed nothing: the descriptor is not the
subject.

**Why no mapping change can move it.** Every leaf this shim writes is 4 KiB
aligned, so `PA bit 9 == VA bit 9` for every byte of every section. 2382's
1.2 MB relocation preserved that equality, which is why the wall did not move.
Any page-aligned translation preserves it. So the remaining levers are not in
the page table at all; they are in the memory path the GPU uses for that PA -
cache mode first, since a cacheable access is the only kind that has ever been
made here.

**2395 reuses the number that 2394 cancelled** (a `0x1A00` confirmation under
vendor leaves, now pointless). It is the first lever test: entry `0x01001A01`,
the `0x1A00` program as in 2391, and the code section mapped with the
non-cacheable attribute instead of the cached one. A marker says the wall is
cacheability and the firmware can boot by changing one attribute; no marker says
the stall is below the cache and the next lever is the memory-group tag.

## 41. 2395 ran: cacheability is not the lever either

2395's container is 2393's, byte for byte - `0x0100EA01` at VA 0x4, the same
twenty-byte marker at `0x0100EA00`, the same control landings, the same 103
bytes against the vendor file. One thing changed: the executable section's leaf
now selects `AS_MEMATTR` index 5 (non-cacheable) and carries no SH bits, which
no build had ever done. 2393 hung at `0xEA00` with the cached index, 2394 ran at
`0xE000` with it, so this is the first lever that reaches below the descriptor
without changing the address.

| field | value |
|---|---|
| image | `e9652ef8...760e`, 26,714,112 B |
| kernel | `ff844738...3824`, `SWEET_BUILD_ID 0x2395` |
| leaf, VA `0x01000000` | `0x30000000401a44d7` - AttrIndx 5, SH clear |
| `input_va` | `0x04002000` (the seed: no landing ran) |
| `groups` / `cleanup_error` | 8 / -53 |
| `as_fault` / `mmu_raw` | 0 / 0 |
| fastboot | 82.73 s, `boot_a` restored to `2931647a...86b1` |

The readback is the point: `0x4d7` is exactly the value the compiler was asked
for - `(leaf & ~0x31c) | 0x14` on the executable section - so the encoding
travelled and the null result is about the hardware, not about the build. The
report's own guard agrees: `code_leaf_attr_index = 5`,
`code_leaf_uncached = true`.

**What is now closed.** With cached (2393) and non-cacheable (2395) giving the
same no-landing on a byte-identical container, the whole descriptor family is
spent: AttrIndx, SH, nG, AP, XN-in-attr, memory group 6 (vendor-grounded: the
`arm,physical-memory-group-manager` path substitutes 6), and `TRANSCFG` (we
write `0x42000006`; the vendor writes `AS_TRANSCFG_ADRMODE_AARCH64_4K` = 6 in
the low field). Nine attribute experiments, all null.

**What is left.** Two families, and one of them has never been tested at all:

1. **Is bit 9 global, or is it a property of the RX section?** Every bit-9
   data point so far - `0x01000200`, `0x01001A00`, `0x01001AF8`, `0x01001BC4` -
   lies in the code section. No probe has ever read a bit-9 address in the
   stack, heap or shared section, all of which are RW and NX. If a stack read at
   `0x02000200` returns while the code read at `0x01001200` hangs, the rule is
   not "bit 9" but "bit 9 inside an executable page", and XN becomes the only
   leaf field still unvaried.
2. **The mapping granularity.** `ADRMODE_AARCH64_4K` walks a level-3 table for
   every access. A 2 MB level-2 block for the code section would bypass that
   walk entirely. If a block mapping starts while a leaf mapping stalls, the
   level-3 walk is the fault; if it also stalls, the address path below the MMU
   is.

Order matters: (1) is one ladder in one build, (2) needs the arena aligned to
2 MB and is the more expensive change.

## 42. 2396 ran: bit 9 only bites inside the executable section

The ladder wrote marker 1, read `0x04000200` in the shared section, wrote marker
2, read `0x02000200` in the stack, wrote marker 3, read `0x01001200` in the code
section and stopped there. `input_va = 3`, so the first two reads returned.

| field | value |
|---|---|
| image | `e05405f9...c6ae`, 26,714,112 B |
| kernel | `82882120...a9e7`, `SWEET_BUILD_ID 0x2396` |
| entry / encoding | `0x0100E001`, 2394's vendor leaves, `0x...4c3` |
| `input_va` | **3** - marker 3 was written, so reads 1 and 2 completed |
| `groups` / `cleanup_error` | 8 / -53 |
| `as_fault` / `mmu_raw` | 0 / 0 |
| fastboot | 83.38 s, `boot_a` restored to `2931647a...86b1` |

**Section 40 is too wide and this corrects it.** The uniform rule "an access
hangs iff bit 9 is set" was fitted to twenty-one points that all happened to
live in the code section. 2396 puts a bit-9 read in two other sections and both
complete:

| read | section | bit 9 | result |
|---|---|---|---|
| `0x04000200` | shared, RW coherent | 1 | **returned** |
| `0x02000200` | stack, RW non-executable | 1 | **returned** |
| `0x01001200` | code, R-X | 1 | stalled |

So the property belongs to the executable section, not to the address. Everything
section 40 says about the *code* section stands - the entry targets, the literal
read at `0x01001BC4`, the `as_fault = 0` signature - but the law is narrower:
bit 9 inside a page the MCU can execute.

**What that leaves.** Between the stack leaf and the code leaf the differences
are now only `AP[2]` and `XN`. `AP[2]` was varied in 2378 - the code pages were
mapped writable and the firmware still stopped at the same literal read - so XN
is the only leaf field this port has never moved. 2397 answers it: same ladder,
same entry, same everything, with the executable section mapped non-executable
and the read at `0x01001200` as the answer. If it returns, XN is the switch and
the reason lives in the fetch/data split inside an executable page; if it still
stalls, XN is exonerated and the next instrument is the level-2 block.

One confound is recorded, not hidden: the three probes differ in physical page
as well as in section, because each section has its own arena offset. 2382 moved
the code section by 1.2 MB without moving the wall, which argues the PA is not
the variable, but it is an argument, not a measurement.

## 43. 2397 ran: executability is not the lever either

2397's container is 2396's, byte for byte - same `0x0100E001` vector, same
forty-eight byte ladder, same ninety-three bytes against the vendor file. One
thing moved, and it is not in the container: the 4 KiB page at VA `0x01001000`
was forced non-executable (`PXN|UXN`, bits 54:53) while every other page kept its
permissions and the entry page `0x0100E000` stayed executable.

| field | value |
|---|---|
| image | `8a651666...b308`, 26,714,112 B |
| kernel | `7043c805...f250`, `SWEET_BUILD_ID 0x2397` |
| leaf, VA `0x01001000` | `0x30600000401a54c3` - XN set, AttrIndx 0, PA `0x401a5000` |
| leaf, VA `0x01000000` / `0x0100E000` | `...4c3` unchanged, X clear |
| `input_va` | **3** - markers 1, 2 and 3 were written, so the shared and stack reads returned and the code read did not |
| `groups` / `cleanup_error` | 8 / -53 |
| `as_fault` / `mmu_raw` | 0 / 0 |
| fastboot | 85.71 s, `boot_a` restored to `2931647a...86b1` |

The readback is the point again: `probe_page_xn = true` and the descriptor
carries `0x0060000000000000`, so the permission travelled. A data read of
`0x01001200` stalled anyway. **XN is exonerated**, and with it every leaf field
this port can vary has now been varied:

| leaf input | build | result |
|---|---|---|
| AttrIndx / MemAttr (vendor pairing) | 2393 | stall |
| cacheability of the code section | 2395 | stall |
| AP[2] (writable code) | 2378 | stall |
| SH (shareability) | 2374 | stall |
| nG | 2393 | stall |
| memory group 6 | throughout | stall |
| XN on the target page | 2397 | stall |

**A second reading dies here as well.** The stall could have been a property of
the physical address rather than the virtual one. It is not: the shared read at
`0x04000200` becomes PA `0x40110200` and the stack read at `0x02000200` becomes
PA `0x40090200`, both with bit 9 set, and both returned. More fundamentally, a
page-aligned mapping always preserves `PA bit 9 == VA bit 9`, so no remap and no
change of granule can ever separate the two - 2382's 1.2 MB relocation preserved
it, a 2 MB block would preserve it too, because a 2 MB aligned base has bit 9
clear.

**What the data now says.** Within one 4 KiB page, one leaf and one physical
page, offset `0x000` works and offset `0x200` stalls, in the MCU's own 64 KiB
code window, while the identical offset pattern in the stack and shared sections
returns. Nothing at the mapping layer can express that difference, because there
is no mapping-layer difference: same entry, same descriptor, same page.

**And that is where the current model breaks.** The vendor firmware's own
prologue calls `0x01001A2A` (bit 9 set) and its cache helper reads
`0x01001BC4` (bit 9 set); under the measured rule both would stall, yet the GPU
boots on Android. So either those paths are never taken on real hardware, or our
image still differs from the vendor's in something we have not looked at. Every
lever we can pull inside the shim has now been pulled; the next instrument
should stop varying our own image and read the vendor's live mapping instead.

## 44. 2398 ran: the memory group tag is not the wall either

2398's container is 2396's byte for byte. One leaf input moved: bits 59..62,
the physical memory group tag, from 6 to 0. Every build since 2327 had published
6 there, inherited from the pinned mali_mgm helper; the tag is the last leaf
input that had never been varied.

| field | value |
|---|---|
| image | `d953fa3a...ef47`, 26,714,112 B |
| kernel | `aa81f1e1...f859`, `SWEET_BUILD_ID 0x2398` |
| leaves | `0x401a44c3`, `0x401a54c3`, `0x401b24c3`, `0x401b34c3` - tag 0, AttrIndx 0, AF, type 3 |
| `leaf_group_tags` | `[0, 0, 0, 0]`, `leaf_group_zero = true` |
| `input_va` | **3** - shared and stack reads returned, the code read did not |
| `groups` / `cleanup_error` | 8 / -53 |
| `as_fault` / `mmu_raw` | 0 / 0 |
| fastboot | 83.40 s, `boot_a` restored to `2931647a...86b1` |

**Why the tag was worth a flight.** The vendor driver never writes a group id
into a page-table entry: `kbase_native_mgm_alloc()` ignores its `group_id`
argument (`CSTD_UNUSED`), and no file in the midgard tree shifts anything into
bits 59..62. The working MT6993 port in this repository's `x9` branch writes 0 as
well. So the shim's 6 was its own invention, and it was the only leaf field never
varied.

**Now the leaf is exhausted.** AttrIndx/MemAttr (2393), cacheability (2395),
AP (2378), SH (2374), nG (2393), XN (2397), memory group (2398) - all null on a
container that differs from 2396's by nothing.

**What the two surviving data points still say.** Within one 4 KiB page, one
leaf and one physical page, offset `0x000` reads and `0x200` stalls, in
`0x01000000`-`0x0100FFFF` only, while the same offset pattern in the stack and
shared sections returns. Since every page-aligned mapping preserves
`PA bit 9 == VA bit 9`, the remaining question is not "which bit" but "which
side of the translation owns it". 2399 can answer that without moving the
pattern: alias the page at VA `0x01001000` onto a stack page (PA `0x40091000`,
offset `0x200` = PA `0x40091200`, bit 9 still set). If that read returns, the
wall follows the code section's physical pages and the firmware allocation can be
moved; if it still stalls, the wall follows the virtual range and no mapping
change can ever fix it.

**Answered in section 45: it still stalled.** The wall follows the virtual range,
not the physical page.

## 45. 2399 ran: the wall is the virtual range, not the physical page

2399 repoints exactly one leaf. VA `0x01001000` - the page that holds the read
target `0x01001200` - is given the physical page that backs VA `0x02000000`, the
stack page the ladder's second read already read through offset `0x200`. After
the alias, read 3 and read 2 name the same physical word `0x40091200`, with the
same PA bit 9 = 1; only the VA and the leaf attributes differ. Container, entry,
encoding and every other leaf stay at 2396's values.

| field | value |
|---|---|
| image | `284b95b2...f453`, 26,714,112 B |
| kernel | `13743a97...d87a`, `SWEET_BUILD_ID 0x2399` |
| container | `d59eb487...0ba8` - byte-identical to 2396/2397/2398, 93 bytes changed against the vendor file |
| leaves | `0x30000000401a54c3`, `0x30000000400914c3`, `0x30000000401b34c3`, `0x30000000401b44c3` |
| `alias_applied` | **true** - the leaf at `0x01001000` is PA `0x40091000` with the code section's own attribute bits |
| `input_va` | **3** - shared and stack reads returned, the code read did not |
| `groups` / `cleanup_error` | 8 / -53 |
| `as_fault` / `mmu_raw` | 0 / 0 |
| fastboot | 87.84 s, `boot_a` restored to `2931647a...86b1` (verified) |

**The two reads of one boot.** Read 2 (`0x02000200`) returned. Read 3
(`0x01001200`) then stalled on the same PA, `0x40091200`, which read 2 had just
brought into the cache. The only differences left are the virtual address and the
leaf's attribute bits. 2397 forced this page non-executable and it still stalled;
2393 and 2395 varied AttrIdx and cacheability. So the physical page is not the
wall, and no page-table field that has been varied moves it.

**What this closes.** The firmware allocation does not need to move: the same
physical memory serves the MCU when it is named through the stack VA. Every
remaining explanation has to sit above the page table - what the AS, the MCU's
own address window, or the platform adds for the `0x01000000`-`0x0100FFFF` range
- or in the leaf attribute class as a whole, which 2400 separates by giving the
code VA the stack leaf's exact low bits and nothing else.

**A note on the build.** The alias helper costs 0x2cc bytes of shim text, which
moved the 0x4000-aligned BSS array ahead of the arena by one page: this build's
arena is `0x40078000`, not `0x40077000`, so every PA in the run is 2396's plus
`0x1000`. The builder pins the per-build arena value instead of relaxing the
check, and the manifest records it (`csf_arena.shim_offset = 0x78000`).

## 46. 2400 ran: the cache mode is not the wall either; the page table is out of levers

2400 is 2396's container and ladder with one page mapped non-cacheable: VA
`0x01001000` takes AS_MEMATTR index 5 with no SH bits, the entry page and every
other leaf keep 2396's values. 2395 had made the whole section non-cacheable but
only asked a fetch to land there, never this read.

| field | value |
|---|---|
| image | `fff61b73...84b3`, 26,714,112 B |
| kernel | `a321ee94...0bb0`, `SWEET_BUILD_ID 0x2400` |
| container | `d59eb487...0ba8` - byte-identical to 2396..2399 |
| leaves | `0x30000000401a44c3`, **`0x30000000401a54d7`**, `0x30000000401b24c3`, `0x30000000401b34c3` |
| `probe_page_uncached` | **true** - AttrIdx 5, SH 0, the other three leaves untouched |
| `input_va` | **3** - the marker written before the one read that actually ran (`0x01001200`); see the correction below |
| `groups` / `cleanup_error` | 8 / -53 |
| `as_fault` / `mmu_raw` | 0 / 0 |
| fastboot | 121.28 s, `boot_a` restored to `2931647a...86b1` (verified) |

**Correction (2026-11-07 13:30).** The 2396..2400 ladder encoded its first two
reads as `f8d4 0200` / `f8d6 0200`, which little-endian Thumb decodes as
`bmi`+`movs` / `bvs`+`movs`; `ldr.w` needs `d4 f8 00 02`. Markers 1 and 2 were
written anyway, so `input_va = 3` names a pending third read, not a shared or
stack stall. The shared read at `0x04000200` and the stack read at `0x02000200`
never executed. 2400's single-read result (a non-cacheable `0x01001200` page
still stalls) stands; the claim that the shared and stack controls returned does
not. The same correction voids 2396's "bit 9 only in R-X pages", 2398's "the
returning stack and shared sections", and 2399's "same physical word readable
through the stack VA".

**The page table has nothing left to vary.** AttrIndx/MemAttr (2393), cacheability
in the fetch direction (2395) and now in the data direction (2400), AP (2378),
SH (2374), nG (2393), XN (2397), memory group/PBHA (2398), physical page (2399) -
every one null *for the one read that ran*, each on a container that differs
from 2396's by nothing else. A data read of `0x01001200` stalls whether the page
is cached or not, while a fetch from the same window at `0x0100E000` completes
and runs the ladder.

**What is left.** The wall is a property of the `0x01000000`-`0x0100FFFF`
virtual window, not of any field the shim writes: same table, same PA bit 9,
same attributes, different VA range, different outcome. The open question for
2401 is whether the window or the VA value is the property: map the very same
code section at a second window (`0x03000000`), reset-vector a ladder there, and
ask whether a `0x03001200` read returns - with a fresh L3 page and with a reuse
of L2[8]'s L3 page, so the original frame is separated from the window too.

## 47. 2401 rebuilt: the ladder reads the page it runs from, and the fault entry names itself

2401 maps the executable section a second time at `0x03000000` with its own L3
and data pages, aliases `0x05000000` onto `L2[8]`'s L3 page, and starts at the
mirror's `0x0300E000`. Read 3 is new: `0x0300E200`, a word in the very page the
core is fetching from, so its translation cannot be cold. That single read splits
"the data path into an executable section refuses" from "the cold walk refuses"
without another build.

| item | value |
|---|---|
| image | `6f0e1fc1...5aa0`, 26,714,112 B, arena `0x78000` |
| kernel | `83ec99c4...05d6`, `SWEET_BUILD_ID 0x2401` (unchanged) |
| container | 121 B vs vendor `de22d2fc...229a`; only `0x19b0..0x19d8` and `0xE000..0xE054` moved |
| plan | 8 mappings, 9 table pages, required `0x14E000` |
| mirror | `0x03000000` copy, entry `0x0300E000`; section PA `0x401a6000`, page `0x401a7000` |
| share | `L2[40] = L2[8]`; `0x05001000` leaf identical to `0x01001000` (`0x30000000401b74c3`) |
| code | relocated to PA `0x401b6000`; original entry `0x0100E000` -> `0x401c4000` |
| reset | word `0x4 = 0x0300e001` |
| ladder | 84 B, marker 1 `0x04000200`, 2 `0x02000200`, 3 `0x0300E200`, 4 `0x03001200`, 5 `0x05001200`, 6 `0x01001200`, 7 all returned |
| fault | `0x010019b0` writes `input_va = 0xE3`, stacked PC to `output_va`, CFSR to `group_stride` |
| tests | 283 ran, 3 skipped; patch series 0001-0197 |

`input_va` names the read that did not return. 3 means even a word in the
executing page stalls - no walk involved. 4 means that page is readable and the
cold one is not, so the walk or leaf index 1 is the wall. 5 means the mirror is
readable and the reused `L2[8]` L3 page is not, which would make the page frame
the suspect and would let the stock firmware be rescued by replacing that one
table page. 6 means `0x05001200` returned and `0x01001200` did not with an
identical table page, leaf and PA, which leaves only the VA. 7 means the stall
needs the core to be executing from `0x0100xxxx` at the same time. `0xE3` means
the core took a synchronous fault instead - `output_va` is the stacked PC and
`group_stride` is CFSR, and a bus read that never completes cannot raise one.

Two metadata bugs were fixed on the way. `mirror_check()` added its own stand-in
base (`0x40077000`) to arena offsets, so 2399/2401's manifest named every mirror
PA `0x1000` below the image; it now returns offsets and `build()` resolves them
against the arena symbol it pinned. It also rebuilt the arena without the vendor
leaf macros, so it recorded `0x...cc7` (AttrIdx 1, nG, SH) where the image ships
`0x...4c3`.

The image is built, unit-tested, static-checked and preflighted but **not flown**.
`boot_a` remains `2931647a...86b1`.

## 48. 2401 ran: the first non-code bit-9 read stalls, and the window was never the wall

`input_va = 1`, `groups = 8`, `as_fault = 0`, `mcu_status = 1`, `error = -53`.
The ladder started at the mirror's `0x0300E000` - marker 1 is in shared and
nothing else writes that word - and the first read, shared `0x04000200`, never
completed. No `0xE3`, so the fault entry was never entered. Reads 2..6 were never
issued. Fastboot appeared at 82.53 s; `boot_a` was restored and verified to
`2931647a...86b1`.

**The mirror is real.** The four published leaves are the predicted words:

```
0x30000000401a64c3  0x30000000401a74c3  0x30000000401b74c3  0x30000000401b74c3
```

`mirror_applied`, `alias_applied` and `relocation_observed` are all true: the
fresh L3 page for `L2[24]`, the copied `L2[8]` entry at `L2[40]`, and the
corrected manifest PAs all describe the image that ran.

**What it means.** `0x04000200` has bit 9 set. Every access in this series that
returned has bit 9 clear, and every one that hung has it set:

| bit 9 = 0 (returned / ran) | bit 9 = 1 (stalled) |
|---|---|
| `0x01001900`, `0x02000000`, `0x02800000` (2375) | `0x01000200` (2374 read, 2386 fetch) |
| `0x0100E000` (2385..2395 fetch) | `0x01001BC4` (2376 vendor `ldr`) |
| `0x010018ec` (2390 entry) | `0x0100EA00` (2393 fetch) |
| | `0x01001200` (2393..2400) |
| | `0x04000200` (2401, first non-code bit-9 read) |

One address bit, not a VA window and not a section. Bit 9 sits below the 4 KiB
page offset, so VA and PA bit 9 are the same bit and no page move can separate
them - which is why 2382 (PA move) and 2399 (leaf repoint) kept the stall.

**2401's own design error.** Both control reads are bit-9 = 1 addresses
(`0x04000200`, `0x02000200`), inherited from the 2396 ladder that never executed
them. The run therefore stopped at read 1 and says nothing about the mirror
window, the L3 page frame, or `0x0300E200`.

**2402** is the bit-9 matrix, one read per cell, in three sections plus a pair
inside one page: `0x04000000` / `0x04000200`, `0x02000000` / `0x02000200`,
`0x0100E000` / `0x0100E200`. If 1/3/5 return and 2/4/6 stall, bit 9 is the rule
and the question moves from the page table to the address decode (GMPU,
`AS_TRANSCFG`).

## 49. 2402 built: the bit-9 matrix, controls first, no mirror

2401's result (section 48) says the wall is address bit 9. 2402 tests that with
six reads and nothing else moved: the mirror is gone, the image is 2400's layout,
reset word `0x4 = 0x0100e001`, and the ladder is back at `0x0100E000`. Every read
below is a word inside a page the image already maps, so no walk takes part.

| marker | read | section | bit 9 | why this address |
|---|---|---|---|---|
| 1 | `0x04000000` | shared | 0 | never read before; 2375's shared probe never ran |
| 2 | `0x02000000` | stack | 0 | returned in 2375, cold |
| 3 | `0x0100E400` | code | 0 | the page the ladder is fetched from, cold line |
| 4 | `0x0100E200` | code | 1 | same page, 0x200 away: the decisive read |
| 5 | `0x02000200` | stack | 1 | same page as 2 |
| 6 | `0x04000200` | shared | 1 | 2401 stalled here |
| 7 | - | - | - | all six returned |

**Order is part of the design.** The first stall ends the run, so all three
bit-9 = 0 reads go first; an earlier sketch put `0x04000200` second, which would
have stopped at the address 2401 had already answered. The code pair is
`0x0100E400` vs `0x0100E200` rather than `0x0100E000` vs `0x0100E200` so that
neither probe is the entry instruction and both sit the same distance from the
page base.

**Read 3 is a control for a competing theory.** 2373/2374 measured that a data
read of an unfetched RX line does not complete. Read 3 is exactly that - a cold
line in the page the core is executing from, at bit 9 = 0. If it stalls, the wall
is the RX cold line and bit 9 is irrelevant; if it returns, that theory dies in
the same boot that tests bit 9.

| item | value |
|---|---|
| image | `e7f00f28...e329`, 26,714,112 B, arena `0x77000` |
| kernel | `ff842023...27ba`, `SWEET_BUILD_ID 0x2402`, patch 0198 |
| container | 115 B changed: vector word, 72 B at `0x0100E000`, 40 B at `0x010019b0` |
| ladder | 72 B, `tools/matisse-csf-ladder2402.S`, pinned as `COLD_BOOT_2402` |
| leaves | `0x01000000` -> `0x401a4000`, `0x01001000` -> `0x401a5000`, vendor encoding |
| tests | 286 ran, 3 skipped |

Readings: `4` proves bit 9 above the MMU (same entry, leaf, PA - only the address
bit differs). `3` makes the RX cold line the wall. `1`/`2` put it in the shared or
stack section itself. `5`/`6` say bit 9 is not the rule and the wall is per
section. `7` says 2401's stall needed the mirror, i.e. the core executing at
`0x0300E000`. `input_va = 0xE3` is a synchronous M7 fault, stacked PC in
`output_va`, CFSR in `group_stride`.

Built, unit-tested, statically verified and preflighted, **not flown**. `boot_a`
is `2931647a...86b1`.

## 50. 2402 ran: bit 9 decides, in one page, and no mapping can move it

Image `e7f00f28...e329`, kernel `0x2402`. `input_va = 4`, `groups = 8`,
`as_fault = 0`, `mcu_status = 1`, `error = -53`: no fault, no response.

| marker | read | section | bit 9 | outcome |
|---|---|---|---|---|
| 1 | `0x04000000` | shared | 0 | returned - first data read ever made there |
| 2 | `0x02000000` | stack | 0 | returned, cold |
| 3 | `0x0100E400` | code | 0 | returned - cold line in the executing page |
| 4 | `0x0100E200` | code | 1 | never returned |
| 5, 6 | - | - | 1 | never issued |

**The pair is the proof.** Reads 3 and 4 are 0x200 apart inside one 4 KiB page:
same L2 entry, same L3 entry, same leaf word (`0x30000000401b24c3`), same
physical page (`0x401b2000`), no walk for either, and 3 returned before 4 was
issued. They differ in bit 10 as well (`0x0100E400` has it set), so bit 10 is
ruled out by the same read and only bit 9 correlates.

**Two older readings are dead.**

- *"A cold data read of an RX line never completes"* (2373/2374). Read 3 **is**
  that access - cold line, executable page, in the page the core is fetching -
  and it returned.
- *"The wall is the `0x0100xxxx` window / a section / an attribute"*. The stall
  is now on record for a fetch (2386, 2393) and a data read (2393..2402), in
  three sections, under every leaf encoding tried, cached and non-cacheable,
  with the mirror and without it.

**Why no page table can ever separate VA from PA here.** `AS_TRANSCFG` reads
`0x42000006` → `ADRMODE = 6 = AS_TRANSCFG_ADRMODE_AARCH64_4K`: a plain AArch64
4 KiB stage-1 translation. Its output address is 4 KiB aligned, so
`PA[11:0] == VA[11:0]` for every mapping the hardware can hold. Bit 9 is inside
that window, so "VA bit 9" and "PA bit 9" are one bit, permanently. 2382 moved
the PA, 2399 repointed a leaf, 2401 built a fresh L3 page - none of them could
have changed it, and none did.

**What is left to explain.** Not the MMU. The CPU wrote the whole 64 KiB section
(bit-9 = 1 halves included) and read the arena back, so the memory and the
system-level path are fine; the MCU's read at the same PA never gets a response.
The vendor firmware's own first data read, `0x01001BC4`, is bit-9 = 1, which is
why the stock firmware cannot boot while this holds.

**2403: split load from store at bit 9, and check the returned data.**

```
1 read  0x0100E000 (b9 0) -> shared+16    does the word match the image?
2 read  0x0100E1FC (b9 0) -> shared+20    last word of the even half
3 store 0x5a5a5a5a to 0x0100E200 (b9 1)   does a write complete where a read cannot?
4 read  0x0100E200 (b9 1) -> shared+24
5 read  0x0100E400 (b9 0)
```

Stall at 3: the address is dead in both directions. Pass 3 and stall at 4: the
address decodes and accepts writes, only the read response never arrives. A
mismatched value at 1 would retroactively question every "returned" in the
series.

```
fastboot 101.14 s; fbraw reboot-recovery -> Recovery in 18 s
boot_a restored and verified 2931647a...86b1; capture 23:49
```

## 51. 2403 built: an L2 alias splits the VA from the leaf

2402 left one question: is the refusal keyed on the virtual address above the
MMU, or on the page that address lands on? 2403 separates them with an alias
that allocates nothing - L2 slot 24 receives slot 8's entry verbatim, so
`0x0300E200` walks the identical L3 page, leaf descriptor and physical word as
`0x0100E200`. The ladder stays at `0x0100E000`, so its first read is 2402's
known-good one.

| marker | read | bit 9 | why |
|---|---|---|---|
| 1 | `0x0100E400` | 0 | baseline; the word goes to `shared+12`, must equal `0x0f10f857` |
| 2 | `0x0300E200` | 1 | the alias: same leaf, same PA, different VA |
| 3 | `0x01001200` | 1 | page `0x01001000` non-cacheable **and** PBHA 0 |
| 4 | `0x0100E200` | 1 | 2402's own address, in the same boot as its alias |
| 5 | - | - | all four returned |

Read 2 decides: returned => the wall is keyed on the VA above the MMU; stalled
=> it travels with the page, the leaf or bit 9 itself. Reads 3 and 4 only run if
read 2 returned, and 3 is the one cell of the attribute matrix that was never
measured - 2398 cleared PBHA with cacheability on, 2400 cleared cacheability
with PBHA 6, and both stalled at bit 9 = 1.

**A premise this build no longer uses.** "2399 showed the stack works at
bit 9 = 1" is false: the 2396..2400 ladder encoded both control reads as
`f8d4 0200` / `f8d6 0200`, which decode to `bmi` + `movs r2,r0`. Reads 1 and 2
never executed in that series; `input_va = 3` only ever meant read 3 stalled. No
bit-9 = 1 access has ever been issued in the shared or stack section.

| item | value |
|---|---|
| image | `83372fdc...0a63`, 26,714,112 B |
| kernel | `eb555c22...4cae`, `SWEET_BUILD_ID 0x2403`, patch 0199 |
| arena | `0x78000` (one page above 2402) |
| relocated | `0x401a5000` - 2402's `0x401a4000` plus that page |
| container | 108 B: 68 B ladder, 40 B fault entry, vector word, `0x01000200` |
| alias | slot 24 <- slot 8; `0x0300E000` leaf must equal `0x0100E000` word for word |
| leaves | PBHA 0 everywhere; `0x01001000` must end `0x4d7`; `0x02000000` published too |
| tests | 289 ran, 3 skipped |

Built, unit-tested, statically verified and preflighted, **not flown**. `boot_a`
is `2931647a...86b1`. The arena/PA shift is the trap this class of build keeps
setting: any build that writes a second L2 slot lands one page higher, and a
decoder pinned to the previous PA would throw the capture away.

## 52. 2403 ran: the VA prefix is out, and the returned bytes are finally verified

Image `83372fdc...0a63`, kernel `0x2403`. `input_va = 2`, `groups = 8`,
`as_fault = 0`, `mcu_status = 1`, `error = -53`: no fault, no response.

| marker | read | VA | bit 9 | leaf | outcome |
|---|---|---|---|---|---|
| 1 | `0x0100E400` | `0x0100xxxx` | 0 | `0x401b34c3` | returned, word `0x0f10f857` |
| 2 | `0x0300E200` | `0x0300xxxx` | 1 | same word | never returned |
| 3 | `0x01001200` | `0x0100xxxx` | 1 | `0x401a64d7` | never issued |
| 4 | `0x0100E200` | `0x0100xxxx` | 1 | `0x401b34c3` | never issued |

**The alias is byte-identical and it still stalls.** L2 slot 24 received slot 8's
entry verbatim, so `0x0300E200` walks the same L2 entry, the same L3 page, the
same leaf word and the same physical word as `0x0100E200`, and it never
completes. The live leaves confirm the image:

```
0x0100E000  0x00000000401b34c3  PBHA 0  cached  RO
0x0300E000  0x00000000401b34c3  PBHA 0  cached  RO   identical, as designed
0x01001000  0x00000000401a64d7  PBHA 0  AttrIdx 5    uncached page
0x02000000  0x0060000040091443  PBHA 0  cached  RW
```

`alias_applied`, `uncached_page_applied`, `pbha_cleared` and
`relocation_observed` are all true, and `firmware_probe_pa = 0x401a5000`, so the
arena page shift this build introduced was pinned correctly.

**Three readings die here.**

- *The `0x0100xxxx` window is special.* It is not: the identical mapping through
  `0x0300xxxx` stalls the same way. That was the last surviving form of the
  window theory, and 2393..2402 had already shown the stall with a fetch and with
  a data read.
- *Some leaf encoding is the lever.* With PBHA cleared everywhere the code page
  became **cached + PBHA 0**, a cell never measured before, and bit 9 = 1 still
  stalls. The measured cells at bit 9 = 1 are now cached+PBHA 6 (2402),
  uncached+PBHA 6 (2400) and cached+PBHA 0 (this run): three of four.
- *The returned bytes may have been wrong all along.* They were not. Read 1
  returned the vendor word `0x0f10f857` from `0x0100E400` - the first data
  verification in the series - so every earlier "returned" now rests on a
  measured data path.

**Where the model stands.** One invariate remains over 2401..2403: the MCU access
carries address bit 9 = 1. It holds for fetches and data reads, three virtual
ranges (`0x0100`, `0x0300`, `0x0400`), two sections (code and shared - the stack
has never been probed at bit 9 = 1), at least four physical pages, and every leaf
encoding tried; reads at bit 9 = 0 return correct data. `AS_TRANSCFG = 0x42000006`
(`ADRMODE 6 = AARCH64_4K`) means `PA[11:0] == VA[11:0]` for every mapping the AS
can hold, so this is not something the page table can express, let alone fix.

**2404: direction, and the last matrix cell.**

```
1 read  0x0100E400 (b9 0) -> shared+12   baseline + data check
2 read  0x04000000 (b9 0) -> shared+16   shared page on an even 512 B block
3 read  0x04000200 (b9 1) -> shared+20   uncached + PBHA 0 - the 4th cell
4 store 0x5a5a5a5a -> 0x04000200 (b9 1)  a write at 2401's stalling address
5 read  0x04000200 (b9 1) -> shared+24   read-after-write
6 read  0x01001200 (b9 1) -> shared+28   the 4th cell on the code page too
7 all six returned
```

Read 3 precedes the store deliberately: it is a read, so a return both answers the
attribute question and lets the run continue, while a stall costs one marker and
the store is still issued. The store and read 5 sit in a page that is RW, so the
store tests the bus and not the MMU's AP bits, and `5a5a5a5a` landing in
`shared+24` is decidable offline.

Store stalls => the odd 512 B blocks are dead in both directions, an address
decode/route problem that no leaf change can ever work around. Store passes and
read 5 stalls => the address decodes and accepts writes, only the read response
never arrives, which is a different bug with a different owner. Read 3 returns =>
uncached + PBHA 0 is the working corner. Read 3 and 5 both return `5a5a5a5a` =>
the block heals once written, pointing at cache/tag state rather than decode.

```
fastboot 85.6 s; the runner completed its own restore this time
boot_a restored and verified 2931647a...86b1
289 tests / 3 skipped
```


## 53. 2404 built: force the page walk to read a descriptor at PA bit 9 = 1

2402 and 2403 left one invariate: every MCU access with address bit 9 = 1 hangs,
every access at bit 9 = 0 returns correct data. Either the address is dead for the
whole GPU side, or the defect is confined to the MCU's own fetches and loads. The
only way to tell is to make hardware that is *not* the MCU read at bit 9 = 1, and
the page walk is such a reader.

**A descriptor has an address too.** Mirroring the executable section at
`0x06040000` puts `L2[48]` at table offset `0x180` (bit 9 = 0) and lands the
section's 16 pages on L3 indices `0x40..0x4F`, i.e. byte offsets `0x200..0x278` of
a fresh table page. Every one of those has PA bit 9 = 1. Reading `0x0604E400` then
costs a cold walk whose final descriptor fetch is at bit 9 = 1, while the access
itself is VA bit 9 = 0, PA bit 9 = 0 (`0x401b3400`), and names the same word as
`0x0100E400`.

`0x08000000` was rejected as the base. The Cortex-M7 window decoders on this family
are documented as owning `0x08000000..0x3FFFFFFF`, and a mis-decode there produces
exactly the symptom under test - no marker at all - which would have been read as
"the walk died". Staying below `0x08000000` removes the ambiguity for free.

**The leaf must be valid.** An unmapped entry faults as soon as the walk succeeds,
ending the run before the store test, and the store direction is the one thing
nobody has measured.

| marker | access | bit 9 | why |
|---|---|---|---|
| 1 | read `0x0100E400` | 0 | warm translation; word must be `0x0f10f857` |
| 2 | read `0x0604E400` | descriptor 1 | the walk question |
| 3 | store `0x5a5a5a5a` -> `0x04000200` + `DSB SY` | 1 | first write anyone has issued there |
| 4 | read `0x04000200` | 1 | read-after-write |
| 5 | - | - | everything returned |

The `DSB` is not optional: a normal non-cacheable store is posted, so without it
marker 3 would appear whether or not the write ever reached AXI. Every read stores
its word to `shared+12`; `shared+16` is the `groups` counter and `shared+20` is
`group_stride`, which the decoder checks as a length, so a `0x5a5a5a5a` word there
would have thrown the run away.

| item | value |
|---|---|
| image | `3c58fb31...cecd`, 26,714,112 B, arena `0x77000` |
| kernel | `04110196...a281`, `SWEET_BUILD_ID 0x2404`, patch 0200 |
| section | `0x401b5000`; probe VA `0x0100E000` -> `0x401c3000` |
| mirror | `0x401a5000`; entry `0x0604E000` -> `0x401b3000` |
| leaves | `0x30000000401c34c3`, `0x30000000401b34c3`, `0x30000000401b64d7` |
| ladder | 88 B, `tools/matisse-csf-ladder2404.S` |
| tests | 292 ran, 3 skipped |

Readings: `2` => the wall is below the page table and above DRAM; `3` => both
directions die, an address decode fault; `4` => writes land and only the read
response is missing; `5` with `shared+12 = 0x5a5a5a5a` => the block heals once
written; `0xe3` => a synchronous fault, which itself proves the walk completed.

Built, unit-tested, statically verified and preflighted, **not flown**. `boot_a` is
`2931647a...86b1`.

## 54. 2404 ran: the ladder stopped at marker 1, and the data slot was never a data check

Flew `3c58fb31...cecd` on 2026-11-08 12:53. `boot_a` is back at `2931647a...86b1`.
No fault (`as_fault` 0, `mmu_raw` 0, `mcu_status` 1), `error` -53, `input_va` 1,
`output_va` `0x04003000`, `groups` 8 (the seed, never overwritten).

**The layout was right.** Live leaves are code `0x401c34c3`, mirror `0x401b34c3`
with identical attribute bits, and `firmware_probe_pa` `0x401b5000` is exactly
`0x401c3000 - 0xE000`, i.e. the firmware base with the ladder 0xE000 into the
64 KiB section. The first decode called this `not-relocated` because it compared
the *base* the kernel reports for VA `0x01000000` against the *probe page*; the
check now requires the base plus `code_leaf == base + 0xE000`.

**`shared+12` is filler, not a read result.** 2402's ladder, disassembled this
session from the shipped `stub_bytes`, writes only markers: there is no
`str [r4, #0xc]` anywhere in it. Its flight nevertheless read `0x04003000` from
`shared+12`. The arena is therefore not zeroed, and that word was sitting there
before any MCU store. 2404 shows the same value for the same reason, so it says
nothing about what read 1 returned - the decoder no longer scores it, and
`marker 1` no longer carries a data WARNING.

**What is left.** Marker 1 is written before read 1, marker 2 before read 2, and
nothing separates them: 2404 has no barrier after a marker store, so "read 1
stalled" and "marker 2 was still in the store buffer behind a stalled read 2"
produce the same report. 2402 and 2403 both got `0x0100E400` back, so the
baseline is not expected to stall and the second reading is the likelier one -
but likelier is not measured, and the descriptor question stays open.

| reading | state |
|---|---|
| marker 1 | stopped at or before read 1; unreachable as evidence |
| marker 2 + `0x0f10f857` | read 1 returned, the bit-9 walk stalled: the wall is below the page table |
| marker 2 + other word | read 1 returned the wrong PA: a mapping fault, not a walk fault |

**2405 must fix the instrument before it asks anything.** Three changes, no new
addresses: `dsb sy` after every marker store and after the result store, so a
marker cannot be lost behind the read that follows it; the kernel writes
`0xDEADBEEF` into `shared+12` before it writes `MCU_CONTROL`, so a word that is
still the sentinel proves no store landed and a replaced word proves one did;
and the same four accesses as 2404, unchanged, so the result is comparable.

`0x004`/`0x048`/`0x2C0..0x2CC` stay for the build after that: they answer the
GPU L2 slice question and cannot be read out of a run whose ladder never got past
marker 1.

## 55. 2405 built: the same four accesses, with an instrument that can report

2404 answered nothing because its instrument could not. Two defects, both in the
build rather than in the hardware:

* **markers were posted writes with no barrier.** Marker N is stored before
  access N, so if access N stalls, marker N can still be in the store buffer
  when the core dies. "Read 1 stalled" and "read 2 stalled, marker 2 undrained"
  print the same report.
* **`shared+12` was never seeded.** 2402's shipped ladder writes markers only -
  no store to `shared+12` anywhere in its `stub_bytes` - yet its flight read
  `0x04003000` out of that slot. The arena arrives uninitialised, so the word is
  filler until the ladder writes it, and 2404's `0x04003000` was filler too.

2405 changes no address. The ladder grows from 88 to 120 bytes and gains nine
`DSB SY` instructions: one after every marker store and one after every result
store. `xnu/gpu/mali_csf_boot.c`, linked into `shim.elf`, seeds `shared+12` with `0xdeadbeef` immediately before
`MCU_CONTROL` and fails closed if the seed does not read back - a slot that
takes no host write cannot report an MCU write.

| marker | access | reads |
|---|---|---|
| 1 | read `0x0100E400` | warm, bit 9 = 0; the word must be `0x0f10f857` |
| 2 | read `0x0604E400` | the same word through the mirror; cold walk, L3 entry at bit 9 = 1 |
| 3 | store `0x5a5a5a5a` -> `0x04000200` + `DSB SY` | first write at bit 9 = 1 |
| 4 | read `0x04000200` | read-after-write |
| 5 | - | everything returned |

| reading | state |
|---|---|
| marker 1, seed intact | read 1 never stored: a warm bit-9 = 0 read stalled, a new refusal |
| marker 1, seed replaced | read 1 returned and stored; the core died before marker 2 |
| marker 2, `0x0f10f857` | read 1 returned; the bit-9 walk is the wall, below the page table |
| marker 2, other word | read 1 translated to the wrong PA; the walk stays unmeasured |
| marker 2, seed intact | impossible by construction; refuse the run |

| item | value |
|---|---|
| image | `f53cde64...b8ace`, 26,714,112 B, arena `0x77000` |
| kernel | `4a289747...fd5`, `SWEET_BUILD_ID 0x2405`, patch 0201 |
| section | `0x401b5000`; probe VA `0x0100E000` -> `0x401c3000` |
| mirror | `0x401a5000`; entry `0x0604E000` -> `0x401b3000` |
| ladder | 120 B, `tools/matisse-csf-ladder2405.S`, 9 x `DSB SY` |
| tests | 295 ran, 3 skipped |

**The build recipe is recovered and verified.** Rebuilding 2404 from the recorded
inputs produced `3c58fb31...cecd` byte for byte, so the same command with
`--build-id 0x2405` is a known-good path rather than a guess:

```
tools/matisse-shim-gpu-image.py --build-id 0x2405 \
  --firmware research/matisse/20261031-gpu/shim2333-path-ready/csf.bin \
  --kernel xnu/out/local/build/xnu.obj/kernel.development.sweet \
  --template backup/boot_a-stock-trim.img --stock backup/boot_a-stock-trim.img \
  --adt research/matisse/20261031-hs/matisse-userland-native-keys-2317.adt \
  --frozen research/matisse/20261031-hs/frozen-shim-2313/shim \
  --cmdline research/matisse/20261031-gpu/cmdline-2317.txt \
  --ndk .../ndk/28.2.13676358/toolchains/llvm/prebuilt/darwin-x86_64/bin \
  --trace-probe --vendor-leaves --relocate-code --mcu-control 2 \
  --leaf-group 0 --uncached-page --mirror-code --out <dir>
```

Built, unit-tested, statically verified and preflighted, **not flown**. `boot_a`
is still `2931647a...86b1`.

## 56. 2405 ran: the instrument works, and it caught a build defect instead of the wall

Flew `f53cde64...b8ace` on 2026-11-08 13:26, restored to `2931647a...86b1`.
`input_va` 2, `shared+12` `0x0f10f857`, seed gone, `error` -54, `as_fault`
`0x0604e400`, `mcu_status` 1.

**Two things are now measured, not argued.**

* Marker 2 exists, which with a `DSB` behind it means read 1 completed.
* `shared+12` holds the vendor word `0x0f10f857` and the `0xdeadbeef` seed is
  gone, so read 1 returned *the right bytes* and stored them. The warm
  bit-9 = 0 read of the executing page is confirmed by data for the first time.

**And the run still could not ask the walk question**, because the shim had the
mirror at a different VA than the ladder read. The AS faulted at `0x0604e400`
with `error -54`: an unmapped VA, not a stall. The cause was in the builder, not
in the hardware:

```
2405 shim.elf:  mov w10, #0x3000000     <- SWEET_CSF_MIRROR_CODE_VA
2406 shim.elf:  mov w10, #0x6040000     <- what the ladder reads
```

`SWEET_CSF_MIRROR_CODE_VA` and `SWEET_CSF_LEAF_VA_LIST` were still chosen by
hardcoded `build == 0x2404` tests, so 2405 fell through to the 2401 branch: the
mirror went to `0x03000000` and the four published leaf VAs were the 2401 list.
`TRACE_PROBE[0x2405]` had said `0x06040000` all along; nothing read it. The
leaf-0 VA table in `Image-bare` is the second witness - 2405 carries
`{0x03000000, 0x03001000, 0x05001000, 0x01001000}`, 2406 carries
`{0x0100e000, 0x0604e000, 0x01001000, 0x02000000}`.

Both values now come from one function, `chip_definitions(build_id,
mirror_code)`, which reads the same `TRACE_PROBE` dict the header patch is built
from and raises when `--mirror-code` and the spec disagree. A unit test pins
2401/2402/2403/2404/2405/2406, and 2404 still rebuilds byte for byte
(`3c58fb31...cecd`), so the refactor is behaviour-preserving.

The decoder was wrong in the same direction: it called this run `not-relocated`
because the four words it read were mislabelled by build id. It now checks
`mirror_mapped` first - a zero leaf at `0x0604E000` means the image never mapped
the VA the ladder reads - and reports `mirror-not-mapped` instead of blaming the
layout.

| item | 2406 |
|---|---|
| image | `38389ecf...c0f9`, 26,714,112 B, arena `0x77000` |
| kernel | `2805ae74...e4d`, `SWEET_BUILD_ID 0x2406`, patch 0202 |
| mirror | `0x06040000` -> `0x401b3000`, L3 entry at offset `0x270` (bit 9 = 1) |
| section | `0x401b5000`; probe VA `0x0100E000` -> `0x401c3000` |
| ladder | unchanged, 120 B, same four accesses, 9 x `DSB SY` |
| tests | 297 ran, 3 skipped |

Built, unit-tested, statically verified and preflighted, **not flown**. `boot_a`
is still `2931647a...86b1`. The readings are 2405's table: marker 1 with the seed
intact is a stalled baseline, marker 2 with `0x0f10f857` is the bit-9 walk, marker
2 with anything else is a bad translation.

## 57. 2406 ran: the wall is the page-table walk itself

Flew `38389ecf...c0f9` on 2026-11-08 13:33, restored to `2931647a...86b1` in the
same run. `input_va` 2, `shared+12` `0x0f10f857`, seed gone, `error` -53, no
fault (`as_fault` 0, `mmu_raw` 0), `mcu_status` 1, `groups` 8.

**The wiring fix worked and the instrument held.** The mirror leaf reads
`0x401b34c3` at VA `0x0604E000` - a real mapping with the same attribute bits as
the code leaf `0x401c34c3` - and the ladder's marker 2 with a `DSB` behind it
means read 1 completed and stored the vendor word. Read 2 never came back: no
marker 3, no fault entry, the MCU still enabled.

**Every address on both paths, and their bit 9:**

| access | step | PA | bit 9 |
|---|---|---|---|
| read 1 | L0 descriptor | `0x40077000` | 0 |
| read 1 | L1 descriptor | `0x40078000` | 0 |
| read 1 | L2 descriptor | `0x4007b040` | 0 |
| read 1 | L3 descriptor | `0x4007b070` | 0 |
| read 1 | data word | `0x401c3400` | 0 |
| read 2 | L0 descriptor | `0x40077000` | 0 |
| read 2 | L1 descriptor | `0x40078000` | 0 |
| read 2 | L2 descriptor | `0x4007f180` | 0 |
| **read 2** | **L3 descriptor** | **`0x4007f270`** | **1** |
| read 2 | data word | `0x401b3400` | 0 |

Read 1's five addresses are all bit-9 = 0 and it returns. Read 2 has exactly one
bit-9 = 1 address in its whole path - the last descriptor, the one that turns VA
`0x0604E400` into a page - and the core stops there.

**Why this is not the cold-walk confound.** Read 2 is the first walk in the
series that has to fetch a table the core has not touched, so "cold fetch" and
"bit 9" arrive together. They can be separated because the boot's own first walk
is cold too and it works: the reset vector is `0x0100E001`, so the core's very
first fetch walks `0x40077000` -> `0x40078000` -> `0x4007b040` -> `0x4007b070`,
four cold descriptors, all bit-9 = 0, and it executes the ladder. Every build in
this series that reached the ladder started that way. Cold table fetches at bit-9 = 0 are therefore not the
problem, and the L2 descriptor read 2 needs is at `0x4007f180`, bit 9 = 0.

**What this changes.** Until now the wall looked like a data-path defect: bit 9
of a *data* address killed the access (2402's `0x0100E200`, the vendor
firmware's first read at `0x01001BC4` -> PA `0x401b6bc4`). 2406 shows the same
bit killing a *descriptor* fetch, at an address no data access ever names. The
fault is not in the leaf encoding, not in the VA, not in the attributes, not in
one bad page: the MCU's DRAM path has no responder for addresses with bit 9 = 1,
whether the transaction is a load or a table walk. The transaction never
completes and never errors, which is why `as_fault` stays 0 and `mcu_status`
stays 1.

Three consequences worth stating, all testable:

* a page is reachable only if its L3 descriptor sits at a bit-9 = 0 offset, i.e.
  `(VA >> 18) & 1 == 0`. The code section `0x01000000`..`0x0100ffff` satisfies
  this for all sixteen of its pages, which is why the ladder runs at all.
* the mirror at `0x06040000`..`0x0604ffff` does not: every page there has
  `(VA >> 18) & 1 == 1`, so its descriptor offset is >= 0x200 and every one of
  them is unwalkable. A mirror read would not have worked at any offset, not
  just at `0x0400`.
* a 512-byte interleave is the obvious suspect: bit 9 selects the half of each
  1 KiB granule, and a channel that is gated would swallow the transaction
  exactly this way. That is a hypothesis about *why*; the measurement is only
  that the address is dead.

**Also fixed: the manifest was lying about this build.** `csf_mirror_code` read
`0x3000000` and `csf_leaf_probe_va` listed the 2401 four for every
`--mirror-code` build, because both fields were literal 2401 values rather than
the spec. 2404/2405/2406 manifests all carried the wrong values, i.e. exactly the
mistake that cost 2405 a flight, frozen into the evidence record. Both now come
from `chip_spec(build_id, mirror_code)`; 2404 still rebuilds byte for byte
(`3c58fb31...cecd`) and 2406 rebuilds to the flown `38389ecf...c0f9`, so only the
manifest changed. 298 tests pass, 3 skipped.

`boot_a` is back at `2931647a...86b1`.

## 58. 2407 built: the same four accesses, plus the registers that could explain bit 9

2406 left the wall at a single address - the L3 descriptor at PA `0x4007f270`, the
only bit-9 = 1 address in either walk. The next question is not *where* but *why*
that address has no responder. 2407 answers it with a read-only sample, not with
another probe of the same wall.

**Nothing about the experiment moves.** The ladder, the `0xdeadbeef` seed and the
four accesses are 2406's bytes. Ten GPU words are sampled before `MCU_CONTROL`
and again after the attempt:

| offset | why it is in the list |
|---|---|
| `0x000`, `0x004`, `0x00c` | the ID/config cluster |
| `0x034` | `GPU_STATUS`, the only word that says the block is clocked |
| `0x048`, `0x04c` | the L2 config the dual-slice hypothesis hangs on |
| `0x2c0`, `0x2c4`, `0x2c8`, `0x2cc` | what the vendor KMD dump reads beside it |

They are published raw and named by offset. Naming an undocumented bit is how a
sample turns into a belief, and this build is only allowed to produce a lead.

**The report grew 88 bytes and the arena moved a page.** The block is 2 + 10 + 10
`uint32`, so `sizeof(struct sweet_csf_boot_report)` went from 696 to 784, the
shim's `.bss` crossed a page boundary, and the arena anchor went `0x77000` ->
`0x78000`. Every PA in this build is therefore `0x1000` higher:

| item | 2406 | 2407 |
|---|---|---|
| firmware base (VA `0x01000000`) | `0x401b5000` | `0x401b6000` |
| code leaf | `0x30000000401c34c3` | `0x30000000401c44c3` |
| mirror leaf | `0x30000000401b34c3` | `0x30000000401b44c3` |
| uncached leaf | `0x30000000401b64d7` | `0x30000000401b74d7` |
| read 1 L3 descriptor | `0x4007b070` (bit 9 = 0) | `0x4007c070` (bit 9 = 0) |
| read 2 L3 descriptor | `0x4007f270` (bit 9 = 1) | `0x40080270` (bit 9 = 1) |
| read 1 / read 2 data | `0x401c3400` / `0x401b3400` | `0x401c4400` / `0x401b4400` |

The shift is `0x1000`, i.e. bit 12, so **no bit-9 relation in the build changes**.
That is the one thing that had to be true for the run to stay comparable, and it
was checked by rebuilding the page table, not by assuming it.

**Three copies of "696" had to go.** Growing the struct would have failed
silently in three places, so all three now read one number:

* `shim/gpu.c` looked up the ADT property with a literal 696 and refused to
  publish if `sizeof` disagreed; it now asks for `sizeof(shim_csf_report)`.
* `shim/csf.c`'s `_Static_assert` pins 696 or 784, chosen by the same macro that
  compiles the block in.
* the kernel's forwarder copied 696 bytes and emitted 87 marks - a hardcoded
  count that would have dropped the new block without a word. It now forwards
  `size / 8` marks for any 696..1024-byte property (`xnu/patches/0204`). A
  register block nobody can read is worse than no block.

| item | value |
|---|---|
| image | `c124e536...1781`, 26,714,112 B, arena `0x78000` |
| kernel | `c01dcbea...d5ea`, `SWEET_BUILD_ID 0x2407`, patches 0203 + 0204 |
| section / probe | `0x401b6000` / `0x0100E000` -> `0x401c4000` |
| mirror | `0x401b4000`, entry `0x0604E000` |
| ladder | unchanged, 120 B, 2406's four accesses |
| tests | 300 ran, 3 skipped |

2404 still rebuilds byte for byte (`3c58fb31...cecd`) with the register block
compiled out, so the guard is honest. Built, unit-tested and preflighted,
**not flown**; `boot_a` is still `2931647a...86b1`.

| reading | state |
|---|---|
| `0x048` shows a slice masked off | a lead: the bit-9 address may belong to an L2 slice that is not configured |
| `0x048` symmetric while bit 9 still dies | the slice story is wrong and the address decode or the EMI channel is next |
| the block is all zeros | the GPU block was not clocked when it was sampled; say so, do not read it |

## 59. 2407 ran: the register block is alive, and it does not show a masked slice

Flew `c124e536...1781` on 2026-11-08 14:10, restored to `2931647a...86b1` in the
same run. `input_va` 2, `shared+12` `0x0f10f857`, seed gone, no fault,
`mcu_status` 1, `error` -53, `gpu_regs_sample_flags` 3, `firmware_probe_pa`
`0x401b6000`, code leaf `0x401c44c3`, mirror `0x401b44c3`.

**It reproduced 2406 exactly.** Same marker, same vendor word, same silent stop
at the bit-9 descriptor. That is the first time a result in this series has been
repeated by an independent build, and it retires the possibility that 2406 was a
one-off.

**The register block is live, so the zeros mean something.**

| offset | before | after | |
|---|---|---|---|
| `0x000` | `0xa8620004` | `0xa8620004` | GPU ID, unchanged |
| `0x004` | `0x07130306` | `0x07130306` | |
| `0x00c` | `0x00000809` | `0x00000809` | |
| `0x034` | `0x00000100` | `0x00000101` | GPU_STATUS: bit 0 appeared during the attempt |
| `0x048` | `0x07130000` | `0x07130000` | **low half zero: no slice mask** |
| `0x04c` | `0` | `0` | |
| `0x2c0`..`0x2cc` | `0` | `0` | all four zero, both sides |

The block answers: four words are non-zero and `GPU_STATUS` changes across the
run, so this is not an unclocked block returning zeroes. That matters, because
it makes the `0x2c0` zeros a fact rather than an artefact.

**What the words do not support.** The hypothesis was that `0x048` would show one
L2 slice masked off, which would explain why a bit-9 = 1 address has no
responder. `0x048` reads `0x07130000`: the low sixteen bits - where a per-slice
enable or mask would sit - are zero, before and after. The `0x2c0` block, which
the vendor dump reads next to it, is zero in all four words. Neither word set
carries a slice-disable signal, so **the dual-slice story is not confirmed by
this build**, and the `0x2c0` offsets say nothing either way: zero is what an
unimplemented or unclocked register also returns.

That is a negative result and it is worth stating plainly: ten words were spent
on the hypothesis and none of them moved it forward.

**The sharper question this run exposes.** Every address that has ever killed the
MCU - the data page behind `0x0100E200` in 2402, the vendor firmware's first
read `0x401b6bc4`, the descriptors at `0x4007f270` and `0x40080270` - lies
inside the 2 MiB arena,
`[0x40078000, 0x40278000)`. Not one bit-9 = 1 access has ever been made outside
it. So "bit 9 has no responder" and "the second 512-byte half of this
allocation has no responder" fit every measurement equally well, and the series
has been treating the stronger of the two as established.

That is the discriminator 2408 should buy: one known word, placed by the kernel
in a page outside the arena, read by the MCU at bit 9 = 1 through a descriptor
at bit 9 = 0. Returns the word means the dead set is a property of that
allocation and the wall is a window/IOMMU question; hangs means the dead set is
the address space and the wall is the interconnect.

`boot_a` is back at `2931647a...86b1`.

## 60. 2408 built: the reset panthor performs, before anything else

2407 left two facts it could not explain and did not try to: `GPU_STATUS` reads
`0x100` before and `0x101` after the attempt, so `DBG_ENABLED` is set the whole
time, and `INT_RAWSTAT` already carries `RESET_COMPLETED` - a bit this
transaction never waited for. The audit in `matisse-gpu-upstream-audit.md`
reorders the queue behind them: the out-of-arena page test moves to 2409, and
2408 asks only whether this GPU answers a soft reset at all.

**What the reference driver actually does.** `panthor_gpu_soft_reset()` under
`panthor_device_reset_work()` is preceded by `panthor_fw_pre_reset()` and
`panthor_mmu_pre_reset()` and followed by `panthor_hw_l2_power_on()`,
`panthor_mmu_post_reset()` and `panthor_fw_post_reset()`; `panthor_device_resume()`
reaches the same op through `panthor_gpu_suspend()`. The cold
`panthor_device_init()` does **not** reset - it trusts the bootloader - so "panthor
always resets before AS/MCU" is true of its reset semantics, not of its cold init.
The vendor KMD is the second witness: `GPU_COMMAND_CODE_PAYLOAD(1,1)` is `0x101`,
the same word panthor's `GPU_CMD_DEF(1,1)` produces, so this is not a
project-specific encoding.

**The block that was already in the tree could not fly.** Two independent
reasons: `SWEET_CSF_PRESTART_RESET` was never defined by the builder, so the
preprocessor removed the whole thing, and the code assigned `r->gpu_status`, a
member `struct sweet_csf_boot_report` does not have (`gpu_status` lives in
`sweet_csf_platform_snapshot`). Fixed by passing the define for `0x2408` only and
by putting the evidence where it costs no ABI: `diag_flags` bit 7 attempt,
bit 8 completion, bit 9 `DBG_ENABLED` before, bit 10 still set after. `reset_raw`
and `reset_completed` remain cleanup's, the report stays 784 bytes, and
`gpu_regs_before.reg_034` samples the same word again once the AS is programmed.

Order copied from panthor, not invented: `INT_CLEAR <- BIT(8)` (write-1-to-clear),
`GPU_CMD <- 0x101`, poll `INT_RAWSTAT.BIT(8)` for 100 ms, clear on success. It runs
after the register snapshot and before the coherency write, the L2 power-on and
any AS command. A timeout does not abort: the ladder runs either way, so one boot
carries both halves.

**Build.** Image `184d5353...9801` (26,714,112 bytes), payload `6f82e96c...4af0`,
kernel `c01dcbea...d5ea` - the same kernel as 2407, no new patches. `.text` grew
`0x118` bytes and the arena anchor did not move, which the builder proves rather
than assumes: `arena_pa 0x40078000`, code section `0x401b6000`, code leaf
`0x401c44c3`, mirror `0x401b44c3`, uncached `0x401b74d7` - every
`csf_relocated_code` field identical to 2407's manifest. 302 tests, 3 skipped; a
new unit test compiles the block in and drives both outcomes, completion and
timeout.

**Reading the four bits.** Bit 8 with bit 10: the GPU answers the reset and stays
in debug - then the halt state came from above (LK/GPUEB) and 2409's page test is
the right next move. Bit 8 with bit 10 clear: the reset both completed and
cleared `DBG_ENABLED`, so the earlier stalls happened on a GPU that had never been
reset. Bit 8 clear: the handshake itself never completes, and the next step is the
handoff, not memory. Nothing here says the bit-9 wall is gone, and a bit-9 result
from a timed-out reset describes a GPU that was asked to reset, not one that did.

**Not flown.** `boot_a` is still `2931647a...86b1`.

## 61. 2408 ran: the reset completes, and nothing changes

Flew `184d5353...9801` on 2026-11-08 14:43, read-back verified against
`de922fdd...f7a8`, normal boot reached fastboot at 85.4 s (2407: 85.6 s), `boot_a`
restored to `2931647a...86b1`.

**The handshake works.** `diag_flags` = `2047`: bit 7 attempted, bit 8
`RESET_COMPLETED` arrived inside the 100 ms budget, bit 9 `DBG_ENABLED` before,
bit 10 still set after. This is the first soft reset in the series that completed,
and it is the one issued *before* `MCU_CONTROL`, the coherency write, the L2
power-on and AS0.

**And it changes nothing that can be measured here.**

| | 2407 | 2408 |
|---|---|---|
| `0x000` / `0x004` / `0x00c` | `0xa8620004` / `0x07130306` / `0x00000809` | identical |
| `0x034` before / after | `0x100` / `0x101` | identical |
| `0x048` / `0x04c` | `0x07130000` / `0` | identical |
| `0x2c0`..`0x2cc` | all zero | identical |
| `input_va` / `groups` / `version` / `mcu_status` / `error` | 2 / 8 / 0 / 1 / -53 | identical |
| ladder | read 1 `0x0f10f857`, read 2 dies at bit 9 | identical |

Every sampled word and every boot field matches 2407 bit for bit, before and
after, and the ladder is 2406's bytes exactly. `reset_raw` `0x200` with
`reset_completed` 0 is also unchanged: cleanup's reset, issued after the MCU was
started and halted, times out in both builds.

**What this rules out.** "The reset never really ran" is dead - it ran and
completed. And because a completed soft reset left `DBG_ENABLED` and every other
word untouched, bit 8 is not a runtime halt state inherited from LK/GPUEB: a
reset that clears the pipeline would have cleared it. It behaves like a static
strap. Note how thin the naming is - panthor calls bit 8 `GPU_STATUS_DBG_ENABLED`,
and r32p1's `mali_kbase_gpu_regmap_csf.h` does not name a single `GPU_STATUS` bit,
so the name is the only evidence for what it means.

**The bit-9 wall is therefore independent of the reset state.** It survived a
completed reset with no register moving, which is what a wall below the page table
and above DRAM looks like. The debug-state lead loses its mechanism and can be
dropped from the queue.

**A side observation, recorded because it explains the series.** The same sequence
completes before `MCU_CONTROL` and times out after the MCU has been started. Every
reset this project issued before 2408 went through the cleanup path, i.e. after
the MCU - so "the reset never completes" was a property of *when* it was asked,
not of the block.

**Next is 2409**, the out-of-arena page: map `0x0100D000` to a page outside the
2 MiB arena (framebuffer `0x9c000000` is the cheapest), then read `0x0100D200`
(VA and PA bit 9 = 1, not in the arena) and `0x0100D400` (bit 9 = 0). The word
returning means the dead set is allocation-shaped; hanging means it is
address-shaped.

Decode note: the kernel was still tagged `SWEET_BUILD_ID 0x2407`, because it was
not rebuilt for this trial, so the capture decodes as
`--build 0x2408 --mark 0x2407`. The image sha identifies the run.

## 62. 2409 built: the first access outside the arena, with the tag as a control

Every access that has ever stopped the MCU lies inside the 2 MiB arena
`[0x40078000, 0x40278000)`. "PA bit 9 has no responder" and "the second
512-byte half of this allocation has no responder" still fit every measurement,
and nothing in 2401..2408 separates them. 2409 asks the question where the two
answers differ: the same two 512-byte offsets of a page the arena does not back.

**Which page, and why that one.** `shim/board.c` derives the bootloader's splash
reservation from `/chosen` (`atag,videolfb-fb_base_l/_h`, `vramSize`) and
`cont_splash_region` is at `0x9c000000`. 2409 takes the **last two pages of that
reservation**, for four reasons and no others: it is DRAM the GPU arena does not
back; the panel is already scanning it, so it is powered and non-secure for the
CPU (our own console draws into it); `fb_size` exceeds `stride * height`, so the
last page lies past the visible frame and never reaches the screen; and the
address comes from the live tree rather than a constant, so a board that reports
something else fails the build closed instead of testing an unknown page.

**The tag is a controlled variable, not a detail.** The firmware tags every leaf
with memory group 6 (bits 59..62), and this series has never shown that group 6's
policy covers anything but the arena. ARM's PBHA documentation is explicit that
the meaning of those bits is implementation-defined, and that the *same* physical
page reached through mappings with different PBHA values has unpredictable
results - so the build must never alias one PA with two tags. 2409 therefore maps
two different pages, one untagged and one with the firmware's tag, and puts both
**control** reads before either bit-9 read:

| marker | read | page | tag | bit 9 |
|---|---|---|---|---|
| 1 | `0x0100D400` | ooa + 0x0000 | 0 | 0 |
| 2 | `0x0100C400` | ooa + 0x1000 | 6 | 0 |
| 3 | `0x0100D200` | ooa + 0x0000 | 0 | 1 |
| 4 | `0x0100C200` | ooa + 0x1000 | 6 | 1 |
| 5 | - | - | - | everything returned |

**How the leaf changes.** `sweet_csf_memory_remap_leaves()` walks the table the
builder just wrote, requires a valid leaf at the VA, replaces bits 47:12 with the
caller's PA and bits 59..62 with the caller's tag, and leaves AttrIdx, AP, SH, AF,
nG and XN exactly as the firmware's own leaf had them. It refuses an unaligned VA
or PA, a tag above 15, a PA outside `pa_bits`, a PA inside the arena, and a VA
with no valid leaf. It is a separate entry point and is compiled only for this
build: folding it into the builder changed every older build's object file, and
`2401..2408 still rebuild byte for byte` is a property this series relies on
(verified again: 2407 rebuilds to `c124e536...1781` after the change).

**Controls the run carries besides the markers.** The shim reads the same four
words with the CPU (MMU off, so the same physical words) and prints them as
`CSF ooa g0/g6`, then prints the four MCU result slots as `CSF b9 g0/g6`. The
leaf probe publishes the two live leaves, so the report shows PA, tag and the
untouched attribute bits for both pages; the decoder refuses the run as
`remap-not-applied` if they do not differ exactly that way.

**Build.** Image `0b35f105...a148` (26,714,112 B), payload `0ddae2ee...1dab`,
kernel `c01dcbea...d5ea` (unchanged, still tagged `0x2407`, so the capture decodes
with `--build 0x2409 --mark 0x2407`). The shim grew past one more page: arena
`0x40079000`, code section `0x401a6000` - different from 2407/2408, which is why
the decoder compares leaves and tag bits rather than absolute PAs. 303 tests, 3
skipped, including a new one that pins "PA and PBHA move, every other bit stays"
and the five refusal cases.

**Reading it.** Marker 1 alone means nothing outside the arena answers even
untagged - bit 9 was never asked, and the next step is SLC/MGM/GMPU coverage.
Marker 2 alone means the tag decides. Marker 3 means bit 9 is not arena-shaped:
a page the arena does not back still refuses its second 512-byte half. Marker 4
means the opposite of marker 3 - the untagged bit-9 read returned and the tagged
one did not. Marker 5 means the wall is a property of the arena allocation.

**Not flown.** `boot_a` is still `2931647a...86b1`.

## 63. 2409 and 2410 both failed to ask the question, and 2410 crashed the boot

Two flights, neither of which says anything about bit 9. They are recorded
together because the second one is a direct consequence of the first.

**2409: the target page was never a page.** `diag_flags` 127, `input_va` 1, the
MCU never returned the first read. The leaves show the remap did work -
`0x0100D000 -> 0x0000ffffd4c3` (tag 0) and `0x0100C000 ->
0x30000000ffffe4c3` (tag 6), PAs differing by exactly 0x1000 with attributes
`0x4c3` identical to `leaf_0x0100e000`. The PA came from
`brd.fb_base + brd.fb_size`, and on this board those are `matisse_defaults`:
`0xfcb3f000 + 0x034c0000 = 0xfffff000`, "the last page under 4 GiB". The ADT has
no `videolfb`, `vramSize` or `splash` property at all, so the value was never
device-derived. The MCU did not answer even at bit 9 = 0, which is a statement
about that address, not about the bit.

The decoder also lied, and that is fixed: `ooa_remap_observed` compared the two
leaves including bits 59..62, which this build varies on purpose, so a correctly
applied remap was reported as `remap-not-applied`. Comparison now masks PA and
tag (`keep = ~(page | 15 << 59)`); 2409's capture re-decodes as
`ooa_remap_observed: true`, `cold_boot_outcome: outside-arena-unreachable`.

**2410: the CPU read memory it does not own.** 2410 moved the target pages to a
page of the shim's own BSS and to `platform->firmware_memory + 0x1000`, the
20 MiB allocation LK leaves for the GPU. Its CPU witness read both. The boot
never published a report - `after-marks.bin` is byte-identical to
`before-marks.bin` and still holds 2409's content - reached fastboot at 73.41 s
against 85.4 s for 2408 (the twelve seconds of CSF timeout never happened), and
the phone reset at the REDMI logo.

The cause is in the source it was taken from. `mtk_gpueb_boot.c` reads that
address out of GPUEB register `0x1fd34` and says, in the same breath: *"Actual LK
stores extra firmware allocation PA>>12 at this register. It allocates 20 MiB;
never dereference or overwrite that allocation."* The shim runs with the MMU
off, so the witness load was a raw physical read of a carveout the CPU does not
own, issued before `sweet_csf_boot()`. Everything about the observation fits:
no report, no timeout, a reset before the kernel.

`boot_a` was restored to `2931647a...86b1` on both flights, the device returned
to Recovery, and the pstore entry left behind is from an older Android boot, so
no shim backtrace exists.

**2411 removes the page, not the question.** One remapped leaf
(`0x0100D000` -> a page of the shim's own BSS at `0x40279000`, one page past the
arena, tag 6) and one untouched leaf as an instrument control: `0x0100C000`
still walks the firmware's own mapping into the arena, so the ladder reads it
first and a stall at marker 1 indicts the image rather than the memory.

| marker | read | what it is | bit 9 |
|---|---|---|---|
| 1 | `0x0100C400` | firmware leaf into the arena, control | 0 |
| 2 | `0x0100D400` | page past the arena | 0 |
| 3 | `0x0100D200` | page past the arena | 1 |
| 4 | - | every access returned | - |

Marker 1 only: the instrument is dead and the run says nothing. Marker 2: a page
one past the arena is unreachable even at bit 9 = 0, so the wall is about which
physical pages the GPU may read at all. Marker 3: bit 9 is the address bit and
not this allocation. Marker 4: the wall is a property of the arena allocation.

Build: image `c8d0b033...b233`, payload `a72b45cc...9083`, kernel
`c01dcbea...d5ea`, arena `0x40078000`, code `0x401a5000`, 303 tests.
**Not flown** - 2410 already cost one boot, and the next flash is a separate
decision.

## 64. 2411: the first controlled answer - a write at bit 9 = 1 stalls too

2411 was built to ask whether a page past the arena answers. It answered a
different question first, and that answer is the cleanest one this series has
produced.

**What the ladder did.** Marker 1 was written, then the MCU read `0x0100C400` -
an untouched firmware leaf into the arena, tag 6, PA `0x401b1400` (bit 9 = 0).
It returned `0xb001500c`, which is exactly the word the firmware carries at VA
`0x0100C400` (container offset `0xd294`), and that word landed in `shared+0x0c`.
The next instruction stores the same word to `shared+0x200`, and marker 2 never
appears: `input_va` = 1, `mcu_status` = 1 (enabled, not halted).

**Why that is an answer and not a failure.** Between the word landing at
`shared+0x0c` and the missing marker there is exactly one memory access:

| access | address | bit 9 | outcome |
|---|---|---|---|
| result store | `0x0400000c` | 0 | landed |
| result store | `0x04000200` | 1 | never returned |

Same page, same mapping, same tag, same instruction, one address bit apart. So
the wall is not a read-side property: **a write at bit 9 = 1 stalls exactly like
a read**, and it does so in a third VA range (`0x04000000`, the shared section)
that has nothing to do with the code pages every earlier build probed.

It also explains a piece of the series' history. `2405`'s ladder contains that
same store as its marker 3 ("first write at bit 9 = 1"), and 2405 through 2408
all stopped at their read 2 before reaching it. 2411 is the first build that ever
executed it, and it behaved exactly as the bit-9 rule predicts.

**Two corrections to the record came out of this run.** The decoder rejected the
control leaf because it bounded the arena at 1 MiB; the arena is 2 MiB, and a
leaf at `0x401b1000` was called "not in the arena". It now uses 0x200000, and the
2411 capture re-decodes as `ooa_remap_observed: true`, `cold_boot_outcome:
write-at-bit9-stalled` - not `remap-not-applied`.

**2412 is 2411 minus that store.** One result word at `shared+0x0c` and no other
slot, because every extra slot is another chance to hang the core between two
markers for a reason that is not the question. Nothing else changes: the same
remapped leaf (`0x0100D000` -> `0x40279000`, tag 6), the same arena control leaf
at `0x0100C000`, the same three reads.

Build: image `333acd79...a3e72`, payload `156b7f6c...2e9d`, kernel
`c01dcbea...d5ea`, arena `0x40078000`, code `0x401a5000`, 303 tests. Runner
`shim2412-ooa4-trials-run-once.py`, partition hash `28a0b698...7fc1`.
**Not flown.**
