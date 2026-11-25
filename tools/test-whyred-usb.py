#!/usr/bin/env python3
"""Run real whyred USB board/core code against modeled MMIO and kernel services."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess


def function(text, name):
    match = re.search(r'^' + re.escape(name) + r'\(', text, re.M)
    if not match:
        raise ValueError('Missing function ' + name)
    start = text.rfind('\nstatic ', 0, match.start()) + 1
    if name in ('sweet_usb_probe', 'sweet_log_copy', 'sweet_log_position', 'sweet_log_append'):
        start = text.rfind('\n', 0, match.start() - 1) + 1
    begin = text.index('{', match.start())
    depth, end = 1, begin + 1
    while depth:
        depth += (text[end] == '{') - (text[end] == '}')
        end += 1
    return text[start:end]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--sanitize', choices=['undefined', 'address,undefined'])
    args = parser.parse_args()
    driver = args.source / 'bsd/dev/sweet_usb.c'
    hardware = args.source / 'bsd/dev/whyred_usb_hw.h'
    startup = args.source / 'bsd/kern/bsd_init.c'
    ring = args.source / 'bsd/dev/sweet_ufs.c'
    text = driver.read_text()
    hook = startup.read_text()
    ring_text = ring.read_text()
    probe = function(text, 'sweet_usb_probe')
    if 'int mode = 0;' not in probe or 'PE_parse_boot_argn("whyred-usb"' not in probe:
        raise ValueError('USB must be explicitly opt-in')
    if 'os_atomic_cmpxchg(&usb_attempted, 0, 1, acq_rel)' not in probe:
        raise ValueError('Missing once-only startup')
    net = hook.index('\tnet_init_run();')
    usb = hook.index('\tsweet_usb_probe();')
    root = hook.index('\tinittodr(0);')
    if not net < usb < root:
        raise ValueError('USB must start after the networking stack and before root discovery')
    if re.search(r'\b(?:sweet_ufs_init|sweet_log_start|ufs_write_blocks)\s*\(', text):
        raise ValueError('USB must not initialize UFS or persistent logging')
    names = ['sweet_usb_probe', 'ud_snapshot', 'ud_fail', 'ud_epcmd', 'ud_start_trb', 'ud_start',
             'ud_start_setup', 'ud_stall', 'ud_string', 'ud_configuration',
             'ud_notify_connected', 'ud_configure', 'ud_setup', 'ud_rx_arm',
             'ud_rx_done', 'ud_tx_kick_locked', 'ud_if_output', 'ud_link_event',
             'ud_data_stop', 'ud_link_ready', 'ud_control_reset', 'ud_event',
             'ud_thread', 'ud_log_thread', 'sweet_usb_gadget_start']
    functions = {n: function(text, n) for n in names}
    if re.search(r'\b(?:dwc_wr|whyred_usb_write|ud_epcmd|ud_sync|delay)\s*\(', functions['ud_snapshot']):
        raise ValueError('Snapshots must not write/acknowledge hardware, issue commands or change DMA ownership')
    if ('ud_snapshot(0);' not in text or 'ud_snapshot(1);' not in text or
            'clock_interval_to_deadline(1, NSEC_PER_SEC, &next_snapshot)' not in functions['ud_thread']):
        raise ValueError('Missing startup snapshots or one-second event-thread sampling')
    for n in ['sweet_log_append', 'sweet_log_copy', 'sweet_log_position']:
        functions[n] = function(ring_text, n)
    definitions = '\n'.join(s for s in text.splitlines() if re.match(r'^#define\s+\w', s))
    declarations = []
    start = text.index('static struct {')
    declarations.append(text[start:text.index('} ud;', start) + len('} ud;')])
    for marker in ['static const uint8_t ud_dev_desc', 'static const uint8_t ud_cfg_desc',
                   'static const char *const ud_strings', 'static const uint8_t ud_phone_mac',
                   'static const uint8_t ud_qualifier']:
        start = text.index(marker)
        declarations.append(text[start:text.index(';', start) + 1])
    source = '\n\n'.join(functions.values())
    hardware_text = hardware.read_text()
    board_helpers = {n: function(hardware_text, n) for n in
                     ['whyred_usb_hw_prepare', 'whyred_usb_hw_rollback',
                      'whyred_usb_hw_select_utmi', 'whyred_usb_hw_release_test']}
    assembly = '__asm__ volatile ("dsb sy" ::: "memory");'
    adaptations = {'startup_dsb_replaced_with_host_barrier': source.count(assembly)}
    source = source.replace(assembly, 'host_barrier();')
    if '__asm__' in source:
        raise ValueError('Undeclared host adaptation')
    fixture = Path(__file__).with_name('whyred-usb-host.c')
    generated = fixture.read_text().replace('/* ACTUAL CONSTANTS */', definitions)
    generated = generated.replace('/* ACTUAL DECLARATIONS */', '\n'.join(declarations))
    generated = generated.replace('/* ACTUAL FUNCTIONS */', source)
    args.output.mkdir(parents=True, exist_ok=True)
    out = args.output / 'usb-host.c'
    out.write_text(generated)
    shutil.copyfile(hardware, args.output / hardware.name)
    binary = args.output / 'usb-host'
    command = [shutil.which('clang') or 'cc', '-std=c11', '-Wall', '-Wextra', '-Werror',
               '-Wno-unused-function', '-O1', '-g', str(out.resolve()), '-o', str(binary.resolve())]
    if args.sanitize:
        command += ['-fsanitize=' + args.sanitize, '-fno-omit-frame-pointer']
    build = subprocess.run(command, capture_output=True, text=True)
    (args.output / 'compile.log').write_text(build.stdout + build.stderr)
    if build.returncode:
        raise SystemExit(build.stdout + build.stderr)
    run = subprocess.run([str(binary.resolve())], capture_output=True, text=True)
    (args.output / 'run.log').write_text(run.stdout + run.stderr)
    if run.returncode:
        raise SystemExit(f'USB host exit {run.returncode}\n' + run.stdout + run.stderr)
    count = int(re.search(r'PASS: (\d+)', run.stdout)[1])
    report = {'passed': True, 'checks': count, 'sanitizers': args.sanitize,
              'source_sha256': {p.relative_to(args.source).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                                for p in (driver, hardware, startup, ring)},
              'function_sha256': {n: hashlib.sha256(s.encode()).hexdigest() for n, s in functions.items()},
              'board_helper_sha256': {n: hashlib.sha256(s.encode()).hexdigest() for n, s in board_helpers.items()},
              'actual_board_helpers': len(board_helpers),
              'fixture_sha256': hashlib.sha256(fixture.read_bytes()).hexdigest(),
              'adaptations': adaptations, 'actual_kernel_functions': len(functions),
              'hardware_emulated': False, 'mmio_modeled': True,
              'limitations': 'Modeled MMIO/cache boundaries/mbufs/sockets/threads; no physical USB, DMA cache coherence, SMMU or real host-stack emulation'}
    (args.output / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    print(run.stdout.strip())


if __name__ == '__main__':
    main()
