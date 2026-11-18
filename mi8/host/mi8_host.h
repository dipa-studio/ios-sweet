#pragma once
/* Host-side HAL for testing shim/mi8.c without hardware (see test_mi8.c). */
#include <stdint.h>
uint32_t rd32(uintptr_t a);
void wr32(uintptr_t a, uint32_t v);
void wr8(uintptr_t a, uint8_t v);
uint64_t host_rsr(const char *name);
#define rsr(r) host_rsr(r)
static inline void dsb(void) {}
uint64_t ticks(void);
uint64_t tfreq(void);
