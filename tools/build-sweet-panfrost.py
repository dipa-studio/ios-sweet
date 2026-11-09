#!/usr/bin/env python3
"""Build pinned Mesa v10/CSF for SweetGPU (hardware required, no fallback).

Keeps the existing softpipe validation profile/artifacts intact. HakiOS supplies
the GLES/OSMesa integration; SweetGPU supplies the G710 Panthor transport.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import sys
import tarfile

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('gles_build', ROOT / 'tools/build-sweet-gles.py')
base = importlib.util.module_from_spec(spec)
spec.loader.exec_module(base)
run = base.run


def replace(path, old, new):
    text = path.read_text()
    if text.count(old) != 1:
        raise ValueError(f'expected exactly one patch anchor in {path}: {old[:60]}')
    path.write_text(text.replace(old, new))


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--work', type=Path, required=True)
    ap.add_argument('--reference', type=Path, required=True)
    ap.add_argument('--archive', type=Path, required=True)
    ap.add_argument('--sdk', type=Path, required=True)
    ap.add_argument('--cc', type=Path, required=True)
    ap.add_argument('--jobs', type=int, default=6)
    a = ap.parse_args()
    # Mesa's generators discover python3 again during Ninja regeneration.
    # Keep them in the same environment that supplied Meson and Mako.
    os.environ['PATH'] = str(Path(sys.executable).parent) + os.pathsep + os.environ['PATH']
    work, ref, sdk, cc = (p.resolve() for p in (a.work, a.reference, a.sdk, a.cc))
    commit = run(['git', '-C', ref, 'rev-parse', 'HEAD'], capture_output=True, text=True).stdout.strip()
    if commit != base.HAKIOS or hashlib.sha256(a.archive.read_bytes()).hexdigest() != base.MESA_SHA:
        ap.error('pinned HakiOS/Mesa input mismatch')
    work.mkdir(parents=True, exist_ok=True)
    src = work / f'mesa-{base.MESA}'
    patches = ['freedreno-darwin.patch', 'osmesa-es-profile.patch', 'panfrost-darwin.patch']
    if not src.exists():
        with tarfile.open(a.archive) as tar:
            tar.extractall(work)
        for patch in patches:
            run(['patch', '-p1', '-i', ref / 'tools/mesa' / patch], cwd=src)
        shutil.copytree(ref / 'tools/mesa/redwood-drm', src / 'src/redwood-drm')
        for f in ['src/panfrost/lib/meson.build', 'src/gallium/drivers/panfrost/meson.build']:
            replace(src / f, "? ['7'] :", "? ['10'] :")
        replace(src / 'src/panfrost/lib/pan_shader.c', 'defined(__APPLE__) && PAN_ARCH == 7',
                'defined(__APPLE__) && PAN_ARCH == 10')
        replace(src / 'src/gallium/drivers/panfrost/pan_screen.c',
                '/* Darwin builds Bifrost v7 alone, the Infinix\'s Mali-G52 */\n'
                '   if (dev->arch == 7)\n      panfrost_cmdstream_screen_init_v7(screen);',
                '/* SweetGPU uses G710 v10/CSF. */\n'
                '   if (dev->arch == 10)\n      panfrost_cmdstream_screen_init_v10(screen);')
        p = src / 'src/gallium/targets/osmesa/osmesa_target.c'
        replace(p, 'drmOpenWithType("panfrost",', 'drmOpenWithType("panthor",')
        replace(p, '   if (screen)\n      return screen;\n#endif',
                '   return screen; /* Hardware profile: failure must not select softpipe. */\n#endif')
        p = src / 'src/panfrost/lib/kmod/panthor_kmod.c'
        replace(p, '''   panthor_dev->flush_id = os_mmap(0, getpagesize(), PROT_READ, MAP_SHARED, fd,
                                   DRM_PANTHOR_USER_FLUSH_ID_MMIO_OFFSET);''',
                '''#ifdef __APPLE__
   /* SweetGPU cleans/invalidates on every CALL; zero requests a full flush. */
   panthor_dev->flush_id = calloc(1, sizeof(uint32_t));
   if (!panthor_dev->flush_id) panthor_dev->flush_id = MAP_FAILED;
#else
   panthor_dev->flush_id = os_mmap(0, getpagesize(), PROT_READ, MAP_SHARED, fd,
                                   DRM_PANTHOR_USER_FLUSH_ID_MMIO_OFFSET);
#endif''')
        replace(p, '   os_munmap(panthor_dev->flush_id, getpagesize());',
                '''#ifdef __APPLE__
   free(panthor_dev->flush_id);
#else
   os_munmap(panthor_dev->flush_id, getpagesize());
#endif''')
        (src / '.sweet-v10-profile').write_text('panthor v10 hardware required\n')
    if not (src / '.sweet-v10-profile').exists():
        ap.error('incomplete or incompatible source tree; choose a fresh work directory')
    # Match SweetGPU's reserved firmware/queue aperture. Gallium otherwise
    # advertises a 32 MiB start, below the kernel's 128 MiB BO boundary.
    p = src / 'src/panfrost/lib/kmod/panthor_kmod.c'
    old_range = '''      .start = 0,

      /* 3G/1G user/kernel VA split'''
    new_range = '''      .start = 0x08000000ull,

      /* 3G/1G user/kernel VA split'''
    if old_range in p.read_text():
        replace(p, old_range, new_range)
        replace(p, 'va_bits == 32 ? (1ull << (va_bits - 2)) * 3 : 1ull << (va_bits - 1),',
                '(va_bits == 32 ? (1ull << (va_bits - 2)) * 3 : 1ull << (va_bits - 1)) - 0x08000000ull,')
    if new_range not in p.read_text():
        ap.error('incompatible Panthor VA range patch')
    # IOSurface IDs are not Linux dma-buf FDs. SweetGPU ABI v1 serializes
    # import with submission and returns from SUBMIT only after the hardware
    # fence completes. Track each imported BO with the same real timeline
    # used for local non-exclusive BOs; never invent/export sync-file FDs.
    sync_marker = '/* SweetGPU synchronous IOSurface timeline. */'
    if sync_marker not in p.read_text():
        replace(p, 'int ret = drmSyncobjCreate(dev->fd, 0, &panthor_bo->sync.handle);',
                '''#ifdef __APPLE__
   /* SweetGPU synchronous IOSurface timeline. No work is in flight on import. */
   int ret = drmSyncobjCreate(dev->fd, DRM_SYNCOBJ_CREATE_SIGNALED, &panthor_bo->sync.handle);
#else
   int ret = drmSyncobjCreate(dev->fd, 0, &panthor_bo->sync.handle);
#endif''')
        text = p.read_text()
        shared = '''   bool shared =
      bo->flags & (PAN_KMOD_BO_FLAG_EXPORTED | PAN_KMOD_BO_FLAG_IMPORTED);'''
        if text.count(shared) != 4:
            raise ValueError('unexpected Panthor implicit synchronization sites')
        # The first occurrence is bo_export, which remains unsupported.
        first = text.index(shared) + len(shared)
        text = text[:first] + text[first:].replace(shared, '''#ifdef __APPLE__
   /* SweetGPU synchronous IOSurface timeline. */
   bool shared = false;
#else
''' + shared + '\n#endif')
        p.write_text(text)
    # 25.0.7 has the v10 compiler/CSF backend but its product table only
    # names G610. The phone reports a8620004 (G710, variant 0). Register the
    # product explicitly instead of lying about GPU_ID in the transport.
    p = src / 'src/panfrost/lib/pan_props.c'
    g610 = '        MODEL(0xa867, 0, "G610",   "TVIx", HAS_ANISO,         32768, {}),'
    g710 = '        MODEL(0xa862, 0, "G710",   "TVIx", HAS_ANISO,         32768, {}),'
    if g710 not in p.read_text():
        replace(p, g610, g710 + '\n' + g610)
    shutil.copyfile(ROOT / 'userland/sweet-panthor-drm.c', src / 'src/redwood-drm/redwood_drm.c')
    shutil.copyfile(ROOT / 'xnu/gpu/sweet_gpu_user.h', src / 'src/redwood-drm/sweet_gpu_user.h')
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
        options = dict(platforms='', gallium_drivers='softpipe,panfrost', freedreno_kmds='msm', vulkan_drivers='',
            glx='disabled', egl='disabled', gbm='disabled', osmesa='true', llvm='disabled',
            shared_glapi='enabled', gles1='disabled', gles2='enabled', opengl='true',
            zstd='disabled', xmlconfig='disabled', expat='disabled', shader_cache='disabled',
            valgrind='disabled', libunwind='disabled', glvnd='disabled', video_codecs='', tools='',
            gallium_vdpau='disabled', gallium_va='disabled', gallium_xa='disabled',
            lmsensors='disabled', build_tests='false')
        run([sys.executable, '-m', 'mesonbuild.mesonmain', 'setup', build, src,
            '--cross-file', cross, '--wrap-mode=nofallback', '--prefix=/usr/local/sweet-gpu',
            '--libdir=lib', '--buildtype=release', '-Db_ndebug=true'] +
            [f'-D{k.replace("_", "-")}={v}' for k, v in options.items()])
    run(['ninja', '-C', build, f'-j{a.jobs}'])
    out = work / 'out';out.mkdir(exist_ok=True)
    # Keep the pinned reference immutable. Apply our compositor fixes to a
    # generated copy so clean builds reproduce the exact tested bridge.
    frontend = work / 'frontend';frontend.mkdir(exist_ok=True)
    shutil.copyfile(ref / 'userland/src/eagl.c', frontend / 'eagl.c')
    run(['patch', '-p1', '-i', ROOT / 'userland/eagl-iosurface.patch'], cwd=frontend)
    library = out / 'libOSMesa.8.dylib'
    shutil.copyfile(build / 'src/gallium/targets/osmesa/libOSMesa.8.dylib', library)
    run(['install_name_tool', '-id', '/usr/local/sweet-gpu/lib/libOSMesa.8.dylib', library])
    glapi = build / 'src/mapi/shared-glapi/libglapi.0.dylib'
    if glapi.exists():
        dst = out / glapi.name;shutil.copyfile(glapi, dst)
        old = run(['otool', '-D', dst], capture_output=True, text=True).stdout.splitlines()[1].strip()
        run(['install_name_tool', '-id', '/usr/local/sweet-gpu/lib/' + dst.name, dst])
        run(['install_name_tool', '-change', old, '/usr/local/sweet-gpu/lib/' + dst.name, library])
    nm = run(['nm', '-gU', library], capture_output=True, text=True).stdout
    exports = out / 'exported-gl.txt'
    exports.write_text('\n'.join(l.split()[-1][1:] for l in nm.splitlines()
        if l.split() and l.split()[-1].startswith('_gl')) + '\n')
    with (out / 'eagl_gen.h').open('w') as f:
        run([sys.executable, ref / 'userland/mkeagl.py', ref / 'userland/src/eagl_slots.txt',
            src / 'src/mapi/glapi/registry/gl.xml', exports, ref / 'userland/src/eagl.c'], stdout=f)
    run(compiler + ['-O2', '-dynamiclib', '-install_name', '/usr/local/sweet-gpu/lib/libsweet-gles.dylib',
        '-I' + str(out), '-I' + str(ref / 'userland/src'), '-framework', 'CoreFoundation', '-framework', 'IOKit', '-framework',
        'IOSurface', '-lobjc', str(library), '-o', str(out / 'libsweet-gles.dylib'),
        str(frontend / 'eagl.c'), str(ref / 'userland/src/gl_osmesa.c')])
    run(compiler + ['-O2', '-Wall', '-Wextra', '-I' + str(src / 'include'),
        '-framework', 'CoreFoundation', '-framework', 'IOKit', '-framework', 'IOSurface', '-lobjc',
        str(library), '-DSWEET_GLES_LIBRARY="/usr/local/sweet-gpu/lib/libsweet-gles.dylib"',
        '-DSWEET_GLES_HARDWARE=1',
        str(ROOT / 'userland/gles-probe.c'), '-o', str(out / 'gles-probe')])
    run(compiler + ['-O2', '-Wall', '-Wextra', '-dynamiclib', '-install_name',
        '/usr/local/sweet/lib/libsweet-gles-loader.dylib',
        str(ROOT / 'userland/gles-loader.c'), '-o', str(out / 'libsweet-gles-loader.dylib')])
    for p in out.iterdir():
        if p.suffix == '.dylib' or p.name == 'gles-probe':run(['codesign', '--force', '--sign', '-', p])
    (out / 'manifest.json').write_text(json.dumps(dict(
        hakios_commit=base.HAKIOS, mesa_version=base.MESA, mesa_archive_sha256=base.MESA_SHA,
        renderer='panfrost-v10-csf', hardware_required=True, hardware_verified=False,
        patches={f: hashlib.sha256((ref / 'tools/mesa' / f).read_bytes()).hexdigest() for f in patches},
        transport_sha256=hashlib.sha256((ROOT / 'userland/sweet-panthor-drm.c').read_bytes()).hexdigest(),
        frontend_patch_sha256=hashlib.sha256((ROOT / 'userland/eagl-iosurface.patch').read_bytes()).hexdigest(),
        target='arm64-apple-ios16.0',
        files={p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in out.iterdir()
               if p.is_file() and p.name != 'manifest.json'}), indent=2) + '\n')
    print(out)


if __name__ == '__main__':
    main()
