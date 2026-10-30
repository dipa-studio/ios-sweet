/*
 * A51 milestone A1: one boot answers the questions that decide the port.
 *   - Does the command-mode panel show what we write to S-Boot's
 *     framebuffer (0xca000000)? A live counter line must keep changing.
 *   - Exception level, MIDR, ID_AA64MMFR0 (TGran16) on the boot A53 and on
 *     an A73 started with PSCI CPU_ON. XNU needs 16K pages.
 *   - PSCI version, trusted-OS migration type, whether the boot A53 may
 *     switch itself off (XNU would then own only the A73 cluster).
 *   - Exynos watchdog state, and the volume/power GPIOs (gpa1 5/6/7).
 * The panel is in MIPI command mode: it only shows memory when DECON is
 * triggered, so first restart DECON and unmask its hardware (TE) trigger
 * the way Samsung's decon_reg_start() does (dpu20/cal_9610/decon_reg.c).
 * After ~40 s the probe resets the phone (PSCI SYSTEM_RESET), so a reboot
 * loop proves the code runs even if nothing shows. Hold Power + Volume up
 * while it restarts to get to TWRP. Nothing is written to storage.
 */
#include <stdint.h>
#include "console.h"

/* pinctrl@11850000 (ALIVE): etc0 0x000, gpa0 0x020, gpa1 0x040 (pinctrl-exynos-arm64.c) */
#define GPA1_CON		0x11850040UL
#define GPA1_DAT		0x11850044UL
#define GPA1_PUD		0x11850048UL
#define PMU			0x11860000UL	/* exynos-reboot.c */
#define PMU_SWRESET		0x0400
#define PMU_INFORM3		0x080c	/* SEC_DEBUG_PANIC_INFORM (sec_ext.h) */
#define  SEC_RESET_REASON_RECOVERY 0x12345674	/* sec_reboot.c */
#define WDT_CL0			0x10050000UL	/* WTCON at +0 */
#define WDT_CL1			0x10060000UL

#define DECON_F			0x148b0000UL	/* decon_f, live DT */
#define GLOBAL_CONTROL		0x0000
#define  DECON_EN		(1U << 1)
#define  DECON_EN_F		(1U << 0)
#define  RUN_STATUS		(1U << 4)
#define SHADOW_REG_UPDATE_REQ	0x0060
#define  UPDATE_REQ_GLOBAL	(1U << 31)
#define HW_SW_TRIG_CONTROL	0x0070
#define  HW_TRIG_EN		(1U << 0)
#define  HW_TRIG_MASK_DECON	(1U << 4)

#define PSCI_VERSION		0x84000000UL
#define PSCI_CPU_OFF		0x84000002UL
#define PSCI_CPU_ON		0xc4000003UL
#define PSCI_AFFINITY_INFO	0xc4000004UL
#define PSCI_SYSTEM_RESET	0x84000009UL
#define PSCI_MIGRATE_INFO_TYPE	0x84000006UL
#define PSCI_MIGRATE_INFO_UP	0xc4000007UL
#define PSCI_FEATURES		0x8400000aUL

#define A73_IDX			4	/* cpu4 = MPIDR 0x100, first core of cluster 1 */

#define rsr(r) ({ uint64_t _v; __asm__ volatile("mrs %0, " r : "=r"(_v)); _v; })
#define isb() __asm__ volatile("isb" ::: "memory")
#define dsb() __asm__ volatile("dsb sy" ::: "memory")

static inline uint32_t rd32(uintptr_t a) { return *(volatile uint32_t *)a; }
static inline void wr32(uintptr_t a, uint32_t v) { *(volatile uint32_t *)a = v; }

extern char secondary_entry[];

static const char *stage;	/* set at runtime: no absolute pointers in data */

/*
 * Filled by the secondaries, indexed Aff0 + 4 * Aff1. MMU and caches are off
 * everywhere: plain shared memory. sec_marker/sec_ctx are written by the
 * first instructions of secondary_entry (MPIDR, and the x0 PSCI handed over).
 */
volatile uint64_t sec_marker[8], sec_ctx[8];
static volatile uint64_t sec_seen[8], sec_el[8], sec_midr[8], sec_mmfr0[8];
static volatile uint64_t sec_go_live;
static volatile int live_row, a53_row;
static volatile int64_t a53_off_ret = 0x7777;	/* stays if CPU_OFF never returns */
static volatile uint32_t decon_before[3], decon_after[3], decon_runwait;

static uint64_t smc(uint64_t fn, uint64_t a1, uint64_t a2, uint64_t a3);
static void delay_ms(unsigned ms);

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

static void delay_ms(unsigned ms)
{
	uint64_t f = rsr("cntfrq_el0");
	if (!f)
		f = 26000000;	/* DT clock-frequency */
	uint64_t end = now() + f / 1000 * ms;
	while (now() < end)
		;
}

static void delay_us(unsigned us)
{
	uint64_t f = rsr("cntfrq_el0");
	if (!f)
		f = 26000000;
	uint64_t end = now() + f / 1000000 * us;
	while (now() < end)
		;
}

/*
 * PSCI SYSTEM_RESET is not implemented (PSCI 0.1). Reboot like Samsung's
 * sec_reboot("recovery"): S-Boot reads the reason from PMU INFORM3 (the
 * generic exynos SYSIP_DAT0 = 0xff was ignored in boot A1d), then SWRESET.
 */
static void __attribute__((noreturn)) reset_now(void)
{
	dsb();
	wr32(PMU + PMU_INFORM3, SEC_RESET_REASON_RECOVERY);
	dsb();
	wr32(PMU + PMU_SWRESET, 1);
	for (;;)
		__asm__ volatile("wfe");
}

/* decon_reg_start(): enable, global shadow update, wait run, unmask HW trigger. */
static void decon_kick(void)
{
	uintptr_t d = DECON_F;
	decon_before[0] = rd32(d + GLOBAL_CONTROL);
	decon_before[1] = rd32(d + SHADOW_REG_UPDATE_REQ);
	decon_before[2] = rd32(d + HW_SW_TRIG_CONTROL);
	wr32(d + GLOBAL_CONTROL, decon_before[0] | DECON_EN | DECON_EN_F);
	wr32(d + SHADOW_REG_UPDATE_REQ, rd32(d + SHADOW_REG_UPDATE_REQ) | UPDATE_REQ_GLOBAL);
	uint32_t i;
	for (i = 0; i < 20000 && !(rd32(d + GLOBAL_CONTROL) & RUN_STATUS); i++)
		delay_us(1);
	decon_runwait = i;
	wr32(d + HW_SW_TRIG_CONTROL,
	     (rd32(d + HW_SW_TRIG_CONTROL) & ~HW_TRIG_MASK_DECON) | HW_TRIG_EN);
	decon_after[0] = rd32(d + GLOBAL_CONTROL);
	decon_after[1] = rd32(d + SHADOW_REG_UPDATE_REQ);
	decon_after[2] = rd32(d + HW_SW_TRIG_CONTROL);
}

static unsigned current_el(void)
{
	return (rsr("CurrentEL") >> 2) & 3;
}

void exc_handler(uint64_t slot, uint64_t *regs)
{
	unsigned el = current_el();
	con_clear(BLUE);
	switch (slot & 3) {
	case 0: con_str("PANIC", "SYNC"); break;
	case 1: con_str("PANIC", "IRQ"); break;
	case 2: con_str("PANIC", "FIQ"); break;
	default: con_str("PANIC", "SERROR"); break;
	}
	con_hex2("SLOT", "n=", slot, "el=", el);
	con_hex("MPIDR", rsr("mpidr_el1"));
	con_str("STAGE", stage);
	if (el == 2) {
		con_hex("ESR", rsr("esr_el2"));
		con_hex("ELR", rsr("elr_el2"));
		con_hex("FAR", rsr("far_el2"));
	} else {
		con_hex("ESR", rsr("esr_el1"));
		con_hex("ELR", rsr("elr_el1"));
		con_hex("FAR", rsr("far_el1"));
	}
	con_hex("X0", regs[0]);
	con_hex("X30", regs[31]);	/* stashed lr is just above the 30-reg frame */
	con_skip();
	con_str("EXIT", "hold Power + Vol down");
}

/* ---- A73 ---- */

void secondary_main(uint64_t idx)
{
	sec_el[idx] = current_el();
	sec_midr[idx] = rsr("midr_el1");
	sec_mmfr0[idx] = rsr("id_aa64mmfr0_el1");
	dsb();
	sec_seen[idx] = 1;
	dsb();
	/* Only cpu4 takes over the screen; the others park. */
	if (idx != A73_IDX)
		for (;;)
			__asm__ volatile("wfe");
	/* The A53 hands over the screen, then tries to switch itself off. */
	while (!sec_go_live)
		;
	delay_ms(500);
	for (uint32_t n = 1;; n++) {
		con_set_row(live_row);
		con_hex2("LIVE73", "n=", n, "keys=", (rd32(GPA1_DAT) >> 5) & 7);
		con_set_row(a53_row);
		/* AFFINITY_INFO: 0 on, 1 off, 2 on-pending */
		con_hex2("A53OFF", "ret=", (uint32_t)a53_off_ret,
			 "aff=", (uint32_t)smc(PSCI_AFFINITY_INFO, 0, 0, 0));
		delay_ms(100);
		if (n == 200)
			reset_now();
	}
}

/* ---- main ---- */

static int tg16_ok(uint64_t mmfr0)
{
	unsigned t = (mmfr0 >> 20) & 0xf;
	return t == 1 || t == 2;
}

static void cpu_lines(const char *label, uint64_t el, uint64_t midr, uint64_t mmfr0)
{
	con_hex2(label, "el=", el, "midr=", midr);
	con_hex2(" mmfr0", "lo=", mmfr0, "tg16=", (mmfr0 >> 20) & 0xf);
	con_str(" 16K", tg16_ok(mmfr0) ? "YES" : "NO");
}

void shim_main(uint64_t dtb)
{
	stage = "decon";
	decon_kick();
	stage = "start";
	con_clear(RED);
	con_str("SHIM", "a51 milestone A1d: probe");
	con_skip();

	/* Display question first: if this line moves, the panel follows memory. */
	live_row = con_get_row();
	con_hex2("LIVE", "n=", 0, "keys=", 0);
	con_skip();

	stage = "dtb";
	con_hex2("DECON", "ctl=", decon_before[0], "trig=", decon_before[2]);
	con_hex2(" after", "ctl=", decon_after[0], "trig=", decon_after[2]);
	con_hex2(" wait", "n=", decon_runwait, "upd=", decon_after[1]);
	con_hex2("DTB", "at=", dtb, "magic=", dtb ? __builtin_bswap32(rd32(dtb)) : 0);
	extern char _head[];
	con_hex2("LOAD", "head=", (uintptr_t)_head, "sec=", (uintptr_t)secondary_entry);
	con_hex("CNTFRQ", rsr("cntfrq_el0"));
	con_hex("SCTLR1", rsr("sctlr_el1"));

	stage = "a53";
	uint64_t m0 = rsr("id_aa64mmfr0_el1");
	cpu_lines("A53", current_el(), rsr("midr_el1"), m0);
	con_hex("MPIDR", rsr("mpidr_el1"));
	con_skip();

	stage = "wdt";
	uint32_t w0 = rd32(WDT_CL0), w1 = rd32(WDT_CL1);
	/* WTCON bit 5 = enable, bit 0 = reset on expiry. Stop both like Linux's driver. */
	wr32(WDT_CL0, w0 & ~((1U << 5) | 1U));
	wr32(WDT_CL1, w1 & ~((1U << 5) | 1U));
	con_hex2("WTCON", "cl0=", w0, "cl1=", w1);
	con_hex2(" now", "cl0=", rd32(WDT_CL0), "cl1=", rd32(WDT_CL1));
	con_skip();

	stage = "psci";
	con_hex2("PSCI", "ver=", smc(PSCI_VERSION, 0, 0, 0),
		 "cpuon=", smc(PSCI_FEATURES, PSCI_CPU_ON, 0, 0));
	con_hex2("MIGRATE", "type=", smc(PSCI_MIGRATE_INFO_TYPE, 0, 0, 0),
		 "upcpu=", smc(PSCI_MIGRATE_INFO_UP, 0, 0, 0));
	con_skip();

	/*
	 * cpu1 (A53, same cluster as us), then cpu4 and cpu5 (A73). Each line:
	 * PSCI return, then the MPIDR the core stored at its first instruction
	 * and the x0 it was entered with (0x5A5A... = never arrived).
	 */
	static const uint8_t try_idx[3] = { 1, 4, 5 };
	for (int t = 0; t < 3; t++) {
		unsigned i = try_idx[t];
		uint64_t mpidr = (i & 3) | ((uint64_t)(i >> 2) << 8);
		char label[] = "CPU0";
		label[3] = '0' + i;
		stage = "cpu on";
		sec_marker[i] = sec_ctx[i] = 0x5a5a5a5a;
		dsb();
		int64_t on = smc(PSCI_CPU_ON, mpidr, (uintptr_t)secondary_entry, 0x1000 + i);
		for (int w = 0; w < 300 && !sec_seen[i]; w++)
			delay_ms(10);
		con_hex2(label, "ret=", (uint32_t)on, "seen=", sec_seen[i]);
		con_hex2(" entry", "mpidr=", sec_marker[i], "x0=", sec_ctx[i]);
	}
	if (sec_seen[A73_IDX])
		cpu_lines("A73", sec_el[A73_IDX], sec_midr[A73_IDX], sec_mmfr0[A73_IDX]);
	con_skip();

	stage = "gpio";
	con_hex2("GPA1", "con=", rd32(GPA1_CON), "dat=", rd32(GPA1_DAT));
	con_hex2(" pud", "pud=", rd32(GPA1_PUD), 0, 0);
	con_str("KEYS", "bit5 volup 6 voldn 7 pwr");
	con_skip();
	a53_row = con_get_row();
	con_str("A53OFF", sec_seen[A73_IDX] ? "pending" : "skipped (no A73)");
	con_skip();
	con_str("EXIT", "auto reboot to TWRP ~40s");

	/*
	 * Live loop for ~20 s on the A53, then hand the heartbeat to the A73 and
	 * try PSCI CPU_OFF on the boot A53. If that works the A73 keeps the LIVE
	 * line running and shows AFFINITY_INFO(A53) = 1 (off).
	 */
	stage = "live";
	for (uint32_t n = 1;; n++) {
		con_set_row(live_row);
		con_hex2("LIVE", "n=", n, "keys=", (rd32(GPA1_DAT) >> 5) & 7);
		delay_ms(100);
		if (n == 200) {
			if (!sec_seen[A73_IDX])
				reset_now();
			break;
		}
	}

	stage = "a53 off";
	sec_go_live = 1;
	dsb();
	/* Only returns on failure; the A73 reports either way. */
	a53_off_ret = smc(PSCI_CPU_OFF, 0, 0, 0);
	dsb();
	for (;;)
		__asm__ volatile("wfe");
}
