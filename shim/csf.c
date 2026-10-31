/* CSF probe arena is part of the shim's own linked BSS, below its payload.
 * It never borrows GPUEB reservations or the XNU RAM window. */
#include "csf.h"
#include "console.h"

static uint8_t arena[2u<<20] __attribute__((aligned(4096)));
extern const uint8_t sweet_csf_blob_start[],sweet_csf_blob_end[];
struct sweet_csf_boot_report shim_csf_report;
_Static_assert(sizeof(struct sweet_csf_boot_report)==304, "CSF2330 report ABI unchanged");
static int overlap(uint64_t a,uint64_t n,uint64_t b,uint64_t m)
{
    if(!n||!m||a>UINT64_MAX-n||b>UINT64_MAX-m)return 1;
    return a<b+m && b<a+n;
}
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
    io->barrier(io->context); /* Native shim has MMU and CPU caches off. */
    struct sweet_csf_boot_config c={.gpu=gpu,.root_pa=root,.arena_pa=pa,
        .arena_bytes=memory.required_bytes,.shared_offset=memory.shared_offset,
        .shared_bytes=memory.shared_bytes,.timeout_ms=1000,.noncoherent=1,
        .pte_group_requested=6,.vendor_ina0=1,.vendor_cached_memattr=1};
    for(uint32_t i=0;i<memory.mapping_count;i++) {
        const struct sweet_csf_mapping *m=&memory.map[i];
        c.pte_pages_built+=m->bytes/4096;
        if(m->va<=0x0202c000 && (uint64_t)m->va+m->bytes>=0x0202d000 && (m->flags&3)==3)
            c.private_probe_offset=m->arena_offset+0x0202c000-m->va;
    }
    if(!c.private_probe_offset) {shim_csf_report.error=SWEET_CSF_BOOT_ARGUMENT;return shim_csf_report.error;}
    rc=sweet_csf_boot(&c,io,&shim_csf_report);
    con_hex2("CSF","stage=",shim_csf_report.stage,"error=",(uint32_t)shim_csf_report.error);
    con_hex2("CSF","version=",shim_csf_report.version,"mcu=",shim_csf_report.mcu_status);
    con_hex2("CSF","mmu=",shim_csf_report.mmu_raw,"reset=",shim_csf_report.reset_raw);
    return rc;
}
