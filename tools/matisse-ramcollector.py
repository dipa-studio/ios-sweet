#!/usr/bin/env python3
"""Build-only, deterministic boot-v4 RAM collector; never talks to a device.

Reads a Recovery newc archive without extracting paths. Copies only static
BusyBox and an audited USB supplier closure. Does not redistribute those inputs.
"""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import stat
import struct
import subprocess
import tempfile

import mkbootimg

ROOT = Path(__file__).resolve().parent
BASE = 'matisse-collector'
SEEDS = ('mtk_wdt.ko', 'log_store.ko', 'nvmem_mtk-devinfo.ko',
         'pinctrl-mtk-v2.ko', 'pinctrl-mt6983.ko',
         'clk-mt6983.ko', 'regmap-spmi.ko', 'mtk-pmic-wrap.ko',
         'mtk-spmi-pmic.ko', 'spmi-mtk-pmif.ko', 'mt6363-regulator.ko',
         'mt6373-regulator.ko', 'phy-mtk-xsphy.ko', 'mtu3.ko')
ALLOWED = frozenset(SEEDS + ('clk-common.ko', 'aee_aed.ko', 'mrdump.ko'))
APPLETS = ('sh', 'cat', 'mkdir', 'mount', 'mknod', 'cp', 'dmesg', 'ls',
           'insmod', 'ln', 'sleep', 'tar', 'wc', 'sha256sum', 'base64', 'stty')
PARAMS = ('rdinit=/matisse-collector/init', 'init=/matisse-collector/init',
          'clk_ignore_unused', 'pd_ignore_unused', 'panic=15')
LZ4_MAGIC = bytes.fromhex('02214c18')


def compress_ramdisk(archive, lz4='lz4'):
    # Actual vendor_boot platform fragment is precisely LZ4_MAGIC. Linux's
    # unlz4 skips repeated legacy magic, but cannot concatenate it with gzip.
    packed = subprocess.run([lz4, '-l', '-9', '-c'], input=archive,
                            capture_output=True, check=True).stdout
    if not packed.startswith(LZ4_MAGIC):
        raise ValueError('compressor did not produce legacy LZ4')
    decoded = subprocess.run([lz4, '-d', '-c'], input=LZ4_MAGIC + packed,
                             capture_output=True, check=True).stdout
    if decoded != archive:
        raise ValueError('platform-prefix LZ4 roundtrip failed')
    return packed


def sha(data):
    return hashlib.sha256(data).hexdigest()


def read_newc(data):
    """Strict single newc archive parser: bounded, no extraction or symlink following."""
    out, off = {}, 0
    while off + 110 <= len(data):
        if data[off:off+6] != b'070701':
            raise ValueError('expected newc magic')
        try:
            h = [int(data[off+6+i*8:off+14+i*8], 16) for i in range(13)]
        except ValueError as e:
            raise ValueError('invalid newc header') from e
        mode, size, namesize = h[1], h[6], h[11]
        start = off + 110
        if namesize < 1 or namesize > 4096 or start + namesize > len(data):
            raise ValueError('invalid newc name bounds')
        raw = data[start:start+namesize]
        if raw[-1:] != b'\0' or b'\0' in raw[:-1]:
            raise ValueError('invalid newc name')
        name = raw[:-1].decode('utf-8')
        if name.startswith('./'):
            name = name[2:]
        path = PurePosixPath(name)
        if not name or path.is_absolute() or '..' in path.parts:
            raise ValueError('unsafe newc path')
        at = (start + namesize + 3) & ~3
        end = at + size
        if end > len(data):
            raise ValueError('truncated newc payload')
        off = (end + 3) & ~3
        if name == 'TRAILER!!!':
            if size or any(data[off:]):
                raise ValueError('nonzero data after newc trailer')
            return out
        if name in out:
            raise ValueError('duplicate newc path')
        out[name] = (mode, data[at:end])
    raise ValueError('missing newc trailer')


def pack_newc(entries):
    out = bytearray()
    for ino, (name, (mode, payload)) in enumerate(
            list(sorted(entries.items())) + [('TRAILER!!!', (0, b''))], 1):
        n = name.encode() + b'\0'
        fields = (ino, mode, 0, 0, 1, 0, len(payload), 0, 0, 0, 0, len(n), 0)
        out += b'070701' + ''.join('%08x' % v for v in fields).encode() + n
        out += bytes(-len(out) % 4)
        out += payload
        out += bytes(-len(out) % 4)
    return bytes(out) + bytes(-len(out) % 512)


def static_arm64(data):
    if len(data) < 64 or data[:6] != b'\x7fELF\x02\x01':
        raise ValueError('need little-endian ELF64')
    typ, machine = struct.unpack_from('<HH', data, 16)
    phoff, = struct.unpack_from('<Q', data, 32)
    entsize, count = struct.unpack_from('<HH', data, 54)
    if typ != 2 or machine != 183 or entsize != 56 or not count:
        raise ValueError('need static executable AArch64 ELF')
    if phoff + count * entsize > len(data):
        raise ValueError('truncated ELF program table')
    for i in range(count):
        typ, = struct.unpack_from('<I', data, phoff + i * entsize)
        if typ in (2, 3):
            raise ValueError('dynamic ELF is not allowed')


def module_order(dep_text):
    graph = {}
    for line in dep_text.splitlines():
        key, sep, tail = line.partition(':')
        if not sep:
            raise ValueError('invalid modules.dep')
        name = PurePosixPath(key).name
        if name in graph:
            raise ValueError('duplicate module key')
        graph[name] = [PurePosixPath(x).name for x in tail.split()]
    result, active = [], set()
    def visit(name):
        if name not in ALLOWED:
            raise ValueError('unreviewed module dependency: ' + name)
        if name in active:
            raise ValueError('module dependency cycle')
        if name in result:
            return
        if name not in graph:
            raise ValueError('module dependency missing: ' + name)
        active.add(name)
        for dep in graph[name]:
            visit(dep)
        active.remove(name)
        result.append(name)
    for seed in SEEDS:
        visit(seed)
    return result


def collector_entries(source, script):
    def regular(name):
        mode, payload = source[name]
        if not stat.S_ISREG(mode):
            raise ValueError('input is not regular: ' + name)
        return payload
    busybox = regular('system/bin/busybox')
    static_arm64(busybox)
    order = module_order(regular('lib/modules/modules.dep').decode())
    entries = {}
    def put(name, mode, data=b''):
        parts = PurePosixPath(name).parts
        for i in range(1, len(parts)):
            entries.setdefault('/'.join(parts[:i]), (stat.S_IFDIR | 0o755, b''))
        entries[name] = (mode, data)
    put(BASE + '/busybox', stat.S_IFREG | 0o755, busybox)
    put(BASE + '/init', stat.S_IFREG | 0o755, script)
    put(BASE + '/modules.list', stat.S_IFREG | 0o644, ('\n'.join(order)+'\n').encode())
    hashes = {}
    vermagics = set()
    for name in order:
        blob = regular('lib/modules/' + name)
        if blob[:6] != b'\x7fELF\x02\x01' or struct.unpack_from('<HH', blob, 16) != (1,183):
            raise ValueError('need AArch64 relocatable module: ' + name)
        versions = re.findall(rb'(?:^|\x00)vermagic=([^\x00]+)', blob)
        if len(versions) != 1:
            raise ValueError('missing/ambiguous module vermagic')
        vermagics.add(versions[0].decode())
        put(BASE + '/modules/' + name, stat.S_IFREG | 0o644, blob)
        hashes[name] = sha(blob)
    if len(vermagics) != 1:
        raise ValueError('module vermagic mismatch')
    for name in APPLETS:
        put(BASE + '/bin/' + name, stat.S_IFLNK | 0o777, b'../busybox')
    metadata = dict(format=1, modules=hashes, module_order=order,
                    vermagic=next(iter(vermagics)), busybox_sha256=sha(busybox),
                    init_sha256=sha(script), block_mounts=False, command_receiver=False)
    put(BASE + '/build.json', stat.S_IFREG | 0o644,
        (json.dumps(metadata, sort_keys=True, indent=2)+'\n').encode())
    return entries, metadata


def rebuild_boot(template, ramdisk, out):
    if len(template) < 4096:
        raise ValueError('truncated boot header')
    h = mkbootimg.parse(template)
    if h['header_version'] != 4 or struct.unpack_from('<I', template, 20)[0] != 1584:
        raise ValueError('need boot v4 header')
    ks, rs = h['kernel_size'], h['ramdisk_size']
    sigoff = 4096 + mkbootimg.pad(ks) + mkbootimg.pad(rs)
    if ks < 64 or sigoff + h['signature_size'] > len(template):
        raise ValueError('truncated boot component')
    cmd = h['cmdline'].decode()
    if any(x.startswith(('init=', 'rdinit=')) for x in cmd.split()):
        raise ValueError('existing init override is not allowed')
    cmd = (cmd + ' ' + ' '.join(PARAMS)).strip()
    if len(cmd.encode()) >= 1536:
        raise ValueError('boot command line too long')
    kernel = template[4096:4096+ks]
    mkbootimg.build(kernel, ramdisk, cmd, out, header_version=4,
                    os_version=h['os_version'], signature_size=h['signature_size'],
                    signature=h['signature'])
    result = Path(out).read_bytes(); rh = mkbootimg.parse(result)
    if result[4096:4096+ks] != kernel or rh['signature'] != h['signature']:
        raise ValueError('kernel or signature changed')
    return dict(kernel_sha256=sha(kernel), source_boot_sha256=sha(template),
                boot_sha256=sha(result), boot_bytes=len(result), cmdline=cmd,
                signature_retained=True, signature_revalidated=False)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--recovery-cpio', required=True)
    ap.add_argument('--template', required=True, help='already validated GPUEB entryprobe boot-v4 image')
    ap.add_argument('--out', required=True)
    ap.add_argument('--lz4', default='lz4')
    a = ap.parse_args()
    out = Path(a.out); source = Path(a.recovery_cpio)
    inputs = {source.resolve(), Path(a.template).resolve()}
    if out.resolve() in inputs or out.with_suffix('.cpio.lz4').resolve() in inputs:
        raise ValueError('output must not overwrite input')
    entries, metadata = collector_entries(read_newc(source.read_bytes()),
                                         (ROOT/'ramcollector/init').read_bytes())
    archive = pack_newc(entries)
    if read_newc(archive) != entries:
        raise ValueError('cpio self-verification failed')
    ramdisk = compress_ramdisk(archive, a.lz4)
    out.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=out.parent) as tmp:
        built = Path(tmp)/'boot.img'
        report = rebuild_boot(Path(a.template).read_bytes(), ramdisk, built)
        if report['boot_bytes'] > 64*1024*1024:
            raise ValueError('boot image exceeds boot_a capacity')
        built.replace(out)
    out.with_suffix('.cpio.lz4').write_bytes(ramdisk)
    report.update(metadata); report.update(ramdisk_sha256=sha(ramdisk),
                   ramdisk_bytes=len(ramdisk), archive_bytes=len(archive),
                   source_cpio_sha256=sha(source.read_bytes()),
                   ramdisk_compression='legacy-lz4', boot_tested=False)
    out.with_suffix('.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))


if __name__ == '__main__':
    main()
