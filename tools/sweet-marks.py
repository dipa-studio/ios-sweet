#!/usr/bin/env python3
"""Decode the SWEET boot-progress marks (kernel patch 0095).

  sweet-marks.py [FILE] [--pull]

The kernel rewrites a record block into the LAST 4 KiB block of the userdata
partition on every sweet_mark() call, so after a hang the last step it
reached is still on disk. With --pull the block is read from a phone in
recovery over adb; otherwise FILE must be a 4096-byte dump of that block.

Layout: "SWEETMRK" | u32 version | u32 count | count * { u32 code, pad,
u64 a, u64 b }.
"""
import struct
import subprocess
import sys
import time

NAMES = {
    1: 'mtu3 probe entry',
    2: 'adt /sweet-usb found',
    3: 'ml_io_map(MAC)',
    4: 'ml_io_map(IPPC)',
    5: 'read IPPC_HW_ID',
    6: 'read IPPC_HW_SUB_ID',
    7: 'read IPPC_DEV_CAP',
    8: 'mt_powered() ok',
    9: 'read DEVICE_CONF/EP0CSR/MISC/PM',
    10: 'userdata geometry known (mark channel live)',
    11: 'sweet_ufs_init -> sweet_usb_probe',
    12: 'sweet_usb_probe returned',
    13: 'sweet_keys_init returned',
    14: 'sweet_touch_init returned',
    15: 'read CAP_EP*FFSZ',
    20: 'mt_start entry',
    21: 'kmem_alloc_contig',
    22: 'pmap_find_phys',
    23: 'mt_if_create',
    24: 'mt_hw_init returned',
    30: 'hw_init entry',
    31: 'pull-up off',
    32: 'IPPC DEV_RST_CTRL toggle',
    33: 'IPPC PW_CTRL2 (port enable)',
    34: 'IPPC U3_CTRL_0P',
    35: 'IPPC U2_CTRL_0P',
    36: 'interrupt status cleared',
    37: 'vendor csr init',
    38: 'DEVICE_CONF=0 + VBUS force',
    39: 'TXDEEMPH',
    40: 'USB3 off + HS enable',
    41: 'EP0 reset state',
    42: 'soft connect (D+ pull-up)',
    43: 'mtu3 poll thread entered',
    44: 'mtu3 first poll: a=EP0CSR b=COMMON_USB_INTR',
    45: 'mtu3 1000 polls: a=setups<<32|resets b=EP0CSR',
    46: 'usb snapshot: a=polls b=setups<<32|resets',
    47: 'usb snapshot: a=EP0CSR b=COMMON_USB_INTR<<32|DEV_LINK_INTR',
    48: 'usb snapshot: a=DEVICE_CONF b=POWER_MANAGEMENT<<32|speed',
    49: 'usb snapshot: a=LINK_STATE_MACHINE b=USB20_OPSTATE<<32|configured',
    50: 'bsd_init -> vfs_mountroot',
    51: 'root mounted',
    52: 'root mount FAILED (a=errno)',
    53: 'IOSecureBSDRoot done',
    54: 'VFS_ROOT (root vnode) ok',
    55: 'vfs_mountroot entry',
    56: 'mountroot hook returned (a=errno)',
    60: 'bsd_init -> load_init_program',
    61: 'load_init_program returned',
    62: 'load_init_program entry',
    63: 'init candidate tried (a=index, b=errno)',
    64: 'init exec failed, about to panic (a=index, b=errno)',
    65: 'load_init_program_at_path entry',
    86: 'display refresh: a=calls b=pushes',
    87: 'legacy display white probe',
    88: 'touch thread woke (a=delay seconds, b=SPI virtual address)',
    89: 'touch init snapshot (a=enabled|trace, b=status<<48|call<<32|stage)',
    90: 'console mapping: a=VA b=physical address',
    91: 'console PAR: a=first pixel b=last pixel',
    93: 'display: a=stride<<32|height b=pre-poll INTSTA',
    94: 'LK DSI: a=CON_CTRL b=TXRX_CTRL',
    95: 'LK DSI: a=CMDQ_SIZE b=CMDQ0',
    96: 'touch SPI6 probe (a=error/id, b=CFG1/CFG2)',
    97: 'touch down (a=finger/raw-x, b=raw-y)',
    98: 'touch up (a=finger/panel-x, b=panel-y)',
    99: 'kernel build ID: a=build b=source line',
    100: 'touch platform: a=CLK_CFG_7/peripheral gate b=SPI6 pinmux/drive',
    101: 'touch diagnostic scheduler hold: a=seconds',
    102: 'touch diagnostic scheduler hold ended: a=seconds',
    103: 'touch SPI timing: a=CFG0/CFG3 b=CMD/STATUS0',
    104: 'touch reset GPIO3: a=mode<<32|dir<<1|out before, b=after',
    105: 'usb diagnostic hold: a=seconds',
    106: 'usb diagnostic hold ended (USB snapshot follows)',
    110: 'touch sweep pre: a=CFG3/PAD_SEL b=STATUS0',
    111: 'touch sweep loopback: a=rx0-3<<32|err b=rx4-7<<32|match',
    112: 'touch sweep A: 4-byte address, CFG3 written 0',
    113: 'touch sweep B: 4-byte address, CFG3 kept',
    114: 'touch sweep C: 3-byte address, CFG3 kept',
    115: 'touch sweep D: PAD_SEL 0, CFG3 kept',
    116: 'touch sweep E: SAMPLE_SEL 1, CFG3 kept',
    117: 'touch sweep STATUS1 A<<32|B, C<<32|D',
    118: 'touch sweep: a=STATUS1 E b=CFG3/PAD_SEL final',
    119: 'touch sweep time ns: a=loopback b=baseline',
    120: 'touch pads: a=mode before<<32|after b=drive before<<32|after',
    122: 'touch reset pad loopback: a=DIN low<<1|high b=DOUT',
    123: 'touch baseline pads: a=idle<<32|seen b=STATUS1<<32|ns',
    124: 'touch loopback pads: a=idle<<32|seen b=STATUS1<<32|ns',
    130: 'touch bitbang rx (4-byte address)',
    131: 'touch bitbang rx (3-byte address)',
    132: 'touch bitbang idle: a=DIN<<32|mode b=mode readback',
    133: 'touch GPIO mode switch: a=before<<32|after b=DIR word',
    134: 'touch IRQ8 samples: a=high<<32|low b=mode reg',
    135: 'touch IES word: a=before<<32|after b=IOCFG_BM +0x110',
    136: 'touch pad PU/PD: a=+0x70 b=+0xA0',
    137: 'touch IRQ8 IES: a=before<<32|after b=0',
    138: 'touch IRQ8 before reset: a=high<<32|low b=0',
    139: 'touch chip ID after long reset',
    140: 'touch IRQ8 after reset: a=high<<32|low b=err',
    141: 'mt6373 enable: a=VRF18 val<<32|err b=VTP val<<32|err',
    142: 'mt6373 vosel: a=VRF18 val<<32|err b=VTP val<<32|err',
    145: 'mt6373 enable after reset: a=VRF18<<32|err b=VTP<<32|err',
    146: 'mt6373 vosel after reset: a=VRF18<<32|err b=VTP<<32|err',
    147: 'spmi info: a=apid_count<<32|init b=arb version',
    148: 'spmi lane sid5/0x1b: a=found<<40|apid<<20|owner<<16 b=map',
    149: 'spmi lane sid5/0x1d: a=found<<40|apid<<20|owner<<16 b=map',
    150: 'spmi control read sid0/0x1000: a=val<<32|err b=0',
    151: 'pmif regs: a=init_done<<32|inf_en b=arb_en<<32|cmdissue_en',
    153: 'pmif SWINF sta: a=before first read b=last read',
    154: 'touch IRQ8 probe: a=high<<32|low b=mode win before<<32|after',
    155: 'mt6373 vrf-only: a=VRF18 val<<32|old b=vosel val<<32|old',
    156: 'touch bitbang system reset 0x81',
    157: 'touch bitbang chip ID pass 1',
    158: 'touch bitbang chip ID pass 2',
    152: 'mt6373 vpower after: a=VRF vsel<<8|en b=VTP vsel<<8|en',
    173: 'mt6373 vpower before: a=VRF vsel<<8|VTP vsel b=VTP en<<8|VRF en',
    174: 'mt6373 VRF18 energise: a=reg<<32|sel b="ENRG"/"ENR>"',
    175: 'mt6373 VTP energise/ramp: a=reg<<32|sel b="ENRG"/"ENR>"/"KEEP"',
    159: 'mt6373 VRF18 enable: a=err<<32|readback b="VRFE"',
    143: 'mt6373 rails after power-on: a=VRF18 val<<32|err b=VTP val<<32|err',
    144: 'mt6373 rail writes: a=w_vtp<<32|w_vrf b=VTP_val<<8|VRF_val',
    160: 'touch power on entered',
    161: 'power on spmi init: a=rc<<32|init_done b=SWINF sta',
    162: 'power on rails before: a=VRF18<<32|err b=VTP<<32|err',
    163: 'power on VTP write: a=rc<<32|0x5654 b=VTP value before',
    164: 'power on VRF18 write: a=rc<<32|0x5652 b=VRF value before',
    165: 'power on rails after: a=VRF18<<32|err b=VTP<<32|err',
    166: 'power on reset released: a=dir<<32|din b=mode reg',
    167: 'system reset 0x81: a=err<<32|rx b=second rx',
    168: 'addr check sid0: a=0x4804<<32|err b=0x4808<<32|err',
    169: 'addr check sid0/0x4808: a=val<<32|err b=STA pre<<32|STA after clear',
    170: 'mt6373 read states: a=STA post<<32|STA after clear b=STA pre',
    171: 'spmi master: a=GRP_ID_EN b=MST_REQ_EN',
    172: 'fw ver 0x20000004: a=rx0-3 b=rx4-7',
    201: 'PMIF type3 audit: a=pass<<32|errors b=SEL3/SEL8/EN3/EN8/ID',
    202: 'SALIXP Controller Ready: a=ready b=timeout ms',
    203: 'SALIXP System Info: a=FW<<32|cfg b=signature<<8|type',
    204: 'SALIXP Sense On: a=SPI error b=command',
    205: 'touch cold-supply guard: a=errors b=SEL3/SEL8/EN3/EN8/ID',
    206: 'touch supply field: a=address<<32|error b=read error<<32|value',
    207: 'touch powered-supply guard: a=errors b=SEL3/SEL8/EN3/EN8/ID',
    208: 'touch reset released after supply check: a=error',
    194: 'VTP low-power off: a=VTP en<<8|vsel b="LPMO"',
    195: 'VTP mode write 0x1d23=1: a=err<<32 b="LPDO"',
    196: 'VTP mode after LP off: a=0x1e34<<8|0x1e35 b="MODE"',
    197: 'VTP off before mode change: a=err<<32 b="OFFW"',
    198: 'VTP relock: a=0x142a read<<8|0x1d23 read b="KEYL"',
    199: 'VTP unlock 0x142a=0x5543 (real this time): a=err<<32 b="MODO"',
    200: 'VTP update_bits clear LP: a=old<<8|new b="UPBT"',
    175: 'pad watch: a=seen<<32|samples b=STATUS1',
    176: 'rail vosel before: a=VRF18<<32|err b=VTP<<32|err',
    177: 'rail vosel after: a=VRF18<<32|err b=VTP<<32|err',
    178: 'chip id after rails: a=rx0-3<<32|err b=rx4-7',
    179: 'VTP enable/LP write: a=before<<32|want b=tag 0x5654',
    180: 'rail enable after: a=VRF18<<32|err b=VTP<<32|err',
    181: 'rail vosel final: a=VRF18<<32|err b=VTP<<32|err',
    182: 'VTP disabled for reprogramming: a=rc<<32|before b=0x4f4646',
    183: 'early rail hook entered: b=SPI virtual address',
    184: 'VTP VOSEL write: a=rc<<32|before b=0x5633',
    185: 'VRF18 VOSEL write: a=rc<<32|before b=0x5631',
    186: 'noop write VTP VOSEL: a=rc<<32|value b=0x4e4f4f50',
    187: 'noop write VRF18 VOSEL: a=rc<<32|value b=0x4e4f4f50',
    188: 'noop write VTP EN: a=rc<<32|value b=0x4e4f4f50',
    189: 'noop write VRF18 EN: a=rc<<32|value b=0x4e4f4f50',
    190: 'ramp VRF18 start: a=reg<<32|idx b=0x524d5030',
    191: 'ramp VRF18 done: a=reg<<32|idx b=0x524d5031',
    192: 'ramp VTP start: a=reg<<32|idx b=0x524d5030',
    193: 'ramp VTP done: a=reg<<32|idx b=0x524d5031',
}


DISP_FIELDS = ('stage reached', 'width<<16|height', 'stride', 'clk gate0',
               'clk gate1', 'clk gate2', 'DSI mode', 'DSI PSCTRL',
               'DSI SIZE_CON', 'DSI VACT', 'DSI BUF_CON0', 'DSI INTSTA',
               'OVL_EN', 'OVL_L0_ADDR', 'OVL_L0_PITCH', 'fb phys')


def pull(attempts: int = 45, pause: float = 2.0) -> bytes:
    adb = subprocess.run(['which', 'adb'], capture_output=True, text=True).stdout.strip()
    adb = adb or f'{__import__("os").path.expanduser("~")}/Library/Android/sdk/platform-tools/adb'
    # After a test boot the phone can take a minute to come back, and recovery
    # briefly answers adb before blockdev works. Retry instead of raising on an
    # empty answer: every 0110-0116 run lost its marks that way.
    problem = 'no attempt'
    for _ in range(attempts):
        dev = subprocess.run([adb, 'shell', 'readlink -f /dev/block/by-name/userdata'],
                             capture_output=True, text=True).stdout.strip()
        probe = subprocess.run([adb, 'shell', f'blockdev --getsize64 {dev}'],
                               capture_output=True, text=True)
        size = probe.stdout.strip()
        if dev.startswith('/dev/') and size.isdigit():
            skip = int(size) // 4096 - 1
            out = subprocess.run([adb, 'exec-out',
                                  f'dd if={dev} bs=4096 skip={skip} count=1 2>/dev/null'],
                                 capture_output=True).stdout
            if len(out) == 4096:
                return out
            problem = f'short read: {len(out)} bytes'
        else:
            problem = f'blockdev returned {size!r} for {dev!r}'
        time.sleep(pause)
    raise RuntimeError(f'could not read the mark block: {problem}')


def decode(data: bytes) -> str:
    if len(data) < 4096:
        raise ValueError(f'short read: {len(data)} bytes')
    magic, version, count = struct.unpack_from('<8sII', data, 0)
    if magic != b'SWEETMRK':
        raise ValueError(f'no SWEETMRK record ({magic!r}): no persisted boot marks')
    if version != 1:
        raise ValueError(f'unsupported version {version}')
    if count > 160:
        raise ValueError(f'bad count {count}')
    records = [struct.unpack_from('<IIQQ', data, 16 + i * 24) for i in range(count)]
    build = next((a for code, _pad, a, b in records if code == 99), None)
    lines = [f'# version {version}, {count} marks']
    if build is None:
        lines.append('# No build ID: this may be a stale record from an earlier boot.')
    else:
        lines.append(f'# kernel build ID 0x{build:x}')
    for i, (code, _pad, a, b) in enumerate(records):
        if 70 <= code <= 85:
            field = DISP_FIELDS[code - 70]
            lines.append(f'{i:3d}  {code:3d}  display {field:<28s} = 0x{b:x}')
            continue
        name = NAMES.get(code, f'code {code}')
        if code == 92:
            name = ('display: a=busy skips b=last INTSTA' if build is not None and build >= 0x2302
                    else 'legacy display: a=TE timeouts b=pushes')
        lines.append(f'{i:3d}  {code:3d}  {name:<40s} a=0x{a:x} b=0x{b:x}')
        if code == 201:
            if a == 0xff:
                lines.append('     SPMI initialization failed; no audit reads issued')
            else:
                values = [(b >> (8 * j)) & 0xff for j in range(5)]
                fields = ('ID', 'VRF18_EN', 'VTP_EN', 'VRF18_SEL', 'VTP_SEL')
                lines.append(f'     pass={a >> 32}, errors=0x{a & 0xffffffff:x}, ' +
                             ' '.join(f'{key}=0x{value:02x}'
                                      for key, value in zip(fields, values)))
        if 112 <= code <= 116:
            rx = struct.pack('>II', a, b)
            lines.append('     rx = ' + ' '.join(f'{c:02x}' for c in rx))
        if code in (123, 124):
            idle = (a >> 32) & 0xf
            seen = a & 0xff
            names = ('MI', 'CSB', 'MO', 'CLK')
            parts = []
            for i, label in enumerate(names):
                lo = (seen >> (2 * i)) & 1
                hi = (seen >> (2 * i + 1)) & 1
                parts.append(f'{label}({164 + i})={"toggle" if lo and hi else ("low" if lo else "high")}'
                             if (lo or hi) else f'{label}({164 + i})=?')
            lines.append('     idle(bits MI/CSB/MO/CLK)=%s, %s' %
                         (format(idle, '04b'), ' '.join(parts)))
        if code == 111:
            rx = struct.pack('>II', a >> 32, b >> 32)
            lines.append('     rx = ' + ' '.join(f'{c:02x}' for c in rx) +
                         f', err={a & 0xffffffff}, match={b & 0xffffffff}')
        if code == 91:
            for label, par in (('first', a), ('last', b)):
                if par & 1:
                    lines.append(f'     {label}: translation FAULT (PAR=0x{par:x})')
                else:
                    attr = par >> 56
                    lines.append(f'     {label}: PA page=0x{par & 0x0000fffffffff000:x}, '
                                 f'attributes=0x{attr:02x}' + (' (Normal-NC)' if attr == 0x44 else ''))
    return '\n'.join(lines)


def main() -> int:
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    data = pull() if '--pull' in sys.argv or not args else open(args[0], 'rb').read()
    try:
        print(decode(data))
    except ValueError as e:
        sys.exit(str(e))
    return 0


if __name__ == '__main__':
    sys.exit(main())
