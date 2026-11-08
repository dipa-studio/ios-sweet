"""Strict C MMIO model for bounded CSF MCU boot, faults and cleanup."""
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[2]
HARNESS=r'''
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include "mali_csf_boot.h"
/*2408: with the pre-start reset built in, one reset has already happened by
 *the time the ladder is running; everything else keeps its old expectation. */
#if SWEET_CSF_PRESTART_RESET
#define PRESTART_RESETS 1
#else
#define PRESTART_RESETS 0
#endif
/*2380: the AS_MEMATTR pair the driver must write in each mode. */
#if SWEET_CSF_VENDOR_MEMATTR
#define MEMATTR_LO 0x888d8f88u
#define MEMATTR_CACHED_LO 0x888d8f88u
#define MEMATTR_HI 0x00084c8du
#else
#define MEMATTR_LO 0x4c4c9f4c
#define MEMATTR_CACHED_LO 0x4c4c884c
#define MEMATTR_HI 0x4c4c4c4c
#endif
struct model {
 uint64_t tick;unsigned reads,writes,enabled,resets,as_updates,locked,flushed,lock_low,lock_high;
 uint32_t path[16],path_after_bits;unsigned path_on,path_reads,marker_reads;
 uint32_t gpu_mask,job_mask,mmu_mask,l2,raw,job,mcu,mmu,transcfg,table_low,table_high;
 uint32_t memattr_lo,memattr_hi,coherency,coherency_writes,control,platform_reads;
 int bad_coherency_readback,vendor_ina0,vendor_cached_memattr,bad_memattr;
 int unpowered,bad_id,bad_bits,as_busy,no_l2,no_fw,fw_fault,reset_fail,bad_iface,stale,stuck_timer,live_table,request_done,disable_fail,bad_readback,bad_irq_mask,clamp_masks,missing_gpu_irq,missing_mmu_irq;
 unsigned prestart_fail;
 unsigned halted,started,halt_writes,expected_control,halt_fail;
 /*2381 global interface: input page at0x90011000, output page at0x90012000. */
 uint32_t in_page[64],in_req,out_req,in_va,out_va;unsigned doorbell_writes,ack_mode,global_writes;
 /*2413: every write into the MFG top page, in order. */
 unsigned glue_writes;uint64_t glue_addr[16];uint32_t glue_value[16];
};
static uint32_t rd(void *p,uint64_t a) {
 struct model*m=p;m->reads++;
 if(m->path_on) {
  const uint64_t addresses[]={0x13f9103c,0x13f91048,0x10001ca0,0x10001cac,
   0x10001c60,0x10001c6c,0x10001c70,0x10001c7c,0x13fbf100,0x13fbf120,
   0x13fbf140,0x13fbf118,0x13fbf0c0,0x13fbf098,0x13fbf1c0,0x13fbf748};
  for(unsigned i=0;i<16;i++)if(a==addresses[i]) {
   assert(m->resets==PRESTART_RESETS && m->as_updates==2 && m->l2);m->path_reads++;
   return m->path[i]|(i==0 && m->enabled?m->path_after_bits:0);
  }
 }
 if(a==0x1c001eb8||a==0x1c001ebc||a==0x1c001ec0||a==0x1c001ec4||
    a==0x13fa000c||a==0x13fa0c0c||a==0x100001f0||a==0x13f91048) {
  assert(!m->unpowered && m->resets==PRESTART_RESETS && m->as_updates==2 && m->l2);
  m->platform_reads++;return (uint32_t)a+(m->enabled?1:0);
 }
 if(a==0x1c001f3c||a==0x1c001f40)return m->unpowered?2:6;
 if(a==0x90010ffc){assert(m->resets==PRESTART_RESETS && m->as_updates==2 && m->control==(m->enabled?(m->expected_control?m->expected_control:2):0));m->marker_reads++;return m->enabled?0x53545542:0;}
 if(a==0x90006000){assert(m->resets==PRESTART_RESETS && m->as_updates==2);return 0x12345678;}
 if(a>=0x90010000 && a<0x90010020) {
  assert(m->as_updates==2);
  switch(a-0x90010000) {case 0:return 0x01020003;case 4:return 0x123;case 8:return m->bad_iface==1?0:(m->in_va?m->in_va:0x4001000);
  case 12:return m->out_va?m->out_va:0x4002000;case 16:return 8;case 20:return m->bad_iface==2?0x4000:64;case 24:return m->enabled&&!m->no_fw?3:0;default:assert(0);}
 }
 if(a==0x90005934||a==0x9000593c||a==0x9000522c) {
  if(!m->enabled||m->no_fw)return 0;
  return a==0x90005934?10:a==0x9000593c?0x200000:0x50c0;
 }
 if(a==0x90011000)return m->in_req;
 if(a==0x90012000)return m->out_req;
 if(a>=0x90011000 && a<0x90011100)return m->in_page[(a-0x90011000)/4];
 if(a>=0x90012000 && a<0x90012100)return 0;
#if SWEET_CSF_MFG_GLUE
 /*2413: the MFG top page reads back as zero in this model, so the test can
  *assert the exact word the glue ORs in. */
 if(a>=0x13fbf000 && a<0x13fc0000)return 0;
#endif
 assert(a>=0x13000000 && a<0x13002500);assert(!m->unpowered);
 switch(a-0x13000000) {
 case 0:return m->bad_id?0xa0020001:0xa8620004;
 case 0x14:return m->bad_bits?0x1010:0x2830;
 case 0x18:return 0xff;
 case 0x20:return m->raw;
 case 0x28:return m->gpu_mask;
 case 0x34:return 0x100;
 case 0x3c:return m->enabled?0x80:0;case 0x40:return 0x12345000;case 0x44:return 2;
 case 0x300:return 1;case 0x304:return m->coherency;
 case 0xf00:return 0x44;case 0xf04:return 0x55;case 0xf08:return 0x66;case 0xf0c:return 0x77;
 case 0x100:return 0xff;case 0x104:return 0;
 case 0x110:return 1;case 0x114:return 0;
 case 0x200:return m->enabled?2:0;case 0x204:return 0;
 case 0x210:return m->enabled?1:0;case 0x214:return 0;
 case 0x140:return m->enabled?0xff:0;case 0x144:return 0;
 case 0x150:return m->enabled?1:0;case 0x154:return 0;
 case 0x120:return 1;case 0x124:return 0;case 0x160:return m->l2;
 case 0x164:case 0x220:case 0x224:return 0;
 case 0x704:return m->mcu;
 case 0x700:return m->control;
 case 0x1000:return m->stale?0x80000000:m->job;
 case 0x100c:return m->job&m->job_mask;
 case 0x1008:return m->bad_irq_mask && m->job_mask==UINT32_MAX?0:m->job_mask;
 case 0x2000:return m->mmu;case 0x2008:return m->mmu_mask;
 case 0x2428:return m->as_busy?1:0;
 case 0x2400:return m->live_table?0x80000000:m->table_low;case 0x2404:return m->table_high;
 case 0x2408:return m->bad_memattr==1?0x4c4c9f4c:m->memattr_lo;case 0x240c:return m->bad_memattr==2?0:m->memattr_hi;
 case 0x2430:return m->bad_readback && m->as_updates==2?(m->vendor_ina0?0x420001c6:6):m->transcfg;case 0x2434:return 0;
 case 0x241c:return m->mmu?0xc0:0;case 0x2420:case 0x2424:return 0;
 default:assert(0);return 0;
 }
}
static void wr(void*p,uint64_t a,uint32_t v) {
 struct model*m=p;m->writes++;assert(!m->unpowered);
 if(a==0x13080000) {
  /*2381: kernel doorbell. The firmware acks the CFG bits by mirroring REQ. */
  assert(m->enabled && m->as_updates==2 && m->resets==PRESTART_RESETS);
  m->doorbell_writes++;m->global_writes++;
  if(!m->ack_mode)m->out_req=m->in_req;
  return;
 }
 if(a==0x90011000){m->in_req=v;m->global_writes++;return;}
 if(a>=0x90011000 && a<0x90011100){m->in_page[(a-0x90011000)/4]=v;m->global_writes++;return;}
#if SWEET_CSF_MFG_GLUE
 /*2413: the MFG top glue, recorded in order. */
 if(a>=0x13fbf000 && a<0x13fc0000) {
  if(m->glue_writes<16){m->glue_addr[m->glue_writes]=a;m->glue_value[m->glue_writes]=v;}
  m->glue_writes++;return;
 }
#endif
 switch(a-0x13000000) {
 case 0x304:
  assert(v==31 && !m->l2 && !m->as_updates && !m->enabled);
  assert(!m->gpu_mask && !m->job_mask && !m->mmu_mask);
  m->coherency_writes++;if(!m->bad_coherency_readback)m->coherency=v;return;
 case 0x28:
  m->gpu_mask=v;
  if(v==0x80503){if(m->clamp_masks)m->gpu_mask=0x103;if(m->missing_gpu_irq)m->gpu_mask&=~1u;}
  return;
 case 0x1008:m->job_mask=v;return;
 case 0x2008:
  m->mmu_mask=v;
  if(v==0xffff){if(m->clamp_masks)m->mmu_mask=0xff;if(m->missing_mmu_irq)m->mmu_mask&=~1u;}
  return;
 case 0x1a0:assert(v==1);if(!m->no_l2)m->l2=1;return;
 case 0x2410:assert(v==47);m->lock_low=1;return;
 case 0x2414:assert(v==0);m->lock_high=1;return;
 case 0x2418:
  if(v==2){assert(m->lock_low && m->lock_high && m->as_updates==1);m->locked=1;return;}
  if(v==5){assert(m->locked);m->flushed=1;return;}
  assert(v==1);m->as_updates++;return;
 case 0x2400:assert(v==0x90000000);m->table_low=v;return;case 0x2404:assert(v==0);m->table_high=v;return;
 case 0x2408:assert(v==(m->vendor_cached_memattr?MEMATTR_CACHED_LO:MEMATTR_LO));m->memattr_lo=v;return;case 0x240c:assert(v==MEMATTR_HI);m->memattr_hi=v;return;
 case 0x2430:assert(v==1||v==(m->vendor_ina0?0x42000006:0x420001c6));if(v!=1)assert(m->flushed);m->transcfg=v;return;
 case 0x2434:assert(v==0);return;
 case 0x2004:m->mmu&=~v;return;
 case 0x1004:m->job&=~v;return;
 case 0x700:
  m->control=v;
  /* A zero write before the start is the explicit halt; after it, the same
   * write is the cleanup disable. halt_fail keeps the MCU awake across the
   * halt so the halt poll has something to time out on. */
  if(v==0){
   if(!m->started && !m->halt_writes){m->halt_writes=1;m->halted=1;
    m->mcu=m->halt_fail?1:0;return;}
   if(!m->disable_fail)m->mcu=0;return;
  }
  assert(m->halted && !m->started);
  assert(v==(m->expected_control?m->expected_control:2));
  assert(m->l2 && m->as_updates==2 && m->transcfg==(m->vendor_ina0?0x42000006:0x420001c6));
  assert((m->gpu_mask&0x103)==0x103 && m->job_mask==UINT32_MAX && (m->mmu_mask&0xff)==0xff);
  m->started=1;m->enabled++;m->mcu=1;
  if(m->request_done)m->mmu=0x10000;
  if(m->fw_fault)m->mmu=1;
  else if(!m->no_fw)m->job|=0x80000000;
  return;
 case 0x24:m->raw&=~v;return;
 case 0x30:
  assert(v==0x101);
  /*2408: prestart_fail drops only the transaction's first reset, so the
   *cleanup reset can still complete and one boot reports both facts. */
  if(!(m->reset_fail||(m->prestart_fail&&!m->resets)))m->raw|=0x100;
  m->resets++;return;
 default:assert(0);
 }
}
static uint64_t ticks(void*p){struct model*m=p;return m->stuck_timer?0:m->tick++;}
static void barrier(void*p){(void)p;}
static struct model model(void){return (struct model){.gpu_mask=0x55,.job_mask=0xaa,.mmu_mask=0xbb,.transcfg=1,.coherency=31};}
static struct sweet_csf_boot_config cfg(void){return (struct sweet_csf_boot_config){.gpu=0x13000000,.root_pa=0x90000000,.arena_pa=0x90000000,.arena_bytes=0x200000,.shared_offset=0x10000,.shared_bytes=0x20000,.timeout_ms=1,.private_probe_offset=0x5000};}
static int run(struct model*m,struct sweet_csf_boot_config*c,struct sweet_csf_boot_report*r){struct sweet_gpu_io io={m,rd,wr,ticks,barrier,1000};return sweet_csf_boot(c,&io,r);}
static void clean(struct model*m,struct sweet_csf_boot_report*r){assert(m->gpu_mask==0x55 && m->job_mask==0xaa && m->mmu_mask==0xbb && m->resets==1+PRESTART_RESETS);assert(r->reset_completed);}
#if SWEET_CSF_MFG_GLUE
/*2413: the MFG top glue, in the vendor's order and with the vendor's masks.
 *gpufreq_mt6983.c __gpufreq_acp_control() and the group6 word of
 *__gpufreq_slc_control(); nothing else in the transaction changes. */
int main(void) {
 static const uint64_t expect_addr[12]={0x13fbf168,0x13fbf8e0,0x13fbf8e8,0x13fbf910,
  0x13fbf918,0x13fbf900,0x13fbf908,0x13fbf920,0x13fbf928,0x13fbf740,0x13fbf744,0x13fbf748};
 static const uint32_t expect_value[12]={0xf,0x855,0x855,0x855,0x855,0x55,0x55,0x55,0x55,
  0xffffffffu,0xffffffffu,0x06002006u};
 struct model m=model();struct sweet_csf_boot_config c=cfg();struct sweet_csf_boot_report r;
 assert(!run(&m,&c,&r));
 assert(m.glue_writes==12);
 for(int i=0;i<12;i++){assert(m.glue_addr[i]==expect_addr[i]);assert(m.glue_value[i]==expect_value[i]);}
 assert(r.diag_flags==(31|2048));
 assert(r.stage==7 && r.firmware_ready);
 clean(&m,&r);
 puts("PASS: 2413 MFG glue writes the vendor power-on words");return 0;
}
#elif SWEET_CSF_PRESTART_RESET
/*2408: the reset panthor performs on its reset/resume path, issued before the
 *coherency write, the L2 power-on and any AS command. Four bits say what
 *happened, and a timeout must not stop the rest of the transaction. */
int main(void) {
 struct model m=model();struct sweet_csf_boot_config c=cfg();struct sweet_csf_boot_report r;
 assert(!run(&m,&c,&r));
 assert(r.diag_flags&128 && r.diag_flags&256);
 assert(r.diag_flags&512 && r.diag_flags&1024);
 assert(r.reset_completed && m.resets==2);
 clean(&m,&r);
 /* The model keeps DBG_ENABLED set, so bit10 is the honest reading here. */
 m=model();m.prestart_fail=1;
 assert(!run(&m,&c,&r));
 assert(r.diag_flags&128 && !(r.diag_flags&256));
 assert(r.diag_flags&512 && r.diag_flags&1024);
 assert(r.reset_completed && m.resets==2);
 puts("PASS: 2408 pre-start soft reset, completed and timed-out");return 0;
}
#else
int main(void) {
 struct model m=model();struct sweet_csf_boot_config c=cfg();struct sweet_csf_boot_report r;
 assert(sizeof(r)==696);assert(!run(&m,&c,&r));assert(r.stage==7 && r.firmware_ready && r.version==0x01020003);clean(&m,&r);
 assert(!r.platform_sample_flags && !m.platform_reads);
 /*2381 single-variable proof: the default configuration never touches the
  * global input page and never rings a doorbell. */
 assert(!m.doorbell_writes && !m.global_writes && !m.in_req);
 assert(r.diag_flags==31 && r.coherency_features==1 && r.coherency_before==31 && r.coherency_after==31);
 assert(!m.coherency_writes && !r.coherency_requested && !r.coherency_readback);
 assert(r.csf_config_before==0x44 && r.csf_config_after==0x44);
 assert(r.shader_config_before==0x55 && r.shader_config_after==0x55);
 assert(r.tiler_config_before==0x66 && r.tiler_config_after==0x66);
 assert(r.l2_mmu_config_before==0x77 && r.l2_mmu_config_after==0x77);
 assert(r.memattr_lo==MEMATTR_LO && r.memattr_hi==MEMATTR_HI);
 assert(r.private_page_lo==0x90005000 && !r.private_page_hi);
 assert(!r.private_early_before && r.private_early_after==10);
 assert(!r.private_feature_before && r.private_feature_after==0x200000);
 assert(!r.private_late_before && r.private_late_after==0x50c0);
 assert(!r.shared_alloc_before && r.shared_alloc_after==3);
 assert(r.job_irq_mask==UINT32_MAX && r.gpu_irq_mask==0x80503 && r.mmu_irq_mask==0xffff);
 assert(r.as_present==0xff && r.irq_gate_passed==1);
 assert(r.shader_present_lo==0xff && r.shader_transition_lo==2 && r.shader_ready_lo==0xff);
 assert(r.tiler_present_lo==1 && r.tiler_transition_lo==1 && r.tiler_ready_lo==1);
 assert(r.sample_flags==15 && r.version_before==r.version && !r.disable_error && !r.disable_status);
 assert(r.transcfg_lo==0x420001c6 && r.transtab_lo==0x90000000 && !r.transtab_hi);
 /*2372: one measured halt before the start, and the start word recorded. */
 assert(r.platform_reserved==0x202 && m.halt_writes==1 && m.started==1);
 c=cfg();c.mcu_control_value=3;m=model();m.expected_control=3;
 assert(!run(&m,&c,&r));clean(&m,&r);
 assert(r.platform_reserved==0x303 && m.halt_writes==1);
 c=cfg();c.mcu_control_value=1;m=model();assert(run(&m,&c,&r)==-50 && !m.reads && !m.writes);
 c=cfg();m=model();m.halt_fail=1;
 assert(run(&m,&c,&r)==-52 && r.stage==8 && !m.started && m.halt_writes==1);
 assert(r.platform_reserved==0 && r.mcu_status==1);
 m=model();m.coherency=0;c=cfg();c.noncoherent=1;assert(!run(&m,&c,&r));clean(&m,&r);
 assert(m.coherency_writes==1 && r.diag_flags==127 && !r.coherency_before);
 assert(r.coherency_requested==31 && r.coherency_readback==31 && r.coherency_after==31);
 assert(r.csf_config_after==0x44 && r.shader_config_after==0x55 && r.tiler_config_after==0x66 && r.l2_mmu_config_after==0x77);
 assert(r.memattr_lo==MEMATTR_LO && r.memattr_hi==MEMATTR_HI && r.transcfg_lo==0x420001c6);
 m=model();m.coherency=0;m.no_fw=1;assert(run(&m,&c,&r)==-53 && !r.firmware_ready);clean(&m,&r);
 assert(m.coherency_writes==1 && r.diag_flags==127 && r.coherency_after==31);
 m=model();m.coherency=0;m.bad_coherency_readback=1;assert(run(&m,&c,&r)==-52);clean(&m,&r);
 assert(m.coherency_writes==1 && !m.enabled && !m.as_updates && !m.l2);
 assert(r.diag_flags==33 && r.coherency_requested==31 && !r.coherency_readback);
 m=model();c.noncoherent=2;assert(run(&m,&c,&r)==-50 && !m.reads && !m.writes);
 c=cfg();c.pte_group_requested=6;c.pte_pages_built=293;
 m=model();assert(!run(&m,&c,&r));clean(&m,&r);
 assert(r.pte_group_requested==6 && r.pte_pages_built==293);
 m=model();c=cfg();c.vendor_ina0=1;m.vendor_ina0=1;c.noncoherent=1;
 c.pte_group_requested=6;c.pte_pages_built=293;
 assert(!run(&m,&c,&r));clean(&m,&r);
 assert(r.transcfg_lo==0x42000006 && r.memattr_lo==MEMATTR_LO && r.memattr_hi==MEMATTR_HI);
 assert(r.pte_group_requested==6 && r.pte_pages_built==293 && r.diag_flags==127);
 m=model();m.vendor_ina0=1;m.no_fw=1;assert(run(&m,&c,&r)==-53 && !r.firmware_ready);clean(&m,&r);
 assert(r.transcfg_lo==0x42000006 && r.sample_flags==15);
 m=model();m.vendor_ina0=1;m.bad_readback=1;assert(run(&m,&c,&r)==-52 && !m.enabled);clean(&m,&r);
 assert(r.transcfg_lo==0x420001c6 && !r.sample_flags);
 m=model();c.vendor_ina0=2;assert(run(&m,&c,&r)==-50 && !m.reads && !m.writes);
 c=cfg();c.vendor_ina0=1;c.vendor_cached_memattr=1;c.noncoherent=1;
 m=model();m.vendor_ina0=1;m.vendor_cached_memattr=1;
 assert(!run(&m,&c,&r));clean(&m,&r);
 assert(r.memattr_lo==MEMATTR_CACHED_LO && r.memattr_hi==MEMATTR_HI && r.transcfg_lo==0x42000006);
 m=model();m.vendor_ina0=1;m.vendor_cached_memattr=1;m.no_fw=1;
 assert(run(&m,&c,&r)==-53 && !r.firmware_ready);clean(&m,&r);
 for(int bad=1;bad<=2;bad++) {
  m=model();m.vendor_ina0=1;m.vendor_cached_memattr=1;m.bad_memattr=bad;
  assert(run(&m,&c,&r)==-52 && !m.enabled && !r.sample_flags);clean(&m,&r);
 }
 m=model();c.vendor_cached_memattr=2;assert(run(&m,&c,&r)==-50 && !m.reads && !m.writes);
 c=cfg();c.platform_snapshot=1;m=model();assert(!run(&m,&c,&r));clean(&m,&r);
 assert(r.platform_sample_flags==3 && r.platform_reserved==0x202 && m.platform_reads==16);
 assert(r.platform_before.mcu_control==0 && r.platform_after.mcu_control==2);
 assert(!r.platform_before.job_stat && r.platform_after.job_stat==0x80000000);
 assert(r.platform_before.mfg_pll_con1==0x13fa000c && r.platform_after.mfg_pll_con1==0x13fa000d);
 assert(r.platform_before.mfg_power3==0x1c001ec4 && r.platform_after.mfg_power3==0x1c001ec5);
 assert(r.platform_after.gpu_status==0x100 && r.platform_after.spm_status==6);
 assert(r.platform_after.gpu_fault_status==0x80 && r.platform_after.gpu_fault_lo==0x12345000 && r.platform_after.gpu_fault_hi==2);
 m=model();m.no_fw=1;assert(run(&m,&c,&r)==-53);clean(&m,&r);
 assert(r.platform_sample_flags==3 && !r.platform_after.job_stat && m.platform_reads==16);
 m=model();m.missing_gpu_irq=1;assert(run(&m,&c,&r)==-52);clean(&m,&r);
 assert(!r.platform_sample_flags && !m.platform_reads);
 c.access_snapshot=1;c.firmware_probe_offset=0x6000;c.firmware_probe_va=0x01000000;
 c.firmware_probe_expected=0x12345678;m=model();assert(!run(&m,&c,&r));clean(&m,&r);
 assert(r.access_sample_flags==3 && !r.access_reserved);
 assert(r.firmware_probe_pa_lo==0x90006000 && !r.firmware_probe_pa_hi);
 assert(r.firmware_probe_va==0x01000000 && r.firmware_probe_expected==0x12345678);
 assert(r.access_before.firmware_word0==0x12345678 && r.access_after.firmware_word0==0x12345678);
 assert(r.access_before.l2_ready_lo==1 && !r.access_before.l2_ready_hi);
 assert(!r.access_before.mmu_raw && !r.access_before.job_raw);
 assert(r.access_after.job_raw==0x80000000 && !r.access_after.as_fault);
 m=model();m.no_fw=1;assert(run(&m,&c,&r)==-53);clean(&m,&r);
 assert(r.access_sample_flags==3 && !r.access_after.job_raw && !r.access_after.as_status);
 m=model();m.fw_fault=1;assert(run(&m,&c,&r)==-54);clean(&m,&r);
 assert(r.access_after.mmu_raw==1 && r.access_after.as_fault==0xc0);
 m=model();m.missing_gpu_irq=1;assert(run(&m,&c,&r)==-52);clean(&m,&r);
 assert(!r.access_sample_flags);
 for(unsigned i=0;i<7;i++) {
  struct sweet_csf_boot_config bad=c;
  if(i==0)bad.access_snapshot=2;else if(i==1)bad.platform_snapshot=0;
  else if(i==2)bad.firmware_probe_offset=1;else if(i==3)bad.firmware_probe_offset=0;
  else if(i==4)bad.firmware_probe_offset=0x200000;
  else if(i==5)bad.firmware_probe_offset=c.shared_offset;else bad.firmware_probe_va=0x04000000;
  m=model();assert(run(&m,&bad,&r)==-50 && !m.reads && !m.writes);
 }
 c.entry_checkpoint=1;m=model();m.no_fw=1;m.disable_fail=1;
 assert(run(&m,&c,&r)==-53);clean(&m,&r);
 assert(m.marker_reads==2 && r.access_reserved==0 && r.path_reserved==0x53545542);
 assert(r.access_sample_flags==3 && r.disable_error==-53);
 for(unsigned i=0;i<2;i++) {
  struct sweet_csf_boot_config bad=c;
  if(i==0)bad.entry_checkpoint=2;else bad.access_snapshot=0;
  m=model();assert(run(&m,&bad,&r)==-50 && !m.reads && !m.writes);
 }
 c.entry_checkpoint=0;
 c.platform_path=1;m=model();m.path_on=1;
 m.path[0]=m.path[1]=0xfff0fff0;assert(!run(&m,&c,&r));clean(&m,&r);
 assert(r.path_sample_flags==3 && !r.path_reserved && m.path_reads==34);
 assert(r.path_before.rpc_enable==0xfff0fff0 && r.path_after.rpc_status==0xfff0fff0);
 for(unsigned i=0;i<8;i++) {
  uint32_t mask=i<2?0xf0000:i<4?0xf:0xc0000;
  for(unsigned bit=0;bit<32;bit++)if(mask&(1u<<bit)) {
   m=model();m.path_on=1;m.path[i]=1u<<bit;
   assert(run(&m,&c,&r)==-52 && !m.enabled && r.path_sample_flags==1);
   assert(!r.firmware_ready && !r.path_after.rpc_enable);clean(&m,&r);
  }
 }
 m=model();m.path_on=1;m.path_after_bits=0x10000;
 assert(run(&m,&c,&r)==-52 && m.enabled==1 && r.path_sample_flags==3);clean(&m,&r);
 assert(r.path_after.rpc_enable==0x10000);
 m=model();m.path_on=1;m.no_fw=1;m.path_after_bits=0x10000;
 assert(run(&m,&c,&r)==-53 && r.path_sample_flags==3);clean(&m,&r);
 for(unsigned i=0;i<2;i++) {
  struct sweet_csf_boot_config bad=c;
  if(i==0)bad.platform_path=2;else bad.access_snapshot=0;
  m=model();assert(run(&m,&bad,&r)==-50 && !m.reads && !m.writes);
 }
 c=cfg();c.platform_snapshot=1;
 m=model();c.platform_snapshot=2;assert(run(&m,&c,&r)==-50 && !m.reads && !m.writes);
 c=cfg();
 m=model();c.pte_group_requested=16;assert(run(&m,&c,&r)==-50 && !m.reads && !m.writes);
 m=model();c=cfg();c.pte_pages_built=513;assert(run(&m,&c,&r)==-50 && !m.reads && !m.writes);
 /*2381: the global stage is opt-in and gated, both before any MMIO. */
 c=cfg();c.global_init=1;m=model();assert(run(&m,&c,&r)==-50 && !m.reads && !m.writes);
 c=cfg();c.global_init=2;m=model();assert(run(&m,&c,&r)==-50 && !m.reads && !m.writes);
#if SWEET_CSF_GLOBAL_INIT
 {
  /* Vendor-equivalent global interface: input page0x4001000, output0x4002000,
   * doorbell0, ACK mirrors REQ. */
  struct sweet_csf_global_evidence ev;struct sweet_csf_boot_config g=cfg();
  g.shared_va=0x4000000;g.global_init=1;g.global_evidence=&ev;
  memset(&ev,0,sizeof ev);m=model();
  assert(!run(&m,&g,&r));clean(&m,&r);
  assert(r.stage==7 && r.firmware_ready);
  assert(ev.flags==7 && !ev.error && ev.ack_matched==1);
  assert(ev.input_va==0x4001000 && ev.output_va==0x4002000);
  assert(ev.input_pa_lo==0x90011000 && ev.output_pa_lo==0x90012000);
  assert(!ev.input_pa_hi && !ev.output_pa_hi);
  assert(!ev.req_before && !ev.ack_before);
  assert(ev.protm_coherency==31 && ev.alloc_en_lo==0xff && !ev.alloc_en_hi);
  assert(ev.progress_timer==0x271000 && ev.pwroff_timer==0x271000 && ev.idle_timer==0x271000);
  assert(ev.ack_irq_mask==0x0480071e && ev.req_mask==0x40e);
  assert(ev.req_written==0x40e && ev.ack_first==0x40e && ev.ack_last==0x40e);
  assert(ev.polls==1 && ev.doorbell_value==1 && m.doorbell_writes==1);
  /* page layout: [1]=ack_irq_mask [4]=progress [5]=poweroff [6..7]=core_en
   * [8]=protm_coherency [0x20]=idle_timer. */
  assert(m.in_page[4]==0x271000 && m.in_page[5]==0x271000 && m.in_page[6]==0xff);
  assert(m.in_page[7]==0 && m.in_page[8]==31 && m.in_page[0x20]==0x271000);
  assert(m.in_req==0x40e && m.in_page[1]==ev.ack_irq_mask);
 }
 {
  /* A firmware that never acks is a timeout, not readiness. */
  struct sweet_csf_global_evidence ev;struct sweet_csf_boot_config g=cfg();
  g.shared_va=0x4000000;g.global_init=1;g.global_evidence=&ev;
  memset(&ev,0,sizeof ev);m=model();m.ack_mode=1;
  assert(run(&m,&g,&r)==-53);clean(&m,&r);
  assert(r.stage==10 && !r.firmware_ready);
  assert(ev.flags==3 && ev.error==-53 && !ev.ack_matched);
  assert(!ev.ack_first && !ev.ack_last && ev.polls>=1 && m.doorbell_writes==1);
 }
 for(unsigned i=0;i<3;i++) {
  struct sweet_csf_global_evidence ev;struct sweet_csf_boot_config g=cfg();
  g.shared_va=0x4000000;g.global_init=1;g.global_evidence=&ev;memset(&ev,0,sizeof ev);
  m=model();
  if(i==0)m.out_va=0x4000004;else if(i==1)m.out_va=0x4000000;else g.shared_va=0x4001000;
  if(i==2)assert(run(&m,&g,&r)==-50 && !m.reads && !m.writes);
  else {
   assert(run(&m,&g,&r)==-55 && !m.doorbell_writes && !m.global_writes);
   assert(ev.flags==8 && r.stage==9 && !r.firmware_ready);clean(&m,&r);
  }
 }
#endif
 c=cfg();
 m=model();m.clamp_masks=1;assert(!run(&m,&c,&r));clean(&m,&r);
 assert(r.gpu_irq_mask==0x103 && r.mmu_irq_mask==0xff && r.irq_gate_passed==1);
 m=model();m.missing_gpu_irq=1;assert(run(&m,&c,&r)==-52 && !m.enabled && r.sample_flags==5);clean(&m,&r);
 assert(r.gpu_irq_mask==0x80502 && !r.irq_gate_passed && !r.shader_transition_lo);
 m=model();m.missing_mmu_irq=1;assert(run(&m,&c,&r)==-52 && !m.enabled && r.sample_flags==5);clean(&m,&r);
 assert(r.mmu_irq_mask==0xfffe && !r.irq_gate_passed);
 m=model();m.request_done=1;assert(!run(&m,&c,&r));assert(r.mmu_raw==0x10000);clean(&m,&r);
 m=model();c=cfg();c.shared_bytes=0xffffff;assert(run(&m,&c,&r)==-50 && !m.reads && !m.writes);
 m=model();c=cfg();c.private_probe_offset=1;assert(run(&m,&c,&r)==-50 && !m.reads && !m.writes);
 m=model();c=cfg();c.private_probe_offset=0x200000;assert(run(&m,&c,&r)==-50 && !m.reads && !m.writes);
 m=model();c=cfg();c.private_probe_offset=0x10000;assert(run(&m,&c,&r)==-50 && !m.reads && !m.writes);
 m=model();c=cfg();c.private_probe_offset=0;assert(!run(&m,&c,&r));clean(&m,&r);
 assert(r.diag_flags==31 && !r.private_page_lo && !r.private_early_after && r.shared_alloc_after==3);
 m=model();c=cfg();m.unpowered=1;assert(run(&m,&c,&r)==-52 && !m.writes);
 m=model();m.bad_id=1;assert(run(&m,&c,&r)==-51 && !m.writes);
 m=model();m.bad_bits=1;assert(run(&m,&c,&r)==-51 && !m.writes);
 m=model();m.transcfg=0;assert(!run(&m,&c,&r));clean(&m,&r);
 m=model();m.transcfg=6;assert(run(&m,&c,&r)==-52 && !m.writes);
 m=model();m.live_table=1;assert(run(&m,&c,&r)==-52 && !m.writes);
 m=model();m.no_l2=1;assert(run(&m,&c,&r)==-53 && !m.enabled);clean(&m,&r);
 m=model();m.as_busy=1;assert(run(&m,&c,&r)==-53 && !m.enabled);clean(&m,&r);
 m=model();m.stale=1;assert(run(&m,&c,&r)==-52 && !m.enabled);clean(&m,&r);
 m=model();c=cfg();m.no_fw=1;assert(run(&m,&c,&r)==-53 && !r.firmware_ready);clean(&m,&r);
 assert(r.diag_flags==31 && !r.private_early_after && !r.private_late_after && !r.shared_alloc_after);
 assert(r.stage==4 && r.sample_flags==15 && r.version==0x01020003 && !r.job_raw);
 m=model();m.bad_irq_mask=1;assert(run(&m,&c,&r)==-52 && !m.enabled && r.sample_flags==5);clean(&m,&r);
 assert(r.diag_flags==7 && !r.private_early_after && !r.coherency_after);
 m=model();m.bad_readback=1;assert(run(&m,&c,&r)==-52 && !m.enabled && !r.sample_flags);clean(&m,&r);
 m=model();m.fw_fault=1;assert(run(&m,&c,&r)==-54 && r.as_fault==0xc0);clean(&m,&r);
 m=model();m.bad_iface=1;assert(run(&m,&c,&r)==-55 && !r.firmware_ready);clean(&m,&r);
 m=model();m.bad_iface=2;assert(run(&m,&c,&r)==-55 && !r.firmware_ready);clean(&m,&r);
 m=model();m.reset_fail=1;assert(run(&m,&c,&r)==-53 && r.cleanup_error==-53 && !r.reset_completed);
 m=model();m.disable_fail=1;assert(run(&m,&c,&r)==-53 && r.cleanup_error==-53 && r.reset_completed);
 assert(r.disable_error==-53 && r.disable_status==1 && r.firmware_ready);
 m=model();m.stuck_timer=1;m.no_fw=1;assert(run(&m,&c,&r)==-53 && !r.firmware_ready);clean(&m,&r);
 puts("PASS: MMU/L2/MCU ordering, stale IRQ, fault, timeout, interface, reset cleanup");return 0;
}
#endif
'''
@unittest.skipUnless(shutil.which('cc'),'requires C compiler')
class CsfBootTests(unittest.TestCase):
    def _run(self,defines=()):
        with tempfile.TemporaryDirectory() as directory:
            p=Path(directory);(p/'h.c').write_text(HARNESS)
            cmd=['cc','-std=c11','-Wall','-Wextra','-Werror','-fsanitize=address,undefined']
            cmd+=list(defines)
            cmd+=['-I',str(ROOT/'xnu/gpu'),str(p/'h.c'),str(ROOT/'xnu/gpu/mali_csf_boot.c'),'-o',str(p/'test')]
            subprocess.run(cmd,check=True,capture_output=True)
            result=subprocess.run([str(p/'test')],capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)

    def test_real_state_machine_with_sanitizers(self):
        self._run()

    def test_vendor_memattr_encoding(self):
        """2380: the driver writes the proven vendor pair, ignore the old switch."""
        self._run(['-DSWEET_CSF_VENDOR_MEMATTR=1'])

    def test_global_interface_stage(self):
        """2381: input page, doorbell and GLB_ACK, with fail-closed paths."""
        self._run(['-DSWEET_CSF_GLOBAL_INIT=1'])

    def test_vendor_memattr_with_global_interface(self):
        self._run(['-DSWEET_CSF_VENDOR_MEMATTR=1','-DSWEET_CSF_GLOBAL_INIT=1'])

    def test_mfg_glue(self):
        """2413: the vendor's power-on glue, in order, before MCU_CONTROL."""
        self._run(['-DSWEET_CSF_MFG_GLUE=1'])

    def test_prestart_soft_reset(self):
        """2408: reset before AS/MCU, and keep going when it times out."""
        self._run(['-DSWEET_CSF_PRESTART_RESET=1'])
if __name__=='__main__':unittest.main()
