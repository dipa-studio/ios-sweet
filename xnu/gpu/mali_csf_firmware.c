#include "mali_csf_firmware.h"

#define CSF_MAGIC UINT32_C(0xc3f13a6e)
#define CSF_SHARED_VA UINT32_C(0x04000000)
#define CSF_READ UINT32_C(1)
#define CSF_PROTECTED (UINT32_C(1) << 5)
#define CSF_SHARED (UINT32_C(1) << 30)
#define CSF_OPTIONAL (UINT32_C(1) << 31)
#define CSF_SECTION_FLAGS (UINT32_C(0x3f) | CSF_SHARED | CSF_OPTIONAL)
/* Bound worst-case work for hostile headers (overlap check is O(n^2)). */
#define CSF_MAX_ENTRIES 4096u

static uint32_t
csf_u32(const uint8_t *p)
{
    return (uint32_t)p[0] | ((uint32_t)p[1] << 8) |
        ((uint32_t)p[2] << 16) | ((uint32_t)p[3] << 24);
}

static void
csf_section(const uint8_t *p, uint32_t size, struct sweet_csf_section *s)
{
    s->flags = csf_u32(p + 4);
    s->va_start = csf_u32(p + 8);
    s->va_end = csf_u32(p + 12);
    s->data_start = csf_u32(p + 16);
    s->data_end = csf_u32(p + 20);
    s->name = p + 24;
    s->name_bytes = size - 24;
}

int
sweet_csf_parse(const uint8_t *data, size_t bytes, struct sweet_csf_layout *out,
                sweet_csf_section_fn callback, void *context)
{
    struct sweet_csf_layout layout = {0};
    uint32_t end, offset;

    if (!data || !out)
        return SWEET_CSF_BAD_ARGUMENT;
    if (bytes < 20)
        return SWEET_CSF_TRUNCATED;
    end = csf_u32(data + 16);
    if (csf_u32(data) != CSF_MAGIC || data[5] != 0 || data[6] || data[7] ||
        csf_u32(data + 12) || end < 20 || (end & 3))
        return SWEET_CSF_BAD_HEADER;
    if ((size_t)end > bytes)
        return SWEET_CSF_TRUNCATED;
    layout.format_major = data[5];
    layout.format_minor = data[4];
    layout.format_hash = csf_u32(data + 8);
    layout.table_end = end;

    for (offset = 20; offset < end;) {
        struct sweet_csf_section s;
        uint32_t h, size, type;
        if (end - offset < 4 || layout.entries == CSF_MAX_ENTRIES)
            return SWEET_CSF_BAD_ENTRY;
        h = csf_u32(data + offset);
        size = (h >> 8) & 255;
        type = h & 255;
        if (size < 4 || (size & 3) || size > end - offset ||
            (h & UINT32_C(0x3fff0000)))
            return SWEET_CSF_BAD_ENTRY;
        layout.entries++;
        if (type == 0) {
            uint32_t previous;
            if (size < 24)
                return SWEET_CSF_BAD_ENTRY;
            csf_section(data + offset, size, &s);
            if ((s.flags & ~CSF_SECTION_FLAGS) || !(s.flags & CSF_READ) ||
                s.va_end <= s.va_start || ((s.va_start | s.va_end) & 4095) ||
                s.data_end < s.data_start || (size_t)s.data_end > bytes ||
                s.data_end - s.data_start > s.va_end - s.va_start ||
                (s.data_end != s.data_start && s.data_start < end))
                return SWEET_CSF_BAD_SECTION;
            if ((s.flags & CSF_SHARED) &&
                (s.va_start != CSF_SHARED_VA || (s.flags & CSF_PROTECTED)))
                return SWEET_CSF_BAD_SECTION;
            if (s.va_start == CSF_SHARED_VA) {
                if (!(s.flags & CSF_SHARED))
                    return SWEET_CSF_BAD_SECTION;
                layout.shared_va = s.va_start;
                layout.shared_bytes = s.va_end - s.va_start;
            }
            for (previous = 20; previous < offset;) {
                uint32_t ph = csf_u32(data + previous);
                uint32_t psize = (ph >> 8) & 255;
                if ((ph & 255) == 0) {
                    uint32_t start = csf_u32(data + previous + 8);
                    uint32_t stop = csf_u32(data + previous + 12);
                    if (s.va_start < stop && start < s.va_end)
                        return SWEET_CSF_OVERLAPPING_SECTION;
                }
                previous += psize;
            }
            layout.sections++;
            if (s.flags & CSF_PROTECTED)
                layout.protected_sections++;
            if ((s.va_start | s.va_end) & 16383)
                layout.non_16k_sections++;
        } else if (type > 4 && !(h & CSF_OPTIONAL)) {
            return SWEET_CSF_UNSUPPORTED_ENTRY;
        }
        offset += size;
    }
    if (!layout.shared_bytes)
        return SWEET_CSF_NO_SHARED;
    if (callback) {
        for (offset = 20; offset < end;) {
            uint32_t h = csf_u32(data + offset);
            uint32_t size = (h >> 8) & 255;
            if ((h & 255) == 0) {
                struct sweet_csf_section s;
                csf_section(data + offset, size, &s);
                if (callback(&s, context))
                    return SWEET_CSF_CALLBACK_FAILED;
            }
            offset += size;
        }
    }
    *out = layout;
    return SWEET_CSF_OK;
}
