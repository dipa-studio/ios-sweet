#!/usr/bin/env python3
"""Prepare a pinned boot99 block-unit backport; no device access.

One ARM64 result instruction implements source patch0178. The supported
sweetnull=- argument stops the dev/null diagnostic tee flooding UART. Keeping all addresses
and the layout UUID preserves System102's matched display/debug ABI. This is
explicitly a modified kernel, identified by its new SHA, not an unchanged99.
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import uuid

KERNEL99 = '961ee9a4f92e4fd595c3825ffa470a5efed1604ad7ba819fa6cadff879adfc1c'
BOOT99 = 'e2c8a0066f8b651d79e7d8e158d57a0806a53e16421c4d80c39e8633c05e28ff'
UUID99 = '2ED4E8A4-6D1C-3C3C-980B-8533C25978D1'
FUNCTION = 0xfffffe000795ebe4
PATCH_VA = FUNCTION + 0x58
OLD = struct.pack('<I', 0x9a882540)  # csinc x0,x10,x8,hs: clamped sector count
NEW = struct.pack('<I', 0x52804000)  # mov w0,#512: fixed block bytes


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def mapped(offsets, address, count):
    matches = [off + address - va for va, size, off in offsets
               if va <= address and address + count <= va + size]
    require(len(matches) == 1, 'Ambiguous/out-of-range code mapping')
    return matches[0]


def replace_word(data, offset):
    require(data[offset:offset + 4] == OLD, 'Original return instruction differs')
    result = data[:offset] + NEW + data[offset + 4:]
    require(len(result) == len(data) and result[:offset] == data[:offset] and
            result[offset + 4:] == data[offset + 4:], 'Unexpected binary change')
    return result


def boot_parts(data):
    require(data[:8] == b'ANDROID!' and len(data) >= 4096, 'Invalid boot image')
    ks, _, rs, _, ss, _, _, page, version, _ = struct.unpack_from('<10I', data, 8)
    require(page == 4096 and version == 0, 'Expected exact boot99 v0 header')
    offset, parts = page, []
    for name, size in [('kernel', ks), ('ramdisk', rs), ('second', ss)]:
        require(offset + size <= len(data), 'Boot component exceeds image')
        parts.append((name, offset, size))
        offset += (size + page - 1) // page * page
    require(offset == len(data), 'Unexpected trailing boot components')
    return parts


def boot_id(data, parts):
    result = hashlib.sha1()
    for _, offset, size in parts:
        result.update(data[offset:offset + size])
        result.update(struct.pack('<I', size))
    return result.digest() + b'\0' * 12


def prepare(kernel, boot):
    require(digest(kernel) == KERNEL99 and digest(boot) == BOOT99, 'Pinned baseline digest mismatch')
    require(struct.unpack_from('<I', kernel)[0] == 0xfeedfacf, 'Invalid Mach-O')
    commands = struct.unpack_from('<I', kernel, 16)[0]
    cursor, mappings, uuids = 32, [], []
    for _ in range(commands):
        cmd, size = struct.unpack_from('<II', kernel, cursor)
        require(size >= 8 and cursor + size <= len(kernel), 'Invalid Mach-O command')
        if cmd == 0x19:
            va, _, off, count = struct.unpack_from('<4Q', kernel, cursor + 24)
            mappings.append((va, count, off))
        if cmd == 0x1b:
            uuids.append(str(uuid.UUID(bytes=kernel[cursor + 8:cursor + 24])).upper())
        cursor += size
    require(uuids == [UUID99], 'Layout UUID differs')
    ko = mapped(mappings, PATCH_VA, 4)
    fo = mapped(mappings, FUNCTION, 0x60)
    require(kernel[fo + 0x3c:fo + 0x44] == struct.pack('<2I', 0x12800000, 0xd65f03c0) and
            kernel[fo + 0x5c:fo + 0x60] == struct.pack('<I', 0xd65f03c0), 'Invalid/valid return layout changed')
    new_kernel = replace_word(kernel, ko)
    parts = boot_parts(boot)
    require(boot[576:608] == boot_id(boot, parts), 'Baseline Android image ID differs')
    _, start, size = next(p for p in parts if p[0] == 'ramdisk')
    payload = boot[start:start + size]
    require(payload[:8] == b'SWEETXNU', 'Expected shim payload absent')
    version, count = struct.unpack_from('<2I', payload, 8)
    require(version == 1 and 1 <= count <= 16, 'Invalid shim segment count')
    rows = [struct.unpack_from('<4Q', payload, 0x2a8 + i * 32) for i in range(count)]
    po = mapped([(va, n, off) for va, _, off, n in rows], PATCH_VA, 4)
    pf = mapped([(va, n, off) for va, _, off, n in rows], FUNCTION, 0x60)
    require(payload[pf:pf + 0x60] == kernel[fo:fo + 0x60], 'Loaded function differs from linked kernel')
    changed = replace_word(payload, po)
    old_line = payload[0x48:0x48 + 608].split(b'\0')[0]
    require(b'sweetnull=' not in old_line, 'Unexpected baseline dev/null tee policy')
    new_line = old_line + b' sweetnull=-'
    require(len(new_line) < 608, 'Boot arguments would be truncated')
    changed = changed[:0x48] + new_line.ljust(608, b'\0') + changed[0x48 + 608:]
    new_boot = boot[:start] + changed + boot[start + size:]
    new_boot = new_boot[:576] + boot_id(new_boot, parts) + new_boot[608:]
    allowed = set(range(start + po, start + po + 4)) | set(range(576, 608)) | set(range(start + 0x48, start + 0x48 + 608))
    differences = [i for i, (a, b) in enumerate(zip(boot, new_boot)) if a != b]
    require(len(new_boot) == len(boot) and differences and set(differences) <= allowed,
            'Unexpected boot byte changes')
    require(new_boot[start + pf:start + pf + 0x60] == new_kernel[fo:fo + 0x60],
            'Kernel/payload patch disagreement')
    report = dict(version=103,base_boot_sha256=BOOT99,base_kernel_sha256=KERNEL99,
                  image_sha256=digest(new_boot),image_bytes=len(new_boot),
                  kernel_sha256=digest(new_kernel),kernel_layout_uuid=UUID99,
                  kernel_uuid_intentionally_preserved=True,kernel_binary_modified=True,
                  kernel_changed_instruction_count=1,kernel_changed_instruction_va=hex(PATCH_VA),
                  kernel_patch_offset=ko,payload_patch_offset=po,boot_patch_offset=start+po,
                  old_instruction_hex=OLD.hex(),new_instruction_hex=NEW.hex(),
                  boot_changed_byte_offsets=differences,only_code_cmdline_and_android_id_changed=True,
                  shim_adt_and_other_kernel_bytes_unchanged=True,
                  original_boot_arguments_preserved=True,added_boot_argument='sweetnull=-',
                  original_cmdline=old_line.decode(),cmdline=new_line.decode(),
                  devnull_diagnostic_tee_disabled=True,
                  new_full_kernel_ci_build=False,source_fix='0178-whyred-emmc-psize-block-unit.patch',
                  device_writes=False,hardware_verified=False)
    return new_kernel, changed, new_boot, report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--kernel99', type=Path, required=True)
    parser.add_argument('--boot99', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    require(not args.output.exists(), 'Refusing to replace a prior candidate')
    kernel, payload, boot, report = prepare(args.kernel99.read_bytes(), args.boot99.read_bytes())
    args.output.mkdir(mode=0o700, parents=True)
    for name, data in [('kernel.development.whyred', kernel), ('payload.bin', payload),
                       ('shim-boot-whyred-psize.img', boot)]:
        path = args.output / name
        path.write_bytes(data); path.chmod(0o600)
    report['builder_sha256'] = digest(Path(__file__).read_bytes())
    (args.output / 'manifest.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
