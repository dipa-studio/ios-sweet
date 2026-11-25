#!/usr/bin/env python3
"""Package a CI-verified APFS RAM-root diagnostic; never flashes the handset."""
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys

PORT = Path(__file__).resolve().parents[1]


def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    if len(sys.argv) != 4:
        raise SystemExit('usage: package-apfs-root-v51.py RUN_ID ARTIFACT_SHA256 SOURCE_COMMIT')
    run, digest, commit = sys.argv[1:]
    if not run.isdigit() or not re.fullmatch('[0-9a-f]{64}', digest) or not re.fullmatch('[0-9a-f]{40}', commit):
        raise SystemExit('Invalid run, artifact digest or commit')
    ci = PORT / f'out/ci-kernel-no-lse-{run}'
    archive = PORT / f'out/build-inputs/run-{run}-kernel.zip'
    if sha(archive) != digest: raise SystemExit('CI artifact digest mismatch')
    kernel = ci / 'kernel.development.sweet'
    sums = {line.split(None, 1)[1].strip().lstrip('*'): line.split()[0]
            for line in (ci / 'SHA256SUMS').read_text().splitlines()}
    if sums.get(kernel.name) != sha(kernel): raise SystemExit('CI kernel checksum mismatch')
    log = (ci / 'build.log').read_text(errors='replace')
    for n in range(115, 136):
        if not re.search(r'Applying patch: [^\r\n]*' + f'{n:04d}-', log):
            raise SystemExit(f'Patch {n} was not confirmed in CI')
        if re.search(r'Skipping patch [^\r\n]*' + f'{n:04d}-', log):
            raise SystemExit(f'Patch {n} was skipped')
    # Optional blacktop patches for other macOS releases print "error: patch
    # does not apply"; warning excerpts also contain printf("error: ...").
    # Match actual compiler diagnostics rather than those strings.
    if re.search(r'(?m)^[^\n|]*:\d+:\d+: (?:fatal )?error:', log):
        raise SystemExit('Compiler error in CI log')

    boot_report = json.loads((ci / 'whyred-source-report.json').read_text())
    reference = json.loads((PORT / 'out/ci-kernel-no-lse-40949733049/whyred-source-report.json').read_text())
    for key, value in reference.items():
        if key == 'source_sha256': continue
        if boot_report.get(key) != value: raise SystemExit(f'Baseline boot check changed: {key}')
    for path, value in reference['source_sha256'].items():
        # Only the filesystem option group changes in the established boot sources.
        expected = sha(PORT / 'out/patch-0135-work' / path) if path == 'config/MASTER.arm64.sweet' else value
        if boot_report['source_sha256'].get(path) != expected: raise SystemExit(f'Baseline source changed: {path}')
    apfs_report = json.loads((ci / 'whyred-apfs-source-report.json').read_text())
    if apfs_report.get('read_only') is not True or apfs_report.get('root_opt_in') != 'whyred-apfs-root=1':
        raise SystemExit('APFS guard did not confirm readonly/opt-in behavior')
    for path, value in apfs_report['source_sha256'].items():
        local = PORT / 'out/patch-0135-work' / path
        if not local.is_file() or sha(local) != value: raise SystemExit(f'APFS source differs from reviewed candidate: {path}')
    cases = json.loads((ci / 'apfs-host-test/report.json').read_text())['tests']
    if len(cases) < 8 or any(c['returncode'] for c in cases): raise SystemExit('APFS host cases did not pass')
    root = ci / 'whyred-test-root.apfs'
    root_meta = json.loads(root.with_suffix('.json').read_text())
    init = ci / 'sweet-init.macho'
    if (root_meta['root_sha256'] != sha(root) or root_meta['init_sha256'] != sha(init) or
        root_meta['contains_apple_ios_userland'] is not False): raise SystemExit('Diagnostic APFS root manifest mismatch')
    if root.stat().st_size != 4 * 1024 * 1024: raise SystemExit('Unexpected diagnostic root size')
    subprocess.run([sys.executable, str(PORT / 'tools/audit-arm64-lse.py'), str(kernel),
                    '--require-none', '--require-no-pan'], check=True)

    base = PORT / 'out/whyred-emmc-block-v49-40949733049'
    baseline = json.loads((base / 'manifest.json').read_text())
    for name, key in [('kernel.development.whyred', 'kernel_sha256'), ('whyred-gold.adt', 'adt_sha256'),
                      ('sweet-init.macho', 'init_sha256'), ('shim-boot-whyred-uartdm-debug.img', 'image_sha256')]:
        if sha(base / name) != baseline[key]: raise SystemExit('Baseline package changed: ' + name)
    stock = PORT.parent / 'device-backups/boot.img'
    if sha(stock) != '7aaa6094c477e4def3638a5a58fc7be063a2bb2661d16ad3305b01bebbd25a0f':
        raise SystemExit('Stock backup changed')
    # Reauthenticate the loader by comparing it with the saved v49 boot layout.
    sys.path.insert(0, str(PORT / 'tools'))
    import mkpayload
    import mkbootimg_whyred_legacy as boot
    boot.verify(base / 'shim-boot-whyred-uartdm-debug.img', stock, base / 'shim/Image', base / 'payload.bin', 0x4000000)

    out = PORT / f'out/whyred-apfs-root-v51-{run}'
    if out.exists(): raise SystemExit(f'Refusing to overwrite {out}')
    (out / 'shim').mkdir(parents=True)
    for src, dest in [(kernel, 'kernel.development.whyred'), (root, 'root.apfs'), (init, 'sweet-init.macho'),
                      (base / 'shim/Image', 'shim/Image'), (base / 'whyred-gold.adt', 'whyred-gold.adt')]:
        shutil.copyfile(src, out / dest)
    # This RAM-root test needs no SDHCI/eMMC diagnostic, and issues no flash commands.
    command = ' '.join(w for w in baseline['cmdline'].split()
                       if not re.match(r'whyred-(?:sdhci|emmc)-', w)) + ' whyred-apfs-root=1'
    if 'rd=md0' not in command.split() or len(command.encode()) >= 608: raise SystemExit('Invalid RAM-root command line')
    payload, info = mkpayload.build(str(out / 'kernel.development.whyred'), str(out / 'whyred-gold.adt'),
                                    command, ramdisk_path=str(out / 'root.apfs'))
    (out / 'payload.bin').write_bytes(payload)
    image = out / 'shim-boot-whyred-uartdm-debug.img'
    boot.build(stock, out / 'shim/Image', out / 'payload.bin', image, 0x4000000)
    check = boot.verify(image, stock, out / 'shim/Image', out / 'payload.bin', 0x4000000)
    (out / 'verification.txt').write_text(check + '\n')
    manifest = {'run': run, 'source_commit': commit, 'actions_artifact_sha256': digest,
                'cmdline': command, 'ramdisk': info['ramdisk'],
                'kernel_sha256': sha(out / 'kernel.development.whyred'), 'root_sha256': sha(out / 'root.apfs'),
                'image_sha256': sha(image), 'adt_sha256': sha(out / 'whyred-gold.adt'),
                'hardware_test': 'pending APFS mount/exec on md0; project static test PID 1 only',
                'flashed_partition': 'none', 'contains_apple_ios_userland': False}
    (out / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print('v51 APFS RAM-root candidate packaged; no device operation was performed')
    print(image); print(manifest['image_sha256'])


if __name__ == '__main__': main()
