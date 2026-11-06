/* CSF probe arena is part of the shim's own linked BSS, below its payload.
 * It never borrows GPUEB reservations or the XNU RAM window. */
#include "csf.h"
#include "console.h"
#ifdef SHIM_CSF_ENTRY_PROBE
#include "../xnu/gpu/mali_csf_entry_probe.h"
#ifdef SHIM_CSF_ENTRY_PTE_GUARD
#include "../xnu/gpu/mali_csf_entry_guard.h"
#endif
#endif
#if defined(SHIM_CSF_ENTRY_PTE_GUARD) && (!defined(SHIM_CSF_ENTRY_PROBE) || !defined(SHIM_CSF_INLINE_ENTRY_PROBE))
#error "entry PTE guard requires the inline reset-entry overlay"
#endif

static uint8_t arena[2u<<20] __attribute__((aligned(4096)));
extern const uint8_t sweet_csf_blob_start[],sweet_csf_blob_end[];
struct sweet_csf_boot_report shim_csf_report;
_Static_assert(sizeof(struct sweet_csf_boot_report)==696, "CSF2333 platform path ABI");
/* Value written to MCU_CONTROL to start the MCU. 3 is ENABLE|AUTO, the form
 * the vendor driver uses; 2 reproduces every build up to2371, which set AUTO
 * alone. The image builder sets this from --mcu-control so a trial changes one
 * number. */
#ifndef SWEET_CSF_MCU_CONTROL
#define SWEET_CSF_MCU_CONTROL 3
#endif
_Static_assert(SWEET_CSF_MCU_CONTROL==2 || SWEET_CSF_MCU_CONTROL==3,
               "MCU_CONTROL must be AUTO alone or ENABLE|AUTO");
static int overlap(uint64_t a,uint64_t n,uint64_t b,uint64_t m)
{
    if(!n||!m||a>UINT64_MAX-n||b>UINT64_MAX-m)return 1;
    return a<b+m && b<a+n;
}
#ifdef SHIM_CSF_ENTRY_PROBE
static int dump_section(const struct sweet_csf_section *s,void *context)
{
    (void)context;
    con_hex2("CSFsec","flags=",s->flags,"va.start=",s->va_start);
    con_hex2("CSFsec","va.end=",s->va_end,"data.start=",s->data_start);
    con_hex("CSFsec data.end",s->data_end);
    return 0;
}
#endif
int shim_csf_powered(void *arg,const struct sweet_gpu_io *io,uint64_t gpu)
{
    const struct shim_csf_context *ctx=arg;
    struct sweet_csf_memory memory;
    uint64_t root=0,pa=(uintptr_t)arena;
    size_t fw_bytes=(uintptr_t)sweet_csf_blob_end-(uintptr_t)sweet_csf_blob_start;
    shim_csf_report=(struct sweet_csf_boot_report){.stage=SWEET_CSF_BOOT_CONFIG};
    if(!ctx||!ctx->platform||!ctx->platform->power_acquired||ctx->platform->on_result!=1||
       overlap(pa,sizeof(arena),ctx->xnu_base,ctx->xnu_bytes)||
       overlap(pa,sizeof(arena),ctx->shared_base,ctx->shared_bytes)||
       overlap(pa,sizeof(arena),ctx->platform->firmware_memory,0x1400000)) {
        shim_csf_report.error=SWEET_CSF_BOOT_ARGUMENT;return shim_csf_report.error;
    }
    int rc=sweet_csf_memory_plan(sweet_csf_blob_start,fw_bytes,&memory);
    uint32_t mmu=io->read32(io->context,gpu+0x14);
    /* Pinned mali_mgm helper defaults to leaf group6 (bits59..62).
     * Isolate this tag: retain2327 PTE low bits, AS attributes and startup. */
    if(!rc)rc=sweet_csf_memory_build_group(sweet_csf_blob_start,fw_bytes,&memory,arena,sizeof(arena),pa,(mmu>>8)&255,6,&root);
    if(rc) {shim_csf_report.error=rc;return rc;}
#ifdef SHIM_CSF_ENTRY_PROBE
    struct sweet_csf_layout layout;
    rc=sweet_csf_parse(sweet_csf_blob_start,fw_bytes,&layout,dump_section,0);
#ifdef SHIM_CSF_INLINE_ENTRY_PROBE
    if(!rc)rc=sweet_csf_inline_probe_install(arena,sizeof(arena),&memory);
#else
    if(!rc)rc=sweet_csf_entry_probe_install(arena,sizeof(arena),&memory);
#endif
    if(rc) {shim_csf_report.error=rc;return rc;}
#endif
    io->barrier(io->context); /* Native shim has MMU and CPU caches off. */
#ifdef SHIM_CSF_ENTRY_PTE_GUARD
    struct sweet_csf_entry_guard_result evidence={0};
    rc=sweet_csf_entry_guard(&memory,pa,root,io->read32,io->context,
        sweet_csf_inline_jump,sizeof(sweet_csf_inline_jump),&evidence);
    con_hex2("CSF entry guard","rc=",(uint32_t)rc,"VA=",SWEET_CSF_RESET_ENTRY_VA);
    con_hex2("CSF entry PTE","lo=",(uint32_t)evidence.leaf_pte,
             "hi=",(uint32_t)(evidence.leaf_pte>>32));
    con_hex2("CSF entry","PA=",(uint32_t)evidence.entry_pa,
             "word=",evidence.entry_word);
    con_hex2("CSF entry words","section=",evidence.code_start_word,
             "expected=",sweet_csf_entry_u32(sweet_csf_inline_jump));
    if(rc) {shim_csf_report.error=SWEET_CSF_BOOT_STATE;return shim_csf_report.error;}
#endif
    struct sweet_csf_boot_config c={.gpu=gpu,.root_pa=root,.arena_pa=pa,
        .arena_bytes=memory.required_bytes,.shared_offset=memory.shared_offset,
        .shared_bytes=memory.shared_bytes,.timeout_ms=1000,.noncoherent=1,
        .pte_group_requested=6,.vendor_ina0=1,.vendor_cached_memattr=1,
        .platform_snapshot=1,.access_snapshot=1,.platform_path=1,
        .mcu_control_value=SWEET_CSF_MCU_CONTROL};
#if defined(SHIM_CSF_ENTRY_PROBE) || defined(SHIM_CSF_ENTRY_CHECKPOINT)
    c.entry_checkpoint=1;
#endif
    for(uint32_t i=0;i<memory.mapping_count;i++) {
        const struct sweet_csf_mapping *m=&memory.map[i];
        c.pte_pages_built+=m->bytes/4096;
        if(m->va<=0x0202c000 && (uint64_t)m->va+m->bytes>=0x0202d000 && (m->flags&3)==3)
            c.private_probe_offset=m->arena_offset+0x0202c000-m->va;
        if(m->va==0x01000000 && (m->flags&4) && m->data_bytes>=4) {
            const uint8_t *p=sweet_csf_blob_start+m->data_start;
            c.firmware_probe_offset=m->arena_offset;c.firmware_probe_va=m->va;
            c.firmware_probe_expected=(uint32_t)p[0]|(uint32_t)p[1]<<8|
                (uint32_t)p[2]<<16|(uint32_t)p[3]<<24;
        }
    }
    if(!c.private_probe_offset||!c.firmware_probe_offset) {
        shim_csf_report.error=SWEET_CSF_BOOT_ARGUMENT;return shim_csf_report.error;
    }
    rc=sweet_csf_boot(&c,io,&shim_csf_report);
    con_hex2("CSF","stage=",shim_csf_report.stage,"error=",(uint32_t)shim_csf_report.error);
    con_hex2("CSF","version=",shim_csf_report.version,"mcu=",shim_csf_report.mcu_status);
    con_hex2("CSF start","ctl=",shim_csf_report.platform_reserved>>8,
             "back=",shim_csf_report.platform_reserved&0xff);
    con_hex2("CSF","mmu=",shim_csf_report.mmu_raw,"reset=",shim_csf_report.reset_raw);
    return rc;
}
