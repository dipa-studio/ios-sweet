#pragma once
#include "../xnu/gpu/mali_csf_boot.h"
struct shim_csf_context {
    uint64_t xnu_base,xnu_bytes,shared_base,shared_bytes;
    const struct sweet_gpu_boot_report *platform;
};
extern struct sweet_csf_boot_report shim_csf_report;
#if SWEET_CSF_GLOBAL_INIT
extern struct sweet_csf_global_evidence shim_csf_global_evidence;
#endif
int shim_csf_powered(void *, const struct sweet_gpu_io *, uint64_t);
