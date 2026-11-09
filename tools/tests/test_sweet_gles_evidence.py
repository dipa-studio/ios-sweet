"""Regression: a previous successful boot cannot validate a new GLES trial."""
import importlib.util
from pathlib import Path
import struct
import unittest

spec = importlib.util.spec_from_file_location('gles', Path(__file__).resolve().parents[1] / 'sweet-gles-evidence.py')
gles = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gles)


def capture(log, seq=1):
    data = log.encode()
    return struct.pack('<8sIIQQ', b'SWEETLOG', 1, 4096, len(data), seq).ljust(4096, b'\0') + data.ljust(4096, b'\0')


def marks(build=0x2429):
    return (struct.pack('<8sII', b'SWEETMRK', 1, 1) + struct.pack('<IIQQ', 99, 0, build, 0)).ljust(4096, b'\0')


LOG = '''boot-args = sweetgles=1 sweettrial=2430
SWEET GLES: backboardd exec loader environment added
SWEET GLES: backboardd AMFI dyld in=0x0 out=0x12 error=0
SWEET GLES: enabling EAGL bridge in backboardd
redwood-gl: 8 of 8 methods of EAGLContext are ours; OpenGL ES by Mesa
SWEET GLES: EAGL bridge loaded; backend=softpipe hardware_claim=0
redwood-gl: an OpenGL ES 3 context for CoreAnimation, by Mesa: softpipe
redwood-gl: f 1 at 55.000 s: 3 draws, 1 clears; display surface 2, 3 draws into it, box off 0,0 1440x3200; vrd 0 vrb 0; 0 in place, 1 copied; spans 0
'''
JOURNAL = dict(status='complete-restored-Recovery', restore_pending=False,
               baseline_sha256='a' * 64, restored_sha256='a' * 64)


class EvidenceTests(unittest.TestCase):
    def result(self, old='', new=LOG, build=0x2429, journal=JOURNAL):
        return gles.analyze(capture(old), capture(new, 2), marks(build), journal, 2430, 0x2429)

    def test_success_requires_display_draw_evidence(self):
        r = self.result()
        self.assertTrue(r['software_display_draws_verified'])
        self.assertTrue(r['boot_a_restored'])
        self.assertFalse(r['hardware_acceleration_verified'])
        self.assertFalse(r['visual_quality_verified'])

    def test_changed_flush_sequence_is_not_a_fresh_console(self):
        r = self.result(old=LOG)
        self.assertFalse(r['capture_valid'])
        self.assertFalse(r['software_display_draws_verified'])

    def test_old_trial_and_wrong_build_rejected(self):
        for text, build in [(LOG.replace('sweettrial=2430', 'sweettrial=2428'), 0x2429), (LOG, 0x2316),
                            (LOG.replace('sweettrial=2430', 'sweettrial=24300'), 0x2429)]:
            self.assertFalse(self.result(new=text, build=build)['capture_valid'])

    def test_library_loaded_is_not_a_frame(self):
        r = self.result(new=LOG[:LOG.index('redwood-gl: f 1')])
        self.assertTrue(r['bridge_loaded_verified'])
        self.assertFalse(r['software_display_draws_verified'])

    def test_draws_without_a_display_surface_are_not_display_draws(self):
        self.assertFalse(self.result(new=LOG.replace('display surface 2', 'display surface 0'))['software_display_draws_verified'])

    def test_pending_or_mismatched_restore_cannot_pass(self):
        for delta in [dict(restore_pending=True), dict(restored_sha256='b' * 64), dict(status='restoring-full-boot-a')]:
            self.assertFalse(self.result(journal=dict(JOURNAL, **delta))['boot_a_restored'])

    def test_truncated_captures_rejected(self):
        with self.assertRaises(ValueError):
            gles.console(capture(LOG)[:-1])
        with self.assertRaises(ValueError):
            gles.kernel_marks(marks()[:-1])


if __name__ == '__main__':
    unittest.main()
