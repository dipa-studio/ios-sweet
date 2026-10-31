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
struct model {
 uint64_t tick;unsigned reads,writes,enabled,resets,as_updates,locked,flushed,lock_low,lock_high;
 uint32_t gpu_mask,job_mask,mmu_mask,l2,raw,job,mcu,mmu,transcfg,table_low,table_high;
 uint32_t memattr_lo,memattr_hi,coherency,coherency_writes;
 int bad_coherency_readback;
 int unpowered,bad_id,bad_bits,as_busy,no_l2,no_fw,fw_fault,reset_fail,bad_iface,stale,stuck_timer,live_table,request_done,disable_fail,bad_readback,bad_irq_mask,clamp_masks,missing_gpu_irq,missing_mmu_irq;
};
static uint32_t rd(void *p,uint64_t a) {
 struct model*m=p;m->reads++;
 if(a==0x1c001f3c||a==0x1c001f40)return m->unpowered?2:6;
 if(a>=0x90010000 && a<0x90010020) {
  assert(m->as_updates==2);
  switch(a-0x90010000) {case 0:return 0x01020003;case 4:return 0x123;case 8:return m->bad_iface==1?0:0x4001000;case 12:return 0x4002000;case 16:return 8;case 20:return m->bad_iface==2?0x4000:64;case 24:return m->enabled&&!m->no_fw?3:0;default:assert(0);}
 }
 if(a==0x90005934||a==0x9000593c||a==0x9000522c) {
  if(!m->enabled||m->no_fw)return 0;
  return a==0x90005934?10:a==0x9000593c?0x200000:0x50c0;
 }
 assert(a>=0x13000000 && a<0x13002500);assert(!m->unpowered);
 switch(a-0x13000000) {
 case 0:return m->bad_id?0xa0020001:0xa8620004;
 case 0x14:return m->bad_bits?0x1010:0x2830;
 case 0x18:return 0xff;
 case 0x20:return m->raw;
 case 0x28:return m->gpu_mask;
 case 0x34:return 0x100;
 case 0x300:return 1;case 0x304:return m->coherency;
 case 0xf00:return 0x44;case 0xf04:return 0x55;case 0xf08:return 0x66;case 0xf0c:return 0x77;
 case 0x100:return 0xff;case 0x104:return 0;
 case 0x110:return 1;case 0x114:return 0;
 case 0x200:return m->enabled?2:0;case 0x204:return 0;
 case 0x210:return m->enabled?1:0;case 0x214:return 0;
 case 0x140:return m->enabled?0xff:0;case 0x144:return 0;
 case 0x150:return m->enabled?1:0;case 0x154:return 0;
 case 0x120:return 1;case 0x124:return 0;case 0x160:return m->l2;case 0x220:return 0;
 case 0x704:return m->mcu;
 case 0x1000:return m->stale?0x80000000:m->job;
 case 0x1008:return m->bad_irq_mask && m->job_mask==UINT32_MAX?0:m->job_mask;
 case 0x2000:return m->mmu;case 0x2008:return m->mmu_mask;
 case 0x2428:return m->as_busy?1:0;
 case 0x2400:return m->live_table?0x80000000:m->table_low;case 0x2404:return m->table_high;
 case 0x2408:return m->memattr_lo;case 0x240c:return m->memattr_hi;
 case 0x2430:return m->bad_readback && m->as_updates==2?6:m->transcfg;case 0x2434:return 0;
 case 0x241c:return m->mmu?0xc0:0;case 0x2420:case 0x2424:return 0;
 default:assert(0);return 0;
 }
}
static void wr(void*p,uint64_t a,uint32_t v) {
 struct model*m=p;m->writes++;assert(!m->unpowered);
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
 case 0x2408:assert(v==0x4c4c9f4c);m->memattr_lo=v;return;case 0x240c:assert(v==0x4c4c4c4c);m->memattr_hi=v;return;
 case 0x2430:assert(v==1||v==0x420001c6);if(v!=1)assert(m->flushed);m->transcfg=v;return;
 case 0x2434:assert(v==0);return;
 case 0x2004:m->mmu&=~v;return;
 case 0x1004:m->job&=~v;return;
 case 0x700:
  if(v==0){if(!m->disable_fail)m->mcu=0;return;}
  assert(v==2 && m->l2 && m->as_updates==2 && m->transcfg==0x420001c6);
  assert((m->gpu_mask&0x103)==0x103 && m->job_mask==UINT32_MAX && (m->mmu_mask&0xff)==0xff);
  m->enabled++;m->mcu=1;
  if(m->request_done)m->mmu=0x10000;
  if(m->fw_fault)m->mmu=1;
  else if(!m->no_fw)m->job|=0x80000000;
  return;
 case 0x24:m->raw&=~v;return;
 case 0x30:assert(v==0x101);m->resets++;if(!m->reset_fail)m->raw|=0x100;return;
 default:assert(0);
 }
}
static uint64_t ticks(void*p){struct model*m=p;return m->stuck_timer?0:m->tick++;}
static void barrier(void*p){(void)p;}
static struct model model(void){return (struct model){.gpu_mask=0x55,.job_mask=0xaa,.mmu_mask=0xbb,.transcfg=1,.coherency=31};}
static struct sweet_csf_boot_config cfg(void){return (struct sweet_csf_boot_config){.gpu=0x13000000,.root_pa=0x90000000,.arena_pa=0x90000000,.arena_bytes=0x200000,.shared_offset=0x10000,.shared_bytes=0x20000,.timeout_ms=1,.private_probe_offset=0x5000};}
static int run(struct model*m,struct sweet_csf_boot_config*c,struct sweet_csf_boot_report*r){struct sweet_gpu_io io={m,rd,wr,ticks,barrier,1000};return sweet_csf_boot(c,&io,r);}
static void clean(struct model*m,struct sweet_csf_boot_report*r){assert(m->gpu_mask==0x55 && m->job_mask==0xaa && m->mmu_mask==0xbb && m->resets==1);assert(r->reset_completed);}
int main(void) {
 struct model m=model();struct sweet_csf_boot_config c=cfg();struct sweet_csf_boot_report r;
 assert(sizeof(r)==296);assert(!run(&m,&c,&r));assert(r.stage==7 && r.firmware_ready && r.version==0x01020003);clean(&m,&r);
 assert(r.diag_flags==31 && r.coherency_features==1 && r.coherency_before==31 && r.coherency_after==31);
 assert(!m.coherency_writes && !r.coherency_requested && !r.coherency_readback);
 assert(r.csf_config_before==0x44 && r.csf_config_after==0x44);
 assert(r.shader_config_before==0x55 && r.shader_config_after==0x55);
 assert(r.tiler_config_before==0x66 && r.tiler_config_after==0x66);
 assert(r.l2_mmu_config_before==0x77 && r.l2_mmu_config_after==0x77);
 assert(r.memattr_lo==0x4c4c9f4c && r.memattr_hi==0x4c4c4c4c);
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
 m=model();m.coherency=0;c=cfg();c.noncoherent=1;assert(!run(&m,&c,&r));clean(&m,&r);
 assert(m.coherency_writes==1 && r.diag_flags==127 && !r.coherency_before);
 assert(r.coherency_requested==31 && r.coherency_readback==31 && r.coherency_after==31);
 assert(r.csf_config_after==0x44 && r.shader_config_after==0x55 && r.tiler_config_after==0x66 && r.l2_mmu_config_after==0x77);
 assert(r.memattr_lo==0x4c4c9f4c && r.memattr_hi==0x4c4c4c4c && r.transcfg_lo==0x420001c6);
 m=model();m.coherency=0;m.no_fw=1;assert(run(&m,&c,&r)==-53 && !r.firmware_ready);clean(&m,&r);
 assert(m.coherency_writes==1 && r.diag_flags==127 && r.coherency_after==31);
 m=model();m.coherency=0;m.bad_coherency_readback=1;assert(run(&m,&c,&r)==-52);clean(&m,&r);
 assert(m.coherency_writes==1 && !m.enabled && !m.as_updates && !m.l2);
 assert(r.diag_flags==33 && r.coherency_requested==31 && !r.coherency_readback);
 m=model();c.noncoherent=2;assert(run(&m,&c,&r)==-50 && !m.reads && !m.writes);
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
'''
@unittest.skipUnless(shutil.which('cc'),'requires C compiler')
class CsfBootTests(unittest.TestCase):
    def test_real_state_machine_with_sanitizers(self):
        with tempfile.TemporaryDirectory() as directory:
            p=Path(directory);(p/'h.c').write_text(HARNESS)
            subprocess.run(['cc','-std=c11','-Wall','-Wextra','-Werror','-fsanitize=address,undefined',
                '-I',str(ROOT/'xnu/gpu'),str(p/'h.c'),str(ROOT/'xnu/gpu/mali_csf_boot.c'),'-o',str(p/'test')],check=True,capture_output=True)
            result=subprocess.run([str(p/'test')],capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)
if __name__=='__main__':unittest.main()
