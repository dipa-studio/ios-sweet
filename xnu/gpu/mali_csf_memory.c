/* Independently written from the CSF section ABI and AArch64 LPAE
 * descriptor format. See docs/matisse-csf-bringup.md for source pins. */
#include "mali_csf_memory.h"

/* Diagnostic only, off unless a trial defines it.2375 and2377 showed reads and
 * writes of the RW section complete while a data read of an R-X page hangs until
 * its line is resident, and the section ABI sets no other difference between
 * those leaves. If the hang is a read-miss fill that the read-only bit refuses,
 * mapping the same page writable removes it. Nothing in the driver sets this:
 * the shipping mapping keeps the firmware's own permissions. */
#ifndef SWEET_CSF_RO_LEAVES_WRITABLE
#define SWEET_CSF_RO_LEAVES_WRITABLE 0
#endif

static int collect(const struct sweet_csf_section *s, void *context)
{
    struct sweet_csf_memory *m = context;
    if (s->flags & 32) { m->protected_skipped++; return 0; }
    if (m->mapping_count == SWEET_CSF_MAX_SECTIONS) return -1;
    struct sweet_csf_mapping *p = &m->map[m->mapping_count++];
    *p = (struct sweet_csf_mapping){s->va_start, s->va_end - s->va_start,
        s->flags, 0, s->data_start, s->data_end - s->data_start};
    return 0;
}
static uint64_t get64(const uint8_t *p)
{
    uint64_t v = 0;
    for (unsigned i = 0; i < 8; i++) v |= (uint64_t)p[i] << (8 * i);
    return v;
}
static void put64(uint8_t *p, uint64_t v)
{
    for (unsigned i = 0; i < 8; i++) p[i] = (uint8_t)(v >> (8 * i));
}
static int conflict(uintptr_t a, size_t n, uintptr_t b, size_t m)
{
    return a < b + m && b < a + n;
}
#if SWEET_CSF_RELOCATE_CODE
/* The one executable section: it holds the reset vector, the entry code and
 * every block the MCU has to fetch. Identified by the same predicate the shim
 * uses to pick its firmware probe, so a relocation can never target a section
 * the probe does not observe. */
static int relocates(const struct sweet_csf_mapping *p)
{
    return p->va == 0x01000000u && (p->flags & 4u) != 0;
}
#endif
int sweet_csf_memory_plan(const uint8_t *fw, size_t bytes, struct sweet_csf_memory *out)
{
    struct sweet_csf_memory m = {0};
    struct sweet_csf_layout layout;
    uint8_t l3_used[256] = {0};
    unsigned l2_used = 0;
    uint64_t data_bytes = 0;
    if (!out || bytes > UINT32_MAX) return SWEET_CSF_MEMORY_ARGUMENT;
    int rc = sweet_csf_parse(fw, bytes, &layout, collect, &m);
    if (rc) return rc;
    m.firmware_bytes = (uint32_t)bytes;
    /* All firmware addresses are below4GiB: one L0 and one L1 table. */
    m.table_pages = 2;
    for (uint32_t i = 0; i < m.mapping_count; i++) {
        const struct sweet_csf_mapping *p = &m.map[i];
        uint64_t end = (uint64_t)p->va + p->bytes;
        data_bytes += p->bytes;
        for (uint64_t va = p->va; va < end; va = ((va >> 21) + 1) << 21) {
            unsigned l2 = (unsigned)(va >> 30), key = (unsigned)(va >> 21);
            if (!(l2_used & (1u << l2))) { l2_used |= 1u << l2; m.table_pages++; }
            if (!(l3_used[key / 8] & (1u << (key % 8)))) {
                l3_used[key / 8] |= (uint8_t)(1u << (key % 8)); m.table_pages++;
            }
        }
    }
    uint64_t used = (uint64_t)m.table_pages * SWEET_CSF_PAGE;
    if (used + data_bytes > UINT32_MAX) return SWEET_CSF_MEMORY_CAPACITY;
    for (uint32_t i = 0; i < m.mapping_count; i++) {
        struct sweet_csf_mapping *p = &m.map[i];
        p->arena_offset = (uint32_t)used; used += p->bytes;
        if (p->flags & (1u << 30)) {
            m.shared_offset = p->arena_offset; m.shared_bytes = p->bytes; m.shared_va = p->va;
        }
    }
#if SWEET_CSF_RELOCATE_CODE
    /* Move the code section alone: it is appended at the offset the normal
     * layout ends at, and its original slot is left as unused padding. Every
     * other section therefore keeps the offset, the PA and the descriptor it
     * has in the unrelocated plan; only this section's PA changes. */
    for (uint32_t i = 0; i < m.mapping_count; i++) {
        struct sweet_csf_mapping *p = &m.map[i];
        if (!relocates(p)) continue;
        p->arena_offset = (uint32_t)used; used += p->bytes;
    }
#endif
    m.required_bytes = (uint32_t)used;
    *out = m;
    return 0;
}
int sweet_csf_memory_build_group(const uint8_t *fw, size_t bytes, const struct sweet_csf_memory *m,
    void *buffer, size_t capacity, uint64_t pa, unsigned pa_bits, unsigned memory_group,
    uint64_t *root_pa)
{
    struct sweet_csf_memory verified;
    if (!fw || !m || !buffer || !root_pa || memory_group > 15 || ((uintptr_t)buffer & 7) ||
        bytes > UINTPTR_MAX - (uintptr_t)fw || capacity > UINTPTR_MAX - (uintptr_t)buffer)
        return SWEET_CSF_MEMORY_ARGUMENT;
    int rc = sweet_csf_memory_plan(fw, bytes, &verified);
    if (rc) return rc;
    /* Compare semantic fields; do not trust caller-controlled offsets. */
    if (m->mapping_count != verified.mapping_count || m->required_bytes != verified.required_bytes ||
        m->table_pages != verified.table_pages || m->shared_offset != verified.shared_offset ||
        m->shared_bytes != verified.shared_bytes || m->shared_va != verified.shared_va ||
        m->protected_skipped != verified.protected_skipped || m->firmware_bytes != verified.firmware_bytes)
        return SWEET_CSF_MEMORY_ARGUMENT;
    for (uint32_t i = 0; i < m->mapping_count; i++) {
        const struct sweet_csf_mapping *a = &m->map[i], *b = &verified.map[i];
        if (a->va != b->va || a->bytes != b->bytes || a->flags != b->flags ||
            a->arena_offset != b->arena_offset || a->data_start != b->data_start || a->data_bytes != b->data_bytes)
            return SWEET_CSF_MEMORY_ARGUMENT;
    }
    if (capacity < m->required_bytes) return SWEET_CSF_MEMORY_CAPACITY;
    if (pa_bits < 32 || pa_bits > 48 || (pa & 4095) || pa < 0x40000000 ||
        pa >= (UINT64_C(1) << pa_bits) || m->required_bytes > (UINT64_C(1) << pa_bits) - pa)
        return SWEET_CSF_MEMORY_PHYSICAL;
    if (conflict((uintptr_t)buffer, capacity, (uintptr_t)fw, bytes) ||
        conflict((uintptr_t)buffer, capacity, (uintptr_t)m, sizeof(*m)) ||
        conflict((uintptr_t)buffer, capacity, (uintptr_t)root_pa, sizeof(*root_pa)))
        return SWEET_CSF_MEMORY_ARGUMENT;
    uint8_t *arena = buffer;
    for (uint32_t i = 0; i < m->required_bytes; i++) arena[i] = 0;
    unsigned next_table = 1;
    for (uint32_t i = 0; i < m->mapping_count; i++) {
        const struct sweet_csf_mapping *p = &m->map[i];
        for (uint32_t j = 0; j < p->data_bytes; j++) arena[p->arena_offset + j] = fw[p->data_start + j];
        for (uint64_t off = 0; off < p->bytes; off += SWEET_CSF_PAGE) {
            uint64_t va = (uint64_t)p->va + off;
            uint8_t *table = arena;
            for (unsigned level = 0; level < 3; level++) {
                unsigned shift = 39 - 9 * level;
                uint8_t *entry = table + ((va >> shift) & 511) * 8;
                uint64_t desc = get64(entry);
                if (!desc) {
                    desc = (pa + (uint64_t)next_table++ * SWEET_CSF_PAGE) | 3;
                    put64(entry, desc);
                }
                table = arena + ((desc & UINT64_C(0x0000fffffffff000)) - pa);
            }
            /* Cache-mode1 in the section ABI is cached. Shareability is NOT a
             * property of the cache mode: mali_kbase_mmu_mode_aarch64.c
             * get_mmu_flags() sets ENTRY_SHARE_BITS only for KBASE_REG_SHARE_BOTH,
             * and mali_kbase_csf_firmware.c convert_mem_flags() sets that bit only
             * for a section whose CSF_FIRMWARE_ENTRY_SHARED flag is set. Every
             * other section carries no share bits at all. Until2374 this code
             * set SH=11 (inner and outer shareable) on every cached section,
             * including the R-X code section that declares shared=0; the
             * page-table walker was configured non-shareable at the same time,
             * so the two disagreed about who owns the transaction. */
            int cached = (p->flags & 24) == 8;
            uint64_t desc = (pa + p->arena_offset + off) | 3 | 0x400 | 0x40;
#if !SWEET_CSF_VENDOR_LEAVES
            /* ARMv8 nG. kbase never sets it; 2393 clears it so the leaf matches
             * mali_kbase_mmu_mode_aarch64.c get_mmu_flags() byte for byte. */
            desc |= 0x800;
#endif
#if SWEET_CSF_VENDOR_MEMATTR
            /*2380 vendor pairing. convert_mem_flags() at system_coherency NONE
             * maps a CACHED section to AS_MEMATTR_INDEX_IMPL_DEF_CACHE_POLICY(0)
             * and everything else, CACHED_COHERENT included, to
             * AS_MEMATTR_INDEX_NON_CACHEABLE(5). Only KBASE_REG_SHARE_BOTH sets
             * ENTRY_SHARE_BITS, and the coherent branches are downgraded to
             * CACHE_MODE_NONE before reaching it, so no leaf carries SH bits.
             * The attribute bytes selected from SWEET_CSF_VENDOR_MEMATTR_* stay
             * 0x88/0x4c, i.e. identical to the index1/index0 pairing. */
            desc |= (uint64_t)(cached ? 0u : 5u) << 2;
#else
            desc |= cached ? 0x004 : 0x000;
            if (p->flags & (1u << 30)) desc |= 0x300;
#endif
#if SWEET_CSF_UNCACHED_CODE
            /* 2395: the executable section takes AS_MEMATTR index 5 and loses
             * every SH bit, whatever pairing the rest of the image selected.
             * AttrIndx is bits[4:2] and SH is bits[9:8]; both are cleared
             * before the index is installed so no branch above can leak
             * through. */
            if (p->flags & 4) {
                desc &= ~(UINT64_C(0x1c) | UINT64_C(0x300));
                desc |= UINT64_C(5) << 2;
            }
#endif
            if (!(p->flags & 2) && !SWEET_CSF_RO_LEAVES_WRITABLE) desc |= 0x80;
            if (!(p->flags & 4)) desc |= UINT64_C(3) << 53;
            desc |= (uint64_t)memory_group << 59;
            put64(table + ((va >> 12) & 511) * 8, desc);
        }
    }
    *root_pa = pa;
    return 0;
}
int sweet_csf_memory_build(const uint8_t *fw, size_t bytes, const struct sweet_csf_memory *m,
    void *buffer, size_t capacity, uint64_t pa, unsigned pa_bits, uint64_t *root_pa)
{
    return sweet_csf_memory_build_group(fw, bytes, m, buffer, capacity, pa, pa_bits, 0, root_pa);
}
