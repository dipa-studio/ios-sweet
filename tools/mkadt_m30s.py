#!/usr/bin/env python3
"""Build the minimal Apple Device Tree that the M30s xnu needs to boot.

Only what the early boot path actually reads; every MMIO address comes from
the Exynos 9610 base DTS + M30s overlay DTB.
Usage:  mkadt_m30s.py OUT.adt [--dump] [--qemu] [--highmem]
"""
import hashlib, os, struct, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import adt  # noqa: E402

# Kernel-managed RAM: Exynos 9611 has 3x 2GB banks (6GB total)
# Bank 0: 0x80000000 - 0x100000000 (2GB)
# Bank 1: 0x880000000 - 0x900000000 (2GB)
# Bank 2: 0x900000000 - 0x980000000 (2GB)
# We'll expose bank 0 as the primary kernel RAM (2GB)
# and add the upper banks as additional memory regions
PHYS_BASE = 0x80000000
MEM_SIZE = 0x80000000  # 2GB primary bank

# Panic log buffer, carved from the TOP of the dram range
PANIC_LOG_SIZE = 0x100000  # 1 MB

# --highmem (phone only): use all 6GB
HIGH_PHYS_BASE = 0x80000000
HIGH_MEM_SIZE = 0x180000000  # 6GB total

# SOC base for /arm-io children
SOC_BASE = 0x01000000

# GICv3 registers (from Exynos 9610 DTS)
GICD, GICD_SIZE = 0x12301000, 0x1000
GICR, GICR_SIZE = 0x12302000, 0x200000

# Framebuffer (S-Boot splash, continuous) - phys addr from live FDT
# Will be patched at runtime from the live FDT
FB, FB_SIZE = 0x0, 0x0
FB_W, FB_H, FB_STRIDE = 1080, 2340, 1080 * 4

# Synthetic ECID for IOPlatformUUID
M30S_ECID = 0x4d33307300000001  # 'M30S' + 1

# UFS host controller
UFS, UFS_SIZE = 0x13520000, 0x10000

# Generic timer frequency: Exynos 9611 = 26 MHz
TIMEBASE = 26000000
VTIMER_INTID = 13  # PPI 13 (CNTV)

# QEMU virt (for testing)
QEMU_GICD, QEMU_GICR, QEMU_TIMEBASE = 0x08000000, 0x080a0000, 62500000
QEMU_VTIMER_INTID = 27

BOOT_MANIFEST_HASH = hashlib.sha384(b'm30s boot manifest').digest()

# The iOS userland is the iPhone X (iPhone10,3 / D22AP) IPSW
D22AP_ADT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '../research/ipsw-x/d22ap.adt')


def d22ap_product(path=D22AP_ADT):
    """/product properties of the real D22AP tree."""
    if not os.path.exists(path):
        print(f'warning: {path} missing, no /product node', file=sys.stderr)
        return None
    root, _ = adt.parse(open(path, 'rb').read())
    for c in root.children:
        if dict((k, v) for k, f, v in c.props).get('name') == b'product\0':
            return [(k, v) for k, f, v in c.props if not f and k not in ('name', 'AAPL,phandle')]
    raise SystemExit(f'{path}: no /product node')


u32 = lambda *v: struct.pack('<%dI' % len(v), *v)
u64 = lambda *v: struct.pack('<%dQ' % len(v), *v)
cstr = lambda s: s.encode() + b'\0'


def node(name, props=(), children=()):
    n = adt.Node()
    n.props = [('name', 0, cstr(name))] + [(k, 0, v) for k, v in props]
    n.children = list(children)
    return n


def build(seed=None, qemu=False, highmem=False):
    """qemu=True: same tree, but with QEMU virt's GIC addresses and CNTFRQ."""
    phys_base, mem_size = (HIGH_PHYS_BASE, HIGH_MEM_SIZE) if highmem else (PHYS_BASE, MEM_SIZE)
    # Carve the panic log off the top
    panic_base = phys_base + mem_size - PANIC_LOG_SIZE
    mem_size -= PANIC_LOG_SIZE
    gicd, gicr, timebase = (QEMU_GICD, QEMU_GICR, QEMU_TIMEBASE) if qemu else (GICD, GICR, TIMEBASE)
    vtimer_intid = QEMU_VTIMER_INTID if qemu else VTIMER_INTID
    seed = seed if seed is not None else os.urandom(64)
    phandle = iter(range(1, 1000))
    ph = lambda: ('AAPL,phandle', u32(next(phandle)))

    chosen = node('chosen', [
        ph(),
        ('dram-base', u64(phys_base)),
        ('dram-size', u64(mem_size)),
        ('random-seed', seed),
        ('debug-enabled', u32(1)),
        ('embedded-panic-log-size', u32(PANIC_LOG_SIZE)),
        ('firmware-version', cstr('m30s-shim')),
        ('system-firmware-version', cstr('m30s-shim')),
        ('boot-manifest-hash', BOOT_MANIFEST_HASH),
        ('crypto-hash-method', cstr('sha2-384')),
        # MobileGestalt's screen class: 1080x2340 @3x = 360x780 points
        ('display-scale', u32(3)),
        # IOPlatformUUID from unique-chip-id + chip-id
        ('unique-chip-id', struct.pack('<Q', M30S_ECID)),
        ('chip-id', u32(0x8015)),  # A11 chip-id for iPhone X
        # Security status for Hactivation
        ('certificate-production-status', u32(0)),
        ('effective-production-status-ap', u32(0)),
        ('certificate-security-mode', u32(1)),
        ('effective-security-mode-sep', u32(1)),
    ], [node('memory-map', [ph()]),
        node('asmb', [ph(), ('lp-sip0', u64(0x6f)), ('lp-sip1', u32(1))])])

    # M30s SMP: 8 cores (4x Cortex-A53 little + 4x Cortex-A73 big)
    # MPIDR format: Aff1=cluster (0=little, 1=big), Aff0=core
    cpu_nodes = []
    # Little cluster (Cortex-A53): cores 0-3, Aff1=0, Aff0=0..3
    for core in range(4):
        cpu_nodes.append(node(f'cpu{core}', [
            ph(),
            ('device_type', cstr('cpu')),
            ('compatible', cstr('arm,cortex-a53') + cstr('ARM,v8')),
            ('reg', u32(core)),  # MPIDR Aff1:Aff0 = 0:core
            ('cpu-id', u32(core)),
            ('cluster-id', u32(0)),
            ('cluster-type', u32(0)),  # homogeneous SMP
            ('die-cluster-id', u32(0)),
            ('cluster-core-id', u32(core)),
            ('l2-cache-id', u32(core)),
            ('l3-cache-id', u32(0)),
            ('state', cstr('running' if core == 0 else 'stopped')),
            ('timebase-frequency', u32(timebase)),
            ('clock-frequency', u32(1600000000)),  # 1.6 GHz A53
            ('bus-frequency', u32(100000000)),
            ('memory-frequency', u32(1866000000)),
            ('peripheral-frequency', u32(timebase)),
            ('fixed-frequency', u32(timebase)),
        ]))
    # Big cluster (Cortex-A73): cores 4-7, Aff1=1, Aff0=0..3
    for core in range(4):
        cpu_nodes.append(node(f'cpu{core + 4}', [
            ph(),
            ('device_type', cstr('cpu')),
            ('compatible', cstr('arm,cortex-a73') + cstr('ARM,v8')),
            ('reg', u32(0x100 | core)),  # MPIDR Aff1:Aff0 = 1:core
            ('cpu-id', u32(core + 4)),
            ('cluster-id', u32(1)),
            ('cluster-type', u32(0)),
            ('die-cluster-id', u32(0)),
            ('cluster-core-id', u32(core)),
            ('l2-cache-id', u32(core)),
            ('l3-cache-id', u32(1)),
            ('state', cstr('stopped')),
            ('timebase-frequency', u32(timebase)),
            ('clock-frequency', u32(2300000000)),  # 2.3 GHz A73
            ('bus-frequency', u32(100000000)),
            ('memory-frequency', u32(1866000000)),
            ('peripheral-frequency', u32(timebase)),
            ('fixed-frequency', u32(timebase)),
        ]))
    cpus = node('cpus', [ph(), ('#address-cells', u32(1)),
                         ('#size-cells', u32(0))], cpu_nodes)

    gic = node('gic', [
        ph(),
        ('compatible', cstr('arm,gic-v3')),
        ('interrupt-controller', b''),
        ('virtual-timer-intid', u32(vtimer_intid)),
        ('reg', u64(gicd - SOC_BASE, GICD_SIZE, gicr - SOC_BASE, GICR_SIZE)),
    ])

    # DECON display controller
    decon = node('decon', [
        ph(),
        ('compatible', cstr('samsung,exynos-decon') + cstr('samsung,exynos9610-decon')),
        ('reg', u64(0x148B0000 - SOC_BASE, 0x10000)),
        ('interrupts', u32(0, 155, 4)),  # GIC SPI 155
        ('clocks', u32(0x2, 0x2e)),  # from clock controller
        ('clock-names', cstr('gate')),
        ('status', cstr('okay')),
    ])

    # DSIM (MIPI DSI)
    dsim = node('dsim', [
        ph(),
        ('compatible', cstr('samsung,exynos-dsim') + cstr('samsung,exynos9610-dsim')),
        ('reg', u64(0x148E0000 - SOC_BASE, 0x10000)),
        ('interrupts', u32(0, 156, 4)),  # GIC SPI 156
        ('clocks', u32(0x2, 0x2f)),
        ('clock-names', cstr('gate')),
        ('status', cstr('okay')),
        # Panel info from M30s overlay
        ('panel', [
            ph(),
            ('compatible', cstr('samsung,ea8076')),
            ('mode', u32(2)),
            ('resolution', u32(1080, 2340)),
            ('size', u32(68, 147)),  # mm
            ('timing,refresh', u32(60)),
            ('timing,h-porch', u32(2, 2, 2)),
            ('timing,v-porch', u32(15, 3, 1)),
            ('timing,dsi-hs-clk', u32(1200)),
            ('timing,pmsk', u32(3, 0x115, 1, 0)),
            ('timing,dsi-escape-clk', u32(16)),
            ('data-lane', u32(4)),
            ('dsc-en', u32(0)),
        ]),
    ])

    # UFS host controller
    ufs = node('ufs', [
        ph(),
        ('compatible', cstr('samsung,exynos-ufshc') + cstr('samsung,exynos9610-ufshc')),
        ('reg', u64(UFS - SOC_BASE, UFS_SIZE)),
        ('interrupts', u32(0, 0x1cc, 4)),  # GIC SPI 460
        ('clocks', u32(0x2, 0x106)),
        ('clock-names', cstr('gate')),
        ('status', cstr('okay')),
        # PHY
        ('phy', [
            ph(),
            ('compatible', cstr('samsung,exynos-ufs-phy')),
            ('reg', u64(0x13500000 - SOC_BASE, 0x10000)),
            ('status', cstr('okay')),
        ]),
    ])

    arm_io = node('arm-io', [
        ph(),
        ('device_type', cstr('m30s-io')),
        ('compatible', cstr('m30s-io') + cstr('arm-io')),
        ('#address-cells', u32(2)),
        ('#size-cells', u32(2)),
        ('ranges', u64(0, SOC_BASE, 0x100000000 - SOC_BASE)),
    ], [gic, decon, dsim, ufs])

    # Framebuffer console (S-Boot splash)
    fbcon = node('m30s-fbcon', [
        ph(),
        ('reg', u64(FB, FB_SIZE)),
        ('width', u32(FB_W)),
        ('height', u32(FB_H)),
        ('stride', u32(FB_STRIDE)),
    ])

    # GPIO keys (Power, Volume Up/Down)
    buttons = node('buttons', [
        ph(),
        ('button-names', cstr('volup') + cstr('voldown') + cstr('hold')),
        ('home-button-type', u32(2)),  # No home button (Face ID class)
        ('opposed-power-vol-buttons', u32(1)),
        ('power-key', [
            ph(),
            ('label', cstr('KEY_POWER')),
            ('linux,code', u32(0x74)),
            ('gpio', u32(0x7, 0xf)),  # gpm7-15
            ('gpio-key,wakeup', u32(1)),
        ]),
        ('volume-up-key', [
            ph(),
            ('label', cstr('KEY_VOLUMEUP')),
            ('linux,code', u32(0x73)),
            ('gpio', u32(0x5, 0xf)),  # gpm5-15
        ]),
        ('volume-down-key', [
            ph(),
            ('label', cstr('KEY_VOLUMEDOWN')),
            ('linux,code', u32(0x72)),
            ('gpio', u32(0x6, 0xf)),  # gpm6-15
        ]),
    ])

    # HSI2C touch controller (Melfas MSS100)
    hsi2c4 = node('hsi2c4', [
        ph(),
        ('compatible', cstr('samsung,exynos5-hsi2c')),
        ('reg', u64(0x13870000 - SOC_BASE, 0x1000)),
        ('interrupts', u32(0, 0x75, 4)),  # GIC SPI 117
        ('clocks', u32(0x2, 0x259, 0x2, 0x25d)),
        ('clock-names', cstr('ipclk_hsi2c') + cstr('gate_hsi2c_clk')),
        ('samsung,scl-clk-stretching', b''),
        ('samsung,usi-i2c-v2', b''),
        ('#address-cells', u32(1)),
        ('#size-cells', u32(0)),
        ('status', cstr('okay')),
        # Touch controller
        ('mms_ts@48', [
            ph(),
            ('compatible', cstr('melfas,mms_ts')),
            ('reg', u32(0x48)),
            ('melfas,vdd-en', cstr('tsp_ldo_en')),
            ('melfas,irq-gpio', u32(0x0, 0x0, 0x0)),  # gph0-0
            ('melfas,scl-gpio', u32(0x0, 0x1, 0x0)),
            ('melfas,sda-gpio', u32(0x0, 0x0, 0x0)),
            ('melfas,area-size', u32(0x85, 0x10a, 0x155)),
            ('melfas,max-x-y', u32(0xfff, 0xfff)),
            ('melfas,node-info', u32(0xf, 0x20, 0x0)),
            ('melfas,event-info', u32(0x8, 0xc)),
            ('melfas,support-lpm', cstr('true')),
            ('melfas,fw-name', cstr('tsp_melfas/mss100_m30s.fw')),
            ('status', cstr('okay')),
        ]),
    ])

    # S2MPU09 PMIC (via Speedy/I2C)
    speedy = node('speedy', [
        ph(),
        ('compatible', cstr('samsung,exynos-speedy')),
        ('reg', u64(0x11A10000 - SOC_BASE, 0x2000)),
        ('interrupts', u32(0, 0x25, 4)),
        ('#address-cells', u32(1)),
        ('#size-cells', u32(0)),
        ('status', cstr('okay')),
        ('s2mpu09@0', [
            ph(),
            ('compatible', cstr('samsung,s2mpu09')),
            ('reg', u32(0x0)),
            ('interrupts', u32(0, 0x0, 0x0)),
            ('interrupt-parent', u32(0x1)),  # GIC
            ('s2mpu09,wakeup', cstr('enabled')),
            ('s2mpu09,irq-gpio', u32(0x0, 0x0, 0x0)),  # gph0-0
            # Regulators (from M30s overlay)
            ('regulators', [
                ph(),
                ('BUCK1', [ph(), ('regulator-name', cstr('vdd_mif')), ('regulator-min-microvolt', u32(0x7a120)), ('regulator-max-microvolt', u32(0x10c8e0)), ('regulator-always-on', b'')]),
                ('BUCK2', [ph(), ('regulator-name', cstr('vdd_cpucl1')), ('regulator-min-microvolt', u32(0x7a120)), ('regulator-max-microvolt', u32(0x13d620)), ('regulator-always-on', b'')]),
                ('BUCK3', [ph(), ('regulator-name', cstr('vdd_cpucl0')), ('regulator-min-microvolt', u32(0x7a120)), ('regulator-max-microvolt', u32(0x13d620)), ('regulator-always-on', b'')]),
                ('BUCK4', [ph(), ('regulator-name', cstr('vdd_int')), ('regulator-min-microvolt', u32(0x7a120)), ('regulator-max-microvolt', u32(0x10c8e0)), ('regulator-always-on', b'')]),
                ('BUCK5', [ph(), ('regulator-name', cstr('vdd_g3d')), ('regulator-min-microvolt', u32(0x7a120)), ('regulator-max-microvolt', u32(0x124f80)), ('regulator-always-on', b'')]),
                ('BUCK6', [ph(), ('regulator-name', cstr('vdd_cam_vipx')), ('regulator-min-microvolt', u32(0x7a120)), ('regulator-max-microvolt', u32(0x13d620)), ('regulator-always-on', b'')]),
                ('BUCK7', [ph(), ('regulator-name', cstr('vdd2_mem')), ('regulator-min-microvolt', u32(0x7a120)), ('regulator-max-microvolt', u32(0x13d620)), ('regulator-always-on', b'')]),
                ('BUCK8', [ph(), ('regulator-name', cstr('vdd_lldo')), ('regulator-min-microvolt', u32(0x124f80)), ('regulator-max-microvolt', u32(0x16e360)), ('regulator-always-on', b'')]),
                ('BUCK9', [ph(), ('regulator-name', cstr('vdd_mldo')), ('regulator-min-microvolt', u32(0x1b7740)), ('regulator-max-microvolt', u32(0x200b20)), ('regulator-always-on', b'')]),
                ('LDO1', [ph(), ('regulator-name', cstr('vdd_ldo1')), ('regulator-min-microvolt', u32(0xaae60)), ('regulator-max-microvolt', u32(0x13d620)), ('regulator-always-on', b'')]),
                ('LDO2', [ph(), ('regulator-name', cstr('vqmmc')), ('regulator-min-microvolt', u32(0x1b7740)), ('regulator-max-microvolt', u32(0x337f98))]),
                ('LDO11', [ph(), ('regulator-name', cstr('vdd_ldo11')), ('regulator-min-microvolt', u32(0x7a120)), ('regulator-max-microvolt', u32(0x13d620)), ('regulator-always-on', b'')]),
                ('LDO33', [ph(), ('regulator-name', cstr('vdd_ldo33')), ('regulator-min-microvolt', u32(0xc3500)), ('regulator-max-microvolt', u32(0x1dc130))]),
                ('LDO34', [ph(), ('regulator-name', cstr('vdd_ldo34')), ('regulator-min-microvolt', u32(0x1b7740)), ('regulator-max-microvolt', u32(0x337f98))]),
                ('LDO35', [ph(), ('regulator-name', cstr('vmmc')), ('regulator-min-microvolt', u32(0x1b7740)), ('regulator-max-microvolt', u32(0x337f98))]),
                ('LDO40', [ph(), ('regulator-name', cstr('regulator_3v3')), ('regulator-min-microvolt', u32(0x325aa0)), ('regulator-max-microvolt', u32(0x325aa0)), ('regulator-boot-on', b'')]),
                ('LDO42', [ph(), ('regulator-name', cstr('regulator_1v8')), ('regulator-min-microvolt', u32(0x1b7740)), ('regulator-max-microvolt', u32(0x1b7740)), ('regulator-ramp-delay', u32(0x2ee0)), ('regulator-boot-on', b'')]),
            ]),
        ]),
    ])

    # Battery (SM5713 fuel gauge via S2MPU09)
    battery = node('battery', [
        ph(),
        ('compatible', cstr('samsung,sec-battery')),
        ('status', cstr('okay')),
        ('battery,vendor', cstr('Battery')),
        ('battery,charger-name', cstr('sm5713-charger')),
        ('battery,fuelgauge-name', cstr('sm5713-fuelgauge')),
        ('battery,technology', u32(2)),  # Li-ion
        ('battery,chip-vendor', cstr('LSI')),
        ('battery,temp-adc-type', u32(1)),
        ('battery,temp-check-type', u32(2)),
        ('battery,chg-temp-check-type', u32(2)),
        ('battery,thermal-source', u32(3)),
        ('battery,polling-time', u32(10, 30, 30, 30, 3600)),
        # Voltage/temp tables from M30s overlay
        ('battery,temp-table-adc', u32(0x132, 0x190, 0x22b, 0x287, 0x2f3, 0x370, 0x3fe, 0x49e, 0x54e, 0x60f, 0x6ea, 0x7d1, 0x8bf, 0x9af, 0xa91, 0xb5f, 0xc27, 0xccd, 0xd55, 0xdd8, 0xe16)),
        ('battery,temp-table-data', u32(0x384, 0x320, 0x2bc, 0x28a, 0x258, 0x226, 0x1f4, 0x1c2, 0x190, 0x15e, 0x12c, 0xfa, 0xc8, 0x96, 0x64, 0x32, 0x0, 0xffffffce, 0xffffff9c, 0xffffff6a, 0xffffff38)),
    ])

    # Defaults
    defaults = node('defaults', [ph(), ('no-effaceable-storage', u32(1))])

    # Panic log region
    pram = node('pram', [ph(), ('reg', u64(panic_base) + u64(PANIC_LOG_SIZE))])

    # Product node from real D22AP
    product_props = d22ap_product()
    product = [node('product', [ph()] + product_props)] if product_props else []

    # Device tree root
    return node('device-tree', [
        ph(),
        ('compatible', cstr('D22AP') + cstr('iPhone10,3') + cstr('samsung,m30s') + cstr('samsung,exynos9611') + cstr('AppleARM')),
        ('model', cstr('iPhone10,3')),
        ('target-type', cstr('D22')),
        ('target-sub-type', cstr('D22AP')),
        ('manufacturer', cstr('Apple Inc.')),
        ('#address-cells', u32(2)),
        ('#size-cells', u32(2)),
    ], [chosen, defaults, cpus, arm_io, fbcon, buttons, hsi2c4, speedy, battery, pram] + product)


if __name__ == '__main__':
    root = build(qemu='--qemu' in sys.argv, highmem='--highmem' in sys.argv)
    blob = adt.serialize(root)
    open(sys.argv[1], 'wb').write(blob)
    if '--dump' in sys.argv:
        adt.dump(adt.parse(blob)[0])
    print(f'{sys.argv[1]}: {len(blob)} bytes', file=sys.stderr)