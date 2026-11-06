/*
 * sweet/matisse boot shim entry point.
 *
 * Runs at EL1 with the MMU and caches off, x0 = live device tree. Either
 * boots the SWEETXNU payload found in the initrd, or, when there is none,
 * answers the questions that decide the port: CPU features, PSCI, GIC and
 * timer, MMU behaviour, and the state of the UFS host. Any unexpected
 * exception paints a panic screen.
 */
#include <stdint.h>
#include "board.h"
#include "console.h"
#include "diag.h"
#include "display.h"
#include "fdt.h"
#include "mmu.h"
#include "loader.h"
#include "ufs.h"
#include "logstore.h"

#ifdef KICK_ONLY
void entryprobe_display_kick(uint64_t dtb, char *banner);
#endif

#define GICR_TYPER		0x08
#define GICR_WAKER		0x14
#define GICR_SGI		0x10000
#define GICR_IGROUPR0		(GICR_SGI + 0x080)
#define GICR_ISENABLER0		(GICR_SGI + 0x100)
#define GICR_ICENABLER0		(GICR_SGI + 0x180)
#define GICR_IPRIORITYR		(GICR_SGI + 0x400)
#define GICR_ISPENDR0		(GICR_SGI + 0x200)
#define GICR_ISACTIVER0		(GICR_SGI + 0x300)

#define PSCI_VERSION		0x84000000UL
#define PSCI_CPU_SUSPEND	0xc4000001UL
#define PSCI_CPU_OFF		0x84000002UL
#define PSCI_CPU_ON		0xc4000003UL
#define PSCI_MIGRATE_INFO_TYPE	0x84000006UL
#define PSCI_SYSTEM_RESET	0x84000009UL
#define PSCI_FEATURES		0x8400000aUL
#define PSCI_SYSTEM_SUSPEND	0xc400000eUL
#define SMCCC_VERSION		0x80000000UL

#define NR_CPUS			8

#define rsr(r) ({ uint64_t _v; __asm__ volatile("mrs %0, " r : "=r"(_v)); _v; })
#define wsr(r, v) __asm__ volatile("msr " r ", %0" : : "r"((uint64_t)(v)))
#define isb() __asm__ volatile("isb" ::: "memory")

static inline uint32_t rd32(uintptr_t a) { return *(volatile uint32_t *)a; }
static inline uint64_t rd64(uintptr_t a) { return *(volatile uint64_t *)a; }
static inline void wr32(uintptr_t a, uint32_t v) { *(volatile uint32_t *)a = v; }
static inline void wr8(uintptr_t a, uint8_t v) { *(volatile uint8_t *)a = v; }

extern char secondary_entry[];

static void log_flush(void);

/* Append only new console text. /chosen/log_store is a structured header,
 * NOT a text buffer; ram_console has another format that we do not write. */
static void dram_log(void)
{
#ifdef SHIM_LOGSTORE_MARK
	/* Experimental: matisse entry+FDT probe boots, but adding direct
	 * PL/LK access prevents recovery from starting. Never enable by default. */
	static uint32_t copied;
	uint32_t len;
	const char *txt = con_text(&len);
	if (len < copied)
		copied = 0;
	if (len > copied && logstore_write(txt + copied, len - copied))
		copied = len;
#endif
}

/* One-block progress marker in the log partition: block index = stage. */
static void mark(uint32_t block, const char *tag)
{
	if (brd.log_part)
		ufs_mark(brd.log_part, block, tag);
}

static const char *stage;	/* set at runtime: no absolute pointers in data */
static volatile uint64_t sec_mpidr[NR_CPUS];
static volatile uint32_t irq_count, irq_other, irq_last;
static volatile int irq_src;

/* ICC_SGI1R_EL1 value targeting the calling core only. */
static uint64_t sgi_self(unsigned id)
{
	uint64_t m = rsr("mpidr_el1");
	return ((m >> 16) & 0xff) << 32 |	/* Aff2 */
	       ((m >> 8) & 0xff) << 16 |	/* Aff1 */
	       (uint64_t)id << 24 |
	       (1U << (m & 0xf));		/* target list: Aff0 */
}

static uint64_t smc(uint64_t fn, uint64_t a1, uint64_t a2, uint64_t a3)
{
	register uint64_t x0 __asm__("x0") = fn;
	register uint64_t x1 __asm__("x1") = a1;
	register uint64_t x2 __asm__("x2") = a2;
	register uint64_t x3 __asm__("x3") = a3;
	__asm__ volatile("smc #0"
			 : "+r"(x0), "+r"(x1), "+r"(x2), "+r"(x3)
			 :
			 : "x4", "x5", "x6", "x7", "x8", "x9", "x10", "x11",
			   "x12", "x13", "x14", "x15", "x16", "x17", "memory");
	return x0;
}

static uint64_t now(void)
{
	isb();
	return rsr("cntpct_el0");
}

/* MTK watchdog (mediatek,mt6983-wdt at 0x1c007000). LK arms it before the
 * jump and XNU does not pet it during early boot. Disable it as the first C
 * statement: the console clear and payload copy are slow with the MMU off.
 * Register layout from the device's own mtk_wdt.ko: MODE bit0 enable and
 * key 0x22000000 (movk w10,#0x2200,lsl#16 in mtk_wdt_stop); PING at +0x08
 * takes 0x1971. The older mainline 0x33<<3 key does not work on MT6983. */
static uint32_t wdt_mode_before, wdt_sta_before, wdt_mode_after;

static void wdt_disable_raw(void)
{
	volatile uint32_t *w = (volatile uint32_t *)0x1c007000UL;

	wdt_mode_before = w[0];
	wdt_sta_before = w[3];
	w[0] = (wdt_mode_before & ~1u) | 0x22000000u;
	__asm__ volatile("dsb sy" ::: "memory");
	wdt_mode_after = w[0];
}

static void wdt_report(void)
{
	con_hex2("WDT", "mode=", wdt_mode_before, "sta=", wdt_sta_before);
	con_hex("WDT", wdt_mode_after);
}

#ifdef XNU_DIAG
/* Diagnostic builds want the 31 s AP watchdog to reset the phone when XNU
 * hangs, so the next shim boot can report the trace. Restore LK's mode and
 * ping once; normal builds leave it off for the life of the system. */
void shim_wdt_restore(void)
{
	volatile uint32_t *w = (volatile uint32_t *)0x1c007000UL;

	w[0] = (wdt_mode_before & ~0x22000000u) | 0x22000000u;
	w[2] = 0x1971;
	__asm__ volatile("dsb sy" ::: "memory");
}
#endif

static void delay_ms(unsigned ms)
{
	uint64_t f = rsr("cntfrq_el0");
	uint64_t end = now() + f / 1000 * ms;
	while (now() < end)
		;
}

static void __attribute__((noreturn)) reset(unsigned after_s)
{
	con_skip();
	con_str("RESET", after_s > 20 ? "in 40s" : "in 20s");
	delay_ms(after_s * 1000);
	smc(PSCI_SYSTEM_RESET, 0, 0, 0);
	for (;;)
		__asm__ volatile("wfe");
}

/* ---- exceptions ---- */

static void irq_handler(void)
{
	uint64_t iar = rsr("icc_iar1_el1");
	uint32_t id = iar & 0xffffff;

	if (id >= 1020 && id <= 1023)
		return;	/* spurious */
	irq_last = id;
	if (id == (uint32_t)irq_src)
		irq_count++;
	else
		irq_other++;
	if (id == brd.vtimer_intid)
		wsr("cntv_tval_el0", rsr("cntfrq_el0") / 100);	/* 10 ms */
	else if (id == brd.ptimer_intid)
		wsr("cntp_tval_el0", rsr("cntfrq_el0") / 100);
	wsr("icc_eoir1_el1", iar);
	isb();
}

void exc_handler(uint64_t slot, uint64_t *regs)
{
	/* A char array, not an array of pointers: the image is linked at 0 and
	 * runs wherever the bootloader put it, so no absolute addresses. */
	static const char kind[4][7] = { "SYNC", "IRQ", "FIQ", "SERROR" };

	if (slot == 5) {	/* IRQ from current EL, SPx */
		irq_handler();
		return;
	}
	con_clear(BLUE);
	con_str("PANIC", kind[slot & 3]);
	con_hex2("SLOT", "n=", slot, "cpu=", rsr("mpidr_el1"));
	con_str("STAGE", stage);
	con_hex("ESR", rsr("esr_el1"));
	con_hex("ELR", rsr("elr_el1"));
	con_hex("FAR", rsr("far_el1"));
	con_hex("SPSR", rsr("spsr_el1"));
	con_hex("X0", regs[0]);
	con_hex("X1", regs[1]);
	con_hex("X30", regs[29]);	/* stashed lr is just above the frame */
	log_flush();
	con_str("HALT", "power+vol-down for fastboot");
	display_refresh();
	for (;;)
		__asm__ volatile("wfe");
}

/* ---- SMP ---- */

static uintptr_t find_gicr(void)
{
	uint64_t aff = rsr("mpidr_el1");
	uint32_t want = (aff & 0xffffff) | ((aff >> 8) & 0xff000000);

	for (uint64_t off = 0; off < brd.gicr_size;) {
		uint64_t typer = rd64(brd.gicr + off + GICR_TYPER);
		if ((uint32_t)(typer >> 32) == want)
			return brd.gicr + off;
		if (typer & (1 << 4))	/* Last */
			break;
		/* A redistributor with VLPI support occupies two 128K frames */
		off += (typer & (1 << 1)) ? 0x40000 : 0x20000;
	}
	return 0;
}

void secondary_main(uint64_t idx)
{
	sec_mpidr[idx] = rsr("mpidr_el1") | (1ULL << 63);
	__asm__ volatile("dsb sy" ::: "memory");
	smc(PSCI_CPU_OFF, 0, 0, 0);
}

/* ---- GIC + timer ---- */

static void gicd_wait_rwp(void)
{
	for (int i = 0; i < 1000000 && (rd32(brd.gicd) & (1U << 31)); i++)
		;
}

/* Run one interrupt source for ~300 ms and report what the GIC saw. */
static void irq_window(const char *label, uintptr_t r, uint32_t src)
{
	uint64_t f = rsr("cntfrq_el0");
	uint32_t pend = 0, act = 0, isr = 0, hppi = 0x3ff, ist = 0;

	irq_count = irq_other = 0;
	irq_last = 0x3ff;
	irq_src = src;
	if (src == brd.vtimer_intid) {
		wsr("cntv_tval_el0", f / 100);
		wsr("cntv_ctl_el0", 1);
	} else if (src == brd.ptimer_intid) {
		wsr("cntp_tval_el0", f / 100);
		wsr("cntp_ctl_el0", 1);
	}
	isb();
	/* sample state with IRQs still masked, after the first period */
	uint64_t t = now() + f / 50;
	while (now() < t)
		;
	if (src == brd.sgi_intid)
		wsr("icc_sgi1r_el1", sgi_self(brd.sgi_intid));
	isb();
	ist = src == brd.ptimer_intid ? rsr("cntp_ctl_el0") : rsr("cntv_ctl_el0");
	pend = rd32(r + GICR_ISPENDR0);
	act = rd32(r + GICR_ISACTIVER0);
	isr = rsr("isr_el1");
	hppi = rsr("icc_hppir1_el1");

	__asm__ volatile("msr daifclr, #2" ::: "memory");
	t = now() + f * 3 / 10;
	uint64_t next = now() + f / 100;
	for (int sent = 1; now() < t;)
		if (src == brd.sgi_intid && sent < 10 && now() >= next) {
			wsr("icc_sgi1r_el1", sgi_self(brd.sgi_intid));
			isb();
			sent++;
			next += f / 100;
		}
	__asm__ volatile("msr daifset, #2" ::: "memory");
	wsr("cntv_ctl_el0", 0);
	wsr("cntp_ctl_el0", 0);
	isb();

	con_hex2(label, "irqs=", irq_count, "other=", irq_other);
	con_hex2(" pre", "pend=", pend, "act=", act);
	con_hex2(" pre", "isr=", isr, "hppi=", hppi);
	con_hex2(" pre", "tctl=", ist, "last=", irq_last);
}

static void test_gic(void)
{
	stage = "gic sre";
	uint64_t sre = rsr("icc_sre_el1");
	if (!(sre & 1)) {
		wsr("icc_sre_el1", sre | 1);
		isb();
	}
	if (!(rsr("icc_sre_el1") & 1)) {
		con_str("GIC", "no sysreg iface, skip");
		return;
	}

	/* Identify the distributor: GICD_IIDR (0x8) and GICD_PIDR2 (0xfe8). */
	stage = "gic id";
	con_hex2("GICD", "iidr=", rd32(brd.gicd + 0x8), "pidr2=", rd32(brd.gicd + 0xfe8));
	con_hex2("GICR", "typer=", (uint32_t)rd64(brd.gicr + GICR_TYPER),
		 "typerhi=", (uint32_t)(rd64(brd.gicr + GICR_TYPER) >> 32));

	stage = "gic dist";
	uint32_t dctlr = rd32(brd.gicd);
	/* Non-secure view (DS=0): bit0 EnableGrp1, bit1 EnableGrp1A, bit4 ARE_NS */
	wr32(brd.gicd, dctlr | 0x13);
	gicd_wait_rwp();
	con_hex2("GICD", "was=", dctlr, "now=", rd32(brd.gicd));

	stage = "gic redist";
	uintptr_t r = find_gicr();
	if (!r) {
		con_str("GICR", "not found");
		return;
	}
	uint32_t waker = rd32(r + GICR_WAKER);
	if (waker & 2) {
		wr32(r + GICR_WAKER, waker & ~2U);
		for (int i = 0; i < 100000 && (rd32(r + GICR_WAKER) & 4); i++)
			;
	}
	con_hex2("GICR", "base=", (uint32_t)r, "waker=", rd32(r + GICR_WAKER));

	stage = "gic config";
	wr32(r + GICR_IGROUPR0, 0xffffffff);	/* NS view: secure bits are WI */
	uint32_t en_before = rd32(r + GICR_ISENABLER0);
	for (int id = 0; id < 32; id++)
		wr8(r + GICR_IPRIORITYR + id, 0xa0);
	wr32(r + GICR_ISENABLER0, (1U << brd.vtimer_intid) | (1U << brd.ptimer_intid) |
				   (1U << brd.sgi_intid));
	con_hex2("ENABLE", "was=", en_before, "now=", rd32(r + GICR_ISENABLER0));

	uint64_t ctlr = rsr("icc_ctlr_el1");
	wsr("icc_ctlr_el1", ctlr & ~2ULL);	/* EOImode 0: EOIR also deactivates */
	wsr("icc_pmr_el1", 0xf0);
	wsr("icc_bpr1_el1", 0);
	wsr("icc_igrpen1_el1", 1);
	isb();
	con_hex2("ICC", "ctlr=", (uint32_t)ctlr, "grpen1=", (uint32_t)rsr("icc_igrpen1_el1"));

	stage = "gic vtimer";
	irq_window("VTIMER", r, brd.vtimer_intid);
	stage = "gic ptimer";
	irq_window("PTIMER", r, brd.ptimer_intid);
	stage = "gic sgi";
	irq_window("SGI1", r, brd.sgi_intid);
	wr32(r + GICR_ICENABLER0, 0xffffffff);
	isb();
}

/* ---- main ---- */

#ifdef DIAG_LOG
static char *
diag_hex(char *p, uint32_t v)
{
	static const char h[] = "0123456789abcdef";
	for (int i = 28; i >= 0; i -= 4)
		*p++ = h[(v >> i) & 15];
	return p;
}

static char *
diag_str(char *p, const char *s)
{
	while (*s)
		*p++ = *s++;
	return p;
}

/* Dump the display handoff state into the PL/LK log_store (read via
 * /proc/pl_lk in a later recovery boot). Fixed MMIO addresses: this is the
 * matisse-only diagnostic build, not the normal path. */
static void
diag_log(void)
{
	char b[512];
	char *p = b;
	uint32_t o0 = *(volatile uint32_t *)0x1400200cUL;
	uint32_t o0a = *(volatile uint32_t *)0x14002f40UL;
	uint32_t o2 = *(volatile uint32_t *)0x1400400cUL;
	uint32_t o2a = *(volatile uint32_t *)0x14004f40UL;
	uint32_t con = *(volatile uint32_t *)0x14017010UL;
	uint32_t mod = *(volatile uint32_t *)0x14017014UL;
	uint32_t sta = *(volatile uint32_t *)0x1401700cUL;
	uint32_t st = *(volatile uint32_t *)0x14017000UL;
	uint32_t ps = *(volatile uint32_t *)0x1401701cUL;
	uint32_t sc = *(volatile uint32_t *)0x14017038UL;
	uint32_t c0 = *(volatile uint32_t *)0x14000100UL;
	uint32_t c1 = *(volatile uint32_t *)0x14000110UL;
	uint32_t c2 = *(volatile uint32_t *)0x140001a0UL;

	p = diag_str(p, "SWEETXNU-DIAG ");
	p = diag_str(p, "o0="); p = diag_hex(p, o0); *p++ = '/';
	p = diag_hex(p, o0a);
	p = diag_str(p, " o2="); p = diag_hex(p, o2); *p++ = '/';
	p = diag_hex(p, o2a);
	p = diag_str(p, " dsi="); p = diag_hex(p, con); *p++ = '/';
	p = diag_hex(p, mod); *p++ = '/'; p = diag_hex(p, st); *p++ = '/';
	p = diag_hex(p, sta);
	p = diag_str(p, " ps="); p = diag_hex(p, ps);
	p = diag_str(p, " sc="); p = diag_hex(p, sc);
	p = diag_str(p, " cg="); p = diag_hex(p, c0); *p++ = '/';
	p = diag_hex(p, c1); *p++ = '/'; p = diag_hex(p, c2);
	p = diag_str(p, " fb="); p = diag_hex(p, (uint32_t)brd.fb_base);
	p = diag_str(p, " st="); p = diag_hex(p, brd.fb_stride);
	*p++ = '\n';
	logstore_write(b, (uint32_t)(p - b));
}
#endif

/* Persistent one-byte progress marker for diagnosing a pre-serial hang.
 * Writes a short line into the kernel ram_console buffer, which LK's
 * `fastboot oem lkmsg` dumps after a warm reset. Kept far from the ring
 * cursor so a partial kernel log cannot hide it. The address was never
 * confirmed on matisse; opt in only when testing that channel. */
#ifdef DIAG_MARK
static void persist_mark(char tag)
{
	uintptr_t base = brd.ram_console ? (uintptr_t)brd.ram_console
	    : 0x00d01100UL;
	volatile char *p = (volatile char *)(base + 0x3ff00);
	const char *s = "SWEETXNU-SHIM-";
	while (*s)
		*p++ = *s++;
	*p++ = tag;
	*p++ = '\n';
	__asm__ volatile("dsb sy" ::: "memory");
}
#else
static inline void persist_mark(char tag)
{
	(void)tag;
}
#endif

/*
 * Persist the console text so far. Called after every stage and from the
 * panic handler: the panel is often dark on MediaTek (LK turns the DSI link
 * off before jumping). All persistent/experimental log channels are opt-in.
 */
static void log_flush(void)
{
	uint32_t len;
	const char *txt;

	dram_log();
	if (!brd.log_part)
		return;
	txt = con_text(&len);
	ufs_log_write(brd.log_part, brd.log_off_blocks, txt, len);
}

/*
 * Paint the stored console text into every scanout buffer the bootloader
 * reserved. MediaTek's DSI driver cycles through three frames, so the one
 * on screen is not necessarily the first; this costs 3 x 18 MiB of writes.
 */
static void fb_paint_all(void)
{
	for (int i = 0; i < brd.fb_count; i++) {
		uint64_t base = brd.fb_base + (uint64_t)i * brd.fb_stride * brd.fb_h;

		con_target((volatile uint32_t *)base);
		con_redraw(RED);
	}
	con_target((volatile uint32_t *)brd.fb_base);
	display_refresh();
}

/*
 * Set the Android boot-control block in `misc` to "boot-recovery" and reset.
 * The block is read first and only patched when it looks like a BCB, so a
 * broken UFS path cannot scribble on the partition.
 */
static int boot_recovery(void)
{
#ifndef SHIM_STORAGE_LOG
	return -1; /* misc is persistent state; no implicit writes during bring-up */
#else
	static uint8_t bcb[4096] __attribute__((aligned(4096)));
	int rc = ufs_part_read("misc", 0, bcb, 1);

	if (rc)
		return rc;
	/* command[32] must be NUL-terminated printable text or empty */
	for (int i = 0; i < 32; i++)
		if (bcb[i] && (bcb[i] < 0x20 || bcb[i] > 0x7e))
			return 6;
	for (int i = 0; i < 32; i++)
		bcb[i] = 0;
	const char cmd[] = "boot-recovery";
	for (int i = 0; cmd[i]; i++)
		bcb[i] = (uint8_t)cmd[i];
	return ufs_part_write("misc", 0, bcb, 1);
#endif
}

/* Board facts, printed on every boot. */
static void print_board(uintptr_t dtb)
{
	con_str("BOARD", board_name());
	con_hex2("FB", "base=", (uint32_t)brd.fb_base, "size=", (uint32_t)brd.fb_size);
	con_hex2("FB", "w=", brd.fb_w, "h=", brd.fb_h);
	con_hex2("GIC", "gicd=", (uint32_t)brd.gicd, "gicr=", (uint32_t)brd.gicr);
	con_hex2("GIC", "rsize=", (uint32_t)brd.gicr_size, "stride=", (uint32_t)brd.gicr_stride);
	con_hex2("TIMER", "virt=", brd.vtimer_intid, "phys=", brd.ptimer_intid);
	con_hex2("UFS", "base=", (uint32_t)brd.ufs_base, "dram=", (uint32_t)brd.dram_base);
	con_hex("DRAM", brd.dram_size);
	con_hex2("MPIDR", "lo=", (uint32_t)rsr("mpidr_el1"), "hi=", (uint32_t)(rsr("mpidr_el1") >> 32));
	con_hex2("EL", "now=", (uint32_t)(rsr("CurrentEL") >> 2), "spsel=", (uint32_t)rsr("spsel"));
	con_hex2("CNTFRQ", "hz=", (uint32_t)rsr("cntfrq_el0"), "cnt=", (uint32_t)now());
	con_hex2("MMFR0", "pa=", (uint32_t)(rsr("id_aa64mmfr0_el1") & 0xf),
		 "tg16=", (uint32_t)((rsr("id_aa64mmfr0_el1") >> 20) & 0xf));
	con_hex2("DTB", "at=", (uint32_t)dtb, "magic=", dtb ? fdt_be32(dtb) : 0);
}

void shim_main(uint64_t dtb)
{
	struct mmu_info mi;

#ifdef KICK_ONLY
	/* Isolation build: no board_probe, no logstore, no payload. Run the
	 * exact display-kick function that was validated on hardware, with
	 * the measured matisse framebuffer. Leave the watchdog alone so a
	 * hang cycles through LK instead of staying dark forever. */
	brd.name = "matisse";
	brd.fb_base = 0xfcb3f000ULL;
	brd.fb_size = 0x34c0000ULL;
	brd.fb_w = 1440;
	brd.fb_h = 3200;
	brd.fb_stride = 5760;
	brd.fb_bgr = 0;
	con_fb = (volatile uint32_t *)(uintptr_t)brd.fb_base;
	con_w = brd.fb_w;
	con_h = brd.fb_h;
	con_stride = brd.fb_stride;
	con_bgr = brd.fb_bgr;
	con_text_reset();
	{
		static char banner[512];

		entryprobe_display_kick(dtb, banner);
	}
	con_str("SHIM", "KICK DONE");
	for (;;)
		__asm__ volatile("wfe");
#endif

#ifdef RAW_RESET
	/* Execution proof: if LK jumps into this image, reset immediately so
	 * the boot cycle is visibly shorter than a watchdog timeout. */
	smc(PSCI_SYSTEM_RESET, 0, 0, 0);
	for (;;)
		__asm__ volatile("wfe");
#endif

#ifdef RAW_PAINT
	/* Last-resort execution + display proof: no FDT/console/board_probe.
	 * Validate the OVL scan address (a gated block reads all ones), paint
	 * green there and at the documented base, wait for TE, then push a
	 * few frames. A missing TE or a bad address simply halts. */
	{
		/* Enable any gated display clock first: reading a gated OVL/DSI
		 * block can hang the boot. CLR is status+8; SET would gate it. */
		uint32_t g0 = *(volatile uint32_t *)0x14000100UL;
		uint32_t g1 = *(volatile uint32_t *)0x14000110UL;
		uint32_t g2 = *(volatile uint32_t *)0x140001a0UL;
		if (g0 & 0x28000001UL)
			*(volatile uint32_t *)0x14000108UL = g0 & 0x28000001UL;
		if (g1 & 0x100UL)
			*(volatile uint32_t *)0x14000118UL = g1 & 0x100UL;
		if (g2 & 1UL)
			*(volatile uint32_t *)0x140001a8UL = g2 & 1UL;
		__asm__ volatile("dsb sy" ::: "memory");

		/* Rebuild the cmd-mode buffer if LK left it off. */
		uint32_t bc0 = *(volatile uint32_t *)0x14017400UL;
		if ((bc0 & 1u) == 0) {
			uint32_t bc1 = *(volatile uint32_t *)0x14017404UL;
			*(volatile uint32_t *)0x14017404UL =
			    (bc1 & 0xffff0000u) | 0xb1u;
			*(volatile uint32_t *)0x14017410UL = 512000u;
			*(volatile uint32_t *)0x14017170UL |= (1u << 10);
			*(volatile uint32_t *)0x14017400UL = bc0 | 1u;
		}
		*(volatile uint32_t *)0x14017090UL = 0x3cu;

		uint32_t scan = *(volatile uint32_t *)0x14004f40UL;
		if (scan < 0x40000000UL || scan >= 0x100000000UL)
			scan = 0xfcb3f000UL;
		volatile uint32_t *targets[2] = {
			(volatile uint32_t *)(uintptr_t)scan,
			(volatile uint32_t *)0xfcb3f000UL
		};
		for (int t = 0; t < 2; t++) {
			volatile uint32_t *fb = targets[t];
			for (uint32_t y = 0; y < 64; y++)
				for (uint32_t x = 0; x < 1440; x++)
					fb[(uint64_t)y * 1440 + x] = 0xff00ff00u;
		}
		__asm__ volatile("dsb sy" ::: "memory");

		*(volatile uint32_t *)0x14017010UL =
		    (1u << 1) | (1u << 24) | (1u << 27);
		*(volatile uint32_t *)0x14017100UL = 0x55;
		*(volatile uint32_t *)0x14017104UL |= 1u;
		/* Wait for a fresh TE pulse: cmd-mode START is ignored without
		 * it. INTSTA is write-0-to-clear. */
		*(volatile uint32_t *)0x1401700cUL = ~(1u << 2);
		uint64_t frq;
		__asm__ volatile("mrs %0, cntfrq_el0" : "=r"(frq));
		uint64_t deadline;
		__asm__ volatile("isb; mrs %0, cntpct_el0" : "=r"(deadline));
		deadline += frq / 30;	/* 33 ms */
		while ((*(volatile uint32_t *)0x1401700cUL & (1u << 2)) == 0) {
			uint64_t now;
			__asm__ volatile("isb; mrs %0, cntpct_el0" : "=r"(now));
			if (now >= deadline)
				break;
		}
		for (int i = 0; i < 4; i++) {
			*(volatile uint32_t *)0x14001008UL = 0;
			*(volatile uint32_t *)0x14001020UL = 0;
			*(volatile uint32_t *)0x14001020UL = 1;
			*(volatile uint32_t *)0x14017000UL = 1;
			__asm__ volatile("dsb sy" ::: "memory");
			uint64_t until;
			__asm__ volatile("isb; mrs %0, cntpct_el0" : "=r"(until));
			until += frq / 50;	/* 20 ms between frames */
			while (1) {
				uint64_t now;
				__asm__ volatile("isb; mrs %0, cntpct_el0" : "=r"(now));
				if (now >= until)
					break;
			}
		}
	}
	for (;;)
		__asm__ volatile("wfe");
#endif

	/* Do this before any 18 MB framebuffer clear or payload copy. */
#ifndef WDT_NO_TOUCH
	wdt_disable_raw();
#endif
	/* Find log_store and decide whether this boot reports the previous
	 * test. Must happen before the loader copies segments again. */
	diag_early(dtb);
	diag_stage("S0 wdt", wdt_mode_before, wdt_mode_after);

#ifdef WDT_HALT
	/* Bisection build: prove the shim executes (WDT_NO_TOUCH) and/or the
	 * watchdog write takes effect. No display push, no payload. */
	for (;;)
		__asm__ volatile("wfe");
#endif

	persist_mark('A');

#ifdef BRINGUP_MARK
#ifndef SHIM_STORAGE_LOG
#error "BRINGUP_MARK writes partitions; explicitly enable SHIM_STORAGE_LOG"
#endif
	/* Bisection build: no FDT, no console, no MMU - just prove the UFS
	 * path works by writing one marker block, then reset. */
	brd.name = "matisse";
	brd.log_part = "oops";
	brd.log_off_blocks = 0;
	brd.ufs_base = 0x112b0000ULL;
	brd.gicd = 0x0c400000ULL;
	brd.gicr = 0x0c440000ULL;
	brd.gicr_size = 0x200000ULL;
	brd.gicr_stride = 0x20000ULL;
	brd.vtimer_intid = 27;
	brd.ptimer_intid = 30;
	brd.sgi_intid = 1;
	brd.fb_base = 0;
	ufs_mark("oops", 0, "raw");
	ufs_mark("boot_a", 1024, "raw");
	delay_ms(500);
	smc(PSCI_SYSTEM_RESET, 0, 0, 0);
	for (;;)
		__asm__ volatile("wfe");
#endif

#ifdef SHIM_LOGSTORE_MARK
	logstore_mark("entry", dtb, rsr("cntfrq_el0"));
#endif
	stage = "board";
	persist_mark('B');
	if (!board_probe(dtb)) {
		/* No usable tree: fall back to the compile-time defaults. */
		brd.name = "unknown";
		brd.fb_base = 0x9c000000UL;
		brd.fb_size = 0x1700000UL;
		brd.fb_w = 1080;
		brd.fb_h = 2400;
		brd.fb_stride = 1080 * 4;
		brd.gicd = 0x17a00000UL;
		brd.gicr = 0x17a60000UL;
		brd.gicr_size = 0x100000UL;
		brd.gicr_stride = 0x20000UL;
		brd.vtimer_intid = 19;
		brd.ptimer_intid = 18;
		brd.sgi_intid = 1;
		brd.ufs_base = 0x01d84000UL;
		brd.dram_base = 0x100000000ULL;
		brd.dram_size = 0xfcc00000UL;
	}
	/* First act after reading the tree: leave evidence that we ran at all.
	 * The panel is command-mode DSI, so framebuffer writes are invisible
	 * until something pushes a frame. Partition logging is opt-in only. */
	mark(0, "entry");
	dram_log();
#ifdef SHIM_LOGSTORE_MARK
	logstore_mark("board", brd.log_store, brd.fb_base);
#endif

	con_fb = brd.fb_base ? (volatile uint32_t *)brd.fb_base : 0;
	con_w = brd.fb_w;
	con_h = brd.fb_h;
	con_stride = brd.fb_stride;
	con_bgr = brd.fb_bgr;
	con_text_reset();
	persist_mark('C');
#ifdef SHIM_LOGSTORE_MARK
	logstore_mark("con-init", (uint64_t)(uintptr_t)con_fb, brd.fb_stride);
#endif
#ifdef MINIMAL_PAINT
	/* Display-path diagnostic: no payload is loaded, no 18 MB clear. Paint
	 * a small green band, push exactly one command-mode frame, then halt
	 * so the panel keeps the result until the watchdog. */
	if (con_fb) {
		for (uint32_t y = 0; y < 64 && y < con_h; y++) {
			volatile uint32_t *line = con_fb + (uint64_t)y * (con_stride / 4);
			for (uint32_t x = 0; x < con_w; x++)
				line[x] = GREEN;
		}
		__asm__ volatile("dsb sy" ::: "memory");
	}
	persist_mark('D');
#ifdef DIAG_LOG
	diag_log();
#endif
	int pok = display_probe(dtb, brd.fb_base, brd.fb_stride);
	persist_mark(pok ? 'E' : 'e');
	con_str("SHIM", "MINIMAL PAINT");
	con_hex2("DISP", "probe=", pok, "active=", display_active());
	con_hex2("FB", "base=", (uint32_t)brd.fb_base, "stride=", brd.fb_stride);
	display_refresh();
	persist_mark('F');
	for (;;)
		__asm__ volatile("wfe");
#endif

	stage = "loader";
#ifdef MINIMAL_PROBE
	/* Over the logo, no clear: 18 MB of Device-memory stores is slow and
	 * the watchdog may fire before anything is visible. */
	con_str("SHIM", "minimal probe: console + FDT");
	con_str("BOARD", board_name());
	con_hex2("FB", "base=", (uint32_t)brd.fb_base, "size=", (uint32_t)brd.fb_size);
	con_hex2("FB", "w=", brd.fb_w, "h=", brd.fb_h);
	con_hex2("GIC", "gicd=", (uint32_t)brd.gicd, "gicr=", (uint32_t)brd.gicr);
	con_hex2("TIMER", "virt=", brd.vtimer_intid, "phys=", brd.ptimer_intid);
	con_hex2("UFS", "base=", (uint32_t)brd.ufs_base, "dram=", (uint32_t)brd.dram_base);
	con_hex2("EL", "now=", (uint32_t)(rsr("CurrentEL") >> 2), "cntfrq=", (uint32_t)rsr("cntfrq_el0"));
	con_hex2("MPIDR", "lo=", (uint32_t)rsr("mpidr_el1"), "dtb=", (uint32_t)dtb);
	con_str("HALT", "if you can read this, the console works");
	for (;;)
		__asm__ volatile("wfe");
#endif
	con_clear(RED);
	log_flush();
	con_str("SHIM", "sweet/matisse xnu loader");
	con_str("DIAG", "wdt-off permissive-display");
	wdt_report();
	if (!con_fb)
		con_str("FB", "no usable framebuffer: log only");
	con_skip();
	print_board(dtb);
	con_skip();
	log_flush();
	/* LK leaves the command-mode panel initialized; push what we drew so
	 * the next visible change is XNU's console rather than a dark screen. */
	int dprobe = display_probe(dtb, brd.fb_base, brd.fb_stride);
	con_hex2("DISP", "probe=", dprobe, "err=", display_error());
	if (dprobe)
		display_refresh();
	else
		display_force_refresh();
	if (diag_reporting()) {
		diag_report();
#ifdef WDT_AUTO_RESET
		shim_wdt_restore();
#endif
		for (;;)
			__asm__ volatile("wfe");
	}
	diag_stage("S1 board", brd.fb_base, brd.fb_stride);
	diag_stage("S1 disp", (uint64_t)dprobe, display_error());
	diag_prev_report();
#ifdef DIAG_UFS_LOG
	/* Partition log probe: the panel may be dead, so the answer is the
	 * SWLG block in expdb, read later with adb dd. */
	test_ufs();
	if (display_active())
		display_refresh();
	{
		uint64_t first = 0, blocks = 0;
		uint32_t len = 0;
		const char *txt = con_text(&len);
		int rc = 9;

		if (ufs_gpt_find("expdb", &first, &blocks) && blocks > 64)
			rc = ufs_log_write("expdb", blocks - 32, txt, len);
		con_hex2("UFSLOG", "rc=", rc, "blk=", (uint32_t)(blocks ? blocks - 32 : 0));
		if (display_active())
			display_refresh();
	}
	for (;;)
		__asm__ volatile("wfe");
#endif
	mark(1, "console");
#ifdef SHIM_LOGSTORE_MARK
	logstore_mark("console", brd.fb_base, brd.fb_size);
	logstore_mark("loader", dtb, 0);
#endif
	con_str("XNU", display_active() ? "loading payload" : "panel unavailable");
	display_refresh();
	/* Leave the loader screen visible before XNU takes the panel. */
	delay_ms(1500);
	const char *why = loader_boot(dtb);
	con_str("LOADER", why);
	con_skip();
#ifdef XNU_DIAG
	diag_stage("SERR", (uint64_t)(uintptr_t)why, 0);
#endif
	/* On matisse the code below probes sweet's Qualcomm UFS/GIC; touching
	 * those registers can hang and hide the LOADER line. Keep the panel on
	 * the loader error instead. */
	if (brd.name && brd.name[0] == 'm') {
		if (display_active())
			display_refresh();
		else
			display_force_refresh();
#ifdef XNU_DIAG
#ifdef WDT_AUTO_RESET
		shim_wdt_restore();
#endif
#endif
		for (;;)
			__asm__ volatile("wfe");
	}
#ifdef SHIM_LOGSTORE_MARK
	logstore_mark("nopayload", (uint64_t)(uintptr_t)why, 0);
#endif

	/* No payload: probe the hardware and leave a log behind. */
	stage = "mmu enable";
	log_flush();
#ifdef SHIM_LOGSTORE_MARK
	logstore_mark("mmu-pre", (uint64_t)(uintptr_t)shim_main, brd.fb_base);
#endif
	int rc = mmu_enable(&mi, brd.fb_base);
	mark(2, "mmu");
#ifdef SHIM_LOGSTORE_MARK
	logstore_mark("mmu", (uint32_t)rc, mi.n_l3);
#endif
	con_hex2("MMU", "rc=", rc, "l3=", mi.n_l3);
	con_hex("TTBR0", mi.ttbr);
	con_hex("SCTLR0", mi.sctlr_before);
	con_hex("SCTLR1", mi.sctlr_after);
	con_hex("PAR img", mmu_probe((uintptr_t)shim_main));
	con_hex("PAR fb", mmu_probe(brd.fb_base + 0x1000));
	con_hex("PAR gic", mmu_probe(brd.gicd));
	con_skip();

	stage = "psci";
	log_flush();
#ifdef SHIM_LOGSTORE_MARK
	logstore_mark("psci-pre", 0, 0);
#endif
	con_hex2("PSCI", "ver=", smc(PSCI_VERSION, 0, 0, 0), "smccc=", smc(SMCCC_VERSION, 0, 0, 0));
	con_hex2("PSCI", "cpu_on=", smc(PSCI_FEATURES, PSCI_CPU_ON, 0, 0),
		 "reset=", smc(PSCI_FEATURES, PSCI_SYSTEM_RESET, 0, 0));
	con_skip();
	mark(3, "psci");
#ifdef SHIM_LOGSTORE_MARK
	logstore_mark("psci", 0, 0);
#endif

	log_flush();
#ifdef SHIM_LOGSTORE_MARK
	logstore_mark("gic-pre", brd.gicd, brd.gicr);
#endif
	test_gic();
	con_skip();
	mark(4, "gic");
#ifdef SHIM_LOGSTORE_MARK
	logstore_mark("gic", irq_count, irq_other);
#endif
	log_flush();

	stage = "ufs";
	log_flush();
#ifdef SHIM_LOGSTORE_MARK
	logstore_mark("ufs-pre", brd.ufs_base, 0);
#endif
	test_ufs();
	con_skip();
	mark(5, "ufs");
#ifdef SHIM_LOGSTORE_MARK
	logstore_mark("ufs", 0, 0);
#endif

	/* Persist the console text so a dark panel is still diagnosable. */
	stage = "log";
	if (brd.log_part) {
		uint32_t len;
		const char *txt = con_text(&len);
		int wrc = ufs_log_write(brd.log_part, brd.log_off_blocks, txt, len);

		con_hex2("LOG", brd.log_part, brd.log_off_blocks, "rc=", wrc);
	}

	stage = "done";
	con_str("DONE", "rebooting into recovery");
	fb_paint_all();
	log_flush();

	/* MediaTek's watchdog resets us anyway; going to recovery makes the
	 * next boot useful (the log is readable over adb there). */
	{
		int rc = boot_recovery();
		con_hex2("BCB", "misc_rc=", rc, "target=", 0);
		fb_paint_all();
		log_flush();
		delay_ms(2000);
		smc(PSCI_SYSTEM_RESET, 0, 0, 0);
	}
	for (;;)
		__asm__ volatile("wfe");
}
