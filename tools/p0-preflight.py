#!/usr/bin/env python3
"""Static preflight for the 0086 PID-1 stall diagnostic.

Checks the prepared payload/kernel pair and the sampler source/evidence. It
does not start QEMU, attach to a guest, or modify an image.
"""
import hashlib
import pathlib
import re
import struct
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
PAYLOAD = ROOT / 'research/vm/payload-0086-launchd-sample.bin'
ORIGINAL_PAYLOAD = ROOT / 'research/vm/payload-0086-iconagent.bin'
KERNEL = ROOT / 'xnu/out-0086-trace/kernel.development.sweet'
SOURCE = ROOT / 'research/buildtree-0084/tree/src/xnu'
SUCCESS = ROOT / 'research/vm/run20h-hour/snap001/msgbuf.txt'
STALL = ROOT / 'research/vm/run20h-0086-repeatable-wake-1h/snap002/msgbuf.txt'
PID1_EVIDENCE = ROOT / 'research/vm/run0084b/snap006/msgbuf.txt'
EXPECTED_KERNEL_SHA256 = '11bb2b36b806b92556a6d4aee75eb3a269dcbabfdce03fe5b01430647583ec43'
EXPECTED_PAYLOAD_SHA256 = '0f31237b363d9d444c3b4d70e7671cb40790e39e00c7cf44bfbe8c9a4c70b673'

failures = []


def check(condition, description, detail=''):
    if condition:
        print(f'[PASS] {description}')
        return True
    message = f'{description}: {detail}' if detail else description
    failures.append(message)
    print(f'[FAIL] {message}')
    return False


def symbol_table(kernel):
    symbols = {}
    offset = 32
    for _ in range(struct.unpack_from('<I', kernel, 16)[0]):
        command, size = struct.unpack_from('<II', kernel, offset)
        if command == 2:
            symoff, nsyms, stroff, strsize = struct.unpack_from('<4I', kernel, offset + 8)
            strings = kernel[stroff:stroff + strsize]
            for index in range(nsyms):
                name_offset, _, _, _, value = struct.unpack_from('<IBBHQ', kernel, symoff + index * 16)
                end = strings.find(b'\0', name_offset)
                symbols[strings[name_offset:end].decode('latin1')] = value
        offset += size
    return symbols


def read_text(path):
    return path.read_text(encoding='utf-8', errors='replace')


def main():
    required = [
        PAYLOAD,
        ORIGINAL_PAYLOAD,
        KERNEL,
        SOURCE / 'bsd/dev/sweet_sample.c',
        SOURCE / 'bsd/dev/sweet_virtio_blk.c',
        SOURCE / 'bsd/kern/kern_exec.c',
        SOURCE / 'bsd/kern/kern_proc.c',
        SOURCE / 'osfmk/kern/exception.c',
        ROOT / 'github-clone/hackios-xnu-userland/userland/src/init.c',
    ]
    for path in required:
        try:
            label = path.relative_to(ROOT)
        except ValueError:
            label = path
        check(path.is_file(), f'input exists: {label}')
    if failures:
        print('\nP0 preflight cannot continue: required artifact is missing.')
        return 1

    payload = PAYLOAD.read_bytes()
    original = ORIGINAL_PAYLOAD.read_bytes()
    boot_args = payload[0x48:0x48 + 608].split(b'\0', 1)[0].decode('latin1')
    args = boot_args.split()
    sample_arg = next((arg for arg in args if arg.startswith('sweetsample=')), '')
    sample_names = sample_arg.split('=', 1)[1].split(',') if '=' in sample_arg else []

    check(hashlib.sha256(payload).hexdigest() == EXPECTED_PAYLOAD_SHA256,
          'payload SHA-256 matches the prepared artifact', hashlib.sha256(payload).hexdigest())
    check(len(payload) == len(original), 'payload length matches the original 0086 payload')
    check(payload[0:0x48] == original[0:0x48] and
          payload[0x48 + 608:] == original[0x48 + 608:],
          'only the fixed 608-byte boot-args field differs from the original payload')
    check(sample_names[:1] == ['launchd'] and 'launchd' in sample_names,
          'sweetsample includes PID 1 process name launchd', sample_arg)
    check(len(sample_arg) < 128,
          'sweetsample fits the kernel 128-byte parse buffer', f'{len(sample_arg)} bytes')
    check('rd=vblk0' in args and 'rootrw=1' in args,
          'boot args keep the external virtio-blk HFS root writable')
    check('virtio_input=1' in args and 'ramfb=1' in args,
          'boot args keep virtio input and ramfb for interaction')

    kernel = KERNEL.read_bytes()
    check(hashlib.sha256(kernel).hexdigest() == EXPECTED_KERNEL_SHA256,
          'kernel SHA-256 matches 0086', hashlib.sha256(kernel).hexdigest())
    symbols = symbol_table(kernel)
    for name in ('_sweet_sample_names', '_sweet_sample_start', '_sweet_sample_task',
                 '_sweet_sample_thread', '_initproc', '_proc_struct_size', '_kernel_stack_size'):
        check(name in symbols and symbols[name] != 0, f'kernel symbol present: {name}',
              hex(symbols.get(name, 0)))

    sampler = read_text(SOURCE / 'bsd/dev/sweet_sample.c')
    check('proc_name(proc_pid(p), name, sizeof(name))' in sampler,
          'sampler resolves each process name through proc_name')
    check('PE_parse_boot_argn("sweetsample"' in sampler,
          'sampler parses the sweetsample boot argument')
    check('tsleep(&chan, PZERO, "sweetsmp", 90 * hz)' in sampler,
          'sampler first sample is 90 guest seconds after start')
    check('tsleep(&chan, PZERO, "sweetsmp", 120 * hz)' in sampler,
          'sampler repeats every 120 guest seconds')
    check('proc_iterate(PROC_ALLPROCLIST, sweet_sample_proc' in sampler,
          'sampler iterates all processes, including PID 1')
    check('printf("SMP --- sample %d\\n"' in sampler,
          'sampler emits an observable sample marker')

    exception = read_text(SOURCE / 'osfmk/kern/exception.c')
    check('sweet_sample_task' in exception and 'find_user_regs(thread)' in exception,
          'kernel sampler reads each thread saved user state')
    check('vm_map_read_user(map, fp, frame, sizeof(frame))' in exception,
          'kernel sampler walks user frame pointers through vm_map_read_user')

    virtio_blk = read_text(SOURCE / 'bsd/dev/sweet_virtio_blk.c')
    check('PE_parse_boot_argn("sweetsample", sample_names, sizeof(sample_names))' in virtio_blk,
          'virtio-blk parses sweetsample before attaching /dev/vblk0')
    check('sweet_sample_start();' in virtio_blk,
          'virtio-blk starts the sampler on the QEMU /dev/vblk0 path')

    init = read_text(ROOT / 'github-clone/hackios-xnu-userland/userland/src/init.c')
    check('const size_t size = 64u << 20, step = 4096;' in init,
          'PID 1 test_memory uses the expected 64 MiB, 4 KiB stride')
    check('mem[off / sizeof(*mem)] = off ^ 0x5a5a5a5a5a5a5a5aUL' in init,
          'PID 1 test_memory store address is the observed fault site')
    check('run_rc(in_image("/etc/rc"));' in init,
          'PID 1 reaches /etc/rc after the self-tests')

    exec_source = read_text(SOURCE / 'bsd/kern/kern_exec.c')
    proc_source = read_text(SOURCE / 'bsd/kern/kern_proc.c')
    check('set_proc_name(imgp, p);' in exec_source and 'p->p_comm' in exec_source,
          'exec sets p_comm from the executable basename')
    check('strlcpy(buf, &p->p_comm[0], size);' in proc_source,
          'proc_name returns p_comm, so /sbin/launchd matches launchd')

    check(PID1_EVIDENCE.is_file(), 'historical PID 1 sampler evidence exists')
    if PID1_EVIDENCE.is_file():
        evidence = read_text(PID1_EVIDENCE)
        check(re.search(r'SMP launchd\.ios\[1\] slide 0x[0-9a-f]+ mh 0x[0-9a-f]+', evidence) is not None,
              'historical sampler emitted a PID 1 header')
        check(re.search(r'SMP launchd\.ios t0 pc 0x[0-9a-f]+ lr 0x[0-9a-f]+ sp 0x[0-9a-f]+ bt', evidence) is not None,
              'historical sampler emitted a PID 1 user stack')

    check(SUCCESS.is_file(), 'successful run msgbuf exists')
    check(STALL.is_file(), 'stalled run msgbuf exists')
    if SUCCESS.is_file() and STALL.is_file():
        success = read_text(SUCCESS)
        stall = read_text(STALL)
        success_load = re.search(r'\[\s*([0-9.]+)\]: load_init_program: attempting to load /sbin/launchd', success)
        success_exec = re.search(r'\[\s*([0-9.]+)\]: exec launchd\.ios', success)
        stall_load = re.search(r'\[\s*([0-9.]+)\]: load_init_program: attempting to load /sbin/launchd', stall)
        check(success_load is not None and success_exec is not None,
              'successful run shows /sbin/launchd load followed by exec launchd.ios')
        check(stall_load is not None and 'exec launchd.ios' not in stall,
              'stalled run shows /sbin/launchd load without exec launchd.ios')
        if success_load and success_exec and stall_load:
            print(f'       success: load {success_load.group(1)}s -> exec {success_exec.group(1)}s')
            print(f'       stall:   load {stall_load.group(1)}s -> no exec in captured msgbuf')

    print('\nP0 preflight summary:')
    if failures:
        print(f'  {len(failures)} check(s) failed; do not start the diagnostic yet.')
        for failure in failures:
            print(f'  - {failure}')
        return 1
    print('  All checks passed. The prepared payload/kernel can sample PID 1;')
    print('  no QEMU process was started and no image was modified.')
    print('  Next: run the bounded P0 command from docs/HACKIOS_20H392_PORT.md.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
