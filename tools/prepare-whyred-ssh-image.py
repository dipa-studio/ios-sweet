#!/usr/bin/env python3
"""Prepare an offline System image adding only SSH userland to verified v70."""
import argparse
import hashlib
import importlib
import json
import os
from pathlib import Path
import plistlib
import shutil
import stat
import subprocess
import sys
from xml.parsers.expat import ExpatError

BASE_SHA = 'd2e155be8cc3457b8d5784cf676933ab17e6052d75b596091fff0e52819983e3'
BUILDER_SHA = '09975effcec5c65261dd0296137b2baa1ba53713d3667bd50b111a72bc6fabc0'
CACHE_SHA = '51634e43a5683e338afd1319204ebeb0ef1658f38855d27e76f2b2e3111d4aa9'
PARTITION_BYTES = 13085938 * 512
LABEL = 'org.whyred.ssh'
JOB_PATH = 'System/Library/LaunchDaemons/org.whyred.ssh.plist'
KEY_DIR = 'System/Library/WhyredSSH'
VERSION = 92


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def get(root, path):
    for part in path.split('/'):
        root = root.children[part]
    return root


def bootstrap_paths(launchd):
    """Read startup paths from this exact launchd's embedded configuration."""
    data = launchd.read_bytes()
    position, matches = 0, []
    while True:
        start = data.find(b'<?xml', position)
        if start < 0:
            break
        end = data.find(b'</plist>', start)
        if end < 0:
            break
        position = end + len(b'</plist>')
        try:
            value = plistlib.loads(data[start:position])
        except (plistlib.InvalidFileException, ExpatError):
            continue
        if isinstance(value, dict) and isinstance(value.get('Bootstrap'), dict):
            paths = value['Bootstrap'].get('Paths')
            if isinstance(paths, list) and all(isinstance(p, str) for p in paths):
                matches.append(paths)
    if len(matches) != 1:
        raise ValueError('Cannot identify the exact launchd bootstrap search paths')
    return matches[0]


def validate_job_path(launchd, job_path):
    paths = bootstrap_paths(launchd)
    if '/' + str(Path(job_path).parent) not in paths:
        raise ValueError('SSH job directory is not in this launchd bootstrap configuration')
    return paths


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--baseline-out', required=True, type=Path)
    ap.add_argument('--userland', required=True, type=Path)
    ap.add_argument('--provenance', required=True, type=Path)
    ap.add_argument('--compatibility-audit', required=True, type=Path)
    ap.add_argument('--keys', required=True, type=Path)
    ap.add_argument('--reader', required=True, type=Path)
    ap.add_argument('--output', required=True, type=Path)
    args = ap.parse_args()
    base = args.baseline_out.resolve()
    userland, keys, out = args.userland.resolve(), args.keys.resolve(), args.output.resolve()
    if out.exists():
        raise SystemExit('Refusing to overwrite an earlier image or keys')
    if shutil.disk_usage(out.parent).free < 18 * 1024**3:
        raise SystemExit('Insufficient space for image and compression spool')
    provenance = json.loads(args.provenance.read_text())
    source_commit = (userland / 'source-commit.txt').read_text().strip()
    if not provenance.get('verified') or provenance.get('head_sha') != source_commit:
        raise SystemExit('Missing matching CI provenance')
    report = json.loads((userland / 'build-report.json').read_text())
    tests = json.loads((userland / 'host-test-report.json').read_text())
    audit = json.loads((userland / 'macho-audit.json').read_text())
    compatibility = json.loads(args.compatibility_audit.read_text())
    if not compatibility.get('passed'):
        raise SystemExit('Exact installed iOS import compatibility audit did not pass')
    if (report.get('password_auth') is not False or not report.get('public_key_auth') or
            report.get('target_bind') != '192.168.7.2' or report.get('port') != 2222 or
            not tests.get('passed') or tests.get('keys_in_artifact') is not False or
            report.get('usb_auth_log_mirror') is not True):
        raise SystemExit('Required userland/authentication checks missing')
    for name in ['dropbear', 'dropbearkey', 'scp', 'sh', 'whyredctl', 'whyreddiag']:
        path = userland / 'ios-bin' / name
        if sha(path) != report['platforms']['ios'][name]['sha256'] or sha(path) != audit[name]['sha256']:
            raise SystemExit('Built binary differs from reports: ' + name)
        if compatibility['binaries'][name].get('sha256') != sha(path) or compatibility['binaries'][name]['missing']:
            raise SystemExit('Installed cache compatibility proof differs: ' + name)
    original = base / 'whyred-rootfs-v70/whyred-system-ios165-v70.apfs'
    old = base / 'whyred-rootfs-v70'
    prep = base / 'whyred-rootfs-prep'
    launchd = prep / 'rootfs-extracted/sbin/launchd'
    startup_paths = validate_job_path(launchd, JOB_PATH)
    if sha(original) != BASE_SHA:
        raise SystemExit('System v70 rollback image differs')
    if sha(prep / 'mkapfs-whyred-v60.py') != BUILDER_SHA or sha(old / 'launchd.bringup.plist') != CACHE_SHA:
        raise SystemExit('Verified v70 builder or launchd cache differs')
    for name in ['authorized_keys', 'dropbear_ed25519_host_key']:
        path = keys / name
        if not path.is_file() or path.is_symlink() or stat.S_IMODE(path.stat().st_mode) & 0o077:
            raise SystemExit('Production key file missing or insufficiently private')
    out.mkdir(mode=0o700, parents=True)
    overlay = out / 'overlay'
    overlay.mkdir(mode=0o700)
    sys.path.insert(0, str(prep))
    builder = importlib.import_module('mkapfs-whyred-v60')
    root = builder.read_tree(str(prep / 'rootfs-extracted'))
    builder.apply_manifest(root, str(old / 'system.whyred.v70.manifest'))
    recovery = json.loads((base / 'whyred-launchd-executable-recovery/overlay.json').read_text())
    if len(recovery['verified_files']) != 8:
        raise SystemExit('Unexpected v70 executable recovery set')
    for item in recovery['verified_files']:
        path = item['path']
        source = base / 'whyred-launchd-executable-recovery' / path
        if source.stat().st_size != item['bytes'] or sha(source) != item['sha256']:
            raise SystemExit('Recovered executable differs: ' + path)
        parent = get(root, str(Path(path).parent))
        if Path(path).name in parent.children:
            raise SystemExit('Recovery destination unexpectedly exists: ' + path)
        node = builder.Node(Path(path).name, int(item['mode'], 8), source=str(source))
        node.uid, node.gid = item['uid'], item['gid']
        parent.children[node.name] = node
    counts = dict(files=0, dirs=0, symlinks=0)
    def inventory(node):
        for name, child in node.children.items():
            if name == '.DS_Store' or name.startswith('._') or ':' in name:
                raise ValueError('Unexpected host metadata in source tree: ' + name)
            kind = ('dirs' if stat.S_ISDIR(child.mode) else
                    'symlinks' if stat.S_ISLNK(child.mode) else 'files')
            counts[kind] += 1
            if kind == 'dirs':
                inventory(child)
    inventory(root)
    if counts != dict(files=45734, dirs=16600, symlinks=671):
        raise SystemExit('Source catalog differs from verified System v70: ' + repr(counts))
    changes = []
    def directory(path, mode=0o755):
        node = root
        for part in path.split('/'):
            child = node.children.get(part)
            if child is None:
                child = builder.Node(part, stat.S_IFDIR | 0o755)
                node.children[part] = child
            if not stat.S_ISDIR(child.mode):
                raise ValueError('Non-directory parent: ' + path)
            node = child
        node.mode = stat.S_IFDIR | mode
        return node
    def add(path, source, mode=0o755):
        parent = directory(str(Path(path).parent))
        if Path(path).name in parent.children:
            raise ValueError('SSH destination already exists: ' + path)
        node = builder.Node(Path(path).name, stat.S_IFREG | mode, source=str(source))
        parent.children[node.name] = node
        changes.append(dict(path=path, source=str(source), mode=oct(node.mode), uid=0, gid=0,
                            bytes=source.stat().st_size, sha256=sha(source)))
    add('bin/sh', userland / 'ios-bin/sh')
    for name in ['dropbear', 'scp', 'whyredctl', 'whyreddiag']:
        add('usr/local/whyred/bin/' + name, userland / 'ios-bin' / name)
    for name in ['DROPBEAR-LICENSE', 'DASH-COPYING']:
        add('usr/local/whyred/share/licenses/' + name, userland / name, 0o644)
    add(KEY_DIR + '/authorized_keys', keys / 'authorized_keys', 0o400)
    add(KEY_DIR + '/dropbear_ed25519_host_key', keys / 'dropbear_ed25519_host_key', 0o400)
    directory(KEY_DIR, 0o700)
    shells = overlay / 'shells'
    shells.write_text('/bin/sh\n')
    add('private/etc/shells', shells, 0o644)
    job = dict(Label=LABEL, ProgramArguments=['/usr/local/whyred/bin/dropbear', '-F',
        '-p', '192.168.7.2:2222', '-D', '/' + KEY_DIR, '-r', '/' + KEY_DIR + '/dropbear_ed25519_host_key',
        '-P', '/private/var/run/whyred-ssh.pid', '-K', '30', '-T', '3'],
        RunAtLoad=True, KeepAlive=True, ThrottleInterval=10, UserName='root', GroupName='wheel',
        ProcessType='Interactive', EnableTransactions=False,
        StandardOutPath='/private/var/root/Library/Logs/whyred-sshd.log',
        StandardErrorPath='/private/var/root/Library/Logs/whyred-sshd.log',
        EnvironmentVariables={'PATH': '/usr/local/whyred/bin:/usr/bin:/bin:/usr/sbin:/sbin', 'LC_ALL': 'C'})
    jobfile = overlay / 'org.whyred.ssh.plist'
    jobfile.write_bytes(plistlib.dumps(job, fmt=plistlib.FMT_BINARY))
    add(JOB_PATH, jobfile, 0o644)
    cache = plistlib.loads((old / 'launchd.bringup.plist').read_bytes())
    before = dict(cache['LaunchDaemons'])
    if len(before) != 530 or any(j.get('Label') == LABEL for j in before.values()):
        raise SystemExit('Unexpected installed launchd job set')
    cache['LaunchDaemons']['/' + JOB_PATH] = job
    if any(cache['LaunchDaemons'].get(k) != v for k, v in before.items()):
        raise SystemExit('Existing launchd job changed')
    cachefile = overlay / 'launchd.plist'
    cachefile.write_bytes(plistlib.dumps(cache, fmt=plistlib.FMT_BINARY))
    get(root, 'System/Library/xpc/launchd.plist').source = str(cachefile)
    changes.append(dict(path='System/Library/xpc/launchd.plist', source=str(cachefile),
                        bytes=cachefile.stat().st_size, sha256=sha(cachefile)))
    image = out / ('whyred-system-ios165-v%d-ssh.apfs' % VERSION)
    plan = dict(version=VERSION, baseline_sha256=BASE_SHA, boot_version_required=89,
                source_commit=source_commit, userland_provenance=provenance, changes=changes,
                baseline_catalog=counts,
                ssh_job_path='/' + JOB_PATH, launchd_bootstrap_paths=startup_paths,
                launchd_bootstrap_path_verified=True, launchd_source_sha256=sha(launchd),
                old_jobs_unchanged=True, old_job_count=530, new_job_count=531,
                device_writes=False, ssh_hardware_verified=False)
    (out / 'plan.json').write_text(json.dumps(plan, indent=2) + '\n')
    with Path(str(image) + '.spool').open('w+b') as spool:
        volume = builder.Volume(0, 'System', root, True, 1683900000 * 1000000000, spool,
                                ['System/Library/Caches/com.apple.dyld'])
        container = builder.Container([volume], 256, image.name)
        container.layout()
        if container.block_count * builder.BS > PARTITION_BYTES:
            raise SystemExit('SSH image exceeds existing System geometry')
        container.write(str(image))
    image.chmod(0o600)
    checks = []
    verify = changes + [dict(path=x, source=str(prep / 'rootfs-extracted' / x))
        for x in ['sbin/launchd', 'private/etc/passwd']]
    verify += [dict(path=x['path'], source=str(base / 'whyred-launchd-executable-recovery' / x['path']))
        for x in recovery['verified_files']]
    cache_source = prep / 'rootfs-extracted/System/Cryptexes/OS/System/Library/Caches/com.apple.dyld'
    verify += [dict(path='System/Library/Caches/com.apple.dyld/' + p.name, source=str(p))
               for p in sorted(cache_source.iterdir()) if p.is_file()]
    for item in verify:
        result = subprocess.run([str(args.reader.resolve()), str(image), '/' + item['path'], item['source']],
                                capture_output=True, text=True)
        if result.returncode:
            raise RuntimeError(result.stdout + result.stderr)
        checks.append(dict(path=item['path'], source_sha256=sha(Path(item['source']))))
        print('Image byte check passed: ' + item['path'], flush=True)
    digest = sha(image)
    manifest = dict(plan, system_apfs_path=str(image), system_apfs_size=image.stat().st_size,
        system_apfs_sha256=digest, system_partition_bytes=PARTITION_BYTES,
        image_cache_verified=True, exact_file_checks=checks, flash_authorized=False)
    (out / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print(json.dumps(dict(image_bytes=image.stat().st_size, image_sha256=digest,
                          verified_files=len(checks), device_writes=False)), flush=True)


if __name__ == '__main__':
    main()
