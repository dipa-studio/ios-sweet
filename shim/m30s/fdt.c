#include "fdt.h"

#define FDT_MAGIC		0xd00dfeed
#define FDT_BEGIN_NODE		1
#define FDT_END_NODE		2
#define FDT_PROP		3
#define FDT_NOP			4
#define FDT_END			9

static uint32_t be32(uintptr_t a)
{
	return __builtin_bswap32(*(volatile uint32_t *)a);
}

static int streq(const char *a, const char *b)
{
	while (*a && *a == *b)
		a++, b++;
	return *a == *b;
}

static uintptr_t align4(uintptr_t a)
{
	return (a + 3) & ~3UL;
}

static uintptr_t skip_str(uintptr_t p)
{
	while (*(volatile char *)p)
		p++;
	return p + 1;
}

int fdt_check_header(uintptr_t fdt)
{
	if (!fdt)
		return 0;
	return be32(fdt) == FDT_MAGIC;
}

int fdt_chosen_u64(uintptr_t fdt, const char *prop, uint64_t *out)
{
	if (!fdt_check_header(fdt))
		return 0;

	uintptr_t p = fdt + be32(fdt + 8);		/* off_dt_struct */
	uintptr_t strings = fdt + be32(fdt + 12);	/* off_dt_strings */
	int depth = 0, in_chosen = 0;

	for (;;) {
		uint32_t tok = be32(p);
		p += 4;
		switch (tok) {
		case FDT_BEGIN_NODE: {
			const char *name = (const char *)p;
			depth++;
			in_chosen = depth == 2 && streq(name, "chosen");
			p = align4(skip_str(p));
			break;
		}
		case FDT_END_NODE:
			if (in_chosen)
				return 0;
			depth--;
			break;
		case FDT_PROP: {
			uint32_t len = be32(p), nameoff = be32(p + 4);
			uintptr_t val = p + 8;
			if (in_chosen && streq((const char *)(strings + nameoff), prop)) {
				if (len == 8) {
					*out = (uint64_t)be32(val) << 32 | be32(val + 4);
					return 1;
				}
				return 0;
			}
			p = align4(val + len);
			break;
		}
		case FDT_NOP:
			break;
		default:
			return 0;
		}
	}
}

int fdt_chosen_u32(uintptr_t fdt, const char *prop, uint32_t *out)
{
	if (!fdt_check_header(fdt))
		return 0;

	uintptr_t p = fdt + be32(fdt + 8);
	uintptr_t strings = fdt + be32(fdt + 12);
	int depth = 0, in_chosen = 0;

	for (;;) {
		uint32_t tok = be32(p);
		p += 4;
		switch (tok) {
		case FDT_BEGIN_NODE: {
			const char *name = (const char *)p;
			depth++;
			in_chosen = depth == 2 && streq(name, "chosen");
			p = align4(skip_str(p));
			break;
		}
		case FDT_END_NODE:
			if (in_chosen)
				return 0;
			depth--;
			break;
		case FDT_PROP: {
			uint32_t len = be32(p), nameoff = be32(p + 4);
			uintptr_t val = p + 8;
			if (in_chosen && streq((const char *)(strings + nameoff), prop)) {
				if (len == 4) {
					*out = be32(val);
					return 1;
				}
				return 0;
			}
			p = align4(val + len);
			break;
		}
		case FDT_NOP:
			break;
		default:
			return 0;
		}
	}
}

/* Find all memory@ nodes and return base/size pairs */
int fdt_memory_regions(uintptr_t fdt, uint64_t *bases, uint64_t *sizes, int max)
{
	if (!fdt_check_header(fdt))
		return 0;

	uintptr_t p = fdt + be32(fdt + 8);
	uintptr_t strings = fdt + be32(fdt + 12);
	int depth = 0, in_memory = 0;
	int count = 0;

	for (;;) {
		uint32_t tok = be32(p);
		p += 4;
		switch (tok) {
		case FDT_BEGIN_NODE: {
			const char *name = (const char *)p;
			depth++;
			/* Look for memory@... nodes at depth 1 */
			in_memory = (depth == 1 && (streq(name, "memory") ||
						    (name[0] == 'm' && name[1] == 'e' &&
						     name[2] == 'm' && name[3] == 'o' &&
						     name[4] == 'r' && name[5] == 'y')));
			p = align4(skip_str(p));
			break;
		}
		case FDT_END_NODE:
			in_memory = 0;
			depth--;
			break;
		case FDT_PROP: {
			uint32_t len = be32(p), nameoff = be32(p + 4);
			uintptr_t val = p + 8;
			if (in_memory && streq((const char *)(strings + nameoff), "reg")) {
				if (len >= 16 && count < max) {
					/* reg is <base_hi base_lo size_hi size_lo> for 2-cell addressing */
					bases[count] = (uint64_t)be32(val) << 32 | be32(val + 4);
					sizes[count] = (uint64_t)be32(val + 8) << 32 | be32(val + 12);
					count++;
				}
			}
			p = align4(val + len);
			break;
		}
		case FDT_NOP:
			break;
		default:
			if (tok == FDT_END)
				return count;
			break;
		}
	}
}

/* Find framebuffer from simple-framebuffer or screen_info in /chosen */
int fdt_find_fb(uintptr_t fdt, uint64_t *base, uint32_t *width, uint32_t *height, uint32_t *stride)
{
	if (!fdt_check_header(fdt))
		return 0;

	uintptr_t p = fdt + be32(fdt + 8);
	uintptr_t strings = fdt + be32(fdt + 12);
	int depth = 0, in_chosen = 0;
	uint32_t w = 0, h = 0, s = 0;
	uint64_t b = 0;
	int found = 0;

	for (;;) {
		uint32_t tok = be32(p);
		p += 4;
		switch (tok) {
		case FDT_BEGIN_NODE: {
			const char *name = (const char *)p;
			depth++;
			if (depth == 2 && streq(name, "chosen")) {
				in_chosen = 1;
			} else if (in_chosen && depth == 3) {
				/* Look for simple-framebuffer or screen_info */
				if (streq(name, "simple-framebuffer") ||
				    streq(name, "screen_info") ||
				    streq(name, "display") ||
				    streq(name, "framebuffer")) {
					/* We'll parse its properties */
				}
			}
			p = align4(skip_str(p));
			break;
		}
		case FDT_END_NODE:
			if (in_chosen && depth == 2)
				return found;
			if (in_chosen && depth == 3)
				in_chosen = 0; /* left the sub-node */
			depth--;
			break;
		case FDT_PROP: {
			uint32_t len = be32(p), nameoff = be32(p + 4);
			uintptr_t val = p + 8;
			const char *pname = (const char *)(strings + nameoff);

			if (in_chosen && streq(pname, "framebuffer")) {
				/* EFI framebuffer in /chosen */
				if (len >= 4) {
					b = be32(val);
					found = 1;
				}
			} else if (in_chosen && streq(pname, "width")) {
				if (len == 4) w = be32(val);
			} else if (in_chosen && streq(pname, "height")) {
				if (len == 4) h = be32(val);
			} else if (in_chosen && streq(pname, "stride") || streq(pname, "rowbytes")) {
				if (len == 4) s = be32(val);
			}
			p = align4(val + len);
			break;
		}
		case FDT_NOP:
			break;
		default:
			if (tok == FDT_END)
				break;
			break;
		}
	}

	if (found) {
		*base = b;
		*width = w;
		*height = h;
		*stride = s ? s : w * 4;
		return 1;
	}
	return 0;
}

int fdt_find_node(uintptr_t fdt, const char *path)
{
	/* Simplified: find node by full path */
	if (!fdt_check_header(fdt))
		return -1;

	uintptr_t p = fdt + be32(fdt + 8);
	uintptr_t strings = fdt + be32(fdt + 12);
	int depth = 0;

	while (*path == '/')
		path++;

	for (;;) {
		uint32_t tok = be32(p);
		p += 4;
		switch (tok) {
		case FDT_BEGIN_NODE: {
			const char *name = (const char *)p;
			depth++;
			/* Check if this node matches our path component */
			const char *slash = path;
			while (*slash && *slash != '/')
				slash++;
			int len = slash - path;
			if (streq(name, path) || (len > 0 && !strncmp(name, path, len) &&
			    (name[len] == '\0' || name[len] == '@'))) {
				path = slash;
				while (*path == '/')
					path++;
				if (!*path)
					return depth; /* Found */
			}
			p = align4(skip_str(p));
			break;
		}
		case FDT_END_NODE:
			depth--;
			break;
		case FDT_PROP: {
			uint32_t len = be32(p);
			p = align4(p + 4 + len);
			break;
		}
		case FDT_NOP:
			break;
		default:
			return -1;
		}
	}
}

int fdt_get_reg(uintptr_t fdt, int node, uint64_t *base, uint64_t *size)
{
	/* Not fully implemented - placeholder */
	return 0;
}

int fdt_get_prop_u32(uintptr_t fdt, int node, const char *prop, uint32_t *out)
{
	/* Not fully implemented - placeholder */
	return 0;
}

int fdt_get_prop_u64(uintptr_t fdt, int node, const char *prop, uint64_t *out)
{
	/* Not fully implemented - placeholder */
	return 0;
}