#ifndef SWEET_MTK_GPUEB_PROTOCOL_H
#define SWEET_MTK_GPUEB_PROTOCOL_H

#include <stddef.h>
#include <stdint.h>

/* MT6983 protocol facts checked against the OS2.0.2.0 vendor wrapper.
 * Independently written, allocation-free host helpers. No MMIO or transport;
 * success does NOT prove that GPUEB is running or owns the power domains.
 */
#define SWEET_GPUEB_MESSAGE_BYTES 32u
#define SWEET_GPUEB_STATUS_BYTES 0x400u
#define SWEET_GPUEB_CMD_INIT 0u
#define SWEET_GPUEB_CMD_FREQ 1u
#define SWEET_GPUEB_CMD_POWER 6u
#define SWEET_GPUEB_CMD_COMMIT 7u

enum sweet_gpueb_result {
    SWEET_GPUEB_OK = 0,
    SWEET_GPUEB_ARGUMENT = -1,
    SWEET_GPUEB_RANGE = -2,
    SWEET_GPUEB_TABLE = -3,
    SWEET_GPUEB_RESPONSE = -4
};

struct sweet_gpueb_shared {
    uint64_t status_pa;
    uint64_t debug_pa;
    uint32_t status_bytes;
    uint32_t debug_bytes;
};

/* Input is a raw big-endian gpueb_mem_table of (ID, bytes) pairs.
 * IDs must form a permutation of 0..N-1 (N <= 20). Regions accumulate in
 * numeric ID order, as the platform ABI specifies, not property order.
 * Caller obtains base/bytes from the LIVE gpueb_mem_addr/size properties
 * and separately verifies reservation and lifetime before using any PA.
 * On error, all output arguments of these helpers are unchanged.
 */
int sweet_gpueb_shared_layout(uint64_t base, uint64_t bytes,
                              const uint8_t *table, size_t table_bytes,
                              uint32_t gpufreq_id,
                              struct sweet_gpueb_shared *out);

int sweet_gpueb_encode_init(const struct sweet_gpueb_shared *layout,
                            uint8_t out[SWEET_GPUEB_MESSAGE_BYTES]);
int sweet_gpueb_encode_power(uint32_t on,
                             uint8_t out[SWEET_GPUEB_MESSAGE_BYTES]);
/* Decode only the confirmed command/target/return-value prefix. A caller
 * must serialize requests, discard stale completions and impose a timeout.
 * A valid negative firmware result is returned through result, not hidden.
 */
int sweet_gpueb_decode_response(const uint8_t *data, size_t bytes,
                                uint32_t expected_command, int32_t *result);

#endif
