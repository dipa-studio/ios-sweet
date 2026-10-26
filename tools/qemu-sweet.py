#!/usr/bin/env python3
"""Boot a SWEETXNU payload (tools/mkpayload.py) in QEMU's virt board.

  qemu-sweet.py PAYLOAD OUTDIR [--secs N] [--gdb] [--live-serial]

Does what shim/loader.c does on the phone, but on the host: places the
kernel segments, ADT and boot_args at their physical addresses and starts
the CPU at a 6-instruction stub that jumps to the entry with x0 = boot_args.
virt RAM starts at 0x40000000; with 4G it covers the phone's framebuffer
(0x9c000000) and the kernel's phys_base (0xb0000000) as plain memory.

After N seconds (or when the guest stops) it writes into OUTDIR:
  fb.png     the 1080x2400 framebuffer (what the phone screen would show)
  regs.txt   QEMU's view of CPU state
  qemu.log   exceptions with ESR/FAR/ELR (-d int,guest_errors)

With --kernel KERNEL (the matching unstripped Mach-O), also decode the
framebuffer using its iso_font into fb.txt and write result.json. This is a
snapshot of the circular screen, not a complete boot log. --fail-on-panic
returns 2 when a panic is visible; absence of a panic does not prove boot.
An undecodable or blank screen returns 3 with --fail-on-panic.
"""
import argparse, hashlib, json, os, shutil, socket, struct, subprocess, sys, time, zlib

FB_BASE, FB_W, FB_H = 0x9c000000, 1080, 2400
FB_STRIDE = FB_W * 4
PAGE = 0x4000
STUB_PA = 0x40200000	# above the dtb QEMU places at RAM base
BOOT_LINE_LENGTH = 608


def check_qemu_dependency(cpu='cortex-a76'):
    """Verify qemu-system-aarch64 binary and CPU model support."""
    qemu_bin = shutil.which('qemu-system-aarch64')
    if not qemu_bin:
        print('[!] Error: qemu-system-aarch64 not found in PATH.', file=sys.stderr)
        print('    Install instructions:', file=sys.stderr)
        print('      Arch Linux:    sudo pacman -S qemu-system-aarch64', file=sys.stderr)
        print('      Ubuntu/Debian: sudo apt install qemu-system-arm', file=sys.stderr)
        print('      Fedora:         sudo dnf install qemu-system-aarch64', file=sys.stderr)
        print('      macOS:          brew install qemu', file=sys.stderr)
        print('      Windows:        https://www.qemu.org/download/#windows (add QEMU to PATH)', file=sys.stderr)
        return False
    try:
        ver = subprocess.check_output([qemu_bin, '--version'], text=True).splitlines()[0]
        print(f'[*] Found QEMU: {ver}', file=sys.stderr)
    except Exception as e:
        print(f'[!] Warning: Failed to query QEMU version: {e}', file=sys.stderr)
        return False

    try:
        cpu_list = subprocess.check_output([qemu_bin, '-M', 'virt', '-cpu', 'help'], text=True)
        if cpu in cpu_list:
            print(f'[*] CPU model {cpu} supported', file=sys.stderr)
        else:
            print(f'[!] Warning: CPU model {cpu} not explicitly listed in qemu-system-aarch64 -cpu help', file=sys.stderr)
    except Exception:
        pass
    return True


def check_kernel_tools(kernel_path):
    """Verify llvm-nm is available when --kernel is specified."""
    if not shutil.which('llvm-nm'):
        print('[!] Error: llvm-nm not found in PATH, required for --kernel font extraction.', file=sys.stderr)
        print('    Install instructions:', file=sys.stderr)
        print('      Arch Linux:    sudo pacman -S llvm', file=sys.stderr)
        print('      Ubuntu/Debian: sudo apt install llvm', file=sys.stderr)
        print('      Fedora:         sudo dnf install llvm', file=sys.stderr)
        print('      macOS:          brew install llvm', file=sys.stderr)
        return False
    if not os.path.isfile(kernel_path):
        print(f'[!] Error: kernel file does not exist: {kernel_path}', file=sys.stderr)
        return False
    return True


def compose_cmdline(payload, extra_cmdline='', smp=1):
    """Return the exact boot-args bytes placed in boot_args (without padding)."""
    base = payload[0x48:0x48 + BOOT_LINE_LENGTH].split(b'\0', 1)[0].decode('latin1').split()
    cpus_arg = f'cpus={smp}'
    replaced = False
    for i, arg in enumerate(base):
        if arg.startswith('cpus='):
            base[i] = cpus_arg
            replaced = True
            break
    if not replaced:
        base.append(cpus_arg)
    cmdline = ' '.join(base)
    if extra_cmdline:
        cmdline += ' ' + extra_cmdline
    return cmdline.encode('latin1')[:BOOT_LINE_LENGTH - 1]


def iso_now(epoch=None):
    return time.strftime('%Y-%m-%dT%H:%M:%S%z', time.localtime(epoch))


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, 'rb') as source:
        for chunk in iter(lambda: source.read(1 << 20), b''):
            digest.update(chunk)
    return digest.hexdigest()


def file_record(path):
    path = os.path.abspath(path)
    return {
        'path': path.replace(os.sep, '/'),
        'size': os.path.getsize(path),
        'sha256': sha256_file(path),
    }


def qemu_identity():
    """Return (absolute binary path, first --version line); no guest is started."""
    qemu_bin = shutil.which('qemu-system-aarch64')
    if not qemu_bin:
        return None, None
    qemu_bin = os.path.abspath(qemu_bin)
    try:
        version = subprocess.check_output(
            [qemu_bin, '--version'], text=True, stderr=subprocess.DEVNULL
        ).splitlines()[0].strip()
    except Exception:
        version = None
    return qemu_bin, version


def build_manifest(*, argv, payload_path, payload, extra_cmdline, boot_args, trace,
                   disk_snapshot, disk, kernel, sample_kernel, qemu_binary,
                   qemu_version, host_started=None):
    """Build the pre-run manifest without starting QEMU."""
    started = time.time() if host_started is None else host_started
    records = {}

    def record(path):
        if not path:
            return None
        key = os.path.normcase(os.path.abspath(path))
        if key not in records:
            records[key] = file_record(path)
        return dict(records[key])

    manifest = {
        'schema_version': 1,
        'state': 'prepared',
        'host_started': iso_now(started),
        'host_started_unix': round(started, 6),
        'qemu_binary': qemu_binary,
        'qemu_version': qemu_version,
        'argv': list(argv),
        'payload_path': os.path.abspath(payload_path).replace(os.sep, '/'),
        'payload_size': len(payload),
        'payload_sha256': hashlib.sha256(payload).hexdigest(),
        'extra_cmdline': extra_cmdline,
        'boot_args': boot_args,
        'trace': trace,
        'disk_snapshot': bool(disk_snapshot),
    }
    for key, path in (('kernel', kernel), ('sample_kernel', sample_kernel)):
        value = record(path)
        if value is not None:
            manifest[key] = value
    if disk:
        disk = os.path.abspath(disk)
        disk_stat = os.stat(disk)
        # Metadata does not establish disk content identity; avoid scanning multi-GB images at every boot.
        manifest['disk'] = {
            'path': disk.replace(os.sep, '/'),
            'size': disk_stat.st_size,
            'mtime_ns': disk_stat.st_mtime_ns,
        }
    return manifest


def finalize_manifest(manifest, *, stop_reason, qemu_returncode, runner_exit_code,
                      result_status=None, host_finished=None, error=None):
    """Add host outcome fields before writing the final manifest."""
    finished = time.time() if host_finished is None else host_finished
    started = manifest.get('host_started_unix', finished)
    state = {
        'interrupted': 'interrupted',
        'runner_error': 'failed',
        'launch_failed': 'failed',
    }.get(stop_reason, 'finished')
    manifest.update({
        'state': state,
        'host_finished': iso_now(finished),
        'host_finished_unix': round(finished, 6),
        'duration_secs': round(max(0.0, finished - started), 3),
        'stop_reason': stop_reason,
        'qemu_returncode': qemu_returncode,
        'runner_exit_code': runner_exit_code,
        'timed_out': stop_reason == 'deadline',
    })
    if result_status is not None:
        manifest['result_status'] = result_status
    if error:
        manifest['error'] = error
    return manifest


def write_manifest(path, manifest):
    with open(path, 'w', encoding='utf-8') as manifest_file:
        json.dump(manifest, manifest_file, indent=2)
        manifest_file.write('\n')


def build_image(payload, extra_cmdline='', smp=1):
    """Return (phys_base, ram_image, boot_args_pa, entry_pa, boot_args_text)."""
    magic, ver, nsegs = struct.unpack_from('<8sII', payload, 0)
    assert magic == b'SWEETXNU' and ver == 1, 'not a SWEETXNU v1 payload'
    virt_base, entry_va, adt_off, adt_size, kernel_end, phys_base, mem_size = \
        struct.unpack_from('<7Q', payload, 0x10)
    raw_cmdline = compose_cmdline(payload, extra_cmdline, smp)
    cmdline = raw_cmdline + b'\0'
    cmdline = cmdline.ljust(BOOT_LINE_LENGTH, b'\0')
    delta = phys_base - virt_base
    adt_pa = kernel_end + delta
    ba_pa = (adt_pa + adt_size + PAGE - 1) & ~(PAGE - 1)
    top = ba_pa + PAGE
    img = bytearray(top - phys_base)
    for i in range(nsegs):
        vmaddr, vmsize, foff, fsize = struct.unpack_from('<4Q', payload, 0x2a8 + 32 * i)
        o = vmaddr + delta - phys_base
        img[o:o + fsize] = payload[foff:foff + fsize]
    img[adt_pa - phys_base:adt_pa - phys_base + adt_size] = payload[adt_off:adt_off + adt_size]
    ba = struct.pack('<HH4x4Q6QI4xQI', 2, 2, virt_base, phys_base, mem_size, top,
                     FB_BASE, 1, FB_STRIDE, FB_W, FB_H, 32, 0, adt_pa - delta, adt_size)
    ba += cmdline + b'\0' * 4 + struct.pack('<QQ', 0, mem_size)
    assert len(ba) == 736
    img[ba_pa - phys_base:ba_pa - phys_base + len(ba)] = ba
    return phys_base, bytes(img), ba_pa, entry_va + delta, raw_cmdline.decode('latin1')


def stub(ba_pa, entry_pa):
    # ldr x0, =ba ; ldr x1, =entry ; br x1 ; nop ; .quad ba ; .quad entry
    return struct.pack('<4I2Q', 0x58000080, 0x580000a1, 0xd61f0020, 0xd503201f, ba_pa, entry_pa)


def write_png(path, raw):
    rows = []
    for y in range(FB_H):
        line = raw[y * FB_STRIDE:(y + 1) * FB_STRIDE]
        rgb = bytearray(FB_W * 3)	# a8r8g8b8 little endian = B G R A in memory
        rgb[0::3], rgb[1::3], rgb[2::3] = line[2::4], line[1::4], line[0::4]
        rows.append(b'\0' + bytes(rgb))
    chunk = lambda t, d: struct.pack('>I', len(d)) + t + d + struct.pack('>I', zlib.crc32(t + d))
    png = b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', FB_W, FB_H, 8, 2, 0, 0, 0))
    png += chunk(b'IDAT', zlib.compress(b''.join(rows), 6)) + chunk(b'IEND', b'')
    open(path, 'wb').write(png)


def payload_data(payload, va, size):
    """Read initialized segment bytes by VA (the payload has no slide)."""
    nsegs = struct.unpack_from('<I', payload, 12)[0]
    for i in range(nsegs):
        vmaddr, _, foff, fsize = struct.unpack_from('<4Q', payload, 0x2a8 + 32 * i)
        if vmaddr <= va and va + size <= vmaddr + fsize:
            offset = foff + va - vmaddr
            return payload[offset:offset + size]
    raise ValueError(f'VA {va:#x}+{size:#x} not in initialized payload segments')


def decode_screen(raw, font):
    """Exact glyph matching for pe_serial.c's 2x, white-on-black fbcon."""
    glyphs = {font[c * 16:(c + 1) * 16]: chr(c) for c in range(32, 127)}
    rows, unknown = [], 0
    for row in range(FB_H // 32):
        chars = []
        for col in range(FB_W // 16):
            glyph = bytearray(16)
            for y in range(16):
                offset = (row * 32 + y * 2) * FB_STRIDE + col * 16 * 4
                for x in range(8):
                    if raw[offset + x * 8:offset + x * 8 + 4] == b'\xff' * 4:
                        glyph[y] |= 1 << x
            key = bytes(glyph)
            char = glyphs.get(key, '?')
            unknown += key not in glyphs
            chars.append(char)
        rows.append(''.join(chars).rstrip())
    return '\n'.join(rows).rstrip() + '\n', unknown


def screen_result(screen, unknown):
    if 'panic(cpu ' in screen or 'SWEET EARLY PANIC:' in screen:
        status = 'panic'
    elif unknown:
        status = 'incomplete_decode'
    elif screen.strip():
        status = 'no_panic_observed'
    else:
        status = 'blank_screen'
    return {'status': status, 'unknown_glyphs': unknown, 'snapshot_only': True}


def qmp(sock_path, *cmds, pmemsave=None):
    """Run QEMU human-monitor commands over QMP (synchronous, unlike the echoing HMP socket)."""
    s = socket.socket(socket.AF_INET if isinstance(sock_path, tuple) else socket.AF_UNIX)
    s.settimeout(30)
    s.connect(sock_path)
    f = s.makefile('rw')
    f.readline()

    def call(execute, **args):
        f.write(json.dumps({'execute': execute, 'arguments': args}) + '\n')
        f.flush()
        while True:
            line = f.readline()
            if not line:
                raise ConnectionError('QEMU closed the QMP connection')
            r = json.loads(line)
            if 'return' in r or 'error' in r:
                return r

    call('qmp_capabilities')
    out = []
    for c in cmds:
        r = call('human-monitor-command', **{'command-line': c})
        if 'error' in r:
            print(f'qmp {c!r}: {r["error"]}', file=sys.stderr)
        out.append(r.get('return', ''))
    if pmemsave:	# native QMP: HMP's argument parser chokes on '-' in paths
        r = call('pmemsave', val=pmemsave[0], size=pmemsave[1], filename=pmemsave[2])
        if 'error' in r:
            print(f'qmp pmemsave: {r["error"]}', file=sys.stderr)
    s.close()
    return out


def qmp_wake_tap(sock_path, x=16384, y=16384, press_ms=100):
    """Tap the absolute virtio tablet; each QMP request ends with its own SYN."""
    if any(type(value) is not int or not 0 <= value <= 32767 for value in (x, y)):
        raise ValueError('absolute tablet coordinates must be integers in 0..32767')
    if type(press_ms) is not int or not 1 <= press_ms <= 5000:
        raise ValueError('press_ms must be an integer in 1..5000')
    s = socket.socket(socket.AF_INET if isinstance(sock_path, tuple) else socket.AF_UNIX)
    s.settimeout(30)
    s.connect(sock_path)
    f = s.makefile('rw')
    f.readline()  # QMP greeting

    def execute(command, arguments, request_id):
        f.write(json.dumps({'execute': command, 'arguments': arguments, 'id': request_id}) + '\n')
        f.flush()
        while True:
            line = f.readline()
            if not line:
                raise ConnectionError('QEMU closed the QMP connection')
            response = json.loads(line)
            if response.get('id') == request_id:
                if 'error' in response:
                    raise RuntimeError(f"QMP {command} failed: {response['error']}")
                if 'return' not in response:
                    raise RuntimeError(f'QMP {command} returned no result for id {request_id}')
                return response['return']

    try:
        execute('qmp_capabilities', {}, 0)
        down = {'events': [
            {'type': 'abs', 'data': {'axis': 'x', 'value': x}},
            {'type': 'abs', 'data': {'axis': 'y', 'value': y}},
            {'type': 'btn', 'data': {'down': True, 'button': 'left'}},
        ]}
        up = {'events': [{'type': 'btn', 'data': {'down': False, 'button': 'left'}}]}
        try:
            execute('input-send-event', down, 1)
            time.sleep(press_ms / 1000)
        except BaseException:
            try:
                execute('input-send-event', up, 2)
            except Exception:
                pass
            raise
        execute('input-send-event', up, 2)
    finally:
        f.close()
        s.close()


def stream_serial_file(serial_path, file_pos, out_stream=sys.stdout):
    """Read newly appended content from serial.txt and write directly to stream."""
    if not os.path.exists(serial_path):
        return file_pos
    try:
        with open(serial_path, 'r', errors='replace') as f:
            f.seek(file_pos)
            data = f.read()
            if data:
                out_stream.write(data)
                out_stream.flush()
                return f.tell()
    except Exception:
        pass
    return file_pos


def main():
    ap = argparse.ArgumentParser(
        description="Boot a SWEETXNU payload in QEMU's virt board.",
        epilog="Examples:\n"
               "  qemu-sweet.py payload.bin out/\n"
               "  qemu-sweet.py payload.bin out/ --live-serial\n"
               "  qemu-sweet.py payload.bin out/ --kernel kernel.macho --fail-on-panic\n"
               "  qemu-sweet.py --check-env\n",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument('payload', nargs='?', help='SWEETXNU payload binary (from mkpayload.py)')
    ap.add_argument('outdir', nargs='?', help='Output directory for fb.png, regs.txt, and logs')
    ap.add_argument('--secs', type=float, default=20, help='Duration to run QEMU in seconds (default: 20)')
    ap.add_argument('--wait', action='store_true', help='run until QEMU exits (for --display) instead of --secs')
    ap.add_argument('--gdb', action='store_true', help='start halted, gdb stub on :1234, no timeout')
    ap.add_argument('--hmp', action='append', default=[], help='extra monitor command run after stop (repeatable), e.g. "x /8gx 0xfffffe..."')
    ap.add_argument('--cpu', default='cortex-a76', help='QEMU CPU model (default: cortex-a76)')
    ap.add_argument('--smp', type=int, default=1, help='QEMU/XNU CPU count (1-8; enables TCG multi-threading above 1)')
    ap.add_argument('--accel', default='tcg', help='QEMU accelerator (default: tcg; hvf on Apple Silicon with --cpu host)')
    ap.add_argument('--kernel', help='matching unstripped kernel, for exact framebuffer text decoding (uses llvm-nm)')
    ap.add_argument('--fail-on-panic', action='store_true', help='exit 2 for a visible panic, 3 for incomplete/blank decoding; requires --kernel')
    ap.add_argument('--live-serial', action='store_true', help='stream serial console output to stdout in real time')
    ap.add_argument('--disk', metavar='IMAGE', help='raw disk image on QEMU virtio-blk (boot with rd=vblk0)')
    ap.add_argument('--disk-snapshot', action='store_true', help='discard all guest writes to --disk when QEMU exits')
    ap.add_argument('--input', action='store_true', help='attach QEMU virtio tablet and keyboard (boot with virtio_input=1)')
    ap.add_argument('--wake-every', type=float, default=0,
                    help='send a blank-center tablet tap every N host seconds to wake an idle guest display')
    ap.add_argument('--wake-start', type=float, default=300,
                    help='seconds after QEMU starts before the first --wake-every tap (default: 300)')
    ap.add_argument('--wake-press-ms', type=int, default=100,
                    help='QMP tablet press duration in milliseconds (1..5000; default: 100)')
    ap.add_argument('--sample-every', type=float, default=0,
                    help='capture framebuffer, registers, and msgbuf every N host seconds (Windows only; requires --sample-kernel)')
    ap.add_argument('--sample-kernel', help='matching unstripped kernel used by periodic msgbuf capture (does not require llvm-nm)')
    ap.add_argument('--display', metavar='BACKEND', default='gtk', help='QEMU window backend: gtk, sdl, cocoa (default: gtk)')
    ap.add_argument('--headless', action='store_true', help='run without a graphical window (implies -nographic) for unattended tests')
    ap.add_argument('--extra-cmdline', default='', help='append this to the payload boot-args')
    ap.add_argument('--tb-mb', type=int, default=512, help='QEMU TCG translation cache in MB (default: 512)')
    ap.add_argument('--trace', choices=('exceptions', 'errors'), default='exceptions',
                    help='QEMU log detail: exceptions preserves historical tracing; errors omits per-exception logging')
    ap.add_argument('--check-env', action='store_true', help='check QEMU installation and dependencies without running a payload')
    a = ap.parse_args()

    if a.check_env:
        ok = check_qemu_dependency(a.cpu)
        if shutil.which('llvm-nm'):
            print('[*] llvm-nm found in PATH', file=sys.stderr)
        else:
            print('[!] Optional: llvm-nm not found (needed only when using --kernel for text decoding)', file=sys.stderr)
        return 0 if ok else 1

    if not a.payload or not a.outdir:
        ap.error('payload and outdir are required unless --check-env is specified')

    if a.fail_on_panic and not a.kernel:
        ap.error('--fail-on-panic requires --kernel')

    if not 1 <= a.smp <= 8:
        ap.error('--smp must be between 1 and 8')

    if a.wake_every < 0 or a.wake_start < 0:
        ap.error('--wake-every and --wake-start must be non-negative')
    if not 1 <= a.wake_press_ms <= 5000:
        ap.error('--wake-press-ms must be in 1..5000')
    if a.wake_every and not a.input:
        ap.error('--wake-every requires --input')
    if a.sample_every < 0:
        ap.error('--sample-every must be non-negative')
    sample_kernel = a.sample_kernel or a.kernel
    if a.sample_every and not sample_kernel:
        ap.error('--sample-every requires --sample-kernel or --kernel')
    if a.sample_every and not os.path.isfile(sample_kernel):
        ap.error(f'periodic capture kernel does not exist: {sample_kernel}')
    if a.sample_every and os.name != 'nt':
        ap.error('--sample-every currently requires the Windows QMP process lookup used by research/snapshot-qemu.py')

    if not check_qemu_dependency(a.cpu):
        return 1
    qemu_binary, qemu_version = qemu_identity()

    if a.kernel and not check_kernel_tools(a.kernel):
        return 1

    payload = open(a.payload, 'rb').read()
    font = None
    if a.kernel:
        symbols = subprocess.check_output(['llvm-nm', '--defined-only', a.kernel], text=True)
        fonts = [int(line.split()[0], 16) for line in symbols.splitlines()
                 if line.split()[-1:] == ['_iso_font']]
        if len(fonts) != 1:
            ap.error('kernel must contain exactly one _iso_font symbol')
        font = payload_data(payload, fonts[0], 256 * 16)
    os.makedirs(a.outdir, exist_ok=True)
    out = os.path.abspath(a.outdir).replace(os.sep, '/')

    phys_base, img, ba_pa, entry_pa, boot_args = build_image(payload, a.extra_cmdline, a.smp)
    open(f'{out}/ram.bin', 'wb').write(img)
    open(f'{out}/stub.bin', 'wb').write(stub(ba_pa, entry_pa))
    print(f'phys_base={phys_base:#x} boot_args={ba_pa:#x} entry={entry_pa:#x}', file=sys.stderr)

    if a.disk:
        a.disk = os.path.abspath(a.disk).replace(os.sep, '/')
        if not os.path.exists(a.disk):
            ap.error(f'disk image not found: {a.disk}')
    bootline = payload[0x48:0x48 + BOOT_LINE_LENGTH].split(b'\0', 1)[0].decode('latin1')
    bootline += ' ' + a.extra_cmdline
    if a.disk and 'rd=vblk0' not in bootline.split():
        print('[!] --disk: the payload boot-args do not say rd=vblk0; '
              'build it with that (and rootrw=1) or pass --extra-cmdline', file=sys.stderr)
    if a.input and 'virtio_input=1' not in bootline.split():
        print('[!] --input: the payload boot-args do not say virtio_input=1; '
              'build it with that or pass --extra-cmdline', file=sys.stderr)
    if not a.headless and a.display and 'ramfb=1' not in bootline.split():
        print('[!] --display: the payload boot-args do not say ramfb=1; '
              'build it with that or pass --extra-cmdline', file=sys.stderr)

    if os.name == 'nt':
        # Use loopback TCP so the Windows monitor does not require Unix sockets.
        with socket.socket() as probe:
            probe.bind(('127.0.0.1', 0))
            mon = probe.getsockname()
        monitor_arg = f'tcp:{mon[0]}:{mon[1]},server=on,wait=off'
    else:
        mon = f'{out}/mon.sock'
        if os.path.exists(mon):
            os.unlink(mon)
        monitor_arg = f'unix:{mon},server=on,wait=off'
    # virt RAM starts at 0x40000000: cover the payload's RAM (mkadt.py --highmem needs 8G).
    mem_size = struct.unpack_from('<Q', payload, 0x40)[0]
    ram_gib = max(4, -(-(phys_base + mem_size - 0x40000000) // (1 << 30)))
    cmd = ['qemu-system-aarch64', '-M', 'virt,gic-version=3', '-cpu', a.cpu, '-smp', str(a.smp), '-m', f'{ram_gib}G',
           '-serial', f'file:{out}/serial.txt', '-qmp', monitor_arg,
           '-d', 'int,guest_errors,unimp' if a.trace == 'exceptions' else 'guest_errors,unimp',
           '-D', f'{out}/qemu.log', '-no-reboot',
           '-device', f'loader,file={out}/ram.bin,addr={phys_base:#x},force-raw=on',
           '-device', f'loader,file={out}/stub.bin,addr={STUB_PA:#x},force-raw=on',
           '-device', f'loader,addr={STUB_PA:#x},cpu-num=0']
    if a.accel == 'tcg':
        tcg_threads = ',thread=multi' if a.smp > 1 else ''
        cmd += ['-accel', f'tcg,tb-size={a.tb_mb}{tcg_threads}']
    else:
        cmd += ['-accel', a.accel]
    if a.headless:
        cmd += ['-nographic']
    else:
        cmd += ['-display', a.display, '-device', 'ramfb,id=sweetfb']
    if a.disk or a.input:
        cmd += ['-global', 'virtio-mmio.force-legacy=false']
    if a.disk:
        snapshot = ',snapshot=on' if a.disk_snapshot else ''
        cmd += ['-drive', f'file={a.disk},format=raw,if=none,id=vmdisk,cache=writeback{snapshot}',
                '-device', 'virtio-blk-device,drive=vmdisk']
    if a.input:
        cmd += ['-device', 'virtio-tablet-device',
                '-device', 'virtio-keyboard-device']
    if a.gdb:
        cmd += ['-S', '-gdb', 'tcp::1234']

    manifest = build_manifest(
        argv=cmd,
        payload_path=a.payload,
        payload=payload,
        extra_cmdline=a.extra_cmdline,
        boot_args=boot_args,
        trace=a.trace,
        disk_snapshot=a.disk_snapshot,
        disk=a.disk,
        kernel=a.kernel,
        sample_kernel=sample_kernel,
        qemu_binary=qemu_binary,
        qemu_version=qemu_version,
    )
    manifest_path = f'{out}/run-manifest.json'
    write_manifest(manifest_path, manifest)

    p = None
    serial_file = f'{out}/serial.txt'
    serial_pos = 0
    wake_log = None
    stop_reason = 'launch_failed'
    qemu_returncode = None
    runner_exit_code = None
    result_status = None
    manifest_error = None

    try:
        p = subprocess.Popen(cmd, stdin=subprocess.DEVNULL)
        stop_reason = 'running'
        if a.gdb:
            print('gdb stub on :1234; QMP socket:', mon, file=sys.stderr)
            p.wait()
            stop_reason = 'gdb_exited'
            qemu_returncode = p.returncode
            runner_exit_code = 0
            return 0

        t0 = time.time()
        deadline = float('inf') if a.wait else a.secs
        next_wake = t0 + a.wake_start if a.wake_every else float('inf')
        next_sample = t0 + a.sample_every if a.sample_every else float('inf')
        sample_index = 1
        wake_log = open(f'{out}/wake-events.log', 'a', encoding='utf-8') if a.wake_every else None
        while p.poll() is None and time.time() - t0 < deadline:
            now = time.time()
            if wake_log is not None and now >= next_wake:
                qmp_wake_tap(mon, press_ms=a.wake_press_ms)
                stamp = time.strftime('%Y-%m-%dT%H:%M:%S%z', time.localtime(now))
                wake_log.write(f'{stamp} QMP absolute tablet tap x=16384 y=16384\n')
                wake_log.flush()
                while next_wake <= now:
                    next_wake += a.wake_every
            if now >= next_sample:
                sample_dir = f'{out}/snap{sample_index:03d}'
                snapshot_script = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                               'research', 'snapshot-qemu.py')
                with open(f'{out}/snapshot-capture.log', 'a', encoding='utf-8') as capture_log:
                    capture_log.write(f'[{time.strftime("%Y-%m-%dT%H:%M:%S%z", time.localtime(now))}] '
                                      f'capture {sample_dir}\n')
                    capture_log.flush()
                    capture = subprocess.run([sys.executable, snapshot_script, sample_dir, sample_kernel],
                                             cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                             stdout=capture_log, stderr=subprocess.STDOUT)
                    capture_log.write(f'snapshot exit {capture.returncode}\n')
                sample_index += 1
                while next_sample <= time.time():
                    next_sample += a.sample_every
            if a.live_serial:
                serial_pos = stream_serial_file(serial_file, serial_pos)
            time.sleep(0.2)

        if a.live_serial:
            stream_serial_file(serial_file, serial_pos)

        stop_reason = 'qemu_exited' if p.poll() is not None else 'deadline'
        result = {'status': 'qemu_exited', 'qemu_returncode': p.returncode}
        if p.poll() is None:
            _, regs, *extra = qmp(mon, 'stop', 'info registers', *a.hmp, pmemsave=(FB_BASE, FB_STRIDE * FB_H, f'{out}/fb.raw'))
            open(f'{out}/regs.txt', 'w').write(regs + ''.join(f'\n(qemu) {c}\n{r}' for c, r in zip(a.hmp, extra)))
            p.kill()
            p.wait()
            raw = open(f'{out}/fb.raw', 'rb').read()
            write_png(f'{out}/fb.png', raw)
            result = {'status': 'not_decoded'}
            if font is not None:
                screen, unknown = decode_screen(raw, font)
                open(f'{out}/fb.txt', 'w').write(screen)
                result = screen_result(screen, unknown)
            os.unlink(f'{out}/fb.raw')
        else:
            print(f'qemu exited early: {p.returncode}', file=sys.stderr)

        qemu_returncode = p.returncode
        result_status = result['status']
        open(f'{out}/result.json', 'w').write(json.dumps(result, indent=2) + '\n')
        print(json.dumps(result), file=sys.stderr)
        print(f'{out}/fb.png  {out}/regs.txt  {out}/qemu.log', file=sys.stderr)
        if a.fail_on_panic and result['status'] == 'panic':
            runner_exit_code = 2
        elif a.fail_on_panic and result['status'] in ('incomplete_decode', 'blank_screen'):
            runner_exit_code = 3
        elif result['status'] == 'qemu_exited':
            runner_exit_code = 1
        else:
            runner_exit_code = 0
        return runner_exit_code

    except KeyboardInterrupt:
        print('\n[!] Interrupted by user, stopping QEMU...', file=sys.stderr)
        stop_reason = 'interrupted'
        runner_exit_code = 130
        if p and p.poll() is None:
            p.kill()
            p.wait()
        return 130
    except Exception as exc:
        stop_reason = 'runner_error'
        runner_exit_code = 1
        manifest_error = f'{type(exc).__name__}: {exc}'
        raise
    finally:
        if wake_log is not None:
            wake_log.close()
        if p and p.poll() is None:
            p.kill()
            p.wait()
        if p is not None and qemu_returncode is None:
            qemu_returncode = p.returncode
        try:
            finalize_manifest(
                manifest,
                stop_reason=stop_reason,
                qemu_returncode=qemu_returncode,
                runner_exit_code=runner_exit_code,
                result_status=result_status,
                error=manifest_error,
            )
            write_manifest(manifest_path, manifest)
        except Exception as exc:
            print(f'[!] Failed to finalize run manifest: {exc}', file=sys.stderr)
        ram_file = f'{out}/ram.bin'
        if os.path.exists(ram_file):
            try:
                os.unlink(ram_file)
            except Exception:
                pass


if __name__ == '__main__':
    sys.exit(main())
