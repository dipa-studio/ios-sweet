#!/usr/bin/env python3
"""Build pinned Dropbear and dash for the whyred iOS USB diagnostic channel."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tarfile

SOURCES = {
    'dropbear': ('https://matt.ucc.asn.au/dropbear/releases/dropbear-2026.94.tar.bz2',
                 'e098034a843699200c8c977a991fff73159735bf795d5f72ef672c41a6b1ae81'),
    'dash': ('https://kernel.googlesource.com/pub/scm/utils/dash/dash/+archive/037bbdfd330017c368caf6242f977974123239b5.tar.gz',
             'tree:22ec8a5fdfc358ffb94ddd5c9c4450730c62066ed6c38e2c8c802f3a145676e6'),
    'automake': ('https://ftp.gnu.org/gnu/automake/automake-1.18.1.tar.xz',
                 '168aa363278351b89af56684448f525a5bce5079d0b6842bd910fdd3f1646887'),
}

OPTIONS = '''/* USB diagnostic server: public-key authentication only. */
#define DROPBEAR_SVR_PASSWORD_AUTH 0
#define DROPBEAR_SVR_PAM_AUTH 0
#define DROPBEAR_SVR_PUBKEY_AUTH 1
#define DROPBEAR_SVR_MULTIUSER 1
/* Darwin has no setresgid(); retain ordinary authenticated session UID handling. */
#define DROPBEAR_SVR_DROP_PRIVS 0
#define DROPBEAR_SVR_LOCALTCPFWD 0
#define DROPBEAR_SVR_REMOTETCPFWD 0
#define DROPBEAR_SVR_LOCALSTREAMFWD 0
#define DROPBEAR_SVR_REMOTESTREAMFWD 0
#define DROPBEAR_SVR_AGENTFWD 0
#define DROPBEAR_X11FWD 0
#define DROPBEAR_SFTPSERVER 0
#define DROPBEAR_RSA 0
#define DROPBEAR_DSS 0
#define DROPBEAR_ECDSA 0
#define DROPBEAR_ED25519 1
#define DROPBEAR_DEFADDRESS "192.168.7.2"
#define DROPBEAR_DEFPORT "2222"
#define DEFAULT_PATH "/usr/local/whyred/bin:/usr/bin:/bin:/usr/sbin:/sbin"
'''


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def source_digest(path, expected):
    if not expected.startswith('tree:'):
        return sha(path)
    # Gitiles regenerates gzip/tar metadata on download. Pin every member's
    # name, kind, mode, link target and complete file bytes instead of timestamps.
    rows = {}
    with tarfile.open(path) as tar:
        for member in tar:
            if member.name in rows or '..' in Path(member.name).parts or member.name.startswith('/'):
                raise ValueError('Unsafe or duplicate archive member')
            rows[member.name] = (member.mode, member.type.decode(), member.linkname,
                hashlib.sha256(tar.extractfile(member).read()).hexdigest() if member.isfile() else None)
    return 'tree:' + hashlib.sha256(json.dumps(rows, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def run(args, cwd, env, log):
    with log.open('w') as stream:
        result = subprocess.run(args, cwd=cwd, env=env, stdout=stream, stderr=subprocess.STDOUT)
    if result.returncode:
        raise RuntimeError('Command failed: ' + repr(args) + '\n' + log.read_text()[-6000:])


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--output', required=True, type=Path)
    ap.add_argument('--cache', type=Path)
    ap.add_argument('--platform', choices=['native', 'ios', 'both'], default='both')
    ap.add_argument('--dropbear-only', action='store_true')
    args = ap.parse_args()
    out = args.output.resolve()
    if out.exists():
        raise SystemExit('Refusing to overwrite an earlier build')
    out.mkdir(parents=True)
    cache = args.cache.resolve() if args.cache else out / 'downloads'
    cache.mkdir(parents=True, exist_ok=True)
    archives = {}
    for name, (url, digest) in SOURCES.items():
        if name != 'dropbear' and args.dropbear_only:
            continue
        path = cache / url.rsplit('/', 1)[-1]
        if not path.exists():
            subprocess.run(['curl', '--fail', '--location', '--retry', '2', '--silent', '--show-error',
                            url, '--output', str(path)], check=True)
        if source_digest(path, digest) != digest:
            raise SystemExit('Source archive digest mismatch: ' + name)
        archives[name] = path
    env = dict(os.environ)
    if not args.dropbear_only:
        if not shutil.which('autoconf', path=env.get('PATH')):
            raise SystemExit('Host autoconf is required for dash source generation')
        if not shutil.which('automake', path=env.get('PATH')):
            host = out / 'host-build'
            host.mkdir()
            with tarfile.open(archives['automake']) as tar:
                tar.extractall(host, filter='data')
            src = host / 'automake-1.18.1'
            prefix = out / 'host-tools'
            for command, phase in [(['./configure', '--prefix=' + str(prefix)], 'configure'),
                                   (['make', '-j4'], 'make'), (['make', 'install'], 'install')]:
                run(command, src, env, out / ('automake-' + phase + '.log'))
            env['PATH'] = str(prefix / 'bin') + os.pathsep + env['PATH']
    platforms = ['native', 'ios'] if args.platform == 'both' else [args.platform]
    reports = {}
    for platform in platforms:
        work = out / platform
        work.mkdir()
        target_env = dict(env)
        target_env.pop('MACOSX_DEPLOYMENT_TARGET', None)
        target_env['CC_FOR_BUILD'] = 'clang'
        target_env['CFLAGS'] = '-Os -fno-common'
        target_env['LDFLAGS'] = '-Wl,-S'
        cross = []
        compile_args = ['clang']
        if platform == 'ios':
            sdk = subprocess.check_output(['xcrun', '--sdk', 'iphoneos', '--show-sdk-path'], text=True).strip()
            compile_args += ['-target', 'arm64-apple-ios16.4', '-isysroot', sdk,
                             '-mcpu=generic+crypto', '-mno-outline-atomics']
            cross = ['--build=x86_64-apple-darwin', '--host=aarch64-apple-darwin']
            # SDK18 exports this newer function, but the exact installed16.5
            # libSystem does not. Dash supplies its portable implementation.
            target_env['ac_cv_func_strchrnul'] = 'no'
        import shlex
        target_env['CC'] = shlex.join(compile_args)
        with tarfile.open(archives['dropbear']) as tar:
            tar.extractall(work, filter='data')
        drop = work / 'dropbear-2026.94'
        (drop / 'localoptions.h').write_text(OPTIONS)
        # Mirror only bounded server diagnostics over the existing USB log link.
        # Keep all upstream account, ownership, key and signature checks intact.
        if platform == 'ios':
            shutil.copyfile(Path(__file__).with_name('whyred-ssh-udp.h'), drop / 'src/whyred-ssh-udp.h')
            edits = {
                'svr-session.c': [('#include "includes.h"', '#include "includes.h"\n#include "whyred-ssh-udp.h"'),
                    ('\tvsnprintf(printbuf, sizeof(printbuf), format, param);',
                     '\tvsnprintf(printbuf, sizeof(printbuf), format, param);\n\twhyred_ssh_usb_log(printbuf);')],
                'svr-authpubkey.c': [
                    ('\tif (stat(filename, &filestat) != 0) {',
                     '\tif (stat(filename, &filestat) != 0) {\n\t\tdropbear_log(LOG_WARNING, "WHYRED AUTH stat errno=%d", errno);'),
                    ('\t\tif (!authfile) {\n\t\t\tTRACE',
                     '\t\tif (!authfile) {\n\t\t\tdropbear_log(LOG_WARNING, "WHYRED AUTH open/fdopen errno=%d", errno);\n\t\t\tTRACE')],
                'common-session.c': [('\tpw = getpwnam(username);\n\tif (!pw) {',
                     '\tpw = getpwnam(username);\n\tif (!pw) {\n\t\tdropbear_log(LOG_WARNING, "WHYRED AUTH getpwnam returned NULL errno=%d", errno);')],
            }
            for filename, replacements in edits.items():
                path = drop / 'src' / filename
                text = path.read_text()
                for before, after in replacements:
                    if text.count(before) != 1:
                        raise RuntimeError('Upstream diagnostic patch context changed: ' + filename)
                    text = text.replace(before, after)
                path.write_text(text)
        flags = ['--disable-zlib', '--disable-pam', '--disable-syslog', '--disable-lastlog',
                 '--disable-utmp', '--disable-utmpx', '--disable-wtmp', '--disable-wtmpx',
                 '--disable-loginfunc', '--disable-pututline', '--disable-pututxline']
        run(['./configure', *cross, *flags], drop, target_env, work / 'dropbear-configure.log')
        run(['make', '-j4', 'PROGRAMS=dropbear dropbearkey scp'], drop, target_env, work / 'dropbear-build.log')
        dest = work / 'bin'
        dest.mkdir()
        for name in ['dropbear', 'dropbearkey', 'scp']:
            shutil.copyfile(drop / name, dest / name)
            (dest / name).chmod(0o755)
        shutil.copyfile(drop / 'LICENSE', work / 'DROPBEAR-LICENSE')
        if not args.dropbear_only:
            dash = work / 'dash'
            dash.mkdir()
            with tarfile.open(archives['dash']) as tar:
                tar.extractall(dash, filter='data')
            run(['sh', 'autogen.sh'], dash, env, work / 'dash-autogen.log')
            run(['./configure', *cross, '--disable-memfd-create', '--disable-tee'],
                dash, target_env, work / 'dash-configure.log')
            run(['make', '-j4'], dash, target_env, work / 'dash-build.log')
            shutil.copyfile(dash / 'src/dash', dest / 'sh')
            (dest / 'sh').chmod(0o755)
            shutil.copyfile(dash / 'COPYING', work / 'DASH-COPYING')
            src = Path(__file__).with_name('whyredctl.c')
            run([*compile_args, '-Os', '-Wall', '-Wextra', '-Werror', str(src), '-o', str(dest / 'whyredctl')],
                work, target_env, work / 'whyredctl-build.log')
            src = Path(__file__).with_name('whyreddiag.c')
            run([*compile_args, '-O1', '-fno-omit-frame-pointer', '-Wall', '-Wextra', '-Werror', str(src), '-o', str(dest / 'whyreddiag')],
                work, target_env, work / 'whyreddiag-build.log')
        if platform == 'ios':
            for binary in dest.iterdir():
                signing = ['codesign', '--force', '--sign', '-', '--timestamp=none']
                if binary.name == 'whyreddiag':
                    entitlements = work / 'diagnostic-entitlements.plist'
                    entitlements.write_text('<?xml version="1.0"?><plist version="1.0"><dict><key>task_for_pid-allow</key><true/><key>com.apple.system-task-ports</key><true/></dict></plist>')
                    signing += ['--entitlements', str(entitlements)]
                subprocess.run([*signing, str(binary)], check=True)
                subprocess.run(['codesign', '--verify', '--strict', str(binary)], check=True)
        reports[platform] = {p.name: {'bytes': p.stat().st_size, 'sha256': sha(p)} for p in dest.iterdir()}
        print(platform + ' binaries built', flush=True)
    report = {'sources': SOURCES, 'platforms': reports, 'password_auth': False,
              'public_key_auth': True, 'target_min_ios': '16.4', 'port': 2222,
              'target_bind': '192.168.7.2', 'hardware_verified': False, 'usb_auth_log_mirror': True}
    (out / 'build-report.json').write_text(json.dumps(report, indent=2) + '\n')


if __name__ == '__main__':
    main()
