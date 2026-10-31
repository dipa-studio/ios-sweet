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
    /*2328 software build metadata, not hardware translation readback. */
    uint32_t pte_group_requested, pte_pages_built;
    /*2329: explicit0/1, select vendor's TRANSCFG INA=0. Zero preserves
     * the previous INA=7 sequence. Existing transcfg_lo records readback. */
    uint32_t vendor_ina0;
    /*2330: explicit0/1, use the pinned vendor cached byte88 in our
     * index1. Keep index0 shared byte4c and every PTE unchanged. */
    uint32_t vendor_cached_memattr;
    /*2331:0/1 opt-in original MT6983 platform snapshot. Reads only. */
    uint32_t platform_snapshot;
    /*2332:0/1 read-only AS0/L2 snapshot and pinned executable readback.
     * Offset names an owned arena page, never an arbitrary host address. */
    uint32_t access_snapshot, firmware_probe_offset, firmware_probe_va;
    uint32_t firmware_probe_expected;
    /*2333: check original MFG1 bus-protection masks before MCU AUTO. */
    uint32_t platform_path;
};
struct sweet_csf_platform_snapshot {
    uint32_t gpu_status, mcu_control, gpu_fault_status, gpu_fault_lo, gpu_fault_hi;
    uint32_t job_stat, spm_status, spm_status_second;
    uint32_t mfg_power0, mfg_power1, mfg_power2, mfg_power3;
    uint32_t mfg_pll_con1, mfgsc_pll_con1, topckgen_sel, rpc_slp_protect;
};
struct sweet_csf_access_snapshot {
    uint32_t mmu_raw, job_raw, as_status, as_fault, as_fault_lo, as_fault_hi;
    uint32_t l2_ready_lo, l2_ready_hi, l2_transition_lo, l2_transition_hi;
    uint32_t firmware_word0, version;
};
struct sweet_csf_path_snapshot {
    uint32_t rpc_enable, rpc_status, infra_enable, infra_status;
    uint32_t emi0_enable, emi0_status, emi1_enable, emi1_status;
    uint32_t pdc_cg, pdc_st0, pdc_st1, pdc_st2, pdc_st4, pdc_st5, pdc_st6;
    uint32_t slc_group6;
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
    /*2328 appends8 bytes (304 total). Canonical loader inputs/count only;
     * these do not prove memory routing or firmware execution. */
    uint32_t pte_group_requested, pte_pages_built;
    /*2331 appends136 bytes (440 total). Flags bit0 before AUTO,bit1
     * after wait/before cleanup. Values are observations,not readiness. */
    uint32_t platform_sample_flags, platform_reserved;
    struct sweet_csf_platform_snapshot platform_before, platform_after;
    /*2332 appends120 bytes (560 total), preserving the440-byte prefix.
     * Flags bit0 before AUTO,bit1 after wait; readback is not execution. */
    uint32_t access_sample_flags, access_reserved, firmware_probe_va;
    uint32_t firmware_probe_pa_lo, firmware_probe_pa_hi, firmware_probe_expected;
    struct sweet_csf_access_snapshot access_before, access_after;
    /*2333 appends136B;696B total. Exact MFG1 masks,not a whole-word zero test. */
    uint32_t path_sample_flags, path_reserved;
    struct sweet_csf_path_snapshot path_before, path_after;
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
