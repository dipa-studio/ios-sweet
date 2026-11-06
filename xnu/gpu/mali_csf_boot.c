/* Independent bounded MCU boot transaction. Register facts cross-checked
 * against the device KMD and Linux v6.12 Panthor. No Linux APIs required. */
#include "mali_csf_boot.h"
static uint32_t rd(const struct sweet_gpu_io *io,uint64_t p) {return io->read32(io->context,p);}
static void wr(const struct sweet_gpu_io *io,uint64_t p,uint32_t v) {io->write32(io->context,p,v);io->barrier(io->context);}
static int poll(const struct sweet_gpu_io *io,uint64_t p,uint32_t mask,uint32_t value,uint64_t budget)
{
    uint64_t begin=io->ticks(io->context);
    for(uint32_t i=0;i<10000000;i++) {
        if((rd(io,p)&mask)==value)return 0;
        if(io->ticks(io->context)-begin>=budget)break;
    }
    return SWEET_CSF_BOOT_TIMEOUT;
}
static int as_command(const struct sweet_gpu_io *io,uint64_t gpu,uint32_t command,uint64_t budget)
{
    int rc=poll(io,gpu+0x2428,1,0,budget);
    if(!rc) {wr(io,gpu+0x2418,command);rc=poll(io,gpu+0x2428,1,0,budget);}
    return rc;
}
static void core_state(const struct sweet_gpu_io *io,uint64_t gpu,
                       struct sweet_csf_boot_report *r,uint32_t flag)
{
    r->shader_present_lo=rd(io,gpu+0x100);r->shader_present_hi=rd(io,gpu+0x104);
    r->shader_transition_lo=rd(io,gpu+0x200);r->shader_transition_hi=rd(io,gpu+0x204);
    r->shader_ready_lo=rd(io,gpu+0x140);r->shader_ready_hi=rd(io,gpu+0x144);
    r->tiler_present_lo=rd(io,gpu+0x110);r->tiler_present_hi=rd(io,gpu+0x114);
    r->tiler_transition_lo=rd(io,gpu+0x210);r->tiler_transition_hi=rd(io,gpu+0x214);
    r->tiler_ready_lo=rd(io,gpu+0x150);r->tiler_ready_hi=rd(io,gpu+0x154);
    r->sample_flags|=flag;
}
static void init_registers(const struct sweet_gpu_io *io,uint64_t gpu,
                           struct sweet_csf_boot_report *r,int after)
{
    uint32_t coherency=rd(io,gpu+0x304),csf=rd(io,gpu+0xf00);
    uint32_t shader=rd(io,gpu+0xf04),tiler=rd(io,gpu+0xf08),mmu=rd(io,gpu+0xf0c);
    if(after) {
        r->coherency_after=coherency;r->csf_config_after=csf;
        r->shader_config_after=shader;r->tiler_config_after=tiler;r->l2_mmu_config_after=mmu;
        r->diag_flags|=16;
    } else {
        r->coherency_features=rd(io,gpu+0x300);
        r->coherency_before=coherency;r->csf_config_before=csf;
        r->shader_config_before=shader;r->tiler_config_before=tiler;r->l2_mmu_config_before=mmu;
        r->diag_flags|=1;
    }
}
static void startup_memory(const struct sweet_csf_boot_config *c,const struct sweet_gpu_io *io,
                           struct sweet_csf_boot_report *r,int after)
{
    /* Exact pinned firmware writes:0202c934 @01002bce,0202c93e @01002c16,
     *0202c22c @01002f14 and shared04000018 @01002fd6. Sample aligned words
     * through caller-owned CPU PA, without modifying the firmware or arena. */
    if(c->private_probe_offset) {
        uint64_t page=c->arena_pa+c->private_probe_offset;
        uint32_t early=rd(io,page+0x934),feature=rd(io,page+0x93c),late=rd(io,page+0x22c);
        if(after) {r->private_early_after=early;r->private_feature_after=feature;r->private_late_after=late;}
        else {
            r->private_page_lo=(uint32_t)page;r->private_page_hi=(uint32_t)(page>>32);
            r->private_early_before=early;r->private_feature_before=feature;r->private_late_before=late;
        }
    }
    uint32_t value=rd(io,c->arena_pa+c->shared_offset+0x18);
    if(after) {r->shared_alloc_after=value;r->diag_flags|=8;}
    else {r->shared_alloc_before=value;r->diag_flags|=4;}
}
static void platform_state(const struct sweet_csf_boot_config *c,const struct sweet_gpu_io *io,
                            struct sweet_csf_boot_report *r,int after)
{
    if(!c->platform_snapshot)return;
    struct sweet_csf_platform_snapshot *s=after?&r->platform_after:&r->platform_before;
    s->gpu_status=rd(io,c->gpu+0x34);s->mcu_control=rd(io,c->gpu+0x700);
    s->gpu_fault_status=rd(io,c->gpu+0x3c);
    s->gpu_fault_lo=rd(io,c->gpu+0x40);s->gpu_fault_hi=rd(io,c->gpu+0x44);
    s->job_stat=rd(io,c->gpu+0x100c);
    /* Original vendor_boot/LK DT reg-names plus pinned MT6983 KMD dump
     * readers. Do not call the vendor dump routine:it also writes debug
     * selectors. No frequency-meter,rail,clock or power-domain writes. */
    s->spm_status=rd(io,0x1c001f3c);s->spm_status_second=rd(io,0x1c001f40);
    s->mfg_power0=rd(io,0x1c001eb8);s->mfg_power1=rd(io,0x1c001ebc);
    s->mfg_power2=rd(io,0x1c001ec0);s->mfg_power3=rd(io,0x1c001ec4);
    s->mfg_pll_con1=rd(io,0x13fa000c);s->mfgsc_pll_con1=rd(io,0x13fa0c0c);
    s->topckgen_sel=rd(io,0x100001f0);s->rpc_slp_protect=rd(io,0x13f91048);
    r->platform_sample_flags|=after?2:1;
}
static void access_state(const struct sweet_csf_boot_config *c,const struct sweet_gpu_io *io,
                         struct sweet_csf_boot_report *r,int after)
{
    if(!c->access_snapshot)return;
    struct sweet_csf_access_snapshot *s=after?&r->access_after:&r->access_before;
    s->mmu_raw=rd(io,c->gpu+0x2000);s->job_raw=rd(io,c->gpu+0x1000);
    /* AS0+04/+08/+0c are TRANSTAB_HI/MEMATTR,not fault registers. */
    s->as_status=rd(io,c->gpu+0x2428);s->as_fault=rd(io,c->gpu+0x241c);
    s->as_fault_lo=rd(io,c->gpu+0x2420);s->as_fault_hi=rd(io,c->gpu+0x2424);
    s->l2_ready_lo=rd(io,c->gpu+0x160);s->l2_ready_hi=rd(io,c->gpu+0x164);
    s->l2_transition_lo=rd(io,c->gpu+0x220);s->l2_transition_hi=rd(io,c->gpu+0x224);
    /* Native shim executes with CPU MMU/caches off;barrier publishes stores.
     * Never read the GPU VA through a CPU pointer or read write-only PWRON. */
    io->barrier(io->context);
    s->firmware_word0=rd(io,c->arena_pa+c->firmware_probe_offset);
    s->version=rd(io,c->arena_pa+c->shared_offset);
    if(c->entry_checkpoint) {
        uint32_t marker=rd(io,c->arena_pa+c->shared_offset+0xffc);
        if(after)r->path_reserved=marker;
        else r->access_reserved=marker;
    }
    r->access_sample_flags|=after?2:1;
}
static int platform_path(const struct sweet_csf_boot_config *c,const struct sweet_gpu_io *io,
                         struct sweet_csf_boot_report *r,int after)
{
    if(!c->platform_path)return 0;
    struct sweet_csf_path_snapshot *s=after?&r->path_after:&r->path_before;
    /* Original MT6983 scpsys MFG1 table: separate enable/status registers.
     * Clear offsets are1044/ca8/c68/c78;do not write them while GPUEB owns power.
     * Whole RPC1048 is NOT a low-enable/high-ack pair;only bits16..19 belong
     * to this domain's protection table. Unrelated set bits are preserved. */
    s->rpc_enable=rd(io,0x13f9103c);s->rpc_status=rd(io,0x13f91048);
    s->infra_enable=rd(io,0x10001ca0);s->infra_status=rd(io,0x10001cac);
    s->emi0_enable=rd(io,0x10001c60);s->emi0_status=rd(io,0x10001c6c);
    s->emi1_enable=rd(io,0x10001c70);s->emi1_status=rd(io,0x10001c7c);
    s->pdc_cg=rd(io,0x13fbf100);s->pdc_st0=rd(io,0x13fbf120);
    s->pdc_st1=rd(io,0x13fbf140);s->pdc_st2=rd(io,0x13fbf118);
    s->pdc_st4=rd(io,0x13fbf0c0);s->pdc_st5=rd(io,0x13fbf098);
    s->pdc_st6=rd(io,0x13fbf1c0);s->slc_group6=rd(io,0x13fbf748);
    r->path_sample_flags|=after?2:1;
    /* Observation only for PDC/SLC: no readiness inference from those words. */
    return ((s->rpc_enable|s->rpc_status)&0xf0000) ||
        ((s->infra_enable|s->infra_status)&0xf) ||
        ((s->emi0_enable|s->emi0_status|s->emi1_enable|s->emi1_status)&0xc0000);
}
int sweet_csf_boot(const struct sweet_csf_boot_config *c,const struct sweet_gpu_io *io,
                   struct sweet_csf_boot_report *r)
{
    uint32_t gpu_mask=0,job_mask=0,mmu_mask=0;
    uint64_t budget;
    int rc;
    if(!r)return SWEET_CSF_BOOT_ARGUMENT;
    *r=(struct sweet_csf_boot_report){.stage=SWEET_CSF_BOOT_CONFIG};
    if(!c||!io||!io->read32||!io->write32||!io->ticks||!io->barrier||
       !io->frequency||io->frequency>1000000000||c->gpu!=0x13000000||
       !c->timeout_ms||c->timeout_ms>1000||c->noncoherent>1||c->vendor_ina0>1||
       c->vendor_cached_memattr>1||c->platform_snapshot>1||c->access_snapshot>1||c->platform_path>1||
       c->entry_checkpoint>1||(c->entry_checkpoint&&!c->access_snapshot)||
       (c->mcu_control_value&&c->mcu_control_value!=2&&c->mcu_control_value!=3)||
       c->pte_group_requested>15||
       c->pte_pages_built>c->arena_bytes/4096||c->root_pa!=c->arena_pa||
       c->arena_pa<0x40000000||(c->arena_pa&4095)||!c->arena_bytes||
       c->arena_bytes>0x1000000||c->arena_pa>UINT64_MAX-c->arena_bytes||
       c->shared_bytes<4096||(c->shared_offset&4095)||
       c->shared_offset>c->arena_bytes||c->shared_bytes>c->arena_bytes-c->shared_offset||
       (c->private_probe_offset&&((c->private_probe_offset&4095)||
        c->private_probe_offset>c->arena_bytes||4096>c->arena_bytes-c->private_probe_offset||
        (c->private_probe_offset<(uint64_t)c->shared_offset+c->shared_bytes&&
         c->shared_offset<(uint64_t)c->private_probe_offset+4096)))||
       (c->platform_path&&!c->access_snapshot)||
       (c->access_snapshot&&(!c->platform_snapshot||c->firmware_probe_va!=0x01000000||
        c->firmware_probe_offset<4096||(c->firmware_probe_offset&4095)||
        c->firmware_probe_offset>c->arena_bytes||
        4096>c->arena_bytes-c->firmware_probe_offset||
        (c->firmware_probe_offset<(uint64_t)c->shared_offset+c->shared_bytes&&
         c->shared_offset<(uint64_t)c->firmware_probe_offset+4096)))) {
        r->error=SWEET_CSF_BOOT_ARGUMENT;return r->error;
    }
    budget=(io->frequency*c->timeout_ms+999)/1000;
    r->pte_group_requested=c->pte_group_requested;r->pte_pages_built=c->pte_pages_built;
    if(c->access_snapshot) {
        uint64_t pa=c->arena_pa+c->firmware_probe_offset;
        r->firmware_probe_va=c->firmware_probe_va;r->firmware_probe_expected=c->firmware_probe_expected;
        r->firmware_probe_pa_lo=(uint32_t)pa;r->firmware_probe_pa_hi=(uint32_t)(pa>>32);
    }
    /* Caller must already own power; do not probe a powered-off GPU. */
    if((rd(io,0x1c001f3c)&rd(io,0x1c001f40)&6)!=6) {
        r->error=SWEET_CSF_BOOT_STATE;return r->error;
    }
    r->as_present=rd(io,c->gpu+0x18);
    if(rd(io,c->gpu)!=0xa8620004 || r->as_present==UINT32_MAX || !(r->as_present&1)) {
        r->error=SWEET_CSF_BOOT_MODEL;return r->error;
    }
    r->mmu_features=rd(io,c->gpu+0x14);
    unsigned va_bits=r->mmu_features&255,pa_bits=(r->mmu_features>>8)&255;
    if(va_bits!=SWEET_CSF_VA_BITS||pa_bits<32||pa_bits>48||
       c->arena_pa>=(UINT64_C(1)<<pa_bits)||c->arena_bytes>(UINT64_C(1)<<pa_bits)-c->arena_pa) {
        r->error=SWEET_CSF_BOOT_MODEL;return r->error;
    }
    uint32_t address_mode=rd(io,c->gpu+0x2430)&15;
    /* Reset implementations may expose legacy mode0 or unmapped mode1.
     * Never replace a live table. Establish unmapped explicitly below. */
    if(rd(io,c->gpu+0x704)!=0 || (rd(io,c->gpu+0x34)&0x80) ||
       address_mode>1 || rd(io,c->gpu+0x2400) || rd(io,c->gpu+0x2404)) {
        r->error=SWEET_CSF_BOOT_STATE;return r->error;
    }
    init_registers(io,c->gpu,r,0);
    gpu_mask=rd(io,c->gpu+0x28);job_mask=rd(io,c->gpu+0x1008);mmu_mask=rd(io,c->gpu+0x2008);
    wr(io,c->gpu+0x28,0);wr(io,c->gpu+0x1008,0);wr(io,c->gpu+0x2008,0);
    if(c->noncoherent) {
        /* Pinned vendor KMD kbase_device_coherency_init defaults to31;
         * kbase_cache_set_coherency_mode writes it to GPU+304 for this
         * model (feature19). NONE is a protocol selector, not a bitmask
         * of COHERENCY_FEATURES. Keep PTE/MEMATTR/TRANSCFG unchanged. */
        r->coherency_requested=31;r->diag_flags|=32;
        wr(io,c->gpu+0x304,r->coherency_requested);
        r->coherency_readback=rd(io,c->gpu+0x304);
        if(r->coherency_readback!=r->coherency_requested) {
            r->error=SWEET_CSF_BOOT_STATE;goto cleanup;
        }
        r->diag_flags|=64;
    }
    r->stage=SWEET_CSF_BOOT_L2;
    r->l2_present=rd(io,c->gpu+0x120);r->l2_present_hi=rd(io,c->gpu+0x124);
    if(!(r->l2_present&1)) {r->error=SWEET_CSF_BOOT_MODEL;goto cleanup;}
    rc=poll(io,c->gpu+0x220,1,0,budget);
    if(rc) {r->error=rc;goto cleanup;}
    wr(io,c->gpu+0x1a0,1);
    rc=poll(io,c->gpu+0x160,1,1,budget);r->l2_ready=rd(io,c->gpu+0x160);
    if(rc) {r->error=rc;goto cleanup;}
    r->stage=SWEET_CSF_BOOT_AS;
    wr(io,c->gpu+0x2430,1);wr(io,c->gpu+0x2434,0);
    rc=as_command(io,c->gpu,1,budget);
    if(rc) {r->error=rc;goto cleanup;}
    /* Lock the full48-bit MCU address space before FLUSH_MEM. */
    wr(io,c->gpu+0x2410,SWEET_CSF_VA_BITS-1);wr(io,c->gpu+0x2414,0);
    rc=as_command(io,c->gpu,2,budget);
    if(!rc)rc=as_command(io,c->gpu,5,budget);
    if(rc) {r->error=rc;goto cleanup;}
    wr(io,c->gpu+0x2400,(uint32_t)c->root_pa);wr(io,c->gpu+0x2404,(uint32_t)(c->root_pa>>32));
    /* The vendor uses byte88 at index0 for cached leaves and byte4c
     * at index5 for shared leaves. Our existing PTEs instead select1/0.
     * Isolate cached byte only; copying the whole vendor register would
     * select8f for cached and88 for shared. No PTE or page-walk change. */
    uint32_t memattr_lo=c->vendor_cached_memattr?0x4c4c884c:0x4c4c9f4c;
    wr(io,c->gpu+0x2408,memattr_lo);wr(io,c->gpu+0x240c,0x4c4c4c4c);
    /* Pinned KMD MMIO slice45e80..45fd4 writes42000006 under protocol31.
     * INA selection is independent of the cached MEMATTR diagnostic. */
    uint32_t transcfg=0x42000006|(c->vendor_ina0?0:((55-SWEET_CSF_VA_BITS)<<6));
    wr(io,c->gpu+0x2430,transcfg);wr(io,c->gpu+0x2434,0);
    rc=as_command(io,c->gpu,1,budget);
    if(rc) {r->error=rc;goto cleanup;}
    r->transcfg_lo=rd(io,c->gpu+0x2430);
    r->transtab_lo=rd(io,c->gpu+0x2400);r->transtab_hi=rd(io,c->gpu+0x2404);
    r->memattr_lo=rd(io,c->gpu+0x2408);r->memattr_hi=rd(io,c->gpu+0x240c);r->diag_flags|=2;
    if(r->transcfg_lo!=transcfg||rd(io,c->gpu+0x2434)||
       r->transtab_lo!=(uint32_t)c->root_pa||r->transtab_hi!=(uint32_t)(c->root_pa>>32)||
       (c->vendor_cached_memattr&&(r->memattr_lo!=memattr_lo||r->memattr_hi!=0x4c4c4c4c))) {
        r->error=SWEET_CSF_BOOT_STATE;goto cleanup;
    }
    wr(io,c->gpu+0x2004,0x10001);wr(io,c->gpu+0x1004,0x80000000);
    if(rd(io,c->gpu+0x1000)&0x80000000) {r->error=SWEET_CSF_BOOT_STATE;goto cleanup;}
    uint64_t shared=c->arena_pa+c->shared_offset;
    io->barrier(io->context);
    r->version_before=rd(io,shared);r->sample_flags|=1;
    startup_memory(c,io,r,0);
    /* Match the measured r32p1 internal interrupt enables before MCU AUTO.
     * CPU DAIF stays masked and GIC routing is untouched: the host still
     * polls RAW. Whether these enables fix2323 is a hardware hypothesis. */
    wr(io,c->gpu+0x24,0x80503);
    wr(io,c->gpu+0x28,0x80503);
    wr(io,c->gpu+0x1008,UINT32_MAX);
    wr(io,c->gpu+0x2008,0xffff);
    r->job_irq_mask=rd(io,c->gpu+0x1008);
    r->gpu_irq_mask=rd(io,c->gpu+0x28);r->mmu_irq_mask=rd(io,c->gpu+0x2008);
    core_state(io,c->gpu,r,4);
    /* Reserved/unimplemented bits may read zero. Require the fault/reset
     * sources, global JOB IRQ and page-fault bits for present AS slots.
     * The full requested/read masks remain evidence, never synthesized. */
    uint32_t required_mmu=r->as_present&0xffff;
    if(!(r->job_irq_mask&0x80000000) || (r->gpu_irq_mask&0x103)!=0x103 ||
       (r->mmu_irq_mask&required_mmu)!=required_mmu) {
        r->error=SWEET_CSF_BOOT_STATE;goto cleanup;
    }
    r->irq_gate_passed=1;
    r->stage=SWEET_CSF_BOOT_HALT;
    platform_state(c,io,r,0);
    access_state(c,io,r,0);
    if(platform_path(c,io,r,0)) {
        r->error=SWEET_CSF_BOOT_STATE;goto cleanup;
    }
    /* Drive the MCU to a halt we measured ourselves before starting it. The
     * entry check above already required MCU_STATUS==0, but that is a state
     * this transaction inherited; the vendor driver halts the MCU explicitly
     * before it loads and starts firmware, and a stale AUTO bit from an
     * earlier aborted boot would survive a bare STATUS read. Polling after
     * the write is what turns the assumption into evidence. */
    wr(io,c->gpu+0x700,0);
    r->mcu_status=rd(io,c->gpu+0x704);
    if(r->mcu_status) {
        rc=poll(io,c->gpu+0x704,UINT32_MAX,0,budget);
        r->mcu_status=rd(io,c->gpu+0x704);
        if(rc) {r->error=SWEET_CSF_BOOT_STATE;goto cleanup;}
    }
    r->stage=SWEET_CSF_BOOT_MCU;
    /* Vendor kbase_csf_firmware_enable_mcu writes ENABLE|AUTO(3). Every build
     * up to2371 wrote AUTO alone(2); keeping that value available behind a
     * config word means a trial moves exactly one number. The written and
     * immediately read-back bytes go to platform_reserved so the696-byte
     * report ABI stays unchanged. path_reserved keeps its2335 checkpoint
     * meaning; do not reuse it here. */
    uint32_t control=c->mcu_control_value?c->mcu_control_value:3;
    wr(io,c->gpu+0x700,control);
    r->platform_reserved=(control<<8)|(rd(io,c->gpu+0x700)&0xff);
    uint64_t begin=io->ticks(io->context);
    rc=SWEET_CSF_BOOT_TIMEOUT;
    for(uint32_t i=0;i<10000000;i++) {
        r->mcu_status=rd(io,c->gpu+0x704);r->mmu_raw=rd(io,c->gpu+0x2000);
        r->job_raw=rd(io,c->gpu+0x1000);
        /* Any status bit other than ENABLED(1) means the MCU did not take the
         * start value: the old code faulted on3 only, and3 is ENABLED|HALTED.
         * CSF MMU upper16 bits are request completion, not page faults. */
        if((r->mmu_raw&0xffff) || (r->mcu_status&~1u) || (rd(io,c->gpu+0x20)&3)) {rc=SWEET_CSF_BOOT_FAULT;break;}
        if(r->job_raw&0x80000000) {rc=0;break;}
        if(io->ticks(io->context)-begin>=budget)break;
    }
    r->as_fault=rd(io,c->gpu+0x241c);r->as_fault_lo=rd(io,c->gpu+0x2420);r->as_fault_hi=rd(io,c->gpu+0x2424);
    r->gpu_raw=rd(io,c->gpu+0x20);r->as_status=rd(io,c->gpu+0x2428);
    /* Shared host PA is validated and CPU-readable independent of GPU
     * translation. Capture it even on timeout, before disable/reset. */
    io->barrier(io->context);
    r->version=rd(io,shared);r->features=rd(io,shared+4);
    r->input_va=rd(io,shared+8);r->output_va=rd(io,shared+12);
    r->groups=rd(io,shared+16);r->group_stride=rd(io,shared+20);
    r->sample_flags|=2;
    startup_memory(c,io,r,1);
    init_registers(io,c->gpu,r,1);
    core_state(io,c->gpu,r,8);
    platform_state(c,io,r,1);
    access_state(c,io,r,1);
    if(platform_path(c,io,r,1)&&!rc)rc=SWEET_CSF_BOOT_STATE;
    if(rc) {r->error=rc;goto cleanup;}
    r->stage=SWEET_CSF_BOOT_IFACE;
    /* An input/output page and every CSG control block must fit shared. */
    uint64_t end=UINT64_C(0x4000000)+c->shared_bytes;
    if(!r->version||r->version==UINT32_MAX||r->mcu_status!=1||
       (r->input_va&3)||(r->output_va&3)||r->input_va==r->output_va||
       r->input_va<0x4000000||r->output_va<0x4000000||
       (uint64_t)r->input_va+4096>end||(uint64_t)r->output_va+4096>end||
       !r->groups||r->groups>31||r->group_stride<32||(r->group_stride&3)||
       0x1000+(uint64_t)r->groups*r->group_stride>c->shared_bytes) {
        r->error=SWEET_CSF_BOOT_INTERFACE;goto cleanup;
    }
    r->firmware_ready=1;
cleanup:
    /* GPU reset stops DMA and discards AS0/L2 state before the caller
     * releases its GPUEB reference. Never reclaim arena on failed reset. */
    wr(io,c->gpu+0x700,0);
    r->disable_error=poll(io,c->gpu+0x704,UINT32_MAX,0,budget);
    r->disable_status=rd(io,c->gpu+0x704);
    if(r->disable_error)r->cleanup_error=r->disable_error;
    wr(io,c->gpu+0x24,0x100);wr(io,c->gpu+0x30,0x101);
    rc=poll(io,c->gpu+0x20,0x100,0x100,budget);
    r->reset_raw=rd(io,c->gpu+0x20);
    if(rc)r->cleanup_error=rc;
    else {r->reset_completed=1;wr(io,c->gpu+0x24,0x100);}
    wr(io,c->gpu+0x28,gpu_mask);wr(io,c->gpu+0x1008,job_mask);wr(io,c->gpu+0x2008,mmu_mask);
    if(r->cleanup_error&&!r->error) {r->stage=SWEET_CSF_BOOT_CLEANUP;r->error=r->cleanup_error;}
    if(!r->error)r->stage=SWEET_CSF_BOOT_COMPLETE;
    return r->error;
}
