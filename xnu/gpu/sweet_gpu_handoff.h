/* SPDX-License-Identifier: MIT */
#ifndef SWEET_GPU_HANDOFF_H
#define SWEET_GPU_HANDOFF_H
#include <stdint.h>
#define SWEET_GPU_HANDOFF_MAGIC 0x53475055u
/* Owns one GPUEB power reference and the entire reserved shim arena. The
 * arena is outside the RAM window advertised to XNU. Polling owns the GPU;
 * interrupt masks are zero until the resident driver installs handlers. */
struct sweet_gpu_handoff {
    uint32_t magic, version, bytes, flags;
    uint64_t gpu, arena_pa, arena_bytes, root_pa, shared_pa, memory_pa;
    uint32_t shared_va, shared_bytes, input_va, output_va, memory_bytes;
    uint32_t reserved[3];
    uint64_t reserved64[4];
};
#endif
