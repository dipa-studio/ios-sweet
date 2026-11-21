#include <stdint.h>
#include "mmu.h"
#include "console.h"

#define PAGE_16K		0x4000UL
#define BLOCK_16K		0x2000000UL	/* 32 MB */
#define TCR_TG1_16K		(1UL << 30)
#define TCR_T0SZ(x)		((64 - (x)) << 0)
#define TCR_T1SZ(x)		((64 - (x)) << 16)
#define TCR_IRGN0_WBWA		(1UL << 8)
#define TCR_ORGN0_WBWA		(1UL << 10)
#define TCR_SH0_ISH		(3UL << 12)
#define TCR_EPD0		(1UL << 7)
#define TCR_EPD1		(1UL << 23)
#define TCR_ASID16		(1UL << 36)
#define TCR_TBI0		(1UL << 37)
#define TCR_TBI1		(1UL << 38)

#define MAIR_ATTR_IDX(idx, attr)	((attr) << ((idx) * 8))
#define MAIR_DEVICE_nGnRnE		0x00
#define MAIR_NORMAL_NC		0x44
#define MAIR_NORMAL_WBWA		0xff

#define PTE_VALID		(1UL << 0)
#define PTE_TABLE		(1UL << 1)
#define PTE_BLOCK		(0UL << 1)
#define PTE_AF		(1UL << 10)
#define PTE_SH_INNER		(3UL << 8)
#define PTE_SH_OUTER		(2UL << 8)
#define PTE_NG		(1UL << 11)
#define PTE_AF		(1UL << 10)
#define PTE_ATTR_IDX(idx)	((idx) << 2)
#define PTE_UXN		(1UL << 54)
#define PTE_PXN		(1UL << 53)

/* Memory attributes */
#define ATTR_DEVICE		0
#define ATTR_NORMAL_NC		1
#define ATTR_NORMAL_WBWA	2

static uint64_t l0_table[512] __attribute__((aligned(0x4000)));
static uint64_t l1_table[512] __attribute__((aligned(0x4000)));
static uint64_t l2_table[512] __attribute__((aligned(0x4000)));
static uint64_t l3_tables[8][512] __attribute__((aligned(0x4000)));

static inline uint64_t rd64(uintptr_t a) { return *(volatile uint64_t *)a; }
static inline void wr64(uintptr_t a, uint64_t v) { *(volatile uint64_t *)a = v; }
static inline uint64_t rsr(const char *r) { uint64_t v; __asm__ volatile("mrs %0, " r : "=r"(v)); return v; }
static inline void wsr(const char *r, uint64_t v) { __asm__ volatile("msr " r ", %0" : : "r"(v)); }
static inline void isb(void) { __asm__ volatile("isb" ::: "memory"); }
static inline void dsb(void) { __asm__ volatile("dsb sy" ::: "memory"); }

static uintptr_t phys_base;
static uint64_t mem_size;
static int n_l3_used = 0;

static void map_block(uint64_t *table, int index, uint64_t pa, int attr_idx, int pte_flags)
{
	table[index] = pa | PTE_VALID | PTE_BLOCK | PTE_AF | PTE_SH_INNER | PTE_ATTR_IDX(attr_idx) | pte_flags;
}

static void map_l3_page(uint64_t *l3, int index, uint64_t pa, int attr_idx, int pte_flags)
{
	l3[index] = pa | PTE_VALID | PTE_AF | PTE_SH_INNER | PTE_ATTR_IDX(attr_idx) | pte_flags;
}

int mmu_enable(struct mmu_info *mi)
{
	uint64_t mair, tcr, sctlr;

	/* MAIR: attribute indices */
	mair = MAIR_ATTR_IDX(ATTR_DEVICE, MAIR_DEVICE_nGnRnE) |
	       MAIR_ATTR_IDX(ATTR_NORMAL_NC, MAIR_NORMAL_NC) |
	       MAIR_ATTR_IDX(ATTR_NORMAL_WBWA, MAIR_NORMAL_WBWA);
	wsr("mair_el1", mair);

	/* TCR: 48-bit VA (16K granule), TTBR0 only */
	tcr = TCR_TG1_16K |
	      TCR_T0SZ(16) |		/* 48-bit VA */
	      TCR_IRGN0_WBWA |
	      TCR_ORGN0_WBWA |
	      TCR_SH0_ISH |
	      TCR_EPD1 |		/* Disable TTBR1 */
	      TCR_ASID16 |
	      TCR_TBI0 | TCR_TBI1;
	wsr("tcr_el1", tcr);
	isb();

	/* Build identity mapping for:
	 * - 0x00000000 - 0x40000000 (1GB): shim + kernel + boot data
	 * - 0x80000000 - 0x100000000 (2GB): DRAM bank 0
	 * - 0x880000000 - 0x900000000 (2GB): DRAM bank 1
	 * - 0x900000000 - 0x980000000 (2GB): DRAM bank 2
	 * - Device regions: GIC, UART, UFS, DECON, etc.
	 */

	/* L0 table: 512 entries, each covers 512 GB (39 bits) */
	/* We only need entries 0 (0-512GB) and 1 (512GB-1TB) */
	/* Entry 0: 0x0 - 0x8000000000 (512GB) */
	l0_table[0] = (uint64_t)l1_table | PTE_VALID | PTE_TABLE;
	l0_table[1] = (uint64_t)l1_table | PTE_VALID | PTE_TABLE; /* alias for >512GB */

	/* L1 table: 512 entries, each covers 1 GB (30 bits) */
	/* Map 0x0 - 0x40000000 (1GB) as device for early boot */
	for (int i = 0; i < 4; i++) {
		map_block(l1_table, i, i * BLOCK_16K * 32, ATTR_DEVICE, PTE_PXN | PTE_UXN);
	}

	/* Map DRAM bank 0: 0x80000000 - 0x100000000 (2GB) */
	for (int i = 0x80; i < 0x100; i++) {
		map_block(l1_table, i, (uint64_t)i * 0x40000000, ATTR_NORMAL_WBWA, 0);
	}

	/* Map DRAM bank 1: 0x880000000 - 0x900000000 (2GB) - L1 index 0x110..0x11f */
	/* Actually these are in the upper 32 bits, so we need L0[1] -> L1 for upper region */
	/* For simplicity, create separate L1 for upper region */
	/* L0[1] covers 0x8000000000-0x10000000000 */
	/* We'll use a different L1 table for the upper region */

	/* L0[1] points to a separate L1 for upper memory */
	uint64_t *l1_upper = l3_tables[0]; /* repurpose first l3 table as L1 upper */
	l0_table[1] = (uint64_t)l1_upper | PTE_VALID | PTE_TABLE;

	/* Map DRAM bank 1: 0x880000000 - 0x900000000 (2GB) */
	/* L1 index = (0x880000000 >> 30) & 0x1ff = 0x110..0x11f */
	for (int i = 0x110; i < 0x120; i++) {
		uint64_t pa = (uint64_t)i * 0x40000000;
		map_block(l1_upper, i, pa, ATTR_NORMAL_WBWA, 0);
	}

	/* Map DRAM bank 2: 0x900000000 - 0x980000000 (2GB) */
	/* L1 index = (0x900000000 >> 30) & 0x1ff = 0x120..0x12f */
	for (int i = 0x120; i < 0x130; i++) {
		uint64_t pa = (uint64_t)i * 0x40000000;
		map_block(l1_upper, i, pa, ATTR_NORMAL_WBWA, 0);
	}

	/* Map device regions (identity) in lower 4GB */
	/* GICD: 0x12301000, GICR: 0x12302000, UFS: 0x13520000, DECON: 0x148B0000, DSIM: 0x148E0000 */
	uint64_t device_regions[] = {
		0x12300000, 0x10000,	/* GIC */
		0x13520000, 0x10000,	/* UFS */
		0x148B0000, 0x10000,	/* DECON */
		0x148E0000, 0x10000,	/* DSIM */
		0x11A10000, 0x10000,	/* Speedy (S2MPU09) */
		0x11080000, 0x10000,	/* GPIO (keys) */
		0x11850000, 0x10000,	/* PINCTRL0 */
		0x11C20000, 0x10000,	/* PINCTRL1 */
		0x14A60000, 0x10000,	/* PINCTRL2 */
		0x13490000, 0x10000,	/* PINCTRL3 */
		0x139B0000, 0x10000,	/* PINCTRL4 */
	};

	for (int i = 0; i < sizeof(device_regions)/sizeof(device_regions[0]); i += 2) {
		uint64_t base = device_regions[i];
		uint64_t size = device_regions[i+1];
		uint64_t end = base + size;
		uint64_t aligned_base = base & ~(BLOCK_16K - 1);
		uint64_t aligned_end = (end + BLOCK_16K - 1) & ~(BLOCK_16K - 1);

		for (uint64_t pa = aligned_base; pa < aligned_end; pa += BLOCK_16K) {
			int l1_idx = (pa >> 30) & 0x1ff;
			if (l1_idx < 4) {
				map_block(l1_table, l1_idx, pa, ATTR_DEVICE, PTE_PXN | PTE_UXN);
			}
		}
	}

	/* Set TTBR0 */
	wsr("ttbr0_el1", (uint64_t)l0_table);
	isb();

	/* Enable MMU + caches */
	sctlr = rsr("sctlr_el1");
	mi->sctlr_before = sctlr;
	sctlr |= (1 << 0) | (1 << 2) | (1 << 12) | (1 << 4) | (1 << 11); /* M, C, I, SA0, SA */
	wsr("sctlr_el1", sctlr);
	isb();
	mi->sctlr_after = rsr("sctlr_el1");

	mi->ttbr = (uint64_t)l0_table;
	mi->n_l3 = n_l3_used;

	con_hex("MMU enabled, TTBR0", mi->ttbr);
	con_hex("SCTLR_EL1", mi->sctlr_after);

	return 0;
}

uint64_t mmu_probe(uintptr_t va)
{
	uint64_t par;
	__asm__ volatile("at s1e1r, %0" : : "r"(va) : "memory");
	isb();
	par = rsr("par_el1");
	return par;
}