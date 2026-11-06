"""Compile the exact bounds predicate delivered in the kernel patch."""
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
PATCH = ROOT / 'xnu/patches/0119-matisse-gpu-persistent-evidence.patch'

class DiagnosticBoundsTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which('cc'), 'requires C compiler')
    def test_real_patch_bounds_with_sanitizers(self):
        patch = PATCH.read_text()
        added = '\n'.join(line[1:] for line in patch.splitlines()
                          if line.startswith('+') and not line.startswith('+++'))
        begin = added.index('static bool\nsweet_ufs_write_allowed(')
        end = added.index('\nstatic int\nufs_write_blocks_checked', begin)
        predicate = added[begin:end]
        source = '#include <stdint.h>\n#include <stdbool.h>\n#include <assert.h>\n' + predicate + r'''
int main(void) {
    /* first=100, blocks=5000 => diagnostic tail begins at4075. */
    assert(sweet_ufs_write_allowed(false,true,100,5000,4075,1,256));
    assert(sweet_ufs_write_allowed(false,true,100,5000,5099,1,256));
    assert(!sweet_ufs_write_allowed(false,true,100,5000,4074,1,256));
    assert(!sweet_ufs_write_allowed(false,false,100,5000,4075,1,256));
    assert(sweet_ufs_write_allowed(true,false,100,5000,100,256,256));
    assert(!sweet_ufs_write_allowed(false,true,100,2049,2148,1,256));
    assert(!sweet_ufs_write_allowed(false,true,100,5000,5099,2,256));
    assert(!sweet_ufs_write_allowed(true,false,100,5000,99,1,256));
    assert(!sweet_ufs_write_allowed(true,false,100,5000,5100,1,256));
    assert(!sweet_ufs_write_allowed(true,false,100,5000,100,0,256));
    assert(!sweet_ufs_write_allowed(true,false,100,5000,100,257,256));
    assert(!sweet_ufs_write_allowed(true,false,0,UINT64_MAX,UINT64_MAX-1,4,256));
    assert(!sweet_ufs_write_allowed(true,false,0,UINT64_MAX,UINT32_MAX,2,256));
    assert(sweet_ufs_write_allowed(true,false,0,UINT64_MAX,UINT32_MAX,1,256));
    assert(!sweet_ufs_write_allowed(true,false,UINT64_MAX,1,0,1,256));
    return 0;
}
'''
        with tempfile.TemporaryDirectory() as directory:
            p = Path(directory)
            (p/'bounds.c').write_text(source)
            subprocess.run(['cc','-std=c11','-Wall','-Wextra','-Werror',
                            '-fsanitize=address,undefined',str(p/'bounds.c'),
                            '-o',str(p/'bounds')],check=True,capture_output=True)
            subprocess.run([str(p/'bounds')],check=True,capture_output=True)
        self.assertIn('ufs_write_blocks_checked(base + 1 + blk, n, true)', patch)
        self.assertIn('ufs_write_blocks_checked(base, 1, true)', patch)
        self.assertIn('ufs_write_blocks_checked(lba, count, false)', patch)


@unittest.skipUnless(shutil.which('git'), 'requires git')
class PersistentReportPatchTests(unittest.TestCase):
    def test_tracked_patch_sequence_applies_with_normal_git_flags(self):
        # Exercise the CI-style contextual apply, not --unidiff-zero. A
        # locally edited build tree must not conceal a broken source patch.
        names = subprocess.check_output(['git','ls-files','--','xnu/patches/*.patch'],
                                        cwd=ROOT,text=True).splitlines()
        identity = sorted(n for n in names if n.endswith('-identity.patch'))
        self.assertTrue(identity, 'no identity patch carries the build id')
        last = Path(ROOT / identity[-1]).read_text()
        # The patch removes the old id and adds the new one; the added line is
        # the last occurrence in the file.
        expected = int(last.split('#define SWEET_BUILD_ID 0x')[-1].split('u')[0], 16)
        evidence='xnu/patches/0136-matisse-gpu-dvfs-evidence.patch'
        if evidence not in names:
            names = sorted(names + [evidence])
        self.assertTrue(names)
        with tempfile.TemporaryDirectory(prefix='csf-evidence-patches-') as directory:
            for name in names:
                result = subprocess.run(['git','apply','--whitespace=nowarn',
                    '--include=bsd/dev/sweet_ufs.c',str(ROOT/name)],
                    cwd=directory,capture_output=True,text=True)
                self.assertEqual(result.returncode,0,name+': '+result.stderr)
            source = (Path(directory)/'bsd/dev/sweet_ufs.c').read_text()
        # The last identity patch in the sequence decides the id the tree ends on.
        self.assertEqual(int(source.split('#define SWEET_BUILD_ID 0x')[1].split('u')[0],16),
                         expected)
        begin = source.index('static void\nsweet_gpu_report_marks(void)\n{')
        end = source.index('\n}\n',begin)
        report = source[begin:end]
        self.assertIn('size == 696',report)
        self.assertIn('uint32_t csf[174];',report)
        self.assertIn('i < 87;',report)
        self.assertIn('sweet_mark(320 + i, a, SWEET_BUILD_ID);',report)
        # 2338 widens the GPU report to 112 bytes without touching the CSF ABI.
        self.assertIn('uint32_t words[28];',report)
        self.assertIn('for (uint32_t i = 0; i < 14; i++) {',report)
        self.assertIn('sweet_mark(300 + i, a, SWEET_BUILD_ID);',report)
        self.assertIn('for (uint32_t i = 0; i < 16; i++) {\n'
                      '\t\tsweet_mark(70 + i, i, sweet_disp_trace[i]);',source)


class ReportDecodeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import importlib.util
        spec=importlib.util.spec_from_file_location('gpu_report',ROOT/'tools/matisse-gpu-report.py')
        cls.module=importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.module)

    def marks(self, error=0, omit=None, build=0x2321, reset=0x100, init=0, spm=6,
              stage=10, on=1, off=0):
        import struct
        raw=struct.pack('<I4i8I4xQ2I',stage,error,init,on,off,2,spm,2,0x55667788,
                        0xa0020001,0,reset,0xff,0x250000000,0,1)
        records=[(99,0,build,0)]
        records += [(300+i,0,struct.unpack_from('<Q',raw,i*8)[0],build)
                    for i in range(9) if i!=omit]
        block=bytearray(4096)
        struct.pack_into('<8sII',block,0,b'SWEETMRK',1,len(records))
        for i,record in enumerate(records):
            struct.pack_into('<IIQQ',block,16+i*24,*record)
        return block

    def test_complete_verified_report(self):
        result=self.module.decode(self.marks())
        self.assertTrue(result['power_reset_verified'])
        self.assertFalse(result['csf_firmware_boot_verified'])
        self.assertEqual(result['firmware_memory'],0x250000000)

    def marks_dvfs(self, valid=0xf, oppidx=2, power_count=1, freq=500000,
                   commit=0, omit=None, build=0x2338, **changes):
        import struct
        block = self.csf_marks(build=build, **changes)
        raw = struct.pack('<I2i6Ii', valid, oppidx, power_count, 8, freq, 750000,
                          700000, 1, 1, commit)
        count = struct.unpack_from('<I', block, 12)[0]
        for i in range(5):
            if i == omit:
                continue
            struct.pack_into('<IIQQ', block, 16 + count*24 + i*24,
                             309 + i, 0, struct.unpack_from('<Q', raw, i*8)[0], build)
        struct.pack_into('<I', block, 12, count + (5 if omit is None else 4))
        return block

    def test_2338_gpufreq_block_is_decoded(self):
        result = self.module.decode(self.marks_dvfs(), 0x2338)
        self.assertTrue(result['power_reset_verified'])
        g = result['gpufreq']
        self.assertEqual((g['valid'], g['oppidx'], g['power_count'], g['opp_num']),
                         (0xf, 2, 1, 8))
        self.assertEqual((g['freq_khz'], g['volt_uv'], g['vsram_uv']),
                         (500000, 750000, 700000))
        self.assertEqual(g['commit_result'], 0)

    def test_2338_gpufreq_rejections_and_older_builds(self):
        with self.assertRaises(ValueError):
            self.module.decode(self.marks_dvfs(valid=0x10), 0x2338)
        with self.assertRaises(ValueError):
            self.module.decode(self.marks_dvfs(omit=4), 0x2338)
        # A 2338 capture read under the2337 ABI must be rejected, not truncated.
        with self.assertRaises(ValueError):
            self.module.decode(self.marks_dvfs(), 0x2337)
        # A 2337 capture must never grow a gpufreq section.
        self.assertNotIn('gpufreq', self.module.decode(self.marks()))

    def fetch_prime_report(self, **changes):
        values = dict(stage=4, error=-53, version=0, features=0, job_raw=0,
                      firmware_ready=0, input_va=0x01000200, groups=11,
                      platform_reserved=0x202)
        values.update(changes)
        return self.module.decode(self.marks_dvfs(build=0x2379, **values), 0x2379)

    def test_fetch_prime_checkpoints_are_distinct_and_never_firmware_ready(self):
        for counter, outcome in ((9, 'fetch-call-incomplete'),
                                 (10, 'data-read-incomplete'),
                                 (11, 'data-read-returned')):
            with self.subTest(counter=counter):
                report = self.fetch_prime_report(groups=counter)
                self.assertEqual(report['csf']['fetch_prime_outcome'], outcome)
                self.assertFalse(report['csf_firmware_boot_verified'])

    def test_fetch_prime_faults_and_unexpected_states_are_inconclusive(self):
        for changes in (dict(error=-54), dict(mmu_raw=1), dict(as_fault=0x7cd002c2)):
            with self.subTest(changes=changes):
                self.assertEqual(self.fetch_prime_report(**changes)['csf']['fetch_prime_outcome'],
                                 'fault')
        for changes in (dict(mcu_status=0), dict(stage=7, error=0), dict(firmware_ready=1)):
            with self.subTest(changes=changes):
                self.assertEqual(self.fetch_prime_report(**changes)['csf']['fetch_prime_outcome'],
                                 'unexpected-state')

    def test_fetch_prime_requires_marker_and_a_defined_counter(self):
        self.assertEqual(self.fetch_prime_report(input_va=0x04002000)['csf']['fetch_prime_outcome'],
                         'marker-absent')
        for counter in (8, 12, 0xffffffff):
            with self.subTest(counter=counter):
                self.assertEqual(self.fetch_prime_report(groups=counter)['csf']['fetch_prime_outcome'],
                                 'unexpected-counter')

    def test_failure_is_not_success(self):
        self.assertFalse(self.module.decode(self.marks(error=-23))['power_reset_verified'])
        self.assertFalse(self.module.decode(self.marks(reset=0))['power_reset_verified'])
        self.assertFalse(self.module.decode(self.marks(init=-1))['power_reset_verified'])
        self.assertFalse(self.module.decode(self.marks(spm=2))['power_reset_verified'])

    def test_stale_partial_wrong_build_and_duplicate_rejected(self):
        import struct
        for data in [bytes(4096),self.marks(omit=4),self.marks(build=0x2316),bytes(40)]:
            with self.assertRaises(ValueError):self.module.decode(data)
        data=self.marks()
        count=struct.unpack_from('<I',data,12)[0]
        struct.pack_into('<I',data,12,count+1)
        struct.pack_into('<IIQQ',data,16+24*count,300,0,0,0x2321)
        with self.assertRaises(ValueError):self.module.decode(data)

    def csf_marks(self, omit=None, tag=None, build=0x2322, platform=None, **changes):
        import struct
        data=self.marks(build=build, **(platform or {}))
        if tag is None:tag=build
        values=dict(zip(self.module.CSF_KEYS,[7,0,0,0x2830,1,0,1,1,
            0x80000000,0,0,0,0,0x01020003,0x123,0x4001000,0x4002000,8,64,0x100,1,1]))
        values.update(changes)
        if build>=0x2323:
            values.update(zip(self.module.CSF_DIAGNOSTIC_KEYS,
                [3,0x600,0,0x42000006 if build>=0x2329 else 0x420001c6,0x90000000,0,0,0,0x01020003,0]))
            values.update(changes)
        raw=struct.pack('<I2i19I',*(values[k] for k in self.module.CSF_KEYS))
        if build>=0x2323:
            if build>=0x2324:values['reserved']=changes.get('reserved',0xffffffff)
            raw+=struct.pack('<7Ii2I',*(values[k] for k in self.module.CSF_DIAGNOSTIC_KEYS))
        if build>=0x2325:
            values.update(zip(self.module.CSF_MASK_CORE_KEYS,
                [0x80503,0xff,0xff,1,0xff,0,0,0,0xff,0,1,0,0,0,1,0]))
            values['sample_flags']=changes.get('sample_flags',15)
            values.update(changes)
            raw=struct.pack('<I2i19I',*(values[k] for k in self.module.CSF_KEYS))
            raw+=struct.pack('<7Ii2I',*(values[k] for k in self.module.CSF_DIAGNOSTIC_KEYS))
            raw+=struct.pack('<16I',*(values[k] for k in self.module.CSF_MASK_CORE_KEYS))
        if build>=0x2326:
            values.update(zip(self.module.CSF_STARTUP_KEYS,
                [31,3,31,31,0x44,0x44,0x55,0x55,0x66,0x66,0x77,0x77,
                 0x4c4c884c if build>=0x2330 else 0x4c4c9f4c,0x4c4c4c4c,0,10,0,0x200000,0,0x50c0,0,3,0x90045000,0]))
            values.update(changes)
            raw+=struct.pack('<24I',*(values[k] for k in self.module.CSF_STARTUP_KEYS))
        if build>=0x2327:
            values['diag_flags']=changes.get('diag_flags',127)
            # diag_flags is the first word in the2326 append.
            raw=raw[:192]+struct.pack('<I',values['diag_flags'])+raw[196:]
            raw+=struct.pack('<2I',changes.get('coherency_requested',31),
                             changes.get('coherency_readback',31))
        if build>=0x2328:
            raw+=struct.pack('<2I',changes.get('pte_group_requested',6),changes.get('pte_pages_built',293))
        if build>=0x2331:
            raw+=struct.pack('<2I',changes.get('platform_sample_flags',3),changes.get('platform_reserved',0))
            raw+=struct.pack('<32I',*range(32))
        if build>=0x2332:
            raw+=struct.pack('<6I',changes.get('access_sample_flags',3),changes.get('access_reserved',0),
                changes.get('firmware_probe_va',0x01000000),changes.get('firmware_probe_pa_lo',0x90006000),
                changes.get('firmware_probe_pa_hi',0),changes.get('firmware_probe_expected',0x12345678))
            for prefix in ('before','after'):
                words=[0,0x80000000 if prefix=='after' else 0,0,0,0,0,1,0,0,0,0x12345678,
                       values['version'] if prefix=='after' else values['version_before']]
                words[10]=changes.get('word_'+prefix,words[10])
                for i,key in enumerate(self.module.CSF_ACCESS_KEYS):
                    words[i]=changes.get('access_'+prefix+'_'+key,words[i])
                raw+=struct.pack('<12I',*words)
        if build>=0x2333:
            raw+=struct.pack('<2I',changes.get('path_sample_flags',3),changes.get('path_reserved',0))
            for prefix in ('before','after'):
                words=[0xfff0fff0,0xfff0fff0,0,0,0,0,0,0]+[0]*8
                for i,key in enumerate(self.module.CSF_PATH_KEYS):
                    words[i]=changes.get('path_'+prefix+'_'+key,words[i])
                raw+=struct.pack('<16I',*words)
        count=struct.unpack_from('<I',data,12)[0]
        for i in range(len(raw)//8):
            if i==omit:continue
            struct.pack_into('<IIQQ',data,16+24*count,320+i,0,
                             struct.unpack_from('<Q',raw,8*i)[0],tag)
            count+=1
        struct.pack_into('<I',data,12,count)
        return data

    # platform_path_released needs every MFG1 block mask clear; the shared
    # fixture defaults leave them set, which alone would hold readiness down.
    ZERO_PATH = {f'path_{side}_{key}': 0 for side in ('before','after')
                 for key in ('rpc_enable','rpc_status','infra_enable','infra_status',
                             'emi0_enable','emi0_status','emi1_enable','emi1_status')}

    def test_2380_vendor_memattr_ready(self):
        result = self.module.decode(self.marks_dvfs(build=0x2380,
            memattr_lo=0x888d8f88, memattr_hi=0x00084c8d,
            **self.ZERO_PATH), 0x2380)
        csf = result['csf']
        self.assertEqual(csf['vendor_memattr_pair'], 'vendor-memattr')
        self.assertEqual(csf['vendor_memattr_outcome'], 'ready')
        self.assertTrue(result['csf_firmware_boot_verified'])

    def test_2380_rejects_the_legacy_pair(self):
        result = self.module.decode(self.marks_dvfs(build=0x2380,
            memattr_lo=0x4c4c884c, memattr_hi=0x4c4c4c4c,
            **self.ZERO_PATH), 0x2380)
        csf = result['csf']
        self.assertEqual(csf['vendor_memattr_pair'], 'wrong-memattr')
        self.assertEqual(csf['vendor_memattr_outcome'], 'not-this-image')
        self.assertFalse(result['csf_firmware_boot_verified'])

    def test_2380_unchanged_signature_is_not_a_win(self):
        result = self.module.decode(self.marks_dvfs(build=0x2380,
            memattr_lo=0x888d8f88, memattr_hi=0x00084c8d,
            stage=4, error=-53, cleanup_error=-53, version=0, job_raw=0,
            firmware_ready=0, reset_completed=0), 0x2380)
        csf = result['csf']
        self.assertEqual(csf['vendor_memattr_outcome'], 'unchanged')
        self.assertFalse(result['csf_firmware_boot_verified'])

    def test_2380_fault_demands_a_revert(self):
        result = self.module.decode(self.marks_dvfs(build=0x2380,
            memattr_lo=0x888d8f88, memattr_hi=0x00084c8d,
            stage=4, error=-54, mmu_raw=1, firmware_ready=0), 0x2380)
        csf = result['csf']
        self.assertEqual(csf['vendor_memattr_outcome'], 'fault')
        self.assertFalse(result['csf_firmware_boot_verified'])

    def relocated_report(self, **changes):
        """2382: 2379's probe on a plan that moved the code section's PA."""
        values = dict(stage=4, error=-53, version=0, features=0, job_raw=0,
                      firmware_ready=0, input_va=0x01000200, groups=9,
                      platform_reserved=0x202, transtab_lo=0x40077000,
                      firmware_probe_pa_lo=0x401a4000, firmware_probe_pa_hi=0)
        values.update(changes)
        return self.module.decode(self.marks_dvfs(build=0x2382, **values), 0x2382)

    def test_2382_counter_reads_the_same_way_after_the_move(self):
        result = self.relocated_report()
        csf = result['csf']
        self.assertTrue(csf['relocation_observed'])
        self.assertEqual(csf['relocated_code_pa'], 0x401a4000)
        self.assertEqual(csf['fetch_prime_counter'], 9)
        self.assertEqual(csf['fetch_prime_outcome'], 'fetch-call-incomplete')
        self.assertFalse(result['csf_firmware_boot_verified'])
        self.assertEqual(self.relocated_report(groups=10)['csf']['fetch_prime_outcome'],
                         'data-read-incomplete')
        self.assertEqual(self.relocated_report(groups=11)['csf']['fetch_prime_outcome'],
                         'data-read-returned')

    def test_2382_rejects_a_report_from_an_unmoved_image(self):
        csf = self.relocated_report(firmware_probe_pa_lo=0x40080000)['csf']
        self.assertFalse(csf['relocation_observed'])
        self.assertEqual(csf['fetch_prime_outcome'], 'not-relocated')

    def test_2382_fault_and_unexpected_states_beat_the_counter(self):
        self.assertEqual(self.relocated_report(error=-54, as_fault=1)['csf']['fetch_prime_outcome'],
                         'fault')
        self.assertEqual(self.relocated_report(groups=11, firmware_ready=1)['csf']['fetch_prime_outcome'],
                         'unexpected-state')
        self.assertEqual(self.relocated_report(input_va=0)['csf']['fetch_prime_outcome'],
                         'marker-absent')
        self.assertEqual(self.relocated_report(groups=7)['csf']['fetch_prime_outcome'],
                         'unexpected-counter')

    def test_2382_is_not_adjudicated_with_the_2380_rules(self):
        # 2382 deliberately keeps 2379's leaf/register pair; the decoder must
        # not demand the vendor table from it or the verdict becomes noise.
        csf = self.relocated_report()['csf']
        self.assertEqual((csf['memattr_lo'], csf['memattr_hi']), (0x4c4c884c, 0x4c4c4c4c))
        self.assertNotIn('vendor_memattr_outcome', csf)
        self.assertNotIn('fetch_prime_outcome', self.module.decode(self.marks_dvfs(build=0x2380,
            memattr_lo=0x888d8f88, memattr_hi=0x00084c8d, **self.ZERO_PATH), 0x2380)['csf'])

    def fault_report(self, **changes):
        """2383: 2382's mapping plus the vendor fault entry."""
        values = dict(stage=4, error=-53, version=0, features=0, job_raw=0,
                      firmware_ready=0, input_va=0x01000200, groups=20,
                      output_va=0x01000200, group_stride=1, platform_reserved=0x202,
                      transtab_lo=0x40077000, firmware_probe_pa_lo=0x401a4000,
                      firmware_probe_pa_hi=0)
        values.update(changes)
        return self.module.decode(self.marks_dvfs(build=0x2383, **values), 0x2383)

    def test_2383_fault_value_is_separated_from_the_probe_values(self):
        result = self.fault_report()
        csf = result['csf']
        self.assertTrue(csf['fault_taken'])
        self.assertEqual(csf['fetch_prime_outcome'], 'fault-taken')
        self.assertEqual(csf['fault_stacked_pc'], 0x01000200)
        self.assertEqual(csf['fault_status_cfsr'], 1)
        self.assertEqual(csf['fault_status_names'], ['IACCVIOL'])
        self.assertIn('IACCVIOL', csf['instrument_verdict'])
        self.assertFalse(result['csf_firmware_boot_verified'])

    def test_2383_clear_cfsr_is_reported_as_escalation(self):
        csf = self.fault_report(group_stride=0)['csf']
        self.assertTrue(csf['fault_taken'])
        self.assertEqual(csf['fault_status_names'], [])
        self.assertIn('escalated hard fault', csf['instrument_verdict'])

    def test_2383_nine_now_means_no_fault_was_taken(self):
        csf = self.fault_report(groups=9)['csf']
        self.assertFalse(csf['fault_taken'])
        self.assertEqual(csf['fetch_prime_outcome'], 'no-fault-fetch-incomplete')
        self.assertNotIn('fault_stacked_pc', csf)
        self.assertIn('never completes', csf['instrument_verdict'])
        # 2384 showed the counter alone cannot exclude a refusal; the note keeps
        # that dependency visible in 2383's own record.
        self.assertIn('as_fault and mmu_raw reading 0', csf['fault_instrument_note'])

    def test_2383_state_and_provenance_gate_the_counter(self):
        self.assertEqual(self.fault_report(firmware_probe_pa_lo=0x40080000)['csf']['fetch_prime_outcome'],
                         'not-relocated')
        self.assertEqual(self.fault_report(as_fault=1)['csf']['fetch_prime_outcome'],
                         'gpu-fault')
        self.assertEqual(self.fault_report(firmware_ready=1)['csf']['fetch_prime_outcome'],
                         'unexpected-state')
        self.assertEqual(self.fault_report(input_va=0)['csf']['fetch_prime_outcome'],
                         'marker-absent')
        self.assertEqual(self.fault_report(groups=7)['csf']['fetch_prime_outcome'],
                         'unexpected-counter')

    def control_report(self, **changes):
        """2384: the positive control for the 2383 fault entry."""
        values = dict(stage=4, error=-53, version=0, features=0, job_raw=0,
                      firmware_ready=0, input_va=0x01000200, groups=20,
                      output_va=0x0100190a, group_stride=0x00008202,
                      platform_reserved=0x202, transtab_lo=0x40077000,
                      firmware_probe_pa_lo=0x401a4000, firmware_probe_pa_hi=0)
        values.update(changes)
        return self.module.decode(self.marks_dvfs(build=0x2384, **values), 0x2384)

    def test_2384_proves_the_fault_entry_fires(self):
        csf = self.control_report()['csf']
        self.assertEqual(csf['positive_control_outcome'], 'instrument-proven')
        self.assertEqual(csf['control_counter'], 20)
        self.assertEqual(csf['fault_status_cfsr'], 0x00008202)
        self.assertEqual(csf['fault_status_names'], ['DACCVIOL', 'PRECISERR', 'BFARVALID'])
        self.assertEqual(csf['fault_stacked_pc'], 0x0100190a)
        self.assertIn('fault entry works', csf['instrument_verdict'])

    def test_2384_distinguishes_the_three_outcomes(self):
        self.assertEqual(self.control_report(groups=30)['csf']['positive_control_outcome'],
                         'unmapped-read-completed')
        self.assertEqual(self.control_report(groups=8)['csf']['positive_control_outcome'],
                         'unmapped-read-stalled')
        self.assertEqual(self.control_report(groups=0)['csf']['positive_control_outcome'],
                         'unmapped-read-stalled')
        self.assertEqual(self.control_report(groups=7)['csf']['positive_control_outcome'],
                         'unexpected-counter')

    def test_2384_refusal_is_visible_to_the_mmu_not_to_the_mcu(self):
        # The 2026-11-06 21:14 trial, field for field: counter 8 with the marker
        # set, error -54, mmu_raw 1, AS_FAULT 0x7cd90382 at 0x03000000. The MMU
        # answered the read; the entry program still never advanced, so the
        # refusal reached the core as a hang.
        csf = self.control_report(groups=8, error=-54, mmu_raw=1, as_fault=0x7cd90382,
                                  as_fault_lo=0x03000000, as_fault_hi=0)['csf']
        self.assertEqual(csf['positive_control_outcome'], 'refusal-not-signalled')
        self.assertEqual(csf['control_fault_va'], 0x03000000)
        self.assertEqual(csf['control_fault_status'], 0x7cd90382)
        self.assertIn('hang rather than as an exception', csf['instrument_verdict'])
        # A fault with a completed or failed-in-another-way counter stays where
        # it was: the MMU words never overwrite a 20 or a 30.
        self.assertEqual(self.control_report(groups=20, error=-54, mmu_raw=1,
                                            as_fault=1)['csf']['positive_control_outcome'],
                         'instrument-proven')
        # No MMU evidence and counter 8 is still a plain stall.
        self.assertEqual(self.control_report(groups=8, mmu_raw=0, as_fault=0)['csf']
                         ['positive_control_outcome'], 'unmapped-read-stalled')

    def test_2384_requires_the_marker_and_the_2383_mapping(self):
        self.assertEqual(self.control_report(input_va=0)['csf']['positive_control_outcome'],
                         'control-never-ran')
        self.assertEqual(self.control_report(firmware_probe_pa_lo=0x40080000)['csf']['positive_control_outcome'],
                         'not-relocated')

    def cold_report(self, build=0x2385, **changes):
        """2385/2386: the reset vector points at one chosen block."""
        values = dict(stage=4, error=-53, version=0, features=0, job_raw=0,
                      firmware_ready=0, input_va=0x0100E000, groups=8,
                      output_va=0x04002000, group_stride=0x000000a0,
                      platform_reserved=0x202, transtab_lo=0x40077000,
                      firmware_probe_pa_lo=0x401a4000, firmware_probe_pa_hi=0)
        values.update(changes)
        return self.module.decode(self.marks_dvfs(build=build, **values), build)

    def test_2385_one_word_answers_the_cold_fetch_question(self):
        csf = self.cold_report()['csf']
        self.assertEqual(csf['cold_boot_outcome'], 'cold-boot-fetch-completes')
        self.assertTrue(csf['cold_boot_marker_present'])
        self.assertEqual(csf['cold_boot_target'], 0x0100E000)
        self.assertIn('cold fetch does complete', csf['instrument_verdict'])
        # the marker absent and no fault: the first fetch stalls like the rest
        csf = self.cold_report(input_va=0x04002000)['csf']
        self.assertEqual(csf['cold_boot_outcome'], 'cold-boot-fetch-stalls')
        self.assertIn('already resident', csf['instrument_verdict'])
        # a refusal would mean the build, not the question, is wrong
        self.assertEqual(self.cold_report(mmu_raw=1, error=-54, as_fault=0x7cd002c2)
                         ['csf']['cold_boot_outcome'], 'cold-boot-refused')
        self.assertEqual(self.cold_report(firmware_probe_pa_lo=0x40080000)
                         ['csf']['cold_boot_outcome'], 'not-relocated')

    def test_2386_asks_the_same_question_of_the_block_that_always_hangs(self):
        csf = self.cold_report(build=0x2386, input_va=0x01000200)['csf']
        self.assertEqual(csf['cold_boot_outcome'], 'cold-boot-fetch-completes')
        self.assertEqual(csf['cold_boot_target'], 0x01000200)
        self.assertTrue(csf['cold_boot_marker_present'])
        self.assertIn('never special', csf['instrument_verdict'])
        # the 2385 marker in a 2386 capture is not this block's marker
        csf = self.cold_report(build=0x2386, input_va=0x0100E000)['csf']
        self.assertEqual(csf['cold_boot_outcome'], 'cold-boot-fetch-stalls')
        self.assertIn('differs from the one that worked', csf['instrument_verdict'])
        self.assertEqual(self.cold_report(build=0x2386, input_va=0x01000200, mmu_raw=1,
                                          error=-54)['csf']['cold_boot_outcome'],
                         'cold-boot-refused')

    def test_csf_timeout_provenance_requires_matching_callback_evidence(self):
        platform = dict(stage=8, error=-53)
        result = self.module.decode(self.csf_marks(build=0x2330, platform=platform,
            stage=4, error=-53, cleanup_error=-53, version=0, job_raw=0,
            firmware_ready=0, reset_completed=0), 0x2330)
        self.assertEqual((result['error_name'], result['error_domain'], result['error_source']),
                         ('csf-timeout', 'sweet-csf', 'powered-probe'))
        self.assertFalse(result['csf_firmware_boot_verified'])
        for changes in ({'stage':0}, {'error':-54}):
            args = dict(stage=4, error=-53); args.update(changes)
            r = self.module.decode(self.csf_marks(platform=platform, **args), 0x2322)
            self.assertEqual(r['error_domain'], 'unknown')
        for changes in ({'reset':0}, {'stage':7}, {'init':-1}, {'on':0}):
            p = dict(platform); p.update(changes)
            r = self.module.decode(self.csf_marks(platform=p, stage=4, error=-53), 0x2322)
            self.assertNotEqual(r['error_domain'], 'sweet-csf')
        r = self.module.decode(self.marks(stage=8, error=-53))
        self.assertEqual(r['error_name'], 'unclassified-error')

    def test_gpueb_reply_and_transport_namespaces_do_not_collide(self):
        for stage, key, source in ((5, 'init', 'init'), (6, 'on', 'power-on'),
                                   (9, 'off', 'power-off')):
            for error in (-53, -23):
                with self.subTest(stage=stage, error=error):
                    r = self.module.decode(self.marks(stage=stage, error=error, **{key:error}))
                    self.assertEqual(r['error_domain'], 'gpueb-firmware')
                    self.assertEqual(r['error_source'], source + '-reply')
            r = self.module.decode(self.marks(stage=stage, error=-23))
            self.assertEqual(r['error_domain'], 'sweet-gpueb')
            self.assertEqual(r['error_source'], source + '-transport')
        r = self.module.decode(self.marks(stage=8, error=-23, reset=0))
        self.assertEqual(r['error_domain'], 'sweet-gpu')
        self.assertEqual(r['error_source'], 'soft-reset')

    def test_2331_platform_snapshots_require_complete_fresh_records(self):
        r=self.module.decode(self.csf_marks(build=0x2331),0x2331)
        self.assertTrue(r['csf_firmware_boot_verified'])
        self.assertEqual(r['csf']['platform_before']['mfg_pll_con1'],12)
        self.assertEqual(r['csf']['platform_after']['mfg_pll_con1'],28)
        for field in ('version','job_raw'):
            r=self.module.decode(self.csf_marks(build=0x2331,**{field:0}),0x2331)
            self.assertFalse(r['csf_firmware_boot_verified'])
        for flags in (0,1):
            r=self.module.decode(self.csf_marks(build=0x2331,platform_sample_flags=flags),0x2331)
            self.assertFalse(r['csf_firmware_boot_verified'])
        for changes in ({'platform_sample_flags':2},{'platform_sample_flags':4},
                        {'platform_reserved':1},{'omit':54},{'tag':0x2330}):
            with self.subTest(changes=changes),self.assertRaises(ValueError):
                self.module.decode(self.csf_marks(build=0x2331,**changes),0x2331)
        with self.assertRaises(ValueError):self.module.decode(self.csf_marks(build=0x2330),0x2331)

    def test_2332_access_snapshot_preserves_fault_registers_and_readback_limits(self):
        r=self.module.decode(self.csf_marks(build=0x2332),0x2332)
        self.assertTrue(r['csf_firmware_boot_verified'])
        self.assertTrue(r['csf']['access_snapshot_complete'])
        self.assertTrue(r['csf']['firmware_cpu_readback_matches'])
        self.assertEqual(r['csf']['firmware_probe_pa'],0x90006000)
        self.assertEqual(r['csf']['access_after']['l2_ready_lo'],1)
        for changes in ({'word_before':0},{'word_after':0},{'access_sample_flags':0},
                        {'access_sample_flags':1},{'version':0},{'job_raw':0},
                        {'cleanup_error':-53},{'access_after_mmu_raw':1},
                        {'access_after_as_fault':0xc0},{'access_after_as_status':1},
                        {'access_after_l2_ready_lo':0},{'access_after_l2_transition_lo':1},
                        {'access_after_job_raw':0},{'access_after_version':0}):
            with self.subTest(changes=changes):
                r=self.module.decode(self.csf_marks(build=0x2332,**changes),0x2332)
                self.assertFalse(r['csf_firmware_boot_verified'])
        for changes in ({'access_sample_flags':2},{'access_sample_flags':4},
                        {'access_reserved':1},{'firmware_probe_va':0x04000000},
                        {'firmware_probe_pa_lo':0x90000000},{'firmware_probe_pa_lo':0x90300000},
                        {'firmware_probe_pa_lo':0x90006001},{'omit':69},{'tag':0x2331}):
            with self.subTest(changes=changes),self.assertRaises(ValueError):
                self.module.decode(self.csf_marks(build=0x2332,**changes),0x2332)
        with self.assertRaises(ValueError):
            self.module.decode(self.csf_marks(build=0x2331),0x2332)

    def test_2333_exact_platform_masks_and_paired_path_evidence(self):
        r=self.module.decode(self.csf_marks(build=0x2333),0x2333)
        self.assertTrue(r['csf_firmware_boot_verified'])
        self.assertTrue(r['csf']['platform_path_released'])
        self.assertEqual(r['csf']['path_before']['rpc_status'],0xfff0fff0)
        for name,mask in self.module.CSF_PATH_MASKS.items():
            for suffix in ('enable','status'):
                for prefix in ('before','after'):
                    key='path_'+prefix+'_'+name+'_'+suffix
                    for bit in range(32):
                        if not mask & (1<<bit):continue
                        with self.subTest(key=key,bit=bit):
                            r=self.module.decode(self.csf_marks(build=0x2333,**{key:1<<bit}),0x2333)
                            self.assertFalse(r['csf_firmware_boot_verified'])
                            self.assertFalse(r['csf']['platform_path_released'])
        for changes in ({'path_sample_flags':2},{'path_sample_flags':4},
                        {'path_reserved':1},{'omit':86},{'tag':0x2332},
                        {'path_sample_flags':0}, {'path_sample_flags':1},
                        {'access_sample_flags':1}):
            with self.subTest(changes=changes),self.assertRaises(ValueError):
                self.module.decode(self.csf_marks(build=0x2333,**changes),0x2333)
        # Empty/one-sided failed paths are legitimate, never ready.
        for flags in (0,1):
            changes={'path_sample_flags':flags}
            for prefix in ('before','after'):
                if flags & (1 if prefix=='before' else 2):continue
                for key in self.module.CSF_PATH_KEYS:changes['path_'+prefix+'_'+key]=0
            r=self.module.decode(self.csf_marks(build=0x2333,**changes),0x2333)
            self.assertFalse(r['csf_firmware_boot_verified'])
        with self.assertRaises(ValueError):
            self.module.decode(self.csf_marks(build=0x2332),0x2333)

    def test_csf_ready_requires_fresh_complete_matching_evidence(self):
        result=self.module.decode(self.csf_marks(),0x2322)
        self.assertTrue(result['csf_firmware_boot_verified'])
        self.assertTrue(result['csf']['cleanup_verified'])
        self.assertTrue(self.module.decode(self.csf_marks(mmu_raw=0x10000),0x2322)['csf_firmware_boot_verified'])
        for args in ({'omit':3},{'tag':0x2321}):
            with self.assertRaises(ValueError):self.module.decode(self.csf_marks(**args),0x2322)
        with self.assertRaises(ValueError):self.module.decode(self.csf_marks())

    def test_csf_preloaded_version_fault_and_cleanup_are_not_success(self):
        for args in ({'job_raw':0},{'mmu_raw':1},{'mcu_status':3},{'version':0},
                     {'firmware_ready':0},{'input_va':0},{'output_va':0x4094000},
                     {'groups':0},{'group_stride':31},{'groups':31,'group_stride':0x4c00},{'error':-53},
                     {'cleanup_error':-53},{'reset_completed':0},{'reset_raw':0}):
            with self.subTest(args=args):
                result=self.module.decode(self.csf_marks(**args),0x2322)
                self.assertFalse(result['csf_firmware_boot_verified'])
        result=self.module.decode(self.csf_marks(stage=6,error=-53,cleanup_error=-53,reset_completed=0),0x2322)
        self.assertTrue(result['csf']['firmware_ready_observed'])
        self.assertFalse(result['csf']['cleanup_verified'])

    def test_2323_diagnostics_and_failed_disable_are_independent(self):
        result=self.module.decode(self.csf_marks(build=0x2323),0x2323)
        self.assertTrue(result['csf_firmware_boot_verified'])
        self.assertTrue(result['csf']['runtime_interface_sampled'])
        for args in ({'sample_flags':0},{'gpu_raw':1},{'as_status':1},
                     {'transcfg_lo':0x010005c6},{'transtab_lo':0x90000001},
                     {'disable_status':1},{'disable_error':-53}):
            with self.subTest(args=args):
                self.assertFalse(self.module.decode(self.csf_marks(build=0x2323,**args),0x2323)['csf_firmware_boot_verified'])
        result=self.module.decode(self.csf_marks(build=0x2323,stage=4,error=-53,
            job_raw=0,firmware_ready=0),0x2323)
        self.assertTrue(result['csf']['runtime_interface_sampled'])
        self.assertFalse(result['csf_firmware_boot_verified'])
        self.assertFalse(self.module.decode(self.csf_marks(stage=4,error=-53),0x2322)['csf']['runtime_interface_sampled'])
        for args in ({'omit':15},{'tag':0x2322},{'reserved':1},{'sample_flags':4}):
            with self.assertRaises(ValueError):self.module.decode(self.csf_marks(build=0x2323,**args),0x2323)

    def test_2324_requires_irq_mask_readback_and_fresh_irq(self):
        result=self.module.decode(self.csf_marks(build=0x2324),0x2324)
        self.assertTrue(result['csf_firmware_boot_verified'])
        self.assertEqual(result['csf']['job_irq_mask'],0xffffffff)
        self.assertNotIn('reserved',result['csf'])
        for args in ({'reserved':0},{'reserved':0x80000000},{'job_raw':0},
                     {'version':0},{'cleanup_error':-53}):
            with self.subTest(args=args):
                self.assertFalse(self.module.decode(self.csf_marks(build=0x2324,**args),0x2324)['csf_firmware_boot_verified'])
        for args in ({'omit':15},{'tag':0x2323},{'sample_flags':4}):
            with self.assertRaises(ValueError):self.module.decode(self.csf_marks(build=0x2324,**args),0x2324)
        with self.assertRaises(ValueError):self.module.decode(self.csf_marks(build=0x2324),0x2323)

    def test_2325_supported_masks_and_core_state_evidence(self):
        result=self.module.decode(self.csf_marks(build=0x2325),0x2325)
        self.assertTrue(result['csf_firmware_boot_verified'])
        self.assertEqual(result['csf']['mmu_irq_mask'],0xff)
        self.assertTrue(result['csf']['core_state_after_start'])
        clamped=self.module.decode(self.csf_marks(build=0x2325,
            gpu_irq_mask=0x103,reserved=0x80000000),0x2325)
        self.assertTrue(clamped['csf_firmware_boot_verified'])
        for args in ({'gpu_irq_mask':0x80502},{'mmu_irq_mask':0xfe},
                     {'as_present':0xffff},{'irq_gate_passed':0},{'reserved':0x7fffffff},
                     {'sample_flags':7},{'sample_flags':5},{'job_raw':0},{'version':0},
                     {'cleanup_error':-53}):
            with self.subTest(args=args):
                self.assertFalse(self.module.decode(self.csf_marks(build=0x2325,**args),0x2325)['csf_firmware_boot_verified'])
        rejected=self.module.decode(self.csf_marks(build=0x2325,stage=3,error=-52,
            irq_gate_passed=0,sample_flags=5,mmu_irq_mask=0xfe),0x2325)
        self.assertFalse(rejected['csf']['core_state_after_start'])
        self.assertTrue(rejected['csf']['core_state_sampled'])
        for args in ({'omit':23},{'tag':0x2324},{'sample_flags':16},{'irq_gate_passed':2}):
            with self.assertRaises(ValueError):self.module.decode(self.csf_marks(build=0x2325,**args),0x2325)
        with self.assertRaises(ValueError):self.module.decode(self.csf_marks(build=0x2325),0x2324)

    def test_initial_reset_observation_survives_later_callback_failure(self):
        result=self.module.decode(self.marks(error=-53))
        self.assertTrue(result['initial_power_reset_observed'])
        self.assertFalse(result['power_reset_verified'])
        self.assertFalse(self.module.decode(self.marks(reset=0))['initial_power_reset_observed'])

    def test_2326_startup_mutations_are_not_readiness(self):
        result=self.module.decode(self.csf_marks(build=0x2326),0x2326)
        self.assertTrue(result['csf_firmware_boot_verified'])
        self.assertTrue(result['csf']['private_memory_sampled'])
        self.assertTrue(all(result['csf']['startup_memory_changed'].values()))
        for args in ({'job_raw':0},{'version':0},{'diag_flags':7},{'memattr_lo':0},
                     {'private_page_lo':0},{'cleanup_error':-53}):
            with self.subTest(args=args):
                self.assertFalse(self.module.decode(self.csf_marks(build=0x2326,**args),0x2326)['csf_firmware_boot_verified'])
        stalled=self.module.decode(self.csf_marks(build=0x2326,stage=4,error=-53,
            version=0,job_raw=0,firmware_ready=0),0x2326)
        self.assertTrue(stalled['csf']['startup_memory_changed']['private_early'])
        self.assertFalse(stalled['csf_firmware_boot_verified'])
        unsampled=self.module.decode(self.csf_marks(build=0x2326,diag_flags=7,
            stage=3,error=-52,sample_flags=5,irq_gate_passed=0),0x2326)
        self.assertFalse(unsampled['csf']['startup_memory_sampled'])
        self.assertEqual(unsampled['csf']['startup_memory_changed'],{})
        for args in ({'omit':35},{'tag':0x2325},{'diag_flags':32},{'private_page_lo':1}):
            with self.assertRaises(ValueError):self.module.decode(self.csf_marks(build=0x2326,**args),0x2326)
        with self.assertRaises(ValueError):self.module.decode(self.csf_marks(build=0x2326),0x2325)

    def test_2327_protocol_readback_is_not_firmware_readiness(self):
        result=self.module.decode(self.csf_marks(build=0x2327),0x2327)
        self.assertTrue(result['csf']['noncoherent_protocol_verified'])
        self.assertTrue(result['csf_firmware_boot_verified'])
        for args in ({'coherency_requested':0},{'coherency_readback':0},
                     {'coherency_after':0},{'diag_flags':31},{'job_raw':0},
                     {'version':0},{'cleanup_error':-53}):
            with self.subTest(args=args):
                self.assertFalse(self.module.decode(self.csf_marks(build=0x2327,**args),0x2327)['csf_firmware_boot_verified'])
        stalled=self.module.decode(self.csf_marks(build=0x2327,stage=4,error=-53,
            version=0,job_raw=0,firmware_ready=0),0x2327)
        self.assertTrue(stalled['csf']['noncoherent_protocol_verified'])
        self.assertFalse(stalled['csf_firmware_boot_verified'])
        rejected=self.module.decode(self.csf_marks(build=0x2327,stage=1,error=-52,
            diag_flags=33,coherency_readback=0,sample_flags=0),0x2327)
        self.assertFalse(rejected['csf']['noncoherent_protocol_verified'])
        for args in ({'omit':36},{'tag':0x2326},{'diag_flags':128},{'diag_flags':65}):
            with self.assertRaises(ValueError):self.module.decode(self.csf_marks(build=0x2327,**args),0x2327)
        with self.assertRaises(ValueError):self.module.decode(self.csf_marks(build=0x2327),0x2326)

    def test_2328_mapping_metadata_is_not_hardware_readiness(self):
        result=self.module.decode(self.csf_marks(build=0x2328),0x2328)
        self.assertTrue(result['csf']['pte_group_configuration_matches'])
        self.assertTrue(result['csf_firmware_boot_verified'])
        for args in ({'pte_group_requested':0},{'pte_pages_built':292},
                     {'coherency_after':0},{'version':0},{'job_raw':0},
                     {'cleanup_error':-53},{'reset_completed':0}):
            with self.subTest(args=args):
                self.assertFalse(self.module.decode(self.csf_marks(build=0x2328,**args),0x2328)['csf_firmware_boot_verified'])
        stalled=self.module.decode(self.csf_marks(build=0x2328,stage=4,error=-53,
            version=0,job_raw=0,firmware_ready=0),0x2328)
        self.assertTrue(stalled['csf']['pte_group_configuration_matches'])
        self.assertFalse(stalled['csf_firmware_boot_verified'])
        for args in ({'omit':37},{'tag':0x2327},{'pte_group_requested':16},{'pte_pages_built':4097}):
            with self.assertRaises(ValueError):self.module.decode(self.csf_marks(build=0x2328,**args),0x2328)
        with self.assertRaises(ValueError):self.module.decode(self.csf_marks(build=0x2328),0x2327)

    def test_2329_vendor_ina_readback_does_not_replace_fresh_firmware_evidence(self):
        result=self.module.decode(self.csf_marks(build=0x2329),0x2329)
        self.assertTrue(result['csf']['vendor_ina_readback_matches'])
        self.assertTrue(result['csf_firmware_boot_verified'])
        for args in ({'transcfg_lo':0x420001c6},{'transcfg_lo':6},
                     {'version':0},{'job_raw':0},{'pte_group_requested':0},
                     {'memattr_lo':0x888d8f88},{'cleanup_error':-53},{'reset_completed':0}):
            with self.subTest(args=args):
                self.assertFalse(self.module.decode(self.csf_marks(build=0x2329,**args),0x2329)['csf_firmware_boot_verified'])
        stalled=self.module.decode(self.csf_marks(build=0x2329,stage=4,error=-53,
            version=0,job_raw=0,firmware_ready=0),0x2329)
        self.assertTrue(stalled['csf']['vendor_ina_readback_matches'])
        self.assertFalse(stalled['csf_firmware_boot_verified'])
        for args in ({'omit':37},{'tag':0x2328}):
            with self.assertRaises(ValueError):self.module.decode(self.csf_marks(build=0x2329,**args),0x2329)
        with self.assertRaises(ValueError):self.module.decode(self.csf_marks(build=0x2328),0x2329)
        with self.assertRaises(ValueError):self.module.decode(self.csf_marks(build=0x2329),0x2328)

    def test_2334_marker_is_separate_from_firmware_readiness(self):
        changes=dict(build=0x2334, stage=4, error=-53, firmware_ready=0,
                     version_before=0, version=0x53545542, job_raw=0)
        result=self.module.decode(self.csf_marks(**changes),0x2334)
        self.assertTrue(result['csf']['reset_store_marker_observed'])
        self.assertFalse(result['csf_firmware_boot_verified'])
        self.assertFalse(result['csf']['firmware_ready_observed'])
        for mutation in ({'version':0},{'version_before':0x53545542},
                         {'access_after_version':0},{'access_before_version':1}):
            with self.subTest(mutation=mutation):
                r=self.module.decode(self.csf_marks(**dict(changes,**mutation)),0x2334)
                self.assertFalse(r['csf']['reset_store_marker_observed'])
        with self.assertRaises(ValueError):
            self.module.decode(self.csf_marks(build=0x2333),0x2334)
        pretend_ready=self.module.decode(self.csf_marks(build=0x2334),0x2334)
        self.assertFalse(pretend_ready['csf_firmware_boot_verified'])

    def test_2335_separate_checkpoint_never_replaces_true_version(self):
        kwargs=dict(build=0x2335,version_before=0,access_reserved=0,path_reserved=0x53545542)
        r=self.module.decode(self.csf_marks(**kwargs),0x2335)
        self.assertTrue(r['csf']['entry_marker_observed'])
        self.assertTrue(r['csf_firmware_boot_verified'])
        for change in ({'version':0}, {'version':0x53545542},
                       {'job_raw':0}, {'disable_error':-53}):
            args=dict(kwargs);args.update(change)
            r=self.module.decode(self.csf_marks(**args),0x2335)
            self.assertFalse(r['csf_firmware_boot_verified'],change)
        for change in ({'access_reserved':0x53545542}, {'path_reserved':0},
                       {'path_reserved':1}):
            args=dict(kwargs);args.update(change)
            self.assertFalse(self.module.decode(self.csf_marks(**args),0x2335)['csf']['entry_marker_observed'])
        for data in (self.csf_marks(build=0x2334),self.csf_marks(omit=56,**kwargs),
                     self.csf_marks(tag=0x2334,**kwargs),
                     self.csf_marks(access_sample_flags=1,path_sample_flags=1,**kwargs)):
            with self.assertRaises(ValueError):self.module.decode(data,0x2335)

    def test_2336_inline_and_tail_progress_are_distinct_from_version(self):
        for marker,progress in ((0,'unobserved'),(0x53545542,'inline'),(0x5452414d,'trampoline'),(1,'unobserved')):
            args=dict(build=0x2336,version_before=0,access_reserved=0,path_reserved=marker)
            c=self.module.decode(self.csf_marks(**args),0x2336)['csf']
            self.assertEqual(c['entry_progress'],progress)
            self.assertEqual(c['trampoline_marker_observed'],progress=='trampoline')
            for version in (0,0x53545542,0x5452414d):
                r=self.module.decode(self.csf_marks(version=version,**args),0x2336)
                self.assertFalse(r['csf_firmware_boot_verified'])
            args['access_reserved']=marker or 1
            self.assertFalse(self.module.decode(self.csf_marks(**args),0x2336)['csf']['entry_marker_observed'])
        for data in (self.csf_marks(build=0x2335),self.csf_marks(build=0x2336,omit=56)):
            with self.assertRaises(ValueError):self.module.decode(data,0x2336)

    def test_2337_guard_build_preserves_report_abi_and_rejects_stale_tags(self):
        data=self.csf_marks(build=0x2337,version=0,version_before=0,
                            access_reserved=0,path_reserved=0)
        result=self.module.decode(data,0x2337)
        self.assertEqual(result['csf']['entry_progress'],'unobserved')
        self.assertIn('pre-AUTO',result['csf']['entry_guard_note'])
        self.assertFalse(result['csf_firmware_boot_verified'])
        with self.assertRaises(ValueError):
            self.module.decode(self.csf_marks(build=0x2336),0x2337)

    def test_2330_cached_byte_requires_fresh_firmware_and_cleanup(self):
        result=self.module.decode(self.csf_marks(build=0x2330),0x2330)
        self.assertTrue(result['csf']['vendor_cached_byte_readback_matches'])
        self.assertTrue(result['csf_firmware_boot_verified'])
        for args in ({'memattr_lo':0x4c4c9f4c},{'memattr_lo':0x888d8f88},
                     {'memattr_hi':0x84c8d},{'transcfg_lo':0x420001c6},
                     {'job_raw':0},{'version':0},{'cleanup_error':-53},
                     {'reset_completed':0},{'irq_gate_passed':0}):
            with self.subTest(args=args):
                self.assertFalse(self.module.decode(self.csf_marks(build=0x2330,**args),0x2330)['csf_firmware_boot_verified'])
        stalled=self.module.decode(self.csf_marks(build=0x2330,stage=4,error=-53,
            version=0,job_raw=0,firmware_ready=0),0x2330)
        self.assertTrue(stalled['csf']['vendor_cached_byte_readback_matches'])
        self.assertFalse(stalled['csf_firmware_boot_verified'])
        for args in ({'omit':37},{'tag':0x2329}):
            with self.assertRaises(ValueError):self.module.decode(self.csf_marks(build=0x2330,**args),0x2330)
        with self.assertRaises(ValueError):self.module.decode(self.csf_marks(build=0x2329),0x2330)
        with self.assertRaises(ValueError):self.module.decode(self.csf_marks(build=0x2330),0x2329)

if __name__ == '__main__':
    unittest.main()
