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
