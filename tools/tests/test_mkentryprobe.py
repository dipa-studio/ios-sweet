"""Host-only layout/validation tests; no connected device or Apple files."""
import gzip
from pathlib import Path
import struct
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import mkbootimg
import mkentryprobe


def template(image=None, ramdisk=b'recovery-ramdisk'):
    if image is None:
        image = bytearray(0x8000)
        image[56:60] = b'ARM\x64'
        struct.pack_into('<3Q', image, 8, 0, len(image), 0xa)
        banner = b'Linux version test ' + b'x' * 500 + b'\n\0'
        image[0x1000:0x1000 + len(banner)] = banner
    kernel = gzip.compress(image, mtime=0)
    header = bytearray(4096)
    struct.pack_into('<8s4I', header, 0, b'ANDROID!', len(kernel), len(ramdisk), 0, 1584)
    struct.pack_into('<I', header, 40, 4)
    return (bytes(header) + kernel + bytes(mkbootimg.pad(len(kernel))-len(kernel))
            + ramdisk + bytes(mkbootimg.pad(len(ramdisk))-len(ramdisk)))


class ProbeLayoutTests(unittest.TestCase):
    def test_display_probe_layout_and_status_word(self):
        self.assertEqual(mkentryprobe.LEVELS['display'], 6)
        self.assertEqual(mkentryprobe.LEVELS['display-kick'], 6)
        self.assertEqual(mkentryprobe.DISPLAY_FIELDS['0'],
                         ('dsi0.CON_CTRL', 'dsi0.MODE_CTRL'))
        self.assertEqual(mkentryprobe.DISPLAY_FIELDS['3'],
                         ('dsi0.CMDQ_SIZE', 'dsi0.SIZE_CON'))
        self.assertEqual(mkentryprobe.DISPLAY_FIELDS['i'],
                         ('GCE thread 3 CURR_STATUS',
                          'GCE thread 3 WAIT_TOKEN'))
        self.assertEqual(mkentryprobe.DISPLAY_FIELDS['k'],
                         ('status', 'status'))
        self.assertIn('OVL not scanning boot fb',
                      mkentryprobe.DISPLAY_STATUS_CODES.values())
        display_record, display_offsets = mkentryprobe.banner_record('display')
        kick_record, kick_offsets = mkentryprobe.banner_record('display-kick')
        self.assertLessEqual(len(display_record), 407)  # measured capacity
        self.assertLessEqual(len(kick_record), 407)
        self.assertEqual(len(display_offsets), 21)
        self.assertEqual(display_offsets, kick_offsets)
        self.assertNotIn('dtb', display_offsets)
        decoded = mkentryprobe.decode_display_status((0x50 << 16) | 7)
        self.assertEqual(decoded['stage'], 0x50)
        self.assertEqual(decoded['code'], 7)
        self.assertEqual(decoded['code_name'], 'frame not completed')

    def test_record_offsets(self):
        record, offsets = mkentryprobe.banner_record()
        self.assertLessEqual(len(record), 407)  # measured test kernel capacity
        self.assertTrue(record.endswith(b'\n\0'))
        self.assertEqual(offsets['x16'], offsets['x0'] + 21)
        self.assertEqual(offsets['spsr'], offsets['x16'] + 22)
        for name in mkentryprobe.FIELDS:
            at = offsets[name]
            self.assertEqual(record[at:at+16], b'0' * 16)
            self.assertTrue(record[:at].endswith((name+'=').encode()))

    def test_only_banner_changed_and_ramdisk_retained(self):
        source = template()
        header, image, ramdisk, at, fields, old = mkentryprobe.prepare(source)
        self.assertEqual(at, 0x1000)
        self.assertEqual(header['header_version'], 4)
        self.assertEqual(ramdisk, b'recovery-ramdisk')
        self.assertEqual(image[56:60], b'ARM\x64')
        original = gzip.decompress(source[4096:4096+header['kernel_size']])
        image[at:at+len(old)] = old
        self.assertEqual(bytes(image), original)

    def test_short_printf_format_not_selected(self):
        source = template()
        h = mkbootimg.parse(source)
        image = bytearray(gzip.decompress(source[4096:4096+h['kernel_size']]))
        text = b'Linux version %s (%s)\0'
        image[0x200:0x200+len(text)] = text
        self.assertEqual(mkentryprobe.prepare(template(image))[3], 0x1000)

    def test_no_anywhere_flag_refused(self):
        source = template(); h = mkbootimg.parse(source)
        image = bytearray(gzip.decompress(source[4096:4096+h['kernel_size']]))
        struct.pack_into('<Q', image, 24, 2)
        with self.assertRaisesRegex(ValueError, 'anywhere'):
            mkentryprobe.prepare(template(image))

    def test_nonzero_text_offset_refused(self):
        source = template(); h = mkbootimg.parse(source)
        image = bytearray(gzip.decompress(source[4096:4096+h['kernel_size']]))
        struct.pack_into('<Q', image, 8, 0x80000)
        with self.assertRaisesRegex(ValueError, 'text_offset'):
            mkentryprobe.prepare(template(image))

    def test_truncated_ramdisk_refused(self):
        source = bytearray(template())
        struct.pack_into('<I', source, 12, len(source)+1)
        with self.assertRaisesRegex(ValueError, 'truncated'):
            mkentryprobe.prepare(source)

    def test_ambiguous_banner_refused(self):
        source=template(); h=mkbootimg.parse(source)
        image=bytearray(gzip.decompress(source[4096:4096+h['kernel_size']]))
        text=b'Linux version second ' + b'y'*500 + b'\0'
        image[0x4000:0x4000+len(text)] = text
        with self.assertRaisesRegex(ValueError, 'uniquely'):
            mkentryprobe.prepare(template(image))

    def test_usb_snapshot_layout(self):
        self.assertEqual(mkentryprobe.LEVELS['usb'], 1)
        self.assertEqual(mkentryprobe.USB_FIELDS['gicd'],
                         ('IPPC.PW_CTRL0', 'IPPC.PW_CTRL1'))
        self.assertEqual(mkentryprobe.USB_FIELDS['spsr'],
                         ('MAC.EP0CSR', 'MAC.RXCOUNT0'))
        self.assertIn('no MTU3 node', mkentryprobe.USB_STATUS_CODES.values())
        record, offsets = mkentryprobe.banner_record('usb')
        self.assertTrue(record.startswith(b'SWEET-ENTRY v1'))
        self.assertLessEqual(len(record), 407)
        self.assertEqual(len(offsets), 17)
        self.assertEqual(offsets['spsr'], offsets['x16'] + 22)

    def test_gpueb_snapshot_layout(self):
        self.assertEqual(mkentryprobe.LEVELS['gpueb'], 1)
        record, offsets = mkentryprobe.banner_record('gpueb')
        self.assertLessEqual(len(record), 407)
        self.assertIn('runtime memory', mkentryprobe.GPUEB_FIELDS['fb'])
        self.assertIn('not dereferenced', mkentryprobe.GPUEB_FIELDS['far'])
        self.assertIn('unverified', mkentryprobe.GPUEB_STATUS_CODES[0x9000])
        self.assertEqual(set(mkentryprobe.GPUEB_FIELDS) - set(offsets), set())

    def test_ufs_snapshot_requires_loader_level(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'boot.img'
            path.write_bytes(template())
            with self.assertRaisesRegex(ValueError, 'UFS register snapshot'):
                mkentryprobe.build(str(path), str(Path(tmp) / 'out.img'), None,
                                   'entry', ufs_regs=True)

    def test_ufs_init_requires_loader_level(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'boot.img'
            path.write_bytes(template())
            with self.assertRaisesRegex(ValueError, 'UFS pre-init'):
                mkentryprobe.build(str(path), str(Path(tmp) / 'out.img'), None,
                                   'entry', ufs_init=True)

    def test_ufs_selftest_requires_load_level(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'boot.img'
            path.write_bytes(template())
            with self.assertRaisesRegex(ValueError, 'UFS selftest'):
                mkentryprobe.build(str(path), str(Path(tmp) / 'out.img'), None,
                                   'entry', ufs_test=True)

    def test_ufs_query_mode_requires_init(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'boot.img'
            path.write_bytes(template())
            with self.assertRaisesRegex(ValueError, 'UFS query mode'):
                mkentryprobe.build(str(path), str(Path(tmp) / 'out.img'), None,
                                   'entry', ufs_query='read')


if __name__ == '__main__':
    unittest.main()
