#ifndef FDT_H
#define FDT_H

#include <stdint.h>

int fdt_check_header(uintptr_t fdt);
int fdt_chosen_u64(uintptr_t fdt, const char *prop, uint64_t *out);
int fdt_chosen_u32(uintptr_t fdt, const char *prop, uint32_t *out);
int fdt_memory_regions(uintptr_t fdt, uint64_t *bases, uint64_t *sizes, int max);
int fdt_find_fb(uintptr_t fdt, uint64_t *base, uint32_t *width, uint32_t *height, uint32_t *stride);
int fdt_find_node(uintptr_t fdt, const char *path);
int fdt_get_reg(uintptr_t fdt, int node, uint64_t *base, uint64_t *size);
int fdt_get_prop_u32(uintptr_t fdt, int node, const char *prop, uint32_t *out);
int fdt_get_prop_u64(uintptr_t fdt, int node, const char *prop, uint64_t *out);

#endif