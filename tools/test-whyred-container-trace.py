#!/usr/bin/env python3
"""Execute the real opt-in ARM64 trace helper with mocked copyin/vnode services."""
import argparse
import ctypes
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('source', type=Path)
    ap.add_argument('--output', type=Path, required=True)
    args = ap.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    source = args.source / 'bsd/dev/arm/whyred_container_trace.h'
    hook = args.source / 'bsd/dev/arm/systemcalls.c'
    master = args.source / 'bsd/kern/syscalls.master'
    text = source.read_text(encoding='utf-8')
    calls = {}
    for line in master.read_text(encoding='utf-8').splitlines():
        m = re.match(r'\s*(\d+)\s+.*?\{\s*\w[\w\s*]*?\s+(\w+)\((.*?)\)', line)
        if not m:
            continue
        number, name, params = m.groups()
        name = name.removeprefix('sys_')
        if name != 'nosys':
            calls[name] = (int(number), [] if params == 'void' else params.split(','))
    defs, entries = [], []
    checks = 0
    for name, p0, p1, fd in re.findall(r'^\s*CT\((\w+), (-?\d+), (-?\d+), (-?\d+)\);', text, re.M):
        if name not in calls:
            raise ValueError('No syscall ABI for ' + name)
        number, params = calls[name]
        indexes = list(map(int, (p0, p1, fd)))
        for index in indexes:
            if index >= len(params):
                raise ValueError('Argument outside ABI for ' + name)
        for index in indexes[:2]:
            if index >= 0 and not re.search(r'\b(?:path\d*|from|to|src|dst|link)\b', params[index]):
                raise ValueError('Not a pathname argument: ' + name + ':' + params[index])
        if indexes[2] >= 0 and 'fd' not in params[indexes[2]]:
            raise ValueError('Not a descriptor argument: ' + name)
        defs.append(f'#define SYS_{name} {number}')
        entries.append(f'sysent[{number}].sy_narg = {len(params)};')
        checks += 1
    integration = hook.read_text(encoding='utf-8')
    if integration.count('whyred_container_trace_error(proc, uthread,') != 2:
        raise ValueError('Both ARM return paths must call the trace helper')
    for state in ('state', 'regs'):
        call = f'whyred_container_trace_error(proc, uthread, {state}, code, error);'
        ret = f'arm_prepare_syscall_return(callp, {state}, uthread, error);'
        if integration.index(call) > integration.index(ret):
            raise ValueError('Tracing must precede return-register preparation')
    (args.output / 'syscall-defines.h').write_text('\n'.join(defs) + '\n')
    (args.output / 'syscall-init.h').write_text('\n'.join(entries) + '\n')
    shutil.copyfile(source, args.output / source.name)
    fixture = Path(__file__).with_name('whyred-container-trace-host.c')
    shutil.copyfile(fixture, args.output / fixture.name)
    library = args.output / ('container-trace.dll' if os.name == 'nt' else 'container-trace.so')
    cc = os.environ.get('CC') or shutil.which('clang') or 'cc'
    cmd = [cc, '-std=c11', '-Wall', '-Wextra', '-Werror', '-Wno-unused-function', '-O1',
           '-ffreestanding', '-fno-builtin', '-fno-stack-protector', '-shared',
           str((args.output / fixture.name).resolve()), '-o', str(library.resolve())]
    if os.name == 'nt':
        cmd += ['-nostdlib', '-fuse-ld=lld', '-Wl,/noentry', '-Wl,/nodefaultlib']
    else:
        cmd += ['-fPIC']
    build = subprocess.run(cmd, capture_output=True, text=True)
    (args.output / 'compile.log').write_text(build.stdout + build.stderr)
    if build.returncode:
        raise SystemExit(build.stdout + build.stderr)
    lib = ctypes.CDLL(str(library.resolve()))
    lib.whyred_container_host_checks.restype = ctypes.c_int
    lib.whyred_container_check_count.restype = ctypes.c_uint
    failure = lib.whyred_container_host_checks()
    if failure:
        raise SystemExit('Actual helper check failed at fixture line ' + str(failure))
    result = dict(status='passed', host_checks=lib.whyred_container_check_count(), max_reports=256)
    result.update(abi_descriptors=checks, integration_hooks=2,
                  source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
                  systemcalls_sha256=hashlib.sha256(hook.read_bytes()).hexdigest(),
                  syscall_abi_sha256=hashlib.sha256(master.read_bytes()).hexdigest())
    (args.output / 'report.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
