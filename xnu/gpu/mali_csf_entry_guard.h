#ifndef SWEET_MALI_CSF_ENTRY_GUARD_H
#define SWEET_MALI_CSF_ENTRY_GUARD_H
#include "mali_csf_memory.h"

/* CPU readback of the installed AS0 table and instruction backing.
 * The reset vector selects VA 0x010018ed (Thumb), not the code section's
 * start at 0x01000000. The first instruction is at page offset 0x8ec.
 * The shim runs with CPU MMU/cache disabled; read32 addresses are PAs.
 * This is a pre-AUTO software gate, not evidence of an MCU fetch.
 */
#define SWEET_CSF_RESET_ENTRY_VA 0x010018ecu
#define SWEET_CSF_CODE_START_VA 0x01000000u
#define SWEET_CSF_ENTRY_PA_MASK UINT64_C(0x0000fffffffff000)
enum sweet_csf_entry_guard_error {
    SWEET_CSF_ENTRY_ARGUMENT = -1,
    SWEET_CSF_ENTRY_TABLE = -2,
    SWEET_CSF_ENTRY_LEAF = -3,
    SWEET_CSF_ENTRY_BACKING = -4,
    SWEET_CSF_ENTRY_INSTRUCTION = -5
};
struct sweet_csf_entry_guard_result {
    uint64_t leaf_pte, entry_pa;
    uint32_t code_start_word, entry_word;
};
typedef uint32_t (*sweet_csf_entry_read32)(void *, uint64_t);
static inline int sweet_csf_entry_guard(const struct sweet_csf_memory *m,
    uint64_t arena_pa, uint64_t root_pa, sweet_csf_entry_read32 read32, void *context,
    const uint8_t *expected, size_t expected_bytes,
    struct sweet_csf_entry_guard_result *result)
{
    if(!m||!read32||!expected||!result||root_pa!=arena_pa||
       (arena_pa&4095)||m->table_pages!=8||
       m->required_bytes<SWEET_CSF_PAGE*m->table_pages||
       m->required_bytes>SWEET_CSF_PAGE*512u||
       expected_bytes!=24||m->mapping_count>SWEET_CSF_MAX_SECTIONS)
        return SWEET_CSF_ENTRY_ARGUMENT;
    *result=(struct sweet_csf_entry_guard_result){0};
    const struct sweet_csf_mapping *code=0;
    for(uint32_t i=0;i<m->mapping_count;i++)
        if(m->map[i].va==SWEET_CSF_CODE_START_VA)code=&m->map[i];
    if(!code||code->bytes!=0x10000||code->data_bytes!=0xf848||
       (code->flags&7)!=5||code->arena_offset>m->required_bytes||
       code->bytes>m->required_bytes-code->arena_offset||
       arena_pa>UINT64_MAX-m->required_bytes)
        return SWEET_CSF_ENTRY_ARGUMENT;
    result->code_start_word=read32(context,arena_pa+code->arena_offset);
    uint64_t table=root_pa;
    const unsigned shifts[]={39,30,21};
    for(unsigned level=0;level<3;level++) {
        uint64_t slot=table+(((uint64_t)SWEET_CSF_RESET_ENTRY_VA>>shifts[level])&511u)*8;
        if(slot<arena_pa||slot-arena_pa>
           (uint64_t)m->table_pages*SWEET_CSF_PAGE-8)
            return SWEET_CSF_ENTRY_TABLE;
        uint64_t d=(uint64_t)read32(context,slot)|
                   (uint64_t)read32(context,slot+4)<<32;
        if((d&3)!=3||(d&~(SWEET_CSF_ENTRY_PA_MASK|UINT64_C(3)))!=0)
            return SWEET_CSF_ENTRY_TABLE;
        table=d&SWEET_CSF_ENTRY_PA_MASK;
        if(table<arena_pa||table-arena_pa>=
           (uint64_t)m->table_pages*SWEET_CSF_PAGE)
            return SWEET_CSF_ENTRY_TABLE;
    }
    uint64_t slot=table+((SWEET_CSF_RESET_ENTRY_VA>>12)&511u)*8;
    if(slot<arena_pa||slot-arena_pa>
       (uint64_t)m->table_pages*SWEET_CSF_PAGE-8)
        return SWEET_CSF_ENTRY_TABLE;
    uint64_t leaf=(uint64_t)read32(context,slot)|
                  (uint64_t)read32(context,slot+4)<<32;
    uint64_t page_pa=arena_pa+code->arena_offset+0x1000;
    uint64_t expected_leaf=page_pa|UINT64_C(0xfc7)|(UINT64_C(6)<<59);
    result->leaf_pte=leaf;
    if((leaf&3)!=3) return SWEET_CSF_ENTRY_LEAF;
    uint64_t entry_pa=(leaf&SWEET_CSF_ENTRY_PA_MASK)+
                      (SWEET_CSF_RESET_ENTRY_VA&4095u);
    result->entry_pa=entry_pa;
    if(entry_pa<arena_pa||entry_pa-arena_pa>
       (uint64_t)m->required_bytes-expected_bytes)
        return SWEET_CSF_ENTRY_BACKING;
    result->entry_word=read32(context,entry_pa);
    if(leaf!=expected_leaf||entry_pa!=arena_pa+code->arena_offset+0x18ec)
        return SWEET_CSF_ENTRY_LEAF;
    for(size_t i=0;i<expected_bytes;i+=4) {
        uint32_t word=(uint32_t)expected[i]|(uint32_t)expected[i+1]<<8|
            (uint32_t)expected[i+2]<<16|(uint32_t)expected[i+3]<<24;
        if(read32(context,entry_pa+i)!=word)
            return SWEET_CSF_ENTRY_INSTRUCTION;
    }
    return 0;
}
#endif
