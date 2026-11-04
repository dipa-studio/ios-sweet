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
    /* Second half of the vendor power-on sequence: gpufreq_commit after
     * gpufreq_power_control. Zero leaves the region untouched, matching the
     * powered_probe convention, so a zero-initialised config never sends a
     * commit. When set, dvfs_commit_opp is -1 for "the index GPUEB already
     * reports" (exercises the command path without moving frequency) or an
     * exact index to commit. */
    uint32_t dvfs_commit;
    int32_t dvfs_commit_opp;
    /* Optional synchronous diagnostic while the exclusive power reference
     * is held after reset. Default NULL preserves power/reset-only builds. */
    int (*powered_probe)(void *, const struct sweet_gpu_io *, uint64_t);
    void *probe_context;
};
enum sweet_gpu_stage {
    SWEET_GPU_CONFIG = 1, SWEET_GPU_POWER_DOMAIN = 2,
    SWEET_GPU_FIRMWARE = 3, SWEET_GPU_MEMORY = 4,
    SWEET_GPU_INIT = 5, SWEET_GPU_ON = 6, SWEET_GPU_ID = 7,
    SWEET_GPU_RESET = 8, SWEET_GPU_OFF = 9, SWEET_GPU_COMPLETE = 10,
    /* 2338 appends this value; earlier stage numbers are unchanged. */
    SWEET_GPU_DVFS = 11
};
enum sweet_gpu_error {
    SWEET_GPU_ARGUMENT = -20, SWEET_GPU_HANDOFF = -21,
    SWEET_GPU_OVERLAP = -22, SWEET_GPU_TIMEOUT = -23,
    SWEET_GPU_STALE = -24, SWEET_GPU_REPLY = -25,
    SWEET_GPU_OWNER = -26, SWEET_GPU_UNPOWERED = -27,
    SWEET_GPU_MODEL = -28,
    /* 2338: an accepted CMD_COMMIT did not move the reported OPP index. */
    SWEET_GPU_FREQUENCY = -29
};
struct sweet_gpu_boot_report {
    uint32_t stage;
    int32_t error, init_result, on_result, off_result;
    uint32_t spm_before, spm_after, spm_second, firmware_magic;
    uint32_t gpu_id, gpu_status, reset_rawstat, as_present;
    uint64_t firmware_memory;
    uint32_t power_acquired, cleanup_attempted;
    /* 2338 appends 40 bytes; the ADT slot stays 128 and the CSF report is
     * untouched. These are read back from the gpufreq shared-status region
     * GPUEB was given in CMD_INIT: they report what the firmware published,
     * not what we commanded. An undecodable region is inconclusive, never
     * proof that the GPU is unpowered. */
    uint32_t gpufreq_valid; /* bit0 baseline, bit1 after POWER_ON,
                             * bit2 IPI cross-check agreed, bit3 commit
                             * verified by a second sample */
    int32_t gpufreq_oppidx;
    int32_t gpufreq_power_count;
    uint32_t gpufreq_opp_num;
    uint32_t gpufreq_freq_khz; /* 0 means "not published yet" */
    uint32_t gpufreq_volt_uv;  /* 0 means "not published yet" */
    uint32_t gpufreq_vsram_uv;
    uint32_t gpufreq_dvfs_state;
    uint32_t gpufreq_power_ctrl;
    int32_t gpufreq_commit_result; /* INT32_MIN when not attempted */
};
int sweet_gpu_boot(const struct sweet_gpu_boot_config *,
                   const struct sweet_gpu_io *, struct sweet_gpu_boot_report *);
#endif
