#!/usr/bin/env python3
"""Find whyred's CDC-ECM interface on macOS, configure it and receive UDP logs.

Default: list matching interfaces without changes. After booting a USB-enabled
image: python3 tools/whyred-usbnet.py --connect --log whyred-usb.log
"""
import argparse
import ipaddress
import json
import os
from pathlib import Path
import re
import socket
import subprocess
import sys
import time

MAC = '02:00:5e:77:ee:01'
HOST = '192.168.7.1'
PHONE = '192.168.7.2'
PORT = 5140


def interfaces(text):
    records, current = [], None
    for line in text.splitlines():
        match = re.match(r'^([A-Za-z][A-Za-z0-9_.-]*):\s', line)
        if match:
            current = {'name': match[1], 'mac': None, 'ipv4': []}
            records.append(current)
        elif current is not None:
            words = line.split()
            if len(words) >= 2 and words[0] == 'ether':
                current['mac'] = words[1].lower()
            elif len(words) >= 2 and words[0] == 'inet':
                current['ipv4'].append(str(ipaddress.IPv4Address(words[1])))
    return records


def select(records):
    matches = [r for r in records if r['mac'] == MAC]
    if len(matches) > 1:
        raise ValueError('More than one interface has the whyred test MAC; select the device connection manually.')
    return matches[0] if matches else None


def self_test():
    sample = ('lo0: flags=1\n\tinet 127.0.0.1 netmask 0xff000000\n'
              'en0: flags=1\n\tether 02:00:5e:77:ee:02\n\tinet 10.0.0.4 netmask 0xffffff00\n'
              'en17: flags=1\n\tether 02:00:5E:77:EE:01\n\tinet 192.168.7.1 netmask 0xffffff00\n')
    parsed = interfaces(sample)
    assert select(parsed)['name'] == 'en17'
    assert select(parsed)['ipv4'] == [HOST]
    assert select(parsed[:2]) is None
    try:
        select(parsed + [parsed[-1]])
    except ValueError:
        pass
    else:
        raise AssertionError('Ambiguous interface was accepted')
    assert interfaces('unrelated text\n\tether '+MAC) == []
    print('PASS: macOS interface selection, exact MAC and ambiguity checks')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--connect', action='store_true', help='configure only the matching USB interface, then listen')
    parser.add_argument('--wait', type=float, default=30, help='seconds to wait for enumeration with --connect')
    parser.add_argument('--log', type=Path, help='append exact received bytes to this private local file')
    parser.add_argument('--self-test', action='store_true')
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return
    if sys.platform != 'darwin':
        raise ValueError('This helper supports macOS. The existing sweet-usbnet.sh supports Linux.')
    if args.wait < 0 or args.wait > 3600:
        raise ValueError('--wait must be between 0 and 3600 seconds')
    deadline = time.monotonic() + (args.wait if args.connect else 0)
    while True:
        output = subprocess.run(['/sbin/ifconfig', '-a'], check=True, capture_output=True, text=True).stdout
        records = interfaces(output)
        chosen = select(records)
        if chosen or time.monotonic() >= deadline:
            break
        time.sleep(1)
    if not args.connect:
        print(json.dumps([r for r in records if r['mac'] == MAC], indent=2))
        return
    if not chosen:
        raise ValueError('No whyred CDC-ECM interface appeared. Check the kernel USB handoff/enumeration log.')
    subnet = ipaddress.IPv4Network('192.168.7.0/24')
    for record in records:
        if record['name'] != chosen['name'] and any(ipaddress.IPv4Address(a) in subnet for a in record['ipv4']):
            raise ValueError('The USB subnet is already used by '+record['name']+'; no interface was changed.')
    command = ['/sbin/ifconfig', chosen['name'], 'inet', HOST, 'netmask', '255.255.255.0', 'up']
    if os.geteuid() != 0:
        command.insert(0, 'sudo')
    subprocess.run(command, check=True)
    print(f"{chosen['name']}: {HOST}/24 -> phone {PHONE}; receiving UDP/{PORT}", file=sys.stderr)
    stream = None
    if args.log:
        descriptor = os.open(args.log, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
        stream = os.fdopen(descriptor, 'ab', buffering=0)
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as connection:
            connection.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            connection.bind((HOST, PORT))
            while True:
                data, peer = connection.recvfrom(65536)
                if peer[0] != PHONE:
                    continue
                if stream:
                    stream.write(data)
                sys.stdout.buffer.write(data)
                sys.stdout.buffer.flush()
    finally:
        if stream:
            stream.close()


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        pass
    except (ValueError, OSError, subprocess.CalledProcessError) as error:
        print(str(error), file=sys.stderr)
        raise SystemExit(1)
