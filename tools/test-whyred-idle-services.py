#!/usr/bin/env python3
"""Exercise masked idle waiting and bounded service lifecycle reporting."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('source', type=Path)
    ap.add_argument('--output', type=Path, required=True)
    ap.add_argument('--sanitize', choices=['undefined', 'address,undefined'])
    args = ap.parse_args()
    rels = ['osfmk/arm64/cpu.c', 'osfmk/arm64/cswitch.s',
            'osfmk/arm64/exception_asm.h', 'bsd/kern/kern_exec.c',
            'bsd/kern/kern_exit.c', 'bsd/kern/whyred_service_trace.h']
    texts = {r: (args.source / r).read_text() for r in rels}
    cpu = texts[rels[0]]
    start = cpu.index('static bool\nwhyred_idle_wait_pending(')
    end = cpu.index('\n}\n', start) + 3
    helper = cpu[start:end]
    if cpu.count('ipending = whyred_idle_wait_pending();') != 1:
        raise ValueError('The interrupt-stack timer path must use the masked helper')
    if 'wfe_to_deadline_or_interrupt(cid, ~0ULL, cpu_data_ptr, true)' in cpu:
        raise ValueError('Unmasked timer wait can corrupt the interrupt stack')
    # These contracts explain why interrupt-stack idle cannot run IRQ handlers.
    switch = texts[rels[1]].split('LEXT(Idle_context)', 1)[1].split('LEXT(Idle_load_context)', 1)[0]
    irq_stack = texts[rels[2]].split('.macro SWITCH_TO_INT_STACK', 1)[1].split('.endmacro', 1)[0]
    if 'CPU_ISTACKPTR' not in switch or 'CPU_ISTACKPTR' not in irq_stack:
        raise ValueError('Revisit stack-safety assumptions for changed assembly')
    exec_source = texts[rels[3]]
    for stage in ['EXEC', 'SPAWN']:
        call = f'whyred_service_event(p, WHYRED_SERVICE_{stage}, error, exec_done, 0, 0, 0);'
        if exec_source.count(call) != 1:
            raise ValueError('Missing exec/spawn result hook: ' + stage)
    spawn_hook = exec_source.index('whyred_service_event(p, WHYRED_SERVICE_SPAWN')
    if spawn_hook > exec_source.index('\t/* terminate the new task if exec failed  */'):
        raise ValueError('Spawn result must precede termination and reference cleanup')
    exit_source = texts[rels[4]]
    proc_exit = exit_source[exit_source.index('\nproc_exit(proc_t p)'):]
    if not (proc_exit.index('\tproc_unlock(p);\n\tpid = proc_getpid(p);') <
            proc_exit.index('whyred_service_event(p, WHYRED_SERVICE_EXIT') <
            proc_exit.index('dtrace_proc_exit(p)')):
        raise ValueError('Exit trace must run once after unlocking, with a live process')
    args.output.mkdir(parents=True, exist_ok=True)
    fixture = Path(__file__).with_name('whyred-idle-services-host.c')
    generated = fixture.read_text().replace('/* ACTUAL IDLE HELPER */', helper)
    header = texts[rels[5]].replace('#include <os/atomic_private.h>', '')
    generated = generated.replace('/* ACTUAL SERVICE HELPER */', header)
    source = args.output / 'idle-services-host.c'
    source.write_text(generated)
    binary = args.output / 'idle-services-host'
    cmd = [shutil.which('clang') or 'cc', '-std=c11', '-Wall', '-Wextra', '-Werror',
           '-O1', '-g', '-pthread', str(source.resolve()), '-o', str(binary.resolve())]
    if args.sanitize:
        cmd += ['-fsanitize=' + args.sanitize, '-fno-omit-frame-pointer']
    build = subprocess.run(cmd, capture_output=True, text=True)
    (args.output / 'compile.log').write_text(build.stdout + build.stderr)
    if build.returncode:
        raise SystemExit(build.stdout + build.stderr)
    run = subprocess.run([str(binary.resolve())], capture_output=True, text=True)
    (args.output / 'run.log').write_text(run.stdout + run.stderr)
    if run.returncode:
        raise SystemExit(run.stdout + run.stderr)
    result = json.loads(run.stdout)
    result.update(passed=True, sanitizers=args.sanitize,
                  source_sha256={r: hashlib.sha256((args.source / r).read_bytes()).hexdigest() for r in rels},
                  fixture_sha256=hashlib.sha256(fixture.read_bytes()).hexdigest(),
                  actual_kernel_functions=2, max_service_records=960,
                  hardware_irq_wakeup_tested=False)
    (args.output / 'report.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
