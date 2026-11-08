#pragma once
#include "../xnu/gpu/mali_csf_boot.h"
struct shim_csf_context {
    uint64_t xnu_base,xnu_bytes,shared_base,shared_bytes;
    const struct sweet_gpu_boot_report *platform;
};
#if SWEET_CSF_OUT_OF_ARENA
/*2409: two pages at the top of the bootloader's splash reservation, i.e. DRAM
 *the arena does not back. A setter rather than a context field on purpose:
 *adding a member moved `platform` and changed every older build's .text, and
 *"2401..2408 still rebuild byte for byte" is a property this series relies on.
 *Zero is the default and fails the trial closed. */
void shim_csf_set_out_of_arena(uint64_t pa);
#endif
extern struct sweet_csf_boot_report shim_csf_report;
#if SWEET_CSF_GLOBAL_INIT
extern struct sweet_csf_global_evidence shim_csf_global_evidence;
#endif
#ifndef SWEET_CSF_LEAF_PROBE
#define SWEET_CSF_LEAF_PROBE 0
#endif
#if SWEET_CSF_LEAF_PROBE
/*2388: the leaf descriptors the MCU will walk, read back out of the arena this
 * shim hands the AS - 4 x u64, published as its own32-byte ADT property so the
 *696-byte CSF report ABI stays untouched. Order is fixed and documented by
 * sweet_csf_leaf_va[] in csf.c: 0x01000000, 0x01001000, 0x0100e000, 0x0100f000. */
struct sweet_csf_leaf_evidence { uint64_t leaf[4]; };
extern struct sweet_csf_leaf_evidence shim_csf_leaf_evidence;
#endif
int shim_csf_powered(void *, const struct sweet_gpu_io *, uint64_t);
