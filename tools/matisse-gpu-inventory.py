#!/usr/bin/env python3
"""Read-only Recovery GPU inventory. Dumps stay in ignored research/, never git.

Does not mount, load modules, open /dev/mali0, access MMIO, or write devices.
Existing read-only vendor mounts can be searched with --firmware-root.
"""
import argparse
import gzip
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import shlex
import struct
import subprocess


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def parse_fdt(data):
    """Parse bounded v17+ FDT data; return path -> raw property dictionaries."""
    if len(data) < 40:
        raise ValueError('truncated FDT header')
    magic, total, off, strings_off, _, version, compatible, _, strings_len, size = struct.unpack_from('>10I', data)
    if magic != 0xd00dfeed or total > len(data) or total < 40:
        raise ValueError('invalid FDT magic/size')
    if version < 17 or compatible > 17:
        raise ValueError('unsupported FDT version')
    if off < 40 or off % 4 or strings_off < 40 or off + size > total or strings_off + strings_len > total:
        raise ValueError('invalid FDT block bounds')
    strings = data[strings_off:strings_off + strings_len]
    end = off + size
    nodes, stack = {}, []
    root_seen = False
    while off + 4 <= end:
        tag, = struct.unpack_from('>I', data, off)
        off += 4
        if tag == 1:
            nul = data.find(b'\0', off, end)
            if nul < 0:
                raise ValueError('unterminated node')
            name = data[off:nul].decode('ascii')
            off = (nul + 4) & ~3
            if '/' in name or (not stack and (name or root_seen)):
                raise ValueError('invalid root/node name')
            path = '/' if not stack else stack[-1].rstrip('/') + '/' + name
            if path in nodes:
                raise ValueError('duplicate FDT node')
            root_seen = True
            nodes[path] = {}
            stack.append(path)
        elif tag == 2:
            if not stack:
                raise ValueError('unbalanced FDT node')
            stack.pop()
        elif tag == 3:
            if not stack or off + 8 > end:
                raise ValueError('invalid FDT property')
            length, nameoff = struct.unpack_from('>II', data, off)
            off += 8
            nul = strings.find(b'\0', nameoff)
            if nameoff >= len(strings) or nul < 0 or off + length > end:
                raise ValueError('invalid property bounds')
            name = strings[nameoff:nul].decode('ascii')
            if name in nodes[stack[-1]]:
                raise ValueError('duplicate FDT property')
            nodes[stack[-1]][name] = data[off:off + length]
            off = (off + length + 3) & ~3
        elif tag == 4:
            continue
        elif tag == 9:
            if stack or not root_seen:
                raise ValueError('unbalanced/incomplete FDT')
            return nodes
        else:
            raise ValueError('unknown FDT token')
    raise ValueError('missing FDT end token')


def property_value(data, name=None):
    if not data:
        return True
    string_property = name in {'compatible', 'model', 'name', 'status', 'target-path',
                               'regulator-name', 'device_type', 'bootargs'} or (name or '').endswith(('names', 'name_table'))
    if string_property and data.endswith(b'\0') and all(x == 0 or 32 <= x < 127 for x in data):
        return {'strings': data.rstrip(b'\0').decode('ascii').split('\0')}
    if len(data) % 4 == 0:
        return {'cells': ['0x%x' % v for v in struct.unpack('>%dI' % (len(data) // 4), data)]}
    return {'hex': data.hex()}


def gpu_nodes(nodes):
    """GPU nodes, reserved regions, and transitively referenced DT phandles."""
    selected = {p for p in nodes if re.search(r'mali|gpu|mfg|protected-memory', p, re.I)
                and not p.startswith('/__symbols__')}
    selected.update(p for p in nodes if p.startswith('/reserved-memory/'))
    phandles = {}
    for p, props in nodes.items():
        for key in ('phandle', 'linux,phandle'):
            raw = props.get(key, b'')
            if len(raw) == 4:
                phandles[struct.unpack('>I', raw)[0]] = p
    reference_keys = {'operating-points-v2', 'physical-memory-group-manager',
                      'protected-memory-allocator', 'interrupt-parent',
                      'clocks', 'power-domains', 'resets', 'memory-region'}
    # phandle-array argument cells are deliberately not treated as phandles.
    # Resolve only its first provider; the raw full list remains in the report.
    todo = list(selected)
    while todo:
        p = todo.pop()
        for key, raw in nodes[p].items():
            if (key.endswith('-supply') or key in reference_keys) and len(raw) >= 4:
                target = phandles.get(struct.unpack_from('>I', raw)[0])
                if target and target not in selected:
                    selected.add(target)
                    todo.append(target)
        for child in nodes:
            if child.startswith(p.rstrip('/') + '/') and child not in selected:
                selected.add(child)
                todo.append(child)
    return {p: {k: property_value(v, k) for k, v in nodes[p].items()} for p in sorted(selected)}


def inspect_image(path):
    data = path.read_bytes()
    result = {'name': path.name, 'bytes': len(data), 'sha256': sha256(data), 'magic_hex': data[:16].hex()}
    if len(data) >= 32 and struct.unpack_from('>I', data)[0] == 0xd7b7ab1e:
        _, total, header, entry_size, count, entries, page, version = struct.unpack_from('>8I', data)
        if total > len(data) or header < 32 or entry_size < 32 or entries < header or entries + count * entry_size > total:
            raise ValueError('invalid DTBO table bounds')
        result.update(type='android-dtbo', version=version, page_size=page, overlays=[])
        for i in range(count):
            size, off, ident, rev, *custom = struct.unpack_from('>8I', data, entries + i * entry_size)
            if off + size > total:
                raise ValueError('invalid DTBO entry bounds')
            blob = data[off:off + size]
            nodes = parse_fdt(blob)
            fragments = {p: {k: property_value(v, k) for k, v in props.items()}
                         for p, props in nodes.items() if 'target' in props or 'target-path' in props}
            fixups = {p: {k: v.rstrip(b'\0').decode('ascii').split('\0') for k, v in props.items()}
                      for p, props in nodes.items() if p == '/__fixups__'}
            result['overlays'].append({'index': i, 'id': ident, 'revision': rev, 'custom': custom,
                                       'bytes': size, 'sha256': sha256(blob),
                                       'fragment_targets': fragments, 'fixups': fixups, 'gpu_nodes': gpu_nodes(nodes)})
    return result


class Recovery:
    def __init__(self, adb, output, su=False):
        self.adb, self.output, self.su = adb, output, su
        self.records = []

    def shell(self, command):
        if self.su:
            command = 'su -c ' + shlex.quote(command)
        return subprocess.run([self.adb, 'shell', command], capture_output=True, timeout=45)

    def capture(self, name, command):
        p = self.shell(command)
        data = p.stdout
        (self.output / name).write_bytes(data)
        self.records.append({'name': name, 'command': command, 'exit': p.returncode,
                             'bytes': len(data), 'sha256': sha256(data),
                             'stderr': p.stderr.decode(errors='replace')})
        return data

    def pull(self, remote, name):
        quoted = shlex.quote(remote)
        before = self.shell('sha256sum ' + quoted)
        if before.returncode or not re.match(rb'^[0-9a-f]{64}\s', before.stdout):
            raise RuntimeError('cannot hash ' + remote)
        expected = before.stdout.split()[0].decode()
        dest = self.output / name
        if self.su:
            command = 'su -c ' + shlex.quote('cat ' + quoted)
            with dest.open('wb') as stream:
                p = subprocess.run([self.adb, 'exec-out', command], stdout=stream, stderr=subprocess.PIPE, timeout=120)
        else:
            p = subprocess.run([self.adb, 'pull', remote, str(dest)], capture_output=True, timeout=120)
        if p.returncode:
            raise RuntimeError('pull failed: ' + remote + ': ' + p.stderr.decode(errors='replace'))
        data = dest.read_bytes()
        after = self.shell('sha256sum ' + quoted)
        if after.returncode or not after.stdout.split() or after.stdout.split()[0].decode() != expected or sha256(data) != expected:
            raise RuntimeError('source changed or transfer hash mismatch: ' + remote)
        self.records.append({'name': name, 'remote': remote, 'bytes': len(data),
                             'sha256': expected, 'source_hash_before_after': True})
        return data


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--adb', default=str(Path.home() / 'Library/Android/sdk/platform-tools/adb'))
    parser.add_argument('--output', type=Path, required=True, help='new directory under ignored research/')
    parser.add_argument('--su', action='store_true', help='use su -c on rooted Android')
    parser.add_argument('--offline', action='store_true', help='inspect supplied local images without adb')
    parser.add_argument('--image', type=Path, action='append', default=[])
    parser.add_argument('--firmware-root', action='append', default=[], help='existing read-only firmware/module mount')
    args = parser.parse_args()
    research = Path(__file__).resolve().parents[1] / 'research'
    output = args.output.resolve()
    if research not in output.parents:
        parser.error('output must be inside ignored research/ (contains private device data)')
    output.mkdir(parents=True, exist_ok=False)
    recovery = Recovery(args.adb, output, args.su)
    manifest = {'read_only': True, 'records': recovery.records, 'images': [], 'gpu_id_hardware_read': False}
    try:
        for path in args.image:
            manifest['images'].append(inspect_image(path))
        if args.offline:
            if not args.image or args.firmware_root:
                parser.error('--offline needs images and cannot search device firmware roots')
            print(json.dumps({'output': str(output), 'images': len(manifest['images']), 'offline': True}))
            return
        identity = recovery.capture('identity.txt', 'getprop ro.product.device; getprop ro.boot.slot_suffix; uname -r; id')
        if not identity.splitlines() or identity.splitlines()[0].strip() != b'matisse':
            raise RuntimeError('matisse is not connected/authorized; see identity record in manifest.json')
        if b'uid=0(' not in identity:
            raise RuntimeError('root required; rooted Android needs --su')
        recovery.capture('modules.txt', 'cat /proc/modules')
        recovery.capture('mounts.txt', 'cat /proc/mounts')
        recovery.capture('dmesg.txt', 'dmesg')
        recovery.capture('gpu-bindings.txt', 'ls -ld /dev/mali* /sys/class/misc/mali* /sys/bus/platform/drivers/*mali* /sys/bus/platform/drivers/*gpueb* /sys/bus/platform/drivers/*gpufreq* 2>/dev/null; cat /sys/bus/platform/devices/13000000.mali/uevent; cat /sys/bus/platform/devices/13000000.mali/power/runtime_status')
        config = recovery.pull('/proc/config.gz', 'config.gz')
        (output / 'config.txt').write_bytes(gzip.decompress(config))
        fdt = recovery.pull('/sys/firmware/fdt', 'live.dtb')
        nodes = parse_fdt(fdt)
        (output / 'gpu-dt.json').write_text(json.dumps(gpu_nodes(nodes), indent=2) + '\n')
        for i, root in enumerate(args.firmware_root):
            if not root.startswith('/') or '..' in PurePosixPath(root).parts:
                raise ValueError('firmware root must be absolute without traversal')
            listing = recovery.capture('firmware-list-%d.txt' % i,
                'find ' + shlex.quote(root) + ' -type f 2>/dev/null')
            for line in listing.decode().splitlines():
                name = PurePosixPath(line).name
                if re.search(r'csffw|^(mali_kbase|gpueb|gpufreq|gpufreq_wrapper)\.ko$', name):
                    # Root index and digest of path prevent basename collisions.
                    local = '%d-%s-%s' % (i, sha256(line.encode())[:8], name)
                    recovery.pull(line, local)
    except Exception as exc:
        manifest['error'] = str(exc)
        raise
    finally:
        (output / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print(json.dumps({'output': str(output), 'records': len(recovery.records),
                      'images': len(manifest['images']), 'gpu_id_hardware_read': False}))


if __name__ == '__main__':
    main()
