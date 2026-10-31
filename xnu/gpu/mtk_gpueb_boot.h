#ifndef SWEET_MTK_GPUEB_BOOT_H
#define SWEET_MTK_GPUEB_BOOT_H
#include <stdint.h>
#include "mtk_gpueb_protocol.h"

/* Independently written, single-owner MT6983 bring-up transaction. The
 * callbacks permit deterministic host replay; they are not Linux APIs.
 * This performs platform power plus a GPU soft reset, NOT CSF firmware
 * boot, shader execution, or a usable graphics driver. */
struct sweet_gpu_io {
    void *context;
    uint32_t (*read32)(void *, uint64_t);
    void (*write32)(void *, uint64_t, uint32_t);
    uint64_t (*ticks)(void *);
    void (*barrier)(void *);
    uint64_t frequency;
};
struct sweet_gpu_boot_config {
    uint64_t mailbox, irq_set, irq_clear, tx_status, rx_status;
    uint64_t gpu, gpueb, sleep, shared_base, shared_bytes;
    uint64_t xnu_base, xnu_bytes;
    struct sweet_gpueb_shared layout;
    uint32_t boot_mode, tx_offset, rx_offset, channel, timeout_ms;
    /* Optional synchronous diagnostic while the exclusive power reference
     * is held after reset. Default NULL preserves power/reset-only builds. */
    int (*powered_probe)(void *, const struct sweet_gpu_io *, uint64_t);
    void *probe_context;
};
enum sweet_gpu_stage {
    SWEET_GPU_CONFIG = 1, SWEET_GPU_POWER_DOMAIN = 2,
    SWEET_GPU_FIRMWARE = 3, SWEET_GPU_MEMORY = 4,
    SWEET_GPU_INIT = 5, SWEET_GPU_ON = 6, SWEET_GPU_ID = 7,
    SWEET_GPU_RESET = 8, SWEET_GPU_OFF = 9, SWEET_GPU_COMPLETE = 10
};
enum sweet_gpu_error {
    SWEET_GPU_ARGUMENT = -20, SWEET_GPU_HANDOFF = -21,
    SWEET_GPU_OVERLAP = -22, SWEET_GPU_TIMEOUT = -23,
    SWEET_GPU_STALE = -24, SWEET_GPU_REPLY = -25,
    SWEET_GPU_OWNER = -26, SWEET_GPU_UNPOWERED = -27,
    SWEET_GPU_MODEL = -28
};
struct sweet_gpu_boot_report {
    uint32_t stage;
    int32_t error, init_result, on_result, off_result;
    uint32_t spm_before, spm_after, spm_second, firmware_magic;
    uint32_t gpu_id, gpu_status, reset_rawstat, as_present;
    uint64_t firmware_memory;
    uint32_t power_acquired, cleanup_attempted;
};
int sweet_gpu_boot(const struct sweet_gpu_boot_config *,
                   const struct sweet_gpu_io *, struct sweet_gpu_boot_report *);
#endif
