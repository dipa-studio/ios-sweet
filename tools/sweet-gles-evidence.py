#!/usr/bin/env python3
"""Read a captured GLES trial; never infer rendering from an unchanged old log.

Usage: sweet-gles-evidence.py RUN_DIRECTORY --trial 2430 --kernel-mark 0x2429
The directory contains before/after-tail.bin, after-marks.bin and journal.json.
This is an offline report; it neither accesses a device nor proves visual quality.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import struct


def digest(data):
    return hashlib.sha256(data).hexdigest()


def console(data):
    if len(data) < 4096:
        raise ValueError('truncated console header')
    magic, version, size, total, seq = struct.unpack_from('<8sIIQQ', data)
    if magic != b'SWEETLOG' or size == 0 or size > len(data) - 4096:
        raise ValueError('invalid console ring')
    ring = data[4096:4096 + size]
    raw = ring[:total] if total <= size else ring[total % size:] + ring[:total % size]
    return raw, dict(version=version, total_bytes=total, flush_sequence=seq,
                     wrapped=total > size)


def kernel_marks(data):
    if len(data) != 4096:
        raise ValueError('marks must be one 4096-byte block')
    magic, version, count = struct.unpack_from('<8sII', data)
    if magic != b'SWEETMRK' or count > 160 or 16 + count * 24 > len(data):
        raise ValueError('invalid marks block')
    return [a for code, _, a, _ in struct.iter_unpack('<IIQQ', data[16:16 + count * 24])
            if code == 99]


def analyze(before, after, marks, journal, trial, kernel_mark):
    old, _ = console(before)
    raw, info = console(after)
    log = raw.decode('utf-8', 'replace').replace('\r', '')
    args = re.findall(r'boot-args = ([^\n]*)', log)
    trials = [int(x) for line in args for x in re.findall(r'(?:^| )sweettrial=(\d+)(?= |$)', line)]
    builds = kernel_marks(marks)
    fresh = digest(raw) != digest(old)
    identity = trials == [trial] and builds == [kernel_mark]
    valid = fresh and identity
    # Counts remain observations even in a rejected capture. Only the gated
    # booleans below describe this trial, so a stale success cannot pass it.
    stages = {
        'exec_environment': len(re.findall(r'SWEET GLES: backboardd exec loader environment (?:added|already set)', log)),
        'amfi_dyld_allowed': len(re.findall(r'SWEET GLES: backboardd AMFI dyld in=0x[0-9a-f]+ out=0x12 error=0\b', log)),
        'loader_entered': log.count('SWEET GLES: enabling EAGL bridge in backboardd'),
        'bridge_loaded': log.count('SWEET GLES: EAGL bridge loaded; backend=softpipe hardware_claim=0'),
        'all_methods_installed': log.count('8 of 8 methods of EAGLContext are ours'),
        'es3_contexts': log.count('redwood-gl: an OpenGL ES 3 context for CoreAnimation,'),
    }
    frames = [dict(frame=int(m[0]), draws=int(m[1]), surface=int(m[2]),
                   display_draws=int(m[3]), in_place=int(m[4]), copied=int(m[5]))
              for m in re.findall(r'redwood-gl: f (\d+) at [0-9.]+ s: (\d+) draws, \d+ clears; '
                  r'display surface (\d+), (\d+) draws into it, [^\n]*?; (\d+) in place, (\d+) copied;', log)]
    submitted = [f for f in frames if f['draws'] and f['surface'] and f['display_draws']
                 and (f['in_place'] or f['copied'])]
    errors = {
        'bridge_load_failures': log.count('SWEET GLES: bridge load failed:'),
        'shader_compile_failures': log.count('A SHADER DOES NOT COMPILE'),
        'program_link_failures': log.count('A PROGRAM DOES NOT LINK'),
        'missing_dispatch_calls': log.count('CALLED AND NOT THERE:'),
        'gl_error_lines': len(re.findall(r'redwood-gl: [^\n]*: error 0x[0-9a-f]+', log)),
    }
    restored = (journal.get('restore_pending') is False and
                journal.get('status') == 'complete-restored-Recovery' and
                bool(journal.get('baseline_sha256')) and
                journal.get('restored_sha256') == journal['baseline_sha256'])
    return dict(trial=trial, expected_kernel_mark=hex(kernel_mark),
        console_sha256=digest(raw), console_fresh=fresh,
        captured_trials=trials, captured_kernel_marks=[hex(n) for n in builds],
        identity_matches=identity, capture_valid=valid, console=info,
        observed_stages=stages, observed_errors=errors,
        observed_frame_records=len(frames), observed_display_draw_frames=len(submitted),
        last_observed_frame=frames[-1] if frames else None,
        bridge_loaded_verified=valid and bool(stages['loader_entered'] and stages['bridge_loaded']),
        software_display_draws_verified=valid and all(stages.values()) and bool(submitted),
        visual_quality_verified=False, hardware_acceleration_verified=False,
        boot_a_restored=restored, restored_sha256=journal.get('restored_sha256'))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run_directory', type=Path)
    parser.add_argument('--trial', type=int, required=True)
    parser.add_argument('--kernel-mark', type=lambda x: int(x, 0), required=True)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    p = args.run_directory
    try:
        result = analyze((p / 'before-tail.bin').read_bytes(), (p / 'after-tail.bin').read_bytes(),
            (p / 'after-marks.bin').read_bytes(), json.loads((p / 'journal.json').read_text()),
            args.trial, args.kernel_mark)
    except (OSError, ValueError, struct.error) as exc:
        parser.exit(2, str(exc) + '\n')
    text = json.dumps(result, indent=2) + '\n'
    if args.output:
        args.output.write_text(text)
    print(text, end='')
    return 0 if result['capture_valid'] and result['boot_a_restored'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
