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
 uint32_t prefix[]={0x4826b672,0x010bf04f};memcpy(a+0x28ec,prefix,8);
 uint32_t literal=0x40022000;memcpy(a+0x2988,&literal,4);
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
        bins=list((Path.home()/'Library/Android/sdk/ndk').glob('*/toolchains/llvm/prebuilt/darwin-x86_64/bin'))
        if not bins:self.skipTest('requires ARM linker from Android NDK')
        ndk=sorted(bins)[-1]
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)
            (p/'link.ld').write_text('SECTIONS { .jump 0x010018ec : { *(.text.csf_entry_jump) } .probe 0x0100f900 : { *(.text.csf_entry_probe) } }')
            subprocess.run([str(ndk/'clang'),'--target=armv7m-none-eabi','-mcpu=cortex-m7','-mthumb',
                '-nostdlib','-Wl,--build-id=none','-Wl,-T,'+str(p/'link.ld'),str(ROOT/'tools/matisse-csf-entry-probe.S'),
                '-o',str(p/'probe.elf')],check=True,capture_output=True)
            elf=(p/'probe.elf').read_bytes()
            shoff,=struct.unpack_from('<I',elf,32);entsize,count,names_index=struct.unpack_from('<HHH',elf,46)
            sections=[struct.unpack_from('<10I',elf,shoff+i*entsize) for i in range(count)]
            n=sections[names_index];names=elf[n[4]:n[4]+n[5]]
            actual={names[s[0]:].split(b'\0',1)[0].decode():elf[s[4]:s[4]+s[5]] for s in sections}
            import re
            header=(ROOT/'xnu/gpu/mali_csf_entry_probe.h').read_text()
            for section,array in (('.jump','sweet_csf_entry_jump'),('.probe','sweet_csf_entry_trampoline')):
                body=header.split(array+'[] = {')[1].split('}')[0]
                self.assertEqual(actual[section],bytes(int(x,16) for x in re.findall(r'0x([0-9a-f]+)',body)))
            self.assertFalse(any(s[1] in (4,9) and s[5] for s in sections))
