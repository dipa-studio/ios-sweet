/* SPDX-License-Identifier: MIT
 * Darwin transport for Mesa's Panthor backend. Calls are synchronous: a
 * successful SUBMIT means its GPU fence and extract pointer both completed. */
#ifndef SWEET_GPU_USER_H
#define SWEET_GPU_USER_H
#include <stdint.h>
enum {
    SWEET_GPU_INFO=16, SWEET_GPU_BO_CREATE, SWEET_GPU_BO_CLOSE,
    SWEET_GPU_VM_MAP, SWEET_GPU_GROUP_CREATE, SWEET_GPU_GROUP_CLOSE,
    SWEET_GPU_SUBMIT, SWEET_GPU_SURFACE
};
struct sweet_gpu_info { uint32_t version, gpu[26], cs[6]; };
struct sweet_gpu_bo { uint64_t size; uint32_t handle, flags; };
/* flags: Panthor READONLY=1, NOEXEC=2, UNCACHED=4; UNMAP=1<<28. */
struct sweet_gpu_map { uint32_t handle, flags; uint64_t offset, va, size; };
struct sweet_gpu_group { uint32_t handle, pad; };
struct sweet_gpu_submit { uint32_t group, bytes; uint64_t stream, sequence; };
struct sweet_gpu_surface {
    /* handle=0: query layout only; UINT32_MAX: import/reuse backing BO. */
    uint32_t surface, handle;
    uint64_t size;
    uint32_t offset, row_bytes, width, height, pixel_format, planes;
};
#endif
