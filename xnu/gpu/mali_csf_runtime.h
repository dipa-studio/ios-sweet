/* SPDX-License-Identifier: MIT */
#ifndef SWEET_MALI_CSF_RUNTIME_H
#define SWEET_MALI_CSF_RUNTIME_H
#include "mali_csf_queue.h"

/* Synchronous submissions, persistent CS registers/heap state. The owner
 * serializes these calls and retains every mapped page until stop succeeds.
 * Firmware (AS0) and application VMs map only the group's owned scratch.
 * Eight 64 KiB slots fit in the proven MCU shared-aperture allocation. */
#define SWEET_CSF_GROUPS 8u
#define SWEET_CSF_GROUP_BYTES 0x10000u
struct sweet_csf_runtime_group {
    uint64_t input, output, cs_input, cs_output, memory_pa, memory_va, insert;
    uint32_t slot, as_nr, sequence, active, failed;
};
int sweet_csf_runtime_bind(const struct sweet_csf_queue_config *,
    const struct sweet_gpu_io *, unsigned as_nr, uint64_t root_pa);
int sweet_csf_runtime_invalidate(const struct sweet_csf_queue_config *,
    const struct sweet_gpu_io *, unsigned as_nr);
int sweet_csf_runtime_start(const struct sweet_csf_queue_config *,
    const struct sweet_gpu_io *, struct sweet_csf_runtime_group *,
    unsigned slot, unsigned as_nr);
int sweet_csf_runtime_submit(const struct sweet_csf_queue_config *,
    const struct sweet_gpu_io *, struct sweet_csf_runtime_group *,
    uint64_t stream, uint32_t bytes, struct sweet_csf_queue_report *);
int sweet_csf_runtime_stop(const struct sweet_csf_queue_config *,
    const struct sweet_gpu_io *, struct sweet_csf_runtime_group *);
#endif
