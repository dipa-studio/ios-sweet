/*
 * SM-A510F (a5xelte, Exynos 7580) feasibility probe.
 *
 * Answers, on the real phone, the hardware questions that decide whether an
 * XNU port is worth starting, and shows the answers as rows of bits on the
 * screen (one row per value, see a510f/README.md for how to read them).
 *
 * Timeline after S-Boot jumps here:
 *   - read CPU ID registers, ask the firmware for its PSCI version,
 *   - start a second core with PSCI CPU_ON; it acts as a watchdog,
 *   - find the framebuffer S-Boot left programmed in DECON and draw rows,
 *   - power off: ~60 s after drawing, ~15 s if no framebuffer was found,
 *     or ~75 s via the watchdog core if the primary core hung.
 * The power-off time is the fallback signal when nothing appears on screen.
 *
 * Addresses come from the LineageOS exynos7580-common kernel (lineage-15.1):
 * DECON at 0x14830000 (drivers/video/exynos/decon_7580/regs-decon.h),
 * PMU at 0x10460000 with PS_HOLD_CONTROL at +0x330C, PSCI via smc.
 */
#include <stdint.h>

typedef uint8_t u8;
typedef uint16_t u16;
typedef uint32_t u32;
typedef uint64_t u64;

#define DECON_BASE		0x14830000UL
#define DECON_WINCON(w)		(0x0050 + (w) * 4)
#define DECON_WHOLE_X(w)	(0x0130 + (w) * 8)
#define DECON_OSD_B(w)		(0x0234 + (w) * 0x20)
#define DECON_ADD0(w)		(0x0880 + (w) * 0x10)
#define DECON_TRIGCON		0x06B0
#define TRIG_SWTRIGEN		(1u << 0)
#define TRIG_SWTRIGCMD		(1u << 1)
#define TRIG_HWTRIGEN		(1u << 3)
#define TRIG_HWTRIGMASK		(1u << 4)

#define PMU_PS_HOLD_CONTROL	0x1046330CUL
#define PS_HOLD_OUTPUT_HIGH	(1u << 8)

#define PSCI_VERSION		0x84000000UL
#define PSCI_CPU_ON64		0xC4000003UL
#define PSCI_SYSTEM_OFF		0x84000008UL

#define DRAM_START		0x40000000UL
#define DRAM_END		0xC0000000UL

#define WAIT_AFTER_DRAW_S	60
#define WAIT_NO_FB_S		15
#define WATCHDOG_S		75

extern volatile u64 exc_record[4];	/* count, esr, elr, slot (start.S) */
extern char secondary_entry[];

static volatile u64 sec_report;		/* written by the watchdog core */
static u64 cntfrq;

/* ---- tiny runtime --------------------------------------------------- */

void *memset(void *d, int c, unsigned long n)
{
	u8 *p = d;
	while (n--)
		*p++ = (u8)c;
	return d;
}

void *memcpy(void *d, const void *s, unsigned long n)
{
	u8 *p = d;
	const u8 *q = s;
	while (n--)
		*p++ = *q++;
	return d;
}

static inline u32 rd32(u64 a) { return *(volatile u32 *)a; }
static inline void wr32(u64 a, u32 v) { *(volatile u32 *)a = v; }

#define SYSREG(name) ({ u64 _v; __asm__ volatile("mrs %0, " #name : "=r"(_v)); _v; })

static u64 smc(u64 fid, u64 a1, u64 a2, u64 a3)
{
	register u64 x0 __asm__("x0") = fid;
	register u64 x1 __asm__("x1") = a1;
	register u64 x2 __asm__("x2") = a2;
	register u64 x3 __asm__("x3") = a3;
	__asm__ volatile("smc #0"
			 : "+r"(x0), "+r"(x1), "+r"(x2), "+r"(x3)
			 :
			 : "x4", "x5", "x6", "x7", "x8", "x9", "x10", "x11",
			   "x12", "x13", "x14", "x15", "x16", "x17", "memory");
	return x0;
}

static u64 now(void)
{
	__asm__ volatile("isb");
	return SYSREG(cntvct_el0);
}

static void timer_init(void)
{
	cntfrq = SYSREG(cntfrq_el0) & 0xffffffffu;
	if (cntfrq == 0)
		cntfrq = 26000000;	/* exynos7580.dtsi timer clock-frequency */
}

static void delay_ms(u64 ms)
{
	u64 end = now() + cntfrq / 1000 * ms;
	while (now() < end)
		;
}

static void power_off(void)
{
	smc(PSCI_SYSTEM_OFF, 0, 0, 0);
	/* Firmware without SYSTEM_OFF: drop PS_HOLD like the Exynos kernel does. */
	wr32(PMU_PS_HOLD_CONTROL, rd32(PMU_PS_HOLD_CONTROL) & ~PS_HOLD_OUTPUT_HIGH);
	for (;;)
		__asm__ volatile("wfe");
}

static u32 exc_tag(u64 count_before)
{
	if (exc_record[0] == count_before)
		return 0;
	return 0xEEEE0000u | (u32)((exc_record[1] >> 26) & 0x3f);
}

/* ---- watchdog core ---------------------------------------------------- */

void secondary_main(void)
{
	sec_report = 0xC0DE0000u | ((SYSREG(CurrentEL) >> 2) & 3);
	__asm__ volatile("dsb sy");
	timer_init();
	for (u32 s = 0; s < WATCHDOG_S; s++)
		delay_ms(1000);
	power_off();
}

/* ---- framebuffer -------------------------------------------------------- */

struct fb {
	u64 base;
	u32 w, h, stride;	/* pixels */
	u32 fmt;		/* WINCON BPPMODE */
	int win;
};

static int fb_find(struct fb *fb)
{
	for (int w = 0; w < 5; w++) {
		u32 wc = rd32(DECON_BASE + DECON_WINCON(w));
		if (!(wc & 1))
			continue;
		u64 addr = rd32(DECON_BASE + DECON_ADD0(w));
		if (addr < DRAM_START || addr >= DRAM_END)
			continue;
		u32 osd = rd32(DECON_BASE + DECON_OSD_B(w));
		u32 whole = rd32(DECON_BASE + DECON_WHOLE_X(w));
		fb->base = addr;
		fb->fmt = (wc >> 2) & 0x1f;
		fb->w = ((osd >> 13) & 0x1fff) + 1;
		fb->h = (osd & 0x1fff) + 1;
		fb->stride = whole & 0x3fff;
		if (fb->w < 100 || fb->w > 1080)
			fb->w = 1080;
		if (fb->h < 100 || fb->h > 1920)
			fb->h = 1920;
		if (fb->stride < fb->w || fb->stride > 4096)
			fb->stride = fb->w;
		fb->win = w;
		return 1;
	}
	return 0;
}

static u32 pix(const struct fb *fb, u32 rgb)
{
	u32 r = (rgb >> 16) & 0xff, g = (rgb >> 8) & 0xff, b = rgb & 0xff;
	switch (fb->fmt) {
	case 1: case 5:			/* ABGR / XBGR */
		return 0xff000000u | (b << 16) | (g << 8) | r;
	case 2: case 6:			/* RGBA / RGBX */
		return (r << 24) | (g << 16) | (b << 8) | 0xff;
	case 3: case 7:			/* BGRA / BGRX */
		return (b << 24) | (g << 16) | (r << 8) | 0xff;
	case 8:				/* RGB565 */
		return ((r >> 3) << 11) | ((g >> 2) << 5) | (b >> 3);
	default:			/* ARGB / XRGB and anything unknown */
		return 0xff000000u | rgb;
	}
}

static void fill(const struct fb *fb, u32 x, u32 y, u32 w, u32 h, u32 rgb)
{
	u32 v = pix(fb, rgb);
	if (x >= fb->w || y >= fb->h)
		return;
	if (x + w > fb->w)
		w = fb->w - x;
	if (y + h > fb->h)
		h = fb->h - y;
	for (u32 j = y; j < y + h; j++) {
		if (fb->fmt == 8) {
			volatile u16 *row = (volatile u16 *)(fb->base + (u64)j * fb->stride * 2);
			for (u32 i = x; i < x + w; i++)
				row[i] = (u16)v;
		} else {
			volatile u32 *row = (volatile u32 *)(fb->base + (u64)j * fb->stride * 4);
			for (u32 i = x; i < x + w; i++)
				row[i] = v;
		}
	}
}

/* Ask DECON to send the buffer to the panel (it runs in MIPI command mode). */
static void fb_kick(void)
{
	u32 t = rd32(DECON_BASE + DECON_TRIGCON);
	if (t & TRIG_SWTRIGEN)
		wr32(DECON_BASE + DECON_TRIGCON, t | TRIG_SWTRIGCMD);
	else if (t & TRIG_HWTRIGEN)
		wr32(DECON_BASE + DECON_TRIGCON, t | TRIG_HWTRIGMASK);
}

#define NROWS 13

static const u32 label_rgb[NROWS] = {
	0x00ff00, 0xff0000, 0xff8000, 0xffff00, 0x80ff00, 0x00ffff, 0x0080ff,
	0x0000ff, 0x8000ff, 0xff00ff, 0xff0080, 0x808080, 0xffffff,
};

/* One row: colour label on the left, then 32 cells, bit 31 first. */
static void draw_row(const struct fb *fb, int row, u32 value)
{
	u32 rh = fb->h / NROWS;
	u32 y = row * rh;
	u32 cell_y = y + rh / 8, cell_h = rh - rh / 4;
	u32 x0 = 56, avail = fb->w - x0 - 8;
	u32 nib_gap = 12, cell_w = (avail - 7 * nib_gap) / 32;

	fill(fb, 0, y, fb->w, rh, 0x000000);
	fill(fb, 8, cell_y, 36, cell_h, label_rgb[row]);
	for (int bit = 31; bit >= 0; bit--) {
		u32 i = 31 - bit;
		u32 x = x0 + i * cell_w + (i / 4) * nib_gap;
		u32 on = (value >> bit) & 1;
		fill(fb, x, cell_y, cell_w - 4, cell_h, on ? 0xffffff : 0x303030);
	}
}

/* ---- main ---------------------------------------------------------------- */

void probe_main(u64 dtb, u64 load_addr)
{
	u32 row[NROWS];
	u64 c;

	timer_init();

	u64 el = (SYSREG(CurrentEL) >> 2) & 3;
	u64 mpidr = SYSREG(mpidr_el1);

	c = exc_record[0];
	u32 psci_ver = (u32)smc(PSCI_VERSION, 0, 0, 0);
	if (exc_tag(c))
		psci_ver = exc_tag(c);

	/* Watchdog core: another core in the boot core's cluster. */
	u64 target = (mpidr & 0xff00) | ((mpidr & 0xff) == 1 ? 0 : 1);
	c = exc_record[0];
	u32 cpu_on = (u32)smc(PSCI_CPU_ON64, target, (u64)secondary_entry, 0);
	if (exc_tag(c))
		cpu_on = exc_tag(c);
	for (int i = 0; i < 1000 && sec_report == 0; i++)
		delay_ms(1);

	row[0] = 0xffffffff;			/* alive: all cells lit */
	row[1] = (u32)el;
	row[2] = psci_ver;
	row[3] = cpu_on;
	row[4] = (u32)sec_report;
	row[5] = (u32)SYSREG(id_aa64isar0_el1);
	row[6] = (u32)SYSREG(id_aa64mmfr0_el1);
	row[7] = (u32)SYSREG(midr_el1);
	row[9] = (u32)load_addr;
	row[10] = (u32)dtb;

	struct fb fb;
	if (!fb_find(&fb)) {
		for (u32 s = 0; s < WAIT_NO_FB_S; s++)
			delay_ms(1000);
		power_off();
	}
	u32 trig = rd32(DECON_BASE + DECON_TRIGCON);
	row[11] = (u32)fb.base;
	row[12] = ((u32)fb.win << 28) | ((fb.fmt & 0xff) << 20) | (trig & 0xffff);
	/* row 8 last so it also catches faults from the register reads above */
	row[8] = ((u32)(exc_record[0] & 0xff) << 24) |
		 ((u32)((exc_record[1] >> 26) & 0x3f) << 16) |
		 (u32)(exc_record[3] & 0xff);

	for (int r = 0; r < NROWS; r++)
		draw_row(&fb, r, row[r]);
	__asm__ volatile("dsb sy");

	for (u32 t = 0; t < WAIT_AFTER_DRAW_S * 50; t++) {
		fb_kick();
		delay_ms(20);
	}
	power_off();
}
