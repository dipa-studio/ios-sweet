"""Bounds, supplier allowlist, and wire validation without firmware or devices."""
import base64
from contextlib import ExitStack
import errno
import gzip
import hashlib
import importlib.util
import io
from pathlib import Path
import stat
import struct
import shutil
import subprocess
import sys
import tarfile
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'tools'))
import mkbootimg


def load(name, file):
    spec = importlib.util.spec_from_file_location(name, ROOT/'tools'/file)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


build = load('collector', 'matisse-ramcollector.py')
receive = load('receiver', 'matisse-collector-receive.py')


def elf(program_type=1):
    b = bytearray(120); b[:6] = b'\x7fELF\x02\x01'
    struct.pack_into('<HH', b, 16, 2, 183)
    struct.pack_into('<Q', b, 32, 64)
    struct.pack_into('<HH', b, 54, 56, 1)
    struct.pack_into('<I', b, 64, program_type)
    return bytes(b)


def archive(extra=None):
    out = io.BytesIO()
    with tarfile.open(fileobj=out, mode='w:gz') as t:
        for phase in ('before-modules','after-modules'):
            for name in ('live.dtb','pl_lk.bin','proc-mounts.txt','dmesg.txt'):
                i = tarfile.TarInfo(phase+'/'+name); i.size = 4
                t.addfile(i,io.BytesIO(b'data'))
        if extra:
            t.addfile(extra)
    return out.getvalue()


def frame(blob):
    return (b'MATISSE-COLLECTOR-V1 '+str(len(blob)).encode()+b' '+
            hashlib.sha256(blob).hexdigest().encode()+b'\n'+
            base64.encodebytes(blob)+b'MATISSE-COLLECTOR-END\n')


class CollectorTests(unittest.TestCase):
    def test_priority_handoff_frame_is_independent_and_bounded(self):
        dtb=bytearray(40);dtb[:4]=bytes.fromhex('d00dfeed');dtb[4:8]=(40).to_bytes(4,'big')
        payload=gzip.compress(bytes(dtb),mtime=0)
        encoded=frame(payload).replace(b'MATISSE-COLLECTOR',b'MATISSE-HANDOFF')
        self.assertEqual(receive.handoff_dtb(receive.decode_frame(encoded,handoff=True)),bytes(dtb))
        self.assertIsNone(receive.decode_frame(encoded))
        with self.assertRaises(ValueError):receive.handoff_dtb(gzip.compress(b'x'*(2*1024*1024+1)))
        with self.assertRaises(ValueError):receive.handoff_dtb(gzip.compress(bytes(dtb)+b'extra'))

    def test_partial_serial_bytes_are_saved_before_read_disconnect(self):
        partial=b'MATISSE-COLLECTOR-V1 12345 '+b'a'*64+b'\nYWJj'
        observed=[]
        with ExitStack() as stack:
            stack.enter_context(mock.patch.object(receive.os,'open',return_value=42))
            stack.enter_context(mock.patch.object(receive.os,'close'))
            stack.enter_context(mock.patch.object(receive.termios,'tcgetattr',return_value=[]))
            stack.enter_context(mock.patch.object(receive.termios,'tcsetattr'))
            stack.enter_context(mock.patch.object(receive.tty,'setraw'))
            stack.enter_context(mock.patch.object(receive.termios,'tcflush'))
            stack.enter_context(mock.patch.object(receive.select,'select',return_value=([42],[],[])))
            stack.enter_context(mock.patch.object(receive.os,'read',side_effect=[partial,OSError(errno.ENXIO,'gone')]))
            with self.assertRaises(OSError):receive.receive('/dev/cu.usbmodem-test',1,lambda c,d:observed.append(bytes(c)))
        self.assertEqual(observed,[partial])

    def test_vanished_acm_preserves_read_error_and_closes_descriptor(self):
        with ExitStack() as stack:
            stack.enter_context(mock.patch.object(receive.os,'open',return_value=42))
            closed=stack.enter_context(mock.patch.object(receive.os,'close'))
            stack.enter_context(mock.patch.object(receive.termios,'tcgetattr',return_value=[]))
            stack.enter_context(mock.patch.object(receive.tty,'setraw'))
            stack.enter_context(mock.patch.object(receive.termios,'tcflush'))
            stack.enter_context(mock.patch.object(receive.select,'select',return_value=([42],[],[])))
            failure=OSError(errno.ENXIO,'read disconnected')
            stack.enter_context(mock.patch.object(receive.os,'read',side_effect=failure))
            stack.enter_context(mock.patch.object(receive.termios,'tcsetattr',
                side_effect=receive.termios.error(errno.ENXIO,'cleanup disconnected')))
            with self.assertRaises(OSError) as caught:
                receive.receive('/dev/cu.usbmodem-test',1)
            self.assertIs(caught.exception,failure)
            closed.assert_called_once_with(42)

    def test_failed_tty_initialization_still_closes_descriptor(self):
        with mock.patch.object(receive.os,'open',return_value=42), \
             mock.patch.object(receive.os,'close') as closed, \
             mock.patch.object(receive.termios,'tcgetattr',
                side_effect=receive.termios.error(errno.ENXIO,'port vanished')):
            with self.assertRaises(receive.termios.error):
                receive.receive('/dev/cu.usbmodem-test',1)
            closed.assert_called_once_with(42)

    @unittest.skipUnless(shutil.which('lz4'), 'lz4 CLI required')
    def test_actual_platform_prefix_legacy_lz4_concat(self):
        archive=build.pack_newc({'collector':(stat.S_IFREG|0o755,b'payload')})
        packed=build.compress_ramdisk(archive)
        self.assertEqual(packed,build.compress_ramdisk(archive))
        joined=build.LZ4_MAGIC+packed
        decoded=subprocess.run(['lz4','-d','-c'],input=joined,capture_output=True,check=True).stdout
        self.assertEqual(build.read_newc(decoded)['collector'][1],b'payload')

    def test_newc_deterministic_roundtrip(self):
        e = {'b':(stat.S_IFREG|0o755,b'abc'),
             'dir':(stat.S_IFDIR|0o755,b''),
             'dir/link':(stat.S_IFLNK|0o777,b'../b')}
        self.assertEqual(build.read_newc(build.pack_newc(e)),e)
        self.assertEqual(build.pack_newc(e),build.pack_newc(dict(reversed(list(e.items())))))

    def test_newc_rejects_traversal_duplicates_truncation(self):
        for name in ('../bad','/bad','dir/../../bad'):
            with self.assertRaises(ValueError):
                build.read_newc(build.pack_newc({name:(stat.S_IFREG,b'')}))
        good = build.pack_newc({'foo':(stat.S_IFREG,b'x')})
        for short in (good[:50],good[:115],good[:116]):
            with self.assertRaises(ValueError): build.read_newc(short)
        first = good[:116+4]
        with self.assertRaises(ValueError): build.read_newc(first+good)
        with self.assertRaises(ValueError): build.read_newc(good+b'not-another-archive')

    def test_static_arm64_rejects_dynamic_other_arch_and_truncated(self):
        build.static_arm64(elf())
        for typ in (2,3):
            with self.assertRaises(ValueError): build.static_arm64(elf(typ))
        other = bytearray(elf());struct.pack_into('<H',other,18,62)
        for bad in (bytes(other),elf()[:100],b'not ELF'):
            with self.assertRaises(ValueError): build.static_arm64(bad)

    def test_dependency_closure_order_and_block_driver_rejected(self):
        graph = {n:[] for n in build.SEEDS}
        graph['clk-mt6983.ko']=['clk-common.ko']
        graph['clk-common.ko']=['aee_aed.ko']
        graph['aee_aed.ko']=['mrdump.ko'];graph['mrdump.ko']=[]
        def text(): return '\n'.join(n+': '+' '.join(d) for n,d in graph.items())
        ordered = build.module_order(text())
        self.assertLess(ordered.index('mrdump.ko'),ordered.index('clk-mt6983.ko'))
        graph['mtu3.ko']=['ufs-mediatek-mod.ko']
        with self.assertRaisesRegex(ValueError,'unreviewed'): build.module_order(text())
        graph['mtu3.ko']=['mtu3.ko']
        with self.assertRaisesRegex(ValueError,'cycle'): build.module_order(text())

    def test_boot_replacement_retains_kernel_signature_and_overrides_init(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'source.img';out=Path(d)/'out.img'
            kernel=bytes(range(128));signature=b'signature'
            mkbootimg.build(kernel,b'old','quiet',p,signature_size=len(signature),signature=signature)
            report=build.rebuild_boot(p.read_bytes(),b'new',out)
            b=out.read_bytes();h=mkbootimg.parse(b)
            self.assertEqual(b[4096:4224],kernel)
            self.assertEqual(h['signature'],signature)
            self.assertIn(b'rdinit=/matisse-collector/init',h['cmdline'])
            self.assertEqual(b[8192:8195],b'new')
            self.assertFalse(report['signature_revalidated'])
            mkbootimg.build(kernel,b'old','rdinit=/init',p)
            with self.assertRaisesRegex(ValueError,'existing init'):build.rebuild_boot(p.read_bytes(),b'x',out)
            with self.assertRaises(ValueError):build.rebuild_boot(b'ANDROID!',b'x',out)

    def test_wire_complete_partial_corrupt_and_oversized(self):
        blob=archive();encoded=frame(blob)
        self.assertEqual(receive.decode_frame(b'old-tail\n'+encoded),blob)
        self.assertIsNone(receive.decode_frame(encoded[:-30]))
        corrupt=encoded.replace(hashlib.sha256(blob).hexdigest().encode(),b'0'*64)
        with self.assertRaisesRegex(ValueError,'SHA256'):receive.decode_frame(corrupt)
        too_big=b'MATISSE-COLLECTOR-V1 999999999 '+b'0'*64+b'\n'
        with self.assertRaises(ValueError):receive.decode_frame(too_big)

    def test_archive_paths_symlinks_and_missing_members_rejected(self):
        self.assertEqual(len(receive.archive_files(archive())),8)
        for path in ('../outside','after-modules/../../bad','after-modules/surprise'):
            with self.assertRaises(ValueError):receive.archive_files(archive(tarfile.TarInfo(path)))
        link=tarfile.TarInfo('after-modules/init.log');link.type=tarfile.SYMTYPE;link.linkname='/etc/passwd'
        with self.assertRaises(ValueError):receive.archive_files(archive(link))

    def test_init_is_closed_no_block_mount_or_command_receiver(self):
        s=(ROOT/'tools/ramcollector/init').read_text()
        self.assertIn('[ "$$" = 1 ] || exit 64',s)
        self.assertNotIn('switch_root',s)
        self.assertNotIn('mount -t ext4',s)
        self.assertNotIn('mount -t erofs',s)
        self.assertNotIn('dd ',s)
        self.assertNotIn('/dev/block',s)
        self.assertIn('no-modprobe',s)
        self.assertIn('--snapshot-only',s)
        self.assertNotIn('read -r command',s)


if __name__=='__main__':unittest.main()
