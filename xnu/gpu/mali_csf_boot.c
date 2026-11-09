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
#if SWEET_CSF_GPU_REGS && SWEET_CSF_GLOBAL_RELAY
    /* 2426: this carrier is populated after global_init, not by GPU reads. */
#elif SWEET_CSF_GPU_REGS && SWEET_CSF_STORE_WITNESS
    {
        struct sweet_csf_gpu_regs *g=after?&r->gpu_regs_after:&r->gpu_regs_before;
        uint64_t shared=c->arena_pa+c->shared_offset;
        io->barrier(io->context);
        g->slot200=rd(io,shared+0x200);g->slot400=rd(io,shared+0x400);
        g->marker=rd(io,shared+8);g->result=rd(io,shared+12);
        g->target_pa_lo=(uint32_t)(shared+0x200);
        g->target_pa_hi=(uint32_t)((shared+0x200)>>32);
        g->control_pa_lo=(uint32_t)(shared+0x400);
        g->control_pa_hi=(uint32_t)((shared+0x400)>>32);
#if SWEET_CSF_L2_HASH8
        /* 2421 reuses the seed labels for the pre/post L2_CONFIG readback. */
        g->seed200=r->gpu_regs_before.seed200;
        g->seed400=r->gpu_regs_before.seed400;
#else
        g->seed200=0x24205200;g->seed400=0x24205400;
#endif
        r->gpu_regs_flags|=after?2:1;
    }
#elif SWEET_CSF_GPU_REGS && SWEET_CSF_SLC_GROUPS
    /*2417: the base word of groups0..9, once, after the MCU start. 2416 read
     *five words of this same page before and after and got identical values,
     *so the page is configuration and one post-start snapshot buys ten groups
     *instead of five words twice. The vendor layout is not uniform: group0 is
     *a single word at0x700, groups1..15 are triplets (base, limit, policy)
     *from0x704 with a12-byte stride, so the bases are
     *0x704 + 12*(N-1) for N>=1. Getting that one step wrong is exactly what
     *this build exists to detect, hence the table below is spelled out rather
     *than computed. Nothing here is written by this build. */
    if(after) {
        struct sweet_csf_gpu_regs *g=&r->gpu_regs_after;
        static const uint16_t group_word[10]={0x700,0x704,0x710,0x71c,0x728,
                                              0x734,0x740,0x74c,0x758,0x764};
        uint32_t v[10];
        for(unsigned i=0;i<10;i++)v[i]=rd(io,SWEET_CSF_MFG_BASE+group_word[i]);
        g->g0_word=v[0];g->g1_base=v[1];g->g2_base=v[2];g->g3_base=v[3];
        g->g4_base=v[4];g->g5_base=v[5];g->g6_base=v[6];g->g7_base=v[7];
        g->g8_base=v[8];g->g9_base=v[9];
        /*Bit2 = this snapshot exists; bit1 stays clear because there is no
         *before pass to claim. diag bit15 says the same thing in the flags
         *word the decoder already validates. */
        r->gpu_regs_flags|=2;
        r->diag_flags|=32768;
    }
#elif SWEET_CSF_GPU_REGS && SWEET_CSF_SLC_WINDOW
    /*2416: the SLC group window, read only. 0x740/0x744 are group6's base and
     *limit and 0x748 its policy - the three words __gpufreq_slc_control()
     *writes for the group the firmware tags every leaf with. 0x700 is group0's
     *default word and 0x74C group7's base: the neighbours that make an
     *off-by-one group index visible. Nothing here is written by this build, so
     *before and after should agree; a difference is the finding. */
    {struct sweet_csf_gpu_regs *g=after?&r->gpu_regs_after:&r->gpu_regs_before;
     uint32_t b0=rd(io,SWEET_CSF_MFG_BASE+0x700);
     uint32_t b1=rd(io,SWEET_CSF_MFG_BASE+0x740);
     uint32_t b2=rd(io,SWEET_CSF_MFG_BASE+0x744);
     uint32_t b3=rd(io,SWEET_CSF_MFG_BASE+0x748);
     uint32_t b4=rd(io,SWEET_CSF_MFG_BASE+0x74c);
     if(after) {g->g0_after=b0;g->g6_base_after=b1;g->g6_limit_after=b2;
                g->g6_ctl_after=b3;g->g7_base_after=b4;}
     else      {g->g0_before=b0;g->g6_base_before=b1;g->g6_limit_before=b2;
                g->g6_ctl_before=b3;g->g7_base_before=b4;}
     r->gpu_regs_flags|=after?2:1;}
#elif SWEET_CSF_GPU_REGS && !SWEET_CSF_DISPATCH_SURVEY && !SWEET_CSF_DISPATCH_READBACK
    /*2407: raw GPU words, offsets only. 0x048 is the L2 config the dual-slice
     *hypothesis hangs on;0x2c0.. is what the vendor dump reads beside it. Read
     *both states so a value that only exists while powered is visible. */
    {struct sweet_csf_gpu_regs *g=after?&r->gpu_regs_after:&r->gpu_regs_before;
     g->reg_000=rd(io,c->gpu+0x000);g->reg_004=rd(io,c->gpu+0x004);
     g->reg_00c=rd(io,c->gpu+0x00c);g->reg_034=rd(io,c->gpu+0x034);
     g->reg_048=rd(io,c->gpu+0x048);g->reg_04c=rd(io,c->gpu+0x04c);
     g->reg_2c0=rd(io,c->gpu+0x2c0);g->reg_2c4=rd(io,c->gpu+0x2c4);
     g->reg_2c8=rd(io,c->gpu+0x2c8);g->reg_2cc=rd(io,c->gpu+0x2cc);
     r->gpu_regs_flags|=after?2:1;}
#endif
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
#if SWEET_CSF_EMI_DIAG
    /* 2423: gpufreq_mt6983.c __gpufreq_dump_infra_status() reads these
     * north/south EMI GALS and M6/M7 idle words. Reuse the eight PDC/SLC
     * diagnostic slots; the protection gate above and CPU witness stay intact.
     * Raw observation only: no debug selector or fabric control is written. */
    s->pdc_cg=rd(io,0x1021c82c);s->pdc_st0=rd(io,0x1021c830);
    s->pdc_st1=rd(io,0x1021e82c);s->pdc_st2=rd(io,0x1021e830);
    s->pdc_st4=rd(io,0x10270228);s->pdc_st5=rd(io,0x1027022c);
    s->pdc_st6=rd(io,0x1030e228);s->slc_group6=rd(io,0x1030e22c);
#else
    s->pdc_cg=rd(io,0x13fbf100);s->pdc_st0=rd(io,0x13fbf120);
    s->pdc_st1=rd(io,0x13fbf140);s->pdc_st2=rd(io,0x13fbf118);
    s->pdc_st4=rd(io,0x13fbf0c0);s->pdc_st5=rd(io,0x13fbf098);
    s->pdc_st6=rd(io,0x13fbf1c0);s->slc_group6=rd(io,0x13fbf748);
#endif
#if SWEET_CSF_EMI_KEEP_PDC
    /* 2424 restores all eight reads removed by2423, after the EMI reads.
     * Distinguish priming by added reads from side effects of removed reads. */
    (void)rd(io,0x13fbf100);(void)rd(io,0x13fbf120);
    (void)rd(io,0x13fbf140);(void)rd(io,0x13fbf118);
    (void)rd(io,0x13fbf0c0);(void)rd(io,0x13fbf098);
    (void)rd(io,0x13fbf1c0);(void)rd(io,0x13fbf748);
#endif
    r->path_sample_flags|=after?2:1;
    /* Observation only for PDC/SLC: no readiness inference from those words. */
    return ((s->rpc_enable|s->rpc_status)&0xf0000) ||
        ((s->infra_enable|s->infra_status)&0xf) ||
        ((s->emi0_enable|s->emi0_status|s->emi1_enable|s->emi1_status)&0xc0000);
}
#if SWEET_CSF_GLOBAL_INIT
/*2381 global interface field offsets, pinned by panthor_fw.h
 * panthor_fw_global_input_iface and by the r32p1 global_init() code:
 * 0x00 req, 0x04 ack_irq_mask, 0x10 progress_timer, 0x14 poweroff_timer,
 * 0x18/0x1c core_en_mask lo/hi, 0x20 protm_coherency, 0x80 idle_timer.
 * The output page carries ack at 0x00. */
#define SWEET_CSF_GLB_REQ        0x00u
#define SWEET_CSF_GLB_ACK_IRQ    0x04u
#define SWEET_CSF_GLB_PROGRESS   0x10u
#define SWEET_CSF_GLB_PWROFF     0x14u
#define SWEET_CSF_GLB_ALLOC_LO   0x18u
#define SWEET_CSF_GLB_ALLOC_HI   0x1cu
#define SWEET_CSF_GLB_PROTM      0x20u
#define SWEET_CSF_GLB_IDLE       0x80u
/* CSF_GLB_REQ_CFG_MASK (firmware-r32p1.c:117) = ALLOC_EN|PROGRESS_TIMER|
 * PWROFF_TIMER|IDLE_ENABLE = 0x40e. Only these bits are toggled and waited on;
 * enabling the idle timer also pins bit10 directly, as panthor does. */
#define SWEET_CSF_GLB_REQ_CFG    0x40eu
#define SWEET_CSF_GLB_IDLE_EN    0x400u
/* Vendor ack-mask immediate read from global_init (text0x6dec0). */
#define SWEET_CSF_GLB_ACK_MASK   0x0480071eu
/* PROGRESS_TIMEOUT_CYCLES(5*500*1024*1024)>>10, panthor_fw.c:30. */
#define SWEET_CSF_GLB_TIMER      0x00271000u
#define SWEET_CSF_DOORBELL0      0x80000u

/* Program the global interface the way kbase global_init()/global_init_on_boot()
 * do, then ring the kernel doorbell and wait for GLB_ACK. Runs only after the
 * existing interface gate proved version/input/output/groups, so no write here
 * can execute against an unbooted MCU. */
static int csf_global_init(const struct sweet_csf_boot_config *c,const struct sweet_gpu_io *io,
                           struct sweet_csf_boot_report *r,uint64_t budget)
{
    struct sweet_csf_global_evidence *e;
    uint64_t end;
    if(!c||!c->global_evidence||c->shared_va!=0x04000000u) return SWEET_CSF_BOOT_ARGUMENT;
    e=c->global_evidence;
    end=(uint64_t)c->shared_va+c->shared_bytes;
    e->input_va=r->input_va;e->output_va=r->output_va;
    /* The first page of the shared section is the global control page that
     * carries version/features/input_va/output_va. Neither interface page may
     * alias it, or the writes below would corrupt the firmware's own header. */
    if((r->input_va&4095)||(r->output_va&4095)||r->input_va==r->output_va||
       r->input_va==c->shared_va||r->output_va==c->shared_va||
       r->input_va<c->shared_va||r->output_va<c->shared_va||
       (uint64_t)r->input_va+4096>end||(uint64_t)r->output_va+4096>end) {
        e->flags|=8;e->error=SWEET_CSF_BOOT_INTERFACE;return e->error;
    }
    uint64_t in=c->arena_pa+c->shared_offset+(r->input_va-c->shared_va);
    uint64_t out=c->arena_pa+c->shared_offset+(r->output_va-c->shared_va);
    if(in<c->arena_pa||out<c->arena_pa||
       in+0x100>c->arena_pa+c->arena_bytes||out+0x100>c->arena_pa+c->arena_bytes) {
        e->flags|=8;e->error=SWEET_CSF_BOOT_INTERFACE;return e->error;
    }
    e->input_pa_lo=(uint32_t)in;e->input_pa_hi=(uint32_t)(in>>32);
    e->output_pa_lo=(uint32_t)out;e->output_pa_hi=(uint32_t)(out>>32);
    io->barrier(io->context);
    e->req_before=rd(io,in+SWEET_CSF_GLB_REQ);
    e->ack_before=rd(io,out+SWEET_CSF_GLB_REQ);
    /* Same protocol selector written to GPU+0x304: vendor system_coherency
     * NONE(31) on this platform. Recorded, not inferred from a readback. */
    e->protm_coherency=31;
    e->alloc_en_lo=r->shader_present_lo;e->alloc_en_hi=r->shader_present_hi;
    e->progress_timer=SWEET_CSF_GLB_TIMER;
    e->pwroff_timer=SWEET_CSF_GLB_TIMER;
    e->idle_timer=SWEET_CSF_GLB_TIMER;
    e->ack_irq_mask=SWEET_CSF_GLB_ACK_MASK;
    e->req_mask=SWEET_CSF_GLB_REQ_CFG;
    wr(io,in+SWEET_CSF_GLB_PROTM,e->protm_coherency);
    wr(io,in+SWEET_CSF_GLB_ALLOC_LO,e->alloc_en_lo);
    wr(io,in+SWEET_CSF_GLB_ALLOC_HI,e->alloc_en_hi);
    wr(io,in+SWEET_CSF_GLB_PWROFF,e->pwroff_timer);
    wr(io,in+SWEET_CSF_GLB_PROGRESS,e->progress_timer);
    wr(io,in+SWEET_CSF_GLB_IDLE,e->idle_timer);
    wr(io,in+SWEET_CSF_GLB_ACK_IRQ,e->ack_irq_mask);
    /* panthor_fw_toggle_reqs(): toggle the CFG bits against the firmware's own
     * ACK, then pin IDLE_EN, then ring doorbell 0. */
    uint32_t req=e->req_before;
    e->req_written=(req&~SWEET_CSF_GLB_REQ_CFG)|
        ((e->ack_before^SWEET_CSF_GLB_REQ_CFG)&SWEET_CSF_GLB_REQ_CFG)|
        SWEET_CSF_GLB_IDLE_EN;
    wr(io,in+SWEET_CSF_GLB_REQ,e->req_written);
    io->barrier(io->context);
    e->flags|=1;
    r->stage=SWEET_CSF_BOOT_GLOBAL_ACK;
    e->doorbell_value=1;
    wr(io,c->gpu+SWEET_CSF_DOORBELL0,e->doorbell_value);
    io->barrier(io->context);
    e->flags|=2;
    uint64_t begin=io->ticks(io->context);
    for(uint32_t i=0;i<10000000;i++) {
        uint32_t ack=rd(io,out+SWEET_CSF_GLB_REQ);
        if(!e->polls)e->ack_first=ack;
        e->ack_last=ack;e->polls++;
        if((ack&SWEET_CSF_GLB_REQ_CFG)==(e->req_written&SWEET_CSF_GLB_REQ_CFG)) {
            e->flags|=4;e->ack_matched=1;return 0;
        }
        if(io->ticks(io->context)-begin>=budget)break;
    }
    e->error=SWEET_CSF_BOOT_TIMEOUT;
    return e->error;
}
#endif
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
       c->global_init>1||(!SWEET_CSF_GLOBAL_INIT&&c->global_init)||
       (c->global_init&&(!c->global_evidence||c->shared_va!=0x04000000u))||
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
#if SWEET_CSF_PRESTART_RESET
    /*2408 follows panthor_gpu_soft_reset() on the path where panthor really
     *does reset before it touches an address space: panthor_device_reset_work()
     *runs fw_pre_reset -> mmu_pre_reset -> hw_soft_reset -> l2_power_on ->
     *mmu_post_reset -> fw_post_reset, and panthor_device_resume() reaches the
     *same op through panthor_gpu_suspend(). (The cold panthor_device_init()
     *does not reset: it trusts the bootloader. Never cite it as the invariant.)
     *This transaction never reset at all, and 2407 recorded GPU_STATUS=0x100
     *both before and after its attempt - DBG_ENABLED(BIT(8),
     *panthor_gpu_regs.h) never cleared - with a stale RESET_COMPLETED pending.
     *So the reset is issued here, after the register snapshot and before the
     *coherency write, the L2 power-on or any AS command.
     *Order is panthor's own: INT_CLEAR is write-one-to-clear, BIT(8) is cleared
     *first, then GPU_CMD=GPU_SOFT_RESET(GPU_CMD_DEF(1,1)=0x101), then
     *RESET_COMPLETED=BIT(8) within 100 ms.
     *Evidence is diag_flags bit7 attempt, bit8 completion, bit9 DBG_ENABLED
     *before, bit10 DBG_ENABLED after. The report struct has no gpu_status
     *word (that name lives in sweet_csf_platform_snapshot), so no field is
     *invented here: the later 0x34 reads land in gpu_regs_before/after via
     *platform_state(), which is the same word sampled again after this reset
     *and after the AS setup. 784-byte ABI, reset_raw and reset_completed
     *stay exactly as they were.
     *A timeout is recorded, not swallowed: the transaction runs on so one
     *boot answers both questions. */
    {
        int reset_ok;
        uint64_t reset_budget=(uint64_t)io->frequency*100/1000;
        if(!reset_budget)reset_budget=1;
        if(reset_budget>budget)reset_budget=budget;
        r->diag_flags|=128;
        if(rd(io,c->gpu+0x34)&0x100)r->diag_flags|=512;
        wr(io,c->gpu+0x24,0x100);
        wr(io,c->gpu+0x30,0x101);
        reset_ok=(poll(io,c->gpu+0x20,0x100,0x100,reset_budget)==0);
        if(reset_ok) {
            r->diag_flags|=256;
            wr(io,c->gpu+0x24,0x100);
        }
        if(rd(io,c->gpu+0x34)&0x100)r->diag_flags|=1024;
    }
#endif
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
#if SWEET_CSF_L2_HASH8
    /* r32p1 kbase_pm_l2_config_override(): hash in bits31:24, before L2 ON.
     * kbase_read_l2_config_from_dt permits user selectors 8..15. This is a
     * diagnostic for arch10's hash, NOT arch11+ ASN_HASH enable/coefficients. */
    if(rd(io,c->gpu+0x160)&1) {r->error=SWEET_CSF_BOOT_STATE;goto cleanup;}
    uint32_t l2_config=rd(io,c->gpu+0x48);
    uint32_t l2_hash8=(l2_config&0x00ffffffu)|0x08000000u;
    r->gpu_regs_before.seed200=l2_config;
    wr(io,c->gpu+0x48,l2_hash8);
    r->gpu_regs_before.seed400=rd(io,c->gpu+0x48);
    if(r->gpu_regs_before.seed400!=l2_hash8) {
        r->error=SWEET_CSF_BOOT_STATE;goto cleanup;
    }
#endif
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
#if SWEET_CSF_VENDOR_MEMATTR
    /*2380: the PTE side now selects index0/index5, so the register must carry
     * the vendor table itself. vendor_cached_memattr is ignored here: index0
     * is already0x88 and index5 already0x4c, which makes the diagnostic switch
     * a no-op instead of a second variable. */
    const uint32_t memattr_lo=SWEET_CSF_VENDOR_MEMATTR_LO;
    const uint32_t memattr_hi=SWEET_CSF_VENDOR_MEMATTR_HI;
#else
    uint32_t memattr_lo=c->vendor_cached_memattr?0x4c4c884c:0x4c4c9f4c;
    uint32_t memattr_hi=0x4c4c4c4c;
#endif
    wr(io,c->gpu+0x2408,memattr_lo);wr(io,c->gpu+0x240c,memattr_hi);
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
       ((SWEET_CSF_VENDOR_MEMATTR||c->vendor_cached_memattr)&&
        (r->memattr_lo!=memattr_lo||r->memattr_hi!=memattr_hi))) {
        r->error=SWEET_CSF_BOOT_STATE;goto cleanup;
    }
    wr(io,c->gpu+0x2004,0x10001);wr(io,c->gpu+0x1004,0x80000000);
    if(rd(io,c->gpu+0x1000)&0x80000000) {r->error=SWEET_CSF_BOOT_STATE;goto cleanup;}
    uint64_t shared=c->arena_pa+c->shared_offset;
    io->barrier(io->context);
    r->version_before=rd(io,shared);r->sample_flags|=1;
#if SWEET_CSF_SHARED_SENTINEL
    /* 2405: the shared page arrives uninitialised, so the firmware's output_va
     * slot cannot be scored unless something known was written to it first.
     * Seed it here - after the page table is live and before the MCU is
     * started - and fail closed if the seed does not read back: a slot that
     * accepts no host write cannot report an MCU write either. */
    wr(io,shared+12,SWEET_CSF_SHARED_SENTINEL_WORD);
    if(rd(io,shared+12)!=SWEET_CSF_SHARED_SENTINEL_WORD) {
        r->error=SWEET_CSF_BOOT_STATE;goto cleanup;
    }
#endif
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
#if SWEET_CSF_STORE_WITNESS
    /* The diagnostic MCU code owns these two otherwise unused shared words.
     * Sample before reset: cleanup cannot erase or manufacture the witness. */
    wr(io,shared+0x200,0x24205200);
    wr(io,shared+0x400,0x24205400);
#endif
    platform_state(c,io,r,0);
    access_state(c,io,r,0);
    if(platform_path(c,io,r,0)) {
        r->error=SWEET_CSF_BOOT_STATE;goto cleanup;
    }
#if SWEET_CSF_MFG_GLUE == 1
    /*2413: the SoC side of the GPU, before the MCU is started. The vendor
     *kernel runs __gpufreq_acp_control() on every power-on (gpufreq_mt6983.c):
     *  MFG_AXCOHERENCE            0x168 |= 0xF   M0..M3 coherence enable
     *  MFG_1TO2AXI_CON_00/02/04/06 0x8e0/0x8e8/0x910/0x918 |= 0x855
     *  MFG_OUT_1TO2AXI_CON_00/02/04/06 0x900/0x908/0x920/0x928 |= 0x055
     *and __gpufreq_slc_control() sets group6's base/limit/policy to
     *0xffffffff/0xffffffff/0x06002006 (W-alloc, R cache, no spec).
     *A "1 to 2 AXI" bridge splits a stream by an address bit and by nothing
     *else, and the wall is exactly that shape: the upper 512 bytes of every
     *1 KiB never answered, on any page, through any leaf. The same page read
     *back 0x06000006 for group6 since 2407 - bit13, the vendor's "R cache",
     *was never set - so this block has provably never been programmed here.
     *panthor owns 0x13000000 only; the DDK assumes the platform did this.
     *Order and masks are the vendor's. Only group6 of the SLC table is
     *written, because group6 is the tag this shim's leaves carry.
     *platform_path() sampled this page as "before" and samples it again as
     *"after", so the report's slc_group6 field carries the before/after pair
     *without touching the 784-byte ABI. */
    {
        static const uint16_t in_dispatch[4]={0x8e0,0x8e8,0x910,0x918};
        static const uint16_t out_dispatch[4]={0x900,0x908,0x920,0x928};
        uint32_t v=rd(io,SWEET_CSF_MFG_BASE+0x168);
        wr(io,SWEET_CSF_MFG_BASE+0x168,v|0xfu);
        for(unsigned i=0;i<4;i++) {
            v=rd(io,SWEET_CSF_MFG_BASE+in_dispatch[i]);
            wr(io,SWEET_CSF_MFG_BASE+in_dispatch[i],v|0x855u);
        }
        for(unsigned i=0;i<4;i++) {
            v=rd(io,SWEET_CSF_MFG_BASE+out_dispatch[i]);
            wr(io,SWEET_CSF_MFG_BASE+out_dispatch[i],v|0x055u);
        }
        wr(io,SWEET_CSF_MFG_BASE+0x740,0xffffffffu);
        wr(io,SWEET_CSF_MFG_BASE+0x744,0xffffffffu);
        wr(io,SWEET_CSF_MFG_BASE+0x748,0x06002006u);
        r->diag_flags|=2048;
    }
#endif
#if SWEET_CSF_MFG_GLUE == 2
    /*2414: perturb the same block instead of applying it. 2413 wrote the vendor
     *values and the wall did not move, but it could not show the dispatch words
     *had been different before the write - group 6 already read 0x06002006 on
     *the way in. So this build sets the four in-dispatch words to 0xAAA, a value
     *the hardware cannot already hold, leaves the out-dispatch at the vendor
     *0x055, and records whether each group was already at the vendor value so a
     *no-op is visible instead of silent. Bits 12/13/14 mean "in-dispatch,
     *out-dispatch, group 6 were already 0x855/0x055/0x06002006 before the write";
     *bit 11 still means the block ran.
     *Reading: a dead ladder (no marker 1) means those words govern the MCU's
     *data path and 0x855 is load-bearing; marker 3 with the same result word
     *means the AXI bridge is not the wall under any setting tried. */
    {
        static const uint16_t in_dispatch[4]={0x8e0,0x8e8,0x910,0x918};
        static const uint16_t out_dispatch[4]={0x900,0x908,0x920,0x928};
        uint32_t v,in_already=1,out_already=1,slc_already=1;
        v=rd(io,SWEET_CSF_MFG_BASE+0x168);
        wr(io,SWEET_CSF_MFG_BASE+0x168,v|0xfu);
        for(unsigned i=0;i<4;i++) {
            v=rd(io,SWEET_CSF_MFG_BASE+in_dispatch[i]);
            if((v&0xfffu)!=0x855u)in_already=0;
            wr(io,SWEET_CSF_MFG_BASE+in_dispatch[i],(v&~0xfffu)|0xaaau);
        }
        for(unsigned i=0;i<4;i++) {
            v=rd(io,SWEET_CSF_MFG_BASE+out_dispatch[i]);
            if((v&0xfffu)!=0x055u)out_already=0;
            wr(io,SWEET_CSF_MFG_BASE+out_dispatch[i],v|0x055u);
        }
        v=rd(io,SWEET_CSF_MFG_BASE+0x748);
        if(v!=0x06002006u)slc_already=0;
        wr(io,SWEET_CSF_MFG_BASE+0x740,0xffffffffu);
        wr(io,SWEET_CSF_MFG_BASE+0x744,0xffffffffu);
        wr(io,SWEET_CSF_MFG_BASE+0x748,0x06002006u);
        r->diag_flags|=2048;
        if(in_already)r->diag_flags|=4096;
        if(out_already)r->diag_flags|=8192;
        if(slc_already)r->diag_flags|=16384;
    }
#endif
#if SWEET_CSF_MFG_GLUE == 3 && SWEET_CSF_GPU_REGS && SWEET_CSF_DISPATCH_SURVEY
    /*2418: the 1-to-2 AXI bridge, treated instead of applied. 2413/2414 wrote
     *the vendor values and then an arbitrary one (0xAAA) and the wall did not
     *move; neither experiment asked the bridge to route everything to the port
     *that already answers. Bit9 =0 reads return, so that port works; the field
     *that spreads by address is the candidate, and "all to one port" is the
     *value that would remove a per-address split if the field means what its
     *name says. The eight words are recorded first, full32 bits - the vendor
     *only ever ORs the low12 and never reads them back - so this run also
     *shows whether the upper20 carry anything, and whether the words were at
     *the vendor values before the write (diag bit12). */
    {
        static const uint16_t in_word[4]={0x8e0,0x8e8,0x910,0x918};
        static const uint16_t out_word[4]={0x900,0x908,0x920,0x928};
        struct sweet_csf_gpu_regs *g=&r->gpu_regs_before;
        uint32_t *dst[8]={&g->in_0,&g->in_2,&g->in_4,&g->in_6,
                          &g->out_0,&g->out_2,&g->out_4,&g->out_6};
        uint32_t v[8];unsigned in_ok=1;
        for(unsigned i=0;i<4;i++)v[i]=rd(io,SWEET_CSF_MFG_BASE+in_word[i]);
        for(unsigned i=0;i<4;i++)v[4+i]=rd(io,SWEET_CSF_MFG_BASE+out_word[i]);
        for(unsigned i=0;i<8;i++)*dst[i]=v[i];
        for(unsigned i=0;i<4;i++)if((v[i]&0xfffu)!=0x855u)in_ok=0;
        for(unsigned i=0;i<4;i++)wr(io,SWEET_CSF_MFG_BASE+in_word[i],0);
        r->gpu_regs_flags|=1;
        r->diag_flags|=2048;
        if(in_ok)r->diag_flags|=4096;
    }
#endif
#if SWEET_CSF_MFG_GLUE == 4 && SWEET_CSF_GPU_REGS && SWEET_CSF_DISPATCH_READBACK
    /*2419: three builds have written this page and none has read a word back, so
     *"the bridge ignores the field" and "the write never landed" are still one
     *observation. This block writes0x800 - the vendor's0x855 with only the
     *512-byte port pattern zeroed (2418 showed0x055 = 0101_0101, one bit per
     *512-byte slot, exactly the alternation 2415 measured) and bit11 preserved,
     *which0x000 in 2418 cleared as well - and then reads the same four words
     *back into their own slots. diag bit11 says the block ran, bit12 that the
     *words already held the vendor value, bit13 that all four read back0x800,
     *bit14 that all four still read their pre-value, i.e. the write was inert. */
    {
        static const uint16_t in_word[4]={0x8e0,0x8e8,0x910,0x918};
        static const uint16_t out_word[2]={0x900,0x928};
        struct sweet_csf_gpu_regs *g=&r->gpu_regs_before;
        uint32_t *pre[4]={&g->in_0,&g->in_2,&g->in_4,&g->in_6};
        uint32_t *post[4]={&g->post_0,&g->post_2,&g->post_4,&g->post_6};
        uint32_t v[4];unsigned in_ok=1,landed=1,inert=1;
        for(unsigned i=0;i<4;i++)v[i]=rd(io,SWEET_CSF_MFG_BASE+in_word[i]);
        for(unsigned i=0;i<4;i++)*pre[i]=v[i];
        g->out_0=rd(io,SWEET_CSF_MFG_BASE+out_word[0]);
        g->out_2=rd(io,SWEET_CSF_MFG_BASE+out_word[1]);
        for(unsigned i=0;i<4;i++)if((v[i]&0xfffu)!=0x855u)in_ok=0;
        for(unsigned i=0;i<4;i++)wr(io,SWEET_CSF_MFG_BASE+in_word[i],0x800);
        for(unsigned i=0;i<4;i++) {
            uint32_t p=rd(io,SWEET_CSF_MFG_BASE+in_word[i]);
            *post[i]=p;
            if(p!=0x800u)landed=0;
            if(p!=v[i])inert=0;
        }
        r->gpu_regs_flags|=1;
        r->diag_flags|=2048;
        if(in_ok)r->diag_flags|=4096;
        if(landed)r->diag_flags|=8192;
        if(inert)r->diag_flags|=16384;
    }
#endif
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
    /* r32p1 and Panthor start the MCU with AUTO alone(2). Build2372 tested
     * ENABLE|AUTO(3) on this SoC and MCU_STATUS stayed0 for
     * the whole budget, so2 is the default here and3 stays reachable through
     * the config word for a single-variable trial. The written and
     * immediately read-back bytes go to platform_reserved so the696-byte
     * report ABI stays unchanged. path_reserved keeps its2335 checkpoint
     * meaning; do not reuse it here. */
    uint32_t control=c->mcu_control_value?c->mcu_control_value:2;
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
#if SWEET_CSF_GLOBAL_INIT
    /*2381: the port's next layer. Only reachable once the interface gate above
     * accepted version/input/output/groups, i.e. the firmware really booted.
     * readiness is claimed only after this stage succeeds too, so a firmware
     * that boots but refuses the global handshake is never reported ready. */
    if(c->global_init) {
        r->stage=SWEET_CSF_BOOT_GLOBAL;
        rc=csf_global_init(c,io,r,budget);
#if SWEET_CSF_GLOBAL_RELAY
        /* Persist20 handshake words through the existing two40-byte slots.
         * Physical addresses are already derivable from AS root/shared plan.
         * Zero flags mean global-init was never reached; do not invent ACK. */
        const struct sweet_csf_global_evidence *e=c->global_evidence;
        r->gpu_regs_before=(struct sweet_csf_gpu_regs){
            e->flags,(uint32_t)e->error,e->input_va,e->output_va,
            e->req_before,e->ack_before,e->protm_coherency,
            e->alloc_en_lo,e->alloc_en_hi,e->pwroff_timer};
        r->gpu_regs_after=(struct sweet_csf_gpu_regs){
            e->progress_timer,e->idle_timer,e->ack_irq_mask,e->req_written,
            e->ack_first,e->ack_last,e->polls,e->req_mask,
            e->ack_matched,e->doorbell_value};
        r->gpu_regs_flags=3;
#endif
        if(rc) {r->error=rc;goto cleanup;}
    }
#endif
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
