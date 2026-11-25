#!/usr/bin/env python3
"""Test real RAMFS allocation/error/reclaim code with host VM/VFS adapters."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess


def function(text, name):
    match = re.search(r'^' + re.escape(name) + r'\(', text, re.M)
    if match is None:
        raise ValueError('Missing function: ' + name)
    start = text.rfind('\nstatic ', 0, match.start()) + 1
    begin = text.index('{', match.start())
    depth, end = 1, begin + 1
    while depth:
        depth += (text[end] == '{') - (text[end] == '}')
        end += 1
    return text[start:end]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--sanitize', choices=['undefined', 'address,undefined'])
    args = parser.parse_args()
    source = args.source / 'bsd/miscfs/whyred_ramfs/ramfs.c'
    text = source.read_text()
    names = ['ramfs_dir_find', 'ramfs_logd_classify_locked', 'ramfs_dir_add', 'ramfs_logd_limit_from_arg', 'ramfs_file_limit', 'ramfs_pressure_name', 'ramfs_pressure_record_locked', 'ramfs_pressure_take_locked', 'ramfs_pressure_emit',
             'ramfs_page_alloc', 'ramfs_page_free', 'ramfs_reserve_slots', 'ramfs_free_pages',
             'ramfs_xattr_free', 'ramfs_hash_insert', 'ramfs_hash_remove', 'ramfs_node_free',
             'ramfs_grow_slots', 'ramfs_store', 'ramfs_fetch', 'ramfs_resize', 'ramfs_setattr', 'ramfs_write',
             'ramfs_inactive', 'ramfs_reclaim', 'ramfs_xattr_find', 'ramfs_getxattr', 'ramfs_listxattr']
    extracted = {name: function(text, name) for name in names}
    for name in ['ramfs_make', 'ramfs_link', 'ramfs_rename_common', 'whyred_ramfs_seed_one']:
        if 'ramfs_dir_add(' not in function(text, name):
            raise ValueError('Namespace path bypasses classified insertion: ' + name)
    if 'ramfs_logd_classify_locked(dir, de, node)' not in extracted['ramfs_dir_add']:
        raise ValueError('Missing common cache-classification hook')
    rename = function(text, 'ramfs_rename_common')
    if (rename.count('ramfs_logd_classify_locked(tdir, tde, node)') != 2 or
            'ramfs_logd_classify_locked(fdir, fde, victim)' not in rename):
        raise ValueError('Replacement/swap rename bypasses cache classification')
    declarations = re.findall(r'^#define RAMFS_LOGD_.*$', text, re.M)
    for kind, name in [('struct', 'ramfs_dirent'), ('struct', 'ramfs_xattr'),
                       ('struct', 'ramfs_node'), ('enum', 'ramfs_pressure_reason'),
                       ('struct', 'ramfs_pressure_event'), ('struct', 'ramfs_mount')]:
        start = text.index(kind + ' ' + name + ' {')
        declarations.append(text[start:text.index('\n};', start) + 3])
    gate = 'PE_parse_boot_argn("whyred-ramfs-trace", &trace, sizeof(trace)) && trace == 1'
    if gate not in text or '#if DEVELOPMENT || DEBUG\n\tuint32_t trace = 0;' not in text:
        raise ValueError('Missing default-off development boot gate')
    if '#define WHYRED_RAMFS_DATA_LIMIT (128ULL * 1024 * 1024)' not in text:
        raise ValueError('Unexpected data quota change')
    if 'MIN(max_mem / 4, WHYRED_RAMFS_DATA_LIMIT) / PAGE_SIZE' not in text:
        raise ValueError('Unexpected mount quota policy')
    if 'rm->rm_trace && PE_parse_boot_argn("whyred-ramfs-top", &top, sizeof(top)) && top == 1' not in text:
        raise ValueError('Missing separate default-off owner gate')
    if ('PE_parse_boot_argn("whyred-logd-file-mb", &logd_file_mib, sizeof(logd_file_mib))' not in text or
            'ramfs_logd_limit_from_arg(logd_file_mib, rm->rm_max_pages)' not in text):
        raise ValueError('Missing opt-in logd limit configuration')
    if extracted['ramfs_setattr'].index('final_size > ramfs_file_limit') > extracted['ramfs_setattr'].index('ramfs_resize(node, size)'):
        raise ValueError('Owner/size policy must be checked before attribute mutations')
    seed = function(text, 'whyred_ramfs_seed_one')
    pageout = function(text, 'ramfs_pageout')
    for name, body in [('seed', seed), ('pageout', pageout)]:
        if 'ramfs_pressure_take_locked(rm, &pressure)' not in body:
            raise ValueError('Unobserved store failure in ' + name)
        if body.index('ramfs_pressure_emit(&pressure)') < body.index('lck_mtx_unlock(&rm->rm_lock)'):
            raise ValueError('Logging under mount lock in ' + name)
    fixture = Path(__file__).with_name('whyred-ramfs-pressure-host.c')
    generated = fixture.read_text().replace('/* ACTUAL RAMFS DECLARATIONS */', '\n'.join(declarations))
    generated = generated.replace('/* ACTUAL RAMFS FUNCTIONS */', '\n\n'.join(extracted.values()))
    args.output.mkdir(parents=True, exist_ok=True)
    generated_path = args.output / 'ramfs-pressure.c'
    generated_path.write_text(generated)
    binary = args.output / 'ramfs-pressure'
    command = [shutil.which('clang') or 'cc', '-std=c11', '-Wall', '-Wextra', '-Werror',
               '-Wno-unused-function', '-O1', '-g', str(generated_path.resolve()), '-o', str(binary.resolve())]
    if args.sanitize:
        command += ['-fsanitize=' + args.sanitize, '-fno-omit-frame-pointer']
    build = subprocess.run(command, capture_output=True, text=True)
    (args.output / 'compile.log').write_text(build.stdout + build.stderr)
    if build.returncode:
        raise SystemExit(build.stdout + build.stderr)
    run = subprocess.run([str(binary.resolve())], capture_output=True, text=True)
    (args.output / 'run.log').write_text(run.stdout + run.stderr)
    if run.returncode:
        raise SystemExit(f'Host check exit {run.returncode}\n' + run.stdout + run.stderr)
    count = int(re.search(r'PASS: (\d+)', run.stdout)[1])
    report = {'passed': True, 'checks': count, 'sanitizers': args.sanitize,
              'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
              'function_sha256': {n: hashlib.sha256(s.encode()).hexdigest() for n, s in extracted.items()},
              'fixture_sha256': hashlib.sha256(fixture.read_bytes()).hexdigest(),
              'actual_kernel_functions': True, 'hardware_emulated': False,
              'limitations': 'Host allocator/lock/uio/vnode adapters; no kernel scheduling, UBC, VM pressure or VFS reference-count emulation'}
    (args.output / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    print(run.stdout.strip())


if __name__ == '__main__':
    main()
