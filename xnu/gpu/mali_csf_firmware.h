#ifndef SWEET_MALI_CSF_FIRMWARE_H
#define SWEET_MALI_CSF_FIRMWARE_H

#include <stddef.h>
#include <stdint.h>

/* Portable static parser; no MMIO, allocation, firmware execution or kernel hooks.
 * Device reference: MT6983 Linux 5.10 mali-r32p1/mali_kbase_csf_firmware.c
 * and its GPUEB/gpufreq modules. Mainline panthor is a historical ABI
 * cross-check, not the driver that boots this phone's firmware.
 * Firmware header version/hash are NOT the runtime GLB_VERSION interface ABI.
 */
enum sweet_csf_result {
    SWEET_CSF_OK = 0,
    SWEET_CSF_BAD_ARGUMENT = -1,
    SWEET_CSF_TRUNCATED = -2,
    SWEET_CSF_BAD_HEADER = -3,
    SWEET_CSF_BAD_ENTRY = -4,
    SWEET_CSF_BAD_SECTION = -5,
    SWEET_CSF_NO_SHARED = -6,
    SWEET_CSF_UNSUPPORTED_ENTRY = -7,
    SWEET_CSF_CALLBACK_FAILED = -8,
    SWEET_CSF_OVERLAPPING_SECTION = -9
};

struct sweet_csf_section {
    uint32_t flags;
    uint32_t va_start;
    uint32_t va_end;
    uint32_t data_start;
    uint32_t data_end;
    /* Name points into caller-owned firmware; bounded, may include NUL padding. */
    const uint8_t *name;
    size_t name_bytes;
};

struct sweet_csf_layout {
    uint32_t format_hash;
    uint32_t table_end;
    uint32_t entries;
    uint32_t sections;
    uint32_t protected_sections;
    uint32_t non_16k_sections;
    uint32_t shared_va;
    uint32_t shared_bytes;
    uint8_t format_major;
    uint8_t format_minor;
};

typedef int (*sweet_csf_section_fn)(const struct sweet_csf_section *, void *);

/* Validate the entire container before invoking callbacks. On validation error,
 * out and callbacks are untouched. On callback error, callbacks already issued
 * are not undone; caller must clean up. out is published only on success.
 * A successful parse proves structural validity only, not GPU compatibility,
 * authenticity or permission to distribute the caller-supplied blob.
 */
int sweet_csf_parse(const uint8_t *data, size_t bytes,
                    struct sweet_csf_layout *out,
                    sweet_csf_section_fn callback, void *context);

#endif
