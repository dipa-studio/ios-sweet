#!/usr/bin/env python3
"""Static tests for qemu-sweet.py run manifests.

This never starts QEMU. It exercises the pure manifest helpers and the
boot-args composition used by the runner.
"""
import hashlib
import importlib.util
import json
import os
import pathlib
import struct
import tempfile

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
RUNNER = REPO_ROOT / 'tools' / 'qemu-sweet.py'


def load_runner():
    spec = importlib.util.spec_from_file_location('qemu_sweet', RUNNER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def normalized(path):
    return str(path).replace(os.sep, '/')


def make_payload(boot_args):
    payload = bytearray(0x48 + 608)
    struct.pack_into('<8sII', payload, 0, b'SWEETXNU', 1, 0)
    struct.pack_into(
        '<7Q', payload, 0x10,
        0xfffffe0007000000,  # virt_base
        0xfffffe0007000000,  # entry_va
        0x48 + 608,          # adt_off (unused: adt_size is zero)
        0,                   # adt_size
        0xfffffe0007001000,  # kernel_end
        0x40000000,          # phys_base
        0x10000000,          # mem_size
    )
    encoded = boot_args.encode('latin1')
    payload[0x48:0x48 + len(encoded)] = encoded
    return bytes(payload)


def main():
    q = load_runner()
    with tempfile.TemporaryDirectory() as temporary:
        directory = pathlib.Path(temporary)
        payload_bytes = b'payload-test-bytes'
        payload_path = directory / 'payload.bin'
        payload_path.write_bytes(payload_bytes)
        kernel_path = directory / 'kernel.bin'
        kernel_path.write_bytes(b'kernel-test')
        sample_path = directory / 'sample-kernel.bin'
        sample_path.write_bytes(b'sample-kernel-test')
        disk_path = directory / 'root.img'
        disk_path.write_bytes(b'disk' * 256)

        started = 1700000000.0
        argv = ['qemu-system-aarch64', '-M', 'virt', '-smp', '1']
        manifest = q.build_manifest(
            argv=argv,
            payload_path=str(payload_path),
            payload=payload_bytes,
            extra_cmdline='extra=1',
            boot_args='base cpus=1 extra=1',
            trace='errors',
            disk_snapshot=True,
            disk=str(disk_path),
            kernel=str(kernel_path),
            sample_kernel=str(sample_path),
            qemu_binary='C:/qemu/qemu-system-aarch64.exe',
            qemu_version='QEMU emulator version 11.1.0',
            host_started=started,
        )

        assert manifest['schema_version'] == 1
        assert manifest['state'] == 'prepared'
        assert manifest['host_started'] == q.iso_now(started)
        assert manifest['host_started_unix'] == started
        assert manifest['qemu_binary'] == 'C:/qemu/qemu-system-aarch64.exe'
        assert manifest['qemu_version'] == 'QEMU emulator version 11.1.0'
        assert manifest['argv'] == argv
        assert manifest['payload_path'] == normalized(payload_path)
        assert manifest['payload_size'] == len(payload_bytes)
        assert manifest['payload_sha256'] == hashlib.sha256(payload_bytes).hexdigest()
        assert manifest['extra_cmdline'] == 'extra=1'
        assert manifest['boot_args'] == 'base cpus=1 extra=1'
        assert manifest['trace'] == 'errors'
        assert manifest['disk_snapshot'] is True
        assert manifest['kernel'] == {
            'path': normalized(kernel_path),
            'size': 11,
            'sha256': hashlib.sha256(b'kernel-test').hexdigest(),
        }
        assert manifest['sample_kernel'] == {
            'path': normalized(sample_path),
            'size': 18,
            'sha256': hashlib.sha256(b'sample-kernel-test').hexdigest(),
        }
        assert manifest['disk']['path'] == normalized(disk_path)
        assert manifest['disk']['size'] == 1024
        assert manifest['disk']['mtime_ns'] > 0

        q.finalize_manifest(
            manifest,
            stop_reason='deadline',
            qemu_returncode=-9,
            runner_exit_code=0,
            result_status='not_decoded',
            host_finished=started + 12.5,
        )
        assert manifest['state'] == 'finished'
        assert manifest['host_finished'] == q.iso_now(started + 12.5)
        assert manifest['duration_secs'] == 12.5
        assert manifest['stop_reason'] == 'deadline'
        assert manifest['timed_out'] is True
        assert manifest['qemu_returncode'] == -9
        assert manifest['runner_exit_code'] == 0
        assert manifest['result_status'] == 'not_decoded'

        manifest_path = directory / 'run-manifest.json'
        q.write_manifest(str(manifest_path), manifest)
        on_disk = json.loads(manifest_path.read_text(encoding='utf-8'))
        assert on_disk == manifest
        assert manifest_path.read_text(encoding='utf-8').endswith('\n')

        minimal = q.build_manifest(
            argv=[],
            payload_path=str(payload_path),
            payload=payload_bytes,
            extra_cmdline='',
            boot_args='base cpus=1',
            trace='exceptions',
            disk_snapshot=False,
            disk=None,
            kernel=None,
            sample_kernel=None,
            qemu_binary=None,
            qemu_version=None,
            host_started=started,
        )
        assert 'kernel' not in minimal
        assert 'sample_kernel' not in minimal
        assert 'disk' not in minimal
        assert minimal['qemu_binary'] is None
        assert minimal['qemu_version'] is None

        interrupted = q.build_manifest(
            argv=[], payload_path=str(payload_path), payload=payload_bytes,
            extra_cmdline='', boot_args='base cpus=1', trace='errors',
            disk_snapshot=False, disk=None, kernel=None, sample_kernel=None,
            qemu_binary=None, qemu_version=None, host_started=started,
        )
        q.finalize_manifest(
            interrupted, stop_reason='interrupted', qemu_returncode=-9,
            runner_exit_code=130, host_finished=started + 1,
        )
        assert interrupted['state'] == 'interrupted'

        failed = q.build_manifest(
            argv=[], payload_path=str(payload_path), payload=payload_bytes,
            extra_cmdline='', boot_args='base cpus=1', trace='errors',
            disk_snapshot=False, disk=None, kernel=None, sample_kernel=None,
            qemu_binary=None, qemu_version=None, host_started=started,
        )
        q.finalize_manifest(
            failed, stop_reason='runner_error', qemu_returncode=None,
            runner_exit_code=1, host_finished=started + 1, error='test error',
        )
        assert failed['state'] == 'failed'
        assert failed['error'] == 'test error'

        synthetic = make_payload('base cpus=2 keep=1')
        phys_base, image, boot_args_pa, entry_pa, boot_args = q.build_image(
            synthetic, 'extra=2', smp=4
        )
        assert phys_base == 0x40000000
        assert boot_args_pa == 0x40004000
        assert entry_pa == 0x40000000
        assert boot_args == 'base cpus=4 keep=1 extra=2'
        cmdline_offset = 2 + 2 + 4 + 4 * 8 + 6 * 8 + 4 + 4 + 8 + 4
        assert image[boot_args_pa - phys_base + cmdline_offset:
                     boot_args_pa - phys_base + cmdline_offset + len(boot_args)] == boot_args.encode('latin1')

    print('[PASS] qemu-sweet manifest and boot-args static tests')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
