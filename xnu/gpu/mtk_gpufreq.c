/* Facts sourced from the pinned vendor gpufreq sources; no vendor code is
 * copied. See docs/matisse-gpu-dvfs.md for the evidence boundary. */
#include "mtk_gpufreq.h"

static uint32_t le32(const uint8_t *p)
{
    return p[0] | ((uint32_t)p[1] << 8) | ((uint32_t)p[2] << 16) |
           ((uint32_t)p[3] << 24);
}

static int32_t le32s(const uint8_t *p)
{
    return (int32_t)le32(p);
}

static void put32(uint8_t *p, uint32_t value)
{
    p[0] = (uint8_t)value;
    p[1] = (uint8_t)(value >> 8);
    p[2] = (uint8_t)(value >> 16);
    p[3] = (uint8_t)(value >> 24);
}

static void zero(uint8_t *out)
{
    for (unsigned i = 0; i < SWEET_GPUFREQ_MESSAGE_BYTES; i++)
        out[i] = 0;
}

int sweet_gpufreq_decode(const uint8_t *status, size_t bytes,
                         struct sweet_gpufreq_status *out)
{
    struct sweet_gpufreq_status s;

    if (!status || !out)
        return SWEET_GPUFREQ_ARGUMENT;
    if (bytes < SWEET_GPUFREQ_DECODE_BYTES)
        return SWEET_GPUFREQ_RANGE;

    s.cur_oppidx_gpu = le32s(status + 0x00);
    s.cur_oppidx_stack = le32s(status + 0x04);
    s.opp_num_gpu = le32s(status + 0x08);
    s.opp_num_stack = le32s(status + 0x0c);
    s.cur_fgpu = le32(status + 0x10);
    s.cur_fstack = le32(status + 0x14);
    s.cur_vgpu = le32(status + 0x18);
    s.cur_vstack = le32(status + 0x1c);
    s.cur_vsram_gpu = le32(status + 0x20);
    s.power_control = le32(status + 0x60);
    s.dvfs_state = le32(status + 0x64);
    s.shader_present = le32(status + 0x68);
    s.power_count = le32s(status + 0x6c);

    /* Discriminators. An unwritten region is all-zero, so opp_num_gpu == 0
     * rejects it; an all-ones region fails the same test. */
    if (s.opp_num_gpu < 1 || s.opp_num_gpu > SWEET_GPUFREQ_MAX_OPP)
        return SWEET_GPUFREQ_RANGE;
    if (s.cur_oppidx_gpu < -1 || s.cur_oppidx_gpu >= s.opp_num_gpu)
        return SWEET_GPUFREQ_RANGE;
    if (s.power_count < 0 || s.power_count > SWEET_GPUFREQ_MAX_POWER_COUNT)
        return SWEET_GPUFREQ_RANGE;
    /* Upper bounds catch a saturated or corrupted region. Zero is accepted
     * on purpose: "0" means the firmware has not published a value yet,
     * which is itself the observation we want to record. */
    if (s.cur_fgpu > SWEET_GPUFREQ_MAX_KHZ)
        return SWEET_GPUFREQ_RANGE;
    if (s.cur_vgpu > SWEET_GPUFREQ_MAX_UV)
        return SWEET_GPUFREQ_RANGE;

    *out = s;
    return SWEET_GPUFREQ_OK;
}

int sweet_gpufreq_encode_commit(uint32_t target, int32_t oppidx,
                                uint8_t out[SWEET_GPUFREQ_MESSAGE_BYTES])
{
    if (!out)
        return SWEET_GPUFREQ_ARGUMENT;
    if (target > SWEET_GPUFREQ_TARGET_STACK)
        return SWEET_GPUFREQ_ARGUMENT;
    if (oppidx < 0 || oppidx >= SWEET_GPUFREQ_MAX_OPP)
        return SWEET_GPUFREQ_ARGUMENT;
    zero(out);
    put32(out, SWEET_GPUFREQ_CMD_COMMIT);
    put32(out + 4, target);
    put32(out + 8, (uint32_t)oppidx);
    return SWEET_GPUFREQ_OK;
}

int sweet_gpufreq_encode_query(uint32_t command, uint32_t target,
                               int32_t oppidx,
                               uint8_t out[SWEET_GPUFREQ_MESSAGE_BYTES])
{
    if (!out)
        return SWEET_GPUFREQ_ARGUMENT;
    if (command != SWEET_GPUFREQ_CMD_GET_FREQ)
        return SWEET_GPUFREQ_ARGUMENT;
    if (target > SWEET_GPUFREQ_TARGET_STACK)
        return SWEET_GPUFREQ_ARGUMENT;
    if (oppidx < 0 || oppidx >= SWEET_GPUFREQ_MAX_OPP)
        return SWEET_GPUFREQ_ARGUMENT;
    zero(out);
    put32(out, command);
    put32(out + 4, target);
    put32(out + 8, (uint32_t)oppidx);
    return SWEET_GPUFREQ_OK;
}
