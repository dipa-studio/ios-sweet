#!/usr/bin/env python3
"""Mock QMP capture ordering, console selection, resume and image metadata."""
import importlib.util
import json
import pathlib
import socket
import tempfile
import threading
from unittest.mock import patch

from PIL import Image

path = pathlib.Path(__file__).with_name('capture-display.py')
spec = importlib.util.spec_from_file_location('capture_display', path)
capture = importlib.util.module_from_spec(spec)
spec.loader.exec_module(capture)


def exercise(fail_screendump=False):
    requests = []
    ready = threading.Event()
    port = []
    errors = []
    with tempfile.TemporaryDirectory(prefix='sweet-capture-test-') as temporary:
        root = pathlib.Path(temporary)
        run = root / 'run'
        run.mkdir()
        (run / 'ram.bin').write_bytes(b'test')
        out = root / 'capture'
        kernel = root / 'kernel'
        kernel.write_bytes(b'fake')
        raw = bytes((0x33, 0x66, 0x99, 0xff)) * (capture.sweet.FB_W * capture.sweet.FB_H)

        def server():
            try:
                with socket.socket() as listener:
                    listener.bind(('127.0.0.1', 0))
                    listener.listen(2)
                    listener.settimeout(5)
                    port.append(listener.getsockname()[1])
                    ready.set()
                    for _ in range(2 if fail_screendump else 1):
                        connection, _ = listener.accept()
                        with connection, connection.makefile('rw') as stream:
                            stream.write(json.dumps({'QMP': {}}) + '\n')
                            stream.flush()
                            while line := stream.readline():
                                request = json.loads(line)
                                requests.append(request)
                                command = request['execute']
                                args = request.get('arguments', {})
                                response = {'id': request['id'], 'return': {}}
                                if command == 'pmemsave':
                                    pathlib.Path(args['filename']).write_bytes(raw)
                                elif command == 'screendump':
                                    if fail_screendump:
                                        response = {'id': request['id'], 'error': {'desc': 'injected'}}
                                    else:
                                        Image.new('RGB', (1080, 2400), (0x99, 0x66, 0x33)).save(args['filename'])
                                elif command == 'human-monitor-command':
                                    response['return'] = ('0x0: 0x0' if args['command-line'].startswith('x /1gx')
                                                          else 'PC=0x0')
                                stream.write(json.dumps(response) + '\n')
                                stream.flush()
            except Exception as exc:
                errors.append(exc)

        thread = threading.Thread(target=server, daemon=True)
        thread.start()
        assert ready.wait(5)
        manifest = {'argv': ['qemu-system-aarch64', '-display', 'gtk', '-device', 'ramfb,id=sweetfb',
                             '-qmp', f'tcp:127.0.0.1:{port[0]},server=on,wait=off']}
        (run / 'run-manifest.json').write_text(json.dumps(manifest))

        def fake_gtk(pid, destination):
            image = Image.new('RGB', (270, 600), (0x99, 0x66, 0x33))
            image.save(destination / 'gtk-client.png')
            image.save(destination / 'gtk-display.png')
            return image, {'gtk_started_unix': 1, 'gtk_finished_unix': 2,
                           'gtk_display_resolution': [270, 600]}

        command = f'qemu-system-aarch64 -device loader,file={(run / "ram.bin").resolve().as_posix()}'
        process_result = json.dumps({'ProcessId': 1234, 'CommandLine': command}).encode()
        with patch.object(capture.subprocess, 'check_output', return_value=process_result.decode()), \
             patch.object(capture, 'capture_gtk_window', side_effect=fake_gtk), \
             patch.object(capture, 'msgbuf_address', return_value=0x1234):
            if fail_screendump:
                try:
                    capture.capture(run, out, kernel)
                except RuntimeError as exc:
                    assert 'screendump' in str(exc)
                else:
                    raise AssertionError('screendump failure was reported as success')
            else:
                capture.capture(run, out, kernel)
        thread.join(5)
        assert not thread.is_alive() and not errors, errors
        record = json.loads((out / 'capture.json').read_text())
        assert record['status'] == ('failed' if fail_screendump else 'captured')
        commands = [item['execute'] for item in requests]
        assert commands[:4] == ['qmp_capabilities', 'stop', 'pmemsave', 'screendump']
        assert commands[-1] == 'cont'
        pmem = requests[2]['arguments']
        assert pmem['val'] == 0x9c000000 and pmem['size'] == 1080 * 2400 * 4
        screen = requests[3]['arguments']
        assert screen['device'] == 'sweetfb' and screen['head'] == 0
        if not fail_screendump:
            assert record['guest_resolution'] == [1080, 2400]
            assert record['qmp_resolution'] == [1080, 2400]
            assert record['raw_vs_qmp_mean_abs_rgb'] == 0
            assert record['raw_vs_gtk_crop_mean_abs_rgb'] == 0
            assert record['guest.raw_sha256'] and record['gtk-client.png_sha256']


if __name__ == '__main__':
    exercise()
    exercise(True)
    print('Capture mock: explicit RAMFB/head, geometry, comparisons, failure status and resume passed')
