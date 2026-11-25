#!/usr/bin/env python3
"""Verify bounded, sanitized, nonblocking USB SSH log mirroring on loopback."""
from pathlib import Path
import socket, subprocess, tempfile, threading
root = Path(__file__).resolve().parent
with tempfile.TemporaryDirectory() as directory, socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as receiver:
    work = Path(directory)
    receiver.bind(('127.0.0.1', 0)); receiver.settimeout(5)
    source = work / 'check.c'
    source.write_text('#include "whyred-ssh-udp.h"\nint main(void) {\n'
        ' char big[2048]; memset(big, 65, sizeof(big)-1); big[sizeof(big)-1]=0;\n'
        ' errno=EDOM; whyred_ssh_usb_log("hello\\ncontrol\\001"); if(errno!=EDOM)return 1;\n'
        ' for(int i=1;i<513;i++){errno=ERANGE;whyred_ssh_usb_log(big);if(errno!=ERANGE)return 2;usleep(1000);}\n'
        ' return 0; }\n')
    binary = work / 'check'
    subprocess.run(['clang', '-Wall', '-Wextra', '-Werror', '-I', str(root),
        '-DWHYRED_SSH_LOG_SOURCE=0x7f000001u', '-DWHYRED_SSH_LOG_DESTINATION=0x7f000001u',
        '-DWHYRED_SSH_LOG_PORT=' + str(receiver.getsockname()[1]), str(source), '-o', str(binary)], check=True)
    rows = []; errors = []
    def receive():
        try:
            for _ in range(512): rows.append(receiver.recv(4096))
        except Exception as exc: errors.append(exc)
    thread = threading.Thread(target=receive); thread.start()
    subprocess.run([str(binary)], check=True, timeout=10); thread.join(timeout=10)
    assert not thread.is_alive() and not errors and len(rows)==512, (len(rows),errors)
    receiver.settimeout(.1)
    try: receiver.recv(4096); raise AssertionError('budget exceeded')
    except socket.timeout: pass
    assert b'hello control ' in rows[0]
    assert all(p.startswith(b'WHYRED SSH: pid=') and p.endswith(b'\n') and len(p)<=1023 for p in rows)
    assert all(all(c>=32 and c!=127 for c in p[:-1]) for p in rows)
    assert len(rows[1])==1023
print('USB log checks passed: delivery, budget512,1023-byte cap, sanitization, errno preservation')
