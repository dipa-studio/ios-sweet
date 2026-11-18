#!/usr/bin/env python3
"""Re-run xnu compile commands from a CI log locally (syntax check only).

  xnu-cc.py LOG BUILDTREE [FILTER ...]

LOG        `gh run view --log` output of an xnu.yml run (VERBOSE=YES make)
BUILDTREE  extracted xnu-buildtree artifact (build/xnu.obj, xnu/, fakeroot/, ...)
FILTER     only compile sources whose path contains one of these strings
           a full path relative to xnu/ also compiles newly added sources

Edit the sources under BUILDTREE/xnu, re-run, and turn the result into
patches with `git diff` there. Uses the local Apple-fork clang (swiftlang).

Env: XNU_CC_EXTRA   extra flags (e.g. "-DKPERF -DKPC" for config changes)
     XNU_CC_POST    flags appended after the original ones (like a per-object
                    _CFLAGS_ADD in the xnu Makefiles: -U/-include after -D)
     XNU_CC_OBJDIR  emit real objects there instead of a syntax-only check
                    (then: llvm-nm for undefined symbols = link errors)
"""
import concurrent.futures as cf, os, re, shlex, subprocess, sys
from collections import Counter

CI_DXB = '/Users/runner/work/ios-sweet/ios-sweet/dxb'
CI_SDK_PLATFORM = re.compile(r'/Applications/Xcode[^ ]*?\.sdk/+System/Library/Frameworks/Kernel\.framework/Versions/A/PrivateHeaders/platform')
CLANG = os.path.expanduser('~/swift/usr/bin/clang')
DROP = {'-c', '-g', '-MD', '-MMD'}
DROP_WITH_ARG = {'-MF', '-MT', '-o', '-arch'}
COMPONENTS = ('osfmk', 'bsd', 'iokit', 'libkern', 'pexpert', 'security', 'san', 'libsa')


def commands(log):
    seen = {}
    for line in open(log, errors='replace'):
        if '/clang' not in line or ' -c ' not in line:
            continue
        line = re.sub(r'^build\s+Build\s+\S+\s+', '', line.rstrip('\n'))
        m = re.search(r'(\S+/clang(\+\+)?) (.*)', line)
        if not m:
            continue
        try:
            args = shlex.split(m.group(3), posix=True)
        except ValueError:	# shell fragments with unbalanced quotes: not a plain compile
            continue
        srcs = [a for a in args if re.search(r'\.(c|cpp|s|S)$', a) and a.startswith(CI_DXB)]
        if len(srcs) == 1 and '/xnu/' in srcs[0]:
            seen[srcs[0]] = ('clang++' if m.group(2) else 'clang', args)
    return seen


def makefile_sources(bt):
    """Every source the generated per-config Makefiles build, as CI paths.
    The CI log is not enough: GitHub splits very long (C++) command lines and
    parallel make interleaves them, so some commands cannot be recovered."""
    out = []
    for root, _, files in os.walk(os.path.join(bt, 'build/xnu.obj')):
        if 'Makefile' not in files or 'meta_features.h' not in files:
            continue
        text = open(os.path.join(root, 'Makefile'), errors='replace').read().replace('\\\n', ' ')
        for var in ('CFILES', 'CXXFILES', 'SFILES'):
            m = re.search(r'^%s=(.*)$' % var, text, re.M)
            if not m:
                continue
            for f in m.group(1).split():
                f = f.replace('$(SOURCE_DIR)', CI_DXB + '/xnu')
                if f.startswith('./'):	# generated (iig, yacc) in the build dir
                    f = os.path.join(root.replace(bt, CI_DXB), f[2:])
                out.append(f)
    return out


def template_for(src, cmds):
    """Borrow flags from a recovered command of the same component + language."""
    comp = next((c for c in COMPONENTS if f'/{c}/' in src), None)
    lang = os.path.splitext(src)[1]
    for other, (kind, args) in cmds.items():
        if os.path.splitext(other)[1] == lang and f'/xnu/{comp}/' in other:
            return kind, [src if a == other else a for a in args]
    return None


def component_dirs(bt):
    """component -> its config build dir (where meta_features.h lives)."""
    out = {}
    for root, _, files in os.walk(os.path.join(bt, 'build/xnu.obj')):
        if 'meta_features.h' in files:
            for c in COMPONENTS:
                if f'/{c}/' in root + '/' and c not in out:
                    out[c] = root
    return out


def run(item, bt, cdirs):
    src, (kind, args) = item
    objdir = os.environ.get('XNU_CC_OBJDIR')
    mode = ['-c', '-o', os.path.join(objdir, src.replace(CI_DXB + '/xnu/', '').replace('/', '__') + '.o')] if objdir else ['-fsyntax-only']
    new = [CLANG if kind == 'clang' else CLANG + '++', '-target', 'arm64-apple-macos14.0', *mode,
           # Apple clang-only builtins (kalloc_type); values only matter for codegen
           '-D__builtin_xnu_type_signature(...)=""', '-D__builtin_xnu_type_summary(...)=0',
           '-D__builtin_xnu_types_compatible(...)=1'] + os.environ.get('XNU_CC_EXTRA', '').split()
    skip = False
    for a in args:
        if skip:
            skip = False
            continue
        if a in DROP:
            continue
        if a in DROP_WITH_ARG:
            skip = True
            continue
        a = CI_SDK_PLATFORM.sub(os.path.join(bt, 'sdk-kernel-platform/platform'), a)
        new.append(a.replace(CI_DXB, bt))
    new += os.environ.get('XNU_CC_POST', '').split()
    comp = next((c for c in COMPONENTS if f'/xnu/{c}/' in src), None) or \
        next((c for c in COMPONENTS if f'/{c}/' in src), None)
    cwd = cdirs.get(comp)
    if not cwd:
        return src, 1, f'no build dir for component {comp}'
    p = subprocess.run(new, cwd=cwd, capture_output=True, text=True)
    return src, p.returncode, p.stderr


def main():
    log, bt = sys.argv[1], os.path.abspath(sys.argv[2])
    per_file = '--per-file' in sys.argv
    filters = [a for a in sys.argv[3:] if a != '--per-file']
    cmds = commands(log)
    synth = 0
    for src in makefile_sources(bt):
        if src not in cmds:
            t = template_for(src, cmds)
            if t:
                cmds[src] = t
                synth += 1
    # New patch sources are absent from the previous CI artifact's Makefiles.
    # An explicit source path can still borrow this component's compile flags.
    for f in filters:
        if os.path.isfile(os.path.join(bt, 'xnu', f)) and f.endswith(('.c', '.cpp', '.s', '.S')):
            src = CI_DXB + '/xnu/' + f
            if src not in cmds:
                t = template_for(src, cmds)
                if t:
                    cmds[src] = t
                    synth += 1
    print(f'{synth} commands synthesized from Makefile source lists', file=sys.stderr)
    if filters:
        cmds = {k: v for k, v in cmds.items() if any(f in k for f in filters)}
    if not cmds:
        print('no compile commands matched', file=sys.stderr)
        return 1
    cdirs = component_dirs(bt)
    print(f'{len(cmds)} files, build dirs: {sorted(cdirs)}', file=sys.stderr)
    errors, failed = Counter(), []
    with cf.ThreadPoolExecutor(os.cpu_count()) as ex:
        for src, rc, err in ex.map(lambda i: run(i, bt, cdirs), cmds.items()):
            if rc:
                failed.append(src.replace(CI_DXB + '/xnu/', ''))
                if per_file:
                    first = [l for l in err.splitlines() if 'error:' in l][:2]
                    print(failed[-1])
                    for l in first:
                        print('    ' + l.replace(bt + '/xnu/', '').replace(bt + '/', '')[:220])
            for l in err.splitlines():
                if ' error: ' in l or 'fatal error:' in l:
                    errors[l.replace(bt + '/xnu/', '').replace(bt + '/', '')] += 1
    if not per_file:
        for e, n in sorted(errors.items()):
            print(f'{n:3} {e}')
    print(f'\n{len(failed)} of {len(cmds)} files failed', file=sys.stderr)
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main())
