#ifndef SWEET_MALI_CSF_BOOT_H
#define SWEET_MALI_CSF_BOOT_H
#include "mtk_gpueb_boot.h"
#include "mali_csf_memory.h"

struct sweet_csf_boot_config {
    uint64_t gpu, root_pa, arena_pa, arena_bytes;
    uint32_t shared_offset, shared_bytes, timeout_ms;
};
struct sweet_csf_boot_report {
    uint32_t stage;
    int32_t error, cleanup_error;
    uint32_t mmu_features, l2_present, l2_present_hi, l2_ready, mcu_status;
    uint32_t job_raw, mmu_raw, as_fault, as_fault_lo, as_fault_hi;
    uint32_t version, features, input_va, output_va, groups, group_stride;
    uint32_t reset_raw, firmware_ready, reset_completed;
    /* Appended2323 ABI. Flags bit0: pre-start version sampled; bit1:
     * post-start shared fields sampled. Sampling alone never proves ready. */
    uint32_t sample_flags, gpu_raw, as_status, transcfg_lo;
    uint32_t transtab_lo, transtab_hi, disable_status;
    int32_t disable_error;
    /*2323 reserved this word as zero;2324 records JOB_INT_MASK readback. */
    uint32_t version_before, job_irq_mask;
};
enum sweet_csf_boot_stage {
    SWEET_CSF_BOOT_CONFIG=1, SWEET_CSF_BOOT_L2=2, SWEET_CSF_BOOT_AS=3,
    SWEET_CSF_BOOT_MCU=4, SWEET_CSF_BOOT_IFACE=5, SWEET_CSF_BOOT_CLEANUP=6,
    SWEET_CSF_BOOT_COMPLETE=7
};
enum sweet_csf_boot_error {
    SWEET_CSF_BOOT_ARGUMENT=-50, SWEET_CSF_BOOT_MODEL=-51,
    SWEET_CSF_BOOT_STATE=-52, SWEET_CSF_BOOT_TIMEOUT=-53,
    SWEET_CSF_BOOT_FAULT=-54, SWEET_CSF_BOOT_INTERFACE=-55
};
/* Called ONLY while the caller owns exactly one powered/reset GPU reference.
 * Uses polled raw IRQs with internal enables; GIC routing is untouched.
 * Always attempts soft reset
 * before returning, including failure paths. arena must survive until caller
 * powers off/reset completes. Never treats a nonzero preloaded version as
 * firmware-ready without the MCU's fresh global-interface interrupt. */
int sweet_csf_boot(const struct sweet_csf_boot_config *, const struct sweet_gpu_io *,
    struct sweet_csf_boot_report *);
#endif
