#!/usr/bin/env python3
"""Exercise the real host setter and commpage update across target configurations."""
import argparse
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
    if not match:
        raise ValueError('Missing kernel function: ' + name)
    start = text.rfind('\n', 0, text.rfind('\n', 0, match.start())) + 1
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
    paths = ['osfmk/kern/host.c', 'osfmk/arm/commpage/commpage.c']
    texts = [(args.source / p).read_text() for p in paths]
    setter = function(texts[0], 'host_set_multiuser_config_flags')
    update = function(texts[1], 'commpage_update_multiuser_config')
    fixture = r'''
#include <stdint.h>
#include <stddef.h>
#include <stdio.h>
typedef int kern_return_t;
typedef void *host_priv_t;
#define HOST_PRIV_NULL NULL
#define KERN_INVALID_ARGUMENT 4
#define KERN_SUCCESS 0
#define KERN_NOT_SUPPORTED 46
static void *commPagePtr;
static uint32_t word;
static unsigned checks;
#define _COMM_PAGE_MULTIUSER_CONFIG ((uintptr_t)&word)
#define _COMM_PAGE_RW_OFFSET 0
#define CHECK(c) do { checks++; if (!(c)) { fprintf(stderr,"failure line %d\n",__LINE__); return 1; } } while (0)
''' + update + '\n' + setter + r'''
int main(void) {
    for (unsigned i = 0; i < 40; i++) {
        uint32_t flags = i == 0 ? 0 : i == 1 ? 501 : i == 2 ? 0x800001f5 : 0x9e3779b9U * i;
        word = 0x12345678; commPagePtr = &word;
#if defined(XNU_TARGET_OS_OSX) && (!defined(ARM64_BOARD_CONFIG_SWEET) || !ARM64_BOARD_CONFIG_SWEET)
        CHECK(host_set_multiuser_config_flags(NULL, flags) == KERN_NOT_SUPPORTED);
        CHECK(host_set_multiuser_config_flags((void *)1, flags) == KERN_NOT_SUPPORTED);
        CHECK(word == 0x12345678);
#else
        CHECK(host_set_multiuser_config_flags(NULL, flags) == KERN_INVALID_ARGUMENT);
        CHECK(word == 0x12345678);
        CHECK(host_set_multiuser_config_flags((void *)1, flags) == KERN_SUCCESS);
        CHECK(word == flags);
        commPagePtr = NULL; word = 0x12345678;
        CHECK(host_set_multiuser_config_flags((void *)1, flags) == KERN_SUCCESS);
        CHECK(word == 0x12345678);
#endif
    }
    printf("PASS: %u real host/commpage checks\n", checks);
    return 0;
}
'''
    source = args.output / 'multiuser.c'
    source.write_text(fixture)
    configurations = {
        'sweet-macos': ['-DXNU_TARGET_OS_OSX', '-DARM64_BOARD_CONFIG_SWEET=1'],
        'macos': ['-DXNU_TARGET_OS_OSX'],
        'macos-sweet-off': ['-DXNU_TARGET_OS_OSX', '-DARM64_BOARD_CONFIG_SWEET=0'],
        'ios': [],
        'sweet-ios': ['-DARM64_BOARD_CONFIG_SWEET=1'],
    }
    results = []
    # The full build invokes this from a kernel-only SDK environment.
    # These executables are native userspace tests, with normal libc headers.
    env = os.environ.copy()
    env.pop('SDKROOT', None)
    env.pop('MACOSX_DEPLOYMENT_TARGET', None)
    host_flags = []
    if sys.platform == 'darwin':
        sdk = subprocess.check_output(['xcrun', '--sdk', 'macosx', '--show-sdk-path'],
                                      text=True, env=env).strip()
        host_flags = ['-isysroot', sdk]
    for name, defines in configurations.items():
        binary = args.output / name
        build = subprocess.run([shutil.which('clang') or 'cc', '-std=c11', '-Wall', '-Wextra',
                                '-Werror', '-fsanitize=undefined', *host_flags, *defines, str(source.resolve()),
                                '-o', str(binary.resolve())], capture_output=True, text=True, env=env)
        (args.output / (name + '-compile.log')).write_text(build.stdout + build.stderr)
        if build.returncode:
            raise SystemExit(build.stderr)
        run = subprocess.run([str(binary.resolve())], capture_output=True, text=True, env=env)
        (args.output / (name + '-run.log')).write_text(run.stdout + run.stderr)
        if run.returncode:
            raise SystemExit(name + ': ' + run.stderr)
        results.append(dict(configuration=name, passed=True,
                            checks=int(re.search(r'PASS: (\d+)', run.stdout)[1])))
    report = dict(passed=True, checks=sum(r['checks'] for r in results), configurations=results,
                  actual_kernel_functions=True, source_sha256={p: hashlib.sha256(t.encode()).hexdigest()
                                                              for p, t in zip(paths, texts)},
                  function_sha256={n: hashlib.sha256(t.encode()).hexdigest() for n, t in
                                   [('host_set_multiuser_config_flags', setter),
                                    ('commpage_update_multiuser_config', update)]},
                  limitations='Host port/commPage address adapters; MIG authorization, kernel mappings and device userspace not emulated')
    (args.output / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    print('PASS:', report['checks'], 'real host/commpage checks across', len(results), 'configurations')


if __name__ == '__main__':
    main()
