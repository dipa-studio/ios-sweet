#!/usr/bin/env python3
"""Capture one bounded RAMFB/GTK comparison from an existing Windows QEMU run."""
import argparse
import ctypes
import hashlib
import importlib.util
import json
import pathlib
import re
import socket
import struct
import subprocess
import time

from PIL import Image, ImageChops, ImageGrab, ImageStat

root = pathlib.Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location('sweet_qemu', root / 'tools/qemu-sweet.py')
sweet = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sweet)


def window_for_pid(pid):
    user32 = ctypes.windll.user32
    windows = []
    callback_type = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)

    @callback_type
    def visit(handle, unused):
        owner = ctypes.c_ulong()
        user32.GetWindowThreadProcessId(handle, ctypes.byref(owner))
        if owner.value == pid and user32.IsWindowVisible(handle):
            rect = (ctypes.c_long * 4)()
            if user32.GetClientRect(handle, ctypes.byref(rect)):
                point = (ctypes.c_long * 2)()
                if not user32.ClientToScreen(handle, ctypes.byref(point)):
                    return True
                box = (point[0], point[1], point[0] + rect[2], point[1] + rect[3])
                if box[2] - box[0] > 100 and box[3] - box[1] > 100:
                    windows.append((handle, box))
        return True

    user32.EnumWindows(visit, 0)
    if len(windows) != 1:
        raise RuntimeError(f'expected one visible QEMU window for PID {pid}, found {len(windows)}')
    return windows[0]


def display_crop(image):
    width, height = image.size
    draw_width = min(width, height * sweet.FB_W // sweet.FB_H)
    draw_height = draw_width * sweet.FB_H // sweet.FB_W
    left = (width - draw_width) // 2
    top = (height - draw_height) // 2
    return image.crop((left, top, left + draw_width, top + draw_height)), (left, top, draw_width, draw_height)


def image_difference(reference, candidate):
    candidate = candidate.convert('RGB').resize(reference.size, Image.Resampling.BILINEAR)
    return round(sum(ImageStat.Stat(ImageChops.difference(reference.convert('RGB'), candidate)).mean) / 3, 3)


def capture_gtk_window(pid, out):
    handle, box = window_for_pid(pid)
    user32 = ctypes.windll.user32
    user32.SetForegroundWindow(handle)
    time.sleep(.15)
    foreground = user32.GetForegroundWindow()
    owner = ctypes.c_ulong()
    user32.GetWindowThreadProcessId(foreground, ctypes.byref(owner))
    if owner.value != pid:
        raise RuntimeError('QEMU GTK window is not foreground; screenshot could contain another app')
    started = time.time()
    gtk = ImageGrab.grab(bbox=box, all_screens=True)
    gtk.save(out / 'gtk-client.png')
    crop, crop_box = display_crop(gtk)
    crop.save(out / 'gtk-display.png')
    return crop, {'window_handle': handle, 'client_rect': box,
                  'gtk_display_rect_in_client': crop_box,
                  'gtk_display_resolution': list(crop.size),
                  'gtk_started_unix': started, 'gtk_finished_unix': time.time()}


def qmp_request(stream, command, arguments=None, request_id=0):
    stream.write(json.dumps({'execute': command, 'arguments': arguments or {}, 'id': request_id}) + '\n')
    stream.flush()
    while line := stream.readline():
        reply = json.loads(line)
        if reply.get('id') == request_id:
            if 'error' in reply:
                raise RuntimeError(f'{command}: {reply["error"]}')
            if 'return' not in reply:
                raise RuntimeError(f'{command}: missing return')
            return reply['return']
    raise ConnectionError(f'QMP disconnected during {command}')


def msgbuf_address(kernel):
    binary = kernel.read_bytes()
    offset = 32
    for _ in range(struct.unpack_from('<I', binary, 16)[0]):
        command, size = struct.unpack_from('<II', binary, offset)
        if command == 2:
            symoff, nsyms, stroff, strsize = struct.unpack_from('<4I', binary, offset + 8)
            names = binary[stroff:stroff + strsize]
            for index in range(nsyms):
                name_offset, _, _, _, value = struct.unpack_from('<IBBHQ', binary, symoff + index * 16)
                if names[name_offset:names.find(b'\0', name_offset)] == b'_msgbufp':
                    return value
        offset += size
    raise ValueError('_msgbufp missing from matching kernel')


def _capture(run, out, kernel):
    manifest = json.loads((run / 'run-manifest.json').read_text(encoding='utf-8'))
    if (sweet.FB_BASE, sweet.FB_W, sweet.FB_H, sweet.FB_STRIDE) != (0x9c000000, 1080, 2400, 4320):
        raise ValueError('runner framebuffer geometry differs from RAMFB contract')
    if '-display' not in manifest['argv'] or manifest['argv'][manifest['argv'].index('-display') + 1] != 'gtk':
        raise ValueError('run manifest does not select GTK')
    devices = [manifest['argv'][i + 1] for i, arg in enumerate(manifest['argv'][:-1]) if arg == '-device']
    if devices.count('ramfb,id=sweetfb') != 1:
        raise ValueError('run manifest must contain exactly one named RAMFB device')
    qmp_arg = manifest['argv'][manifest['argv'].index('-qmp') + 1]
    port = int(re.fullmatch(r'tcp:127\.0\.0\.1:(\d+),server=on,wait=off', qmp_arg).group(1))
    ram = str((run / 'ram.bin').resolve()).replace('\\', '/').lower()
    script = "Get-CimInstance Win32_Process -Filter \"Name = 'qemu-system-aarch64.exe'\" | Select-Object ProcessId,CommandLine | ConvertTo-Json -Compress"
    processes = json.loads(subprocess.check_output(['powershell.exe', '-NoProfile', '-Command', script], text=True))
    if isinstance(processes, dict):
        processes = [processes]
    matches = [p for p in processes if ram in p['CommandLine'].replace('\\', '/').lower()]
    if len(matches) != 1:
        raise RuntimeError(f'expected one QEMU process for this run, found {len(matches)}')
    pid = matches[0]['ProcessId']
    out.mkdir(parents=True, exist_ok=False)
    timing = {'status': 'started', 'qemu_pid': pid,
              'ramfb': {'address': sweet.FB_BASE, 'width': sweet.FB_W, 'height': sweet.FB_H,
                        'stride': sweet.FB_STRIDE, 'format': 'XRGB8888'},
              'qmp_display_device': 'sweetfb', 'qmp_display_head': 0,
              'run_manifest': str((run / 'run-manifest.json').resolve())}
    crop, gtk_timing = capture_gtk_window(pid, out)
    timing.update(gtk_timing)
    stopped = False
    try:
        with socket.create_connection(('127.0.0.1', port), timeout=30) as connection:
            connection.settimeout(30)
            with connection.makefile('rw') as stream:
                stream.readline()
                qmp_request(stream, 'qmp_capabilities')
                qmp_request(stream, 'stop', request_id=1)
                stopped = True
                timing['guest_stopped_unix'] = time.time()
                raw_path = out / 'guest.raw'
                qmp_request(stream, 'pmemsave', {'val': sweet.FB_BASE, 'size': sweet.FB_STRIDE * sweet.FB_H,
                                                 'filename': str(raw_path)}, 2)
                timing['raw_saved_unix'] = time.time()
                qmp_request(stream, 'screendump',
                            {'filename': str(out / 'qmp-screen.ppm'), 'device': 'sweetfb', 'head': 0,
                             'format': 'ppm'}, 3)
                timing['screendump_saved_unix'] = time.time()
                registers = qmp_request(stream, 'human-monitor-command', {'command-line': 'info registers'}, 4)
                (out / 'regs.txt').write_text(registers, encoding='utf-8')
                pointer_text = qmp_request(stream, 'human-monitor-command',
                    {'command-line': f'x /1gx {msgbuf_address(kernel):#x}'}, 5)
                pointer = int(re.search(r':\s*(0x[0-9a-fA-F]+)', pointer_text).group(1), 16)
                if pointer:
                    header_text = qmp_request(stream, 'human-monitor-command',
                        {'command-line': f'x /3gx {pointer:#x}'}, 6)
                    values = []
                    for line in header_text.splitlines():
                        if ':' in line:
                            values.extend(int(x, 16) for x in re.findall(r'0x[0-9a-fA-F]+', line.split(':', 1)[1]))
                    if len(values) >= 3:
                        size, index, address = values[0] >> 32, values[1] & 0xffffffff, values[2]
                        if 0 < size <= 4 * 1024 * 1024:
                            log_path = out / 'msgbuf.bin'
                            qmp_request(stream, 'memsave', {'val': address, 'size': size, 'filename': str(log_path)}, 7)
                            data = log_path.read_bytes()
                            (out / 'msgbuf.txt').write_text((data[index:] + data[:index]).replace(b'\0', b'').decode(errors='replace'), encoding='utf-8')
                qmp_request(stream, 'cont', request_id=8)
                stopped = False
    finally:
        if stopped:
            try:
                with socket.create_connection(('127.0.0.1', port), timeout=5) as conn:
                    with conn.makefile('rw') as stream:
                        stream.readline()
                        qmp_request(stream, 'qmp_capabilities')
                        qmp_request(stream, 'cont', request_id=9)
            except Exception:
                pass
    raw = raw_path.read_bytes()
    if len(raw) != sweet.FB_STRIDE * sweet.FB_H:
        raise ValueError(f'raw framebuffer size {len(raw)} does not match geometry')
    sweet.write_png(str(out / 'guest.png'), raw)
    with Image.open(out / 'guest.png') as guest, Image.open(out / 'qmp-screen.ppm') as screen:
        timing['guest_resolution'] = list(guest.size)
        timing['qmp_resolution'] = list(screen.size)
        if guest.size != (sweet.FB_W, sweet.FB_H) or screen.size != guest.size:
            raise ValueError('RAMFB screendump resolution differs from guest framebuffer')
        timing['raw_vs_qmp_mean_abs_rgb'] = image_difference(guest, screen)
        timing['raw_vs_gtk_crop_mean_abs_rgb'] = image_difference(guest, crop)
    for name in ('guest.raw', 'guest.png', 'qmp-screen.ppm', 'gtk-client.png', 'gtk-display.png'):
        timing[name + '_sha256'] = hashlib.sha256((out / name).read_bytes()).hexdigest()
    if (out / 'msgbuf.txt').exists():
        text = (out / 'msgbuf.txt').read_text(encoding='utf-8')
        timing['display_events'] = [line for line in text.splitlines() if 'SWEET FB: display ' in line][-10:]
        timing['swap_events'] = [line for line in text.splitlines() if 'SWEET FB: swap ' in line][-20:]
        timing['hid_touch_events'] = [line for line in text.splitlines() if 'SWEET HID: touch ' in line][-30:]
        stamps = re.findall(r'^\[\s*([0-9.]+)\]', text, re.M)
        timing['guest_last_msgbuf_time'] = float(stamps[-1]) if stamps else None
        timing['display_state'] = ('off' if timing['display_events'] and
                                  'display off' in timing['display_events'][-1] else
                                  'on' if timing['display_events'] else 'unknown')
    timing['status'] = 'captured'
    (out / 'capture.json').write_text(json.dumps(timing, indent=2) + '\n', encoding='utf-8')
    print(out / 'capture.json')


def capture(run, out, kernel):
    if out.exists():
        raise FileExistsError(out)
    try:
        return _capture(run, out, kernel)
    except Exception as exc:
        out.mkdir(parents=True, exist_ok=True)
        status = {'status': 'failed', 'host_failed_unix': time.time(),
                  'error': f'{type(exc).__name__}: {exc}',
                  'run_manifest': str((run / 'run-manifest.json').resolve())}
        (out / 'capture.json').write_text(json.dumps(status, indent=2) + '\n', encoding='utf-8')
        raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('run_dir', type=pathlib.Path)
    parser.add_argument('output_dir', type=pathlib.Path)
    parser.add_argument('matching_kernel', type=pathlib.Path)
    args = parser.parse_args()
    capture(args.run_dir.resolve(), args.output_dir.resolve(), args.matching_kernel.resolve())
