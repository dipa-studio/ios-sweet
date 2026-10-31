"""Replay the real power/reset state machine against a strict MMIO model."""
from pathlib import Path
import ctypes
import shutil
import subprocess
import tempfile
import unittest
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_mtk_gpueb_protocol import fixture, flat_fdt, cells
import struct
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import adt

ROOT = Path(__file__).resolve().parents[2]
HARNESS = r'''
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include "mtk_gpueb_boot.h"

struct model {
    uint64_t tick;
    unsigned reads, writes, requests, resets, gpu_reads;
    uint32_t tx[8], rx[8], pending, spm, raw, mask;
    uint32_t magic, fw, gpu_id, as_present;
    int init_error, on_error, off_error, timeout_command;
    int stale, bad_reply, reset_timeout, stuck_timer, on_count;
};
static uint32_t read32(void *p, uint64_t at) {
    struct model *m=p; m->reads++;
    if(at==0x1c001f3c || at==0x1c001f40)return m->spm;
    if(at==0x13c5fd24)return m->magic;
    if(at==0x13c5fd34)return m->fw;
    if(at==0x13c62000)return 0;
    if(at==0x13c62078)return m->pending | (m->stale?2:0);
    if(at>=0x13c5fe3c && at<0x13c5fe5c)return m->rx[(at-0x13c5fe3c)/4];
    assert(at>=0x13000000 && at<=0x13000034);
    assert((m->spm&6)==6); m->gpu_reads++;
    switch(at-0x13000000) {
    case 0:return m->gpu_id; case 0x18:return m->as_present;
    case 0x20:return m->raw; case 0x28:return m->mask; case 0x34:return 0;
    default:assert(0); return 0;
    }
}
static void write32(void *p,uint64_t at,uint32_t value) {
    struct model *m=p; m->writes++;
    if(at>=0x13c5fd90 && at<0x13c5fdb0) {m->tx[(at-0x13c5fd90)/4]=value;return;}
    if(at==0x13c62074) {assert(value==2);m->pending=0;return;}
    if(at==0x13c62004) {
        assert(value==2 && !m->pending);m->requests++;
        if((int)m->tx[0]==m->timeout_command)return;
        memset(m->rx,0,sizeof(m->rx)); m->rx[0]=m->bad_reply?99:m->tx[0];
        if(m->tx[0]==0) {
            assert(m->tx[2]==0x40000000 && m->tx[3]==2);
            assert(m->tx[4]==0x40000400 && m->tx[5]==2);
            assert(m->tx[6]==0x400 && m->tx[7]==0xc00);
            m->rx[2]=(uint32_t)m->init_error;
        } else {
            assert(m->tx[0]==6);
            if(m->tx[2]) {m->rx[2]=(uint32_t)(m->on_error?m->on_error:m->on_count);if(!m->on_error)m->spm=6;}
            else {m->rx[2]=(uint32_t)m->off_error;if(!m->off_error)m->spm=2;}
        }
        m->pending=2;return;
    }
    assert((m->spm&6)==6);
    if(at==0x13000028) {m->mask=value;return;}
    if(at==0x13000024) {assert(value==0x100);m->raw&=~value;return;}
    assert(at==0x13000030 && value==0x101);m->resets++;
    if(!m->reset_timeout)m->raw|=0x100;
}
static uint64_t ticks(void *p) {struct model *m=p;return m->stuck_timer?0:m->tick++;}
static void barrier(void *p) {(void)p;}
static struct model model(void) {
    return (struct model){.spm=2,.magic=0x55667788,.fw=0x250000,
      .gpu_id=0xa0020001,.as_present=0xff,.mask=0x55,.timeout_command=-1,.on_count=1};
}
static struct sweet_gpu_boot_config config(void) {
    return (struct sweet_gpu_boot_config){
      .mailbox=0x13c5fd80,.irq_set=0x13c62004,.irq_clear=0x13c62074,
      .tx_status=0x13c62000,.rx_status=0x13c62078,.gpu=0x13000000,
      .gpueb=0x13c40000,.sleep=0x1c001000,.shared_base=0x240000000ULL,
      .shared_bytes=0x200000,.xnu_base=0x100000000ULL,.xnu_bytes=0x12e000000,
      .layout={0x240000000ULL,0x240000400ULL,0x400,0xc00},
      .tx_offset=0x10,.rx_offset=0xbc,.channel=1,.timeout_ms=1};
}
static int run(struct model *m,struct sweet_gpu_boot_config *c,struct sweet_gpu_boot_report *r) {
    struct sweet_gpu_io io={m,read32,write32,ticks,barrier,1000};
    return sweet_gpu_boot(c,&io,r);
}
static int powered(void *p,const struct sweet_gpu_io *io,uint64_t gpu) {
    struct model *m=p;(void)io;assert(gpu==0x13000000 && m->spm==6 && m->resets==1 && m->requests==2);
    return -55;
}
int main(void) {
    struct model m=model();struct sweet_gpu_boot_config c=config();struct sweet_gpu_boot_report r;
    assert(!run(&m,&c,&r));assert(r.stage==SWEET_GPU_COMPLETE);
    assert(r.gpu_id==m.gpu_id && r.reset_rawstat==0x100 && r.firmware_memory==0x250000000ULL);
    assert(m.requests==3 && m.resets==1 && m.mask==0x55 && m.spm==2 && !r.power_acquired);
    assert(r.cleanup_attempted && r.on_result==1 && r.off_result==0);
    m=model();c=config();c.boot_mode=2;assert(run(&m,&c,&r)==SWEET_GPU_ARGUMENT);assert(!m.reads && !m.writes);
    m=model();c=config();c.channel=32;assert(run(&m,&c,&r)==SWEET_GPU_ARGUMENT);assert(!m.reads);
    m=model();c=config();c.xnu_bytes=UINT64_MAX;assert(run(&m,&c,&r)==SWEET_GPU_ARGUMENT);assert(!m.reads);
    m=model();c=config();c.xnu_bytes=0x200000000ULL;assert(run(&m,&c,&r)==SWEET_GPU_OVERLAP);assert(!m.reads);
    m=model();c=config();m.spm=0;assert(run(&m,&c,&r)==SWEET_GPU_UNPOWERED);assert(!m.writes && !m.gpu_reads);
    m=model();m.magic=0;assert(run(&m,&c,&r)==SWEET_GPU_HANDOFF);assert(!m.writes);
    m=model();m.fw=0x110000;assert(run(&m,&c,&r)==SWEET_GPU_OVERLAP);assert(!m.writes);
    m=model();m.stale=1;assert(run(&m,&c,&r)==SWEET_GPU_STALE);assert(!m.writes && !m.gpu_reads);
    m=model();m.init_error=-5;assert(run(&m,&c,&r)==-5);assert(m.requests==1 && !m.gpu_reads);
    m=model();m.on_error=-7;assert(run(&m,&c,&r)==-7);assert(m.requests==2 && !m.gpu_reads && !r.cleanup_attempted);
    m=model();m.timeout_command=0;assert(run(&m,&c,&r)==SWEET_GPU_TIMEOUT);assert(m.requests==1 && !m.gpu_reads);
    m=model();m.timeout_command=6;assert(run(&m,&c,&r)==SWEET_GPU_TIMEOUT);assert(m.requests==2 && !r.cleanup_attempted);
    m=model();m.on_count=2;assert(run(&m,&c,&r)==SWEET_GPU_OWNER);assert(m.requests==3 && !m.gpu_reads);
    m=model();m.on_count=0;assert(run(&m,&c,&r)==SWEET_GPU_UNPOWERED);assert(m.requests==2 && !m.gpu_reads);
    m=model();m.bad_reply=1;assert(run(&m,&c,&r)==SWEET_GPU_REPLY);assert(m.requests==1);
    m=model();m.gpu_id=0x90000001;assert(run(&m,&c,&r)==SWEET_GPU_MODEL);assert(!m.resets && m.requests==3);
    m=model();m.reset_timeout=1;assert(run(&m,&c,&r)==SWEET_GPU_TIMEOUT);assert(m.requests==3 && m.mask==0x55);
    m=model();m.off_error=-9;assert(run(&m,&c,&r)==-9);assert(r.stage==SWEET_GPU_OFF && r.power_acquired);
    m=model();c=config();c.powered_probe=powered;c.probe_context=&m;
    assert(run(&m,&c,&r)==-55);assert(m.requests==3 && !r.power_acquired && m.spm==2);
    c=config();m=model();m.stuck_timer=1;m.timeout_command=0;assert(run(&m,&c,&r)==SWEET_GPU_TIMEOUT);
    puts("PASS: success, mode/address/ownership gates, stale/negative/malformed replies, bounded waits, reset and cleanup");
    return 0;
}
'''

@unittest.skipUnless(shutil.which('cc'), 'requires C compiler')
class GpuBootTests(unittest.TestCase):
    def test_real_state_machine_with_sanitizers(self):
        with tempfile.TemporaryDirectory(prefix='gpueb-boot-') as directory:
            work = Path(directory)
            source = work / 'test.c'
            source.write_text(HARNESS)
            binary = work / 'test'
            subprocess.run(['cc', '-std=c11', '-Wall', '-Wextra', '-Werror',
                            '-fsanitize=address,undefined', '-I', str(ROOT / 'xnu/gpu'),
                            str(source), str(ROOT / 'xnu/gpu/mtk_gpueb_boot.c'),
                            str(ROOT / 'xnu/gpu/mtk_gpueb_protocol.c'),
                            '-o', str(binary)], check=True, capture_output=True)
            result = subprocess.run([str(binary)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

class ShimGpuTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix='shim-gpu-')
        work = Path(cls.temp.name)
        stub = work / 'stub.c'
        stub.write_text(r'''
#include "mali_csf_boot.h"
struct sweet_csf_boot_report shim_csf_report = {
    .stage=4,.error=-53,.sample_flags=3,.version_before=0x01020304,
    .disable_error=-53,.disable_status=1,.gpu_irq_mask=0x80503,
    .mmu_irq_mask=0xff,.as_present=0xff,.irq_gate_passed=1,
    .shader_present_lo=0x1234,.tiler_transition_lo=1,
    .coherency_requested=31,.coherency_readback=31 };
unsigned calls;
void shim_gpu_host_run(const struct sweet_gpu_boot_config *c,struct sweet_gpu_boot_report *r) {
    calls++;
    *r=(struct sweet_gpu_boot_report){.stage=SWEET_GPU_COMPLETE,.gpu_id=0xa0020001,
      .reset_rawstat=0x100,.firmware_magic=0x55667788,.on_result=1,.off_result=0,
      .firmware_memory=0x250000000ULL,.spm_before=2,.spm_after=6};
    if(c->tx_offset!=16 || c->rx_offset!=188 || c->channel!=1)r->error=-100;
}
void con_hex2(const char *a,const char *b,uint32_t c,const char *d,uint32_t e)
{(void)a;(void)b;(void)c;(void)d;(void)e;}
void con_hex(const char *a,uint64_t b){(void)a;(void)b;}
''')
        binary = work / 'shim.dylib'
        subprocess.run(['cc', '-shared', '-fPIC', '-std=c11', '-Wall', '-Wextra', '-Werror',
                        '-DSHIM_GPU_HOST_TEST', '-DSHIM_CSF_PROBE', '-I', str(ROOT / 'xnu/gpu'), str(stub),
                        str(ROOT / 'shim/gpu.c'), str(ROOT / 'shim/fdt.c'),
                        str(ROOT / 'xnu/gpu/mtk_gpueb_protocol.c'), '-o', str(binary)],
                       check=True, capture_output=True)
        cls.lib = ctypes.CDLL(str(binary))
        cls.lib.shim_gpu_prepare.argtypes = [ctypes.c_size_t, ctypes.c_uint64, ctypes.c_uint64, ctypes.c_void_p, ctypes.c_void_p]
        cls.lib.shim_gpu_publish.argtypes = [ctypes.c_size_t, ctypes.c_uint32, ctypes.c_void_p, ctypes.c_uint64]

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def nodes(self):
        n = fixture()
        p = next(iter(n.values()))
        p.update({'gpueb_mem_addr': struct.pack('>Q', 0x240000000),
                  'gpueb_mem_size': struct.pack('>Q', 0x200000),
                  'send_table': cells(0,0,4,1,0,8,2,0,31)})
        # Real DT uses 43 TX words, then RX EVENT4 and GPUFREQ8.
        p['recv_table'] = cells(0,0,4,0,1,0,8,1)
        p['send_name_table'] = b'EVENT\0IPI_ID_GPUFREQ\0REST\0'
        p['recv_name_table'] = b'EVENT\0IPI_ID_GPUFREQ\0'
        p['reg-names'] = b'gpueb_base\0mbox0_base\0mbox0_set\0mbox0_clr\0mbox0_send\0mbox0_recv\0'
        p['reg'] = struct.pack('>12Q', 0x13c40000,0x22000,0x13c5fd80,0x280,
                              0x13c62004,4,0x13c62074,4,0x13c62000,4,0x13c62078,4)
        n['/chosen'] = {'atag,boot': struct.pack('<4I',16,0x41000802,0,0)}
        n['/soc/mali'] = {'compatible': b'mediatek,mali\0','reg': struct.pack('>QQ',0x13000000,0x480000)}
        n['/soc/gpufreq'] = {'compatible': b'mediatek,gpufreq\0',
            'reg-names': b'sleep\0','reg': struct.pack('>QQ',0x1c001000,0x1000)}
        return n

    def prepare(self, nodes):
        blob = ctypes.create_string_buffer(flat_fdt(nodes))
        report = ctypes.create_string_buffer(128)
        shared = ctypes.c_uint64()
        rc = self.lib.shim_gpu_prepare(ctypes.addressof(blob),0x100000000,0x12e000000,report,ctypes.byref(shared))
        return rc, report, shared.value

    def test_exact_live_style_handoff_and_bounded_adt_publication(self):
        rc, report, shared = self.prepare(self.nodes())
        self.assertEqual(rc,0)
        self.assertEqual(shared,0x240000000)
        root = adt.Node(); root.props = [('name',0,b'device-tree\0')]
        chosen = adt.Node(); chosen.props = [('name',0,b'chosen\0'),
             ('firmware-version',0,bytes(128)),('system-firmware-version',0,bytes(128)),
             ('sweet-gpu-report',0,bytes(128)),('sweet-csf-report',0,bytes(296))]; root.children=[chosen]
        data = adt.serialize(root)
        buf = ctypes.create_string_buffer(data)
        self.assertEqual(self.lib.shim_gpu_publish(ctypes.addressof(buf),len(data),report,shared),0)
        parsed,end = adt.parse(buf.raw[:len(data)])
        self.assertEqual(end,len(data))
        v = parsed.children[0].prop('firmware-version').split(b'\0')[0]
        self.assertIn(b'id=a0020001',v);self.assertIn(b'rst=00000100',v)
        self.assertTrue(v.startswith(b'sweet-shim/gpu2327'))
        csf=parsed.children[0].prop('sweet-csf-report')
        self.assertEqual(len(csf),296)
        self.assertEqual(struct.unpack_from('<2I',csf,288),(31,31))
        self.assertEqual(struct.unpack_from('<I',csf,88)[0],3)
        self.assertEqual(struct.unpack_from('<IiI',csf,112),(1,-53,0x01020304))
        self.assertEqual(struct.unpack_from('<4I',csf,128),(0x80503,0xff,0xff,1))
        self.assertEqual(struct.unpack_from('<I',csf,144)[0],0x1234)
        self.assertEqual(struct.unpack_from('<I',csf,176)[0],1)
        # A2324-sized report must be rejected, never overrun.
        chosen.props[-1]=('sweet-csf-report',0,bytes(128))
        short=adt.serialize(root);short_buf=ctypes.create_string_buffer(short)
        self.assertEqual(self.lib.shim_gpu_publish(ctypes.addressof(short_buf),len(short),report,shared),-1)
        chosen.props[-1]=('sweet-csf-report',0,bytes(288))
        previous=adt.serialize(root);previous_buf=ctypes.create_string_buffer(previous)
        self.assertEqual(self.lib.shim_gpu_publish(ctypes.addressof(previous_buf),len(previous),report,shared),-1)
        del chosen.props[-1]
        missing=adt.serialize(root); missing_buf=ctypes.create_string_buffer(missing)
        self.assertEqual(self.lib.shim_gpu_publish(ctypes.addressof(missing_buf),len(missing),report,shared),-1)
        for length in (0,7,40,len(data)-128):
            self.assertEqual(self.lib.shim_gpu_publish(ctypes.addressof(buf),length,report,shared),-1)

    def test_recovery_missing_memory_and_bad_channel_do_not_run(self):
        for change in ('recovery','memory','channel','reg'):
            n = self.nodes(); p=next(iter(n.values()))
            if change=='recovery': n['/chosen']['atag,boot']=struct.pack('<4I',16,0x41000802,2,2)
            elif change=='memory': del p['gpueb_mem_addr']
            elif change=='channel': p['send_table']=cells(0,0,4,1,0,7,2,0,35)
            else: p['reg-names']=b'wrong\0'
            calls=ctypes.c_uint.in_dll(self.lib,'calls').value
            self.assertEqual(self.prepare(n)[0],-1,change)
            self.assertEqual(ctypes.c_uint.in_dll(self.lib,'calls').value,calls)

if __name__ == '__main__':
    unittest.main()
