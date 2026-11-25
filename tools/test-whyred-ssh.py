#!/usr/bin/env python3
"""Exercise the built native Dropbear with isolated keys and a loopback listener."""
import argparse
import getpass
import hashlib
import json
import os
from pathlib import Path
import signal
import socket
import subprocess
import time


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('build', type=Path)
    ap.add_argument('--output', required=True, type=Path)
    args = ap.parse_args()
    binary = args.build.resolve() / 'native/bin'
    out = args.output.resolve()
    out.mkdir(mode=0o700, parents=True, exist_ok=False)
    keys = out / 'keys'
    keys.mkdir(mode=0o700)
    for name in ['client', 'wrong']:
        subprocess.run(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-C', 'whyred-test',
                        '-f', str(keys / name)], check=True)
    subprocess.run([str(binary / 'dropbearkey'), '-t', 'ed25519', '-f', str(keys / 'host')],
                   check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    public = subprocess.check_output([str(binary / 'dropbearkey'), '-y', '-f', str(keys / 'host')], text=True)
    public = next(line for line in public.splitlines() if line.startswith('ssh-ed25519 '))
    auth = keys / 'authorized_keys'
    auth.write_bytes((keys / 'client.pub').read_bytes())
    auth.chmod(0o600)
    with socket.socket() as s:
        s.bind(('127.0.0.1', 0))
        port = s.getsockname()[1]
    known = keys / 'known_hosts'
    known.write_text(f'[127.0.0.1]:{port} {public}\n')
    server_log = (out / 'server.log').open('wb')
    server = subprocess.Popen([str(binary / 'dropbear'), '-F', '-p', f'127.0.0.1:{port}',
                               '-D', str(keys), '-r', str(keys / 'host'), '-P', str(out / 'server.pid')],
                              stdin=subprocess.DEVNULL, stdout=server_log, stderr=server_log,
                              start_new_session=True)
    checks = []
    try:
        for _ in range(100):
            if server.poll() is not None:
                raise RuntimeError('Native test server failed: ' + (out / 'server.log').read_text())
            try:
                with socket.create_connection(('127.0.0.1', port), timeout=.1):
                    break
            except OSError:
                time.sleep(.05)
        else:
            raise RuntimeError('Native test server did not listen')
        def ssh(key, command, **kw):
            return subprocess.run(['ssh', '-F', '/dev/null', '-o', 'BatchMode=yes', '-o', 'IdentitiesOnly=yes',
                '-o', 'StrictHostKeyChecking=yes', '-o', 'UserKnownHostsFile=' + str(known),
                '-o', 'ConnectTimeout=5', '-i', str(keys / key), '-p', str(port),
                getpass.getuser() + '@127.0.0.1', command], capture_output=True, timeout=20, **kw)
        p = ssh('client', "printf WHYRED_SSH_OK; exit 7")
        assert p.returncode == 7 and p.stdout == b'WHYRED_SSH_OK', (p.returncode, p.stderr)
        checks.append('correct-key command and exit status')
        p = ssh('wrong', 'printf MUST_NOT_RUN')
        assert p.returncode == 255 and not p.stdout and b'Permission denied' in p.stderr
        checks.append('wrong key rejected')
        payload = bytes(range(256)) * 4096
        p = ssh('client', '/bin/cat', input=payload)
        assert p.returncode == 0 and p.stdout == payload
        checks.append('binary channel round trip, 1048576 bytes')
        if (binary / 'sh').exists():
            p = subprocess.run([str(binary / 'sh'), '-c',
                'x=whyred; [ "$x" = whyred ] && printf "%s" "$(printf shell)"; exit 9'], capture_output=True)
            assert p.returncode == 9 and p.stdout == b'shell'
            checks.append('dash expansion, builtin test and exit')
            for command in [['uname'], ['fs', str(out)], ['ps'], ['ls', str(keys)]]:
                p = subprocess.run([str(binary / 'whyredctl'), *command], capture_output=True)
                assert p.returncode == 0 and p.stdout
            checks.append('native diagnostics uname/fs/ps/ls')
    finally:
        os.killpg(server.pid, signal.SIGTERM)
        server.wait(timeout=5)
        server_log.close()
    report = {'passed': True, 'checks': checks, 'loopback_only': True,
              'target_hardware_tested': False, 'keys_in_artifact': False,
              'binary_roundtrip_sha256': hashlib.sha256(payload).hexdigest()}
    (out / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
