#ifndef SWEET_MALI_CSF_MEMORY_H
#define SWEET_MALI_CSF_MEMORY_H
#include "mali_csf_firmware.h"

#define SWEET_CSF_MAX_SECTIONS 64u
#define SWEET_CSF_PAGE 4096u
/* MCU-only, 48-bit VA, 4 KiB stage-1 LPAE (level0 root). Firmware VAs
 * remain 32-bit. Two leaf encodings exist and only these bits differ:
 *   default:  cached -> AttrIndx1, other -> AttrIndx0, shared -> SH=3
 *   vendor:   cached -> AttrIndx0, other -> AttrIndx5, no SH bits anywhere
 * See SWEET_CSF_VENDOR_MEMATTR below. Host publishes its uncached arena
 * before GPU access. */
#define SWEET_CSF_VA_BITS 48u
/* r32p1 AS_MEMATTR, proven from the pinned mali_kbase_mt6983.ko:
 * kbase_mmu_get_as_setup (text0x47998) and mmu_update (text0x4708c) both
 * build 0x00084C8D888D8F88 with mov/movk chains, and
 * kbase_mmu_hw_configure stores that struct field to GPU+0x2408.
 * Bytes: [0]=88 outer-impl-def cached, [1]=8f outer-WA, [5]=4c non-cacheable,
 * [6]=08 shared. */
#define SWEET_CSF_VENDOR_MEMATTR_LO 0x888d8f88u
#define SWEET_CSF_VENDOR_MEMATTR_HI 0x00084c8du
/* 0 keeps the 2328..2379 leaf/register encoding byte-identical: cached leaves
 * select index1, everything else index0, the shared leaf carries SH=3, and
 * AS_MEMATTR is the 2330 diagnostic pair. 1 selects the vendor pairing that
 * mali_kbase_csf_firmware.c:convert_mem_flags() produces on a non-coherent
 * SoC: CACHE_MODE_CACHED -> index0, everything else (CACHED_COHERENT is
 * downgraded to NONE when system_coherency==NONE) -> index5 with no SH bits.
 * The selected attribute bytes are 0x88/0x4c either way; only the index
 * number, the SH bits and MEMATTR[0] change. */
#ifndef SWEET_CSF_VENDOR_MEMATTR
#define SWEET_CSF_VENDOR_MEMATTR 0
#endif
/* 0 keeps the 2328..2391 leaf encoding: bit11 (nG) is set on every leaf.
 * 1 clears it to match mali_kbase_mmu_mode_aarch64.c get_mmu_flags(), which
 * never sets bit11. 2393 uses this together with SWEET_CSF_VENDOR_MEMATTR=1
 * and read-only leaves to reproduce the vendor page attributes exactly. */
#ifndef SWEET_CSF_VENDOR_LEAVES
#define SWEET_CSF_VENDOR_LEAVES 0
#endif
/* 0 keeps the code section on whatever AttrIndx the selected pairing gives it.
 * 1 forces the R-X section (the only one the MCU fetches from) onto AS_MEMATTR
 * index 5, the non-cacheable byte, and clears its SH bits. 2395 uses it: the
 * bit-9 law measured across 2369-2394 says the stall is downstream of a
 * translation that reports no fault, and a cacheable access is the only kind
 * this port has ever issued to the code section, so cacheability is the first
 * lever that has never been pulled. 2393 gave the same section vendor index 0,
 * which convert_mem_flags() only reaches for CSF_FIRMWARE_CACHE_MODE_CACHED,
 * so it is not this experiment. */
#ifndef SWEET_CSF_UNCACHED_CODE
#define SWEET_CSF_UNCACHED_CODE 0
#endif
/* 0 leaves every page on its section's own execute permission. 2397 sets it to
 * one 4 KiB virtual address and forces only that page non-executable (PXN|UXN,
 * bits 54:53) whatever the section flags say. 2396 showed that a bit-9 read in
 * the shared and stack sections returns while the same read in the code section
 * stalls, so the property belongs to the target page being executable rather
 * than to the address. The page chosen is 0x01001000: it holds the read target
 * 0x01001200 and nothing the core executes, while the entry page 0x0100E000
 * keeps its X permission, so a read that returns names XN as the switch. A data
 * access does not normally consult XN - that is what makes the experiment worth
 * running on this part. */
#ifndef SWEET_CSF_XN_VA
#define SWEET_CSF_XN_VA 0
#endif
/* 0 leaves every page on its section's cache mode. Set to one 4 KiB virtual
 * address and only that page takes AS_MEMATTR index 5 (non-cacheable) with no
 * SH bits; the rest of the section, including the page the MCU starts on, keeps
 * its own. 2396 showed a cached bit-9 read stalls in the code window while the
 * cached stack page reads, 2399 moved the page underneath it and the read still
 * stalled, so the one leaf field never varied in the *data* direction at this
 * VA is cacheability: 2395 made the whole section non-cacheable but tested a
 * fetch landing, not this read. A read that returns here names the cacheable
 * fill as the wall; a read that still stalls says no data access to the code
 * window can complete, whatever the cache mode. */
#ifndef SWEET_CSF_UNCACHED_VA
#define SWEET_CSF_UNCACHED_VA 0
#endif
/* 0 leaves every leaf pointing at the page its own section placed there. Set
 * both to page-aligned virtual addresses inside the plan and the leaf at
 * SWEET_CSF_ALIAS_VA is repointed at the physical page that backs
 * SWEET_CSF_ALIAS_TO_VA, keeping every one of its own attribute bits: same VA,
 * same permissions, same cache mode, same section, different physical page.
 * 2399 uses 0x01001000 -> 0x02000000. 2396 read bit9 = 1 in the shared and
 * stack sections and stalled on it in the code section, 2397 exonerated XN and
 * 2398 exonerated the memory group, so the last structural split is which side
 * of the translation owns the stall. The target is the page the ladder's second
 * read already reads: offset 0x200 through either VA lands on the same physical
 * word, at PA bit 9 = 1, so the alias moves the virtual side and nothing else.
 * A read that returns says the wall follows the code section's physical pages
 * (move the firmware allocation); a read that still stalls, on a word the
 * previous read of the same boot just returned, says it follows the virtual
 * range and no mapping change can fix it. Diagnostic only, never a shipping
 * encoding. */
#ifndef SWEET_CSF_ALIAS_VA
#define SWEET_CSF_ALIAS_VA 0
#endif
#ifndef SWEET_CSF_ALIAS_TO_VA
#define SWEET_CSF_ALIAS_TO_VA 0
#endif
/* 0 keeps every build up to2380 byte-identical: each section's arena offset
 * follows the page tables in container order. 1 leaves every other section at
 * exactly that offset but appends the R-X section (VA0x01000000) after the
 * whole layout, so that one section gets a different PA while its VA, its leaf
 * attributes, its descriptor bits and every other section's PA stay unchanged.
 * 2382 uses this to ask whether the fetch hang follows the physical pages or
 * the virtual range. It is not a fix and must stay off in a shipping build. */
#ifndef SWEET_CSF_RELOCATE_CODE
#define SWEET_CSF_RELOCATE_CODE 0
#endif
/* 0 keeps every build through2400 byte-identical. Set to one page-aligned VA
 * and the plan appends a second mapping of the R-X section at that VA: same
 * size, flags and container bytes, its own copy of the data and its own L3
 * page. 2401 uses 0x03000000 (L2[24], a fresh L3 table page under the existing
 * scheme) while L2[8] stays the only table that backs 0x01000000. Diagnostic
 * only: the firmware runs from whichever VA the reset vector names. */
#ifndef SWEET_CSF_MIRROR_CODE_VA
#define SWEET_CSF_MIRROR_CODE_VA 0
#endif
/* 0 keeps every build through2400 byte-identical. Set to one page-aligned VA
 * in an unused L2 slot and the leaf builder copies the code section's L2 entry
 * into that slot after the tables are built. The alias VA then walks the same
 * L3 table page and the same leaf descriptor as 0x01000000, so a read through
 * it differs from the code read only by the VA. 2401 uses 0x05000000 (L2[40]).
 * Fails closed if the slot is already mapped or the code L3 page is absent. */
#ifndef SWEET_CSF_SHARE_CODE_L3_VA
#define SWEET_CSF_SHARE_CODE_L3_VA 0
#endif
struct sweet_csf_mapping {
    uint32_t va, bytes, flags, arena_offset, data_start, data_bytes;
};
struct sweet_csf_memory {
    uint32_t mapping_count, protected_skipped, table_pages, required_bytes;
    uint32_t shared_offset, shared_bytes, shared_va;
    uint32_t firmware_bytes;
    struct sweet_csf_mapping map[SWEET_CSF_MAX_SECTIONS];
};
enum sweet_csf_memory_error {
    SWEET_CSF_MEMORY_ARGUMENT = -40,
    SWEET_CSF_MEMORY_CAPACITY = -41,
    SWEET_CSF_MEMORY_PHYSICAL = -42
};
/* Atomic planning: out untouched on any failure, no allocation or MMIO. */
int sweet_csf_memory_plan(const uint8_t *, size_t, struct sweet_csf_memory *);
/* Re-validates the firmware and canonical plan before touching arena.
 * Arena, plan and firmware must be distinct; only required_bytes are written.
 * Returns root table PA. Caller owns/retains arena until GPU reset/off. */
int sweet_csf_memory_build(const uint8_t *, size_t, const struct sweet_csf_memory *,
    void *arena, size_t arena_bytes, uint64_t arena_pa, unsigned pa_bits,
    uint64_t *root_pa);
/* Isolated platform diagnostic: leaf bits59..62 carry a 4-bit memory-group
 * tag. Tables, PA, permissions and cache attributes are unchanged. Group0
 * is byte-identical to sweet_csf_memory_build. No routing/readiness claim. */
int sweet_csf_memory_build_group(const uint8_t *, size_t, const struct sweet_csf_memory *,
    void *arena, size_t arena_bytes, uint64_t arena_pa, unsigned pa_bits,
    unsigned memory_group, uint64_t *root_pa);
#endif
