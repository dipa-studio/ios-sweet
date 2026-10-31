/* MT6983 register/protocol facts: live DT, actual modified LK and vendor
 * wrapper. No vendor implementation is incorporated. See
 * docs/matisse-gpu-shim.md for exact evidence and the test boundary. */
#include "mtk_gpueb_boot.h"

static int range(uint64_t base, uint64_t bytes)
{
    return bytes && base <= UINT64_MAX - bytes;
}
static int overlap(uint64_t a, uint64_t n, uint64_t b, uint64_t m)
{
    return a < b + m && b < a + n;
}
static uint32_t rd(const struct sweet_gpu_io *io, uint64_t p)
{
    return io->read32(io->context, p);
}
static void wr(const struct sweet_gpu_io *io, uint64_t p, uint32_t v)
{
    io->write32(io->context, p, v);
    io->barrier(io->context);
}
static int wait_bits(const struct sweet_gpu_io *io, uint64_t p,
                     uint32_t mask, uint32_t value, uint64_t budget)
{
    uint64_t start = io->ticks(io->context);
    /* The iteration bound also terminates a stopped architectural timer. */
    for (uint32_t i = 0; i < 10000000; i++) {
        if ((rd(io, p) & mask) == value)
            return 0;
        if (io->ticks(io->context) - start >= budget)
            break;
    }
    return SWEET_GPU_TIMEOUT;
}
static uint32_t le32(const uint8_t *p)
{
    return p[0] | ((uint32_t)p[1] << 8) | ((uint32_t)p[2] << 16) |
           ((uint32_t)p[3] << 24);
}
static int request(const struct sweet_gpu_boot_config *c,
                   const struct sweet_gpu_io *io, const uint8_t *message,
                   uint32_t command, uint64_t budget, int32_t *result)
{
    uint32_t bit = 1u << c->channel;
    uint8_t reply[32];
    int rc = wait_bits(io, c->tx_status, bit, 0, budget);
    if (rc)
        return rc;
    /* A response already present has unknown ownership. Do not drain it
     * and mistake it for our completion, and do not retry a timed-out IPI. */
    if (rd(io, c->rx_status) & bit)
        return SWEET_GPU_STALE;
    for (unsigned i = 0; i < 8; i++)
        wr(io, c->mailbox + c->tx_offset + 4 * i, le32(message + 4 * i));
    wr(io, c->irq_set, bit);
    rc = wait_bits(io, c->rx_status, bit, bit, budget);
    if (rc)
        return rc;
    io->barrier(io->context);
    /* Hardware ABI acknowledges the receive pin before copying its slot.
     * No other request can overwrite it in this single-owner caller. */
    wr(io, c->irq_clear, bit);
    for (unsigned i = 0; i < 8; i++) {
        uint32_t v = rd(io, c->mailbox + c->rx_offset + 4 * i);
        for (unsigned j = 0; j < 4; j++)
            reply[4 * i + j] = (uint8_t)(v >> (8 * j));
    }
    if (sweet_gpueb_decode_response(reply, sizeof(reply), command, result))
        return SWEET_GPU_REPLY;
    return 0;
}

int sweet_gpu_boot(const struct sweet_gpu_boot_config *c,
                   const struct sweet_gpu_io *io, struct sweet_gpu_boot_report *r)
{
    uint8_t message[32];
    uint64_t budget;
    uint32_t saved_mask = 0;
    int rc;
    if (!r)
        return SWEET_GPU_ARGUMENT;
    *r = (struct sweet_gpu_boot_report){ .stage = SWEET_GPU_CONFIG,
        .init_result = INT32_MIN, .on_result = INT32_MIN, .off_result = INT32_MIN };
    if (!c || !io || !io->read32 || !io->write32 || !io->ticks ||
        !io->barrier || !io->frequency || io->frequency > 1000000000 ||
        !c->timeout_ms || c->timeout_ms > 1000 ||
        c->boot_mode != 0 || c->gpu != 0x13000000 || c->gpueb != 0x13c40000 ||
        c->sleep != 0x1c001000 || c->mailbox != 0x13c5fd80 ||
        c->irq_set != 0x13c62004 || c->irq_clear != 0x13c62074 ||
        c->tx_status != 0x13c62000 || c->rx_status != 0x13c62078 ||
        c->tx_offset != 0x10 || c->rx_offset != 0xbc || c->channel != 1 ||
        !range(c->shared_base, c->shared_bytes) || c->shared_bytes != 0x200000 ||
        c->shared_base < 0x40000000 || c->shared_base + c->shared_bytes > 0x800000000ULL ||
        (c->shared_base & 0xffff) || !range(c->xnu_base, c->xnu_bytes) ||
        c->layout.status_pa != c->shared_base || c->layout.status_bytes != 0x400 ||
        c->layout.debug_pa != c->shared_base + 0x400 || c->layout.debug_bytes != 0xc00) {
        r->error = SWEET_GPU_ARGUMENT;
        return r->error;
    }
    budget = (io->frequency * c->timeout_ms + 999) / 1000;
    r->stage = SWEET_GPU_MEMORY;
    if (overlap(c->shared_base, c->shared_bytes, c->xnu_base, c->xnu_bytes)) {
        r->error = SWEET_GPU_OVERLAP;
        return r->error;
    }
    r->stage = SWEET_GPU_POWER_DOMAIN;
    r->spm_before = rd(io, c->sleep + 0xf3c);
    r->spm_second = rd(io, c->sleep + 0xf40);
    if (!(r->spm_before & r->spm_second & 2)) {
        r->error = SWEET_GPU_UNPOWERED;
        return r->error;
    }
    r->stage = SWEET_GPU_FIRMWARE;
    r->firmware_magic = rd(io, c->gpueb + 0x1fd24);
    if (r->firmware_magic != 0x55667788) {
        r->error = SWEET_GPU_HANDOFF;
        return r->error;
    }
    /* Actual LK stores extra firmware allocation PA>>12 at this register.
     * It allocates 20 MiB; never dereference or overwrite that allocation. */
    r->firmware_memory = (uint64_t)rd(io, c->gpueb + 0x1fd34) << 12;
    r->stage = SWEET_GPU_MEMORY;
    if (r->firmware_memory < 0x40000000 ||
        r->firmware_memory + 0x1400000 > 0x800000000ULL ||
        overlap(r->firmware_memory, 0x1400000, c->xnu_base, c->xnu_bytes) ||
        overlap(r->firmware_memory, 0x1400000, c->shared_base, c->shared_bytes)) {
        r->error = SWEET_GPU_OVERLAP;
        return r->error;
    }
    r->stage = SWEET_GPU_INIT;
    rc = sweet_gpueb_encode_init(&c->layout, message);
    if (!rc)
        rc = request(c, io, message, SWEET_GPUEB_CMD_INIT, budget, &r->init_result);
    if (rc || r->init_result < 0) {
        r->error = rc ? rc : r->init_result;
        return r->error;
    }
    r->stage = SWEET_GPU_ON;
    sweet_gpueb_encode_power(1, message);
    rc = request(c, io, message, SWEET_GPUEB_CMD_POWER, budget, &r->on_result);
    if (rc || r->on_result < 0) {
        r->error = rc ? rc : r->on_result;
        return r->error;
    }
    if (!r->on_result) {
        r->error = SWEET_GPU_UNPOWERED;
        return r->error;
    }
    r->power_acquired = 1;
    if (r->on_result != 1) {
        r->error = SWEET_GPU_OWNER;
        goto power_off;
    }
    rc = wait_bits(io, c->sleep + 0xf3c, 6, 6, budget);
    if (!rc)
        rc = wait_bits(io, c->sleep + 0xf40, 6, 6, budget);
    r->spm_after = rd(io, c->sleep + 0xf3c);
    if (rc) {
        r->error = rc;
        goto power_off;
    }
    r->stage = SWEET_GPU_ID;
    r->gpu_id = rd(io, c->gpu);
    r->gpu_status = rd(io, c->gpu + 0x34);
    r->as_present = rd(io, c->gpu + 0x18);
    /* Restrict this experiment to the expected v10 architecture. Never
     * send a CSF reset opcode to an unrecognized JM GPU. */
    if ((r->gpu_id >> 28) != 10 || !r->as_present || r->as_present == UINT32_MAX ||
        (r->gpu_status & 0x80)) {
        r->error = SWEET_GPU_MODEL;
        goto power_off;
    }
    r->stage = SWEET_GPU_RESET;
    saved_mask = rd(io, c->gpu + 0x28);
    wr(io, c->gpu + 0x28, 0);
    wr(io, c->gpu + 0x24, 0x100);
    wr(io, c->gpu + 0x30, 0x101); /* CSF RESET + SOFT payload, not JM 1. */
    rc = wait_bits(io, c->gpu + 0x20, 0x100, 0x100, budget);
    r->reset_rawstat = rd(io, c->gpu + 0x20);
    if (rc)
        r->error = rc;
    wr(io, c->gpu + 0x24, 0x100);
    wr(io, c->gpu + 0x28, saved_mask);
power_off:
    /* Release precisely the single reference we acquired. Never retry an
     * ambiguous POWER_ON timeout: ownership is then unknown. */
    r->cleanup_attempted = 1;
    sweet_gpueb_encode_power(0, message);
    rc = request(c, io, message, SWEET_GPUEB_CMD_POWER, budget, &r->off_result);
    if (rc || r->off_result < 0) {
        if (!r->error) {
            r->stage = SWEET_GPU_OFF;
            r->error = rc ? rc : r->off_result;
        }
    } else {
        r->power_acquired = 0;
        if (!r->error && r->off_result != 0) {
            r->stage = SWEET_GPU_OFF;
            r->error = SWEET_GPU_OWNER;
        }
    }
    if (!r->error)
        r->stage = SWEET_GPU_COMPLETE;
    return r->error;
}
