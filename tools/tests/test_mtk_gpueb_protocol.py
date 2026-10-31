"""Validate GPUEB wire bytes and reject unsafe/missing handoff descriptions."""
import copy
import ctypes
import importlib.util
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location('inventory', ROOT / 'tools/matisse-gpu-inventory.py')
inventory = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(inventory)
sys.path.insert(0, str(ROOT / 'tools'))
import mkentryprobe


def cells(*values):
    return struct.pack('>%dI' % len(values), *values)


def fixture():
    return {'/soc/gpueb@13c00000': {
        'compatible': b'mediatek,gpueb\0', 'gpueb-support': cells(1),
        'mbox_count': cells(1), 'mbox_size': cells(160), 'slot_size': cells(4),
        'send_table': cells(0, 0, 4, 1, 0, 8),
        'send_name_table': b'IPI_ID_EVENT\0IPI_ID_GPUFREQ\0',
        'recv_table': cells(0, 0, 4, 0, 1, 0, 8, 1),
        'recv_name_table': b'IPI_ID_EVENT\0IPI_ID_GPUFREQ\0',
        'gpueb_mem_table': cells(0, 4096, 1, 0x180000),
        'gpueb_mem_name_table': b'MEM_ID_GPUFREQ\0MEM_ID_LOG\0',
    }}


def flat_fdt(nodes):
    """Independent FDT writer for testing the actual pre-kernel C reader."""
    strings = bytearray()
    offsets = {}
    for props in nodes.values():
        for key in props:
            if key not in offsets:
                offsets[key] = len(strings)
                strings += key.encode() + b'\0'
    def pad(raw):
        return raw + bytes(-len(raw) % 4)
    def node(path):
        name = path.rsplit('/', 1)[-1]
        body = cells(1) + pad(name.encode() + b'\0')
        for key, value in nodes.get(path, {}).items():
            body += cells(3, len(value), offsets[key]) + pad(value)
        children = set()
        prefix = path.rstrip('/') + '/'
        for p in nodes:
            if p.startswith(prefix) and p != path:
                children.add(prefix + p[len(prefix):].split('/')[0])
        for child in sorted(children):
            body += node(child)
        return body + cells(2)
    body = node('/') + cells(9)
    return (cells(0xd00dfeed, 56 + len(body) + len(strings), 56, 56 + len(body),
                  40, 17, 16, 0, len(strings), len(body)) + bytes(16) + body + strings)


@unittest.skipUnless(shutil.which('cc'), 'needs C compiler')
class GpuebEntryProbeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix='gpueb-entry-')
        work = Path(cls.temp.name)
        cls.record, cls.offsets = mkentryprobe.banner_record('gpueb')
        (work / 'entryprobe_config.h').write_text(''.join(
            '#define ENTRY_%s %d\n' % (name.upper(), at) for name, at in cls.offsets.items()))
        binary = work / 'probe.dylib'
        subprocess.run(['cc', '-shared', '-fPIC', '-std=c11', '-Wall', '-Wextra', '-Werror',
                        '-I', str(work), str(ROOT / 'shim/entryprobe_gpueb.c'),
                        str(ROOT / 'shim/fdt.c'), str(ROOT / 'xnu/gpu/mtk_gpueb_protocol.c'),
                        '-o', str(binary)], check=True, capture_output=True)
        cls.lib = ctypes.CDLL(str(binary))
        cls.lib.entryprobe_gpueb.argtypes = [ctypes.c_size_t, ctypes.c_void_p]

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def snapshot(self, nodes):
        tree = ctypes.create_string_buffer(flat_fdt(nodes))
        banner = ctypes.create_string_buffer(self.record)
        self.lib.entryprobe_gpueb(ctypes.addressof(tree), banner)
        return {name: int(banner.raw[at:at + 16], 16) for name, at in self.offsets.items()}

    def test_recovery_snapshot_reports_missing_runtime_memory(self):
        nodes = fixture()
        nodes['/chosen'] = {'atag,boot': struct.pack('<4I', 16, 0x41000802, 2, 2)}
        nodes['/soc/mali@13000000'] = {'compatible': b'mediatek,mali\0',
                                     'reg': struct.pack('>QQ', 0x13000000, 0x480000)}
        result = self.snapshot(nodes)
        self.assertEqual(result['stage'], 0x9004)
        self.assertEqual(result['x0'], 2)
        self.assertEqual(result['gicd'], 0x13000000)
        self.assertEqual(result['vtimer'], 0x480000)
        self.assertEqual(result['far'], 0)

    def test_success_describes_addresses_without_dereferencing(self):
        nodes = fixture()
        props = next(iter(nodes.values()))
        props['gpueb_mem_addr'] = struct.pack('>Q', 0x240000000)
        props['gpueb_mem_size'] = struct.pack('>Q', 0x200000)
        result = self.snapshot(nodes)
        self.assertEqual(result['stage'], 0x9000)
        self.assertEqual(result['fb'], 0x240000000)
        self.assertEqual(result['far'], 0x240000000)
        self.assertEqual(result['pc'], 0x240000400)
        self.assertEqual(result['spsr'], (0x400 << 32) | 0xc00)
        self.assertEqual(result['x0'], (1 << 64) - 1)
        props['gpueb_mem_name_table'] = b'MEM_ID_GPUFREQ'
        self.assertEqual(self.snapshot(nodes)['stage'], 0x9005)
        props['gpueb_mem_name_table'] = b'MEM_ID_GPUFREQ\0MEM_ID_LOG\0'
        props['gpueb_mem_addr'] = struct.pack('>Q', 0)
        self.assertEqual(self.snapshot(nodes)['stage'], 0x9005)

    def test_absent_and_disabled_snapshot(self):
        self.assertEqual(self.snapshot({})['stage'], 0x9001)
        nodes = fixture()
        next(iter(nodes.values()))['gpueb-support'] = cells(0)
        self.assertEqual(self.snapshot(nodes)['stage'], 0x9002)


class GpuebHandoffTests(unittest.TestCase):
    def test_missing_memory_never_produces_addresses(self):
        result = inventory.gpueb_handoff(fixture())
        self.assertEqual(result['state'], 'runtime-memory-missing')
        self.assertEqual(result['channels']['send'][1]['byte_offset'], 16)
        self.assertEqual(result['channels']['recv'][1]['byte_offset'], 64)
        self.assertEqual(result['memory_table_bytes'], 0x181000)
        self.assertNotIn('status_pa', result)
        self.assertFalse(result['mmio_access_permitted'])

    def test_runtime_description_requires_covering_reservation(self):
        nodes = fixture()
        props = next(iter(nodes.values()))
        props['gpueb_mem_addr'] = struct.pack('>Q', 0x240000000)
        props['gpueb_mem_size'] = struct.pack('>Q', 0x200000)
        result = inventory.gpueb_handoff(nodes)
        self.assertEqual(result['state'], 'reservation-unverified')
        nodes['/reserved-memory'] = {'#address-cells': cells(2), '#size-cells': cells(2), 'ranges': b''}
        nodes['/reserved-memory/gpueb'] = {'reg': struct.pack('>QQ', 0x240000000, 0x200000)}
        result = inventory.gpueb_handoff(nodes)
        self.assertEqual(result['state'], 'described')
        self.assertEqual(result['debug_pa'], 0x240000400)
        self.assertEqual(result['debug_bytes'], 0xc00)
        self.assertFalse(result['firmware_running_verified'])
        self.assertFalse(result['mmio_access_permitted'])
        nodes['/reserved-memory']['ranges'] = cells(1)
        self.assertEqual(inventory.gpueb_handoff(nodes)['state'], 'reservation-unverified')

    def test_memory_ids_accumulate_in_id_order(self):
        nodes = fixture()
        props = next(iter(nodes.values()))
        props['gpueb_mem_table'] = cells(1, 0x180000, 0, 4096)
        result = inventory.gpueb_handoff(nodes)
        self.assertEqual(result['memory_regions'][1]['offset'], 4096)

    def test_bad_channels_and_tables_fail_closed(self):
        for key, raw in [
            ('send_table', cells(0, 0, 4, 0, 0, 8)),
            ('send_table', cells(0, 0, 4, 1, 1, 8)),
            ('send_table', cells(0, 0, 4, 1, 0, 7)),
            ('recv_table', cells(0, 0, 4, 0, 1, 0, 8, 0)),
            ('recv_table', cells(0, 0, 4, 0, 2, 0, 8, 1)),
            ('mbox_size', cells(12)), ('slot_size', cells(8)),
            ('gpueb_mem_table', cells(0, 4096, 0, 4096)),
            ('gpueb_mem_table', cells(0, 4096, 2, 4096)),
            ('gpueb_mem_table', cells(0, 1024, 1, 4096)),
            ('gpueb_mem_table', cells(0, 4096, 1)),
            ('send_name_table', b'IPI_ID_EVENT\0IPI_ID_GPUFREQ'),
        ]:
            with self.subTest(key=key, raw=raw):
                nodes = fixture()
                next(iter(nodes.values()))[key] = raw
                before = copy.deepcopy(nodes)
                with self.assertRaises(ValueError):
                    inventory.gpueb_handoff(nodes)
                self.assertEqual(nodes, before)

    def test_bad_runtime_bounds(self):
        for base, size in [(0, 0x200000), (0x800000000, 0x200000),
                           (0x7fffff000, 0x200000), (0x40000001, 0x200000),
                           (0x40000000, 4096), (0x40000000, 0)]:
            nodes = fixture()
            props = next(iter(nodes.values()))
            props['gpueb_mem_addr'] = struct.pack('>Q', base)
            props['gpueb_mem_size'] = struct.pack('>Q', size)
            with self.subTest(base=base, size=size), self.assertRaises(ValueError):
                inventory.gpueb_handoff(nodes)

    def test_absent_disabled_and_ambiguous(self):
        self.assertEqual(inventory.gpueb_handoff({})['state'], 'absent')
        nodes = fixture()
        next(iter(nodes.values()))['gpueb-support'] = cells(0)
        self.assertEqual(inventory.gpueb_handoff(nodes)['state'], 'disabled')
        nodes['/other-gpueb'] = next(iter(nodes.values())).copy()
        with self.assertRaises(ValueError):
            inventory.gpueb_handoff(nodes)


HARNESS = r'''
#include <assert.h>
#include <stdio.h>
#include <string.h>
#include "mtk_gpueb_protocol.h"
static void be(uint8_t *p, uint32_t v) {
    p[0]=v>>24;p[1]=v>>16;p[2]=v>>8;p[3]=v;
}
int main(void) {
    uint8_t table[16], msg[32], sentinel[32], reply[32]={6};
    struct sweet_gpueb_shared layout, before;
    memset(&layout,0xa5,sizeof(layout)); before=layout;
    be(table,0);be(table+4,4096);be(table+8,1);be(table+12,0x180000);
    for (size_t n=0;n<16;n++) {
        if(n==8) continue; /* A complete one-region table is valid too. */
        assert(sweet_gpueb_shared_layout(0x240000000ULL,0x200000,table,n,0,&layout));
        assert(!memcmp(&layout,&before,sizeof(layout)));
    }
    assert(!sweet_gpueb_shared_layout(0x240000000ULL,0x200000,table,16,0,&layout));
    assert(layout.status_pa==0x240000000ULL && layout.debug_pa==0x240000400ULL);
    assert(layout.status_bytes==0x400 && layout.debug_bytes==0xc00);
    assert(!sweet_gpueb_encode_init(&layout,msg));
    const uint8_t init[32]={0,0,0,0,0,0,0,0,0,0,0,0x40,2,0,0,0,
                           0,4,0,0x40,2,0,0,0,0,4,0,0,0,12,0,0};
    assert(!memcmp(msg,init,32));
    assert(!sweet_gpueb_encode_power(1,msg));
    const uint8_t power[32]={6,0,0,0,0,0,0,0,1};
    assert(!memcmp(msg,power,32));
    memcpy(sentinel,msg,32); assert(sweet_gpueb_encode_power(2,msg));
    assert(!memcmp(msg,sentinel,32));
    layout.debug_pa++; assert(sweet_gpueb_encode_init(&layout,msg));
    assert(!memcmp(msg,sentinel,32));
    layout.debug_pa--;
    assert(sweet_gpueb_shared_layout(0x7fffff000ULL,0x200000,table,16,0,&layout));
    assert(sweet_gpueb_shared_layout(0x240000000ULL,4096,table,16,0,&layout));
    be(table+8,0);assert(sweet_gpueb_shared_layout(0x240000000ULL,0x200000,table,16,0,&layout));
    be(table+8,2);assert(sweet_gpueb_shared_layout(0x240000000ULL,0x200000,table,16,0,&layout));
    be(table+8,1);be(table+4,1024);
    assert(sweet_gpueb_shared_layout(0x240000000ULL,0x200000,table,16,0,&layout));
    be(table,1);be(table+4,0x180000);be(table+8,0);be(table+12,4096);
    assert(!sweet_gpueb_shared_layout(0x240000000ULL,0x200000,table,16,0,&layout));
    assert(layout.status_pa==0x240000000ULL);
    int32_t result=123;
    for(size_t n=0;n<32;n++) {
        assert(sweet_gpueb_decode_response(reply,n,6,&result)); assert(result==123);
    }
    reply[8]=0xea;reply[9]=reply[10]=reply[11]=0xff;
    assert(!sweet_gpueb_decode_response(reply,32,6,&result) && result==-22);
    reply[8]=reply[9]=reply[10]=0;reply[11]=0x80;
    assert(!sweet_gpueb_decode_response(reply,32,6,&result) && result==INT32_MIN);
    reply[4]=1;assert(sweet_gpueb_decode_response(reply,32,6,&result));
    reply[4]=0;assert(sweet_gpueb_decode_response(reply,32,0,&result));
    assert(sweet_gpueb_decode_response(NULL,32,6,&result));
    assert(sweet_gpueb_encode_init(NULL,msg));
    /* Mutation corpus: all rejection paths must preserve output. */
    uint32_t rng=1;
    for(unsigned i=0;i<8192;i++) {
        for(unsigned j=0;j<16;j++) {rng=rng*1664525u+1013904223u;table[j]=rng>>24;}
        memset(&layout,0xa5,sizeof(layout));before=layout;
        int rc=sweet_gpueb_shared_layout(0x240000000ULL,0x200000,table,i%17,0,&layout);
        if(rc) assert(!memcmp(&layout,&before,sizeof(layout)));
    }
    puts("PASS: GPUEB layout, 32-byte wire ABI, signed replies, 8192 mutations");
    return 0;
}
'''


@unittest.skipUnless(shutil.which('cc'), 'needs C compiler')
class GpuebProtocolTests(unittest.TestCase):
    def test_portable_wire_helpers_with_sanitizers(self):
        with tempfile.TemporaryDirectory(prefix='gpueb-protocol-') as directory:
            work = Path(directory)
            source = work / 'test.c'
            source.write_text(HARNESS)
            binary = work / 'test'
            subprocess.run(['cc', '-std=c11', '-Wall', '-Wextra', '-Werror',
                            '-fsanitize=address,undefined', '-I', str(ROOT / 'xnu/gpu'),
                            str(source), str(ROOT / 'xnu/gpu/mtk_gpueb_protocol.c'),
                            '-o', str(binary)], check=True, capture_output=True)
            subprocess.run([str(binary)], check=True, capture_output=True)


if __name__ == '__main__':
    unittest.main()
