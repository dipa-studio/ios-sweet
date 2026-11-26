#include <cassert>
#include <cstdint>

#define PTE_TABLE               3ULL
#define PTE_ATTR_INDEX_SHIFT    2
#define PTE_AP_RW_SHIFT         6
#define PTE_SH_SHIFT            8
#define PTE_AF                  (1ULL << 10)
#define PTE_LEAF_RW             (1ULL | (2ULL << PTE_ATTR_INDEX_SHIFT) | \
                                (3ULL << PTE_AP_RW_SHIFT) | (2ULL << PTE_SH_SHIFT) | PTE_AF)
#define PTE_ADDR_MASK           0x0000fffffffff000ULL

static bool
descriptorTest(void)
{
	uint64_t table = 0x12345000ULL | PTE_TABLE;
	uint64_t leaf = 0x12346000ULL | PTE_LEAF_RW;

	assert((table & 3ULL) == 3ULL);
	assert((leaf & 3ULL) == 1ULL);
	assert((leaf & PTE_ADDR_MASK) == 0x12346000ULL);
	assert(((leaf >> PTE_ATTR_INDEX_SHIFT) & 7ULL) == 2ULL);
	assert(((leaf >> PTE_AP_RW_SHIFT) & 3ULL) == 3ULL);
	assert(((leaf >> PTE_SH_SHIFT) & 3ULL) == 2ULL);
	assert((leaf & PTE_AF) != 0ULL);
	return true;
}

static bool
allocBoundsTest(void)
{
	const uint64_t vaBase = 0x02000000ULL;
	const uint64_t vaEnd = 0x100000000ULL;
	const uint64_t pageMask = 4095ULL;

	assert(((4096ULL + pageMask) & ~pageMask) == 4096ULL);
	assert(((4097ULL + pageMask) & ~pageMask) == 8192ULL);
	assert(vaBase + 4096ULL < vaEnd);
	assert(vaEnd - vaBase > 4096ULL);
	return true;
}

int
main(void)
{
	assert(descriptorTest());
	assert(allocBoundsTest());
	return 0;
}
