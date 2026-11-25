#!/usr/bin/env python3
"""Exercise the real eMMC open/ioctl functions and XNU's spec_open geometry path."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys


def block(text, start):
    begin = text.index('{', start)
    depth = 1
    end = begin + 1
    while depth:
        depth += (text[end] == '{') - (text[end] == '}')
        end += 1
    return end


def function(text, name):
    signature = re.search(r'^' + re.escape(name) + r'\(', text, re.M)
    if signature is None:
        raise SystemExit(f'missing driver function {name}')
    start = text.rfind('\nstatic ', 0, signature.start()) + 1
    return text[start:block(text, signature.start())]


def var_mount_harness(root):
    init_path = root / 'bsd/kern/bsd_init.c'
    header_path = root / 'bsd/sweet_hfs/core/hfs_mount.h'
    init = init_path.read_text()
    start = init.index('\tuint32_t whyred_var_md0 = 0;')
    end = init.index('\n#endif', start)
    if not (init.index('devfs_kernel_mount') < start <
            init.index('bsd_utaskbootstrap();') < init.index('bsdinit_task(void)')):
        raise SystemExit('RAM HFS must mount after devfs, before cloning PID 1')
    header = header_path.read_text()
    hs = header.index('struct hfs_mount_args {')
    structure = header[hs:block(header, hs)] + ';'
    code = r'''
#define KERNEL 1
#define uid_t uint32_t
#define gid_t uint32_t
#define mode_t uint16_t
#define u_int32_t uint32_t
struct timezone { int tz_minuteswest, tz_dsttime; };
''' + structure + r'''
#define NULLVP NULL
#define MNT_DONTBROWSE 0x100
#define KERNEL_MOUNT_NOAUTH 1
#define KERNEL_MOUNT_WHYRED_RAMVAR 0x800
static int var_requested, var_mount_calls, var_panics;
static void *vfs_context_kernel(void) { return (void *)(uintptr_t)1; }
static int PE_parse_boot_argn(const char *name, void *data, size_t size)
{
    if (strcmp(name, "whyred-var-md0") || size != sizeof(uint32_t)) return 0;
    *(uint32_t *)data = (uint32_t)var_requested;
    return 1;
}
static void panic(__unused const char *message, ...) { var_panics++; }
static int kernel_mount(const char *type, void *parent, void *covered,
    const char *path, void *data, size_t size, int flags, uint32_t kernel_flags,
    void *context)
{
    char *device;
    struct hfs_mount_args args;
    if (size != sizeof(device) + sizeof(args) || !data ||
        strcmp(type, "hfs") || strcmp(path, "/private/var") || parent || covered ||
        flags != MNT_DONTBROWSE || kernel_flags != (KERNEL_MOUNT_NOAUTH | KERNEL_MOUNT_WHYRED_RAMVAR) ||
        context != vfs_context_kernel()) return EINVAL;
    memcpy(&device, data, sizeof(device));
    memcpy(&args, (char *)data + sizeof(device), sizeof(args));
    if (strcmp(device, "/dev/md0") || args.hfs_uid || args.hfs_gid ||
        args.hfs_mask != 0777 || args.hfs_encoding || args.hfs_timezone.tz_minuteswest ||
        args.hfs_timezone.tz_dsttime || args.flags || args.journal_tbuffer_size ||
        args.journal_flags || args.journal_disable) return EINVAL;
    var_mount_calls++;
    return 0;
}
static void mount_var_from_bsd_init(void)
{
''' + init[start:end] + r'''
}
static int hfs_contract(void)
{
    char *legacy_device = "/dev/md0";
    if (kernel_mount("hfs", NULL, NULL, "/private/var", &legacy_device, 0,
        MNT_DONTBROWSE, KERNEL_MOUNT_NOAUTH, vfs_context_kernel()) != EINVAL) return 1;
    var_requested = 0;
    mount_var_from_bsd_init();
    if (var_mount_calls || var_panics) return 1;
    var_requested = 1;
    mount_var_from_bsd_init();
    if (var_mount_calls != 1 || var_panics) return 1;
    printf("whyred HFS mount contract: 3 checks passed; complete arguments before PID 1\n");
    return 0;
}
'''
    return code, (init_path, header_path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--cc', default=os.environ.get('CC') or shutil.which('clang') or 'cc')
    args = parser.parse_args()
    driver_path = args.source / 'bsd/dev/whyred_emmc_pio_probe.c'
    spec_path = args.source / 'bsd/miscfs/specfs/spec_vnops.c'
    driver = driver_path.read_text()
    spec = spec_path.read_text()
    spec_start = spec.index('spec_open(struct vnop_open_args *ap)')
    start = spec.index('if (!VNOP_IOCTL(vp, DKIOCGETBLOCKSIZE,', spec_start)
    geometry = spec[start:block(spec, start)]
    harness = r'''
#include <stdint.h>
#include <stdbool.h>
#include <stdio.h>
#include <errno.h>
#include <limits.h>
#include <string.h>
#ifndef __unused
#define __unused __attribute__((unused))
#endif
typedef uint32_t whyred_test_dev_t;
#define dev_t whyred_test_dev_t
#define caddr_t char *
#define u_long unsigned long
#define minor(d) ((d) & 0xffffffU)
#define MIN(a, b) ((a) < (b) ? (a) : (b))
#define FREAD 1
#define FWRITE 2
#define WHYRED_GPT_MAX_ENTRIES 64
#define WHYRED_GPT_BLOCK_BYTES 512
enum {
    DKIOCGETBLOCKSIZE = 1, DKIOCGETPHYSICALBLOCKSIZE, DKIOCSETBLOCKSIZE,
    DKIOCGETBLOCKCOUNT, DKIOCISWRITABLE, DKIOCGETMAXBLOCKCOUNTREAD,
    DKIOCGETMAXSEGMENTCOUNTREAD, DKIOCGETMAXBLOCKCOUNTWRITE,
    DKIOCGETMAXSEGMENTCOUNTWRITE
};
struct proc { int unused; };
struct whyred_gpt_partition { uint32_t index; uint64_t first, last; };
static struct whyred_gpt_partition whyred_gpt_parts[WHYRED_GPT_MAX_ENTRIES];
static uint32_t whyred_gpt_part_count;
static bool whyred_emmc_block_ready;
''' + '\n'.join(function(driver, name) for name in (
        'whyred_emmc_partition', 'whyred_emmc_open', 'whyred_emmc_ioctl', 'whyred_emmc_psize')) + r'''
struct vnode { dev_t v_rdev; int v_specsize; };
struct vnop_open_args { void *a_context; };
static int emulate_missing_setblocksize;
static int
test_ioctl(struct vnode *vp, u_long cmd, caddr_t data, int flags,
    __unused void *context)
{
    if (emulate_missing_setblocksize && cmd == DKIOCSETBLOCKSIZE)
        return ENOTTY;
    return whyred_emmc_ioctl(vp->v_rdev, cmd, data, flags, NULL);
}
#define VNOP_IOCTL test_ioctl
static int
root_geometry_open(dev_t dev, int flags)
{
    int error = whyred_emmc_open(dev, flags, 0, NULL);
    if (error) return error;
    struct vnode node = { .v_rdev = dev };
    struct vnode *vp = &node;
    struct vnop_open_args arguments = { NULL };
    struct vnop_open_args *ap = &arguments;
    uint64_t blkcnt = 0;
    uint32_t blksize = 0, size512 = 512;
    int setsize = 0;
''' + geometry + r'''
    if (!error && (!setsize || blksize != 512 || blkcnt != 1024)) return EIO;
    return error;
}
#define CHECK(expr) do { checks++; if (!(expr)) { \
    fprintf(stderr, "failed at line %d: %s\n", __LINE__, #expr); return 1; \
} } while (0)
int main(void)
{
    unsigned int checks = 0;
    uint32_t value32;
    uint64_t value64;
    const dev_t disk = 61;
    whyred_gpt_parts[0].index = disk;
    whyred_gpt_parts[0].first = 128;
    whyred_gpt_parts[0].last = 1151;
    whyred_gpt_part_count = 1;
    whyred_emmc_block_ready = true;
    emulate_missing_setblocksize = 1;
    CHECK(root_geometry_open(disk, FREAD) == ENXIO);
    emulate_missing_setblocksize = 0;
    CHECK(root_geometry_open(disk, FREAD) == 0);
    CHECK(root_geometry_open(disk, FREAD | FWRITE) == EROFS);
    CHECK(whyred_emmc_open(0, FREAD, 0, NULL) == ENXIO);
    CHECK(whyred_emmc_open(65, FREAD, 0, NULL) == ENXIO);
    value32 = 0;
    CHECK(whyred_emmc_ioctl(disk, DKIOCGETBLOCKSIZE, (caddr_t)&value32, 0, NULL) == 0 && value32 == 512);
    value32 = 512;
    CHECK(whyred_emmc_ioctl(disk, DKIOCSETBLOCKSIZE, (caddr_t)&value32, FWRITE, NULL) == 0);
    value32 = 4096;
    CHECK(whyred_emmc_ioctl(disk, DKIOCSETBLOCKSIZE, (caddr_t)&value32, FWRITE, NULL) == EINVAL);
    value32 = 0;
    CHECK(whyred_emmc_ioctl(disk, DKIOCSETBLOCKSIZE, (caddr_t)&value32, FWRITE, NULL) == EINVAL);
    value32 = 1;
    CHECK(whyred_emmc_ioctl(disk, DKIOCISWRITABLE, (caddr_t)&value32, 0, NULL) == 0 && value32 == 0);
    value64 = 0;
    CHECK(whyred_emmc_ioctl(disk, DKIOCGETBLOCKCOUNT, (caddr_t)&value64, 0, NULL) == 0 && value64 == 1024);
    value64 = 1;
    CHECK(whyred_emmc_ioctl(disk, DKIOCGETMAXBLOCKCOUNTWRITE, (caddr_t)&value64, 0, NULL) == 0 && value64 == 0);
    CHECK(whyred_emmc_ioctl(disk, 9999, (caddr_t)&value64, FWRITE, NULL) == ENOTTY);
    whyred_emmc_block_ready = false;
    CHECK(whyred_emmc_open(disk, FREAD, 0, NULL) == ENXIO);
    printf("whyred eMMC contract: %u checks passed; historical spec_open failure reproduced; FWRITE denied\n", checks);
    return 0;
}
'''
    # Exercise the exact specfs unit consumer, including its16KiB read guard.
    start = re.search(r'^spec_read\(', spec, re.M).start()
    reader = spec[start:block(spec, start)]
    geometry_start = reader.index('\t\tdevBlockSize = vp->v_specsize;', reader.index('case VBLK:'))
    geometry_end = reader.index('\n\t\tdo {', geometry_start)
    read_geometry = reader[geometry_start:geometry_end]
    unit_code = r"""
#define DEV_BSIZE 512
#define PAGE_SIZE 16384
#define major(d) 0
static int emulate_psize_count;
static int test_psize(dev_t dev) {
    const struct whyred_gpt_partition *p = whyred_emmc_partition(dev);
    return emulate_psize_count && p ? (int)(p->last - p->first + 1) : whyred_emmc_psize(dev);
}
static const struct { int (*d_psize)(dev_t); } bdevsw[] = {{test_psize}};
static const int nblkdev = 1;
""" + function(spec, 'set_blocksize') + r"""
static int spec_read_geometry(dev_t dev, int *unit, size_t *transfer) {
    struct vnode node = { .v_rdev = dev }, *vp = &node;
    int devBlockSize;
    long bscale;
    size_t bsize;
    set_blocksize(vp, dev);
""" + read_geometry + r"""
    *unit = vp->v_specsize;
    *transfer = bsize;
    return 0;
}
"""
    harness = harness.replace('struct vnop_open_args {', unit_code + '\nstruct vnop_open_args {')
    unit_checks = r"""
    int unit = 0; size_t transfer = 0;
    whyred_gpt_parts[0].last = whyred_gpt_parts[0].first + 65536 - 1;
    emulate_psize_count = 1;
    CHECK(spec_read_geometry(disk, &unit, &transfer) == EINVAL);
    emulate_psize_count = 0;
    const uint64_t capacities[] = {16, 1024, 65536, 61071360};
    for (unsigned i = 0; i < sizeof(capacities) / sizeof(*capacities); i++) {
        whyred_gpt_parts[0].last = whyred_gpt_parts[0].first + capacities[i] - 1;
        CHECK(whyred_emmc_psize(disk) == 512);
        CHECK(spec_read_geometry(disk, &unit, &transfer) == 0 && unit == 512 && transfer == PAGE_SIZE);
        value64 = 0;
        CHECK(whyred_emmc_ioctl(disk, DKIOCGETBLOCKCOUNT, (caddr_t)&value64, 0, NULL) == 0 && value64 == capacities[i]);
    }
    CHECK(whyred_emmc_psize(0) == -1);
    CHECK(whyred_emmc_psize(65) == -1);
"""
    harness = harness.replace('    whyred_emmc_block_ready = false;', unit_checks + '\n    whyred_emmc_block_ready = false;')
    var_code, var_paths = var_mount_harness(args.source)
    harness = harness.replace('#define CHECK(expr)', var_code + '\n#define CHECK(expr)')
    harness = harness.replace('    printf("whyred eMMC contract:',
                              '    if (hfs_contract() != 0) return 1;\n    printf("whyred eMMC contract:')
    args.output.mkdir(parents=True, exist_ok=True)
    source = args.output / 'emmc-contract.c'
    executable = args.output / ('emmc-contract.exe' if os.name == 'nt' else 'emmc-contract')
    source.write_text(harness)
    host_env = os.environ.copy()
    host_env.pop('SDKROOT', None)
    compiler = [args.cc, '-std=c11', '-Wall', '-Wextra', '-Werror', '-O1']
    if sys.platform == 'darwin':
        sdk = subprocess.check_output(['xcrun', '--sdk', 'macosx', '--show-sdk-path'],
                                      text=True, env=host_env).strip()
        compiler += ['-isysroot', sdk]
    subprocess.run([*compiler, str(source), '-o', str(executable)],
                   check=True, env=host_env)
    result = subprocess.check_output([str(executable.resolve())], text=True, env=host_env)
    print(result, end='')
    report = {'result': result.strip(), 'source_sha256': {
        p.relative_to(args.source).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in (driver_path, spec_path, *var_paths)}, 'hardware_emulated': False}
    (args.output / 'report.json').write_text(json.dumps(report, indent=2) + '\n')


if __name__ == '__main__':
    main()
