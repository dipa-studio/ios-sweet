#!/usr/bin/env python3
"""Rewrite the framebuffer constants in xnu/patches/ for the Xiaomi Mi 8 (run by CI before the patches are applied).

  patch-board.py xnu/patches

Only the early-boot framebuffer code (0010/0012) and the presented-display crop (0061) hardcode the sweet panel.
Everything after that reads geometry from the ADT / boot_args (set by mkadt.py --board mi8 and the shim).

Mi 8: ABL splash buffer 0x9d400000, 1080x2248, stride 4320. The bootstrap mapping is one 16K-granule L2 block (32 MB,
must be 32 MB aligned): it stays at 0x9c000000 and covers 0x9c000000..0x9dffffff, so the buffer sits 0x1400000 into
the block. Edits keep every patch hunk the same length, and the 0010 additions and the 0012 lines that remove/rewrite
them are changed together so the series still applies in order.
"""
import os, sys

FB, FB_H, MARK_ROW, BLOCK_OFF = '0x9d400000', 2248, 2248 - 32, '0x1400000'

EDITS = {
    '0010-sweet-early-framebuffer-debug.patch': [
        ('MOV64\tx0, (0x9c000000 + 2368 * 4320)', f'MOV64\tx0, ({FB} + {MARK_ROW} * 4320)'),
        ('#define EARLY_FB ((volatile uint32_t *)(uintptr_t)0x9c000000)',
         f'#define EARLY_FB ((volatile uint32_t *)(uintptr_t){FB})'),
        ('#define EARLY_HEIGHT 2400u', f'#define EARLY_HEIGHT {FB_H}u'),
    ],
    '0012-sweet-keep-debug-console-after-ttbr0.patch': [
        ('#define EARLY_FB ((volatile uint32_t *)(uintptr_t)0x9c000000)',
         f'#define EARLY_FB ((volatile uint32_t *)(uintptr_t){FB})'),
        ('static volatile uint32_t *early_fb = (volatile uint32_t *)(uintptr_t)0x9c000000;',
         f'static volatile uint32_t *early_fb = (volatile uint32_t *)(uintptr_t){FB};'),
        ('#define EARLY_HEIGHT 2400u', f'#define EARLY_HEIGHT {FB_H}u'),
        ('early_fb = (volatile uint32_t *)(uintptr_t)base;',
         f'early_fb = (volatile uint32_t *)(uintptr_t)(base + {BLOCK_OFF});'),
    ],
    '0061-sweet-iphone-x-display-size.patch': [
        ('fLogicalH = native ? 2400 : 2436;', f'fLogicalH = native ? {FB_H} : 2436;'),
        ('fOffY = (fLogicalH - 2400) / 2;', f'fOffY = (fLogicalH - {FB_H}) / 2;'),
    ],
    '0071-sweet-touch-edge.patch': [
        ('y > 2399 - SWEET_TOUCH_EDGE_PX', f'y > {FB_H - 1} - SWEET_TOUCH_EDGE_PX'),
    ],
}


# bsd/conf/files lists sweet_touch.c (added by 0060, context in 0062 and 0072): point it at the Mi 8 touch driver instead.
FILES_LINE = ('bsd/dev/sweet_touch.c\t\t\tstandard', 'bsd/dev/mi8_touch.c\t\t\tstandard')
FILES_PATCHES = ['0060-sweet-keys-touch-drivers.patch', '0062-sweet-touch-power-battery.patch',
                 '0072-sweet-usb-probe.patch']
NEW_PATCH = '0099-mi8-fts-touch.patch'		# creates bsd/dev/mi8_touch.c (source in mi8/xnu/mi8_touch.c)


def swap_touch_driver(d):
    old, new = FILES_LINE
    for name in FILES_PATCHES:
        path = os.path.join(d, name)
        s = open(path).read()
        if s.count(old) == 1:
            s = s.replace(old, new)
            open(path, 'w').write(s)
            print(f'{name}: conf/files now builds mi8_touch.c')
        elif s.count(new) == 1 and s.count(old) == 0:
            print(f'{name}: conf/files already points at mi8_touch.c')
        else:
            sys.exit(f'{name}: expected exactly one {old!r} (found {s.count(old)})')
    src = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'xnu', NEW_PATCH)
    dst = os.path.join(d, NEW_PATCH)
    open(dst, 'wb').write(open(src, 'rb').read())
    print(f'{NEW_PATCH}: copied into {d}')


def main(d):
    for name, edits in EDITS.items():
        path = os.path.join(d, name)
        s = open(path).read()
        for old, new in edits:
            if s.count(old) == 1:
                s = s.replace(old, new)
            elif s.count(new) == 1 and s.count(old) == 0:
                print(f'{name}: already applied: {new[:60]}')
            else:
                sys.exit(f'{name}: expected exactly one match for: {old!r} (found {s.count(old)})')
        open(path, 'w').write(s)
        print(f'{name}: {len(edits)} edits')
    swap_touch_driver(d)
    # The 0010 additions and the 0012 lines that remove them must stay in sync.
    a = open(os.path.join(d, '0010-sweet-early-framebuffer-debug.patch')).read()
    b = open(os.path.join(d, '0012-sweet-keep-debug-console-after-ttbr0.patch')).read()
    for line in ('#define EARLY_FB ((volatile uint32_t *)(uintptr_t)' + FB + ')', '#define EARLY_HEIGHT ' + str(FB_H) + 'u'):
        assert line in a and line in b, line


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else 'xnu/patches')
