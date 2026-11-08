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

/* 2398. The leaf's bits 59..62 carry a physical memory group tag. This shim has
 * always published 6 there because the pinned mali_mgm helper names group 6 for
 * GPU allocations, but neither the vendor driver nor the working MT6993 port
 * ever writes those bits into a page-table entry: in kbase the group id is a
 * context allocation hint, and mali_kbase_native_mgm_alloc() marks it unused.
 * 2398 sets the tag to 0 so the last leaf input that has never been varied is
 * varied, with the container unchanged. */
#ifndef SWEET_CSF_LEAF_GROUP
#define SWEET_CSF_LEAF_GROUP 6
#endif
#ifndef SWEET_CSF_OUT_OF_ARENA
#define SWEET_CSF_OUT_OF_ARENA 0
#endif
/*0 = two sentinels (2411-2414), 1 = four, one per 512-byte offset of the page
 *(2415). The extra two exist so the value the MCU returns names the offset that
 *answered without any extra bookkeeping. */
#ifndef SWEET_CSF_OOA_SHAPE
#define SWEET_CSF_OOA_SHAPE 0
#endif
#if SWEET_CSF_OUT_OF_ARENA
/*2411: one page the CSF arena does not back, carrying the tag the firmware puts
 *on every other leaf (group 6), so bit 9 is the only variable.
 *
 * It is a page of this shim's own BSS, immediately past the arena. The CPU MMU
 * is off, so its address is its physical address; the MCU already reads the
 * arena out of the same image, so reachability costs no assumption; and the CPU
 * may read and write it freely, which is what 2410's far page was not - the CPU
 * witness dereferenced LK's GPU firmware allocation and the shim died before it
 * could hand the report back, so that build answered nothing.
 *
 * The page is written with 0x2412a400 at +0x400 and 0x2412a200 at +0x200, so
 * the word the MCU returns names the offset by itself. 0x0100C000 keeps the
 * firmware's own leaf into the arena and serves as the instrument control.
 */
static uint8_t ooa_near[4096] __attribute__((aligned(4096)));
#endif

static uint8_t arena[2u<<20] __attribute__((aligned(4096)));
extern const uint8_t sweet_csf_blob_start[],sweet_csf_blob_end[];
struct sweet_csf_boot_report shim_csf_report;
#if SWEET_CSF_GPU_REGS
_Static_assert(sizeof(struct sweet_csf_boot_report)==784, "CSF2407 GPU register block");
#else
_Static_assert(sizeof(struct sweet_csf_boot_report)==696, "CSF2333 platform path ABI");
#endif
#if SWEET_CSF_GLOBAL_INIT
/*2381 evidence carrier. Published through its own ADT property, so the
 *696-byte report above stays byte-identical. */
struct sweet_csf_global_evidence shim_csf_global_evidence;
_Static_assert(sizeof(struct sweet_csf_global_evidence)==96, "sweet-csf-global size");
#endif
#if SWEET_CSF_LEAF_PROBE
/*2388: read the descriptors the MCU will actually walk. The shim runs with the
 *CPU MMU off, so a physical address is a plain load; this issues no write and
 *changes no mapping. The default four VAs cover the page that cannot be fetched
 *(0x01000000), the page that holds the vendor reset handler (0x01001000) and
 *the pair that is known to work (0x0100e000/0x0100f000). 2401 overrides the
 *list to sample the mirrored code page, the mirror's read target and the same
 *leaf reached through the shared-L3 alias, next to the original leaf. */
#ifndef SWEET_CSF_LEAF_VA_LIST
#define SWEET_CSF_LEAF_VA_LIST {0x01000000u,0x01001000u,0x0100e000u,0x0100f000u}
#endif
struct sweet_csf_leaf_evidence shim_csf_leaf_evidence;
_Static_assert(sizeof(struct sweet_csf_leaf_evidence)==32, "sweet-csf-leaf size");
static const uint32_t sweet_csf_leaf_va[4]=SWEET_CSF_LEAF_VA_LIST;
static uint64_t sweet_csf_leaf_of(const struct sweet_gpu_io *io,uint64_t root,uint32_t va)
{
    uint64_t table=root;
    for(unsigned level=0;level<3;level++) {
        uint64_t at=table+((((uint64_t)va)>>(39-9*level))&511u)*8;
        uint64_t d=(uint64_t)io->read32(io->context,at)|((uint64_t)io->read32(io->context,at+4)<<32);
        if((d&3)!=3)return 0;           /* no table here: report it as absent */
        table=d&UINT64_C(0x0000fffffffff000);
    }
    uint64_t at=table+((((uint64_t)va)>>12)&511u)*8;
    return (uint64_t)io->read32(io->context,at)|((uint64_t)io->read32(io->context,at+4)<<32);
}
#endif
/* Value written to MCU_CONTROL to start the MCU. 2 is AUTO alone and is what
 * every build up to2371 used; 3 is the vendor driver's ENABLE|AUTO. 2372 measured
 * 3 on this SoC: the write reads back, but MCU_STATUS stays0 for the whole
 * budget and the firmware never runs, so AUTO alone is the start value here.
 * The halt step in front of it is unaffected. */
#ifndef SWEET_CSF_MCU_CONTROL
#define SWEET_CSF_MCU_CONTROL 2
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
#if SWEET_CSF_OUT_OF_ARENA
    /*2411: one leaf of the R-X section points past the arena. The other VA the
     *ladder reads is left alone, so it still walks the firmware's own leaf into
     *the arena and proves the instrument works before the new page is asked. */
    uint64_t pa_near=(uint64_t)(uintptr_t)ooa_near;
    struct sweet_csf_remap remaps[1]={{0x0100D000u,pa_near,SWEET_CSF_LEAF_GROUP}};
#if SWEET_CSF_OOA_SHAPE
    /*2415: four offsets, four words. +0x000 has bit 9 = 0 and bit 10 = 0,
     *+0x200 has bit 9 = 1, +0x400 has bit 10 = 1 and +0x600 has both, so the
     *returned word is the shape measurement by itself. */
    ((volatile uint32_t *)ooa_near)[0x000/4]=0x2415a000u;
    ((volatile uint32_t *)ooa_near)[0x200/4]=0x2415a200u;
    ((volatile uint32_t *)ooa_near)[0x400/4]=0x2415a400u;
    ((volatile uint32_t *)ooa_near)[0x600/4]=0x2415a600u;
#else
    ((volatile uint32_t *)ooa_near)[0x400/4]=0x2412a400u;
    ((volatile uint32_t *)ooa_near)[0x200/4]=0x2412a200u;
#endif
    /* Fail closed rather than fly a page whose backing is unknown. */
    if(!pa_near||(pa_near&4095)||(pa_near>=pa&&pa_near<pa+sizeof(arena))) {
        shim_csf_report.error=SWEET_CSF_BOOT_ARGUMENT;return shim_csf_report.error;
    }
#endif
    if(!rc)rc=sweet_csf_memory_build_group(sweet_csf_blob_start,fw_bytes,&memory,arena,sizeof(arena),pa,(mmu>>8)&255,SWEET_CSF_LEAF_GROUP,&root);
#if SWEET_CSF_OUT_OF_ARENA
    if(!rc)rc=sweet_csf_memory_remap_leaves(arena,sizeof(arena),pa,(mmu>>8)&255,remaps,1);
#endif
    if(rc) {shim_csf_report.error=rc;return rc;}
#if SWEET_CSF_OUT_OF_ARENA
    /* CPU witness: the shim runs with the MMU off, so these are the same
     * physical words the MCU will read through the remapped leaf. Only this
     * shim's own page is touched - 2410 dereferenced LK's firmware allocation
     * here and did not survive it. */
    {
        const volatile uint32_t *near=(const volatile uint32_t *)(uintptr_t)pa_near;
        con_hex2("CSF ooa near","b9=0",near[0x400/4],"b9=1",near[0x200/4]);
    }
#endif
#if SWEET_CSF_LEAF_PROBE
    /* Sample the table as handed to the AS, before the MCU is started: this is
     * the mapping every fetch in the trial walks, not a re-derivation of it. */
    for(unsigned i=0;i<4;i++)
        shim_csf_leaf_evidence.leaf[i]=sweet_csf_leaf_of(io,root,sweet_csf_leaf_va[i]);
#endif
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
        .pte_group_requested=SWEET_CSF_LEAF_GROUP,.vendor_ina0=1,.vendor_cached_memattr=1,
        .platform_snapshot=1,.access_snapshot=1,.platform_path=1,
        .mcu_control_value=SWEET_CSF_MCU_CONTROL
#if SWEET_CSF_GLOBAL_INIT
        ,.shared_va=memory.shared_va,.global_init=1,
        .global_evidence=&shim_csf_global_evidence
#endif
        };
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
#if SWEET_CSF_MFG_GLUE
    /*2413: the MFG top page on the way in. These are plain reads of a block
     *the CPU already samples since 2407 (0x748 lands in path_before), so the
     *witness adds no new register access - it only prints the words the
     *glue is about to change. The after-line below is the same four words
     *read back once the write has happened. */
    con_hex2("CSF mfg in","coh=",io->read32(io->context,SWEET_CSF_MFG_BASE+0x168),
             "dsp0=",io->read32(io->context,SWEET_CSF_MFG_BASE+0x8e0));
    con_hex2("CSF mfg in","dsp2=",io->read32(io->context,SWEET_CSF_MFG_BASE+0x910),
             "out0=",io->read32(io->context,SWEET_CSF_MFG_BASE+0x900));
    con_hex("CSF mfg in slc6",io->read32(io->context,SWEET_CSF_MFG_BASE+0x748));
#endif
    rc=sweet_csf_boot(&c,io,&shim_csf_report);
#if SWEET_CSF_MFG_GLUE
    con_hex2("CSF mfg out","coh=",io->read32(io->context,SWEET_CSF_MFG_BASE+0x168),
             "dsp0=",io->read32(io->context,SWEET_CSF_MFG_BASE+0x8e0));
    con_hex2("CSF mfg out","dsp2=",io->read32(io->context,SWEET_CSF_MFG_BASE+0x910),
             "out0=",io->read32(io->context,SWEET_CSF_MFG_BASE+0x900));
    con_hex("CSF mfg out slc6",io->read32(io->context,SWEET_CSF_MFG_BASE+0x748));
#endif
#if SWEET_CSF_OUT_OF_ARENA
    /* The ladder's four result slots, read back through the CPU's view of the
     * arena. Marker semantics live in the ladder header; the slots are the only
     * place both words survive when the second read never returns. */
    {
        const volatile uint32_t *slot=(const volatile uint32_t *)(uintptr_t)(arena+memory.shared_offset);
        con_hex2("CSF b9 g0","ctl=",slot[0x200/4],"tst=",slot[0x208/4]);
        con_hex2("CSF b9 g6","ctl=",slot[0x204/4],"tst=",slot[0x20c/4]);
    }
#endif
    con_hex2("CSF","stage=",shim_csf_report.stage,"error=",(uint32_t)shim_csf_report.error);
    con_hex2("CSF","version=",shim_csf_report.version,"mcu=",shim_csf_report.mcu_status);
    con_hex2("CSF start","ctl=",shim_csf_report.platform_reserved>>8,
             "back=",shim_csf_report.platform_reserved&0xff);
    con_hex2("CSF","mmu=",shim_csf_report.mmu_raw,"reset=",shim_csf_report.reset_raw);
    con_hex2("CSF memattr","lo=",shim_csf_report.memattr_lo,
             "hi=",shim_csf_report.memattr_hi);
#if SWEET_CSF_GLOBAL_INIT
    con_hex2("CSF global","flags=",shim_csf_global_evidence.flags,
             "err=",(uint32_t)shim_csf_global_evidence.error);
    con_hex2("CSF global ack","first=",shim_csf_global_evidence.ack_first,
             "last=",shim_csf_global_evidence.ack_last);
#endif
    return rc;
}
