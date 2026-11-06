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
CSF_STAGES = {0:'not-run',1:'config',2:'l2',3:'address-space',4:'mcu',
              5:'interface',6:'cleanup',7:'complete'}
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


def decode(data, expected_build=0x2321):
    if expected_build not in (0x2321,0x2322,0x2323,0x2324,0x2325,0x2326,0x2327,0x2328,0x2329,0x2330,0x2331,0x2332,0x2333,0x2334,0x2335,0x2336,0x2337,0x2338,0x2339,0x2340,0x2341,0x2342,0x2343,0x2344,0x2345,0x2346,0x2347,0x2348,0x2349,0x2350,0x2351,0x2352,0x2353,0x2354,0x2355,0x2356,0x2357,0x2358,0x2359,0x2360,0x2361,0x2362,0x2363,0x2364,0x2365,0x2366,0x2367,0x2368,0x2369,0x2370,0x2371,0x2372,0x2373,0x2374,0x2375,0x2376,0x2377,0x2378):
        raise ValueError('unsupported report ABI/build')
    if len(data) != 4096:
        raise ValueError('requires exactly one 4096-byte SWEETMRK block')
    magic,version,count = struct.unpack_from('<8sII',data)
    if magic != b'SWEETMRK' or version != 1 or count > 160:
        raise ValueError('invalid marks header')
    records = [struct.unpack_from('<IIQQ',data,16+24*i) for i in range(count)]
    builds = [a for code,pad,a,b in records if code == 99]
    if builds != [expected_build]:
        raise ValueError('missing/ambiguous/unexpected kernel build mark')
    raw = report_bytes(records,300,14 if expected_build >= 0x2338 else 9,expected_build,'GPU')
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
        raw = report_bytes(records,320,count,expected_build,'CSF')
        csf = dict(zip(CSF_KEYS,struct.unpack('<I2i19I',raw[:88])))
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
            if expected_build >= 0x2326:
                ready = (ready and csf['diag_flags'] == (127 if expected_build >= 0x2327 else 31) and
                    csf['memattr_lo'] == (0x4c4c884c if expected_build >= 0x2330 else 0x4c4c9f4c) and csf['memattr_hi'] == 0x4c4c4c4c and
                    csf['private_memory_sampled'])
            if expected_build >= 0x2327:
                ready = ready and csf['noncoherent_protocol_verified'] and csf['coherency_after'] == 31
            if expected_build >= 0x2328:
                ready = ready and csf['pte_group_configuration_matches']
            if expected_build >= 0x2329:
                csf['vendor_ina_readback_matches'] = csf['transcfg_lo'] == 0x42000006
            if expected_build >= 0x2330:
                csf['vendor_cached_byte_readback_matches'] = (csf['memattr_lo'] == 0x4c4c884c and
                                                            csf['memattr_hi'] == 0x4c4c4c4c)
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
        result['csf_firmware_boot_verified'] = (success and ready and cleanup and
                                               csf['stage'] == 7 and csf['error'] == 0)
    result.update(error_details(result, result.get('csf')))
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('marks',type=Path)
    p.add_argument('--build',type=lambda s:int(s,0),default=0x2321,
                   help='expected kernel/report build (0x2321 through 0x2354)')
    a=p.parse_args()
    try:
        report=decode(a.marks.read_bytes(),a.build)
    except ValueError as exc:
        p.exit(1,str(exc)+'\n')
    print(json.dumps(report,indent=2))

if __name__ == '__main__':
    main()
