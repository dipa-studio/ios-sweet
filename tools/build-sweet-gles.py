#!/usr/bin/env python3
"""Build the pinned HakiOS GLES bridge and a pixel-checked iOS rendering probe.

External source and Apple SDKs stay outside git. This builds softpipe first;
it does not pretend the G52/JM Darwin shim supports our G710/CSF GPU.
Needs clang/SDK for iOS, ninja, bison >= 2.7 and Python meson/mako/packaging.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
HAKIOS = '620c77507a17ad23ac5a40bad900abe9ed4d7740'
MESA = '25.0.7'
MESA_SHA = '592272df3cf01e85e7db300c449df5061092574d099da275d19e97ef0510f8a6'


def run(args, **kw):
    return subprocess.run([str(x) for x in args], check=True, **kw)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--work', type=Path, required=True)
    ap.add_argument('--reference', type=Path, required=True, help='HakiOS common tree, branch mtk')
    ap.add_argument('--sdk', type=Path, required=True)
    ap.add_argument('--cc', type=Path, required=True)
    ap.add_argument('--jobs', type=int, default=6)
    a = ap.parse_args()
    work, ref, sdk, cc = (p.resolve() for p in (a.work, a.reference, a.sdk, a.cc))
    commit = run(['git', '-C', ref, 'rev-parse', 'HEAD'], capture_output=True, text=True).stdout.strip()
    if commit != HAKIOS:
        ap.error('reference must be pinned to ' + HAKIOS)
    work.mkdir(parents=True, exist_ok=True)
    archive = work / f'mesa-{MESA}.tar.xz'
    if not archive.exists():
        urllib.request.urlretrieve(f'https://archive.mesa3d.org/mesa-{MESA}.tar.xz', archive)
    if hashlib.sha256(archive.read_bytes()).hexdigest() != MESA_SHA:
        ap.error('Mesa archive SHA256 mismatch')
    src = work / f'mesa-{MESA}'
    patch = ref / 'tools/mesa/osmesa-es-profile.patch'
    if not src.exists():
        with tarfile.open(archive) as tar:
            tar.extractall(work)
        run(['patch', '-p1', '-i', patch], cwd=src)
    # Reject an unpatched tree; never silently build desktop GL for an ES test.
    if 'OSMESA_ES_PROFILE' not in (src / 'include/GL/osmesa.h').read_text():
        ap.error('source tree is missing the HakiOS OSMesa ES profile patch')
    cross = work / 'ios-cross.ini'
    compiler = [str(cc), '-target', 'arm64-apple-ios16.0', '-isysroot', str(sdk)]
    cross.write_text('[binaries]\n' + '\n'.join(
        f'{kind} = {repr([str(cc) + suffix] + compiler[1:])}'
        for kind, suffix in [('c', ''), ('cpp', '++'), ('objc', '')]) + '''
ar = '/usr/bin/ar'
strip = '/usr/bin/strip'
pkg-config = '/usr/bin/false'
[host_machine]
system = 'darwin'
subsystem = 'ios'
cpu_family = 'aarch64'
cpu = 'arm64'
endian = 'little'
[properties]
needs_exe_wrapper = true
''')
    build = work / 'build-ios'
    if not (build / 'build.ninja').exists():
        options = dict(platforms='', gallium_drivers='softpipe', vulkan_drivers='',
            glx='disabled', egl='disabled', gbm='disabled', osmesa='true', llvm='disabled',
            shared_glapi='enabled', gles1='disabled', gles2='enabled', opengl='true',
            zstd='disabled', xmlconfig='disabled', expat='disabled', shader_cache='disabled',
            valgrind='disabled', libunwind='disabled', glvnd='disabled', video_codecs='', tools='',
            gallium_vdpau='disabled', gallium_va='disabled', gallium_xa='disabled',
            lmsensors='disabled', build_tests='false')
        run([sys.executable, '-m', 'mesonbuild.mesonmain', 'setup', build, src,
            '--cross-file', cross, '--wrap-mode=nofallback', '--prefix=/usr/local/sweet',
            '--libdir=lib', '--buildtype=release', '-Db_ndebug=true'] +
            [f'-D{k.replace("_", "-")}={v}' for k, v in options.items()])
    run(['ninja', '-C', build, f'-j{a.jobs}'])
    config = {v['name']: v['value'] for v in json.loads(
        (build / 'meson-info/intro-buildoptions.json').read_text())}
    if config['gallium-drivers'] != ['softpipe'] or config['vulkan-drivers'] != []:
        ap.error('existing build directory is not the software validation profile')
    out = work / 'out'; out.mkdir(exist_ok=True)
    library = out / 'libOSMesa.8.dylib'
    shutil.copy2(build / 'src/gallium/targets/osmesa/libOSMesa.8.dylib', library)
    run(['install_name_tool', '-id', '/usr/local/sweet/lib/libOSMesa.8.dylib', library])
    # Mesa's separate glapi is a runtime dependency on Darwin.
    glapi = build / 'src/mapi/shared-glapi/libglapi.0.dylib'
    if glapi.exists():
        dst = out / glapi.name; shutil.copy2(glapi, dst)
        old = run(['otool', '-D', dst], capture_output=True, text=True).stdout.splitlines()[1].strip()
        run(['install_name_tool', '-id', '/usr/local/sweet/lib/' + dst.name, dst])
        run(['install_name_tool', '-change', old, '/usr/local/sweet/lib/' + dst.name, library])
    nm = run(['nm', '-gU', library], capture_output=True, text=True).stdout
    exports = out / 'exported-gl.txt'
    exports.write_text('\n'.join(line.split()[-1][1:] for line in nm.splitlines()
        if line.split() and line.split()[-1].startswith('_gl')) + '\n')
    with (out / 'eagl_gen.h').open('w') as f:
        run([sys.executable, ref / 'userland/mkeagl.py', ref / 'userland/src/eagl_slots.txt',
            src / 'src/mapi/glapi/registry/gl.xml', exports, ref / 'userland/src/eagl.c'], stdout=f)
    run(compiler + ['-O2', '-dynamiclib', '-install_name', '/usr/local/sweet/lib/libsweet-gles.dylib',
        '-I' + str(out), '-framework', 'CoreFoundation', '-framework', 'IOKit', '-framework',
        'IOSurface', '-lobjc', str(library), '-o', str(out / 'libsweet-gles.dylib'),
        str(ref / 'userland/src/eagl.c'), str(ref / 'userland/src/gl_osmesa.c')])
    run(compiler + ['-O2', '-Wall', '-Wextra', '-I' + str(src / 'include'),
        '-framework', 'CoreFoundation', '-framework', 'IOKit', '-framework', 'IOSurface', '-lobjc',
        str(library), str(ROOT / 'userland/gles-probe.c'), '-o', str(out / 'gles-probe')])
    for p in out.iterdir():
        if p.suffix == '.dylib' or p.name == 'gles-probe':
            run(['codesign', '--force', '--sign', '-', p])
    files = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in out.iterdir()
             if p.is_file() and p.name != 'manifest.json'}
    (out / 'manifest.json').write_text(json.dumps(dict(
        hakios_commit=HAKIOS, mesa_version=MESA, mesa_archive_sha256=MESA_SHA,
        renderer='softpipe', target='arm64-apple-ios16.0', sdk=str(sdk),
        hardware_acceleration=False, files=files), indent=2) + '\n')
    print(out)


if __name__ == '__main__':
    main()
