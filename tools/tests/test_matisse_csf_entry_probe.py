"""Pinned entry overlay rejects drift atomically; no vendor firmware in tests."""
from pathlib import Path
import shutil
import struct
import subprocess
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[2]
HARNESS=r'''
#include <assert.h>
#include <string.h>
#include "mali_csf_entry_probe.h"
static uint8_t a[0x12000], original[sizeof(a)];
int main(void) {
 struct sweet_csf_memory m={.mapping_count=3,.required_bytes=sizeof(a),
 .shared_va=0x04000000,.shared_bytes=4096,.shared_offset=0x11000};
 m.map[0]=(struct sweet_csf_mapping){.va=0,.bytes=4096,.arena_offset=0};
 m.map[1]=(struct sweet_csf_mapping){.va=0x01000000,.bytes=0x10000,.data_bytes=0xf848,.flags=13,.arena_offset=0x1000};
 m.map[2]=(struct sweet_csf_mapping){.va=0x04000000,.bytes=4096,.flags=0xc000001b,.arena_offset=0x11000};
 uint32_t words[]={0x02040000,0x010018ed};memcpy(a,words,8);
 uint32_t prefix[]={0x4826b672,0x010bf04f,0x48256001,0x0107f04f,0x48246001,0x21e0f44f};memcpy(a+0x28ec,prefix,24);
 uint32_t literal[]={0x40022000,0x40022004,0xe000ed24};memcpy(a+0x2988,literal,12);
 memcpy(original,a,sizeof(a));
 for(unsigned i=0;i<6;i++) {
  memcpy(a,original,sizeof(a));
  unsigned pos[]={4,0x28ec,0x2988,0x10900,0x11ffc,0x11000};a[pos[i]]^=1;
  uint8_t before[sizeof(a)];memcpy(before,a,sizeof(a));
  assert(sweet_csf_entry_probe_install(a,sizeof(a),&m));assert(!memcmp(a,before,sizeof(a)));
 }
 memcpy(a,original,sizeof(a));assert(!sweet_csf_entry_probe_install(a,sizeof(a),&m));
 assert(!memcmp(a+0x28ec,sweet_csf_entry_jump,8));
 assert(!memcmp(a+0x10900,sweet_csf_entry_trampoline,36));
 memcpy(a+0x28ec,original+0x28ec,8);memcpy(a+0x10900,original+0x10900,36);
 assert(!memcmp(a,original,sizeof(a)));
 for(unsigned i=0;i<9;i++) {
  memcpy(a,original,sizeof(a));
  unsigned pos[]={4,0x28ec,0x28f4,0x28fc,0x2988,0x298c,0x2990,0x1093f,0x11ffc};a[pos[i]]^=1;
  uint8_t before[sizeof(a)];memcpy(before,a,sizeof(a));
  assert(sweet_csf_inline_probe_install(a,sizeof(a),&m));assert(!memcmp(a,before,sizeof(a)));
 }
 memcpy(a,original,sizeof(a));assert(!sweet_csf_inline_probe_install(a,sizeof(a),&m));
 assert(!memcmp(a+0x28ec,sweet_csf_inline_jump,24));
 assert(!memcmp(a+0x10900,sweet_csf_inline_trampoline,64));
 memcpy(a+0x28ec,original+0x28ec,24);memcpy(a+0x10900,original+0x10900,64);
 assert(!memcmp(a,original,sizeof(a)));
 return 0;
}
'''
class EntryProbeTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which('cc'),'requires C compiler')
    def test_c_overlay_rejects_drift_before_writing(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);(p/'test.c').write_text(HARNESS)
            subprocess.run(['cc','-std=c11','-Wall','-Wextra','-Werror','-fsanitize=address,undefined',
                '-I',str(ROOT/'xnu/gpu'),str(p/'test.c'),'-o',str(p/'test')],check=True,capture_output=True)
            subprocess.run([str(p/'test')],check=True,capture_output=True)

    def test_linked_thumb_assembly_matches_installed_bytes(self):
        self.check_linked_thumb(False)
        self.check_linked_thumb(True)

    def check_linked_thumb(self, inline_marker):
        bins=list((Path.home()/'Library/Android/sdk/ndk').glob('*/toolchains/llvm/prebuilt/darwin-x86_64/bin'))
        if not bins:self.skipTest('requires ARM linker from Android NDK')
        ndk=sorted(bins)[-1]
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)
            (p/'link.ld').write_text('SECTIONS { .jump 0x010018ec : { *(.text.csf_entry_jump) } .probe 0x0100f900 : { *(.text.csf_entry_probe) } }')
            subprocess.run([str(ndk/'clang'),'--target=armv7m-none-eabi','-mcpu=cortex-m7','-mthumb',
                *(['-DCSF_INLINE_MARKER'] if inline_marker else []),
                '-nostdlib','-Wl,--build-id=none','-Wl,-T,'+str(p/'link.ld'),str(ROOT/'tools/matisse-csf-entry-probe.S'),
                '-o',str(p/'probe.elf')],check=True,capture_output=True)
            elf=(p/'probe.elf').read_bytes()
            shoff,=struct.unpack_from('<I',elf,32);entsize,count,names_index=struct.unpack_from('<HHH',elf,46)
            sections=[struct.unpack_from('<10I',elf,shoff+i*entsize) for i in range(count)]
            n=sections[names_index];names=elf[n[4]:n[4]+n[5]]
            actual={names[s[0]:].split(b'\0',1)[0].decode():elf[s[4]:s[4]+s[5]] for s in sections}
            import re
            header=(ROOT/'xnu/gpu/mali_csf_entry_probe.h').read_text()
            for section,array in ((('.jump','sweet_csf_inline_jump'),('.probe','sweet_csf_inline_trampoline'))
                                  if inline_marker else (('.jump','sweet_csf_entry_jump'),('.probe','sweet_csf_entry_trampoline'))):
                body=header.split(array+'[] = {')[1].split('}')[0]
                self.assertEqual(actual[section],bytes(int(x,16) for x in re.findall(r'0x([0-9a-f]+)',body)))
            self.assertFalse(any(s[1] in (4,9) and s[5] for s in sections))

class InlineExecutionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import importlib.util
        if not importlib.util.find_spec('unicorn'):raise unittest.SkipTest('requires Unicorn')
        spec=importlib.util.spec_from_file_location('fetch',ROOT/'tools/matisse-csf-fetch-audit.py')
        cls.audit=importlib.util.module_from_spec(spec);spec.loader.exec_module(cls.audit)
        data=bytearray(136+0xf848+4096)
        struct.pack_into('<I',data,0,0xc3f13a6e);struct.pack_into('<I',data,16,116)
        sections=[(9,0,0x1000,128,136),(13,0x01000000,0x01010000,136,136+0xf848),
                  (0x8000000b,0x02000000,0x02040000,0,0),
                  (0xc000001b,0x04000000,0x04001000,136+0xf848,len(data))]
        for i,fields in enumerate(sections):struct.pack_into('<6I',data,20+i*24,24<<8,*fields)
        struct.pack_into('<II',data,128,0x02040000,0x010018ed)
        struct.pack_into('<6I',data,136+0x18ec,0x4826b672,0x010bf04f,0x48256001,0x0107f04f,0x48246001,0x21e0f44f)
        struct.pack_into('<HH',data,136+0x1904,0x6001,0xe7fe)
        struct.pack_into('<3I',data,136+0x1988,0x40022000,0x40022004,0xe000ed24)
        with tempfile.TemporaryDirectory() as d:
            f=Path(d)/'synthetic.bin';f.write_bytes(data)
            cls.original,cls.plan=cls.audit.build_arena(f,0x40077000,memory_group=6)
            cls.patched,p=cls.audit.build_arena(f,0x40077000,memory_group=6,inline_entry=True)
            assert p==cls.plan

    def run_arena(self,arena,**kwargs):
        return self.audit.replay(arena,self.plan,step_limit=100,self_loop_pc=0x01001906,
                                 entry_checkpoint=True,resume_pc=0x01001904,**kwargs)

    def test_inline_store_precedes_remote_arrival_and_original_mmio(self):
        first=self.run_arena(self.patched,stop_before_pc=0x0100f900)
        self.assertEqual(first['reason'],'diagnostic-checkpoint')
        self.assertEqual(first['startup_probes']['entry_checkpoint']['after'],'0x53545542')
        self.assertEqual(first['mmio_writes'],[])
        self.assertEqual(first['version'],'0x0')
        original=self.run_arena(self.original);complete=self.run_arena(self.patched)
        self.assertEqual(complete['reason'],'diagnostic-self-loop')
        self.assertEqual(complete['startup_probes']['entry_checkpoint']['after'],'0x5452414d')
        self.assertEqual(complete['entry_resume_registers'],original['entry_resume_registers'])
        # First two stores were relocated into the tail, preserving their addresses/values/order.
        strip_pc=lambda result:[{k:v for k,v in w.items() if k!='pc'} for w in result['mmio_writes']]
        self.assertEqual(strip_pc(complete),strip_pc(original))
        self.assertEqual([w['value'] for w in complete['startup_probe_writes'] if w['name']=='entry_checkpoint'],
                         ['0x53545542','0x5452414d'])

    def test_remote_fetch_failure_leaves_inline_checkpoint_visible(self):
        a=bytearray(self.patched);table=0;va=0x0100f900
        for shift in (39,30,21):
            desc,=struct.unpack_from('<Q',a,table+((va>>shift)&511)*8)
            table=(desc&self.audit.PA_MASK)-self.plan['root_pa']
        pos=table+((va>>12)&511)*8;desc,=struct.unpack_from('<Q',a,pos)
        struct.pack_into('<Q',a,pos,desc|(1<<53))
        result=self.run_arena(a)
        self.assertEqual(result['reason'],'access-violation')
        self.assertEqual(result['startup_probes']['entry_checkpoint']['after'],'0x53545542')
        self.assertEqual(result['mmio_writes'],[])
