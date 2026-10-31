/* Optional MT6983 shim diagnostic, independent from the frozen board/UFS
 * objects. Default loader builds do not reference this translation unit. */
#include "gpu.h"
#include "fdt.h"
#include "console.h"
#ifdef SHIM_CSF_PROBE
#include "csf.h"
#endif

static int equal(const char *a, const char *b)
{
    while (*a && *a == *b) a++, b++;
    return *a == *b;
}
static uint32_t little32(const uint8_t *p)
{
    return p[0] | ((uint32_t)p[1] << 8) | ((uint32_t)p[2] << 16) |
           ((uint32_t)p[3] << 24);
}
static int named_reg(uintptr_t dtb, const char *path, const char *name,
                      uint64_t *address, uint64_t minimum)
{
    for (int i = 0; i < 24; i++) {
        const char *n = fdt_str_n(dtb, path, "reg-names", i);
        uint64_t bytes;
        if (!n) return 0;
        if (equal(n, name))
            return fdt_reg_n(dtb, path, i, address, &bytes) && bytes >= minimum;
    }
    return 0;
}

uintptr_t shim_recovery_target(uintptr_t dtb)
{
#ifdef SHIM_RECOVERY_FALLBACK
    extern const uint8_t _head[];
    const void *raw; uint32_t bytes;
    if (fdt_prop(dtb, "/chosen", "atag,boot", &raw, &bytes) && bytes == 16 &&
        little32(raw) == 16 && little32((const uint8_t *)raw + 4) == 0x41000802 &&
        little32((const uint8_t *)raw + 8) == 0) return 0;
    /* Unknown/recovery modes cannot accidentally enter the power test. */
    return (uintptr_t)_head + SHIM_RECOVERY_OFFSET;
#else
    (void)dtb; return 0;
#endif
}

int shim_gpu_arm_recovery(uintptr_t dtb)
{
#ifdef SHIM_RECOVERY_FALLBACK
    uint64_t base, bytes;
    if (!fdt_reg(dtb, "/watchdog@1c007000", &base, &bytes) || base != 0x1c007000 || bytes != 0x100 ||
        fdt_u32(dtb, "/watchdog@1c007000/reboot-mode", "offset", 0) != 0x24 ||
        fdt_u32(dtb, "/watchdog@1c007000/reboot-mode", "mask", 0) != 15 ||
        fdt_u32(dtb, "/watchdog@1c007000/reboot-mode", "mode-recovery", 0) != 2) return -1;
#ifndef SHIM_GPU_HOST_TEST
    volatile uint32_t *w = (volatile uint32_t *)(uintptr_t)base;
    /* Volatile reboot-mode scratch from this board's DT. No misc/GPT or
     * other partition writes. MT6983 WDT length: (seconds<<11)|8. */
    w[9] = (w[9] & ~15u) | 2;
    w[1] = (31u << 11) | 8;
    w[2] = 0x1971;
    w[0] = (w[0] & ~(8u | 64u)) | 0x22000005;
    __asm__ volatile("dsb sy" ::: "memory");
    return (w[9] & 15) == 2 && (w[0] & 1) ? 0 : -1;
#else
    return 0;
#endif
#else
    (void)dtb; return -1;
#endif
}
static int pin(uintptr_t dtb, const char *path, const char *table_name,
                const char *names_name, unsigned width, uint32_t *offset,
                uint32_t *channel, uint32_t *used)
{
    const void *raw;
    uint32_t bytes, ids = 0, matches = 0;
    if (!fdt_prop(dtb, path, table_name, &raw, &bytes) ||
        !bytes || bytes % (width * 4) || bytes / (width * 4) > 20) return 0;
    for (uint32_t i = 0; i < bytes / (width * 4); i++) {
        uintptr_t row = (uintptr_t)raw + i * width * 4;
        const char *name = fdt_str_n(dtb, path, names_name, (int)i);
        uint32_t id = fdt_be32(row), box = fdt_be32(row + 4);
        uint32_t words = fdt_be32(row + 8);
        if (!name || id >= 32 || ids & (1u << id) || box || !words ||
            words > 160 || *used > 160 - words ||
            (width == 4 && fdt_be32(row + 12) > 1)) return 0;
        ids |= 1u << id;
        if (equal(name, "IPI_ID_GPUFREQ")) {
            if (words != 8 || (width == 4 && fdt_be32(row + 12) != 1)) return 0;
            *offset = *used * 4; *channel = id; matches++;
        }
        *used += words;
    }
    return matches == 1;
}

#ifndef SHIM_GPU_HOST_TEST
static uint32_t native_read(void *unused, uint64_t address)
{
    (void)unused; return *(volatile uint32_t *)(uintptr_t)address;
}
static void native_write(void *unused, uint64_t address, uint32_t value)
{
    (void)unused; *(volatile uint32_t *)(uintptr_t)address = value;
}
static uint64_t native_ticks(void *unused)
{
    uint64_t value; (void)unused;
    __asm__ volatile("isb; mrs %0, cntpct_el0" : "=r"(value)); return value;
}
static void native_barrier(void *unused)
{
    (void)unused; __asm__ volatile("dsb sy" ::: "memory");
}
#endif

int shim_gpu_prepare(uintptr_t dtb, uint64_t xnu_base, uint64_t xnu_bytes,
                     struct sweet_gpu_boot_report *r, uint64_t *shared)
{
    struct sweet_gpu_boot_config c = { .timeout_ms = 250,
        .xnu_base = xnu_base, .xnu_bytes = xnu_bytes };
    const void *raw; uint32_t bytes, used = 0, rx_channel;
    char path[192], gpu_path[192], freq_path[192];
    uint64_t gpu_bytes;
    *r = (struct sweet_gpu_boot_report){ .stage = SWEET_GPU_CONFIG,
        .error = SWEET_GPU_HANDOFF };
    *shared = 0;
    if (!fdt_prop(dtb, "/chosen", "atag,boot", &raw, &bytes) || bytes != 16 ||
        little32(raw) != 16 || little32((const uint8_t *)raw + 4) != 0x41000802) return -1;
    c.boot_mode = little32((const uint8_t *)raw + 8);
    if (c.boot_mode != 0 ||
        !fdt_find_compatible(dtb, "mediatek,gpueb", path, sizeof(path)) ||
        !fdt_find_compatible(dtb, "mediatek,mali", gpu_path, sizeof(gpu_path)) ||
        !fdt_find_compatible(dtb, "mediatek,gpufreq", freq_path, sizeof(freq_path)) ||
        !fdt_reg(dtb, gpu_path, &c.gpu, &gpu_bytes) || gpu_bytes != 0x480000 ||
        fdt_u32(dtb, path, "gpueb-support", 0) != 1 ||
        fdt_u32(dtb, path, "mbox_count", 0) != 1 ||
        fdt_u32(dtb, path, "mbox_size", 0) != 160 ||
        fdt_u32(dtb, path, "slot_size", 0) != 4) return -1;
    if (!named_reg(dtb, path, "gpueb_base", &c.gpueb, 0x22000) ||
        !named_reg(dtb, path, "mbox0_base", &c.mailbox, 0x280) ||
        !named_reg(dtb, path, "mbox0_set", &c.irq_set, 4) ||
        !named_reg(dtb, path, "mbox0_clr", &c.irq_clear, 4) ||
        !named_reg(dtb, path, "mbox0_send", &c.tx_status, 4) ||
        !named_reg(dtb, path, "mbox0_recv", &c.rx_status, 4) ||
        !named_reg(dtb, freq_path, "sleep", &c.sleep, 0x1000) ||
        !pin(dtb, path, "send_table", "send_name_table", 3, &c.tx_offset, &c.channel, &used) ||
        !pin(dtb, path, "recv_table", "recv_name_table", 4, &c.rx_offset, &rx_channel, &used) ||
        rx_channel != c.channel) return -1;
    if (!fdt_prop(dtb, path, "gpueb_mem_addr", &raw, &bytes) || bytes != 8) return -1;
    c.shared_base = fdt_be64((uintptr_t)raw); *shared = c.shared_base;
    if (!fdt_prop(dtb, path, "gpueb_mem_size", &raw, &bytes) || bytes != 8) return -1;
    c.shared_bytes = fdt_be64((uintptr_t)raw);
    const char *mem_name = fdt_str_n(dtb, path, "gpueb_mem_name_table", 0);
    if (!mem_name || !equal(mem_name, "MEM_ID_GPUFREQ") ||
        !fdt_prop(dtb, path, "gpueb_mem_table", &raw, &bytes) ||
        sweet_gpueb_shared_layout(c.shared_base, c.shared_bytes, raw, bytes, 0, &c.layout)) return -1;
#ifndef SHIM_GPU_HOST_TEST
    uint64_t frequency;
    __asm__ volatile("mrs %0, cntfrq_el0" : "=r"(frequency));
    const struct sweet_gpu_io io = { .read32 = native_read, .write32 = native_write,
        .ticks = native_ticks, .barrier = native_barrier, .frequency = frequency };
    #ifdef SHIM_CSF_PROBE
    struct shim_csf_context probe = { .xnu_base=xnu_base, .xnu_bytes=xnu_bytes,
        .shared_base=c.shared_base, .shared_bytes=c.shared_bytes, .platform=r };
    c.powered_probe=shim_csf_powered; c.probe_context=&probe;
#endif
    sweet_gpu_boot(&c, &io, r);
#else
    extern void shim_gpu_host_run(const struct sweet_gpu_boot_config *, struct sweet_gpu_boot_report *);
    shim_gpu_host_run(&c, r);
#endif
    con_hex2("GPU", "stage=", r->stage, "error=", (uint32_t)r->error);
    con_hex2("GPU", "id=", r->gpu_id, "reset=", r->reset_rawstat);
    con_hex("GPUEB shared", c.shared_base);
    con_hex("GPUEB firmware", r->firmware_memory);
    /* Do not copy XNU over firmware memory or start after ambiguous power
     * ownership. A definite pre-power IPI failure can still be logged by XNU. */
    if (r->error == SWEET_GPU_OVERLAP || r->error == SWEET_GPU_ARGUMENT ||
        r->error == SWEET_GPU_HANDOFF || r->error == SWEET_GPU_UNPOWERED ||
        r->power_acquired || (r->stage == SWEET_GPU_ON && r->error)) return -1;
    return 0;
}

/* Bounded ADT walker. The build reserves 128 bytes for each shim-owned
 * version and 128 for the full raw diagnostic. No node insertion at boot. */
static uint8_t *property(uintptr_t adt, uint32_t bytes, const char *wanted, uint32_t expected)
{
    uint32_t pos = 0, remaining[17] = {1};
    unsigned depth = 0;
    for (;;) {
        if (!remaining[depth]) { if (!depth) break; depth--; continue; }
        remaining[depth]--;
        if (pos > bytes || bytes - pos < 8 || depth == 16) return 0;
        const uint8_t *node = (const uint8_t *)adt + pos;
        uint32_t props = little32(node), children = little32(node + 4); pos += 8;
        if (props > 256 || children > 256) return 0;
        for (uint32_t i = 0; i < props; i++) {
            if (pos > bytes || bytes - pos < 36) return 0;
            const uint8_t *p = (const uint8_t *)adt + pos;
            uint32_t n = little32(p + 32) & 0x7fffffff;
            if (n > bytes - pos - 36 || n > UINT32_MAX - 3) return 0;
            unsigned j = 0;
            while (j < 32 && p[j] && wanted[j] && p[j] == (uint8_t)wanted[j]) j++;
            if (j < 32 && !p[j] && !wanted[j] && n == expected) return (uint8_t *)p + 36;
            pos += 36 + ((n + 3) & ~3u);
        }
        if (children) remaining[++depth] = children;
    }
    return 0;
}
static char *text(char *p, const char *s)
{
    while (*s) *p++ = *s++; return p;
}
static char *hex(char *p, uint64_t value, unsigned digits)
{
    static const char h[] = "0123456789abcdef";
    for (unsigned i = digits; i; i--) *p++ = h[(value >> ((i - 1) * 4)) & 15];
    return p;
}
int shim_gpu_publish(uintptr_t adt, uint32_t bytes,
                     const struct sweet_gpu_boot_report *r, uint64_t shared)
{
    uint8_t *raw = property(adt, bytes, "sweet-gpu-report", 128);
    char *a = (char *)property(adt, bytes, "firmware-version", 128);
    char *b = (char *)property(adt, bytes, "system-firmware-version", 128);
    if (!raw || !a || !b || sizeof(*r) > 128) return -1;
#ifdef SHIM_CSF_PROBE
    uint8_t *csf=property(adt, bytes, "sweet-csf-report", 304);
    if (!csf || sizeof(shim_csf_report)!=304) return -1;
    for (unsigned i=0;i<304;i++) csf[i]=0;
    for (unsigned i=0;i<sizeof(shim_csf_report);i++) csf[i]=((const uint8_t *)&shim_csf_report)[i];
#endif
    for (unsigned i = 0; i < 128; i++) raw[i] = 0, a[i] = 0, b[i] = 0;
    for (unsigned i = 0; i < sizeof(*r); i++) raw[i] = ((const uint8_t *)r)[i];
    char *p = text(a, "sweet-shim/gpu2329 s=");
    p = hex(p, r->stage, 2); p = text(p, " e="); p = hex(p, (uint32_t)r->error, 8);
    p = text(p, " id="); p = hex(p, r->gpu_id, 8);
    p = text(p, " rst="); p = hex(p, r->reset_rawstat, 8);
    p = text(p, " on="); p = hex(p, (uint32_t)r->on_result, 8);
    p = text(p, " off="); p = hex(p, (uint32_t)r->off_result, 8); *p = 0;
    p = text(b, "sweet-shim/gpu2329 shared="); p = hex(p, shared, 16);
    p = text(p, " fw="); p = hex(p, r->firmware_memory, 16);
    p = text(p, " magic="); p = hex(p, r->firmware_magic, 8);
    p = text(p, " spm="); p = hex(p, r->spm_before, 8);
    p = text(p, "/"); p = hex(p, r->spm_after, 8); *p = 0;
    return 0;
}
