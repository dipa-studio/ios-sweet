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


def decode(data, expected_build=0x2321):
    if len(data) != 4096:
        raise ValueError('requires exactly one 4096-byte SWEETMRK block')
    magic,version,count = struct.unpack_from('<8sII',data)
    if magic != b'SWEETMRK' or version != 1 or count > 160:
        raise ValueError('invalid marks header')
    records = [struct.unpack_from('<IIQQ',data,16+24*i) for i in range(count)]
    builds = [a for code,pad,a,b in records if code == 99]
    if builds != [expected_build]:
        raise ValueError('missing/ambiguous/unexpected kernel build mark')
    report = {}
    for code,pad,a,b in records:
        if 300 <= code <= 308:
            if code in report or b != expected_build:
                raise ValueError('duplicate or mismatched GPU report record')
            report[code] = a
    if len(report) != 9:
        raise ValueError('incomplete GPU report; cannot infer success')
    raw = b''.join(struct.pack('<Q',report[code]) for code in range(300,309))
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
    return dict(kernel_build=hex(expected_build),stage_name=STAGES[fields['stage']],
                error_name=ERRORS.get(fields['error'],'firmware-error'),
                power_reset_verified=success,csf_firmware_boot_verified=False,**fields)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('marks',type=Path)
    a=p.parse_args()
    try:
        report=decode(a.marks.read_bytes())
    except ValueError as exc:
        p.exit(1,str(exc)+'\n')
    print(json.dumps(report,indent=2))

if __name__ == '__main__':
    main()
