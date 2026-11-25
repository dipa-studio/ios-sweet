#!/usr/bin/env python3
"""Offline System95 descendant adding the real CPU display client and its job.

No device access. The enabled image remains a candidate until the exact live
binary passes its device pilot. Existing jobs, keys and system files are retained.
"""
import argparse
import copy
import hashlib
import importlib
import importlib.util
import json
import os
from pathlib import Path
import plistlib
import re
import shutil
import stat
import subprocess
import whyred_boot_profile as hardware

BASE70 = 'd2e155be8cc3457b8d5784cf676933ab17e6052d75b596091fff0e52819983e3'
SYSTEM91 = 'fa356fa4a02ae74fff9dbc674336f52f9754560767ee3c88ca3579629905ebe0'
SYSTEM95 = '6d8da8962b0cb6e40d329e2050ce9f57bb02bae417e26b17ba3ff8259324b99f'
BUILDER = '09975effcec5c65261dd0296137b2baa1ba53713d3667bd50b111a72bc6fabc0'
CACHE = 'System/Library/xpc/launchd.plist'
LABEL = 'org.whyred.display'
JOB = 'System/Library/LaunchDaemons/' + LABEL + '.plist'
LIVE = 'usr/local/whyred/bin/whyred-display'
WAKE = 'usr/local/whyred/bin/whyred-display-wake'
KERNEL99 = '2ED4E8A4-6D1C-3C3C-980B-8533C25978D1'
PARTITION_BYTES = 13085938 * 512
JETSAM = 'System/Library/LaunchDaemons/com.apple.jetsamproperties.D22.plist'


def require(value, message):
    if not value:
        raise ValueError(message)


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def get(root, path):
    for component in path.split('/'):
        root = root.children[component]
    return root


def merge_job(cache):
    require(isinstance(cache.get('LaunchDaemons'), dict), 'Missing daemon cache')
    jobs = cache['LaunchDaemons']
    require(len(jobs) == 531, 'Unexpected System95 job count')
    require('/' + JOB not in jobs and all(j.get('Label') != LABEL for j in jobs.values()),
            'Display job already exists')
    for name in ('com.apple.bluetoothd', 'com.apple.fairplayd.H2'):
        require(jobs['/System/Library/LaunchDaemons/' + name + '.plist'].get('Disabled') is True,
                'Requested disabled job changed')
    job = dict(Label=LABEL, ProgramArguments=['/' + LIVE, 'live'], RunAtLoad=True,
               KeepAlive={'SuccessfulExit': False}, ThrottleInterval=30,
               UserName='mobile', GroupName='mobile', ProcessType='Interactive', Nice=10,
               EnableTransactions=False, WorkingDirectory='/private/var/mobile',
               StandardOutPath='/private/var/mobile/Library/Logs/whyred-display.log',
               StandardErrorPath='/private/var/mobile/Library/Logs/whyred-display.log',
               EnvironmentVariables={'HOME': '/var/mobile', 'PATH': '/usr/local/whyred/bin:/usr/bin:/bin'})
    result = copy.deepcopy(cache)
    result['LaunchDaemons']['/' + JOB] = job
    require(all(result['LaunchDaemons'][key] == value for key, value in jobs.items()),
            'Existing job altered')
    return result, job


def merge_display_budget(properties, memory_mb):
    require(memory_mb == 128, 'Only the finite128MiB display experiment is supported')
    require(isinstance(properties, dict) and isinstance(properties.get('Version4'), dict),
            'Missing Version4 budget table')
    daemon = properties['Version4'].get('Daemon')
    require(isinstance(daemon, dict) and isinstance(daemon.get('Override'), dict),
            'Missing daemon overrides')
    require(LABEL not in daemon['Override'] and
            all(not isinstance(value, dict) or LABEL not in value for value in daemon.values()),
            'Display budget already present')
    result = copy.deepcopy(properties)
    result['Version4']['Daemon']['Override'][LABEL] = {
        'ActiveHardMemoryLimit': memory_mb, 'InactiveHardMemoryLimit': memory_mb}
    restored = copy.deepcopy(result)
    del restored['Version4']['Daemon']['Override'][LABEL]
    require(restored == properties, 'Existing memory policy altered')
    return result


def self_test():
    jobs = {'/base/%d.plist' % n: {'Label': 'base.%d' % n} for n in range(529)}
    for name in ('com.apple.bluetoothd', 'com.apple.fairplayd.H2'):
        jobs['/System/Library/LaunchDaemons/' + name + '.plist'] = {'Label': name, 'Disabled': True}
    original = {'LaunchDaemons': jobs, 'OtherConfiguration': {'preserved': [1, 2, 3]}}
    before = copy.deepcopy(original)
    result, job = merge_job(original)
    require(original == before and len(result['LaunchDaemons']) == 532, 'Input mutation/count')
    require({key: value for key, value in result['LaunchDaemons'].items() if key != '/' + JOB} == jobs,
            'Job conservation failure')
    require(result['OtherConfiguration'] == before['OtherConfiguration'], 'Other cache data changed')
    require(job['ProgramArguments'] == ['/' + LIVE, 'live'] and job['UserName'] == 'mobile', 'Wrong executable/user')
    for bad in [result, {'LaunchDaemons': {}}, {}]:
        try:
            merge_job(bad)
        except (KeyError, ValueError):
            pass
        else:
            raise ValueError('Accepted invalid baseline/collision')
    bad = copy.deepcopy(original)
    bad['LaunchDaemons']['/System/Library/LaunchDaemons/com.apple.bluetoothd.plist']['Disabled'] = False
    try:
        merge_job(bad)
    except ValueError:
        pass
    else:
        raise ValueError('Accepted reenabled Bluetooth job')
    baseline = {'Version4': {'Daemon': {'Default': {'old': {'EnablePressuredExit': False}},
                'Override': {'old': {'ActiveHardMemoryLimit': 6, 'InactiveHardMemoryLimit': -1}}},
                'App': {'preserved': [1, 2]}}}
    budget = merge_display_budget(baseline, 128)
    require(budget['Version4']['Daemon']['Override'][LABEL] == {
        'ActiveHardMemoryLimit': 128, 'InactiveHardMemoryLimit': 128}, 'Wrong display budget')
    for invalid, amount in [(baseline, 0), (baseline, -1), (baseline, 512), (budget, 128), ({}, 128),
                            ({'Version4': {'Daemon': {'Override': []}}}, 128)]:
        try:
            merge_display_budget(invalid, amount)
        except ValueError:
            pass
        else:
            raise ValueError('Accepted invalid/colliding memory policy')
    print('PASS: preserve all531 jobs/cache fields; reject collisions and changed baseline policy')
    print('PASS: retain full memory table; only own128MiB hard limits; reject invalid/colliding policy')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--self-test', action='store_true')
    for key in ('baseline-out', 'system91', 'system95', 'live-dir', 'wake-dir', 'provenance', 'reader', 'comparator', 'output'):
        parser.add_argument('--' + key, type=Path)
    parser.add_argument('--build', action='store_true')
    parser.add_argument('--display-memory-mb', type=int, choices=[128],
                        help='Build101 with only the display job budget added to the D22 memory table')
    parser.add_argument('--hardware-profile', choices=['minimal-hardware'],
                        help='System102: disable exactly19 unsupported hardware jobs; retains101 display policy')
    args = parser.parse_args()
    require(not args.hardware_profile or args.display_memory_mb == 128,
            'Hardware profile requires the working101 display budget')
    if args.self_test:
        self_test()
        return
    require(all(getattr(args, key.replace('-', '_')) for key in
                ('baseline-out', 'system91', 'system95', 'live-dir', 'wake-dir', 'provenance', 'reader', 'output')),
            'Missing image preparation argument')
    require(not args.build or args.comparator, 'Independent comparator required for image build')
    os.umask(0o077)
    out = args.output.resolve()
    require(not out.exists(), 'Refusing to overwrite candidate')
    base = args.baseline_out.resolve()
    prior91 = json.loads((args.system91 / 'manifest.json').read_text())
    prior95 = json.loads((args.system95 / 'manifest.json').read_text())
    require(prior95['system_apfs_sha256'] == SYSTEM95 and sha(prior95['system_apfs_path']) == SYSTEM95,
            'System95 rollback/provenance mismatch')
    require(prior91['system_apfs_sha256'] == SYSTEM91 and sha(prior91['system_apfs_path']) == SYSTEM91,
            'System91 provenance mismatch')
    require(json.loads((args.system95 / 'offline-readiness.json').read_text())['offline_ready'],
            'System95 independent validation missing')
    prep, v70 = base / 'whyred-rootfs-prep', base / 'whyred-rootfs-v70'
    require(sha(prep / 'mkapfs-whyred-v60.py') == BUILDER and
            sha(v70 / 'whyred-system-ios165-v70.apfs') == BASE70, 'Base/builder mismatch')
    import sys
    sys.path.insert(0, str(prep))
    builder = importlib.import_module('mkapfs-whyred-v60')
    root = builder.read_tree(str(prep / 'rootfs-extracted'))
    builder.apply_manifest(root, str(v70 / 'system.whyred.v70.manifest'))
    recovery_dir = base / 'whyred-launchd-executable-recovery'
    recovery = json.loads((recovery_dir / 'overlay.json').read_text())['verified_files']
    require(len(recovery) == 8, 'Unexpected executable recovery set')
    for item in recovery:
        source = recovery_dir / item['path']
        require(sha(source) == item['sha256'], 'Recovered executable mismatch')
        parent, name = get(root, str(Path(item['path']).parent)), Path(item['path']).name
        require(name not in parent.children, 'Recovery destination collision')
        node = builder.Node(name, int(item['mode'], 8), source=str(source))
        node.uid, node.gid = item['uid'], item['gid']
        parent.children[name] = node

    def directory(path):
        node = root
        for part in path.split('/'):
            if part not in node.children:
                node.children[part] = builder.Node(part, stat.S_IFDIR | 0o755)
            node = node.children[part]
            require(stat.S_ISDIR(node.mode), 'Non-directory parent')
        return node

    for item in prior91['changes'] + prior95['changes_from_v91']:
        require(sha(item['source']) == item['sha256'], 'Prior overlay source changed')
        parent, name = directory(str(Path(item['path']).parent)), Path(item['path']).name
        if name not in parent.children:
            require('mode' in item, 'New prior file lacks metadata')
            parent.children[name] = builder.Node(name, int(item['mode'], 8), source=item['source'])
        node = parent.children[name]
        node.source = item['source']
        if 'mode' in item:
            node.mode, node.uid, node.gid = int(item['mode'], 8), item['uid'], item['gid']
    directory('System/Library/WhyredSSH').mode = stat.S_IFDIR | 0o700
    cache = plistlib.loads(Path(get(root, CACHE).source).read_bytes())
    updated, job = merge_job(cache)
    version = 102 if args.hardware_profile else (101 if args.display_memory_mb else 100)
    native_hardware = {}
    if args.hardware_profile:
        native_hardware = {hardware.DAEMONS + filename:
            plistlib.loads(Path(get(root, (hardware.DAEMONS + filename).lstrip('/')).source).read_bytes())
            for _, filename, _ in hardware.HARDWARE_JOBS}
        updated, native_hardware = hardware.merge(updated, native_hardware)
    budget_properties = (merge_display_budget(plistlib.loads(Path(get(root, JETSAM).source).read_bytes()),
                         args.display_memory_mb) if args.display_memory_mb else None)
    spec = importlib.util.spec_from_file_location('verified_ssh_image', Path(__file__).with_name('prepare-whyred-ssh-image.py'))
    ssh_image = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ssh_image)
    bootstrap_paths = ssh_image.validate_job_path(prep / 'rootfs-extracted/sbin/launchd', JOB)
    provenance = json.loads(args.provenance.read_text())
    require(provenance.get('verified') is True, 'Signed tool provenance missing')
    binaries = [(LIVE, args.live_dir / 'whyred-render-probe', 'live'),
                (WAKE, args.wake_dir / 'whyred-display-wake', 'wake')]
    for target, source, kind in binaries:
        require(sha(source) == provenance[kind]['sha256'] and
                KERNEL99.encode() in source.read_bytes(), 'Matched signed99 tool changed')
        report = json.loads((source.parent / 'report.json').read_text())
        require(report['source'] == provenance[kind]['source'] and report['sha256'] == sha(source) and
                report['bytes'] == source.stat().st_size, 'CI source/bytes report mismatch')
        subprocess.run(['codesign', '--verify', '--strict', str(source)], check=True, capture_output=True)
        signed = subprocess.run(['codesign', '-d', '--entitlements', ':-', str(source)],
                                check=True, capture_output=True).stdout
        expected_rights = ({'com.apple.QuartzCore.displayable-context': True,
                            'com.apple.QuartzCore.global-capture': True} if kind == 'live' else
                           {'com.apple.private.hid.client.event-dispatch': True,
                            'com.apple.hid.system.user-access-service': True})
        require(plistlib.loads(signed) == expected_rights, 'Unexpected signed tool rights')
        commands = subprocess.run(['otool', '-l', str(source)], check=True, capture_output=True, text=True).stdout
        require(re.search(r'platform\s+(?:2|IOS)\b', commands), 'Wrong executable platform')
        disassembly = subprocess.run(['xcrun', 'llvm-objdump', '-d', str(source)],
                                     check=True, capture_output=True, text=True).stdout
        require(not re.search(r'\b(?:cas[a-z]*|ldadd[a-z]*|swp[a-z]*|stadd[a-z]*)\s+[wx]', disassembly),
                'Unsupported LSE executable instruction')
        require(Path(target).name not in get(root, str(Path(target).parent)).children, 'Binary collision')
    if args.build:
        # Each retained spool stream is placed in the final bounded container.
        # Budget two complete System partitions plus1GiB, rather than requiring
        # an unrelated round18GiB threshold. Recheck the exact layout below.
        require(shutil.disk_usage(out.parent).free >= 2 * PARTITION_BYTES + 1024**3,
                'Insufficient bounded image/spool space')
    out.mkdir(mode=0o700)
    overlay = out / 'overlay'
    overlay.mkdir()
    jobfile = overlay / (LABEL + '.plist')
    jobfile.write_bytes(plistlib.dumps(job, fmt=plistlib.FMT_BINARY))
    cachefile = overlay / 'launchd.plist'
    cachefile.write_bytes(plistlib.dumps(updated, fmt=plistlib.FMT_BINARY))
    changes = []
    for target, source in [(LIVE, binaries[0][1]), (WAKE, binaries[1][1]), (JOB, jobfile)]:
        parent, name = get(root, str(Path(target).parent)), Path(target).name
        require(name not in parent.children, 'Display destination collision')
        mode = stat.S_IFREG | (0o644 if target == JOB else 0o755)
        node = builder.Node(name, mode, source=str(source))
        parent.children[name] = node
        changes.append(dict(path=target, source=str(source), sha256=sha(source), mode=oct(mode), uid=0, gid=0))
    get(root, CACHE).source = str(cachefile)
    changes.append(dict(path=CACHE, source=str(cachefile), sha256=sha(cachefile),
                        mode=oct(get(root, CACHE).mode), uid=get(root, CACHE).uid, gid=get(root, CACHE).gid))
    if budget_properties is not None:
        budgetfile = overlay / Path(JETSAM).name
        budgetfile.write_bytes(plistlib.dumps(budget_properties, fmt=plistlib.FMT_BINARY))
        node = get(root, JETSAM)
        node.source = str(budgetfile)
        changes.append(dict(path=JETSAM, source=str(budgetfile), sha256=sha(budgetfile),
                            mode=oct(node.mode), uid=node.uid, gid=node.gid))
    for path, properties in native_hardware.items():
        local = overlay / Path(path).name
        local.write_bytes(plistlib.dumps(properties, fmt=plistlib.FMT_BINARY))
        node = get(root, path.lstrip('/'))
        node.source = str(local)
        changes.append(dict(path=path.lstrip('/'), source=str(local), sha256=sha(local),
                            mode=oct(node.mode), uid=node.uid, gid=node.gid))
    plan = dict(version=version, base_system_version=95, base_system_sha256=SYSTEM95,
                live_binary_provenance=provenance, changes=changes, job=job,
                old_jobs_unchanged=not bool(native_hardware), old_job_count=531, job_count=532,
                hardware_profile=args.hardware_profile,
                hardware_disabled_labels=[x[0] for x in hardware.HARDWARE_JOBS] if native_hardware else [],
                bootstrap_paths=bootstrap_paths, added_files=3, modified_files=1 + bool(budget_properties) + len(native_hardware),
                display_memory_mb=args.display_memory_mb,
                recommended_kernel_uuid=KERNEL99, device_writes=False,
                live_pilot_required_before_flash=True, hardware_verified=False,
                tool_sha256=sha(__file__), builder_sha256=BUILDER)
    (out / 'plan.json').write_text(json.dumps(plan, indent=2) + '\n')
    if not args.build:
        print('Validated display overlay/launchd cache plan; image not built')
        return
    image = out / ('whyred-system-ios165-v%d-live-display.apfs' % version)
    spoolpath = Path(str(image) + '.spool')
    with spoolpath.open('w+b') as spool:
        volume = builder.Volume(0, 'System', root, True, 1683900000 * 1000000000, spool,
                                ['System/Library/Caches/com.apple.dyld'])
        container = builder.Container([volume], 256, image.name)
        container.layout()
        require(container.block_count * builder.BS < PARTITION_BYTES, 'Image exceeds System partition')
        spool.flush()
        require(spoolpath.stat().st_size < PARTITION_BYTES and
                shutil.disk_usage(out).free >= container.block_count * builder.BS + 1024**3,
                'Insufficient space for exact image layout')
        container.write(str(image))
    image.chmod(0o600)
    checks = []
    metadata = args.reader.resolve().with_name('verify-metadata')
    for item in changes:
        subprocess.run([str(args.reader.resolve()), str(image), '/' + item['path'], item['source']], check=True,
                       capture_output=True)
        subprocess.run([str(metadata), str(image), '/' + item['path'], item['mode'][2:],
                        str(item['uid']), str(item['gid'])], check=True, capture_output=True)
        checks.append(item['path'])
    comparison_args = [str(args.comparator.resolve()), prior95['system_apfs_path'], str(image)]
    if budget_properties is not None:
        comparison_args.append('--display-memory-policy')
    if native_hardware:
        comparison_args.append('--minimal-hardware')
    result = subprocess.run(comparison_args,
                            capture_output=True, text=True, check=True)
    comparison = json.loads(result.stdout)
    require(comparison.get('passed') is True and comparison.get('added_files') == 3 and
            comparison.get('explicit_file_exceptions') == 1 + bool(budget_properties) + len(native_hardware) and
            comparison.get('exact_bytes_compared', 0) > 4 * 1024**3, 'Whole-image comparison failed')
    manifest = dict(plan, system_apfs_path=str(image), system_apfs_size=image.stat().st_size,
                    system_apfs_sha256=sha(image), system_partition_bytes=PARTITION_BYTES,
                    exact_file_checks=checks, comparison=comparison, offline_image_verified=True)
    (out / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    spoolpath.unlink()
    print(json.dumps(dict(image_sha256=manifest['system_apfs_sha256'], image_bytes=image.stat().st_size,
                          whole_image_verified=True, hardware_verified=False, device_writes=False)))


if __name__ == '__main__':
    main()
