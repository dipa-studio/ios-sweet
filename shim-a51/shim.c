/*
 * A51 milestone A1: one boot answers the questions that decide the port.
 *   - Does the command-mode panel show what we write to S-Boot's
 *     framebuffer (0xca000000)? A live counter line must keep changing.
 *   - Exception level, MIDR, ID_AA64MMFR0 (TGran16) on the boot A53 and on
 *     an A73 started with PSCI CPU_ON. XNU needs 16K pages.
 *   - PSCI version, trusted-OS migration type, whether the boot A53 may
 *     switch itself off (XNU would then own only the A73 cluster).
 *   - Exynos watchdog state, and the volume/power GPIOs (gpa1 5/6/7).
 * Nothing is written to storage. Leave with a long Power + Volume down.
 */
#include <stdint.h>
#include "console.h"

#define GPA1_CON		0x11850020UL	/* pinctrl@11850000 (ALIVE), bank stride 0x20 (guess) */
#define GPA1_DAT		0x11850024UL
#define WDT_CL0			0x10050000UL	/* WTCON at +0 */
#define WDT_CL1			0x10060000UL

#define PSCI_VERSION		0x84000000UL
#define PSCI_CPU_OFF		0x84000002UL
#define PSCI_CPU_ON		0xc4000003UL
#define PSCI_AFFINITY_INFO	0xc4000004UL
#define PSCI_MIGRATE_INFO_TYPE	0x84000006UL
#define PSCI_MIGRATE_INFO_UP	0xc4000007UL
#define PSCI_FEATURES		0x8400000aUL

#define A73_MPIDR		0x100	/* cpu4, first core of cluster 1 */
#define A73_IDX			4

#define rsr(r) ({ uint64_t _v; __asm__ volatile("mrs %0, " r : "=r"(_v)); _v; })
#define isb() __asm__ volatile("isb" ::: "memory")
#define dsb() __asm__ volatile("dsb sy" ::: "memory")

static inline uint32_t rd32(uintptr_t a) { return *(volatile uint32_t *)a; }
static inline void wr32(uintptr_t a, uint32_t v) { *(volatile uint32_t *)a = v; }

extern char secondary_entry[];

static const char *stage;	/* set at runtime: no absolute pointers in data */

/* Filled by the A73. MMU and caches are off everywhere: plain shared memory. */
static volatile uint64_t sec_seen, sec_el, sec_midr, sec_mmfr0, sec_mpidr;
static volatile uint64_t sec_go_live;
static volatile int live_row, a53_row;
static volatile int64_t a53_off_ret = 0x7777;	/* stays if CPU_OFF never returns */

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
	sec_el = current_el();
	sec_midr = rsr("midr_el1");
	sec_mmfr0 = rsr("id_aa64mmfr0_el1");
	sec_mpidr = rsr("mpidr_el1") | (idx << 56);
	dsb();
	sec_seen = 1;
	dsb();
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
	stage = "start";
	con_clear(RED);
	con_str("SHIM", "a51 milestone A1: probe");
	con_skip();

	/* Display question first: if this line moves, the panel follows memory. */
	live_row = con_get_row();
	con_hex2("LIVE", "n=", 0, "keys=", 0);
	con_skip();

	stage = "dtb";
	con_hex2("DTB", "at=", dtb, "magic=", dtb ? __builtin_bswap32(rd32(dtb)) : 0);
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

	stage = "a73 on";
	int64_t on = smc(PSCI_CPU_ON, A73_MPIDR, (uintptr_t)secondary_entry, A73_IDX);
	for (int i = 0; i < 100 && !sec_seen; i++)
		delay_ms(10);
	con_hex2("CPU_ON", "ret=", (uint32_t)on, "seen=", sec_seen);
	if (sec_seen) {
		cpu_lines("A73", sec_el, sec_midr, sec_mmfr0);
		con_hex("MPIDR", sec_mpidr);
	}
	con_skip();

	stage = "gpio";
	con_hex2("GPA1", "con=", rd32(GPA1_CON), "dat=", rd32(GPA1_DAT));
	con_str("KEYS", "bit5 volup 6 voldn 7 pwr");
	con_skip();
	a53_row = con_get_row();
	con_str("A53OFF", sec_seen ? "pending" : "skipped (no A73)");
	con_skip();
	con_str("EXIT", "hold Power + Vol down");

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
		if (n == 200 && sec_seen)
			break;
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
