#pragma once
#include <stdint.h>

/* Boot the SWEETXNU payload found in the ABL ramdisk; returns only on error. */
const char *loader_boot(uintptr_t dtb);
/*
 * Load it but do not jump: returns 0 and the physical entry point and
 * boot_args address (enter with MMU/caches off, x0 = boot_args), or an
 * error string. For boards that start XNU on another core (shim-a51).
 */
const char *loader_prepare(uintptr_t dtb, uintptr_t *entry_pa, uintptr_t *boot_args_pa);
