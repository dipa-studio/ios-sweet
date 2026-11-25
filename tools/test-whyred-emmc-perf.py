#!/usr/bin/env python3
"""Execute actual eMMC clock/batch/recovery/strategy code with modeled MMIO."""
import argparse
import ctypes
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

def function(text, name):
    match = re.search(r'^' + re.escape(name) + r'\(', text, re.M)
    if match is None:
        raise SystemExit('Missing kernel function: ' + name)
    start = text.rfind('\nstatic ', 0, match.start()) + 1
    begin = text.index('{', match.start())
    depth, end = 1, begin + 1
    while depth:
        depth += (text[end] == '{') - (text[end] == '}')
        end += 1
    return text[start:end]

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('source', type=Path)
    ap.add_argument('--output', type=Path, required=True)
    args = ap.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    driver_path = args.source / 'bsd/dev/whyred_emmc_pio_probe.c'
    perf_path = args.source / 'bsd/dev/whyred_emmc_perf.h'
    log_path = args.source / 'bsd/sys/whyred_boot_log.h'
    exports_path = args.source / 'bsd/sys/Makefile'
    exports = exports_path.read_text()
    xnu_exports = exports[exports.index('XNU_ONLY_EXPORTS ='):exports.index('EXPORT_MI_LIST')]
    if 'whyred_boot_log.h' not in xnu_exports.split():
        raise SystemExit('Quiet helper is not exported to other XNU subsystems')
    driver = driver_path.read_text()
    perf = perf_path.read_text()
    constants = '\n'.join(re.findall(r'^#define (?:SDHCI_|WHYRED_)[^\n]+', driver, re.M))
    (args.output / 'kernel-defines.h').write_text(constants + '\n')
    fragment = '\n'.join(function(driver, f) for f in (
        'whyred_emmc_wait_status', 'whyred_emmc_command',
        'whyred_emmc_log_msm_v5_snapshot', 'whyred_emmc_reset_data_path', 'whyred_emmc_read_sector'))
    fragment += '\n' + perf
    fragment += '\n' + '\n'.join(function(driver, f) for f in (
        'whyred_emmc_partition', 'whyred_emmc_strategy'))
    adaptations = {
        '__asm__ volatile("dsb sy" ::: "memory");': '__asm__ volatile("" ::: "memory");',
        '__builtin_arm_rsr64("CNTFRQ_EL0")': 'test_frequency',
    }
    for original, replacement in adaptations.items():
        if original not in fragment:
            raise SystemExit('Host adaptation anchor missing: ' + original)
        fragment = fragment.replace(original, replacement)
    (args.output / 'kernel-fragment.h').write_text(fragment)
    shutil.copyfile(log_path, args.output / log_path.name)
    fixture = Path(__file__).with_name('whyred-emmc-perf-host.c')
    wrapper = args.output / fixture.name
    shutil.copyfile(fixture, wrapper)
    library = args.output / ('emmc-perf.dll' if os.name == 'nt' else 'emmc-perf.so')
    cc = os.environ.get('CC') or shutil.which('clang') or 'cc'
    cmd = [cc, '-std=c11', '-Wall', '-Wextra', '-Werror', '-Wno-unused-function',
           '-O1', '-ffreestanding', '-fno-builtin', '-fno-stack-protector', '-shared',
           str(wrapper.resolve()), '-o', str(library.resolve())]
    env = os.environ.copy()
    env.pop('SDKROOT', None)
    env.pop('MACOSX_DEPLOYMENT_TARGET', None)
    if os.name == 'nt':
        cmd += ['-nostdlib', '-fuse-ld=lld', '-Wl,/noentry', '-Wl,/nodefaultlib']
    else:
        cmd += ['-fPIC']
        if sys.platform == 'darwin':
            sdk = subprocess.check_output(['xcrun', '--sdk', 'macosx', '--show-sdk-path'],
                                          text=True, env=env).strip()
            cmd += ['-isysroot', sdk]
    subprocess.run(cmd, check=True, env=env)
    lib = ctypes.CDLL(str(library.resolve()))
    lib.whyred_perf_host_checks.restype = ctypes.c_int
    result = lib.whyred_perf_host_checks()
    if result:
        raise SystemExit('eMMC host check failed at fixture line ' + str(result))
    count = lib.whyred_perf_check_count() + 1  # private-header export guard above
    report = dict(passed=True, checks=count, actual_kernel_functions=True,
                  hardware_emulated=False,private_header_export_guard=True,
                  source_sha256={p.relative_to(args.source).as_posix():
                      hashlib.sha256(p.read_bytes()).hexdigest()
                      for p in (driver_path, perf_path, log_path, exports_path)},
                  fixture_sha256=hashlib.sha256(fixture.read_bytes()).hexdigest(),
                  adaptations=adaptations,
                  coverage=['CMD23/CMD18 sizes 2..32 with guarded byte-exact data',
                      'invalid ranges/null/overflow before commands',
                      'command, data CRC, early-end and missing-end failures',
                      'GCC XO programming, delayed clock readback and rollback',
                      'preflight mismatch and multiblock rejection',
                      'runtime recovery/reread and unrecoverable rejection',
                      'completion resampled after a scheduling delay at deadline',
                      'late CMD17 FIFO readiness requires clean fresh status and full exact transfer',
                      'baseline CMD17 recovery and batch-then-baseline transient errors',
                      'CMD12 timeout latch reset, CMD13 retry and rejection of unsafe status',
                      'transient illegal STOP status requires a clean second CMD13 and fresh exact reread',
                      'persistent card errors, status timeout, inhibit, stale FIFO and failed reread reject I/O',
                      'actual block strategy/residuals and read-only bounds',
                      'log sampling and bounded telemetry'])
    (args.output / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    print('PASS:', count, 'eMMC/quiet-log checks; modeled MMIO, no hardware claim')

if __name__ == '__main__':
    main()
