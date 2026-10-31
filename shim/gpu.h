#pragma once
#include <stdint.h>
#include "../xnu/gpu/mtk_gpueb_boot.h"

/* Returns zero only when it is safe to proceed with this XNU RAM window.
 * Device operations run only for an exact, normal-mode MT6983 handoff. */
int shim_gpu_prepare(uintptr_t dtb, uint64_t xnu_base, uint64_t xnu_bytes,
                     struct sweet_gpu_boot_report *report, uint64_t *shared);
/* Writes only the preallocated ADT diagnostic properties. Keeps the XNU
 * kernel unchanged; its existing iBoot-version log persists the summary. */
int shim_gpu_publish(uintptr_t adt, uint32_t bytes,
                     const struct sweet_gpu_boot_report *report, uint64_t shared);
uintptr_t shim_recovery_target(uintptr_t dtb);
int shim_gpu_arm_recovery(uintptr_t dtb);
