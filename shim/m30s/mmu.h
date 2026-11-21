#ifndef MMU_H
#define MMU_H

#include <stdint.h>

struct mmu_info {
	uint64_t img_lo;
	uint64_t img_hi;
	uint64_t ttbr;
	uint64_t sctlr_before;
	uint64_t sctlr_after;
	int n_l3;
};

int mmu_enable(struct mmu_info *mi);
uint64_t mmu_probe(uintptr_t va);

#endif