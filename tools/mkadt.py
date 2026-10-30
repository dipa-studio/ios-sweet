#!/usr/bin/env python3
"""Build the minimal Apple Device Tree that the SWEET xnu needs to boot.

Only what the early boot path actually reads (see NOTES.md); every MMIO
address comes from the board's live FDT.
Usage:  mkadt.py OUT.adt [--dump] [--qemu] [--highmem] [--board sweet|a51]
"""
import hashlib, os, struct, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import adt  # noqa: E402

# Kernel-managed RAM: above every Qualcomm XPU carve-out (see NOTES.md)
PHYS_BASE = 0xb0000000
MEM_SIZE = 0x4d000000
# Panic log buffer, carved from the TOP of the dram range and exposed to XNU as
# /pram + /chosen/embedded-panic-log-size. Without it, pe_init.c's
# check_for_panic_log() leaves gPanicBase == 0, debug_log_init() bails out twice
# and the kernel hangs right after "kdp_core zlib memory" — reproduced on QEMU
# and independently on ios-fajita.
PANIC_LOG_SIZE = 0x100000
# --highmem (phone only): the whole upper DDR bank. The live FDT memory node is
# <0x80000000 2G>, <0x1_00000000 0xfcc00000>; every fixed reserved-memory
# carve-out is in the low bank and the dynamic pools are limited below 4G.
HIGH_PHYS_BASE = 0x100000000
HIGH_MEM_SIZE = 0xfcc00000
# /arm-io children are relative to this; it must not be 0 (serial_init bails)
SOC_BASE = 0x01000000

GICD, GICD_SIZE = 0x17a00000, 0x10000
GICR, GICR_SIZE = 0x17a60000, 0x100000
FB, FB_SIZE = 0x9c000000, 0x1700000
SWEET_ECID = 0x5357454554000001  # 'SWEET' + 1, synthetic
FB_W, FB_H, FB_STRIDE = 1080, 2400, 1080 * 4
# Internal UFS host (ufshc@1d84000 "ufs_mem"); QEMU virt has none
UFS, UFS_SIZE = 0x01d84000, 0x3000
TIMEBASE = 19200000
VTIMER_INTID = 19
# QEMU virt (-M virt,gic-version=3 -cpu cortex-a76): GICD/GICR and the generic timer's CNTFRQ
QEMU_GICD, QEMU_GICR, QEMU_TIMEBASE = 0x08000000, 0x080a0000, 62500000
QEMU_VTIMER_INTID = 27

BOOT_MANIFEST_HASH = hashlib.sha384(b'sweet boot manifest').digest()

# Samsung Galaxy A51 (SM-A515F, Exynos 9611), values from its live FDT and
# the shim-a51 probes (NOTES.md "A51 port"). XNU runs on the four Cortex-A73s
# only: the A53s have no 16K granule. RAM is the 4 GiB bank at 0x8_8000_0000
# below Samsung's uH el2_earlymem (0x9_7de0_0000); every Samsung carve-out
# (modem, debug-snapshot, abox, kaslr page, S-Boot's framebuffer) is in the
# low banks. GIC-400 is GICv2: distributor and CPU interface, no redistributors.
A51 = dict(
    phys_base=0x880000000,
    mem_size=0x97de00000 - 0x880000000,
    gicd=(0x12301000, 0x1000),
    gicc=(0x12302000, 0x2000),
    timebase=26000000,
    vtimer_intid=27,
    fb=(0xca000000, 0xa00000),
    fb_geom=(1080, 2400, 1080 * 4),
    # exynos-ufs: HCI, vendor-specific, UNIPRO, UFSP (live FDT order)
    ufs=(0x13520000, 0x200, 0x13521100, 0x200, 0x13510000, 0x8000, 0x13530000, 0x100),
    ecid=0x4135310000000001,  # 'A51' + 1, synthetic
)

# The iOS userland is the iPhone X (iPhone10,3 / D22AP) IPSW. MobileGestalt
# derives product type, device class, home-button-less UI, artwork etc. from
# the root identity and /product of the real D22AP device tree. That tree is
# an Apple artifact (kept out of git): extract it from the IPSW with
#   tools/remotezip.py URL DeviceTree.d22ap.im4p DIR
#   ipsw img4 im4p extract DIR/Firmware/all_flash/DeviceTree.d22ap.im4p -o d22ap.adt
D22AP_ADT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '../research/ipsw-x/d22ap.adt')


def d22ap_product(path=D22AP_ADT):
    """/product properties of the real D22AP tree, without the syscfg
    placeholders iBoot would fill in (flag bit set) and the node bookkeeping."""
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


def build(seed=None, qemu=False, highmem=False, board='sweet'):
    """qemu=True: same tree, but with QEMU virt's GIC addresses and CNTFRQ (tools/qemu-sweet.py)."""
    if board == 'a51':
        return build_a51(seed)
    phys_base, mem_size = (HIGH_PHYS_BASE, HIGH_MEM_SIZE) if highmem else (PHYS_BASE, MEM_SIZE)
    # Carve the panic log off the top so the kernel never allocates over it.
    panic_base = phys_base + mem_size - PANIC_LOG_SIZE
    mem_size -= PANIC_LOG_SIZE
    gicd, gicr, timebase = (QEMU_GICD, QEMU_GICR, QEMU_TIMEBASE) if qemu else (GICD, GICR, TIMEBASE)
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
        ('firmware-version', cstr('sweet-shim')),
        ('system-firmware-version', cstr('sweet-shim')),
        # iBoot's SHA-384 of the boot manifest; /sbin/mount -P 1 exits unless
        # it exists (bind mounts /private/preboot/<hex>/usr/standalone/firmware,
        # tolerating a missing directory). Fixed stand-in value.
        ('boot-manifest-hash', BOOT_MANIFEST_HASH),
        # libimg4 (cryptexd) aborts "failed to get crypto algorithm" without
        # it; real A11+ device trees say sha2-384.
        ('crypto-hash-method', cstr('sha2-384')),
        # MobileGestalt's screen class: display-scale (u32, default 0) comes
        # from /chosen, the pixel size from IOMobileFramebuffer. Scale 0 makes
        # SpringBoard's FBSDisplayMode "infxinf@0x" invalid. 1080x2400 @3x =
        # 360x800 points (like iPhone X class devices).
        ('display-scale', u32(3)),
        # XNU derives IOPlatformUUID (gethostuuid) from these on arm; without
        # them CFPreferences cannot use kCFPreferencesCurrentHost (no ByHost
        # files), so e.g. DataMigration never records LastSystemVersion and
        # migrates on every boot. Synthetic ECID (not the phone's); chip-id
        # of the A11 that the iPhone X userland expects.
        ('unique-chip-id', struct.pack('<Q', SWEET_ECID)),
        ('chip-id', u32(0x8015)),
        # Security status as on a dev-fused, undemoted board (tuple 0,0,1,1):
        # MobileGestalt reads these from /chosen, and mobileactivationd's
        # DeviceType then takes its native "Hactivation" branch (state
        # Activated without an activation record; no SEP, no baseband here).
        ('certificate-production-status', u32(0)),
        ('effective-production-status-ap', u32(0)),
        ('certificate-security-mode', u32(1)),
        ('effective-security-mode-sep', u32(1)),
    ], [node('memory-map', [ph()]),
        # Local boot policy (kern_csr.c): SIP relaxed like `csrutil disable`
        # (lp-sip0: untrusted kexts, unrestricted FS, task_for_pid, kernel
        # debugger, dtrace, nvram), lp-sip1: unauthenticated (unsealed) root.
        # The iOS shared cache is in no trust cache, so dyld can only map it
        # with CSR_ALLOW_UNRESTRICTED_FS (vm_unix.c shared region checks).
        node('asmb', [ph(), ('lp-sip0', u64(0x6f)), ('lp-sip1', u32(1))])])

    # SWEET SMP: all eight cores in physical-core order (0-5 Cortex-A55,
    # 6-7 Cortex-A76), one homogeneous cluster. The kernel defaults to one
    # and uses cpus=N to select an initial prefix (N <= 8).
    # QEMU retains its original single-CPU tree: its MPIDRs differ from sweet.
    cpu_nodes = []
    for core in range(1 if qemu else 8):
        cpu_nodes.append(node(f'cpu{core}', [
            ph(),
            ('device_type', cstr('cpu')),
            ('compatible', cstr('qcom,kryo470') + cstr('ARM,v8')),
            ('reg', u32(core << 8)),  # actual MPIDR Aff1:Aff0, NOT logical ID
            ('cpu-id', u32(core)),   # descriptive: XNU assigns IDs by DT order
            ('cluster-id', u32(0)),  # descriptive; see ml_parse_cpu_topology
            ('cluster-type', u32(0)),  # homogeneous CLUSTER_TYPE_SMP, not AMP
            ('die-cluster-id', u32(0)),
            ('cluster-core-id', u32(core)),
            ('l2-cache-id', u32(core)),  # distinct per-core L2 nodes in live FDT
            ('l3-cache-id', u32(0)),     # shared L3
            ('state', cstr('running' if core == 0 else 'stopped')),
            ('timebase-frequency', u32(timebase)),
            ('clock-frequency', u32(2304000000 if core >= 6 else 1804800000)),
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
        ('virtual-timer-intid', u32(QEMU_VTIMER_INTID if qemu else VTIMER_INTID)),
        ('reg', u64(gicd - SOC_BASE, GICD_SIZE, gicr - SOC_BASE, GICR_SIZE)),
    ])
    arm_io = node('arm-io', [
        ph(),
        ('device_type', cstr('sweet-io')),
        ('compatible', cstr('sweet-io') + cstr('arm-io')),
        ('#address-cells', u32(2)),
        ('#size-cells', u32(2)),
        ('ranges', u64(0, SOC_BASE, 0x100000000 - SOC_BASE)),
    ], [gic,
        # No hardware: watchdogd checks IODeviceTree:/arm-io/wdt for no-pmu and
        # otherwise crashes trying to set the PMU boot stage (customer builds
        # ignore the -wdt_no_pmu boot-arg).
        node('wdt', [ph(), ('no-pmu', u32(1))]),
        # Main display: IOMobileFramebuffer.framework counts /arm-io children
        # with this device_type and reads the canvas size from the node
        # (the presented iPhone X size, see SweetFramebuffer.cpp);
        # the kernel's AppleCLCD matches the compatible string.
        node('disp0', [
            ph(),
            ('device_type', cstr('display-subsystem')),
            ('compatible', cstr('sweet,display')),
            ('canvas-width', u32(1125)),
            ('canvas-height', u32(2436)),
        ])])

    fbcon = node('sweet-fbcon', [
        ph(),
        ('reg', u64(FB, FB_SIZE)),
        ('width', u32(FB_W)),
        ('height', u32(FB_H)),
        ('stride', u32(FB_STRIDE)),
    ])

    # bsd/dev/sweet_ufs.c: the UFS host ABL leaves running (absolute physical reg).
    ufs = node('sweet-ufs', [
        ph(),
        ('compatible', cstr('qcom,ufshc')),
        ('reg', u64(UFS, UFS_SIZE)),
    ])

    # pmap_compute_max_asids requires the node even when no overrides are set.
    # An absent pmap-max-asids property selects XNU's own MAX_ASIDS default.
    # No effaceable storage: keybagd then reads /private/var/keybags/systembag.kb
    # as a plain plist instead of decrypting it with the effaceable key.
    defaults = node('defaults', [ph(), ('no-effaceable-storage', u32(1))])

    # MobileGestalt HomeButtonType = IODeviceTree:/buttons home-button-type
    # (D22AP: 2, no Home button; absent = 0 = Home-button device).
    buttons = node('buttons', [
        ph(),
        ('button-names', cstr('volup') + cstr('voldown') + cstr('hold')),
        ('home-button-type', u32(2)),
        ('opposed-power-vol-buttons', u32(1)),
    ])

    product_props = d22ap_product()
    product = [node('product', [ph()] + product_props)] if product_props else []

    # Panic log region. /pram reg = <phys size>; it sits just above the
    # dram-size we expose, so XNU maps it but never allocates into it.
    pram = node('pram', [ph(), ('reg', u64(panic_base) + u64(PANIC_LOG_SIZE))])

    # Identity of the iPhone X whose userland runs here: compatible[0] is
    # hw.model/hw.target (D22AP), model is hw.machine/hw.product
    # (iPhone10,3). 'xiaomi,sweet' stays for SweetPlatformExpert matching.
    return node('device-tree', [
        ph(),
        ('compatible', cstr('D22AP') + cstr('iPhone10,3') + cstr('xiaomi,sweet') + cstr('qcom,sm7150') + cstr('AppleARM')),
        ('model', cstr('iPhone10,3')),
        ('target-type', cstr('D22')),
        ('target-sub-type', cstr('D22AP')),
        ('manufacturer', cstr('Apple Inc.')),
        ('#address-cells', u32(2)),
        ('#size-cells', u32(2)),
    ], [chosen, defaults, cpus, arm_io, fbcon, buttons, pram] + product + ([] if qemu else [ufs]))


def build_a51(seed=None):
    """The same tree as sweet's with the A51's memory, GICv2, A73 cpus,
    framebuffer and UFS. Properties without a comment mean what they mean in
    build() above."""
    b = A51
    phys_base = b['phys_base']
    mem_size = b['mem_size']
    panic_base = phys_base + mem_size - PANIC_LOG_SIZE
    mem_size -= PANIC_LOG_SIZE
    seed = seed if seed is not None else os.urandom(64)

    # Start from sweet's tree so the identity, /chosen security status,
    # /defaults, /buttons, /pram layout and /product stay in one place.
    root = build(seed=seed, highmem=True)
    # New nodes continue sweet's phandle numbering (no duplicates).
    def max_ph(n):
        own = [struct.unpack('<I', v)[0] for k, f, v in n.props if k == 'AAPL,phandle']
        return max(own + [max_ph(c) for c in n.children] + [0])
    phandle = iter(range(max_ph(root) + 1, 100000))
    ph = lambda: ('AAPL,phandle', u32(next(phandle)))
    kids = {dict((k, v) for k, f, v in c.props)['name'].rstrip(b'\0').decode(): c for c in root.children}

    chosen = kids['chosen']
    def setp(n, key, val):
        for i, (k, f, v) in enumerate(n.props):
            if k == key:
                n.props[i] = (k, f, val)
                return
        n.props.append((key, 0, val))
    setp(chosen, 'dram-base', u64(phys_base))
    setp(chosen, 'dram-size', u64(mem_size))
    setp(chosen, 'firmware-version', cstr('a51-shim'))
    setp(chosen, 'system-firmware-version', cstr('a51-shim'))
    setp(chosen, 'unique-chip-id', struct.pack('<Q', b['ecid']))
    setp(kids['pram'], 'reg', u64(panic_base) + u64(PANIC_LOG_SIZE))

    # cpu0..3 = cpu4..7 of Linux: Cortex-A73, MPIDR Aff1 1 (cluster 1). The
    # shim starts XNU on 0x100; the A53 cluster is never handed to XNU.
    cpu_nodes = []
    for core in range(4):
        cpu_nodes.append(node(f'cpu{core}', [
            ph(),
            ('device_type', cstr('cpu')),
            ('compatible', cstr('arm,cortex-a73') + cstr('ARM,v8')),
            ('reg', u32(0x100 | core)),  # MPIDR Aff1:Aff0
            ('cpu-id', u32(core)),
            ('cluster-id', u32(0)),
            ('cluster-type', u32(0)),
            ('die-cluster-id', u32(0)),
            ('cluster-core-id', u32(core)),
            ('l2-cache-id', u32(0)),     # one shared L2 per A73 cluster
            ('state', cstr('running' if core == 0 else 'stopped')),
            ('timebase-frequency', u32(b['timebase'])),
            ('clock-frequency', u32(2314000000)),
            ('bus-frequency', u32(100000000)),
            ('memory-frequency', u32(1794000000)),
            ('peripheral-frequency', u32(b['timebase'])),
            ('fixed-frequency', u32(b['timebase'])),
        ]))
    cpus = node('cpus', [ph(), ('#address-cells', u32(1)), ('#size-cells', u32(0))], cpu_nodes)

    gicd, gicd_size = b['gicd']
    gicc, gicc_size = b['gicc']
    gic = node('gic', [
        ph(),
        ('compatible', cstr('arm,gic-400') + cstr('arm,cortex-a15-gic')),
        ('interrupt-controller', b''),
        ('virtual-timer-intid', u32(b['vtimer_intid'])),
        # GICv2: <GICD size GICC size>, relative to SOC_BASE like sweet's
        ('reg', u64(gicd - SOC_BASE, gicd_size, gicc - SOC_BASE, gicc_size)),
    ])
    arm_io = kids['arm-io']
    arm_io.children = [gic if dict((k, v) for k, f, v in c.props)['name'] == b'gic\0' else c
                       for c in arm_io.children]
    setp(arm_io, 'device_type', cstr('a51-io'))
    setp(arm_io, 'compatible', cstr('a51-io') + cstr('sweet-io') + cstr('arm-io'))

    fb, fb_size = b['fb']
    w, h, stride = b['fb_geom']
    fbcon = node('sweet-fbcon', [ph(), ('reg', u64(fb, fb_size)), ('width', u32(w)),
                                 ('height', u32(h)), ('stride', u32(stride))])
    ufs = node('sweet-ufs', [ph(), ('compatible', cstr('samsung,exynos-ufs')), ('reg', u64(*b['ufs']))])

    root.children = [cpus if c is kids['cpus'] else fbcon if c is kids['sweet-fbcon'] else
                     ufs if c is kids.get('sweet-ufs') else c for c in root.children]
    # 'xiaomi,sweet' stays so SweetPlatformExpert still matches; the board is
    # told apart by 'samsung,a51'.
    setp(root, 'compatible', cstr('D22AP') + cstr('iPhone10,3') + cstr('samsung,a51') +
         cstr('xiaomi,sweet') + cstr('samsung,exynos9611') + cstr('AppleARM'))
    return root


if __name__ == '__main__':
    board = sys.argv[sys.argv.index('--board') + 1] if '--board' in sys.argv else 'sweet'
    root = build(qemu='--qemu' in sys.argv, highmem='--highmem' in sys.argv, board=board)
    blob = adt.serialize(root)
    open(sys.argv[1], 'wb').write(blob)
    if '--dump' in sys.argv:
        adt.dump(adt.parse(blob)[0])
    print(f'{sys.argv[1]}: {len(blob)} bytes', file=sys.stderr)
