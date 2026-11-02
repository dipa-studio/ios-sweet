#ifndef SWEET_MALI_CSF_ENTRY_PROBE_H
#define SWEET_MALI_CSF_ENTRY_PROBE_H
#include "mali_csf_memory.h"

/* Linked from tools/matisse-csf-entry-probe.S. Keep the original reset VA,
 * vectors, container, page tables and all initialized data. The trampoline
 * uses only an executable section's zero-filled tail, with no stack access.
 * It restores the original reset prefix's r0/r1/PRIMASK state before the
 * first peripheral store. Marker is separate from global-control version.
 */
#define SWEET_CSF_ENTRY_MARKER_VA 0x04000ffcu
#define SWEET_CSF_ENTRY_MARKER 0x53545542u
static const uint8_t sweet_csf_entry_jump[] = {
    0x0e,0xf0,0x08,0xb8,0x00,0xbf,0x00,0xbf
};
static const uint8_t sweet_csf_entry_trampoline[] = {
    0x72,0xb6,0x05,0x48,0x05,0x49,0x01,0x60,0xbf,0xf3,0x4f,0x8f,
    0x04,0x48,0x00,0x68,0x4f,0xf0,0x0b,0x01,0xf1,0xf7,0xee,0xbf,
    0xfc,0x0f,0x00,0x04,0x42,0x55,0x54,0x53,0x88,0x19,0x00,0x01
};
static inline uint32_t sweet_csf_entry_u32(const uint8_t *p)
{
    return (uint32_t)p[0]|(uint32_t)p[1]<<8|(uint32_t)p[2]<<16|(uint32_t)p[3]<<24;
}
static inline int sweet_csf_entry_probe_install(uint8_t *arena,size_t bytes,
                                               const struct sweet_csf_memory *m)
{
    if(!arena||!m||m->mapping_count>SWEET_CSF_MAX_SECTIONS||
       bytes<m->required_bytes||m->shared_va!=0x04000000||m->shared_bytes<4096)
        return SWEET_CSF_MEMORY_ARGUMENT;
    const struct sweet_csf_mapping *code=0,*vectors=0,*shared=0;
    for(uint32_t i=0;i<m->mapping_count;i++) {
        const struct sweet_csf_mapping *p=&m->map[i];
        if(p->arena_offset>bytes||p->bytes>bytes-p->arena_offset||p->data_bytes>p->bytes)
            return SWEET_CSF_MEMORY_ARGUMENT;
        if(p->va==0) vectors=p;
        if(p->va==0x01000000) code=p;
        if(p->va==0x04000000) shared=p;
    }
    if(!vectors||vectors->bytes<8||!code||code->bytes!=0x10000||
       (code->flags&7)!=5||code->data_bytes!=0xf848||!shared||shared->bytes<4096||
       shared->arena_offset!=m->shared_offset||(shared->flags&0xc0000003)!=0xc0000003)
        return SWEET_CSF_MEMORY_ARGUMENT;
    const uint8_t *v=arena+vectors->arena_offset;
    uint8_t *entry=arena+code->arena_offset+0x18ec;
    uint8_t *tail=arena+code->arena_offset+0xf900;
    uint8_t *marker=arena+shared->arena_offset+0xffc;
    if(sweet_csf_entry_u32(v)!=0x02040000||sweet_csf_entry_u32(v+4)!=0x010018ed||
       sweet_csf_entry_u32(entry)!=0x4826b672||sweet_csf_entry_u32(entry+4)!=0x010bf04f||
       sweet_csf_entry_u32(arena+code->arena_offset+0x1988)!=0x40022000||
       sweet_csf_entry_u32(marker)||sweet_csf_entry_u32(arena+shared->arena_offset))
        return SWEET_CSF_MEMORY_ARGUMENT;
    for(size_t i=0;i<sizeof(sweet_csf_entry_trampoline);i++)
        if(tail[i])return SWEET_CSF_MEMORY_ARGUMENT;
    for(size_t i=0;i<sizeof(sweet_csf_entry_trampoline);i++)tail[i]=sweet_csf_entry_trampoline[i];
    for(size_t i=0;i<sizeof(sweet_csf_entry_jump);i++)entry[i]=sweet_csf_entry_jump[i];
    return 0;
}
#endif
