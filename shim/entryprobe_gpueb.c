/* FDT-only GPUEB handoff snapshot. Does not touch GPU/GPUEB MMIO, send
 * messages, load firmware, dereference shared PAs, or initialize UFS.
 * Read the same-boot Linux banner before another LK run replaces it.
 */
#include <stdint.h>
#include "entryprobe_config.h"
#include "fdt.h"
#include "../xnu/gpu/mtk_gpueb_protocol.h"

static void field(char *banner, unsigned offset, uint64_t value)
{
    static const char hex[] = "0123456789abcdef";
    unsigned i;
    for (i = 0; i < 16; i++)
        banner[offset + i] = hex[(value >> (60 - i * 4)) & 15];
}

static uint32_t little32(const uint8_t *p)
{
    return p[0] | ((uint32_t)p[1] << 8) | ((uint32_t)p[2] << 16) |
           ((uint32_t)p[3] << 24);
}

void entryprobe_gpueb(uintptr_t dtb, char *banner)
{
    char path[192], mali[192];
    const void *raw;
    uint32_t len, id, at, found = 0;
    uint64_t base = 0, bytes = 0, gpu_base = 0, gpu_bytes = 0;
    struct sweet_gpueb_shared layout;
    const unsigned fields[] = { ENTRY_GICD, ENTRY_VTIMER, ENTRY_FB,
                                ENTRY_X16, ENTRY_FAR, ENTRY_PC, ENTRY_SPSR };
    unsigned i;
    for (i = 0; i < sizeof(fields) / sizeof(fields[0]); i++)
        field(banner, fields[i], 0);
    /* Unlike ordinary FDT numeric cells, MTK atag,boot is a LE structure.
     * Preserve unknown when the exact observed header is not present. */
    field(banner, ENTRY_X0, UINT64_MAX);
    field(banner, ENTRY_STAGE, 0x9001);
    if (fdt_prop(dtb, "/chosen", "atag,boot", &raw, &len) && len == 16) {
        const uint8_t *p = raw;
        if (little32(p) == 16 && little32(p + 4) == 0x41000802)
            field(banner, ENTRY_X0, little32(p + 8));
    }
    if (fdt_find_compatible(dtb, "mediatek,mali", mali, sizeof(mali)) &&
        fdt_reg(dtb, mali, &gpu_base, &gpu_bytes)) {
        field(banner, ENTRY_GICD, gpu_base);
        field(banner, ENTRY_VTIMER, gpu_bytes);
    }
    if (!fdt_find_compatible(dtb, "mediatek,gpueb", path, sizeof(path)))
        return;
    if (!fdt_prop(dtb, path, "gpueb-support", &raw, &len) || len != 4) {
        field(banner, ENTRY_STAGE, 0x9003);
        return;
    }
    if (fdt_be32((uintptr_t)raw) != 1) {
        field(banner, ENTRY_STAGE, 0x9002);
        return;
    }
    if (!fdt_prop(dtb, path, "gpueb_mem_addr", &raw, &len) || len != 8) {
        field(banner, ENTRY_STAGE, 0x9004);
        return;
    }
    base = fdt_be64((uintptr_t)raw);
    field(banner, ENTRY_FB, base);
    if (!fdt_prop(dtb, path, "gpueb_mem_size", &raw, &len) || len != 8) {
        field(banner, ENTRY_STAGE, 0x9004);
        return;
    }
    bytes = fdt_be64((uintptr_t)raw);
    field(banner, ENTRY_X16, bytes);
    if (!fdt_prop(dtb, path, "gpueb_mem_name_table", &raw, &len)) {
        field(banner, ENTRY_STAGE, 0x9005);
        return;
    }
    const uint8_t *names = raw;
    static const char wanted[] = "MEM_ID_GPUFREQ";
    for (id = 0, at = 0; id < 20 && at < len; id++) {
        uint32_t start = at, j;
        while (at < len && names[at])
            at++;
        if (at == len || at == start)
            break;
        if (at - start == sizeof(wanted) - 1) {
            for (j = 0; j < sizeof(wanted) - 1 && names[start + j] == (uint8_t)wanted[j]; j++)
                ;
            if (j == sizeof(wanted) - 1) {
                found = 1;
                break;
            }
        }
        at++;
    }
    if (!found ||
        !fdt_prop(dtb, path, "gpueb_mem_table", &raw, &len) ||
        sweet_gpueb_shared_layout(base, bytes, raw, len, id, &layout)) {
        field(banner, ENTRY_STAGE, 0x9005);
        return;
    }
    field(banner, ENTRY_FAR, layout.status_pa);
    field(banner, ENTRY_PC, layout.debug_pa);
    field(banner, ENTRY_SPSR, ((uint64_t)layout.status_bytes << 32) | layout.debug_bytes);
    /* Structurally described only. Reservation, firmware-ready state and
     * ownership still need independent verification before any access. */
    field(banner, ENTRY_STAGE, 0x9000);
}
