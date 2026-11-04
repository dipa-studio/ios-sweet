#ifndef SWEET_MTK_GPUFREQ_H
#define SWEET_MTK_GPUFREQ_H

#include <stddef.h>
#include <stdint.h>

/* MT6983 GPUEB gpufreq facts taken from the pinned vendor sources
 * (gpufreq_ipi.h, gpufreq_v2.c, gpufreq_mt6983.c, kbase-full-disasm.txt).
 * Independently written helpers: no allocator, no MMIO, no transport.
 *
 * A decoded value reports what GPUEB published into the shared-status
 * region we handed it in CMD_INIT. It does NOT prove that GPUEB flushed
 * that region, that the GPU is powered, or that the CSF MCU executed.
 * A region that decodes as invalid is inconclusive, never a failure.
 */
#define SWEET_GPUFREQ_MESSAGE_BYTES 32u
#define SWEET_GPUFREQ_STATUS_BYTES 0x400u
/* Only the head of the region is decoded; the rest is vendor-internal.
 * DECODE_BYTES is the span the decoder actually reads and therefore the
 * minimum buffer it accepts. */
#define SWEET_GPUFREQ_DECODE_WORDS 32u
#define SWEET_GPUFREQ_DECODE_BYTES 0x70u

/* Command IDs are shared with the power path; CMD_INIT(0) and CMD_POWER(6)
 * already live in mtk_gpueb_protocol.h and are intentionally duplicated
 * here only for the query/commit encoders. */
enum sweet_gpufreq_command {
    SWEET_GPUFREQ_CMD_GET_FREQ = 1u,
    SWEET_GPUFREQ_CMD_POWER = 6u,
    SWEET_GPUFREQ_CMD_COMMIT = 7u
};
enum sweet_gpufreq_target {
    SWEET_GPUFREQ_TARGET_DEFAULT = 0u,
    SWEET_GPUFREQ_TARGET_GPU = 1u,
    SWEET_GPUFREQ_TARGET_STACK = 2u
};
enum sweet_gpufreq_result {
    SWEET_GPUFREQ_OK = 0,
    SWEET_GPUFREQ_ARGUMENT = -1,
    SWEET_GPUFREQ_RANGE = -2
};

/* Sanity bounds. They reject a region that cannot be a real gpufreq status
 * (notably an all-zero or all-ones region) while still accepting every
 * plausible MT6983 value, so a genuine reading is never discarded. */
#define SWEET_GPUFREQ_MAX_OPP 64
#define SWEET_GPUFREQ_MAX_KHZ 2000000u
#define SWEET_GPUFREQ_MAX_UV 1200000u
#define SWEET_GPUFREQ_MAX_POWER_COUNT 8

/* Field offsets in struct gpufreq_shared_status. Every other member of the
 * vendor struct is deliberately not decoded: it is either debug-only or
 * has not been verified against this device. */
struct sweet_gpufreq_status {
    int32_t cur_oppidx_gpu;   /* 0x00, -1 when no OPP is selected */
    int32_t cur_oppidx_stack; /* 0x04 */
    int32_t opp_num_gpu;      /* 0x08, decoded-region discriminator */
    int32_t opp_num_stack;    /* 0x0c */
    uint32_t cur_fgpu;        /* 0x10 kHz; 0 means "not published" */
    uint32_t cur_fstack;      /* 0x14 kHz */
    uint32_t cur_vgpu;        /* 0x18 uV; 0 means "not published" */
    uint32_t cur_vstack;      /* 0x1c uV */
    uint32_t cur_vsram_gpu;   /* 0x20 uV */
    uint32_t power_control;   /* 0x60, 1 while the MFG rail is on */
    uint32_t dvfs_state;      /* 0x64, vendor enum, reported not gated */
    uint32_t shader_present;  /* 0x68 */
    int32_t power_count;      /* 0x6c, references GPUEB believes it holds */
};

/* Decodes the published status. Returns SWEET_GPUFREQ_OK and writes *out
 * only when the region looks like a real status; otherwise returns an
 * error and leaves *out untouched. */
int sweet_gpufreq_decode(const uint8_t *status, size_t bytes,
                         struct sweet_gpufreq_status *out);

/* CMD_COMMIT(target, oppidx): the second half of the vendor power-on
 * sequence. Applying it changes real frequency and voltage, so callers
 * must be explicit about it. */
int sweet_gpufreq_encode_commit(uint32_t target, int32_t oppidx,
                                uint8_t out[SWEET_GPUFREQ_MESSAGE_BYTES]);

/* CMD_GET_FREQ_BY_IDX(target, oppidx): read-only query whose MHz answer
 * comes back through the IPI response, which is coherent by construction
 * and therefore usable to cross-check the shared-status region. */
int sweet_gpufreq_encode_query(uint32_t command, uint32_t target,
                               int32_t oppidx,
                               uint8_t out[SWEET_GPUFREQ_MESSAGE_BYTES]);

#endif
