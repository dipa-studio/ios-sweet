"""Decode and encode the MT6983 gpufreq shared-status layout.

The C harness runs the real translation unit with sanitizers. Field offsets
are asserted explicitly so a silent reordering of the vendor struct cannot
pass as a green test.
"""
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]

HARNESS = r'''
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include "mtk_gpufreq.h"

static void put(uint8_t *p, unsigned off, uint32_t v) {
    p[off]=v&0xff; p[off+1]=(v>>8)&0xff; p[off+2]=(v>>16)&0xff; p[off+3]=(v>>24)&0xff;
}
/* Writes the pinned field offsets of struct gpufreq_shared_status. */
static void fill(uint8_t *s) {
    memset(s,0,0x400);
    put(s,0x00,2);       /* cur_oppidx_gpu */
    put(s,0x04,1);       /* cur_oppidx_stack */
    put(s,0x08,8);       /* opp_num_gpu */
    put(s,0x0c,6);       /* opp_num_stack */
    put(s,0x10,500000);  /* cur_fgpu kHz */
    put(s,0x14,400000);  /* cur_fstack */
    put(s,0x18,750000);  /* cur_vgpu uV */
    put(s,0x1c,700000);  /* cur_vstack */
    put(s,0x20,700000);  /* cur_vsram_gpu */
    put(s,0x60,1);       /* power_control */
    put(s,0x64,1);       /* dvfs_state */
    put(s,0x68,0xff);    /* shader_present */
    put(s,0x6c,1);       /* power_count */
}
int main(void) {
    uint8_t raw[0x400], msg[32], copy[32];
    struct sweet_gpufreq_status s, guard;
    unsigned i;

    /* --- encoding: exact wire bytes, tail must be zero ------------------ */
    memset(msg,0xa5,sizeof(msg));
    assert(sweet_gpufreq_encode_commit(SWEET_GPUFREQ_TARGET_GPU,3,msg)==SWEET_GPUFREQ_OK);
    assert(msg[0]==7 && msg[1]==0 && msg[2]==0 && msg[3]==0);
    assert(msg[4]==1 && msg[5]==0 && msg[6]==0 && msg[7]==0);
    assert(msg[8]==3 && msg[9]==0 && msg[10]==0 && msg[11]==0);
    for(i=12;i<32;i++) assert(msg[i]==0);
    memset(msg,0xa5,sizeof(msg));
    assert(sweet_gpufreq_encode_query(SWEET_GPUFREQ_CMD_GET_FREQ,
        SWEET_GPUFREQ_TARGET_GPU,5,msg)==SWEET_GPUFREQ_OK);
    assert(msg[0]==1 && msg[4]==1 && msg[8]==5);
    for(i=12;i<32;i++) assert(msg[i]==0);
    /* --- encoding: rejected inputs leave the buffer untouched ----------- */
    memset(copy,0xa5,sizeof(copy)); memcpy(msg,copy,sizeof(msg));
    assert(sweet_gpufreq_encode_commit(3,0,msg)==SWEET_GPUFREQ_ARGUMENT);
    assert(!memcmp(msg,copy,sizeof(msg)));
    assert(sweet_gpufreq_encode_commit(0,-1,msg)==SWEET_GPUFREQ_ARGUMENT);
    assert(sweet_gpufreq_encode_commit(0,SWEET_GPUFREQ_MAX_OPP,msg)==SWEET_GPUFREQ_ARGUMENT);
    assert(!memcmp(msg,copy,sizeof(msg)));
    assert(sweet_gpufreq_encode_query(SWEET_GPUFREQ_CMD_COMMIT,0,0,msg)==SWEET_GPUFREQ_ARGUMENT);
    assert(sweet_gpufreq_encode_query(SWEET_GPUFREQ_CMD_GET_FREQ,3,0,msg)==SWEET_GPUFREQ_ARGUMENT);
    assert(sweet_gpufreq_encode_query(SWEET_GPUFREQ_CMD_GET_FREQ,0,-1,msg)==SWEET_GPUFREQ_ARGUMENT);
    assert(!memcmp(msg,copy,sizeof(msg)));
    assert(sweet_gpufreq_encode_commit(0,0,NULL)==SWEET_GPUFREQ_ARGUMENT);

    /* --- decoding: the happy path reads the pinned offsets -------------- */
    fill(raw);
    memset(&s,0,sizeof(s));
    assert(sweet_gpufreq_decode(raw,sizeof(raw),&s)==SWEET_GPUFREQ_OK);
    assert(s.cur_oppidx_gpu==2 && s.cur_oppidx_stack==1);
    assert(s.opp_num_gpu==8 && s.opp_num_stack==6);
    assert(s.cur_fgpu==500000 && s.cur_fstack==400000);
    assert(s.cur_vgpu==750000 && s.cur_vstack==700000);
    assert(s.cur_vsram_gpu==700000);
    assert(s.power_control==1 && s.dvfs_state==1 && s.shader_present==0xff);
    assert(s.power_count==1);
    /* The decoder only needs its own span, not the whole 1 KiB region. */
    assert(sweet_gpufreq_decode(raw,SWEET_GPUFREQ_DECODE_BYTES,&s)==SWEET_GPUFREQ_OK);

    /* --- decoding: rejected regions leave the output untouched ---------- */
    memset(&guard,0x5a,sizeof(guard)); s=guard;
    memset(raw,0,sizeof(raw));   /* never written by GPUEB */
    assert(sweet_gpufreq_decode(raw,sizeof(raw),&s)==SWEET_GPUFREQ_RANGE);
    assert(!memcmp(&s,&guard,sizeof(s)));
    memset(raw,0xff,sizeof(raw)); /* saturated bus or torn read */
    assert(sweet_gpufreq_decode(raw,sizeof(raw),&s)==SWEET_GPUFREQ_RANGE);
    assert(!memcmp(&s,&guard,sizeof(s)));
    fill(raw);
    assert(sweet_gpufreq_decode(raw,SWEET_GPUFREQ_DECODE_BYTES-1,&s)==SWEET_GPUFREQ_RANGE);
    assert(!memcmp(&s,&guard,sizeof(s)));
    assert(sweet_gpufreq_decode(NULL,sizeof(raw),&s)==SWEET_GPUFREQ_ARGUMENT);
    assert(!memcmp(&s,&guard,sizeof(s)));
    assert(sweet_gpufreq_decode(raw,sizeof(raw),NULL)==SWEET_GPUFREQ_ARGUMENT);

    /* --- decoding: every discriminating bound --------------------------- */
    fill(raw); put(raw,0x08,0);
    assert(sweet_gpufreq_decode(raw,sizeof(raw),&s)==SWEET_GPUFREQ_RANGE);
    fill(raw); put(raw,0x08,SWEET_GPUFREQ_MAX_OPP+1);
    assert(sweet_gpufreq_decode(raw,sizeof(raw),&s)==SWEET_GPUFREQ_RANGE);
    fill(raw); put(raw,0x00,8);          /* oppidx == opp_num */
    assert(sweet_gpufreq_decode(raw,sizeof(raw),&s)==SWEET_GPUFREQ_RANGE);
    fill(raw); put(raw,0x00,0xffffffff); /* oppidx == -1 is valid */
    { uint8_t t[0x400]; memcpy(t,raw,sizeof(t)); put(t,0x00,0xffffffff);
      assert(sweet_gpufreq_decode(t,sizeof(t),&s)==SWEET_GPUFREQ_OK);
      assert(s.cur_oppidx_gpu==-1); }
    fill(raw); put(raw,0x00,0xfffffffe); /* oppidx == -2 is not */
    assert(sweet_gpufreq_decode(raw,sizeof(raw),&s)==SWEET_GPUFREQ_RANGE);
    /* Zero frequency and voltage are recorded, not rejected: "not
     * published yet" is itself the observation we want in the report. */
    fill(raw); put(raw,0x10,0); put(raw,0x18,0); put(raw,0x6c,0);
    assert(sweet_gpufreq_decode(raw,sizeof(raw),&s)==SWEET_GPUFREQ_OK);
    assert(s.cur_fgpu==0 && s.cur_vgpu==0 && s.power_count==0);
    fill(raw); put(raw,0x10,SWEET_GPUFREQ_MAX_KHZ+1);
    assert(sweet_gpufreq_decode(raw,sizeof(raw),&s)==SWEET_GPUFREQ_RANGE);
    fill(raw); put(raw,0x18,SWEET_GPUFREQ_MAX_UV+1);
    assert(sweet_gpufreq_decode(raw,sizeof(raw),&s)==SWEET_GPUFREQ_RANGE);
    fill(raw); put(raw,0x6c,SWEET_GPUFREQ_MAX_POWER_COUNT+1);
    assert(sweet_gpufreq_decode(raw,sizeof(raw),&s)==SWEET_GPUFREQ_RANGE);
    fill(raw); put(raw,0x6c,0xffffffff); /* power_count == -1 */
    assert(sweet_gpufreq_decode(raw,sizeof(raw),&s)==SWEET_GPUFREQ_RANGE);
    puts("PASS: exact wire bytes, untouched-on-error, pinned offsets, every decode bound");
    return 0;
}
'''

@unittest.skipUnless(shutil.which('cc'), 'requires C compiler')
class GpufreqTests(unittest.TestCase):
    def test_layout_codec_with_sanitizers(self):
        with tempfile.TemporaryDirectory(prefix='gpufreq-') as directory:
            work = Path(directory)
            source = work / 'test.c'
            source.write_text(HARNESS)
            binary = work / 'test'
            subprocess.run(['cc', '-std=c11', '-Wall', '-Wextra', '-Werror',
                            '-fsanitize=address,undefined', '-I', str(ROOT / 'xnu/gpu'),
                            str(source), str(ROOT / 'xnu/gpu/mtk_gpufreq.c'),
                            '-o', str(binary)], check=True, capture_output=True)
            result = subprocess.run([str(binary)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

if __name__ == '__main__':
    unittest.main()
