#!/usr/bin/env python3
"""Compile and execute the exact new C policy/macros on the host, then replay the patch."""
import argparse
import ctypes as C
import hashlib
import json
import os
from pathlib import Path
import random
import re
import shutil
import subprocess
import sys


PREAMBLE = r'''
typedef int int32_t;
typedef unsigned long long uint64_t;
typedef int boolean_t;
typedef int kern_return_t;
typedef _Bool bool;
#define PROC_NULL ((proc_t)0)
#define TRUE 1
#define FALSE 0
#define NULL ((void *)0)
#define KERN_SUCCESS 0
#define MACRO_BEGIN do {
#define MACRO_END } while (0)
#define P_MEMSTAT_MEMLIMIT_ACTIVE_FATAL 1
#define P_MEMSTAT_MEMLIMIT_INACTIVE_FATAL 2
#define P_MEMSTAT_FATAL_MEMLIMIT 4
struct proc {
    const char *p_name;
    int32_t p_memstat_memlimit_active, p_memstat_memlimit_inactive, p_memstat_memlimit;
    unsigned int p_memstat_state;
};
typedef struct proc *proc_t;
typedef struct proc *task_t;
static int max_task_footprint_mb;
static int boot_present, boot_value, log_count;
static int memorystatus_highwater_enabled = 1;
static int test_active, ledger_calls, ledger_request, ledger_active, ledger_fatal, lock_depth, bad_lock;
static int strcmp(const char *a, const char *b) {
    while (*a && *a == *b) { ++a; ++b; }
    return (unsigned char)*a - (unsigned char)*b;
}
static int printf(const char *format, ...) { (void)format; ++log_count; return 0; }
static int PE_parse_boot_argn(const char *key, void *value, unsigned long long size) {
    (void)key; (void)size;
    if (!boot_present) return 0;
    *(int32_t *)value = boot_value;
    return 1;
}
static int proc_getpid(proc_t p) { (void)p; return 67; }
static task_t proc_task(proc_t p) { return p; }
static uint64_t get_task_phys_footprint(task_t t) { (void)t; return 3456789ULL; }
static kern_return_t task_get_phys_footprint_limit(task_t t, int *mb) { (void)t; *mb = 64; return 0; }
static void proc_list_lock(void) { ++lock_depth; }
static void proc_list_unlock(void) { --lock_depth; }
static boolean_t proc_jetsam_state_is_active_locked(proc_t p) { (void)p; return test_active; }
static kern_return_t task_set_phys_footprint_limit_internal(task_t task, int limit,
    int *old, boolean_t active, boolean_t fatal) {
    (void)task; (void)old;
    if (lock_depth != 1) ++bad_lock;
    ++ledger_calls; ledger_request = limit; ledger_active = active; ledger_fatal = fatal;
    return KERN_SUCCESS;
}
'''

WRAPPERS = r'''
#ifdef _WIN32
#define EXPORT __declspec(dllexport)
#else
#define EXPORT __attribute__((visibility("default")))
#endif
static const char *name_for(int name) {
    if (name == 0) return "driverkitd";
    if (name == 1) return "driverkitdx";
    if (name == 2) return "xpcproxy";
    return "Driverkitd";
}
EXPORT void test_budget(int boot, int present, int system_mb, int name,
    int active, int inactive, int fatalbits, int use_active, int *out) {
    max_task_footprint_mb = system_mb;
    boot_present = present;
    boot_value = boot;
    log_count = 0;
#if defined(ARM64_BOARD_CONFIG_SWEET)
    whyred_driverkitd_mem_mb = 0;
    whyred_driverkitd_boot_config();
#endif
    struct proc process;
    proc_t p = &process;
    p->p_name = name_for(name);
    p->p_memstat_state = 0x80;
    p->p_memstat_memlimit_active = -99;
    p->p_memstat_memlimit_inactive = -98;
    p->p_memstat_memlimit = -97;
    SET_ACTIVE_LIMITS_LOCKED(p, active, fatalbits & 1);
    SET_INACTIVE_LIMITS_LOCKED(p, inactive, fatalbits & 2);
#if defined(ARM64_BOARD_CONFIG_SWEET)
    whyred_driverkitd_log_limits(p, active, inactive, "host");
#endif
    boolean_t is_fatal;
    if (use_active) { CACHE_ACTIVE_LIMITS_LOCKED(p, is_fatal); }
    else { CACHE_INACTIVE_LIMITS_LOCKED(p, is_fatal); }
    out[0] = p->p_memstat_memlimit_active;
    out[1] = p->p_memstat_memlimit_inactive;
    out[2] = p->p_memstat_memlimit;
    out[3] = p->p_memstat_state;
    out[4] = is_fatal;
    out[5] = log_count;
#if defined(ARM64_BOARD_CONFIG_SWEET)
    out[6] = whyred_driverkitd_mem_mb;
#else
    out[6] = 0;
#endif
    /* A later user request that lowers both slots is clamped again. */
    SET_ACTIVE_LIMITS_LOCKED(p, 1, fatalbits & 1);
    SET_INACTIVE_LIMITS_LOCKED(p, 2, fatalbits & 2);
    if (use_active) { CACHE_ACTIVE_LIMITS_LOCKED(p, is_fatal); }
    else { CACHE_INACTIVE_LIMITS_LOCKED(p, is_fatal); }
    out[7] = p->p_memstat_memlimit_active;
    out[8] = p->p_memstat_memlimit_inactive;
    out[9] = p->p_memstat_memlimit;
    out[10] = p->p_memstat_state;
}
EXPORT int test_event(int name, int warning, int fatal) {
    struct proc process;
    proc_t p = &process;
    p->p_name = name_for(name);
    p->p_memstat_memlimit_active = 64;
    p->p_memstat_memlimit_inactive = 64;
    log_count = 0;
#if defined(ARM64_BOARD_CONFIG_SWEET)
    whyred_driverkitd_log_footprint(p, warning, 1, fatal);
#else
    (void)p; (void)warning; (void)fatal;
#endif
    return log_count;
}
EXPORT void test_proxy_exec(int boot, int system_mb, int final_name, int active, int inactive,
    int fatalbits, int use_active, int highwater, int *out) {
    max_task_footprint_mb = system_mb;
    boot_present = 1; boot_value = boot; log_count = 0;
    memorystatus_highwater_enabled = highwater;
    test_active = use_active;
    lock_depth = 0; bad_lock = 0; ledger_calls = 0;
#if defined(ARM64_BOARD_CONFIG_SWEET)
    whyred_driverkitd_mem_mb = 0;
    whyred_driverkitd_boot_config();
#endif
    struct proc process;
    proc_t p = &process;
    p->p_name = "xpcproxy";
    p->p_memstat_state = 0x80;
    SET_ACTIVE_LIMITS_LOCKED(p, active, fatalbits & 1);
    SET_INACTIVE_LIMITS_LOCKED(p, inactive, fatalbits & 2);
    boolean_t is_fatal;
    if (use_active) { CACHE_ACTIVE_LIMITS_LOCKED(p, is_fatal); }
    else { CACHE_INACTIVE_LIMITS_LOCKED(p, is_fatal); }
    out[0] = p->p_memstat_memlimit_active;
    out[1] = p->p_memstat_memlimit_inactive;
    ledger_request = p->p_memstat_memlimit > 0 ? p->p_memstat_memlimit : -1;
    ledger_active = use_active; ledger_fatal = is_fatal;
    /* Exec changes the actual image name. No second spawn SET occurs. */
    p->p_name = name_for(final_name);
#if defined(ARM64_BOARD_CONFIG_SWEET)
    memorystatus_whyred_driverkitd_exec(p);
#endif
    out[2] = p->p_memstat_memlimit_active;
    out[3] = p->p_memstat_memlimit_inactive;
    out[4] = p->p_memstat_memlimit;
    out[5] = p->p_memstat_state;
    out[6] = ledger_calls;
    out[7] = ledger_request;
    out[8] = ledger_active;
    out[9] = ledger_fatal;
    out[10] = lock_depth;
    out[11] = bad_lock;
}
'''


def run():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('source', type=Path, help='Patched XNU source root')
    ap.add_argument('--output', type=Path, required=True)
    ap.add_argument('--baseline', type=Path, help='Optional original XNU source root')
    ap.add_argument('--patch', type=Path, help='Optional patch to replay against baseline')
    args = ap.parse_args()
    SOURCE = args.source / 'bsd/kern/kern_memorystatus.c'
    OUT = args.output
    PATCH = args.patch
    OUT.mkdir(parents=True, exist_ok=True)
    source = SOURCE.read_text(encoding='utf-8')
    policy = source[source.index('/* WHYRED_DRIVERKITD_POLICY_BEGIN */'):
                    source.index('/* WHYRED_DRIVERKITD_POLICY_END */')]
    macro_start = source.index('#define SET_ACTIVE_LIMITS_LOCKED')
    macro_end = source.index('\n/*', source.index('#define CACHE_INACTIVE_LIMITS_LOCKED'))
    macros = source[macro_start:macro_end]
    exec_policy = source[source.index('/* WHYRED_DRIVERKITD_EXEC_BEGIN */'):
                         source.index('/* WHYRED_DRIVERKITD_EXEC_END */')]
    cc = os.environ.get('CC') or shutil.which('clang') or 'cc'
    env = os.environ.copy()
    env.pop('SDKROOT', None)
    env.pop('MACOSX_DEPLOYMENT_TARGET', None)
    host_sdk = None
    if sys.platform == 'darwin':
        host_sdk = subprocess.check_output(['xcrun', '--sdk', 'macosx', '--show-sdk-path'],
            text=True, env=env).strip()
    results = []
    for board in (False, True):
        wrapper = OUT / ('policy-sweet.c' if board else 'policy-other.c')
        wrapper.write_text(PREAMBLE + policy + '\n' + macros + '\n' + exec_policy + '\n' + WRAPPERS,
                           encoding='utf-8', newline='\n')
        library = wrapper.with_suffix('.dll' if sys.platform == 'win32' else '.so')
        command = [cc, '-std=c11', '-O2', '-Wall', '-Wextra', '-Werror',
            '-Wno-unused-function', '-Wno-unused-variable', '-ffreestanding',
            '-fno-stack-protector', '-shared', str(wrapper.resolve()), '-o', str(library.resolve())]
        if board:
            command += ['-DARM64_BOARD_CONFIG_SWEET=1']
        if sys.platform == 'win32':
            command += ['-nostdlib', '-fuse-ld=lld', '-Wl,/noentry', '-Wl,/nodefaultlib']
        else:
            command += ['-fPIC']
            if host_sdk:
                command += ['-isysroot', host_sdk]
        subprocess.run(command, check=True, env=env)
        lib = C.CDLL(str(library.resolve()))
        lib.test_budget.argtypes = [C.c_int] * 8 + [C.POINTER(C.c_int)]
        lib.test_budget.restype = None
        lib.test_event.argtypes = [C.c_int] * 3
        lib.test_event.restype = C.c_int
        lib.test_proxy_exec.argtypes = [C.c_int] * 8 + [C.POINTER(C.c_int)]
        lib.test_proxy_exec.restype = None
        checked = 0

        def check(boot, present, default, name, active, inactive, fatalbits, use_active):
            nonlocal checked
            out = (C.c_int * 11)()
            lib.test_budget(boot, present, default, name, active, inactive, fatalbits, use_active, out)
            floor = boot if board and present and 0 <= boot <= 512 else 0

            def expected(limit):
                effective = limit if limit > 0 else default
                return floor if name == 0 and 0 < effective < floor else limit

            a, i = expected(active), expected(inactive)
            selected_fatal = bool(fatalbits & (1 if use_active else 2))
            state = 0x80 | fatalbits | (4 if selected_fatal else 0)
            boot_logs = int(board and present and boot != 0)
            expected_logs = boot_logs + int(name == 0 and floor > 0)
            expected_out = [a, i, a if use_active else i, state, int(selected_fatal),
                expected_logs, floor, expected(1), expected(2),
                expected(1) if use_active else expected(2), state]
            assert list(out) == expected_out, (board, boot, present, default, name,
                active, inactive, fatalbits, use_active, list(out), expected_out)
            checked += 1

        # Deterministic boundaries: absent/disabled/invalid bootarg, -1/0 defaults,
        # unlimited default, larger explicit/default limits, exact name, both states/flags.
        for boot in (-2147483648, -1, 0, 1, 64, 512, 513, 2147483647):
            for present in (0, 1):
                for default in (0, 32, 64, 128, 1024):
                    for name in (0, 1, 2, 3):
                        for active, inactive in ((-1, -1), (0, 0), (1, 2), (32, 128), (1024, 32)):
                            for fatal in range(4):
                                for use_active in (0, 1):
                                    check(boot, present, default, name, active, inactive, fatal, use_active)
        rng = random.Random(152)
        for _ in range(2000):
            check(rng.randrange(-20, 550), rng.randrange(2), rng.choice((0, 50, 512)),
                rng.randrange(4), rng.randrange(-5, 1200), rng.randrange(-5, 1200),
                rng.randrange(4), rng.randrange(2))
        for name in range(4):
            for warning in (0, 1):
                for fatal in (0, 1):
                    assert lib.test_event(name, warning, fatal) == int(board and name == 0)
        exec_cases = 0
        for boot in (-1, 0, 1, 64, 512, 513):
            floor = boot if board and 0 <= boot <= 512 else 0
            for default in (0, 50, 128):
                for active, inactive in ((-1, -1), (0, 0), (1, 2), (32, 128), (1024, 32)):
                    for final_name in (0, 1, 2):
                        for fatal in range(4):
                            for use_active in (0, 1):
                                for highwater in (0, 1):
                                    def raised(limit):
                                        effective = limit if limit > 0 else default
                                        return floor if final_name == 0 and 0 < effective < floor else limit
                                    out = (C.c_int * 12)()
                                    lib.test_proxy_exec(boot, default, final_name, active, inactive,
                                                        fatal, use_active, highwater, out)
                                    a, i = raised(active), raised(inactive)
                                    selected = a if use_active else i
                                    old_selected = active if use_active else inactive
                                    selected_fatal = int(bool(fatal & (1 if use_active else 2)))
                                    runs = int(final_name == 0 and floor > 0)
                                    writes = runs * highwater * int(selected != old_selected)
                                    ledger_raw = selected if writes else old_selected
                                    expected_out = [active, inactive, a, i, selected, 0x80 | fatal | (4 if selected_fatal else 0),
                                        writes, ledger_raw if ledger_raw > 0 else -1, use_active, selected_fatal, 0, 0]
                                    assert list(out) == expected_out, ('proxy-exec', board, boot, default, final_name,
                                        active, inactive, fatal, use_active, highwater, list(out), expected_out)
                                    exec_cases += 1
        results.append({'board': 'SWEET' if board else 'other', 'budget_cases': checked,
                        'event_cases': 16, 'proxy_exec_cases': exec_cases, 'result': 'passed'})

    # Integration checks tied to the real source, rather than host stubs.
    for name in ('memlimit_active', 'memlimit_inactive'):
        stores = re.findall(r'p_memstat_' + name + r'\s*=(?!=)([^;]+);', source)
        assert len(stores) == 1 and 'whyred_driverkitd_memlimit' in stores[0], (name, stores)
    spawn = source[source.index('memorystatus_update(proc_t '):source.index('memorystatus_update(proc_t ') + 16000]
    assert spawn.index('whyred_driverkitd_log_limits') < spawn.index('task_set_phys_footprint_limit_internal')
    setter = source[source.index('memorystatus_set_memlimit_properties_internal(proc_t p, memorystatus_memlimit_properties_t *p_entry)\n{'):]
    assert setter.index('whyred_driverkitd_log_limits') < setter.index('task_set_phys_footprint_limit_internal')
    assert source.count('whyred_driverkitd_log_limits(p,') == 3
    assert source.count('whyred_driverkitd_log_footprint(p,') == 1
    original = None
    if args.baseline:
        original = (args.baseline / 'bsd/kern/kern_memorystatus.c').read_text(encoding='utf-8')
        fatal_start = original.index('\tif (memlimit_is_fatal) {', original.index('memorystatus_on_ledger_footprint_exceeded('))
        fatal_end = original.index('\n}\n', fatal_start)
        assert original[fatal_start:fatal_end] in source, 'Original fatal/soft kill behavior changed'
    assert 'os_reason_create(OS_REASON_JETSAM, JETSAM_REASON_MEMORY_PERPROCESSLIMIT)' in source
    assert 'memorystatus_kill_process_sync(proc_getpid(p), kMemorystatusKilledPerProcessLimit, jetsam_reason)' in source
    exec_source = (args.source / 'bsd/kern/kern_exec.c').read_text(encoding='utf-8')
    imgact = exec_source.index('exec_mach_imgact(struct image_params *imgp)')
    spawn_activation = exec_source.index('\terror = exec_activate_image(imgp);', exec_source.index('posix_spawn('))
    spawn_update = exec_source.index('memorystatus_update(p,', spawn_activation)
    # The success path installs the accounting name inside exec_mach_imgact;
    # posix_spawn calls the limit setter only after exec_activate_image returns.
    accounting = exec_source.index('Remember file name for accounting.', imgact)
    success_name = exec_source.index('\tset_proc_name(imgp, p);\n', accounting)
    activator_end = exec_source.index('\n/*\n * exec_activate_image', success_name)
    assert imgact < accounting < success_name < activator_end < spawn_activation < spawn_update
    common = exec_source[exec_source.index('proc_footprint_entitlement_hacks(proc_t p, task_t task)'):]
    common = common[:common.index('\n}\n')]
    assert 'memorystatus_whyred_driverkitd_exec(p);' in common and 'JETSAM_SET' not in common
    assert exec_source.count('memorystatus_whyred_driverkitd_exec(p);') == 1
    assert exec_source.count('proc_footprint_entitlement_hacks(p, new_task);') == 2
    for activation in (spawn_activation, exec_source.index('\terror = exec_activate_image(imgp);', spawn_activation + 1)):
        task_switch = exec_source.index('p = proc_exec_switch_task(', activation)
        refloor = exec_source.index('proc_footprint_entitlement_hacks(p, new_task);', task_switch)
        user_wait_release = exec_source.index('task_clear_return_wait(', refloor)
        assert activation < task_switch < refloor < user_wait_release

    replay_result = 'not requested'
    if PATCH:
        assert original is not None, '--patch requires --baseline'
        replay = OUT / 'apply-check/xnu/bsd/kern'
        replay.mkdir(parents=True, exist_ok=True)
        (replay / 'kern_memorystatus.c').write_text(original, encoding='utf-8', newline='\n')
        extra_files = ('bsd/kern/kern_exec.c', 'bsd/sys/kern_memorystatus.h')
        for rel in extra_files:
            dest = replay.parents[1] / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes((args.baseline / rel).read_bytes())
        git_apply = ['git', '-c', 'core.autocrlf=false', 'apply']
        subprocess.run(git_apply + ['--check', str(PATCH.resolve())], cwd=replay.parents[1], check=True)
        subprocess.run(git_apply + [str(PATCH.resolve())], cwd=replay.parents[1], check=True)
        assert (replay / 'kern_memorystatus.c').read_bytes() == SOURCE.read_bytes()
        for rel in extra_files:
            assert (replay.parents[1] / rel).read_bytes() == (args.source / rel).read_bytes()
        replay_result = 'passed'
    report = {'host_policy_and_macro_execution': results, 'integration_checks': 'passed',
        'patch_apply_check': replay_result,
        'compiled_full_kernel': False, 'runtime_device_tested': False,
        'source_sha256': hashlib.sha256(SOURCE.read_bytes()).hexdigest()}
    if PATCH:
        report['patch_sha256'] = hashlib.sha256(PATCH.read_bytes()).hexdigest()
    (OUT / 'validation.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    run()
