#ifndef SWEET_MALI_CSF_BOOT_H
#define SWEET_MALI_CSF_BOOT_H
#include "mtk_gpueb_boot.h"
#include "mali_csf_memory.h"

/*2413: MTK's "MFG top" block, the SoC side of the GPU that panthor never
 *touches. The vendor kernel programs it on every power-on
 *(gpufreq_mt6983.c __gpufreq_acp_control / __gpufreq_slc_control); the DDK
 *assumes the platform already did, so a shim that powers the GPU itself
 *starts the MCU on a block whose AXI dispatch and SLC policy are whatever
 *the bootloader left. One 4 KiB page holds every register used here.
 *Only compiled in when SWEET_CSF_MFG_GLUE is1; zero keeps older builds
 *byte-identical. */
#define SWEET_CSF_MFG_BASE 0x13fbf000u
/*0 = do not touch the page, 1 = vendor values (2413), 2 = perturb (2414). */
#ifndef SWEET_CSF_MFG_GLUE
#define SWEET_CSF_MFG_GLUE 0
#endif

struct sweet_csf_global_evidence;
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
    /*2335:0/1 read a distinct checkpoint word at shared+0xffc before AUTO
     * and after the wait,before cleanup. Never changes interface version. */
    uint32_t entry_checkpoint;
    /*2372: value written to MCU_CONTROL to start the MCU.0 selects AUTO
     * alone(2), the measured-good value on this SoC;3 is the vendor
     * ENABLE|AUTO form, which2372 measured as leaving MCU_STATUS at0 for the
     * whole budget. Only0,2,3 are accepted so a trial moves one number.
     * The written/readback pair is recorded in platform_reserved. */
    uint32_t mcu_control_value;
    /*2381: firmware shared-section VA. The CSF global interface lives inside
     * that section and is addressed by VA, so the input/output pages can only
     * be converted to arena offsets when the section base is known. */
    uint32_t shared_va;
    /*2381:0/1 program the post-boot global interface (input page + kernel
     * doorbell + GLB_ACK). Zero preserves every build up to2380: not a single
     * additional MMIO access is issued. Requires global_evidence. */
    uint32_t global_init;
    struct sweet_csf_global_evidence *global_evidence;
};
/*2381 evidence, published through a separate ADT property so the 696-byte
 * report ABI is byte-identical. 24 words = 96 bytes = 12 SWEETMRK records;
 * the kernel mark table is 160 entries and already holds about119, so this
 * block must never grow past 12 records. flags: bit0 input page programmed,
 * bit1 doorbell rung, bit2 ACK matched, bit3 ABORTED before any write. */
struct sweet_csf_global_evidence {
    uint32_t flags;
    int32_t error;
    uint32_t input_va, output_va;
    uint32_t input_pa_lo, input_pa_hi, output_pa_lo, output_pa_hi;
    uint32_t req_before, ack_before;
    uint32_t protm_coherency, alloc_en_lo, alloc_en_hi;
    uint32_t pwroff_timer, progress_timer, idle_timer, ack_irq_mask;
    uint32_t req_written, ack_first, ack_last;
    uint32_t polls, req_mask, ack_matched, doorbell_value;
};
#if defined(__STDC_VERSION__) && __STDC_VERSION__ >= 201112L
_Static_assert(sizeof(struct sweet_csf_global_evidence)==96,
    "sweet-csf-global must stay 12 SWEETMRK records");
#endif
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
/*2407 samples the GPU register words that could explain a PA bit-9 wall: the
 *ID/config cluster at0x000..0x04c and the0x2c0 block the vendor KMD dumps.
 *Raw offsets only - naming bits nobody documented is how a sample turns into an
 *assumption. Guarded so every earlier build still compiles to its old size. */
#if SWEET_CSF_GPU_REGS
struct sweet_csf_gpu_regs {
    uint32_t reg_000, reg_004, reg_00c, reg_034, reg_048;
    uint32_t reg_04c, reg_2c0, reg_2c4, reg_2c8, reg_2cc;
};
#endif
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
     * mutations never substitute for fresh IRQ/version readiness checks.
     *2408 adds, only when SWEET_CSF_PRESTART_RESET is built in: bit7 the
     * pre-start soft reset was issued, bit8 its RESET_COMPLETED arrived,
     * bit9 GPU_STATUS.DBG_ENABLED was set before it, bit10 still set after.
     *2413 adds, only when SWEET_CSF_MFG_GLUE == 1 is built in: bit11 the SoC-side
     * MFG glue was written before MCU_CONTROL - AXCOHERENCE |= 0xF, the eight
     * AXI 1-to-2 read-dispatch words and group 6's SLC policy, in the vendor's
     * own order.
     *2414 uses SWEET_CSF_MFG_GLUE == 2 instead: the same block, but the four
     * in-dispatch words are set to 0xAAA rather than the vendor's 0x855, so the
     * treatment cannot be a silent no-op. Bits12/13/14 then say that the
     * in-dispatch, out-dispatch and group 6 words already held the vendor value
     * before the write; bit11 still says the block ran.
     *Bits7..14 are zero on every build that does not do this. */
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
    /*2331 header word. 2372 repurposes the reserved word: bits15..8 hold the
     * value written to MCU_CONTROL, bits7..0 the byte read back immediately
     * afterwards. Zero on every build before2372. */
    uint32_t platform_sample_flags, platform_reserved;
    struct sweet_csf_platform_snapshot platform_before, platform_after;
    /*2332 appends120 bytes (560 total), preserving the440-byte prefix.
     * Flags bit0 before AUTO,bit1 after wait; readback is not execution. */
    /*2335 reuses access_reserved for checkpoint-before and path_reserved
     * for checkpoint-after;older builds retain reserved-zero semantics. */
    uint32_t access_sample_flags, access_reserved, firmware_probe_va;
    uint32_t firmware_probe_pa_lo, firmware_probe_pa_hi, firmware_probe_expected;
    struct sweet_csf_access_snapshot access_before, access_after;
    /*2333 appends136B;696B total. Exact MFG1 masks,not a whole-word zero test. */
    uint32_t path_sample_flags, path_reserved;
    struct sweet_csf_path_snapshot path_before, path_after;
#if SWEET_CSF_GPU_REGS
    /*2407 appends88B;784B total. 0x048 is the L2 config the dual-slice
     *hypothesis hangs on; the0x2c0 words are what the vendor dump reads next
     *to it. Flags bit0 before MCU_CONTROL, bit1 after the experiment. */
    uint32_t gpu_regs_flags, gpu_regs_reserved;
    struct sweet_csf_gpu_regs gpu_regs_before, gpu_regs_after;
#endif
};
enum sweet_csf_boot_stage {
    SWEET_CSF_BOOT_CONFIG=1, SWEET_CSF_BOOT_L2=2, SWEET_CSF_BOOT_AS=3,
    SWEET_CSF_BOOT_MCU=4, SWEET_CSF_BOOT_IFACE=5, SWEET_CSF_BOOT_CLEANUP=6,
    SWEET_CSF_BOOT_COMPLETE=7,
    /*2372: stop between the platform assertions and the start write, i.e. the
     * MCU did not return to a halt state we could measure. Earlier builds
     * never reported this stage. */
    SWEET_CSF_BOOT_HALT=8,
    /*2381: firmware reported ready and the global input page is being
     * programmed, or the kernel doorbell has been rung and GLB_ACK is being
     * polled. A successful transaction still finishes at COMPLETE(7), so the
     * existing decoder readiness rule is unchanged. */
    SWEET_CSF_BOOT_GLOBAL=9, SWEET_CSF_BOOT_GLOBAL_ACK=10
};
enum sweet_csf_boot_error {
    SWEET_CSF_BOOT_ARGUMENT=-50, SWEET_CSF_BOOT_MODEL=-51,
    SWEET_CSF_BOOT_STATE=-52, SWEET_CSF_BOOT_TIMEOUT=-53,
    SWEET_CSF_BOOT_FAULT=-54, SWEET_CSF_BOOT_INTERFACE=-55
};
/* 0 keeps every build up to2380 identical. 1 additionally programs the global
 * interface after the firmware reports ready, i.e. the step
 * kbase_csf_firmware_r32p1's global_init_on_boot() performs. */
#ifndef SWEET_CSF_GLOBAL_INIT
#define SWEET_CSF_GLOBAL_INIT 0
#endif
/* 2405 only. Seed the firmware's shared output slot with a word no code path
 * writes, so the report can tell "the core stored a read result" from "the
 * core died before the store". 2404 printed 0x04003000 out of that slot with a
 * ladder that never writes it - the arena arrives uninitialised - and the value
 * was read as a data result it never was. 0 keeps every earlier build byte
 * identical. */
#ifndef SWEET_CSF_SHARED_SENTINEL
#define SWEET_CSF_SHARED_SENTINEL 0
#endif
/*2407: sample the GPU ID/config block and the0x2c0 words. 0 keeps every earlier
 *build byte identical, which is how the 2404/2406 rebuild checks stay honest. */
#ifndef SWEET_CSF_GPU_REGS
#define SWEET_CSF_GPU_REGS 0
#endif
#define SWEET_CSF_SHARED_SENTINEL_WORD 0xdeadbeefu
/* Called ONLY while the caller owns exactly one powered/reset GPU reference.
 * Uses polled raw IRQs with internal enables; GIC routing is untouched.
 * Always attempts soft reset
 * before returning, including failure paths. arena must survive until caller
 * powers off/reset completes. Never treats a nonzero preloaded version as
 * firmware-ready without the MCU's fresh global-interface interrupt. */
int sweet_csf_boot(const struct sweet_csf_boot_config *, const struct sweet_gpu_io *,
    struct sweet_csf_boot_report *);
#endif
