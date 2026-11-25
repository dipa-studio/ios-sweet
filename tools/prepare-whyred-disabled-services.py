#!/usr/bin/env python3
"""Rebuild verified System91 with Disabled=true for exactly two requested jobs."""
import argparse
import copy
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

SYSTEM91 = 'fa356fa4a02ae74fff9dbc674336f52f9754560767ee3c88ca3579629905ebe0'
BASE70 = 'd2e155be8cc3457b8d5784cf676933ab17e6052d75b596091fff0e52819983e3'
BUILDER = '09975effcec5c65261dd0296137b2baa1ba53713d3667bd50b111a72bc6fabc0'
LABELS = ('com.apple.bluetoothd', 'com.apple.fairplayd.H2')
CACHE = 'System/Library/xpc/launchd.plist'


def sha(p):
    with Path(p).open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def get(root, path):
    for part in path.split('/'):
        root = root.children[part]
    return root


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--baseline-out', type=Path, required=True)
    ap.add_argument('--system91', type=Path, required=True)
    ap.add_argument('--reader', type=Path, required=True)
    ap.add_argument('--output', type=Path, required=True)
    args = ap.parse_args()
    os.umask(0o077)
    base, old, out = args.baseline_out.resolve(), args.system91.resolve(), args.output.resolve()
    if out.exists():
        raise SystemExit('Refusing to overwrite a prior image')
    if shutil.disk_usage(out.parent).free < 18 * 1024**3:
        raise SystemExit('Insufficient space for image and compression spool')
    prior = json.loads((old / 'manifest.json').read_text())
    ready = json.loads((old / 'offline-readiness.json').read_text())
    if prior['version'] != 91 or prior['system_apfs_sha256'] != SYSTEM91 or not ready['offline_ready']:
        raise SystemExit('Unexpected System91 provenance')
    if sha(prior['system_apfs_path']) != SYSTEM91:
        raise SystemExit('System91 rollback bytes changed')
    prep, v70 = base / 'whyred-rootfs-prep', base / 'whyred-rootfs-v70'
    if sha(prep / 'mkapfs-whyred-v60.py') != BUILDER or sha(v70 / 'whyred-system-ios165-v70.apfs') != BASE70:
        raise SystemExit('Verified base/builder changed')
    sys.path.insert(0, str(prep))
    builder = importlib.import_module('mkapfs-whyred-v60')
    root = builder.read_tree(str(prep / 'rootfs-extracted'))
    builder.apply_manifest(root, str(v70 / 'system.whyred.v70.manifest'))
    recovery_dir = base / 'whyred-launchd-executable-recovery'
    recovery = json.loads((recovery_dir / 'overlay.json').read_text())['verified_files']
    if len(recovery) != 8:
        raise SystemExit('Unexpected executable recovery set')
    for item in recovery:
        source = recovery_dir / item['path']
        assert sha(source) == item['sha256'] and source.stat().st_size == item['bytes']
        parent = get(root, str(Path(item['path']).parent))
        assert Path(item['path']).name not in parent.children
        node = builder.Node(Path(item['path']).name, int(item['mode'], 8), source=str(source))
        node.uid, node.gid = item['uid'], item['gid']
        parent.children[node.name] = node

    def directory(path, mode=0o755):
        node = root
        for part in path.split('/'):
            if part not in node.children:
                node.children[part] = builder.Node(part, stat.S_IFDIR | 0o755)
            node = node.children[part]
            assert stat.S_ISDIR(node.mode)
        node.mode = stat.S_IFDIR | mode
        return node

    # Replay ONLY the already verified91 overlay, including the existing keys.
    for item in prior['changes']:
        assert sha(item['source']) == item['sha256']
        parent = directory(str(Path(item['path']).parent))
        name = Path(item['path']).name
        if name not in parent.children:
            assert 'mode' in item
            parent.children[name] = builder.Node(name, int(item['mode'], 8), source=item['source'])
        node = parent.children[name]
        node.source = item['source']
        if 'mode' in item:
            node.mode, node.uid, node.gid = int(item['mode'], 8), item['uid'], item['gid']
    directory('System/Library/WhyredSSH', 0o700)

    def snapshot(node, prefix=''):
        result = {}
        for name, child in node.children.items():
            path = prefix + name
            result[path] = (child.mode, child.uid, child.gid, child.source, getattr(child, 'target', None))
            if stat.S_ISDIR(child.mode):
                result.update(snapshot(child, path + '/'))
        return result

    before_tree = snapshot(root)
    out.mkdir(mode=0o700)
    overlay = out / 'overlay'
    overlay.mkdir()
    cache = plistlib.loads(Path(get(root, CACHE).source).read_bytes())
    before_cache = copy.deepcopy(cache)
    assert len(cache['LaunchDaemons']) == 531
    changes = []
    for label in LABELS:
        path = 'System/Library/LaunchDaemons/' + label + '.plist'
        node = get(root, path)
        original = plistlib.loads(Path(node.source).read_bytes())
        assert original['Label'] == label and not original.get('Disabled', False)
        updated = dict(original, Disabled=True)
        local = overlay / (label + '.plist')
        local.write_bytes(plistlib.dumps(updated, fmt=plistlib.FMT_BINARY))
        node.source = str(local)
        cached = cache['LaunchDaemons']['/' + path]
        assert cached['Label'] == label and not cached.get('Disabled', False)
        cached['Disabled'] = True
        changes.append(dict(path=path, source=str(local), sha256=sha(local), bytes=local.stat().st_size))
    cachefile = overlay / 'launchd.plist'
    cachefile.write_bytes(plistlib.dumps(cache, fmt=plistlib.FMT_BINARY))
    get(root, CACHE).source = str(cachefile)
    changes.append(dict(path=CACHE, source=str(cachefile), sha256=sha(cachefile), bytes=cachefile.stat().st_size))
    expected = copy.deepcopy(before_cache)
    for label in LABELS:
        expected['LaunchDaemons']['/System/Library/LaunchDaemons/' + label + '.plist']['Disabled'] = True
    assert cache == expected and len(cache['LaunchDaemons']) == 531
    after_tree = snapshot(root)
    assert before_tree.keys() == after_tree.keys()
    assert {p for p in before_tree if before_tree[p] != after_tree[p]} == {x['path'] for x in changes}
    for item in changes:
        assert before_tree[item['path']][:3] == after_tree[item['path']][:3]
    image = out / 'whyred-system-ios165-v95-services-disabled.apfs'
    plan = dict(version=95, base_system_version=91, base_system_sha256=SYSTEM91,
                boot_version_required=94, disabled_jobs=list(LABELS), changes_from_v91=changes,
                other_529_jobs_unchanged=True, catalog_paths_and_metadata_unchanged=True,
                keys_and_ssh_unchanged=True, job_count=531, device_writes=False,
                builder_sha256=BUILDER, tool_sha256=sha(__file__), hardware_verified=False)
    (out / 'plan.json').write_text(json.dumps(plan, indent=2) + '\n')
    print('Verified91 tree reconstructed; only two job plists and launchd cache changed', flush=True)
    spoolpath = Path(str(image) + '.spool')
    with spoolpath.open('w+b') as spool:
        volume = builder.Volume(0, 'System', root, True, 1683900000 * 1000000000, spool,
                                ['System/Library/Caches/com.apple.dyld'])
        container = builder.Container([volume], 256, image.name)
        container.layout()
        assert container.block_count * builder.BS < 13085938 * 512
        container.write(str(image))
    image.chmod(0o600)
    # Retain every previous critical byte check, plus both changed job files.
    sources = {x['path']: x['source'] for x in prior['changes']}
    sources.update({x['path']: str(recovery_dir / x['path']) for x in recovery})
    for path in ['sbin/launchd', 'private/etc/passwd']:
        sources[path] = str(prep / 'rootfs-extracted' / path)
    caches = prep / 'rootfs-extracted/System/Cryptexes/OS/System/Library/Caches/com.apple.dyld'
    sources.update({'System/Library/Caches/com.apple.dyld/' + p.name: str(p) for p in caches.iterdir() if p.is_file()})
    sources.update({x['path']: x['source'] for x in changes})
    checks = []
    for path, source in sources.items():
        run = subprocess.run([str(args.reader.resolve()), str(image), '/' + path, source], capture_output=True, text=True)
        if run.returncode:
            raise RuntimeError(run.stdout + run.stderr)
        checks.append(dict(path=path, source_sha256=sha(source)))
        print('Image byte check passed: ' + path, flush=True)
    metadata = args.reader.resolve().with_name('verify-metadata')
    for path in sources:
        node = get(root, path)
        subprocess.run([str(metadata), str(image), '/' + path, format(node.mode, 'o'), str(node.uid), str(node.gid)], check=True, capture_output=True)
    digest = sha(image)
    manifest = dict(plan, system_apfs_path=str(image), system_apfs_size=image.stat().st_size,
                    system_apfs_sha256=digest, system_partition_bytes=13085938 * 512,
                    image_cache_verified=True, exact_file_checks=checks, metadata_checks=len(sources), flash_authorized=False)
    (out / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    spoolpath.unlink()
    print(json.dumps(dict(image_sha256=digest, image_bytes=image.stat().st_size,
                          verified_files=len(checks), device_writes=False)), flush=True)


if __name__ == '__main__':
    main()
