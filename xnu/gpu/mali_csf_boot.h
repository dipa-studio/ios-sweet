#ifndef SWEET_MALI_CSF_BOOT_H
#define SWEET_MALI_CSF_BOOT_H
#include "mtk_gpueb_boot.h"
#include "mali_csf_memory.h"

struct sweet_csf_boot_config {
    uint64_t gpu, root_pa, arena_pa, arena_bytes;
    uint32_t shared_offset, shared_bytes, timeout_ms;
    /* Optional pinned-blob diagnostics: arena page backing MCU0202c000.
     * Zero disables private probes. Never supplies an arbitrary host PA. */
    uint32_t private_probe_offset;
    /*2327 isolated diagnostic: select vendor's protocol NONE (31).
     * Zero preserves the previous boot sequence; only 0/1 are accepted. */
    uint32_t noncoherent;
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
    /*2325 appends exact mask readbacks and core state, 192 bytes total.
     * Flags bit2: pre-start core state; bit3: post-start core state.
     * Post-start capture replaces the core words when bit3 is set. */
    uint32_t gpu_irq_mask, mmu_irq_mask, as_present, irq_gate_passed;
    uint32_t shader_present_lo, shader_present_hi;
    uint32_t shader_transition_lo, shader_transition_hi;
    uint32_t shader_ready_lo, shader_ready_hi;
    uint32_t tiler_present_lo, tiler_present_hi;
    uint32_t tiler_transition_lo, tiler_transition_hi;
    uint32_t tiler_ready_lo, tiler_ready_hi;
    /*2326 appends evidence only, 288 bytes total. diag_flags: bit0 reset
     * register snapshot, bit1 programmed MEMATTR, bit2 memory before AUTO,
     * bit3 memory after AUTO, bit4 post-AUTO register snapshot. Memory
     * mutations never substitute for fresh IRQ/version readiness checks. */
    uint32_t diag_flags, coherency_features;
    uint32_t coherency_before, coherency_after;
    uint32_t csf_config_before, csf_config_after;
    uint32_t shader_config_before, shader_config_after;
    uint32_t tiler_config_before, tiler_config_after;
    uint32_t l2_mmu_config_before, l2_mmu_config_after;
    uint32_t memattr_lo, memattr_hi;
    uint32_t private_early_before, private_early_after;
    uint32_t private_feature_before, private_feature_after;
    uint32_t private_late_before, private_late_after;
    uint32_t shared_alloc_before, shared_alloc_after;
    uint32_t private_page_lo, private_page_hi;
    /*2327 appends 8 bytes (296 total). diag_flags bit5: protocol write
     * attempted; bit6: immediate readback matched. No readiness inference. */
    uint32_t coherency_requested, coherency_readback;
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
