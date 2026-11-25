#!/usr/bin/env python3
"""Require the bounded, read-only APFS integration before the kernel builds."""
import argparse
import hashlib
import json
from pathlib import Path
import re

UNITS = ('apfs_lib', 'apfs_deflate', 'apfs_zbitmap', 'apfs_vfsops', 'apfs_vnops')


def verify(root):
    ap = root / 'bsd/miscfs/apfs'
    patterns = {
        'bsd/miscfs/apfs/apfs_vfsops.c': [
            r'len > dc->size - off', r'buf_reset\(bp, B_READ\)',
            r'buf_resid\(bp\) != 0', r'buf_count\(bp\) != n',
            r'block != 512', r'blocks > UINT64_MAX / block',
            r'whyred-apfs-root', r'enabled != 1', r'whyred-apfs-volume',
            r'if \(!vfs_isrdonly\(mp\)\) return EROFS;',
            r'vfs_setflags\(mp, MNT_RDONLY \| MNT_LOCAL\)',
            r'dev.read = apfs_dev_read;', r'WHYRED APFS: mounted read-only',
        ],
        'bsd/miscfs/apfs/apfs_lib.c': [r'nx->block_count > UINT64_MAX / bs',
            r'nx->block_count > nx->dev.size / bs', r'desc_blocks > 1024',
            r'le32\(blk \+ 36\) != bs', r'if \(zerr != Z_STREAM_END\)'],
        'bsd/miscfs/apfs/apfs_lib.h': [r'#define APFS_CACHE_BLOCKS 256'],
        'bsd/miscfs/apfs/apfs_deflate.c': [r'#define FREESTANDING 1', r'#undef ARCH_ARM64', r'#undef ARCH_X86_64'],
        'bsd/miscfs/apfs/apfs_vnops.c': [r'return EROFS;', r'UPL_COMMIT_CLEAR_DIRTY', r'INT64_MAX - \(uint64_t\)ap->a_size', r'whole > MIN\(XATTR_MAXSIZE, 1024 \* 1024\)'],
        'bsd/vfs/vfs_conf.c': [r'vfc_name = "apfs"', r'vfc_mountroot = apfs_mountroot', r'&apfs_vnodeop_opv_desc', r'VFC_VFSNATIVEXATTR'],
        'bsd/dev/whyred_emmc_pio_probe.c': [
            r'case DKIOCSETBLOCKSIZE:',
            r'return \*v32 == WHYRED_GPT_BLOCK_BYTES \? 0 : EINVAL;',
            r'return \(flags & FWRITE\) \? EROFS : 0;',
            r'if \(\(buf_flags\(bp\) & B_READ\) == 0\) {\s*error = EROFS;',
            r'case DKIOCISWRITABLE:\s*\*v32 = 0;',
        ],
        'bsd/kern/bsd_init.c': [
            r'#include <sweet_hfs/core/hfs_mount.h>',
            r'struct hfs_mount_args hfs_args;',
            r'\.hfs_args = { \.hfs_mask = 0777 }',
            r'"/private/var", &mount_args, sizeof\(mount_args\)',
            r'KERNEL_MOUNT_NOAUTH \| KERNEL_MOUNT_WHYRED_RAMVAR',
            r'WHYRED VAR: mounting RAM HFS before PID 1',
        ],
        'bsd/sweet_hfs/core/hfs_mount.h': [r'struct hfs_mount_args', r'journal_disable'],
        'bsd/sys/mount_internal.h': [
            r'KERNEL_MOUNT_WHYRED_RAMVAR\s+0x800',
            r'MNTK_SUPL_WHYRED_RAMVAR\s+0x00000002',
        ],
        'bsd/vfs/vfs_syscalls.c': [
            r'whyred_ramvar_mount', r'strncmp\(fstypename, \"hfs\"',
            r'strcmp\(cnp->cn_pnbuf, \"/private/var\"',
            r'MNT_UPDATE \| MNT_RDONLY', r'!whyred_ramvar_mount',
            r'mnt_supl_kern_flag \|= MNTK_SUPL_WHYRED_RAMVAR',
            r'char \*\*devnamepp = \(char \*\*\)fsmountargs',
            r'fsmountargs \+= sizeof\(\*devnamepp\)',
            r'whyred_ramvar_mount\) \{\s*seg = UIO_SYSSPACE',
        ],
        'bsd/sweet_hfs/core/hfs_vfsops.c': [
            r'#include <sys/mount_internal\.h>',
            r'mnt_supl_kern_flag & MNTK_SUPL_WHYRED_RAMVAR',
            r'bcopy\(\(const void \*\)\(uintptr_t\)data, \(caddr_t\)&args, sizeof\(args\)\)',
            r'WHYRED HFS: kernel RAM /var mount arguments accepted',
        ],
        'config/MASTER': [r'options\s+WHYRED_APFS'],
        'config/MASTER.arm64.sweet': [r'FILESYS_BASE.*\bwhyred_apfs\b'],
    }
    hashes = {}
    for rel, required in patterns.items():
        data = (root / rel).read_bytes(); text = data.decode()
        for pattern in required:
            if not re.search(pattern, text): raise SystemExit(f'{rel}: missing APFS requirement {pattern}')
        hashes[rel] = hashlib.sha256(data).hexdigest()
    init = (root / 'bsd/kern/bsd_init.c').read_text()
    var_mount = init.index('uint32_t whyred_var_md0 = 0;')
    if not (init.index('devfs_kernel_mount') < var_mount <
            init.index('bsd_utaskbootstrap();') < init.index('bsdinit_task(void)')):
        raise SystemExit('RAM HFS must mount in the kernel map before PID 1 is cloned')
    files = (root / 'bsd/conf/files').read_text()
    make = (root / 'bsd/conf/Makefile.arm64').read_text()
    for name in UNITS:
        if not re.search(r'bsd/miscfs/apfs/' + name + r'\.c\s+optional whyred_apfs', files):
            raise SystemExit(f'APFS source is not enabled: {name}')
        if f'{name}.o_CFLAGS_ADD += -mgeneral-regs-only' not in make:
            raise SystemExit(f'APFS scalar code generation missing: {name}')
    for name in ('apfs_write.c', 'apfs_store.c'):
        if (ap / name).exists(): raise SystemExit('APFS media write/store source must not be imported')
    for p in ap.rglob('*'):
        if p.is_file():
            hashes[p.relative_to(root).as_posix()] = hashlib.sha256(p.read_bytes()).hexdigest()
            if p.suffix in ('.c', '.h'):
                text = p.read_text()
                if re.search(r'#include[^\n]*hakios|thread_runnable_and_run_self|hakios_ufs_dev|hakios_virtio_blk_dev|dev\.write\s*=', text):
                    raise SystemExit(f'Unexpected platform dependency/write callback: {p}')
    return {'upstream': json.loads((ap / 'UPSTREAM.json').read_text())['commit'],
            'source_sha256': hashes, 'read_only': True, 'root_opt_in': 'whyred-apfs-root=1',
            'scalar_decoders': True, 'hardware_mount_validated': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()
    args.report.write_text(json.dumps(verify(args.source), indent=2) + '\n')
    print('whyred APFS source/readonly/scalar requirements passed')


if __name__ == '__main__': main()

