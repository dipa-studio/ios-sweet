#!/usr/bin/env python3
"""Exercise the QMP tap protocol without launching QEMU."""
import importlib.util
import json
import pathlib
import socket
import threading
from unittest.mock import patch

module_path = pathlib.Path(__file__).with_name('qemu-sweet.py')
spec = importlib.util.spec_from_file_location('qemu_sweet', module_path)
qemu = importlib.util.module_from_spec(spec)
spec.loader.exec_module(qemu)


def exchange(failure=None):
    requests = []
    ready = threading.Event()
    endpoint = []
    errors = []

    def server():
        try:
            with socket.socket() as listener:
                listener.bind(('127.0.0.1', 0))
                listener.listen(1)
                endpoint.append(listener.getsockname())
                ready.set()
                listener.settimeout(5)
                conn, _ = listener.accept()
                with conn, conn.makefile('rw') as stream:
                    stream.write(json.dumps({'QMP': {'version': {}, 'capabilities': []}}) + '\n')
                    stream.flush()
                    while line := stream.readline():
                        request = json.loads(line)
                        requests.append(request)
                        reply = {'id': request['id'], 'return': {}}
                        if request['id'] == failure:
                            reply = {'id': failure, 'error': {'class': 'GenericError', 'desc': 'injected'}}
                        stream.write(json.dumps(reply) + '\n')
                        stream.flush()
        except Exception as exc:
            errors.append(exc)

    worker = threading.Thread(target=server, daemon=True)
    worker.start()
    assert ready.wait(5)
    try:
        with patch.object(qemu.time, 'sleep') as sleep:
            try:
                qemu.qmp_wake_tap(endpoint[0], 4492, 7795, press_ms=175)
                outcome = 'success'
            except RuntimeError:
                outcome = 'failure'
        if failure is None:
            sleep.assert_called_once_with(.175)
    finally:
        worker.join(5)
    assert not worker.is_alive() and not errors, errors
    return outcome, requests


def main():
    outcome, requests = exchange()
    assert outcome == 'success'
    assert [item['id'] for item in requests] == [0, 1, 2]
    assert [item['execute'] for item in requests] == ['qmp_capabilities', 'input-send-event', 'input-send-event']
    down, up = [item['arguments']['events'] for item in requests[1:]]
    assert down == [
        {'type': 'abs', 'data': {'axis': 'x', 'value': 4492}},
        {'type': 'abs', 'data': {'axis': 'y', 'value': 7795}},
        {'type': 'btn', 'data': {'down': True, 'button': 'left'}},
    ]
    assert up == [{'type': 'btn', 'data': {'down': False, 'button': 'left'}}]
    for failed_id in (0, 1, 2):
        outcome, failed_requests = exchange(failed_id)
        assert outcome == 'failure'
        assert failed_requests[-1]['id'] == (0 if failed_id == 0 else 2)
    for coordinates in [(-1, 10), (32768, 10), (10, -1), (10, 32768), (1.5, 5)]:
        try:
            qemu.qmp_wake_tap(('127.0.0.1', 1), *coordinates)
        except ValueError:
            pass
        else:
            raise AssertionError(f'accepted invalid coordinates {coordinates}')
    for press_ms in (0, 5001, 1.5):
        try:
            qemu.qmp_wake_tap(('127.0.0.1', 1), press_ms=press_ms)
        except ValueError:
            pass
        else:
            raise AssertionError(f'accepted invalid press_ms {press_ms}')
    assert 'qmp_wake_tap(endpoint, x, y)' in pathlib.Path('research/vm/control-3000-monitor.py').read_text()
    assert 'qmp_wake_tap(mon, press_ms=a.wake_press_ms)' in module_path.read_text()
    print('QMP mock: separate sync requests, coordinates, replies, failures and call sites passed')


if __name__ == '__main__':
    main()
