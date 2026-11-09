# MT6983 MCU bring-up, 2026-11-09

This audit supersedes broad hardware conclusions in older trial narratives.
Raw source, device captures and images remain under ignored `research/`.

## Pinned reference implementations

- Linux: `7475ea8b58616b33c04afb976cf0fbaad9dd63fb`, nine Panthor files requested
  by the user, freshly downloaded by commit (the 2026-11-08 master snapshot
  in the older report was not immutable).
- Xiaomi rubens-s-oss: `270b84910b941bf75490fccdb5fb2b3021dd7cbf`.
- OnePlus `oneplus/mt6983_t_13.0_oneplus_ace_2v`:
  `ff51a39c66a87f91d870bfff1611e2b36371c8a4`.

Eight files are byte-identical across the selected Xiaomi/OnePlus commits:
MT6983 platform C/header, gpufreq_mt6983.c, L2/MMU config, CSF firmware header,
GPU register wrapper, AArch64 MMU encoder and protected allocator. Paths and
SHA256 hashes: `research/matisse/20261109-gpu-sources/sources.json`.

Concrete corrections from these sources:

1. AS_COMMAND is GPU+0x2418, AS_STATUS is +0x2428. The implementation was
   already correct; the earlier upstream audit table was wrong.
2. The vendor labels BOTH +0x8e0 and +0x900 clusters `R_dispatch_mode`.
   It does not document 0x055 as an eight-slot address map or the OUT cluster
   as the write channel. The 2419 readback establishes writable registers
   and an unchanged test outcome; it does not exclude the entire bridge.
3. Arch10 has an L2_CONFIG hash selector at bits31:24. The newer ASN_HASH
   coefficients at +0x2c0 are a different feature. Panthor's ASN configuration
   is explicitly gated to arch>=11. The original value 0x07130000 must not be
   described as an all-zero cache configuration.
4. r32p1 `mali_kbase_gpuprops.c` permits user hash selectors 8..15 for the
   older L2_CONFIG feature. `kbase_pm_l2_config_override()` programs this
   field before L2 power-on and preserves size and other fields.
5. GPUEB voltage numbers use 10 microvolt units: gpufreq divides regulator
   microvolts by 10 when reading and multiplies by 10 when programming.
   The previously reported 65000 means 650 mV, not 65 mV. These are published
   status values, not independent rail measurements.

## Trial 2420: CPU witness before cleanup

The MCU test uses no stack or literal pool. It writes/reads shared+0x400 as a
control, then writes/reads shared+0x200. Every checkpoint and data write has
a DSB. The CPU seeds both words before AUTO and reads both after the bounded
wait, before disable or reset can erase the evidence. The shared leaf selects
vendor MEMATTR index5 (non-cacheable). Existing 784-byte report ABI retained.

| Observation | Result |
|---|---|
| MCU checkpoint | 2: odd store/DSB has not completed |
| +0x400 CPU before / after | 0x24205400 / 0x2420a400 |
| +0x200 CPU before / after | 0x24205200 / 0x24205200 |
| Last MCU read result | 0x2420a400 (correct control) |
| MCU_STATUS / AS_FAULT | 1 / 0 |
| Fastboot arrival | 82.26 seconds |
| Full boot_a restored | 2931647a56039722ea2585990b8ef3b1a2daf4c9b990231879f753049eaf86b1 |

Image SHA256: e47c27d83f11bc4e32e1568759b7b6af8e781a85c3448f9eee3affa3501b7d39.
Kernel unchanged: c01dcbea...d5ea, persistent mark0x2407 (explicit decoder
`--mark 0x2407`), trial identity2420 from the image/manifest/console. Fresh
before/after marks differ. No CI kernel build was needed.

This contradicts “stores work, only read responses fail.” Earlier 2402/2404
did not prove store completion; the older report's section55 already explains
the instrumentation problems. It still does not prove a physical memory hole,
a broken GPU, or any particular interconnect mechanism.

## Trial 2421

Same witness/MCU program as2420, supported L2 hash selector8 instead of the
observed7; only bits31:24 changed before power-on, with readback. Built image:
8e31785b853a18e736d5898af06063042abac4600b0083aa381b7adeb9a6dc9f.
Hardware result: 0x07130000 -> 0x08130000 readback verified; marker2,
control visible, odd store absent. Fastboot87.45s; full boot_a restored to
2931647a56039722ea2585990b8ef3b1a2daf4c9b990231879f753049eaf86b1.
The hash override does not fix this witness.

## Trial 2422: relocate the complete arena

All page tables, firmware sections and shared backing move to an owned 2 MiB
zero-filled Image tail at0x45000000. Image.image_size covers the allocation,
and the stock fallback, ramdisk and signature bytes are checked unchanged.
The unused old BSS allocation and near-page mapping remain. MCU program and
memory attributes match2420; default L2 hash7 is restored by the next boot.

Image SHA256: d11fbb7ba449601d4eb476e3ea2cf57d68b3e070b70655f457f4c2a378c38d49.
AS root readback0x45000000, firmware PA0x4512d000, target PA0x45099200.
Marker2, control0x2420a400 visible, odd word remains0x24205200. MCU_STATUS1,
AS_FAULT0. Thus the symptom is reproducible at both arena locations; this
still does not identify a hardware defect or prove every RAM range fails.

Fastboot113.28s, fresh marks, full boot_a restored/verified to the same baseline.
122 tests pass (boot model, assembled/Unicorn ladder, fetch, evidence); kernel
c01dcbea...d5ea unchanged, no CI build. Runner and captures under
research/matisse/20261109-gpu/shim2422-far-arena*.

## Next measurement

Vendor gpufreq_mt6983.c:1316-1342 reads four EMI GALS slave debug words
(0x1021c82c/830, 0x1021e82c/830) and four M6/M7 idle controls. These have not
been measured in the existing MFG-top trials. Read them before and after the
MCU test and preserve CPU witness data. No bit decoding is claimed without
source evidence. Also,2408 already demonstrated pre-MCU soft-reset completion;
post-stall cleanup timeout must not be described as universal reset failure.


## Trial 2423: first successful controlled odd-slot store/read

This trial replaces the eight PDC/SLC observation slots with eight vendor
EMI/GALS/idle-register reads, keeping the MFG1 protection gate and complete
CPU witness. MCU bytecode and arena0x40078000 match2420. No EMI register is
written. Image c43e902e027a3e4f8eee17d1773eefae0a4969831f175f6266336d356b330e1a.

**Observed:** marker4, CPU control0x2420a400, CPU odd0x2420a200, output0x2420a200.
Both stores, DSBs and reads completed. This is diagnostic-program success,
not real firmware boot. Four GALS registers all read0x01007514 before/after;
north/south idle_en1 read0x10000618 and idle_en0 read0xc40000e8.

Fastboot96.66s; fresh marks; full boot_a restored and verified. 74 decoder
tests and the strict MMIO model pass. No CI/new XNU kernel.

Causality is not isolated: added reads, removed PDC reads, timing and run
variation are competing explanations. Repeat the image, then split the reads.
Do not conclude that an EMI register write is necessary: this trial writes none.


2423 repeat: same image, marker4 again, both stores visible, cleanup_error0 and
reset_completed1. Fastboot84.28s, full boot_a restored/verified.

## Trial 2424: retain the original PDC/SLC reads

Image afccc2206a36c7c710d237aba9de75ff412df5c62a3e619db79034c69e92fecc
adds all eight original PDC/SLC reads after the EMI reads; everything else
matches2423. Marker4, both CPU stores visible, output0x2420a200,
cleanup_error0/reset_completed1 again. EMI values match2423. Fastboot156.87s;
full boot_a restored/verified. Removing the original reads is not necessary
for the successful outcome. Added EMI reads versus delay remains unisolated.

2425 is prepared/running with the unmodified vendor firmware, vendor leaves
and EMI reads, no diagnostic shared writes or remaps. Arena0x40077000;
firmware hash de22d2fc...7229a unchanged. Image
 a1fa8065544fa2b5c1f7bbc06288670a2a98ddb09ca60c960fb2f47b9f07c58f.
Hardware outcome pending; no CSF firmware boot claim yet.
