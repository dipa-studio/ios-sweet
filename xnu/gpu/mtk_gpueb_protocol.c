#include "mtk_gpueb_protocol.h"

static uint32_t be32(const uint8_t *p)
{
    return ((uint32_t)p[0] << 24) | ((uint32_t)p[1] << 16) |
           ((uint32_t)p[2] << 8) | p[3];
}

static uint32_t le32(const uint8_t *p)
{
    return p[0] | ((uint32_t)p[1] << 8) | ((uint32_t)p[2] << 16) |
           ((uint32_t)p[3] << 24);
}

static void put32(uint8_t *p, uint32_t value)
{
    p[0] = (uint8_t)value;
    p[1] = (uint8_t)(value >> 8);
    p[2] = (uint8_t)(value >> 16);
    p[3] = (uint8_t)(value >> 24);
}

static void put64(uint8_t *p, uint64_t value)
{
    put32(p, (uint32_t)value);
    put32(p + 4, (uint32_t)(value >> 32));
}

static int valid_region(uint64_t base, uint64_t bytes)
{
    const uint64_t limit = 0x800000000ULL;
    return base >= 0x40000000ULL && base < limit && bytes &&
           bytes <= limit - base;
}

int sweet_gpueb_shared_layout(uint64_t base, uint64_t bytes,
                              const uint8_t *table, size_t table_bytes,
                              uint32_t gpufreq_id,
                              struct sweet_gpueb_shared *out)
{
    uint32_t sizes[20] = {0};
    uint64_t offset = 0, total = 0;
    size_t i, count;
    struct sweet_gpueb_shared candidate;

    if (!table || !out)
        return SWEET_GPUEB_ARGUMENT;
    if (!valid_region(base, bytes) || (base & 0xfff) || (bytes & 0xfff))
        return SWEET_GPUEB_RANGE;
    if (!table_bytes || table_bytes % 8 || table_bytes / 8 > 20)
        return SWEET_GPUEB_TABLE;
    count = table_bytes / 8;
    if (gpufreq_id >= count)
        return SWEET_GPUEB_TABLE;
    for (i = 0; i < count; i++) {
        uint32_t id = be32(table + i * 8);
        uint32_t size = be32(table + i * 8 + 4);
        if (id >= count || !size || (size & 3) || sizes[id])
            return SWEET_GPUEB_TABLE;
        sizes[id] = size;
        total += size;
    }
    if (total > bytes || sizes[gpufreq_id] <= SWEET_GPUEB_STATUS_BYTES)
        return SWEET_GPUEB_RANGE;
    for (i = 0; i < gpufreq_id; i++)
        offset += sizes[i];
    candidate.status_pa = base + offset;
    candidate.debug_pa = candidate.status_pa + SWEET_GPUEB_STATUS_BYTES;
    candidate.status_bytes = SWEET_GPUEB_STATUS_BYTES;
    candidate.debug_bytes = sizes[gpufreq_id] - SWEET_GPUEB_STATUS_BYTES;
    *out = candidate;
    return SWEET_GPUEB_OK;
}

int sweet_gpueb_encode_init(const struct sweet_gpueb_shared *layout,
                            uint8_t out[SWEET_GPUEB_MESSAGE_BYTES])
{
    uint64_t bytes;
    unsigned i;
    if (!layout || !out)
        return SWEET_GPUEB_ARGUMENT;
    bytes = (uint64_t)layout->status_bytes + layout->debug_bytes;
    if (layout->status_bytes != SWEET_GPUEB_STATUS_BYTES ||
        !layout->debug_bytes || (layout->debug_bytes & 3) ||
        (layout->status_pa & 3) || !valid_region(layout->status_pa, bytes) ||
        layout->debug_pa != layout->status_pa + layout->status_bytes)
        return SWEET_GPUEB_RANGE;
    for (i = 0; i < SWEET_GPUEB_MESSAGE_BYTES; i++)
        out[i] = 0;
    put32(out, SWEET_GPUEB_CMD_INIT);
    put64(out + 8, layout->status_pa);
    put64(out + 16, layout->debug_pa);
    put32(out + 24, layout->status_bytes);
    put32(out + 28, layout->debug_bytes);
    return SWEET_GPUEB_OK;
}

int sweet_gpueb_encode_power(uint32_t on,
                             uint8_t out[SWEET_GPUEB_MESSAGE_BYTES])
{
    unsigned i;
    if (!out)
        return SWEET_GPUEB_ARGUMENT;
    if (on > 1)
        return SWEET_GPUEB_ARGUMENT;
    for (i = 0; i < SWEET_GPUEB_MESSAGE_BYTES; i++)
        out[i] = 0;
    put32(out, SWEET_GPUEB_CMD_POWER);
    put32(out + 8, on);
    return SWEET_GPUEB_OK;
}

int sweet_gpueb_decode_response(const uint8_t *data, size_t bytes,
                                uint32_t expected_command, int32_t *result)
{
    uint32_t value;
    if (!data || !result ||
        (expected_command != SWEET_GPUEB_CMD_INIT &&
         expected_command != SWEET_GPUEB_CMD_FREQ &&
         expected_command != SWEET_GPUEB_CMD_POWER &&
         expected_command != SWEET_GPUEB_CMD_COMMIT))
        return SWEET_GPUEB_ARGUMENT;
    if (bytes != SWEET_GPUEB_MESSAGE_BYTES ||
        le32(data) != expected_command || le32(data + 4) != 0)
        return SWEET_GPUEB_RESPONSE;
    value = le32(data + 8);
    *result = (value <= INT32_MAX) ? (int32_t)value :
              -1 - (int32_t)(UINT32_MAX - value);
    return SWEET_GPUEB_OK;
}
