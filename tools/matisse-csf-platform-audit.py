#!/usr/bin/env python3
"""Offline MT6983 MFG1 protection audit against pinned original sources.

Reads local source files only; never opens a device or writes registers.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
COMMIT = '270b84910b941bf75490fccdb5fb2b3021dd7cbf'
PINS = {
    'mtk-scpsys-mt6983.c': 'a51b69fe0f03843d3001608946a66a601ccaeaa2a12ab52f26939f298781415f',
    'mtk-scpsys.c': '1f78c8f04234ab7e35f833af5b17ed9968fade4f55ebb3039c5747ef01ba4465',
    'mtk-scpsys.h': '4dfca501d5ff3ca133dba4cce820f01c24240ee5580b5873b2f2d1cf0f41eabc',
    'mtk-pd-chk-mt6983.c': 'fe12ca7cc3f84332125cc28291554af1b6bbdbfa0c2bf5b01e13c486c9767f54',
    'gpufreq_mt6983.c': '2f692a49ab1e3d319961851f690ebd153a05dffc4be709dbc55364c4b8bca7ac',
    'gpufreq_mt6983.h': '6182e09425e4f6c1e86011178bd314d769e893c570727096c083951808ec756d',
}
EXPECTED_STEPS = [
    ('IFR_TYPE', 0xca4, 0xca8, 0xca0, 0xcac, 1 << bit) for bit in range(4)
] + [
    ('MFGRPC_TYPE', 0x1040, 0x1044, 0x103c, 0x1048, 0xf0000),
    ('IFR_TYPE', 0xc64, 0xc68, 0xc60, 0xc6c, 0xc0000),
    ('IFR_TYPE', 0xc74, 0xc78, 0xc70, 0xc7c, 0xc0000),
]
PATH_REGISTERS = {
    'rpc_enable': 0x13f9103c, 'rpc_status': 0x13f91048,
    'infra_enable': 0x10001ca0, 'infra_status': 0x10001cac,
    'emi0_enable': 0x10001c60, 'emi0_status': 0x10001c6c,
    'emi1_enable': 0x10001c70, 'emi1_status': 0x10001c7c,
}


def pinned_sources(directory):
    result = {}
    for name, expected in PINS.items():
        data = (directory / name).read_bytes()
        if hashlib.sha256(data).hexdigest() != expected:
            raise ValueError('source SHA256 mismatch: ' + name)
        result[name] = data.decode()
    return result


def domain_block(source, name):
    match = re.search(r'\[MT6983_POWER_DOMAIN_' + re.escape(name) + r'\]\s*=\s*\{', source)
    if not match:
        raise ValueError('missing original domain: ' + name)
    end = source.find('\n\t[MT6983_POWER_DOMAIN_', match.end())
    return source[match.end():end if end >= 0 else len(source)]


def mfg1_steps(source):
    block = domain_block(source, 'MFG1')
    result = []
    pattern = (r'BUS_PROT_IGN\(\s*(\w+),\s*(0x[\da-fA-F]+),\s*'
               r'(0x[\da-fA-F]+),\s*(0x[\da-fA-F]+),\s*'
               r'(0x[\da-fA-F]+),\s*(\w+)\s*\)')
    for kind, setoff, clear, enable, status, macro in re.findall(pattern, block):
        definition = re.search(r'^#define\s+' + re.escape(macro) + r'\s+([^\n]+)', source, re.M)
        if not definition:
            raise ValueError('missing original protection mask: ' + macro)
        expr = definition[1]
        bits = re.findall(r'\(0x1\s*<<\s*(\d+)\)', expr)
        if not bits or re.sub(r'[()|\s]', '', re.sub(r'0x1\s*<<\s*\d+', '', expr)):
            raise ValueError('unsupported original mask expression: ' + macro)
        mask = sum(1 << int(bit) for bit in bits)
        result.append((kind, *(int(value, 16) for value in (setoff, clear, enable, status)), mask))
    if result != EXPECTED_STEPS:
        raise ValueError('original MFG1 protection table differs from reviewed sequence')
    return result


def validate_snapshot(source):
    for name, address in PATH_REGISTERS.items():
        match = re.search(r's->' + name + r'\s*=\s*rd\(io,\s*(0x[\da-fA-F]+)\)', source)
        if not match or int(match[1], 16) != address:
            raise ValueError('snapshot address differs from original source: ' + name)


def audit(sources, snapshot_source, rpc_status=0xfff0fff0, spm_status=0xf):
    steps = mfg1_steps(sources['mtk-scpsys-mt6983.c'])
    validate_snapshot(snapshot_source)
    status_bits = {}
    for name in ('MFG0_DORMANT', 'MFG1', 'MFG2'):
        match = re.search(r'\{MT6983_POWER_DOMAIN_' + name +
                          r',\s*XPU_PWR_STA,\s*(0x[\da-fA-F]+)\}',
                          sources['mtk-pd-chk-mt6983.c'])
        if not match:
            raise ValueError('missing original SPM status bit: ' + name)
        status_bits[name] = int(match[1], 16)
    if status_bits != dict(MFG0_DORMANT=2, MFG1=4, MFG2=8):
        raise ValueError('original SPM mapping differs from reviewed mapping')
    mfg0 = domain_block(sources['mtk-scpsys-mt6983.c'], 'MFG0_DORMANT')
    if not re.search(r'\.sram_slp_bits\s*=\s*GENMASK\(9, 9\)', mfg0):
        raise ValueError('original MFG0 sleep bit differs')
    if not re.search(r'#define\s+GPUFREQ_PDCv2_ENABLE\s+\(1\)', sources['gpufreq_mt6983.h']):
        raise ValueError('original PDCv2 configuration differs')
    return dict(source_commit=COMMIT, source_pins=PINS, original_table_verified=True,
        snapshot_addresses_verified=True,
        protection_assert_order=[dict(kind=k, set=hex(s), clear=hex(c), enable=hex(e),
            status=hex(t), mask=hex(m)) for k, s, c, e, t, m in steps],
        protection_release_table_indices=list(reversed(range(len(steps)))),
        protection_release_ack_note='Original BUS_PROT_IGN skips clear acknowledgement polling.',
        observed_rpc_status=hex(rpc_status), mfg1_rpc_mask='0xf0000',
        observed_rpc_mfg1_status_bits=hex(rpc_status & 0xf0000),
        rpc_enable_and_infra_emi_observed=False,
        observed_spm_status=hex(spm_status), spm_domain_masks=status_bits,
        observed_spm_domain_bits={name: bool(spm_status & mask) for name, mask in status_bits.items()},
        pdcv2_enabled_in_reference=True, mfg0_sram_sleep_bits=[9, 13],
        hardware_power_or_memory_reachability_verified=False,
        note='Status bits and source configuration do not prove live rail, clock or MCU execution.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-dir', type=Path, required=True)
    parser.add_argument('--rpc-status', type=lambda s: int(s, 0), default=0xfff0fff0)
    parser.add_argument('--spm-status', type=lambda s: int(s, 0), default=0xf)
    args = parser.parse_args()
    try:
        if any(not 0 <= value <= 0xffffffff for value in (args.rpc_status, args.spm_status)):
            raise ValueError('register values must be unsigned32')
        result = audit(pinned_sources(args.source_dir),
            (ROOT / 'xnu/gpu/mali_csf_boot.c').read_text(), args.rpc_status, args.spm_status)
    except (ValueError, OSError) as exc:
        parser.exit(1, str(exc) + '\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
