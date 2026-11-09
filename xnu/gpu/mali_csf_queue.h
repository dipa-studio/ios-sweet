/* SPDX-License-Identifier: MIT */
#ifndef SWEET_MALI_CSF_QUEUE_H
#define SWEET_MALI_CSF_QUEUE_H
#include "mtk_gpueb_boot.h"
#include <stddef.h>

/* First CSF transport: one exclusively owned group/stream, synchronous submit.
 * The caller keeps the GPU powered and resets it before releasing any memory.
 * This is a queue-execution witness, not a shader/rendering implementation. */
/* CS_USER_INPUT/OUTPUT are MCU pointers. The MCU shared-region aperture is
 * [0x04000000,0x08000000), even when a page exists in the GPU page tables. */
#define SWEET_CSF_QUEUE_VA 0x06000000u
#define SWEET_CSF_QUEUE_BYTES 0x80000u
#define SWEET_CSF_QUEUE_TAG 0x2433c5f1u
#ifndef SWEET_CSF_COMPUTE_PROBE
#define SWEET_CSF_COMPUTE_PROBE 0
#endif
#define SWEET_CSF_COMPUTE_TAG 0x2436c5f1u
struct sweet_csf_queue_config {
    uint64_t gpu, root_pa, shared_pa, memory_pa;
    uint32_t shared_va, shared_bytes, input_va, output_va, memory_bytes;
    uint32_t timeout_ms;
    uint32_t reuse_as1;
};
struct sweet_csf_queue_report {
    uint32_t stage;
    int32_t error;
    uint32_t csg_req, csg_ack, cs_req, cs_ack, insert, extract;
    uint32_t before, after, fault, fatal, mmu_raw, as_fault;
    uint32_t cmd_lo, cmd_hi, suspend_bytes, streams, stop_ack, polls;
};
/* Add an owned noncacheable data region at QUEUE_VA before starting AS0.
 * Existing firmware leaves are unchanged. One new L3 table and data buffer
 * come from unused arena tail; the caller supplies the proven plan bounds. */
int sweet_csf_queue_memory(void *arena, size_t capacity, uint64_t arena_pa,
    uint32_t used, uint32_t table_pages, unsigned pa_bits, uint64_t *memory_pa);
int sweet_csf_queue_probe(const struct sweet_csf_queue_config *,
    const struct sweet_gpu_io *, struct sweet_csf_queue_report *);
#endif
