#!/usr/bin/env python3
"""Decode the independent shim GPU report from a Recovery SWEETMRK capture."""
import argparse
import json
from pathlib import Path
import struct

STAGES = {1:'config',2:'power-domain',3:'firmware',4:'memory',5:'shared-init',
          6:'power-on',7:'gpu-id',8:'soft-reset',9:'power-off',10:'complete',
          11:'gpufreq-dvfs'}
ERRORS = {0:'success',-20:'argument',-21:'handoff',-22:'overlap',-23:'timeout',
          -24:'stale-reply',-25:'invalid-reply',-26:'ownership',-27:'unpowered',
          -28:'gpu-model',-29:'frequency'}
KEYS = ['stage','error','init_result','on_result','off_result','spm_before',
        'spm_after','spm_second','firmware_magic','gpu_id','gpu_status',
        'reset_rawstat','as_present','firmware_memory','power_acquired','cleanup_attempted']
# 2338 appends 10 words (112 bytes total). These are decoded from the
# gpufreq shared-status region GPUEB was handed in CMD_INIT: they say what
# the firmware published, not what the shim commanded.
GPUFREQ_KEYS = ['valid','oppidx','power_count','opp_num','freq_khz','volt_uv',
                'vsram_uv','dvfs_state','power_ctrl','commit_result']
CSF_KEYS = ['stage','error','cleanup_error','mmu_features','l2_present','l2_present_hi',
            'l2_ready','mcu_status','job_raw','mmu_raw','as_fault','as_fault_lo',
            'as_fault_hi','version','features','input_va','output_va','groups',
            'group_stride','reset_raw','firmware_ready','reset_completed']
CSF_DIAGNOSTIC_KEYS = ['sample_flags','gpu_raw','as_status','transcfg_lo',
                       'transtab_lo','transtab_hi','disable_status','disable_error',
                       'version_before','reserved']
CSF_MASK_CORE_KEYS = ['gpu_irq_mask','mmu_irq_mask','as_present','irq_gate_passed',
    'shader_present_lo','shader_present_hi','shader_transition_lo','shader_transition_hi',
    'shader_ready_lo','shader_ready_hi','tiler_present_lo','tiler_present_hi',
    'tiler_transition_lo','tiler_transition_hi','tiler_ready_lo','tiler_ready_hi']
CSF_STARTUP_KEYS = ['diag_flags','coherency_features','coherency_before','coherency_after',
    'csf_config_before','csf_config_after','shader_config_before','shader_config_after',
    'tiler_config_before','tiler_config_after','l2_mmu_config_before','l2_mmu_config_after',
    'memattr_lo','memattr_hi','private_early_before','private_early_after',
    'private_feature_before','private_feature_after','private_late_before','private_late_after',
    'shared_alloc_before','shared_alloc_after','private_page_lo','private_page_hi']
CSF_COHERENCY_KEYS = ['coherency_requested','coherency_readback']
CSF_PLATFORM_KEYS = ['gpu_status','mcu_control','gpu_fault_status','gpu_fault_lo','gpu_fault_hi',
    'job_stat','spm_status','spm_status_second','mfg_power0','mfg_power1','mfg_power2','mfg_power3',
    'mfg_pll_con1','mfgsc_pll_con1','topckgen_sel','rpc_slp_protect']
CSF_ACCESS_KEYS = ['mmu_raw','job_raw','as_status','as_fault','as_fault_lo','as_fault_hi',
    'l2_ready_lo','l2_ready_hi','l2_transition_lo','l2_transition_hi','firmware_word0','version']
CSF_PATH_KEYS = ['rpc_enable','rpc_status','infra_enable','infra_status',
    'emi0_enable','emi0_status','emi1_enable','emi1_status','pdc_cg','pdc_st0',
    'pdc_st1','pdc_st2','pdc_st4','pdc_st5','pdc_st6','slc_group6']
CSF_PATH_MASKS = dict(rpc=0x000f0000, infra=0xf, emi0=0xc0000, emi1=0xc0000)
# Cortex-M CFSR bits the 2383 fault entry can report (SCB->CFSR, 0xE000ED28).
CFSR_BITS = ((0, 'IACCVIOL'), (1, 'DACCVIOL'), (3, 'MUNSTKERR'), (4, 'MSTKERR'),
             (5, 'MLSPERR'), (7, 'MMARVALID'), (8, 'IBUSERR'), (9, 'PRECISERR'),
             (10, 'IMPRECISERR'), (15, 'BFARVALID'),
             (11, 'UNSTKERR'), (12, 'STKERR'), (13, 'LSPERR'), (16, 'UNDEFINSTR'),
             (17, 'INVSTATE'), (18, 'INVPC'), (19, 'NOCP'), (20, 'STKOF'),
             (24, 'UNALIGNED'), (25, 'DIVBYZERO'))
CSF_STAGES = {0:'not-run',1:'config',2:'l2',3:'address-space',4:'mcu',
              5:'interface',6:'cleanup',7:'complete',8:'halt',
              9:'global-input',10:'global-ack'}
CSF_ERRORS = {0:'success',-40:'memory-argument',-41:'memory-capacity',
              -42:'memory-physical',-50:'argument',-51:'model',-52:'state',
              -53:'timeout',-54:'fault',-55:'interface'}


def error_details(fields, csf=None):
    """Resolve the return site before interpreting a numeric error namespace.

    The platform report retains stage8 when powered_probe fails. A fresh
    matching CSF report and observed initial reset distinguish that callback
    from the preceding reset wait. GPUEB negative replies have their own
    namespace even when their number collides with a local enum.
    """
    error = fields['error']
    if not error:
        return dict(error_name='success', error_domain='none', error_source='none')
    reply = {5: ('init', 'init_result'), 6: ('power-on', 'on_result'),
             9: ('power-off', 'off_result')}.get(fields['stage'])
    if reply:
        operation, key = reply
        if fields[key] < 0 and fields[key] == error:
            return dict(error_name='firmware-error', error_domain='gpueb-firmware',
                        error_source=operation + '-reply')
        if error in (-23, -24, -25):
            return dict(error_name=ERRORS[error], error_domain='sweet-gpueb',
                        error_source=operation + '-transport')
    if (csf and fields['stage'] == 8 and fields['initial_power_reset_observed'] and
            csf['stage'] != 0 and csf['error'] == error):
        return dict(error_name='csf-' + CSF_ERRORS.get(error, 'firmware-format'),
                    error_domain='sweet-csf', error_source='powered-probe')
    return dict(error_name=ERRORS.get(error, 'unclassified-error'),
                error_domain='sweet-gpu' if error in ERRORS else 'unknown',
                error_source=STAGES[fields['stage']])


def report_bytes(records, first, count, expected_build, name):
    report = {}
    for code,pad,a,b in records:
        if first <= code < first + count:
            if code in report or b != expected_build:
                raise ValueError('duplicate or mismatched ' + name + ' report record')
            report[code] = a
    if len(report) != count:
        raise ValueError('incomplete ' + name + ' report; cannot infer success')
    return b''.join(struct.pack('<Q',report[code]) for code in range(first,first+count))


def decode(data, expected_build=0x2321, mark=None, require_leaf=True):
    # `mark` is the kernel's SWEET_BUILD_ID as it appears in the capture. It is
    # normally the build under test, but a kernel built without bumping that
    # constant tags its records with the previous trial's number. Passing the
    # observed mark keeps such a capture decodable without pretending the tag
    # matches: the image sha, not the tag, is what identifies the run.
    if expected_build not in (0x2321,0x2322,0x2323,0x2324,0x2325,0x2326,0x2327,0x2328,0x2329,0x2330,0x2331,0x2332,0x2333,0x2334,0x2335,0x2336,0x2337,0x2338,0x2339,0x2340,0x2341,0x2342,0x2343,0x2344,0x2345,0x2346,0x2347,0x2348,0x2349,0x2350,0x2351,0x2352,0x2353,0x2354,0x2355,0x2356,0x2357,0x2358,0x2359,0x2360,0x2361,0x2362,0x2363,0x2364,0x2365,0x2366,0x2367,0x2368,0x2369,0x2370,0x2371,0x2372,0x2373,0x2374,0x2375,0x2376,0x2377,0x2378,0x2379,0x2380,0x2382,0x2383,0x2384,0x2385,0x2386,0x2387,0x2388,0x2389,0x2390,0x2391,0x2393,0x2394,0x2395,0x2396,0x2397):
        raise ValueError('unsupported report ABI/build')
    if len(data) != 4096:
        raise ValueError('requires exactly one 4096-byte SWEETMRK block')
    magic,version,count = struct.unpack_from('<8sII',data)
    if magic != b'SWEETMRK' or version != 1 or count > 160:
        raise ValueError('invalid marks header')
    records = [struct.unpack_from('<IIQQ',data,16+24*i) for i in range(count)]
    mark = expected_build if mark is None else mark
    builds = [a for code,pad,a,b in records if code == 99]
    if builds != [mark]:
        raise ValueError('missing/ambiguous/unexpected kernel build mark')
    raw = report_bytes(records,300,14 if expected_build >= 0x2338 else 9,mark,'GPU')
    fields = dict(zip(KEYS,struct.unpack('<I4i8I4xQ2I',raw[:72])))
    gpufreq = None
    if expected_build >= 0x2338:
        gpufreq = dict(zip(GPUFREQ_KEYS,struct.unpack('<I2i6Ii',raw[72:112])))
        if gpufreq['valid'] & ~0xf:
            raise ValueError('invalid gpufreq validity bits')
        if gpufreq['commit_result'] not in (-0x80000000,) and gpufreq['commit_result'] > 0:
            raise ValueError('invalid gpufreq commit result')
    if fields['stage'] not in STAGES:
        raise ValueError('invalid GPU report stage')
    success = (fields['stage'] == 10 and fields['error'] == 0 and
               fields['init_result'] >= 0 and
               fields['spm_before'] & fields['spm_second'] & 2 != 0 and
               fields['spm_after'] & 6 == 6 and
               fields['firmware_magic'] == 0x55667788 and
               fields['gpu_id'] >> 28 == 10 and fields['as_present'] not in (0,0xffffffff) and
               fields['on_result'] == 1 and fields['off_result'] == 0 and
               fields['reset_rawstat'] & 0x100 != 0 and
               fields['power_acquired'] == 0 and fields['cleanup_attempted'] == 1)
    result = dict(kernel_build=hex(expected_build),stage_name=STAGES[fields['stage']],
                error_name=ERRORS.get(fields['error'],'unclassified-error'),
                power_reset_verified=success,csf_firmware_boot_verified=False,**fields)
    if gpufreq is not None:
        # Observation, not readiness: valid bit0/bit1 mean the region looked
        # like a published status before/after POWER_ON, bit2 that the
        # coherent IPI answer agreed, bit3 that an issued commit took effect.
        result['gpufreq'] = gpufreq
    # Keep aggregate success strict, expose the observed earlier power/reset
    # separately when a later CSF callback fails. Never infer it from zeros.
    result['initial_power_reset_observed'] = (
        fields['init_result'] >= 0 and fields['on_result'] == 1 and
        fields['spm_before'] & fields['spm_second'] & 2 != 0 and
        fields['spm_after'] & 6 == 6 and fields['firmware_magic'] == 0x55667788 and
        fields['gpu_id'] >> 28 == 10 and fields['as_present'] not in (0,0xffffffff) and
        fields['reset_rawstat'] & 0x100 != 0)
    if expected_build >= 0x2322:
        count = 87 if expected_build >= 0x2333 else 70 if expected_build >= 0x2332 else (55 if expected_build >= 0x2331 else (38 if expected_build >= 0x2328 else (37 if expected_build == 0x2327 else (36 if expected_build == 0x2326 else (24 if expected_build == 0x2325 else (16 if expected_build >= 0x2323 else 11))))))
        raw = report_bytes(records,320,count,mark,'CSF')
        csf = dict(zip(CSF_KEYS,struct.unpack('<I2i19I',raw[:88])))
        if expected_build >= 0x2388 and (require_leaf or
                any(420 <= code < 424 for code, pad, a, b in records)):
            #2388: the four leaf descriptors the shim read back out of the arena
            # it handed the AS, in their own32-byte property and mark range
            #420..423 so no earlier ABI moved. These are the table the MCU walks,
            #not a re-derivation of what it should be. A capture that predates
            #the property (2389 shipped without it) is still decodable on request.
            csf.update(zip(('leaf_0x01000000','leaf_0x01001000',
                            'leaf_0x0100e000','leaf_0x0100f000'),
                          struct.unpack('<4Q',report_bytes(records,420,4,mark,'LEAF'))))
        if expected_build >= 0x2323:
            csf.update(zip(CSF_DIAGNOSTIC_KEYS,struct.unpack('<7Ii2I',raw[88:128])))
            allowed_flags = 15 if expected_build >= 0x2325 else 3
            if csf['sample_flags'] & ~allowed_flags or (expected_build == 0x2323 and csf['reserved']):
                raise ValueError('invalid CSF diagnostic flags/reserved word')
        if expected_build >= 0x2324:
            csf['job_irq_mask'] = csf.pop('reserved')
        if expected_build >= 0x2325:
            csf.update(zip(CSF_MASK_CORE_KEYS,struct.unpack('<16I',raw[128:192])))
            if csf['irq_gate_passed'] not in (0,1):
                raise ValueError('invalid CSF IRQ gate state')
        if expected_build >= 0x2326:
            csf.update(zip(CSF_STARTUP_KEYS,struct.unpack('<24I',raw[192:288])))
            if csf['diag_flags'] & ~(127 if expected_build >= 0x2327 else 31):
                raise ValueError('invalid CSF startup diagnostic flags')
            before,after=bool(csf['diag_flags'] & 4),bool(csf['diag_flags'] & 8)
            page=csf['private_page_hi'] << 32 | csf['private_page_lo']
            if page and (page < 0x40000000 or page & 4095):
                raise ValueError('invalid private diagnostic page')
            csf['startup_memory_sampled'] = before and after
            csf['private_memory_sampled'] = before and after and bool(page)
            csf['startup_memory_changed'] = {}
            if before and after:
                for name in ('private_early','private_feature','private_late','shared_alloc'):
                    if name == 'shared_alloc' or page:
                        csf['startup_memory_changed'][name] = csf[name+'_before'] != csf[name+'_after']
            csf['startup_memory_note'] = ('Endpoint mutations are diagnostic evidence only; '
                'unchanged words cannot exclude MCU execution. Fresh IRQ/version remain required.')
        if expected_build >= 0x2327:
            csf.update(zip(CSF_COHERENCY_KEYS,struct.unpack('<2I',raw[288:296])))
            attempted=bool(csf['diag_flags'] & 32)
            matched=bool(csf['diag_flags'] & 64)
            if matched and not attempted:
                raise ValueError('coherency readback flag without a write attempt')
            csf['noncoherent_protocol_verified'] = (attempted and matched and
                csf['coherency_requested'] == 31 and csf['coherency_readback'] == 31)
        if expected_build >= 0x2328:
            csf['pte_group_requested'],csf['pte_pages_built']=struct.unpack('<2I',raw[296:304])
            if csf['pte_group_requested'] > 15 or csf['pte_pages_built'] > 4096:
                raise ValueError('invalid CSF software mapping metadata')
            csf['pte_group_configuration_matches'] = (csf['pte_group_requested'] == 6 and
                                                       csf['pte_pages_built'] == 293)
            csf['pte_group_note'] = ('Software builder configuration only; '
                'not hardware translation or memory-routing readback.')
        if csf['stage'] not in CSF_STAGES:
            raise ValueError('invalid CSF report stage')
        if expected_build >= 0x2331:
            flags, reserved = struct.unpack_from('<2I', raw, 304)
            #2372 repurposes the2331 reserved word: bits15..8 are the value
            # written to MCU_CONTROL, bits7..0 the byte read back after it.
            # Earlier builds always wrote zero there.
            if flags & ~3 or flags == 2:
                raise ValueError('invalid CSF platform snapshot flags/reserved word')
            if expected_build < 0x2372 and reserved:
                raise ValueError('invalid CSF platform snapshot flags/reserved word')
            if expected_build >= 0x2372:
                csf['mcu_control_written'] = reserved >> 8
                csf['mcu_control_readback'] = reserved & 0xFF
                csf['mcu_control_roundtrip'] = (csf['mcu_control_written'] != 0 and
                                                csf['mcu_control_written'] == csf['mcu_control_readback'])
            csf['platform_sample_flags'] = flags
            for name, offset in (('before', 312), ('after', 376)):
                values = dict(zip(CSF_PLATFORM_KEYS, struct.unpack_from('<16I', raw, offset)))
                csf['platform_' + name] = values
            csf['platform_snapshot_complete'] = flags == 3
            csf['platform_snapshot_note'] = ('Raw register snapshots only; PLL programming words '
                'do not measure clock rate or lock, MCU enabled does not trace execution.')
        if expected_build >= 0x2332:
            flags, reserved, va, pa_lo, pa_hi, word = struct.unpack_from('<6I', raw, 440)
            if flags & ~3 or flags == 2 or (reserved and expected_build not in (0x2335,0x2336,0x2337,0x2338,0x2339,0x2340,0x2341,0x2342,0x2343,0x2344)):
                raise ValueError('invalid CSF access snapshot flags/reserved word')
            if expected_build in (0x2335,0x2336,0x2337,0x2338,0x2339,0x2340,0x2341,0x2342):
                csf['entry_marker_before'] = reserved
            pa = pa_hi << 32 | pa_lo
            root = csf['transtab_hi'] << 32 | csf['transtab_lo']
            if flags and (va != 0x01000000 or pa & 4095 or
                          not root + 4096 <= pa <= root + 0x200000 - 4096):
                raise ValueError('invalid CSF executable probe mapping metadata')
            csf.update(access_sample_flags=flags, firmware_probe_va=va,
                firmware_probe_pa=pa, firmware_probe_expected=word)
            for name, offset in (('before', 464), ('after', 512)):
                csf['access_' + name] = dict(zip(CSF_ACCESS_KEYS, struct.unpack_from('<12I', raw, offset)))
            csf['access_snapshot_complete'] = flags == 3
            csf['firmware_cpu_readback_matches'] = (flags == 3 and all(
                csf['access_' + name]['firmware_word0'] == word for name in ('before', 'after')))
            csf['access_snapshot_note'] = ('AS0 faults at +0x241c/+0x2420/+0x2424, status +0x2428; '
                'L2 ready +0x160. MMU upper16 bits are request completions; '
                'CPU executable readback does not prove MCU fetch or execution. '
                'Native shim CPU MMU/caches are off; barriers precede readback.')
        if expected_build >= 0x2333:
            flags, reserved = struct.unpack_from('<2I', raw, 560)
            if flags & ~3 or flags == 2 or (reserved and expected_build not in (0x2335,0x2336,0x2337,0x2338,0x2339,0x2340,0x2341,0x2342,0x2343,0x2344)):
                raise ValueError('invalid CSF platform path flags/reserved word')
            if expected_build in (0x2335,0x2336,0x2337,0x2338,0x2339,0x2340,0x2341,0x2342):
                csf['entry_marker_after'] = reserved
            if flags and csf['access_sample_flags'] & 1 == 0:
                raise ValueError('platform path snapshot without preceding access snapshot')
            if flags == 3 and csf['access_sample_flags'] != 3:
                raise ValueError('platform path pair without access snapshot pair')
            csf['path_sample_flags'] = flags
            for name, offset in (('before', 568), ('after', 632)):
                snapshot = dict(zip(CSF_PATH_KEYS, struct.unpack_from('<16I', raw, offset)))
                csf['path_' + name] = snapshot
                if not flags & (1 if name == 'before' else 2) and any(snapshot.values()):
                    raise ValueError('unsampled platform path contains data')
                csf['path_' + name + '_blocked'] = {
                    key: (snapshot[key + '_enable'] | snapshot[key + '_status']) & mask
                    for key, mask in CSF_PATH_MASKS.items()}
            csf['platform_path_complete'] = flags == 3
            csf['platform_path_released'] = flags == 3 and not any(
                value for name in ('before', 'after')
                for value in csf['path_' + name + '_blocked'].values())
            csf['platform_path_note'] = ('Original MT6983 scpsys MFG1 masks: RPC bits16..19, '
                'INFRA bits0..3, EMI0/1 bits18..19; enable and status are separate registers. '
                'PDC/SLC words are raw observations, not power or reachability proof.')
        end = 0x4094000  # shared VA + measured pinned firmware shared size
        ready = (csf['firmware_ready'] == 1 and csf['mcu_status'] == 1 and
                 csf['job_raw'] & 0x80000000 != 0 and csf['mmu_raw'] & 0xffff == 0 and
                 csf['version'] not in (0,0xffffffff) and
                 csf['input_va'] != csf['output_va'] and
                 all(0x4000000 <= csf[k] and csf[k] + 4096 <= end and
                     csf[k] & 3 == 0 for k in ('input_va','output_va')) and
                 # 2372+ reuse this word as a probe counter seeded8, so it
                 # runs to 8+256 for the whole-section map.
                 1 <= csf['groups'] <= (264 if expected_build >= 0x2372 else 31) and
                 csf['group_stride'] >= 32 and
                 csf['group_stride'] & 3 == 0 and
                 0x1000 + csf['groups'] * csf['group_stride'] <= 0x94000)
        cleanup = (csf['cleanup_error'] == 0 and csf['reset_completed'] == 1 and
                   csf['reset_raw'] & 0x100 != 0)
        sampled = csf['stage'] in (5,6,7)
        if expected_build >= 0x2323:
            sampled = bool(csf['sample_flags'] & 2)
            expected_flags = 15 if expected_build >= 0x2325 else 3
            ready = (ready and csf['sample_flags'] == expected_flags and csf['gpu_raw'] & 3 == 0 and
                     csf['as_status'] & 1 == 0 and
                     csf['transcfg_lo'] == (0x42000006 if expected_build >= 0x2329 else 0x420001c6) and
                     (csf['transtab_hi'] << 32 | csf['transtab_lo']) >= 0x40000000 and
                     csf['transtab_lo'] & 4095 == 0)
            cleanup = cleanup and csf['disable_error'] == 0 and csf['disable_status'] == 0
            if expected_build == 0x2324:
                ready = ready and csf['job_irq_mask'] == 0xffffffff
            if expected_build >= 0x2325:
                required_mmu = csf['as_present'] & 0xffff
                mask_gate = (csf['irq_gate_passed'] == 1 and
                    csf['as_present'] == fields['as_present'] and
                    csf['as_present'] not in (0,0xffffffff) and required_mmu & 1 != 0 and
                    csf['job_irq_mask'] & 0x80000000 != 0 and
                    csf['gpu_irq_mask'] & 0x103 == 0x103 and
                    csf['mmu_irq_mask'] & required_mmu == required_mmu)
                ready = ready and mask_gate
                csf.update(irq_gate_verified=mask_gate,
                    core_state_sampled=bool(csf['sample_flags'] & 4),
                    core_state_after_start=bool(csf['sample_flags'] & 8))
            #2380 moved MEMATTR to the exact vendor table, so the expected
            # readback pair is a property of the build, not a constant.
            if expected_build in (0x2382, 0x2383, 0x2384):
                # 2382 keeps 2379's leaf encoding and register pair on purpose:
                # the code section's PA is the only variable in that build.
                expected_memattr = (0x4c4c884c, 0x4c4c4c4c)
            elif expected_build >= 0x2380:
                expected_memattr = (0x888d8f88, 0x00084c8d)
            elif expected_build >= 0x2330:
                expected_memattr = (0x4c4c884c, 0x4c4c4c4c)
            else:
                expected_memattr = (0x4c4c9f4c, 0x4c4c4c4c)
            if expected_build >= 0x2326:
                ready = (ready and csf['diag_flags'] == (127 if expected_build >= 0x2327 else 31) and
                    (csf['memattr_lo'], csf['memattr_hi']) == expected_memattr and
                    csf['private_memory_sampled'])
            if expected_build >= 0x2327:
                ready = ready and csf['noncoherent_protocol_verified'] and csf['coherency_after'] == 31
            if expected_build >= 0x2328:
                ready = ready and csf['pte_group_configuration_matches']
            if expected_build >= 0x2329:
                csf['vendor_ina_readback_matches'] = csf['transcfg_lo'] == 0x42000006
            if expected_build >= 0x2330:
                csf['vendor_cached_byte_readback_matches'] = (
                    (csf['memattr_lo'], csf['memattr_hi']) == expected_memattr)
        csf.update(stage_name=CSF_STAGES[csf['stage']],
                   error_name=CSF_ERRORS.get(csf['error'],'firmware-format'),
                   runtime_interface_sampled=sampled,
                   firmware_ready_observed=ready,cleanup_verified=cleanup)
        result['csf'] = csf
        if expected_build >= 0x2331:
            ready = ready and csf['platform_snapshot_complete']
            csf['firmware_ready_observed'] = ready
        if expected_build >= 0x2332:
            after = csf['access_after']
            ready = (ready and csf['access_snapshot_complete'] and csf['firmware_cpu_readback_matches'] and
                after['mmu_raw'] & 0xffff == 0 and after['as_fault'] == 0 and
                after['as_status'] & 1 == 0 and after['l2_ready_lo'] & 1 != 0 and
                after['l2_transition_lo'] & 1 == 0 and after['job_raw'] & 0x80000000 != 0 and
                after['version'] == csf['version'])
            csf['firmware_ready_observed'] = ready
        if expected_build >= 0x2333:
            ready = ready and csf['platform_path_released']
            csf['firmware_ready_observed'] = ready
        if expected_build == 0x2334:
            csf['reset_store_diagnostic_only'] = True
            csf['reset_store_marker_observed'] = (
                csf['sample_flags'] & 3 == 3 and csf['access_snapshot_complete'] and
                csf['version_before'] == csf['access_before']['version'] == 0 and
                csf['version'] == csf['access_after']['version'] == 0x53545542)
            csf['reset_store_note'] = ('Pinned20-byte Thumb reset-store diagnostic. A fresh marker '
                'is separate from CSF firmware readiness; an absent marker does not localize the stall.')
            ready = False
            csf['firmware_ready_observed'] = False
        if expected_build in (0x2335,0x2336,0x2337,0x2338):
            csf['entry_marker_va'] = 0x04000ffc
            csf['entry_marker_sampled'] = csf['access_snapshot_complete']
            csf['entry_marker_observed'] = (csf['entry_marker_sampled'] and
                csf['entry_marker_before'] == 0 and csf['entry_marker_after'] == 0x53545542)
            csf['entry_marker_note'] = ('Separate shared+0xffc checkpoint sampled before AUTO and '
                'after wait,before cleanup. Global control/version remains at shared+0.')
            if expected_build in (0x2336,0x2337):
                fresh = csf['entry_marker_sampled'] and csf['entry_marker_before'] == 0
                marker = csf['entry_marker_after']
                csf['entry_marker_observed'] = fresh and marker in (0x53545542,0x5452414d)
                csf['trampoline_marker_observed'] = fresh and marker == 0x5452414d
                csf['entry_progress'] = ('trampoline' if csf['trampoline_marker_observed'] else
                    'inline' if csf['entry_marker_observed'] else 'unobserved')
                csf['entry_marker_note'] += ' Build2336/2337: inline STUB then tail overwrites same word with TRAM.'
            if expected_build == 0x2337:
                csf['entry_guard_note'] = ('A pre-AUTO CPU page-table/instruction gate runs before the CSF '
                    'boot transaction. Its console values are diagnostic only; this report does not '
                    'contain the walked leaf or prove an MCU fetch.')
            ready = ready and csf['version'] not in (0x53545542,0x5452414d)
            csf['firmware_ready_observed'] = ready
        if expected_build in (0x2339,0x2340,0x2341,0x2342):
            # The unmodified reset handler stores0xb to0x40022000 and7 to
            # 0x40022004. Build2339 repoints both literals at shared+0xffc
            # without touching an instruction, so the word records how far the
            # MCU got: 0 nothing, 0xb the first store, 0x7 both.
            marker = csf['entry_marker_after']
            csf['entry_marker_va'] = 0x04000ffc
            csf['entry_marker_sampled'] = csf['access_snapshot_complete']
            csf['mcu_store_progress'] = {0: 'none', 0xb: 'first-store', 0x7: 'both-stores'}.get(
                marker, 'other')
            csf['entry_marker_observed'] = csf['entry_marker_sampled'] and marker in (0xb, 0x7)
            csf['entry_marker_note'] = ('Original reset handler with its two MCU peripheral store '
                'literals repointed at shared+0xffc; no instruction was replaced. 0=none, '
                '0xb=first store, 0x7=both. A nonzero word proves the MCU executed the reset '
                'handler, not that the runtime interface is ready.')
        if expected_build == 0x2343:
            # All five Cortex-M fault vectors point at one handler; build2343
            # replaces 20 bytes there with mrs r0,psp / ldr r1,[r0,#0x18] /
            # str r1,[shared+0x10] / b ., so the stacked PC lands in the word
            # the report already exposes as 'groups'. The reset entry and both
            # peripheral accesses are untouched.
            pc = csf['groups']
            csf['fault_pc'] = pc
            csf['fault_handler_reached'] = 0x01000000 <= pc < 0x02000000
            csf['fault_progress'] = ('faulted' if csf['fault_handler_reached'] else
                'no-fault-recorded')
            csf['fault_probe_note'] = ('Stacked PC from the shared Cortex-M fault handler. '
                '0x0100xxxx means the MCU faulted at that instruction; anything else means the '
                'handler never ran, so it is spinning rather than trapped. Absence of a fault '
                'does not prove progress: the stub only runs on exception entry.')
        if expected_build in (0x2348,0x2349):
            # The handler now selects MSP or PSP from lr bit 2 exactly like the
            # vendor prologue, writes the stacked PC to shared+0x08 (the word
            # 2347 proved takes a write) and parks. version/features still carry
            # the two redirected stores, so this single boot separates "faulted
            # at X" from "reached the barrier" without a second run.
            pc = csf['input_va']
            csf['fault_pc'] = pc
            csf['fault_handler_reached'] = 0x01000000 <= pc < 0x02000000
            csf['fault_progress'] = ('faulted' if csf['fault_handler_reached'] else
                'no-fault-recorded')
            csf['fault_probe_note'] = ('Stacked PC from the shared Cortex-M fault handler, taken '
                'through whichever stack lr selected. 0x0100xxxx names the instruction; anything '
                'else means no fault was recorded at all. In 2349 the SCS store is redirected, so '
                'output_va=0x70000 proves it ran and input_va=0x01001914 means the barrier was '
                'reached with fault delivery live.')
        if expected_build == 0x2350:
            # No exceptions involved: the barrier is a bl to a stub that ORs
            # bit 0 into shared+0x08 and returns, so the word only changes if
            # the MCU really executed 0x01001914.
            value = csf['input_va']
            csf['branch_probe_value'] = value
            csf['barrier_reached'] = bool(value & 1)
            csf['branch_probe_note'] = ('shared+0x08 is the host placeholder 0x04002000; bit 0 '
                'set means the MCU executed the barrier at 0x01001914. A fault anywhere would '
                'land in the same stub and park on its lr guard, so a clear bit 0 also proves no '
                'exception was taken.')
        if expected_build == 0x2379:
            raw = csf['groups']
            csf['fetch_prime_counter'] = raw
            csf['fetch_prime_target'] = '0x01000200'
            csf['fetch_prime_data_address'] = '0x01000210'
            if csf['error'] == -54 or csf['mmu_raw'] & 0xffff or csf['as_fault']:
                outcome = 'fault'
                verdict = 'a fault was reported; the counter does not establish fetch priming'
            elif csf['input_va'] != 0x01000200:
                outcome = 'marker-absent'
                verdict = 'the target marker is absent; the probe did not establish entry'
            elif (csf['stage'] != 4 or csf['error'] != -53 or
                  csf['mcu_status'] != 1 or csf['firmware_ready']):
                outcome = 'unexpected-state'
                verdict = 'unexpected MCU/report state; no fetch-priming conclusion is justified'
            elif raw == 9:
                outcome = 'fetch-call-incomplete'
                verdict = ('the fresh-block call did not return; this localises the stop to '
                           'the fetch/return path, before the explicit data read')
            elif raw == 10:
                outcome = 'data-read-incomplete'
                verdict = ('the fresh-block call returned but the read at 0x01000210 did not; '
                           'executing at 0x01000200 is insufficient to make that word readable')
            elif raw == 11:
                outcome = 'data-read-returned'
                verdict = ('the fresh-block call and subsequent data read both returned; '
                           'this supports fetch priming at this target but does not establish '
                           'an exact 512-byte block size or vendor firmware readiness')
            else:
                outcome = 'unexpected-counter'
                verdict = 'the probe did not reach a defined 9/10/11 checkpoint'
            csf['fetch_prime_outcome'] = outcome
            csf['instrument_verdict'] = verdict
        if expected_build == 0x2391:
            # Three landings instrumented and one word moved: the marker names
            # which of the three rules the core actually follows.
            csf['cold_boot_counter'] = csf['groups']
            csf['relocation_observed'] = csf['firmware_probe_pa'] == 0x401a4000
            csf['cold_boot_landings'] = {
                '0x1001a00': 'the vector taken literally',
                '0x1001000': 'the vector masked to its page base',
                '0x10018ec': 'the vendor entry, if a non-aligned word is ignored'}
            landing = {0x01001A00: 'vector-literal', 0x01001000: 'page-base',
                       0x010018EC: 'vendor-entry-fallback'}.get(csf['input_va'])
            if not csf['relocation_observed']:
                outcome = 'not-relocated'
                verdict = ('the executable probe PA is not the relocated one; this is not the '
                           '2383 mapping the build reuses')
            elif csf['error'] == -54 or csf['mmu_raw'] & 0xffff or csf['as_fault']:
                outcome = 'cold-boot-refused'
                verdict = ('the MMU refused something before any marker appeared (AS_FAULT %#x at '
                           '%#x), so this run cannot say which landing the core took' %
                           (csf['as_fault'], csf['as_fault_hi'] << 32 | csf['as_fault_lo']))
            elif landing == 'vector-literal':
                outcome = 'start-vector-literal'
                csf['cold_boot_target'] = 0x01001A00
                csf['cold_boot_marker_present'] = True
                csf['cold_boot_start'] = landing
                verdict = ('the core started at 0x01001A00, the block the word names, so the '
                           'reset vector is used as written even when it is not page aligned. '
                           'The mask reading of 2388/2389 is dead for good, and 2386/2387/2388 '
                           'failed for a reason of their own: their three addresses are the only '
                           'ones that never ran, and they are the only ones that are 512-byte '
                           'aligned inside a page. Next: one of them again, with the vendor entry '
                           'also instrumented, to see whether the core went there instead')
            elif landing == 'page-base':
                outcome = 'start-masked-to-page-base'
                csf['cold_boot_target'] = 0x01001000
                csf['cold_boot_marker_present'] = True
                csf['cold_boot_start'] = landing
                verdict = ('the core reached 0x01001000 - the page base - while the word named '
                           '0x01001A00, so the low 12 bits are dropped. That is 2389 rule restored '
                           'with a witness that can tell it from the alternative, and 2390 marked '
                           '0x010018ec only because 0x18ec and 0x1000 are in the same page: the '
                           'vendor entry was never reached either, and this port has never executed '
                           'a byte the vendor wrote')
            elif landing == 'vendor-entry-fallback':
                outcome = 'start-vendor-entry-fallback'
                csf['cold_boot_target'] = 0x010018EC
                csf['cold_boot_marker_present'] = True
                csf['cold_boot_start'] = landing
                verdict = ('the word named 0x01001A00 and the core started at 0x010018ec instead, '
                           'so a reset vector that is not page aligned is ignored and the core '
                           'falls back to the vendor entry. Every earlier build that got a marker '
                           'was therefore page aligned by luck: 2385 at 0x0100E000 and 2389 at '
                           '0x01001000. Moving the vector is not a usable instrument here, and '
                           'the vendor firmware has been starting at 0x010018ec in every image, '
                           'including the ones that patched it away')
            else:
                outcome = 'cold-boot-fetch-stalls'
                csf['cold_boot_target'] = 0x01001A00
                csf['cold_boot_marker_present'] = False
                csf['cold_boot_start'] = None
                verdict = ('none of the three landings ran: not the address the word names, not '
                           'the page base, not the vendor entry. So the entry is neither the word '
                           'nor its page base nor the vendor default, and the three earlier '
                           'non-starts plus this one all point at the same unexplained rule')
            if 'leaf_0x01000000' in csf:
                csf['leaf_pa'] = {name: csf[name] & 0x0000fffffffff000 for name in
                                  ('leaf_0x01000000', 'leaf_0x01001000',
                                   'leaf_0x0100e000', 'leaf_0x0100f000')}
                csf['leaf_page0_as_planned'] = csf['leaf_pa']['leaf_0x01000000'] == 0x401a4000
            csf['cold_boot_outcome'] = outcome
            csf['instrument_verdict'] = verdict
        if expected_build == 0x2393:
            # 2391's 512-byte-aligned target repeated with vendor page
            # attributes (AttrIdx 0/5, no nG, read-only code). A literal landing
            # here says the 512 rule was an attribute artefact; no marker says it
            # survives the vendor encoding and is below the driver.
            csf['cold_boot_counter'] = csf['groups']
            csf['relocation_observed'] = csf['firmware_probe_pa'] == 0x401a4000
            csf['cold_boot_landings'] = {
                '0x100ea00': 'the vector taken literally, under vendor page attributes',
                '0x1001000': 'the vector masked to its page base',
                '0x10018ec': 'the vendor entry, if a non-aligned word is ignored'}
            landing = {0x0100EA00: 'vector-literal', 0x01001000: 'page-base',
                       0x010018EC: 'vendor-entry-fallback'}.get(csf['input_va'])
            if not csf['relocation_observed']:
                outcome = 'not-relocated'
                verdict = ('the executable probe PA is not the relocated one; this is not the '
                           '2382 mapping the build reuses')
            elif csf['error'] == -54 or csf['mmu_raw'] & 0xffff or csf['as_fault']:
                outcome = 'cold-boot-refused'
                verdict = ('the MMU refused something before any marker appeared (AS_FAULT %#x at '
                           '%#x), so this run cannot say which landing the core took' %
                           (csf['as_fault'], csf['as_fault_hi'] << 32 | csf['as_fault_lo']))
            elif landing == 'vector-literal':
                outcome = 'start-vector-literal'
                csf['cold_boot_target'] = 0x0100EA00
                csf['cold_boot_marker_present'] = True
                csf['cold_boot_start'] = landing
                verdict = ('the core started at 0x0100EA00 with AttrIdx 0/5, no nG and read-only '
                           'code. The 512-byte rule was an artefact of the shim page attributes, '
                           'not a hardware rule. Next: repeat 0x01001A00 with the same attributes '
                           'to close 2391')
            elif landing == 'page-base':
                outcome = 'start-masked-to-page-base'
                csf['cold_boot_target'] = 0x01001000
                csf['cold_boot_marker_present'] = True
                csf['cold_boot_start'] = landing
                verdict = ('the core reached 0x01001000 while the word named 0x0100EA00, so the '
                           'low 12 bits are dropped even under vendor page attributes. This is '
                           'the mask reading, not the 512-byte rule; 2390 already ruled it out')
            elif landing == 'vendor-entry-fallback':
                outcome = 'start-vendor-entry-fallback'
                csf['cold_boot_target'] = 0x010018EC
                csf['cold_boot_marker_present'] = True
                csf['cold_boot_start'] = landing
                verdict = ('the word named 0x0100EA00 and the core started at 0x010018ec: a '
                           'non-page-aligned word is ignored and the vendor entry is used, even '
                           'with vendor page attributes. 2391 had already ruled the fallback out')
            else:
                outcome = 'cold-boot-fetch-stalls'
                csf['cold_boot_target'] = 0x0100EA00
                csf['cold_boot_marker_present'] = False
                csf['cold_boot_start'] = None
                verdict = ('none of the three landings ran under vendor page attributes: the '
                           '512-byte rule survives AttrIdx 0/5, no nG and read-only code, so it '
                           'is below the driver. Next: 0x01001A00 with the same attributes')
            if 'leaf_0x01000000' in csf:
                csf['leaf_pa'] = {name: csf[name] & 0x0000fffffffff000 for name in
                                  ('leaf_0x01000000', 'leaf_0x01001000',
                                   'leaf_0x0100e000', 'leaf_0x0100f000')}
                csf['leaf_page0_as_planned'] = csf['leaf_pa']['leaf_0x01000000'] == 0x401a4000
            csf['cold_boot_outcome'] = outcome
            csf['instrument_verdict'] = verdict
        if expected_build == 0x2395:
            # 2393's container byte for byte, with the code section's leaf moved
            # to AS_MEMATTR index 5 (non-cacheable). 2393 hung at 0xEA00 with the
            # cached index and 2394 ran at 0xE000 with it, so this is the first
            # test of cacheability as the lever behind the bit-9 law.
            csf['cold_boot_counter'] = csf['groups']
            csf['relocation_observed'] = csf['firmware_probe_pa'] == 0x401a4000
            csf['cold_boot_landings'] = {
                '0x100ea00': 'the bit-9 target, with the code section non-cacheable',
                '0x1001000': 'the vector masked to its page base',
                '0x10018ec': 'the vendor entry, if a non-aligned word is ignored'}
            leaf = csf.get('leaf_0x01000000')
            code_attr = None if leaf is None else (leaf >> 2) & 7
            csf['code_leaf_attr_index'] = code_attr
            csf['code_leaf_uncached'] = code_attr == 5
            landing = {0x0100EA00: 'vector-literal', 0x01001000: 'page-base',
                       0x010018EC: 'vendor-entry-fallback'}.get(csf['input_va'])
            if not csf['relocation_observed']:
                outcome = 'not-relocated'
                verdict = ('the executable probe PA is not the relocated one; this is not the '
                           '2382 mapping the build reuses')
            elif csf['error'] == -54 or csf['mmu_raw'] & 0xffff or csf['as_fault']:
                outcome = 'cold-boot-refused'
                verdict = ('the MMU refused something before any marker appeared (AS_FAULT %#x at '
                           '%#x), so this run cannot say whether 0x0100EA00 starts' %
                           (csf['as_fault'], csf['as_fault_hi'] << 32 | csf['as_fault_lo']))
            elif code_attr is not None and code_attr != 5:
                outcome = 'encoding-not-applied'
                csf['cold_boot_target'] = 0x0100EA00
                csf['cold_boot_marker_present'] = False
                csf['cold_boot_start'] = None
                verdict = ('the live code leaf still carries AttrIndx %s, so the image did not '
                           'travel with the non-cacheable encoding and this run says nothing '
                           'about cacheability' % code_attr)
            elif landing == 'vector-literal':
                outcome = 'start-vector-literal'
                csf['cold_boot_target'] = 0x0100EA00
                csf['cold_boot_marker_present'] = True
                csf['cold_boot_start'] = landing
                verdict = ('the core started at 0x0100EA00 with the code section non-cacheable '
                           'and the same container that stalled in 2393. So cacheability is the '
                           'lever: the bit-9 stall is in the cached path, and the firmware can be '
                           'booted by mapping its code section index 5. Next: run the unpatched '
                           'container with this encoding')
            elif landing == 'page-base':
                outcome = 'start-masked-to-page-base'
                csf['cold_boot_target'] = 0x01001000
                csf['cold_boot_marker_present'] = True
                csf['cold_boot_start'] = landing
                verdict = ('the core reached 0x01001000 while the word named 0x0100EA00, so '
                           'dropping the low twelve bits reappears once the code is uncached. '
                           'That is the mask reading, not cacheability')
            elif landing == 'vendor-entry-fallback':
                outcome = 'start-vendor-entry-fallback'
                csf['cold_boot_target'] = 0x010018EC
                csf['cold_boot_marker_present'] = True
                csf['cold_boot_start'] = landing
                verdict = ('the word named 0x0100EA00 and the core started at 0x010018ec: a '
                           'non-page-aligned word is ignored once the code is uncached. That is '
                           'the fallback reading, not cacheability')
            else:
                outcome = 'cold-boot-fetch-stalls'
                csf['cold_boot_target'] = 0x0100EA00
                csf['cold_boot_marker_present'] = False
                csf['cold_boot_start'] = None
                verdict = ('non-cacheable code does not move the bit-9 target: 2393\'s stall is '
                           'below the cache path, so the next lever is the memory-group tag the '
                           'leaf carries in bits 59..62 and then the platform blocks the EB owns')
            if 'leaf_0x01000000' in csf:
                csf['leaf_pa'] = {name: csf[name] & 0x0000fffffffff000 for name in
                                  ('leaf_0x01000000', 'leaf_0x01001000',
                                   'leaf_0x0100e000', 'leaf_0x0100f000')}
                csf['leaf_page0_as_planned'] = csf['leaf_pa']['leaf_0x01000000'] == 0x401a4000
            csf['cold_boot_outcome'] = outcome
            csf['instrument_verdict'] = verdict
        if expected_build == 0x2396:
            # A ladder, not a landing: marker N is written before read N, so the
            # marker itself names the read that stopped the core.
            csf['cold_boot_counter'] = csf['groups']
            csf['relocation_observed'] = csf['firmware_probe_pa'] == 0x401a4000
            csf['cold_boot_target'] = 0x0100E000
            csf['cold_boot_ladder'] = {
                '0x1': 'stopped reading shared 0x04000200',
                '0x2': 'stopped reading stack 0x02000200',
                '0x3': 'stopped reading code 0x01001200',
                '0x4': 'all three bit-9 reads returned'}
            marker = csf['input_va']
            csf['cold_boot_marker_present'] = marker in (1, 2, 3, 4)
            if not csf['relocation_observed']:
                outcome = 'not-relocated'
                verdict = ('the executable probe PA is not the relocated one; this is not the '
                           '2382 mapping the build reuses')
            elif csf['error'] == -54 or csf['mmu_raw'] & 0xffff or csf['as_fault']:
                outcome = 'cold-boot-refused'
                verdict = ('the MMU refused something before any marker appeared (AS_FAULT %#x at '
                           '%#x), so the ladder never reached its first read' %
                           (csf['as_fault'], csf['as_fault_hi'] << 32 | csf['as_fault_lo']))
            elif marker not in (1, 2, 3, 4):
                outcome = 'no-marker'
                csf['cold_boot_start'] = None
                verdict = ('the core never wrote a marker, so 0x0100E000 did not start under the '
                           'encoding 2394 ran with. Fix that before reading the ladder')
            elif marker == 1:
                outcome = 'bit9-hangs-in-shared'
                csf['cold_boot_start'] = 'shared-0x04000200'
                verdict = ('the first bit-9 read, in the shared section, never returned. The rule '
                           'is not a property of executable pages: a bit-9 address stalls in any '
                           'section, so the wall is the address itself and no leaf field can move '
                           'it. Next: 2397, one 2 MB level-2 block for the code section, to '
                           'bypass the level-3 walk')
            elif marker == 2:
                outcome = 'bit9-hangs-in-stack'
                csf['cold_boot_start'] = 'stack-0x02000200'
                verdict = ('shared returned at bit 9 = 1 and the stack did not. The two differ in '
                           'cache mode: shared is uncached coherent, the stack is cached RW. So '
                           'bit 9 bites on cacheable data as well as on code, and the next '
                           'variable is the cache mode of the data sections, not XN')
            elif marker == 3:
                outcome = 'bit9-hangs-in-code-only'
                csf['cold_boot_start'] = 'code-0x01001200'
                verdict = ('shared and stack both returned at bit 9 = 1 and only the executable '
                           'section stalled. The rule is then bit 9 inside an R-X page, and XN is '
                           'the only leaf field never varied: the next build maps the code section '
                           'non-executable and reads the same address')
            else:
                outcome = 'bit9-not-reproduced'
                csf['cold_boot_start'] = 'all-three-returned'
                verdict = ('all three bit-9 reads returned, including the one in the code section. '
                           'Nothing in the current mapping reproduces the stall, so the earlier '
                           'no-landing results have to be re-read before another attribute is '
                           'tried')
            csf['cold_boot_outcome'] = outcome
            csf['instrument_verdict'] = verdict
        if expected_build == 0x2397:
            # 2396's container, entry and ladder, with one leaf bit moved: the
            # page holding the read target is forced non-executable. Read 3
            # returning names XN as the switch; read 3 stalling exonerates it.
            csf['cold_boot_counter'] = csf['groups']
            csf['relocation_observed'] = csf['firmware_probe_pa'] == 0x401a4000
            csf['cold_boot_target'] = 0x0100E000
            csf['cold_boot_ladder'] = {
                '0x1': 'stopped reading shared 0x04000200',
                '0x2': 'stopped reading stack 0x02000200',
                '0x3': 'stopped reading code 0x01001200, now on an XN page',
                '0x4': 'all three reads returned, the code one included'}
            page = csf.get('leaf_0x01001000')
            csf['probe_page_leaf'] = page
            csf['probe_page_xn'] = None if page is None else bool(page & (3 << 53))
            marker = csf['input_va']
            csf['cold_boot_marker_present'] = marker in (1, 2, 3, 4)
            if not csf['relocation_observed']:
                outcome = 'not-relocated'
                verdict = ('the executable probe PA is not the relocated one; this is not the '
                           '2382 mapping the build reuses')
            elif csf['error'] == -54 or csf['mmu_raw'] & 0xffff or csf['as_fault']:
                outcome = 'cold-boot-refused'
                verdict = ('the MMU refused something before any marker appeared (AS_FAULT %#x at '
                           '%#x), so the ladder never reached its first read' %
                           (csf['as_fault'], csf['as_fault_hi'] << 32 | csf['as_fault_lo']))
            elif page is not None and not csf['probe_page_xn']:
                outcome = 'xn-not-applied'
                csf['cold_boot_marker_present'] = False
                csf['cold_boot_start'] = None
                verdict = ('the live leaf for 0x01001000 carries no XN bits, so the image did not '
                           'travel with the forced page permission and this run says nothing '
                           'about executability')
            elif marker == 1:
                outcome = 'shared-stalls-again'
                csf['cold_boot_start'] = 'shared-0x04000200'
                verdict = ('the shared read stalled, which 2396 did not do. Something other than '
                           'the intended page permission moved, so this run cannot be read as an '
                           'XN result')
            elif marker == 2:
                outcome = 'stack-stalls-again'
                csf['cold_boot_start'] = 'stack-0x02000200'
                verdict = ('the stack read stalled, which 2396 did not do. The run is not '
                           'comparable to 2396 and says nothing about XN')
            elif marker == 3:
                outcome = 'xn-exonerated'
                csf['cold_boot_start'] = 'code-0x01001200'
                verdict = ('the read of 0x01001200 still stalled with its page non-executable, so '
                           'executability is not the lever either. Every leaf field has now been '
                           'varied: the remaining structural variable is the level-3 walk, and '
                           'the next build maps the code section with a 2 MB level-2 block')
            elif marker == 4:
                outcome = 'xn-is-the-switch'
                csf['cold_boot_start'] = 'all-three-returned'
                verdict = ('the code read returned once its page was forced non-executable, while '
                           'the same read stalled in 2396 on the same container. The stall is '
                           'keyed on the target page being executable, so the hardware is '
                           'treating an MCU data access to an executable page differently from '
                           'one to a non-executable page; the fix is then a page permission, not '
                           'a different boot path')
            else:
                outcome = 'no-marker'
                csf['cold_boot_start'] = None
                verdict = ('the core never wrote a marker, so 0x0100E000 did not start even though '
                           'only 0x01001000 lost X. Check the entry page leaf before reading the '
                           'ladder')
            csf['cold_boot_outcome'] = outcome
            csf['instrument_verdict'] = verdict
        if expected_build == 0x2394:
            # 2393's positive control: 2385's known-good 4 KB page base at
            # 0xE000, with the vendor page encoding. It says whether 2393's
            # failure at 0xEA00 is about the address or about the encoding.
            csf['cold_boot_counter'] = csf['groups']
            csf['relocation_observed'] = csf['firmware_probe_pa'] == 0x401a4000
            csf['cold_boot_landings'] = {
                '0x100e000': 'the positive control, under vendor page attributes'}
            if not csf['relocation_observed']:
                outcome = 'not-relocated'
                verdict = ('the executable probe PA is not the relocated one; this is not the '
                           '2382 mapping the build reuses')
            elif csf['error'] == -54 or csf['mmu_raw'] & 0xffff or csf['as_fault']:
                outcome = 'cold-boot-refused'
                verdict = ('the MMU refused something before any marker appeared (AS_FAULT %#x at '
                           '%#x), so this run cannot say whether 0x0100E000 starts' %
                           (csf['as_fault'], csf['as_fault_hi'] << 32 | csf['as_fault_lo']))
            elif csf['input_va'] == 0x0100E000:
                outcome = 'positive-control-runs'
                csf['cold_boot_target'] = 0x0100E000
                csf['cold_boot_marker_present'] = True
                csf['cold_boot_start'] = 'vector-literal'
                verdict = ('the core starts at 0x0100E000 under the vendor page encoding. 2393 '
                           'is closed: its failure at 0x0100EA00 is about the address, not the '
                           'attributes, so the 512 rule is below the driver')
            else:
                outcome = 'positive-control-stalls'
                csf['cold_boot_target'] = 0x0100E000
                csf['cold_boot_marker_present'] = False
                csf['cold_boot_start'] = None
                verdict = ('the vendor page encoding itself stops the start at a known-good 4 KB '
                           'page base. 2393 cannot be read as a 512 rule; fix the encoding before '
                           'another address test')
            if 'leaf_0x01000000' in csf:
                csf['leaf_pa'] = {name: csf[name] & 0x0000fffffffff000 for name in
                                  ('leaf_0x01000000', 'leaf_0x01001000',
                                   'leaf_0x0100e000', 'leaf_0x0100f000')}
                csf['leaf_page0_as_planned'] = csf['leaf_pa']['leaf_0x01000000'] == 0x401a4000
            csf['cold_boot_outcome'] = outcome
            csf['instrument_verdict'] = verdict
        if expected_build == 0x2390:
            # The vendor's word is left exactly as it ships, so this capture is
            # not a moved vector at all: a marker program sits at both candidate
            # landings and writes its own address, so input_va names where the
            # core started. One build, three outcomes, no new mapping.
            csf['cold_boot_counter'] = csf['groups']
            csf['relocation_observed'] = csf['firmware_probe_pa'] == 0x401a4000
            csf['cold_boot_landings'] = {'0x10018ec': 'the address the vendor word names',
                                         '0x1001000': 'the page base below it'}
            if not csf['relocation_observed']:
                outcome = 'not-relocated'
                verdict = ('the executable probe PA is not the relocated one; this is not the '
                           '2383 mapping the build reuses')
            elif csf['error'] == -54 or csf['mmu_raw'] & 0xffff or csf['as_fault']:
                outcome = 'cold-boot-refused'
                verdict = ('the MMU refused something before either marker appeared (AS_FAULT %#x '
                           'at %#x), so this run cannot answer where the core started' %
                           (csf['as_fault'], csf['as_fault_hi'] << 32 | csf['as_fault_lo']))
            elif csf['input_va'] == 0x010018EC:
                outcome = 'vendor-entry-executed'
                csf['cold_boot_target'] = 0x010018EC
                csf['cold_boot_marker_present'] = True
                csf['cold_boot_start'] = 'vendor-entry'
                verdict = ('the core started at 0x010018ec - the address the vendor word names - '
                           'and that word was never touched in this build. So the reset vector is '
                           'honoured exactly and the page-base reading of 2388/2389 is wrong: 2388 '
                           'failed for some other reason, and the vendor entry is reachable here. '
                           'The next question is why the untouched firmware still never reports '
                           'ready (version 0, firmware_ready 0) when its own entry does run')
            elif csf['input_va'] == 0x01001000:
                outcome = 'start-masked-to-page-base'
                csf['cold_boot_target'] = 0x01001000
                csf['cold_boot_marker_present'] = True
                csf['cold_boot_start'] = 'page-base'
                verdict = ('the core reached 0x01001000, not the 0x010018ec the vendor word names, '
                           'so the low 12 bits are dropped. The vendor firmware starts at a page '
                           'base too: 0x010018ec was never an entry, SWEET_CSF_RESET_ENTRY_VA and '
                           'every probe built on it (2369-2384) were aimed 0x8ec past the entry, '
                           'and the vendor handler at 0x010018ec has never run in this port. What '
                           'actually boots the vendor firmware is whatever sits at 0x01001000, '
                           'which this port has been overwriting since 2389')
            else:
                outcome = 'cold-boot-fetch-stalls'
                csf['cold_boot_target'] = 0x010018EC
                csf['cold_boot_marker_present'] = False
                csf['cold_boot_start'] = None
                verdict = ('neither landing ran and nothing faulted: the word the vendor relies on '
                           'starts nothing here at all. Either the image the device boots is not '
                           'this container - check mali_csffw_reload.bin - or the AS rejects the '
                           'entry before the first fetch. Both are offline questions, and this '
                           'retires the assumption that the vendor path ever started in this port')
            if 'leaf_0x01000000' in csf:
                csf['leaf_pa'] = {name: csf[name] & 0x0000fffffffff000 for name in
                                  ('leaf_0x01000000', 'leaf_0x01001000',
                                   'leaf_0x0100e000', 'leaf_0x0100f000')}
                csf['leaf_page0_as_planned'] = csf['leaf_pa']['leaf_0x01000000'] == 0x401a4000
            csf['cold_boot_outcome'] = outcome
            csf['instrument_verdict'] = verdict
        if expected_build in (0x2385, 0x2386, 0x2387, 0x2388, 0x2389):
            # The reset vector is the only thing between the core and a block
            # nothing has executed, so one word answers the primitive question.
            # 2385 asks it of a block nothing else uses, 2386 of the block every
            # branch and data read has failed to reach, 2387 of a third block on
            # 2386's page, and 2388 of page 1 - the page that holds the vendor's
            # own reset handler, which this port has never seen execute.
            target = {0x2385: 0x0100E000, 0x2386: 0x01000200,
                      0x2387: 0x01000600, 0x2388: 0x01001200,
                      0x2389: 0x01001000}[expected_build]
            csf['cold_boot_target'] = target
            csf['cold_boot_marker_present'] = csf['input_va'] == target
            csf['cold_boot_counter'] = csf['groups']
            csf['relocation_observed'] = csf['firmware_probe_pa'] == 0x401a4000
            if not csf['relocation_observed']:
                outcome = 'not-relocated'
                verdict = ('the executable probe PA is not the relocated one; this is not the '
                           '2383 mapping the build reuses')
            elif csf['error'] == -54 or csf['mmu_raw'] & 0xffff or csf['as_fault']:
                # A refusal here would mean the vector was read but the target
                # page is not mapped - a build fault, not an answer.
                outcome = 'cold-boot-refused'
                verdict = ('the MMU refused something before the marker appeared (AS_FAULT %#x at '
                           '%#x); the reset target is not mapped the way the plan says, so this '
                           'run cannot answer the fetch question' %
                           (csf['as_fault'], csf['as_fault_hi'] << 32 | csf['as_fault_lo']))
            elif csf['cold_boot_marker_present']:
                outcome = 'cold-boot-fetch-completes'
                if expected_build == 0x2389:
                    verdict = ('the reset fetch reached 0x01001000 - page 1 at offset zero - so page 1 '
                               'does execute and 2388 failed because its target was not page '
                               'aligned, not because of the page. That makes the start address '
                               'the discriminator: page 0 still failed as a branch target '
                               '(2379/2383), so it remains separately unreachable, and the '
                               'next question is what 0x01000000-0x01000fff has that the rest of '
                               'the section does not')
                elif expected_build == 0x2388:
                    verdict = ('the reset fetch reached 0x01001200, block 1 of page 1 - the page '
                               'that holds the vendor reset handler at 0x010018ec - so the MCU '
                               'does execute that page and page 0 is the exception. Compare '
                               'leaf_0x01000000 with leaf_0x01001000: if both carry the planned '
                               'PAs (0x401a4000 / 0x401a5000) the table is not what separates '
                               'them, and the difference is in how the AS treats that one page')
                elif expected_build == 0x2387:
                    verdict = ('the reset fetch reached 0x01000600 - block 3 of the page that '
                               'holds 0x01000200 - so page 0 is reachable and the damage is '
                               'confined to block 1. Compare that block alone: its container '
                               'bytes, its history in earlier images, and what the vendor code '
                               'at 0x01000000 does with 0x010002ec')
                elif expected_build == 0x2386:
                    verdict = ('the core fetched 0x01000200 at reset and executed it - the block '
                               'that no branch and no data read has ever reached. The block was '
                               'never special, so the wall is somewhere the plan does not show')
                else:
                    verdict = ('the core fetched 0x0100E000 - a block nothing had ever touched - '
                               'and executed it, so a cold fetch does complete when the reset '
                               'word asks for one: the memory path is not the wall')
            else:
                outcome = 'cold-boot-fetch-stalls'
                if expected_build == 0x2389:
                    verdict = ('nothing ran at 0x01001000 - page 1 at offset zero - so page 1 does '
                               'not execute at any offset and the alignment idea dies with it. '
                               'Only page 14 has ever run, on the same leaves and the same '
                               'reset path, so the discriminator is the address itself. '
                               'Scan: the same program from a page-aligned address in another '
                               'page (0x01002000, 0x01008000) maps which pages can start a '
                               'core, and that pattern is the wall')
                elif expected_build == 0x2388:
                    verdict = ('nothing ran at 0x01001200 either, so page 1 does not execute '
                               'and the only fetch this port has ever seen complete is page 14. '
                               'That makes every "firmware started" reading here shim-side only. '
                               'The leaf words are the discriminator: if leaf_0x01001000 and '
                               'leaf_0x0100e000 both carry the planned PAs and only page 0 fails '
                               'to translate differently, the wall is the page tables after all; '
                               'if all three look alike, it is not the table that stops the '
                               'fetch and the MCU-side path has to be re-examined')
                elif expected_build == 0x2387:
                    verdict = ('nothing ran at 0x01000600 and nothing faulted, so page 0 as a '
                               'whole cannot be reached by the reset fetch while page 14 can: the '
                               'damage is page-granular, not confined to block 1. The plan shows '
                               'identical leaves for the two pages, and the vendor entry veneer at '
                               '0x01000000 into 0x010002ec is dead for the same reason')
                elif expected_build == 0x2386:
                    verdict = ('the reset fetch of 0x01000200 stalls with nothing faulted, while '
                               '2385 fetched 0x0100E000 this way: this block cannot be reached by '
                               'any entry path, so the block - not the core state - is the wall')
                else:
                    verdict = ('the marker is absent and nothing faulted: the very first fetch, of '
                               'a block nothing has touched, does not complete either - the block '
                               'that works was already resident, and no cold fill ever lands')
            if 'leaf_0x01000000' in csf:
                # The leaves are the arena's own words, read back by the shim; the
                # PA is what the walk would use, everything below bit12 is flags.
                csf['leaf_pa'] = {name: csf[name] & 0x0000fffffffff000 for name in
                                  ('leaf_0x01000000', 'leaf_0x01001000',
                                   'leaf_0x0100e000', 'leaf_0x0100f000')}
                csf['leaf_page0_as_planned'] = csf['leaf_pa']['leaf_0x01000000'] == 0x401a4000
                csf['leaf_note'] = ('Read from the arena the shim handed the AS, not re-derived '
                                    'from the plan. Zero means the walk found no table. '
                                    'AttrIndx/AF/AP are the low bits of each word.')
            csf['cold_boot_outcome'] = outcome
            csf['instrument_verdict'] = verdict
        if expected_build == 0x2384:
            # Positive control for the 2383 fault entry: identical mapping and
            # fault stub, but the entry window writes the marker and then reads
            # the deliberately unmapped protected section. Only the counter can
            # differ from 2383, and each value has one meaning.
            raw = csf['groups']
            csf['control_counter'] = raw
            csf['control_marker_present'] = csf['input_va'] == 0x01000200
            csf['relocation_observed'] = csf['firmware_probe_pa'] == 0x401a4000
            # The MMU is a second, independent instrument for the same event.
            # 2375 read an unmapped address and the shim saw mmu_raw=1 and a
            # fault status; if the control's read is refused, those words move
            # even when the entry program never advances.
            refused = (csf['error'] == -54 or csf['mmu_raw'] & 0xffff or csf['as_fault'])
            if refused:
                csf['control_fault_status'] = csf['as_fault']
                csf['control_fault_va'] = csf['as_fault_hi'] << 32 | csf['as_fault_lo']
            if not csf['relocation_observed']:
                outcome = 'not-relocated'
                verdict = ('the executable probe PA is not the relocated one; this is not the '
                           '2383 mapping the control reuses')
            elif not csf['control_marker_present']:
                outcome = 'control-never-ran'
                verdict = ('the marker is absent, so the control entry window never executed; '
                           'the image or the entry patch is wrong and no instrument claim holds')
            elif raw == 20:
                csf['fault_stacked_pc'] = csf['output_va']
                csf['fault_status_cfsr'] = csf['group_stride']
                csf['fault_status_names'] = [name for bit, name in CFSR_BITS
                                             if csf['group_stride'] >> bit & 1]
                outcome = 'instrument-proven'
                verdict = ('the deliberate read faulted and the 2383 stub recorded it (PC %#x, '
                           'CFSR %#x %s), so the fault entry works and the 2383 counter 9 really '
                           'means no exception was taken' %
                           (csf['fault_stacked_pc'], csf['fault_status_cfsr'],
                            '/'.join(csf['fault_status_names']) or 'no CFSR bits'))
            elif raw == 30:
                outcome = 'unmapped-read-completed'
                verdict = ('the read of the unmapped protected section completed, so the reachable '
                           'address space is larger than the built tables and the 2383 counter 9 '
                           'must be re-read before any conclusion')
            elif raw in (0, 8) and refused:
                outcome = 'refusal-not-signalled'
                verdict = ('the MMU refused the read (%s) but the entry program never advanced, so '
                           'the refusal reached the MCU as a hang rather than as an exception: the '
                           'exception entry is not an instrument on this machine. The MMU words '
                           'are - and 2383 read both of them clear, which does exclude a refusal '
                           'for that fetch' %
                           ('AS_FAULT %#x at %#x, mmu_raw %#x' %
                            (csf['control_fault_status'], csf.get('control_fault_va', 0),
                             csf['mmu_raw'])))
            elif raw in (0, 8):
                outcome = 'unmapped-read-stalled'
                verdict = ('the marker is set but the counter still holds its template seed: the '
                           'unmapped read neither faulted nor completed, so an access that stalls '
                           'is indistinguishable from one that faults silently - the 2383 result '
                           'loses its diagnostic value')
            else:
                outcome = 'unexpected-counter'
                verdict = 'the control reached no defined 20/30 checkpoint'
            csf['positive_control_outcome'] = outcome
            csf['instrument_verdict'] = verdict
        if expected_build == 0x2383:
            # 2382 plus the vendor fault entry: the fetch-prime probe is
            # unchanged, so 9/10/11 still mean what they meant, and 20 can only
            # come from the handler this build installed.
            raw = csf['groups']
            csf['fetch_prime_counter'] = raw
            csf['relocated_code_pa'] = csf['firmware_probe_pa']
            relocated = csf['firmware_probe_pa'] == 0x401a4000
            csf['relocation_observed'] = relocated
            csf['fault_entry_counter'] = raw
            csf['fault_taken'] = raw == 20
            csf['fault_instrument_note'] = (
                '2384 measured that a refused access reaches the MCU as a hang: the control '
                'program wrote its marker and then stopped without ever entering the fault '
                'handler. A clear fault counter therefore cannot, on its own, exclude a refusal; '
                'the load-bearing evidence in this build is as_fault and mmu_raw reading 0.')
            if raw == 20:
                # shared+12 and shared+20 are repurposed only on this path.
                csf['fault_stacked_pc'] = csf['output_va']
                csf['fault_status_cfsr'] = csf['group_stride']
                csf['fault_status_names'] = [name for bit, name in CFSR_BITS
                                             if csf['group_stride'] >> bit & 1]
            # The state gate comes before the counter: a fault is only
            # interpretable in the state every probe build reports.
            if not relocated:
                outcome = 'not-relocated'
                verdict = ('the executable probe PA is not the relocated one; this report did '
                           'not come from the 2382 mapping the build reuses')
            elif csf['error'] == -54 or csf['mmu_raw'] & 0xffff or csf['as_fault']:
                outcome = 'gpu-fault'
                verdict = ('AS_FAULT or the MMU status is set; treat this as a GPU-side fault '
                           'and do not read the counter as the MCU answer')
            elif csf['input_va'] != 0x01000200:
                outcome = 'marker-absent'
                verdict = 'the target marker is absent; the probe did not establish entry'
            elif (csf['stage'] != 4 or csf['error'] != -53 or
                  csf['mcu_status'] != 1 or csf['firmware_ready']):
                outcome = 'unexpected-state'
                verdict = 'unexpected MCU/report state; no fault-vs-hang conclusion is justified'
            elif raw == 20:
                outcome = 'fault-taken'
                pc = csf['fault_stacked_pc']
                if csf['fault_status_cfsr']:
                    verdict = ('the MCU faulted at %#x; CFSR=%#x (%s), so the access is refused '
                               'rather than never completing - a translation or permission '
                               'answer, not a bus timeout' %
                               (pc, csf['fault_status_cfsr'],
                                '/'.join(csf['fault_status_names'])))
                else:
                    verdict = ('the MCU faulted at %#x with CFSR clear, i.e. an escalated hard '
                               'fault; HFSR was not captured, so the next build must record it '
                               'before any mechanism claim' % pc)
            elif raw == 9:
                outcome = 'no-fault-fetch-incomplete'
                verdict = ('the counter is still 9 and the handler never ran, so no fault was '
                           'taken: the fetch of the cold block never completes, which points at '
                           'the MCU-side fetch/ready path rather than at translation')
            elif raw == 10:
                outcome = 'data-read-incomplete'
                verdict = ('the call returned but the data read at 0x01000210 did not; the fetch '
                           'completes and the read is the broken one')
            elif raw == 11:
                outcome = 'data-read-returned'
                verdict = ('the call and the read both returned; both paths work at this target '
                           'and the remaining wall is elsewhere')
            else:
                outcome = 'unexpected-counter'
                verdict = 'the probe did not reach a defined 9/10/11/20 checkpoint'
            csf['fetch_prime_outcome'] = outcome
            csf['instrument_verdict'] = verdict
        if expected_build == 0x2382:
            # 2379's container patch, byte for byte, on a plan that appends the
            # R-X section after the whole layout. Same VA, same leaf encoding,
            # same descriptor bits; only the section's PA moved, by0x124000.
            raw = csf['groups']
            csf['fetch_prime_counter'] = raw
            csf['relocated_code_pa'] = csf['firmware_probe_pa']
            #0x40077000 arena +0x12d000 relocated offset. Both are pinned by
            # the builder (arena symbol, and the plan's own offsets), so any
            # other value means this report cannot answer the PA question.
            relocated = csf['firmware_probe_pa'] == 0x401a4000
            csf['relocation_observed'] = relocated
            if not relocated:
                outcome = 'not-relocated'
                verdict = ('the executable probe PA is not the relocated one, so this image '
                           'did not move the code section; the counter says nothing about '
                           'physical placement')
            elif csf['error'] == -54 or csf['mmu_raw'] & 0xffff or csf['as_fault']:
                outcome = 'fault'
                verdict = ('the relocated mapping faulted translation; the counter does not '
                           'establish fetch priming and the move itself is the suspect')
            elif csf['input_va'] != 0x01000200:
                outcome = 'marker-absent'
                verdict = 'the target marker is absent; the probe did not establish entry'
            elif (csf['stage'] != 4 or csf['error'] != -53 or
                  csf['mcu_status'] != 1 or csf['firmware_ready']):
                outcome = 'unexpected-state'
                verdict = 'unexpected MCU/report state; no physical-placement conclusion is justified'
            elif raw == 9:
                outcome = 'fetch-call-incomplete'
                verdict = ('the fresh-block call still did not return with the section '
                           '0x124000 further into the arena; the physical pages this build '
                           'moved it to are not the difference, so the wall is above PA '
                           'placement - the MCU fetch path or the translation regime')
            elif raw == 10:
                outcome = 'data-read-incomplete'
                verdict = ('the call returned at the relocated section but the data read at '
                           '0x01000210 did not; executing a cold block is not the same as '
                           'making that word readable')
            elif raw == 11:
                outcome = 'data-read-returned'
                verdict = ('the call and the data read both returned once the section moved, '
                           'so the original physical pages were the blocker and the next '
                           'suspect is PA routing rather than the virtual mapping')
            else:
                outcome = 'unexpected-counter'
                verdict = 'the probe did not reach a defined 9/10/11 checkpoint'
            csf['fetch_prime_outcome'] = outcome
            csf['instrument_verdict'] = verdict
        if expected_build == 0x2380:
            # The first build that maps every firmware section the way the
            # pinned r32p1 convert_mem_flags() does on a non-coherent SoC:
            # cached->AS_MEMATTR index0, everything else->index5, no SH bits.
            # The selected attribute bytes stay 0x88/0x4c; the index number,
            # the shared leaf's share bits and MEMATTR[0] are what changed.
            if csf['memattr_lo'] == 0x888d8f88 and csf['memattr_hi'] == 0x00084c8d:
                integrity = 'vendor-memattr'
            else:
                integrity = 'wrong-memattr'
            csf['vendor_memattr_pair'] = integrity
            if integrity == 'wrong-memattr':
                outcome = 'not-this-image'
                verdict = ('the AS_MEMATTR pair is not the 2380 vendor pair; this image or '
                           'report does not belong to build 2380')
            elif csf['error'] == -54 or csf['mmu_raw'] & 0xffff or csf['as_fault']:
                outcome = 'fault'
                verdict = ('the vendor index/share pairing faulted translation; revert to the '
                           '2379 leaf encoding before trying anything else')
            elif (csf['stage'] == 7 and csf['error'] == 0 and csf['firmware_ready'] and
                  csf['version'] not in (0, 0xffffffff)):
                outcome = 'ready'
                verdict = ('the firmware reached its runtime interface with the vendor MemAttr '
                           'pairing; the shared-leaf share bits and the index numbering were '
                           'the blocker, and the global interface stage (2381) is next')
            elif (csf['stage'] == 4 and csf['error'] == -53 and csf['mcu_status'] == 1 and
                  not csf['firmware_ready'] and csf['version'] in (0, 0xffffffff)):
                outcome = 'unchanged'
                verdict = ('same signature as 2376/2378: the firmware still never reaches its '
                           'interface, so the share bits and index numbering are not the wall '
                           'and the cold code-page access pattern remains the suspect')
            else:
                outcome = 'unexpected-state'
                verdict = 'unexpected stage/error combination; no MemAttr conclusion is justified'
            csf['vendor_memattr_outcome'] = outcome
            csf['instrument_verdict'] = verdict
        if expected_build == 0x2366:
            # No firmware, no ladder: the 2363 counter loop, byte for byte,
            # relocated from 0x010018ec to 0x010019ee and entered by a direct
            # branch from the reset vector. groups is still the template's 8
            # plus one per turn.
            spin = csf.get('groups')
            turns = None if spin is None else (spin - 8) & 0xffffffff
            csf['window_spin_raw_groups'] = spin
            csf['window_spin_turns'] = turns
            if spin == 8:
                csf['instrument_verdict'] = (
                    'the loop never turned once at 0x010019ee, while the identical loop at '
                    '0x010018ec ran 406 million turns: that address cannot host a loop, so the '
                    'stop in 2362-2365 was the place, not the ladder')
                csf['next_step'] = ('map what makes 0x010019ee different: check the page tables and '
                    'the instruction fetch window for the second half of the code section')
            elif turns is not None and turns > 8:
                csf['instrument_verdict'] = (
                    'the loop free-runs at 0x010019ee (%d turns) exactly as it does at '
                    '0x010018ec, so the address is fine on its own and it is the ladder that '
                    'leaves the core unable to continue' % turns)
                csf['next_step'] = ('put one rung back in front of the loop and see how many '
                    'turns survive; the delta names what the ladder breaks')
            else:
                csf['instrument_verdict'] = (
                    'the relocated loop turned %d times and stopped, so that address tolerates a '
                    'few instructions but not a sustained loop' % (turns or 0))
                csf['next_step'] = ('vary only the loop address in steps of 0x100 to find where '
                    'sustained execution stops being possible')
        if expected_build == 0x2363:
            # This build runs no firmware at all: the reset entry is a loop that
            # increments the groups word forever. It answers the question every
            # earlier build assumed away - does the core keep executing?
            spin = csf.get('groups')
            csf['spin_raw_groups'] = spin
            csf['spin_iterations'] = None if spin is None else (spin - 8) & 0xffffffff
            csf['spin_note'] = ('the reset entry at 0x010018ec is a five-instruction loop that '
                'adds 1 to shared+0x10 and branches back; the template starts that word at 8, '
                'so iterations = groups-8')
            if spin == 8:
                csf['instrument_verdict'] = (
                    'the loop never executed once: the core does not run our code at all after '
                    'MCU_CONTROL, so every ladder result so far measured a core that had already '
                    'stopped before the first instruction')
                csf['next_step'] = ('stop touching firmware: find what actually releases the CSF '
                    'core (power, clock or a vendor handshake) before any further ladder work')
            elif spin is not None and spin > 8 and spin <= 8 + 100000:
                csf['instrument_verdict'] = (
                    'the core executed exactly %d loop iterations and then stopped, so it does '
                    'run but is stalled by something outside the loop' % (spin - 8))
                csf['next_step'] = ('the stall is not instruction dependent: look for the agent '
                    'that halts the core, since a five-instruction loop with no bus access '
                    'cannot stop itself')
            else:
                csf['instrument_verdict'] = (
                    'the core free-runs: the counter wrapped, so the MCU executes continuously '
                    'for the whole second and every earlier stall was real code behaviour')
                csf['next_step'] = ('keep the ladder and resume bisecting the firmware path')
        if expected_build == 0x2371:
            # Same sweep as 2370 but in 0x10 steps: 0x01001900 .. 0x01001a00.
            raw = csf.get('groups')
            probes = None if raw is None else max(0, raw - 8)
            fail = None if probes is None else 0x01001900 + 0x10 * probes
            csf['fine_probes'] = probes
            csf['fine_first_failing'] = None if fail is None else '%#010x' % fail
            if probes is None:
                csf['instrument_verdict'] = 'no groups word was sampled'
            elif probes == 0:
                csf['instrument_verdict'] = (
                    'even the first probe at 0x01001900 - bytes this loop is executing - did not '
                    'return, so the counter itself is broken rather than the window')
            elif probes == 1:
                csf['instrument_verdict'] = (
                    "the sweep stopped at 0x01001910, one line past the last byte of this loop at "
                    '0x01001907: the core can only read code-region bytes it has already fetched '
                    'as instructions, which is why every distant literal in the vendor firmware '
                    'stalls it')
                csf['next_step'] = ('stop treating the code region as readable data: inline every '
                    'constant the boot path needs, or find why a data read of an unfetched code '
                    'line never completes')
            else:
                csf['instrument_verdict'] = (
                    'the sweep completed %d reads in 0x10 steps and stopped at %#010x, so '
                    '0x01001900..%#010x is readable without having been fetched: the limit is a '
                    'region size near 0x01001a00, not the fetch stream'
                    % (probes, fail, fail - 0x10))
                csf['next_step'] = ('narrow the top edge in 4-byte steps around %#010x and check '
                    'what the kernel maps or copies at that offset' % fail)
        if expected_build == 0x2370:
            # Address sweep: probe 0x01001900, 0x01001a00, ... one 0x100 step
            # per turn, counting only after a read returns.
            raw = csf.get('groups')
            probes = None if raw is None else max(0, raw - 8)
            fail = None if probes is None else 0x01001900 + 0x100 * probes
            csf['sweep_probes'] = probes
            csf['sweep_first_failing'] = None if fail is None else '%#010x' % fail
            csf['sweep_site'] = csf.get('progress_site')
            if probes is None:
                csf['instrument_verdict'] = 'no groups word was sampled'
            elif probes == 0:
                csf['instrument_verdict'] = (
                    'the very first probe - 0x01001900, eight bytes past the end of this loop - '
                    'already stops the core, so even a read of code the core itself is executing '
                    'hangs unless it is part of the fetched instruction stream')
                csf['next_step'] = ('treat code-region data reads as unusable: build every '
                    'constant the firmware needs beside the instruction that uses it, or find the '
                    'mapping attribute that makes data reads at range complete')
            else:
                csf['instrument_verdict'] = (
                    'the sweep completed %d reads and the first address that stops the core is '
                    '%#010x: everything below it returns, so the window is real and its top edge '
                    'is now known to 0x100' % (probes, fail))
                csf['next_step'] = ('narrow the edge with the same probe in 0x10 steps between '
                    'the last good address and %#010x' % fail)
        if expected_build == 0x2369:
            # Counter pointer built from immediates; the far slot is read once
            # into a discarded register, so only the read itself can stop the
            # loop from counting.
            raw = csf.get('groups')
            turns = None if raw is None else max(0, raw - 8)
            csf['imm_counter_turns'] = turns
            csf['imm_counter_raw_groups'] = raw
            if turns is None:
                csf['instrument_verdict'] = 'no groups word was sampled'
            elif turns == 0:
                csf['instrument_verdict'] = (
                    'the loop never counted even though its counter pointer came from '
                    'immediates: the single discarded read of the far slot is what stops the '
                    'core, so a distant data read from the code region hangs it rather than '
                    'returning a wrong value')
                csf['next_step'] = ('map the code region so the core can read it as data - check '
                    'the PTE attributes and whether the read goes through the same translation '
                    'as the fetch - because the vendor firmware cannot run without its pool')
            else:
                csf['instrument_verdict'] = (
                    'the loop counted %d turns with the far read executed once and discarded, so '
                    'that read does not stall the core: it returns a wrong value, and 2368 failed '
                    'because the counter pointer it fed was garbage, not because the bus hung'
                    % turns)
                csf['next_step'] = ('find out what the far read actually returns: store it to '
                    'shared+0x0c and read it back, then decide whether the code region needs a '
                    'different mapping attribute')
        if expected_build == 0x2368:
            # 2363's loop byte for byte, with its literal moved from 0x010018f8
            # (twelve bytes away) to 0x01001af8 (520 bytes away).
            raw = csf.get('groups')
            turns = None if raw is None else max(0, raw - 8)
            csf['far_literal_turns'] = turns
            csf['far_literal_raw_groups'] = raw
            csf['far_literal_site'] = csf.get('progress_site')
            if turns is None:
                csf['instrument_verdict'] = 'no groups word was sampled'
            elif turns == 0:
                csf['instrument_verdict'] = (
                    'the loop never turned once with its literal 520 bytes away, while the '
                    'same loop with the literal twelve bytes away turned 406 million times: a '
                    'distant data read from the code region stops the core, and that is exactly '
                    'what the vendor code at 0x010019ee does with ldr r0,[pc,#0x1d8]')
                csf['next_step'] = ('stop trying to execute the vendor literal pool: either copy '
                    'the constants next to the code, or find the mapping attribute that makes '
                    'the code region readable as data at range')
            elif turns > 1000:
                csf['instrument_verdict'] = (
                    'the loop free-ran with its literal 520 bytes away (%d turns), so distance '
                    'is harmless and 2367 died for another reason - most likely the 528-byte '
                    'overwrite rather than the literal' % turns)
                csf['next_step'] = ('repeat 2367 with the literal moved next to the loader but '
                    'keep the full 528-byte sled, to separate size from distance')
            else:
                csf['instrument_verdict'] = (
                    'the loop turned %d times with the far literal and then stopped, so the far '
                    'read is survivable but something after it is not' % turns)
        if expected_build == 0x2367:
            # No branches anywhere: 128 `adds r2,#1 / str r2,[r3]` pairs from
            # the reset entry, one store every four bytes, then `b .`.
            raw = csf.get('groups')
            stores = None if raw is None else max(0, raw - 8)
            frontier = None if stores is None else 0x010018ec + 4 * stores
            csf['sled_raw_groups'] = raw
            csf['sled_stores'] = stores
            csf['sled_frontier'] = None if frontier is None else '%#010x' % frontier
            if stores is None:
                csf['instrument_verdict'] = 'no groups word was sampled'
            elif frontier >= 0x01001af8:
                csf['instrument_verdict'] = (
                    'the core executed all %d stores and parked in `b .`: a straight line of '
                    '%d instructions across %#x bytes runs to completion from the reset entry, '
                    'so linear execution is fine and only a branch or a return can stop it'
                    % (stores, 2 * stores + 2, 4 * stores))
                csf['next_step'] = ('keep the sled and add a single short backward branch at '
                    'its end; if that kills the core, branches are the wall and the firmware '
                    'has to be booted through a path with none')
            elif stores == 0:
                csf['instrument_verdict'] = (
                    'not one store landed, so the core died in the first four bytes after the '
                    'reset vector: the entry itself is no longer executable in this build')
            else:
                csf['instrument_verdict'] = (
                    'the core landed %d stores and died at %#010x, i.e. after %d instructions '
                    'in a straight line with no branch: the wall is a place, not a control-flow '
                    'event' % (stores, frontier, 2 * stores))
                csf['next_step'] = ('put the same sled at a different base (e.g. 0x01001a00) '
                    'and see whether the frontier moves with the base or stays at the same '
                    'absolute address')
        if expected_build in (0x2351, 0x2352, 0x2353, 0x2354, 0x2355, 0x2356, 0x2357, 0x2358, 0x2359, 0x2360, 0x2361, 0x2362, 0x2364, 0x2365):
            # Nine barriers are `bl` sites into one stub that stores the site
            # address in shared+0x08; the last write is where execution stopped.
            sites = {0x01001914: 'isb after the PSP switch',
                     0x010019e2: 'dsb in the cache-clean helper',
                     0x010019e6: 'the isb right after it',
                     0x010019ea: 'the mov.w right after the isb',
                     0x010019ee: 'the ICIALLU literal load',
                     0x010019f2: 'the CCR literal load',
                     0x010019f6: 'the orr that sets CCR.IC',
                     0x010019fc: 'dsb in the cache-enable helper',
                     0x01001a2c: 'entry helper 3',
                     0x01002aec: 'state dispatch block',
                     0x01002b26: 'before the NVIC write',
                     0x01002b32: 'before the TBB',
                     0x01003018: 'end of init',
                     0x01003036: 'inside the idle loop'}
            value = csf['input_va']
            csf['progress_site'] = '%#010x' % value
            csf['progress_name'] = sites.get(value, 'unknown')
            csf['progress_note'] = ('Each visited barrier overwrites shared+0x08 with its own '
                'address, so the word names the LAST site reached. 0x04002000 means none were '
                'reached; anything 0x0100xxxx is real progress.')
            if expected_build in (0x2354, 0x2355, 0x2356, 0x2357, 0x2358, 0x2359, 0x2360, 0x2361, 0x2362, 0x2364, 0x2365):
                # The stub counts its own entries by incrementing the groups
                # word, which the firmware's shared-section template preloads
                # with 8 (group_stride 0xa0 follows it). The count of rung
                # entries is therefore groups-8: one entry means the core
                # stopped after that site, more means it keeps re-entering the
                # reset path instead of halting.
                raw = csf.get('groups')
                hits = None if raw is None else max(0, raw - 8)
                csf['rung_hits_raw_groups'] = raw
                csf['rung_hits'] = hits
                csf['rung_hits_note'] = ('groups-8, because the firmware shared template starts '
                    'the word at 8; group_stride 0xa0 in the next word never changes')
                if hits is not None and hits > 1:
                    csf['loop_verdict'] = ('the reset path was entered %d times, so the core is '
                        'restarting rather than parking at the last site' % hits)
                elif hits == 1:
                    csf['loop_verdict'] = ('exactly one rung entry, so the core executed the '
                        'ladder once and then stopped')
                else:
                    csf['loop_verdict'] = 'the counter never advanced'
                if expected_build == 0x2357:
                    # The stub no longer returns to lr: it overwrites the stacked
                    # return address with 0x0100192a, the call site of the helper
                    # whose first instruction is rung 2. Every entry bounces back
                    # there, so advancing proves the ladder's return path works.
                    if csf['progress_site'] == '0x010019e2' or (hits or 0) > 1:
                        csf['instrument_verdict'] = ('the bounce worked: the stub returns and '
                            'execution reaches the rung-2 helper, so the ladder is sound and the '
                            'stop at 0x01001914 in 2351-2356 was real firmware behaviour')
                    else:
                        csf['instrument_verdict'] = ('the bounce did not work: even a fixed return '
                            'target never reaches the rung-2 helper, so the ladder cannot be '
                            'trusted past rung 1 and the measurement has to change')
                if expected_build == 0x2358:
                    # 2358 drops the stack entirely: the stub keeps lr, touches
                    # only r3/r12 and returns with bx lr. If PSP at 0x0203f000 is
                    # not real RAM the old push/pop instrument was killing the
                    # core itself, so any advance here re-opens every earlier
                    # verdict; a second stop at rung 1 means the call/return is
                    # not survivable at all and the probe has to stop using bl.
                    if (hits or 0) > 1:
                        csf['instrument_verdict'] = (
                            'the stack was the wall: a stack-free call/return advances the '
                            'ladder, so the single entry in 2351-2357 was the probe killing '
                            'the core and those stops were not firmware behaviour')
                        csf['next_step'] = ('keep this stub and re-read the rung order before '
                            'changing any firmware byte again')
                    elif hits == 1:
                        csf['instrument_verdict'] = (
                            'a stack-free bl/bx lr still stops at rung 1, so the barrier '
                            'replacement itself is not survivable and no call-based ladder can '
                            'measure past 0x01001914')
                        csf['next_step'] = ('stop using bl: either patch the barrier with an '
                            'inline marker that needs no return, or sample the core through a '
                            'debug port instead of the firmware image')
                if expected_build == 0x2359:
                    # 2358 advanced to rung 2, so the stop is now inside the
                    # cache-enable helper: ICIALLU (0xe000ef50) write, CCR
                    # (0xe000ed14) read, CCR.IC write. 2359 nops only the two
                    # stores and keeps the read, which is always safe.
                    if csf['progress_site'] != '0x010019e2':
                        csf['instrument_verdict'] = (
                            'the cache writes were the wall: with ICIALLU and CCR.IC removed '
                            'execution leaves the cache helper, so the MCU cannot take those '
                            'two stores and the firmware has to come up with caches off')
                        csf['next_step'] = ('keep both nops and follow the ladder to the next '
                            'stop; a C-cache/CB block that cannot be written is a platform '
                            'power or clock question, not a firmware one')
                    else:
                        csf['instrument_verdict'] = (
                            'the two cache writes are not the wall: the helper still dies with '
                            'ICIALLU and CCR.IC nop\'d, so the kill is the CCR read or the '
                            'isb/fetch that follows it')
                        csf['next_step'] = ('nop the CCR read as well; if the helper then '
                            'returns, the core cannot read its own SCB at all')
                if expected_build == 0x2360:
                    # Two extra rungs split the cache helper: the isb at
                    # 0x010019e6 and the orr at 0x010019f6. With both stores
                    # already nop'd the only device access between them is the
                    # CCR read, and after the orr there is nothing but the call
                    # into rung 3.
                    site = csf['progress_site']
                    if site == '0x010019e6':
                        csf['instrument_verdict'] = (
                            'the CCR read is the wall: execution reaches the isb after the '
                            'rung-2 call and never reaches the orr, so ldr r1,[0xe000ed14] '
                            'takes the core down even though both stores are gone')
                        csf['next_step'] = ('the MCU cannot reach its own System Control Space; '
                            'nop the CCR read to confirm the rest of the helper runs, then '
                            'treat SCB/NVIC access as unavailable until the block is powered')
                    elif site == '0x010019f6':
                        csf['instrument_verdict'] = (
                            'the CCR read survives: the orr is reached, so the stop is the call '
                            'into rung 3 that follows it')
                        csf['next_step'] = ('inspect the fetch at 0x010019fc; the helper body '
                            'is clear and the failure is in the next rung')
                    else:
                        csf['instrument_verdict'] = (
                            'the whole cache helper runs: ICIALLU, CCR and CCR.IC are behind '
                            'the core and rung 3 is reached')
                if expected_build == 0x2361:
                    # The reset prologue's first three stores were redirected to
                    # RAM since 2339; 2361 puts the vendor literals back, so the
                    # ladder now says whether those writes are what make the
                    # peripheral/PPB space reachable at all.
                    site = csf['progress_site']
                    if site in ('0x04002000', '0x00000000') or not (hits or 0):
                        csf['instrument_verdict'] = (
                            'the first vendor store itself is fatal: nothing is recorded, so '
                            'str 0xb,[0x40022000] takes the core down before the PSP switch and '
                            'the MCU has no working path to any peripheral')
                        csf['next_step'] = ('find what powers or un-gates the MCU peripheral '
                            'bridge; the core fetches and reaches RAM, so the failure is in the '
                            'bus fabric or in the block that 0x40022000 belongs to')
                    elif site == '0x01001914' and (hits or 0) == 1:
                        csf['instrument_verdict'] = (
                            'the prologue is not the enabler: all three vendor stores go through '
                            'and rung 1 is reached, yet the CCR read still kills the core')
                        csf['next_step'] = ('treat the PPB as unreachable for now and look at '
                            'how the MCU is released from reset; the vendor prologue ran and '
                            'the core still cannot read CCR')
                    elif site == '0x010019e2' and (hits or 0) == 2:
                        csf['instrument_verdict'] = (
                            'the prologue makes the stall come EARLIER, not later: 2360 reached '
                            'the isb rung with three entries and this build stops at rung 2, so '
                            'those three real stores do not unlock the peripheral space')
                        csf['next_step'] = ('put the redirects back and stop treating the entry '
                            'prologue as an enabler; nothing was gained by running it')
                    else:
                        csf['instrument_verdict'] = (
                            'the entry prologue was the missing piece: with the vendor stores in '
                            'place execution gets past the CCR read and the ladder advances')
                if expected_build == 0x2362:
                    # 2361 showed the vendor prologue makes things worse, so 2362
                    # is 2360 again with the last device access of the cache
                    # helper - the CCR read - turned into a nop. Its window now
                    # holds nothing but arithmetic and literal loads.
                    site = csf['progress_site']
                    if site == '0x010019e6' and (hits or 0) == 3:
                        csf['instrument_verdict'] = (
                            'with no device access left between the isb rung and the orr rung the '
                            'core still stops there, so the stall is not a bus access at all but '
                            'the core itself between those two instructions')
                        csf['next_step'] = ('stop looking at peripherals: compare the core clock '
                            'and the fetch path, because plain arithmetic cannot stall a bus')
                    elif site == '0x010019f6':
                        csf['instrument_verdict'] = (
                            'the CCR read was the stall: the orr rung is reached once the read is '
                            'gone, and the core then dies on the branch into rung 3')
                        csf['next_step'] = ('the helper is clear; the next wall is the fetch at '
                            '0x010019fc, so instrument inside rung 3')
                    else:
                        csf['instrument_verdict'] = (
                            'the cache helper is behind the core: with ICIALLU, CCR and the CCR '
                            'read all gone the ladder reaches rung 3 or further')
                if expected_build == 0x2364:
                    # 2363 proved the core free-runs, so every remaining four-byte
                    # window of the cache helper is a rung now. The pair
                    # (last site, hits) separates the two ways a rung can end a
                    # run: the stub stores the site first and only then bumps the
                    # counter, so equal counts mean the core died inside the stub
                    # and a higher count means it returned and died before the
                    # next rung.
                    site = csf['progress_site']
                    h = hits or 0
                    dead = {
                        '0x010019e6': ('the return from the isb rung never lands on 0x010019ea: '
                            'calling the stub is the last thing the core survives'),
                        '0x010019ea': ('the core dies on the first instruction after the isb, the '
                            'four bytes at 0x010019ea that in the vendor image only zero r1'),
                        '0x010019ee': ('the core dies at 0x010019ee, the ICIALLU literal load '
                            'whose consumer store is already a nop'),
                        '0x010019f2': ('the core dies at 0x010019f2, the CCR literal load whose '
                            'read and store are already nops'),
                        '0x010019f6': ('the window is clear: the core dies at or inside the orr '
                            'rung, so the wall is the branch into the second half of the helper'),
                        '0x010019fc': ('the cache helper is complete: the core passes the orr rung '
                            'and dies on the dsb rung that opens the next block'),
                    }
                    if site in dead:
                        csf['instrument_verdict'] = dead[site]
                    if site in ('0x010019ea', '0x010019ee', '0x010019f2'):
                        if h >= 4:
                            csf['instrument_verdict'] += (' - the counter advanced, so the stub '
                                'returned and the core died before the next rung')
                        else:
                            csf['instrument_verdict'] += (' - the counter did not advance, so the '
                                'core died inside the stub, between its site store and its counter '
                                'store, not after returning')
                    csf['next_step'] = ('a plain instruction killing a core that free-runs a counter '
                        'is a fetch or pipeline effect, so rerun the 2363 counter loop from '
                        '0x010019ea: if it free-runs there the address is not the difference and '
                        'the stop depends on what the ladder did before it')
                if expected_build == 0x2365:
                    # 2364 moved the stop forward by exactly the four bytes of
                    # rung it was given, so 2365 turns 0x010019ee itself into a
                    # counter loop instead of a call. group_stride is the seed
                    # 0xa0 plus four per turn, and nothing else touches it.
                    site = csf['progress_site']
                    stride = csf.get('group_stride')
                    spins = None if stride is None else ((stride - 0xa0) & 0xffffffff) // 4
                    csf['window_loop_stride'] = stride
                    csf['window_loop_spins'] = spins
                    if site != '0x010019ea':
                        csf['instrument_verdict'] = (
                            'the ladder did not reach rung 4 here, so the loop was never entered '
                            'and the previous stop is not stable across builds')
                    elif spins:
                        csf['instrument_verdict'] = (
                            'the core runs happily at 0x010019ee: the plain counter loop turned '
                            '%d times at the very address where 2364 died, so the instruction '
                            'there is reachable and the wall is the call and its return, not the '
                            'address' % spins)
                        csf['next_step'] = ('keep the ladder, replace the bl at 0x010019ee with a '
                            'call to a stub moved elsewhere, and see whether the target or the '
                            'return address is what fails')
                    else:
                        csf['instrument_verdict'] = (
                            'the core dies at 0x010019ee even when those bytes are a three-'
                            'instruction loop, so the address becomes unreachable once the ladder '
                            'has run and something the ladder leaves behind is what stops it')
                        csf['next_step'] = ('run the same loop with the ladder patched out: if it '
                            'free-runs there, the ladder corrupts core state rather than the code')
        if expected_build == 0x2344:
            # The same fault entry, but it returns: every hit ORs its udf
            # immediate into shared+0xffc and execution resumes after the
            # marker. The word is therefore a map of barriers the MCU really
            # passed, in execution order, not just the first trap.
            before = struct.unpack_from('<I', raw, 444)[0]
            after = struct.unpack_from('<I', raw, 564)[0]
            sites = ((0x01, 0x010019e2), (0x02, 0x010019fc), (0x04, 0x01001a2c),
                     (0x08, 0x01002aec), (0x10, 0x01002b26), (0x20, 0x01002b32),
                     (0x40, 0x01003018), (0x80, 0x01003036))
            csf['trace_bitmap_before'] = before
            csf['trace_bitmap_after'] = after
            csf['trace_sites_reached'] = [hex(va) for bit, va in sites if after & bit]
            csf['trace_sites_missing'] = [hex(va) for bit, va in sites if not after & bit]
            csf['trace_furthest'] = next(
                (hex(va) for bit, va in reversed(sites) if after & bit), None)
            csf['trace_probe_note'] = ('Bits are ordered barriers from the reset path '
                '(0x19e2 cache clean, 0x19fc, 0x1a2c, 0x2aec dispatch block, 0x2b26 before '
                'NVIC, 0x2b32 before the TBB, 0x3018 end of init, 0x3036 idle loop). A bit '
                'means the MCU provably executed that barrier; the highest bit is where it '
                'stopped advancing. Missing bits are proof of non-arrival, not of failure.')
        if expected_build in (0x2345,0x2346,0x2347):
            # Same resumable handler, but the bitmap lives in shared+4 because
            # shared+0xffc is the one word in that page that never takes a
            # write (build 2341). Bit 0 is the barrier right after the PSP
            # switch, so a clear bit 0 means the MCU stopped before the
            # 0x40003034 load rather than inside a later helper.
            bitmap = csf['features']
            sites = ((0x01, 0x01001914), (0x02, 0x010019e2), (0x04, 0x01001a2c),
                     (0x08, 0x01002aec), (0x10, 0x01002b26), (0x20, 0x01002b32),
                     (0x40, 0x01003018), (0x80, 0x01003036))
            csf['trace_bitmap'] = bitmap
            csf['trace_sites_reached'] = [hex(va) for bit, va in sites if bitmap & bit]
            csf['trace_sites_missing'] = [hex(va) for bit, va in sites if not bitmap & bit]
            csf['trace_furthest'] = next(
                (hex(va) for bit, va in reversed(sites) if bitmap & bit), None)
            csf['trace_probe_note'] = ('shared+4 bitmap of barriers the MCU passed: 0x01 '
                'post-PSP-switch, 0x02 first helper, 0x04 third helper, 0x08 dispatch block, '
                '0x10 pre-NVIC, 0x20 pre-TBB, 0x40 tail of init, 0x80 wfi loop. Bit 0x01 clear '
                'means it never got past the 0x40003034 load window at all.')
        # A2380 report that does not carry the vendor AS_MEMATTR pair did not
        # come from the image that was measured, so it can never be verified.
        pair_ok = csf.get('vendor_memattr_pair', 'vendor-memattr') == 'vendor-memattr'
        result['csf_firmware_boot_verified'] = (success and ready and cleanup and pair_ok and
                                               csf['stage'] == 7 and csf['error'] == 0)
    result.update(error_details(result, result.get('csf')))
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('marks',type=Path)
    p.add_argument('--build',type=lambda s:int(s,0),default=0x2321,
                   help='expected kernel/report build (0x2321 through 0x2397)')
    p.add_argument('--allow-missing-leaf',action='store_true',
                   help='decode a build >=0x2388 whose image shipped without the '
                        'sweet-csf-leaf property (2389 did); leaf fields stay absent')
    p.add_argument('--mark',type=lambda s:int(s,0),default=None,
                   help='kernel SWEET_BUILD_ID observed in the capture, when it was '
                        'not bumped for this trial')
    a=p.parse_args()
    try:
        report=decode(a.marks.read_bytes(),a.build,a.mark,
                      require_leaf=not a.allow_missing_leaf)
    except ValueError as exc:
        p.exit(1,str(exc)+'\n')
    print(json.dumps(report,indent=2))

if __name__ == '__main__':
    main()
