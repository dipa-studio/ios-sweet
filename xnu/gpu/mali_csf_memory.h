#ifndef SWEET_MALI_CSF_MEMORY_H
#define SWEET_MALI_CSF_MEMORY_H
#include "mali_csf_firmware.h"

#define SWEET_CSF_MAX_SECTIONS 64u
#define SWEET_CSF_PAGE 4096u
/* MCU-only, 32-bit VA, 4 KiB stage-1 LPAE. Data and page walks are
 * non-cacheable; the host must publish the arena before GPU access. */
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
#endif
