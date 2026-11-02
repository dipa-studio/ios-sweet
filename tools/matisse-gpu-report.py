#!/usr/bin/env python3
"""Decode the independent shim GPU report from a Recovery SWEETMRK capture."""
import argparse
import json
from pathlib import Path
import struct

STAGES = {1:'config',2:'power-domain',3:'firmware',4:'memory',5:'shared-init',
          6:'power-on',7:'gpu-id',8:'soft-reset',9:'power-off',10:'complete'}
ERRORS = {0:'success',-20:'argument',-21:'handoff',-22:'overlap',-23:'timeout',
          -24:'stale-reply',-25:'invalid-reply',-26:'ownership',-27:'unpowered',-28:'gpu-model'}
KEYS = ['stage','error','init_result','on_result','off_result','spm_before',
        'spm_after','spm_second','firmware_magic','gpu_id','gpu_status',
        'reset_rawstat','as_present','firmware_memory','power_acquired','cleanup_attempted']
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
    if expected_build not in (0x2321,0x2322,0x2323,0x2324,0x2325,0x2326,0x2327,0x2328,0x2329,0x2330,0x2331,0x2332,0x2333,0x2334,0x2335):
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
    raw = report_bytes(records,300,9,expected_build,'GPU')
    fields = dict(zip(KEYS,struct.unpack('<I4i8I4xQ2I',raw)))
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
            if flags & ~3 or reserved or flags == 2:
                raise ValueError('invalid CSF platform snapshot flags/reserved word')
            csf['platform_sample_flags'] = flags
            for name, offset in (('before', 312), ('after', 376)):
                values = dict(zip(CSF_PLATFORM_KEYS, struct.unpack_from('<16I', raw, offset)))
                csf['platform_' + name] = values
            csf['platform_snapshot_complete'] = flags == 3
            csf['platform_snapshot_note'] = ('Raw register snapshots only; PLL programming words '
                'do not measure clock rate or lock, MCU enabled does not trace execution.')
        if expected_build >= 0x2332:
            flags, reserved, va, pa_lo, pa_hi, word = struct.unpack_from('<6I', raw, 440)
            if flags & ~3 or flags == 2 or (reserved and expected_build != 0x2335):
                raise ValueError('invalid CSF access snapshot flags/reserved word')
            if expected_build == 0x2335:
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
            if flags & ~3 or flags == 2 or (reserved and expected_build != 0x2335):
                raise ValueError('invalid CSF platform path flags/reserved word')
            if expected_build == 0x2335:
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
                 1 <= csf['groups'] <= 31 and csf['group_stride'] >= 32 and
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
        if expected_build == 0x2335:
            csf['entry_marker_va'] = 0x04000ffc
            csf['entry_marker_sampled'] = csf['access_snapshot_complete']
            csf['entry_marker_observed'] = (csf['entry_marker_sampled'] and
                csf['entry_marker_before'] == 0 and csf['entry_marker_after'] == 0x53545542)
            csf['entry_marker_note'] = ('Separate shared+0xffc checkpoint sampled before AUTO and '
                'after wait,before cleanup. Global control/version remains at shared+0.')
            ready = ready and csf['version'] != 0x53545542
            csf['firmware_ready_observed'] = ready
        result['csf_firmware_boot_verified'] = (success and ready and cleanup and
                                               csf['stage'] == 7 and csf['error'] == 0)
    result.update(error_details(result, result.get('csf')))
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('marks',type=Path)
    p.add_argument('--build',type=lambda s:int(s,0),default=0x2321,
                   help='expected kernel/report build (0x2321 through 0x2335)')
    a=p.parse_args()
    try:
        report=decode(a.marks.read_bytes(),a.build)
    except ValueError as exc:
        p.exit(1,str(exc)+'\n')
    print(json.dumps(report,indent=2))

if __name__ == '__main__':
    main()
