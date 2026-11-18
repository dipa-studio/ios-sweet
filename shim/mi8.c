/*
 * Xiaomi Mi 8 (dipper, SDM845) bring-up diagnostic, v2.
 *
 * v1 result (real phone): ABL leaves PP0 in auto-refresh (PP_AUTOREFRESH =
 * 0x80000001, tear check on), so the command-mode AMOLED shows whatever is
 * written into the buffer ABL scans out (0x9d400000, 1080 px stride, red/blue
 * as expected). The manual CTL START kicks in v1 were not needed and the
 * pipeline stopped updating after them. v2 therefore does NOT write any
 * display register: it dumps the pipeline, then cycles colours for ~25 s to
 * show the panel keeps refreshing, then returns (shim.c runs the read-only
 * UFS probe next).
 *
 * Everything is also written to the ramoops console zone (DDR survives a
 * warm reset); readable with root: cat /sys/fs/pstore/console-ramoops*
 *
 * Register offsets follow the Linux SDE driver (msm-4.9 sde_hw_*.c); block
 * bases come from the live FDT. Only reads touch the display block. No
 * absolute pointers in data: ABL runs this image wherever it likes with no
 * relocation pass (see the notes on prz_write and on string tables below).
 */
#include <stdint.h>
#include "board.h"
#include "console.h"
#include "mi8.h"

#ifdef MI8_HOST
#include "mi8_host.h"
#else
#define rsr(r) ({ uint64_t _v; __asm__ volatile("mrs %0, " r : "=r"(_v)); _v; })
static inline uint32_t rd32(uintptr_t a) { return *(volatile uint32_t *)a; }
static inline void wr32(uintptr_t a, uint32_t v) { *(volatile uint32_t *)a = v; }
static inline void wr8(uintptr_t a, uint8_t v) { *(volatile uint8_t *)a = v; }
static inline void dsb(void) { __asm__ volatile("dsb sy" ::: "memory"); }
static inline uint64_t ticks(void) { __asm__ volatile("isb"); return rsr("cntpct_el0"); }
static inline uint64_t tfreq(void) { return rsr("cntfrq_el0"); }
#endif

/* ---- SDM845 display block map (live FDT) ---- */
#define MDP_BASE	0x0ae00000UL
#define CTL_OFF(n)	(0x2000 + (n) * 0x200)		/* qcom,sde-ctl-off */
#define PP_OFF(n)	(0x71000 + (n) * 0x800)		/* qcom,sde-pp-off */
#define INTF_1_OFF	0x6b800				/* DSI0 */
#define INTF_2_OFF	0x6c000				/* DSI1 */
#define DSI0_BASE	0x0ae94000UL

#define CTL_TOP		0x014
#define CTL_FLUSH	0x018
#define CTL_START	0x01c
#define CTL_INTF_ACTIVE	0x0f4
#define CTL_INTF_FLUSH	0x110
#define PP_TEAR_EN	0x000
#define PP_SYNC_VSYNC	0x004
#define PP_SYNC_HEIGHT	0x008
#define PP_LINE_COUNT	0x02c
#define PP_AUTOREFRESH	0x030

#define SSPP_SIZE	0x00
#define SSPP_SRC0_ADDR	0x14
#define SSPP_YSTRIDE0	0x2c
#define SSPP_FORMAT	0x30

/* ramoops@b0000000: 4 MB, record-size 0x40000, console-size 0x40000, ecc off.
 * The ROM kernel (4.9) puts the console zone after the dump records:
 * 4 * 0x40000 = +0x100000. +0x120000 is a hedge for kernels that lay it out
 * as size - console - ftrace - pmsg. */
#define PRZ_A		0xb0100000UL
#define PRZ_B		0xb0120000UL
#define PRZ_SIG		0x43474244U	/* 'DBGC' persistent_ram_buffer.sig */
#define LOG_MAX		7168

#define C_BLUE		0xff0000a0U
#define C_RED		0xffc00000U
#define C_GREEN		0xff006000U
#define C_PURPLE	0xff600080U

/* ---- result lines: filled at runtime, shown on screen and logged ---- */

/* Fixed-size inline text only: no pointer ever lives in data, so the compiler
 * has nothing to turn into an absolute relocation. */
struct line {
	char label[8];
	char an[40];	/* value name, or the whole text for kind 0 */
	char bn[8];
	uint32_t av, bv;
	uint8_t kind;	/* 0 = message, 1 = one or two hex values */
	uint8_t has_b;
};

#define MAXL	80
static struct line L[MAXL];
static int nl;
static char lb[LOG_MAX];
static unsigned ll;

static void cpy(char *dst, const char *src, unsigned max)
{
	unsigned i = 0;

	while (src && src[i] && i < max - 1) {
		dst[i] = src[i];
		i++;
	}
	dst[i] = 0;
}

static struct line *newline(const char *label, int idx)
{
	struct line *l;
	unsigned n;

	if (nl >= MAXL)
		return 0;
	l = &L[nl++];
	cpy(l->label, label, sizeof(l->label));
	if (idx >= 0) {
		for (n = 0; l->label[n]; n++)
			;
		if (n < sizeof(l->label) - 1) {
			l->label[n] = '0' + idx;
			l->label[n + 1] = 0;
		}
	}
	l->an[0] = l->bn[0] = 0;
	l->av = l->bv = 0;
	l->kind = l->has_b = 0;
	return l;
}

static void msg(const char *label, const char *text)
{
	struct line *l = newline(label, -1);

	if (l)
		cpy(l->an, text, sizeof(l->an));
}

/* label with optional trailing digit (idx < 0: none), one or two name=value pairs */
static void pair(const char *label, int idx, const char *an, uint32_t av, const char *bn, uint32_t bv)
{
	struct line *l = newline(label, idx);

	if (!l)
		return;
	cpy(l->an, an, sizeof(l->an));
	l->av = av;
	l->kind = 1;
	if (bn) {
		cpy(l->bn, bn, sizeof(l->bn));
		l->bv = bv;
		l->has_b = 1;
	}
}

static void lc(char c)
{
	if (ll < LOG_MAX - 1)
		lb[ll++] = c;
}

static void ls(const char *s)
{
	while (*s)
		lc(*s++);
}

static void lhex(uint32_t v)
{
	static const char hex[] = "0123456789abcdef";
	for (int i = 28; i >= 0; i -= 4)
		lc(hex[(v >> i) & 0xf]);
}

static void build_log(void)
{
	ll = 0;
	ls("MI8DIAG v1 ");
	ls(BOARD_NAME);
	lc('\n');
	for (int i = 0; i < nl; i++) {
		ls(L[i].label);
		lc(' ');
		ls(L[i].an);
		if (L[i].kind) {
			lhex(L[i].av);
			if (L[i].has_b) {
				lc(' ');
				ls(L[i].bn);
				lhex(L[i].bv);
			}
		}
		lc('\n');
	}
}

/* struct persistent_ram_buffer { u32 sig; u32 start; u32 size; u8 data[]; }
 * noinline/noclone + the empty asm keep `zone` a runtime value: if the compiler
 * knows it is a constant it folds "lb - zone" into a 64-bit constant-pool entry,
 * i.e. an absolute relocation, which this image cannot have. */
static void __attribute__((noinline, noclone)) prz_write(uintptr_t zone)
{
	__asm__ volatile("" : "+r"(zone));
	for (unsigned i = 0; i < ll; i++)
		wr8(zone + 12 + i, (uint8_t)lb[i]);
	wr32(zone + 4, 0);
	wr32(zone + 8, ll);
	wr32(zone + 0, PRZ_SIG);
}

static void flush_log(void)
{
	build_log();
	prz_write(PRZ_A);
	prz_write(PRZ_B);
	dsb();
}

/* ---- display ---- */

static void delay_ms(unsigned ms)
{
	uint64_t end = ticks() + tfreq() / 1000 * ms;

	while (ticks() < end)
		;
}

static void render(uint32_t bg, const char *title)
{
	con_clear(bg);
	con_str("MI8", title);
	for (int i = 0; i < nl; i++) {
		if (L[i].kind == 0)
			con_str(L[i].label, L[i].an);
		else
			con_hex2(L[i].label, L[i].an, L[i].av, L[i].has_b ? L[i].bn : 0, L[i].bv);
	}
	dsb();
}

static void scan_pipes(uint32_t *fb_addr, uint32_t *fb_stride)
{
	static const uint32_t sspp_off[8] = {
		0x5000, 0x7000, 0x9000, 0xb000, 0x25000, 0x27000, 0x29000, 0x2b000,
	};
	int active = 0;

	*fb_addr = 0;
	*fb_stride = 0;
	for (int i = 0; i < 8; i++) {
		uintptr_t b = MDP_BASE + sspp_off[i];
		uint32_t addr = rd32(b + SSPP_SRC0_ADDR);

		if (!addr)
			continue;
		active++;
		uint32_t ys = rd32(b + SSPP_YSTRIDE0);
		pair("SSPP", i, "addr=", addr, "ystr=", ys);
		pair(" fmt", -1, "fmt=", rd32(b + SSPP_FORMAT), "size=", rd32(b + SSPP_SIZE));
		if (!*fb_addr && addr >= 0x80000000U) {
			*fb_addr = addr;
			*fb_stride = ys & 0xffff;
		}
	}
	pair("SSPPs", -1, "active=", active, 0, 0);
}

static int tick_i = -1;

static void tick(uint32_t n)
{
	if (tick_i >= 0 && tick_i < nl) {
		L[tick_i].av = rd32(MDP_BASE + PP_OFF(0) + PP_LINE_COUNT);
		L[tick_i].bv = n;
	}
}

void mi8_diag(uintptr_t dtb)
{
	uint32_t fb_addr, fb_stride;

	nl = 0;
	msg("BOARD", BOARD_NAME);
	pair("CPU", -1, "midr=", (uint32_t)rsr("midr_el1"), "mpidr=", (uint32_t)rsr("mpidr_el1"));
	pair("MMFR0", -1, "tg16=", (rsr("id_aa64mmfr0_el1") >> 20) & 0xf, "parng=", rsr("id_aa64mmfr0_el1") & 0xf);
	pair("EL", -1, "cur=", (uint32_t)(rsr("currentel") >> 2), "sctlr=", (uint32_t)rsr("sctlr_el1"));
	pair("DTB", -1, "at=", (uint32_t)dtb, "magic=", dtb ? __builtin_bswap32(rd32(dtb)) : 0);
	flush_log();	/* first thing: proves ramoops works even if MDSS reads hang */

	pair("MDP", -1, "rev=", rd32(MDP_BASE), 0, 0);
	flush_log();

	scan_pipes(&fb_addr, &fb_stride);
	if (fb_addr) {
		con_fb = (volatile uint32_t *)(uintptr_t)fb_addr;
		if (fb_stride && !(fb_stride & 3) && fb_stride <= 16384)
			con_stride4 = fb_stride / 4;
		if (fb_addr != FB_BASE)
			msg("FB", "ABL buffer is not cont_splash base");
	} else {
		msg("FB", "no active SSPP: splash off?");
	}
	pair("FBUSE", -1, "base=", (uint32_t)(uintptr_t)con_fb, "str4=", con_stride4);
	flush_log();

	for (int i = 0; i < 2; i++) {
		uintptr_t c = MDP_BASE + CTL_OFF(i);

		pair("CTL", i, "top=", rd32(c + CTL_TOP), "flush=", rd32(c + CTL_FLUSH));
		pair(" ", -1, "start=", rd32(c + CTL_START), "intfa=", rd32(c + CTL_INTF_ACTIVE));
	}
	flush_log();

	for (int i = 0; i < 2; i++) {
		uintptr_t p = MDP_BASE + PP_OFF(i);

		pair("PP", i, "tear=", rd32(p + PP_TEAR_EN), "vsync=", rd32(p + PP_SYNC_VSYNC));
		pair(" ", -1, "hght=", rd32(p + PP_SYNC_HEIGHT), "auto=", rd32(p + PP_AUTOREFRESH));
	}
	flush_log();

	pair("INTF", 1, "en=", rd32(MDP_BASE + INTF_1_OFF), "cfg=", rd32(MDP_BASE + INTF_1_OFF + 4));
	pair("INTF", 2, "en=", rd32(MDP_BASE + INTF_2_OFF), "cfg=", rd32(MDP_BASE + INTF_2_OFF + 4));
	pair("DSI0", -1, "ctrl=", rd32(DSI0_BASE + 4), 0, 0);
	flush_log();

	/* No display register is written from here on. A live counter line shows the
	 * pipeline is ticking. Straight-line code on purpose: a switch over colour
	 * names would become a table of string pointers (absolute relocations). */
	tick_i = nl;
	pair("PP0C", -1, "cnt=", 0, "n=", 0);
	flush_log();
	for (uint32_t round = 0; round < 1; round++) {
		tick(round * 4 + 0);
		render(C_BLUE, "cycle BLUE (no display writes)");
		delay_ms(3000);
		tick(round * 4 + 1);
		render(C_RED, "cycle RED (no display writes)");
		delay_ms(3000);
		tick(round * 4 + 2);
		render(C_GREEN, "cycle GREEN (no display writes)");
		delay_ms(3000);
		tick(round * 4 + 3);
		render(C_PURPLE, "cycle PURPLE (no display writes)");
		delay_ms(3000);
	}
	flush_log();
}

/* ---- touch bring-up probe (v6/v7): GPIO bit-banged I2C ----
 * v5 result on a real phone: SE6 = global SE14 (DT: i2c@a98000, pins gpio33/gpio34 function qup14, dmas present). Its
 * FIFO interface is disabled (the SE is GSI/DMA-only), so sweet's FIFO-mode driver cannot be used: sweet's own check
 * (SE_FIFO_IF_DISABLE_RO 0x64 bit0) rejected it (SEINIT rc=1). Same situation the LG V60 port hit; its answer was to
 * bit-bang the bus. So v6 touches no GCC or SE register at all: TLMM only.
 *   gpio33/34 = I2C pins (which one is SDA is not certain: both orders are tried), gpio31 = irq, gpio32 = reset,
 *   all in the TLMM north tile (0x3900000, cfg at pin*0x1000, io at +4: bit0 in, bit1 out value, cfg bit9 = output
 *   enable, bits[1:0] pull, bits[5:2] function, bits[8:6] drive). Open drain: drive low = latch 0 + output enable,
 *   release = output disable with pull-up. Touch rails (pm8998_l28 via RPMh) are NOT touched: an unpowered chip
 *   NACKs, a powered one ACKs and then returns its info block. */
#define TLMM_NORTH	0x03900000UL

static void memset_b(uint8_t *p, uint8_t v, unsigned n)
{
	while (n--)
		*p++ = v;
}

static void delay_us(unsigned us)
{
	uint64_t end = ticks() + tfreq() / 1000000 * us;

	while (ticks() < end)
		;
}

static uintptr_t pin_cfg(unsigned pin)
{
	return TLMM_NORTH + pin * 0x1000U;
}

/* sweet touch_gpio() */
static void touch_gpio(unsigned pin, unsigned mux, unsigned pull, unsigned drive, int out)
{
	uintptr_t off = pin_cfg(pin);
	uint32_t cfg = rd32(off);

	if (out)
		wr32(off + 4, rd32(off + 4) | 2U);	/* latch high before enabling the output: no reset pulse */
	cfg &= ~0x3ffU;
	cfg |= (mux << 2) | pull | (drive << 6) | (out ? 0x200U : 0U);
	wr32(off, cfg);
}

static unsigned bb_sda, bb_scl;

static void line_low(unsigned pin)
{
	uintptr_t off = pin_cfg(pin);

	wr32(off + 4, rd32(off + 4) & ~2U);
	wr32(off, rd32(off) | 0x200U);
}

static void line_rel(unsigned pin)
{
	uintptr_t off = pin_cfg(pin);

	wr32(off, rd32(off) & ~0x200U);
}

static int line_get(unsigned pin)
{
	return (int)(rd32(pin_cfg(pin) + 4) & 1U);
}

/* release SCL and wait for it to go high (clock stretching); 0 = ok, 1 = stuck low */
static int scl_high(void)
{
	line_rel(bb_scl);
	for (unsigned i = 0; i < 2000; i++) {
		if (line_get(bb_scl))
			return 0;
		delay_us(1);
	}
	return 1;
}

static void bb_setup(unsigned sda, unsigned scl)
{
	bb_sda = sda;
	bb_scl = scl;
	touch_gpio(sda, 0, 3, 1, 0);	/* GPIO function, pull-up, 4 mA, input (released) */
	touch_gpio(scl, 0, 3, 1, 0);
	delay_us(50);
}

static int bb_start(void)
{
	if (scl_high() || !line_get(bb_sda))
		return 1;
	delay_us(5);
	line_low(bb_sda);
	delay_us(5);
	line_low(bb_scl);
	delay_us(5);
	return 0;
}

static void bb_stop(void)
{
	line_low(bb_sda);
	delay_us(5);
	scl_high();
	delay_us(5);
	line_rel(bb_sda);
	delay_us(10);
}

/* write one byte, return the ACK bit (0 = ACK) or 2 on a stuck clock */
static int bb_wbyte(uint8_t v)
{
	int ack;

	for (int i = 7; i >= 0; i--) {
		if ((v >> i) & 1)
			line_rel(bb_sda);
		else
			line_low(bb_sda);
		delay_us(3);
		if (scl_high())
			return 2;
		delay_us(5);
		line_low(bb_scl);
		delay_us(3);
	}
	line_rel(bb_sda);
	delay_us(3);
	if (scl_high())
		return 2;
	delay_us(3);
	ack = line_get(bb_sda);
	delay_us(2);
	line_low(bb_scl);
	delay_us(3);
	return ack;
}

static uint8_t bb_rbyte(int ack)
{
	uint8_t v = 0;

	line_rel(bb_sda);
	for (int i = 0; i < 8; i++) {
		delay_us(3);
		scl_high();
		delay_us(3);
		v = (uint8_t)((v << 1) | (unsigned)line_get(bb_sda));
		delay_us(2);
		line_low(bb_scl);
	}
	if (ack)
		line_low(bb_sda);
	else
		line_rel(bb_sda);
	delay_us(3);
	scl_high();
	delay_us(5);
	line_low(bb_scl);
	delay_us(3);
	line_rel(bb_sda);
	return v;
}

/* ---- RPMh client for ONE resource (port of sweet_rpmh.c, SM7150 -> SDM845) ----
 * apps_rsc DRV2 @ 0x179e0000, TCS bank @ 0x179e0d00 (DT: qcom,drv-id 2, tcs-config ACTIVE 2 / SLEEP 3 / WAKE 3 / CONTROL 1,
 * same layout as sweet). cmd-db locator 0x0c3f000c as on sweet; the db itself is at 0x85fe0000 on this phone.
 * Used for pm8998_l28 ("ldoa28", pmic4-ldo, the touch avdd rail): voltage, mode HPM, enable, ACTIVE set only.
 * Conservative like the original: refuses on any unexpected register state, never retries. */
#define RH_RSC		0x179e0000UL
#define RH_TCS		0x179e0d00UL
#define RH_DICT		0x0c3f000cUL
#define RH_DRV		2U
#define RH_TCS_SIZE	0x3000U
#define RH_ACTIVE_N	2U
#define RH_NORMAL_N	8U
#define RH_STRIDE	0x2a0U
#define RH_CMDSTR	0x14U
#define RH_IRQ_EN	0x00U
#define RH_IRQ_ST	0x04U
#define RH_IRQ_CLR	0x08U
#define RH_WAIT		0x10U
#define RH_CONTROL	0x14U
#define RH_STATUS	0x18U
#define RH_ENABLE	0x1cU
#define RH_MSGID	0x30U
#define RH_ADDR		0x34U
#define RH_DATA		0x38U
#define RH_CMDST	0x3cU
#define RH_AMC_EN	(1U << 16)
#define RH_TRIGGER	(1U << 24)
#define RH_ISSUED	(1U << 8)
#define RH_COMPLETE	(1U << 16)
#define RH_WRITE_ACK	(8U | (1U << 8) | (1U << 16))
#define RH_DB_MAGIC	0x0c0330dbU
#define RH_DB_HEADER	144U
#define RH_DB_ENTRY	24U
#define RH_VRM		4U

static uintptr_t rh_db;
static uint32_t rh_db_size;
static unsigned rh_ncpt;

static void rh_w(uint32_t off, uint32_t v)
{
	wr32(RH_TCS + off, v);
	dsb();
}

static int rh_sync(uint32_t off, uint32_t v)
{
	rh_w(off, v);
	for (unsigned i = 0; i < 1000; i++) {
		if (rd32(RH_TCS + off) == v)
			return 1;
		delay_us(1);
	}
	return 0;
}

static unsigned rh_db16(uint32_t off)
{
	return (unsigned)((rd32(rh_db + (off & ~3U)) >> (8U * (off & 3U))) & 0xffffU);
}

static int rh_range(uint32_t off, uint32_t size)
{
	return off <= rh_db_size && size <= rh_db_size - off;
}

/* 0 ok, 1 RSC geometry/revision unsupported, 2 cmd-db locator, 3 cmd-db header */
static int rh_map(void)
{
	uint32_t id = rd32(RH_RSC), solver = rd32(RH_RSC + 4), config = rd32(RH_RSC + 0x0c);
	unsigned major = (id >> 16) & 0xffU, count = (config >> (6U * RH_DRV)) & 0x3fU;
	uint32_t pa, size;

	rh_ncpt = (config >> 27) & 0x1fU;
	pair("RSC", -1, "id=", id, "cfg=", config);
	if ((major != 1 && major != 2) || config == 0xffffffffU || solver == 0xffffffffU || count < RH_NORMAL_N ||
	    count > RH_TCS_SIZE / RH_STRIDE || rh_ncpt < 3 || rh_ncpt > 16)
		return 1;
	pa = rd32(RH_DICT);
	size = rd32(RH_DICT + 4);
	pair("CMDDB", -1, "pa=", pa, "size=", size);
	if (pa < 0x80000000U || (pa & 3U) || (size & 3U) || size < RH_DB_HEADER || size > 0x100000U ||
	    (uint64_t)pa + size > 0x100000000ULL)
		return 2;
	rh_db = pa;
	rh_db_size = size;
	pair(" ", -1, "ver=", rd32(rh_db), "magic=", rd32(rh_db + 4));
	if (rd32(rh_db + 4) != RH_DB_MAGIC || rd32(rh_db) != 1U || (rd32(rh_db + 140) & 1U))
		return 3;
	return 0;
}

/* resource name "ldoa28": 0 ok (address in *address), 4 malformed db, 5 not exactly one match / bad VRM entry */
static int rh_lookup(uint32_t k0, uint32_t k1, uint32_t *address)
{
	unsigned matches = 0;

	for (unsigned i = 0; i < 8; i++) {
		uint32_t h = 8U + 16U * i;
		unsigned slave = rh_db16(h);
		uint32_t entries, aux;
		unsigned count;

		if (!slave)
			break;
		entries = RH_DB_HEADER + rh_db16(h + 2);
		aux = RH_DB_HEADER + rh_db16(h + 4);
		count = rh_db16(h + 6);
		if (slave < 3 || slave > 5 || (entries & 3U) || !rh_range(entries, count * RH_DB_ENTRY) || !rh_range(aux, 0))
			return 4;
		for (unsigned j = 0; j < count; j++) {
			uint32_t e = entries + RH_DB_ENTRY * j, addr;

			if (rd32(rh_db + e) != k0 || rd32(rh_db + e + 4) != k1)
				continue;
			addr = rd32(rh_db + e + 16);
			if (slave != RH_VRM || (addr >> 16) != RH_VRM || (addr & 15U) ||
			    !rh_range(aux + rh_db16(e + 22), rh_db16(e + 20)))
				return 5;
			*address = addr;
			matches++;
		}
	}
	return matches == 1 ? 0 : 5;
}

static int rh_free(unsigned t)
{
	uint32_t b = t * RH_STRIDE;

	return rd32(RH_TCS + b + RH_STATUS) != 0 && rd32(RH_TCS + b + RH_STATUS) != 0xffffffffU &&
	       rd32(RH_TCS + b + RH_CONTROL) == 0 && rd32(RH_TCS + b + RH_ENABLE) == 0 &&
	       rd32(RH_TCS + b + RH_WAIT) == 0 && !(rd32(RH_TCS + RH_IRQ_ST) & (1U << t));
}

/* 0 ok, 6 inherited state/conflict/no free ACTIVE TCS, 7 register readback, 8 vote timeout (TCS left quarantined) */
static int rh_send(uint32_t address, unsigned mv)
{
	static const uint32_t offsets[3] = { 0, 8, 4 };	/* voltage, mode, enable (enable last) */
	uint32_t values[3];
	int chosen = -1;
	uint32_t irq_en, b, bit;
	unsigned t;

	values[0] = mv;
	values[1] = 7;	/* HPM */
	values[2] = 1;
	for (unsigned i = 0; i < RH_ACTIVE_N; i++) {
		uint32_t bb = i * RH_STRIDE, enabled = rd32(RH_TCS + bb + RH_ENABLE);

		if (enabled & ~((1U << rh_ncpt) - 1U))
			return 6;
		for (unsigned c = 0; c < rh_ncpt; c++)
			if ((enabled & (1U << c)) && (rd32(RH_TCS + bb + RH_ADDR + c * RH_CMDSTR) & ~15U) == address)
				return 6;
		if (chosen < 0 && rh_free(i))
			chosen = (int)i;
	}
	if (chosen < 0)
		return 6;
	t = (unsigned)chosen;
	b = t * RH_STRIDE;
	bit = 1U << t;
	irq_en = rd32(RH_TCS + RH_IRQ_EN);
	if (irq_en == 0xffffffffU || !rh_free(t))
		return 6;
	if (!rh_sync(RH_IRQ_EN, irq_en & ~bit))
		return 7;
	if (!rh_free(t)) {
		rh_sync(RH_IRQ_EN, (rd32(RH_TCS + RH_IRQ_EN) & ~bit) | (irq_en & bit));
		return 6;
	}
	for (unsigned c = 0; c < 3; c++) {
		uint32_t cmd = b + c * RH_CMDSTR;

		if (!rh_sync(cmd + RH_MSGID, RH_WRITE_ACK) || !rh_sync(cmd + RH_ADDR, address + offsets[c]) ||
		    !rh_sync(cmd + RH_DATA, values[c]))
			return 7;
	}
	if (!rh_sync(b + RH_WAIT, 7) || !rh_sync(b + RH_ENABLE, 7) || !rh_sync(b + RH_CONTROL, 0) ||
	    !rh_sync(b + RH_CONTROL, RH_AMC_EN))
		return 7;
	rh_w(b + RH_CONTROL, RH_AMC_EN | RH_TRIGGER);
	{
		int done = 0, progress = 0;
		uint32_t irq = 0, idle = 0, st[3] = { 0, 0, 0 };

		for (unsigned us = 0; us < 100000U; us++) {
			int complete = 1;

			irq = rd32(RH_TCS + RH_IRQ_ST);
			idle = rd32(RH_TCS + b + RH_STATUS);
			for (unsigned c = 0; c < 3; c++) {
				st[c] = rd32(RH_TCS + b + RH_CMDST + c * RH_CMDSTR);
				complete &= st[c] != 0xffffffffU && (st[c] & (RH_ISSUED | RH_COMPLETE)) == (RH_ISSUED | RH_COMPLETE);
			}
			progress |= idle == 0 || !complete;
			if (idle && idle != 0xffffffffU && irq != 0xffffffffU && ((irq & bit) || progress) && complete) {
				done = 1;
				break;
			}
			delay_us(1);
		}
		pair("RHTCS", (int)t, "idle=", idle, "irq=", irq);
		pair(" ", -1, "st0=", st[0], "st1=", st[1]);
		if (!done)
			return 8;
	}
	if (!rh_sync(b + RH_CONTROL, RH_AMC_EN) || !rh_sync(b + RH_CONTROL, 0) || !rh_sync(b + RH_ENABLE, 0) ||
	    !rh_sync(b + RH_WAIT, 0))
		return 7;
	rh_w(RH_IRQ_CLR, bit);	/* write-1-to-clear: only our TCS */
	if ((rd32(RH_TCS + RH_IRQ_ST) & bit) || !rh_sync(RH_IRQ_EN, (rd32(RH_TCS + RH_IRQ_EN) & ~bit) | (irq_en & bit)))
		return 7;
	return 0;
}

/* pm8998_l28 "ldoa28" at 3.3 V; returns 0 on success, otherwise a code (see the helpers above) */
static int rh_enable_l28(void)
{
	uint32_t address = 0;
	int rc = rh_map();

	if (!rc)
		rc = rh_lookup(0x616f646cU, 0x00003832U, &address);	/* "ldoa28\0\0" */
	if (!rc) {
		pair("L28", -1, "addr=", address, 0, 0);
		rc = rh_send(address, 3300);
	}
	return rc;
}

/* TLMM tiles on this SoC family: north 0x3900000 (holds gpio31-34), south 0x3d00000, west 0x3500000. The right tile for a
 * pin is the one where its neighbours read non-zero (an unmapped tile reads 0). */
static uintptr_t find_pin(unsigned pin)
{
	static const uint32_t tile_off[3] = { 0x03900000U, 0x03d00000U, 0x03500000U };

	for (int i = 0; i < 3; i++) {
		uintptr_t base = tile_off[i];
		uint32_t me = rd32(base + pin * 0x1000U), lo = rd32(base + (pin - 1) * 0x1000U),
			 hi = rd32(base + (pin + 1) * 0x1000U);

		pair("TILE", i, "p23=", me, "p22=", lo);
		pair(" ", -1, "p24=", hi, 0, 0);
		if (lo | hi)
			return base + pin * 0x1000U;
	}
	return TLMM_NORTH + pin * 0x1000U;
}

/* disp_vddio_vreg (touch vdd, 1.8 V) is a fixed regulator enabled by GPIO23, active high, startup delay 4 ms.
 * Drive it high if the pin answers (output high reads 1, output low reads 0), else restore it. 1 = enabled. */
static int vddio_enable(void)
{
	uintptr_t off = find_pin(23);
	uint32_t cfg = rd32(off), io = rd32(off + 4), hi, lo;

	wr32(off + 4, io | 2U);
	wr32(off, (cfg & ~0x3ffU) | 0x200U | (1U << 6));	/* gpio, no pull, 4 mA, output */
	delay_us(50);
	hi = rd32(off + 4) & 1U;
	wr32(off + 4, rd32(off + 4) & ~2U);
	delay_us(50);
	lo = rd32(off + 4) & 1U;
	pair("V23", -1, "hi=", hi, "lo=", lo);
	if (hi == 1U && lo == 0U) {
		wr32(off + 4, rd32(off + 4) | 2U);
		delay_ms(10);
		pair(" ", -1, "cfg=", rd32(off), "io=", rd32(off + 4));
		return 1;
	}
	wr32(off + 4, io);
	wr32(off, cfg);
	return 0;
}

/* write nw bytes (may be 0), then if nr: repeated start + read nr bytes. 0 ok, 1 NACK, 2 stuck */
static int bb_xfer(uint8_t addr, const uint8_t *w, unsigned nw, uint8_t *r, unsigned nr)
{
	int a;

	if (bb_start())
		return 2;
	a = bb_wbyte((uint8_t)(addr << 1));
	for (unsigned i = 0; !a && i < nw; i++)
		a = bb_wbyte(w[i]);
	if (a) {
		bb_stop();
		return a == 2 ? 2 : 1;
	}
	if (nr) {
		line_rel(bb_sda);
		delay_us(5);
		if (bb_start()) {
			bb_stop();
			return 2;
		}
		a = bb_wbyte((uint8_t)((addr << 1) | 1));
		if (a) {
			bb_stop();
			return a == 2 ? 2 : 1;
		}
		for (unsigned i = 0; i < nr; i++)
			r[i] = bb_rbyte(i + 1 < nr);
	}
	bb_stop();
	return 0;
}

static uint32_t le32(const uint8_t *b)
{
	return (uint32_t)b[0] | ((uint32_t)b[1] << 8) | ((uint32_t)b[2] << 16) | ((uint32_t)b[3] << 24);
}

#define FTS_ADDR	0x49
#define EV_LINES	5
static int ev_i = -1, xy_i = -1, raw_i = -1;

/* STM FTS5 event: 8 bytes. id 0x13 enter / 0x23 motion / 0x33 leave (touch), 0x03 controller ready, 0x00 none.
 * Position as in ST's fts5 driver (unverified for this chip): x = (b3 & 0x0f) << 8 | b2, y = b4 << 4 | b3 >> 4. */
static void fts_show_event(const uint8_t *e, unsigned n)
{
	if (ev_i < 0)
		return;
	for (int k = EV_LINES - 1; k > 0; k--) {
		L[ev_i + k].av = L[ev_i + k - 1].av;
		L[ev_i + k].bv = L[ev_i + k - 1].bv;
	}
	L[ev_i].av = le32(e);
	L[ev_i].bv = le32(e + 4);
	if (xy_i >= 0 && (e[0] == 0x13 || e[0] == 0x23 || e[0] == 0x33)) {
		L[xy_i].av = ((uint32_t)(e[3] & 0x0fU) << 8) | e[2];
		L[xy_i].bv = ((uint32_t)e[4] << 4) | (e[3] >> 4);
	}
	L[xy_i + 1].av = n;
}

static unsigned ok85, bad85, ok86, bad86, nz85, nz86, hi_after;
static int st_i = -1;

static void st_update(unsigned irq_low, unsigned polls)
{
	if (st_i < 0)
		return;
	L[st_i].av = ok85;	L[st_i].bv = bad85;
	L[st_i + 1].av = ok86;	L[st_i + 1].bv = bad86;
	L[st_i + 2].av = nz85;	L[st_i + 2].bv = nz86;
	L[st_i + 3].av = hi_after;	L[st_i + 3].bv = irq_low;
	L[st_i + 4].av = polls;
}

static int win_i = -1;
static uint32_t pt_x[2], pt_y[2];
static int pt_next, pt_valid;
static uint8_t cmd_scan[3];

static void draw_pts(void)
{
	for (int k = 0; k < 2; k++) {
		int slot = (pt_next + k) & 1;	/* k = 0 is the older one, k = 1 the newest */
		uint32_t color = k ? 0xffffffffU : 0xffffff00U;

		if (!(pt_valid & (1 << slot)))
			continue;
		for (int dy = -14; dy <= 14; dy++) {
			for (int dx = -14; dx <= 14; dx++) {
				int px = (int)pt_x[slot] + dx, py = (int)pt_y[slot] + dy;

				if (px >= 0 && px < FB_W && py >= 0 && py < FB_H)
					con_fb[(unsigned)py * con_stride4 + (unsigned)px] = color;
			}
		}
	}
	dsb();
}

static void win_event(int w, const uint8_t *e)
{
	int base = win_i + w * 3;
	uint32_t x = ((uint32_t)(e[3] & 0x0fU) << 8) | e[2], y = ((uint32_t)e[4] << 4) | (e[3] >> 4), z = e[5];

	L[base].av++;
	if (z > L[base].bv)
		L[base].bv = z;
	if (x < L[base + 1].av)
		L[base + 1].av = x;
	if (x > L[base + 1].bv)
		L[base + 1].bv = x;
	if (y < L[base + 2].av)
		L[base + 2].av = y;
	if (y > L[base + 2].bv)
		L[base + 2].bv = y;
	pt_x[pt_next] = x;
	pt_y[pt_next] = y;
	pt_valid |= 1 << pt_next;
	pt_next ^= 1;
}

/* ST fts_interrupt_handler(): read one event with FIFO_CMD_READALL (0x86); byte 7 & 0x1f = events still queued; read those
 * with a second 0x86 of 8*remaining bytes. Returns the number of events in buf (8 bytes each, up to 32), 0 if empty,
 * 0xffffffff if the first transfer failed. *rem_out = events that were queued behind the first one. */
static unsigned fts_read_fifo(uint8_t *buf, unsigned *rem_out)
{
	uint8_t cmd = 0x86;
	unsigned n = 1, rem;

	if (bb_xfer(FTS_ADDR, &cmd, 1, buf, 8))
		return 0xffffffffU;
	*rem_out = 0;
	if (!buf[0])
		return 0;
	rem = buf[7] & 0x1fU;
	if (rem > 31)
		rem = 31;
	*rem_out = rem;
	if (rem) {
		if (bb_xfer(FTS_ADDR, &cmd, 1, buf + 8, 8 * rem))
			return n;
		n += rem;
	}
	return n;
}

static uint8_t fifo_buf[256];
static unsigned rem_max, rem_last, stat_n;
static int stat_i = -1;

static void note_status(const uint8_t *e)
{
	stat_n++;
	if (stat_i >= 0) {
		L[stat_i].av = le32(e);
		L[stat_i].bv = le32(e + 4);
		L[stat_i + 1].av = stat_n;
	}
}

/* run for ms milliseconds; count touch-type events (0x13/0x23/0x33) and note status events; returns the count */
static unsigned count_touch_events(unsigned ms)
{
	unsigned total = 0;

	for (unsigned t = 0; t < ms / 20U; t++) {
		if (!line_get(31)) {
			unsigned rem = 0, n = fts_read_fifo(fifo_buf, &rem);

			if (n != 0xffffffffU) {
				rem_last = rem;
				if (rem > rem_max)
					rem_max = rem;
				for (unsigned k = 0; k < n; k++) {
					uint8_t id = fifo_buf[8 * k];

					if (id == 0x13 || id == 0x23 || id == 0x33)
						total++;
					else if (id == 0x43)
						note_status(fifo_buf + 8 * k);
				}
			}
		}
		delay_ms(20);
	}
	return total;
}

#ifdef MI8_FTS_FW
/* ---- ST FTM5 firmware burn (port of fts_lib/ftsFlash.c: flash_burn / fillFlash, Google fts_touch tree) ----
 * The stock Mi 8 log shows the ROM driver doing this on every boot (about 5 s: "load program DONE!", "load config DONE!"):
 * the chip comes up with FW 0x54 / config 0x24 and the driver burns the ROM's st_fts_e1.ftb (FW 0x51, config 0x21, sec0 94376
 * bytes, sec1 2656 bytes, no CX). Without it the chip reports ghost touches. The file is embedded at build time
 * (mi8/fw/st_fts_e1.ftb, see mi8/README.md). Same sequence as ST's library, keep_cx = 1 (panel init + CX pages are not
 * erased: the stock log shows CX VER FFFF both before and after, nothing to lose). FLASH_CHUNK is 32 KB (ST uses 32 or 64 KB per
 * DMA round depending on the part; smaller is always valid). If anything fails the stock driver simply burns again at the next
 * Android boot, which it already does on every boot. */
extern const uint8_t fts_fw_start[], fts_fw_end[];

#define FLASH_CHUNK	(32U * 1024U)
#define DMA_CHUNK	32U
#define FLASH_RETRY	200U
#define FLASH_WAIT_MS	50U

struct ftsfw {
	uint32_t fw_ver, cfg_ver, sec0, sec1, sec2, sec3, code_addr, cfg_addr;
	const uint8_t *data;
};

static int bn_i = -1;

static void bn_step(uint32_t step, uint32_t a, uint32_t b, const char *title)
{
	if (bn_i >= 0) {
		L[bn_i].av = step;
		L[bn_i].bv = a;
		L[bn_i + 1].av = b;
	}
	render(C_RED, title);
	flush_log();
}

/* parseBinFile(): 0 ok, else the failing check */
static int fts_parse(const uint8_t *f, uint32_t size, struct ftsfw *o)
{
	uint32_t dim, pg_code, pg_panel, pg_cx, pg_cfg;

	o->fw_ver = o->cfg_ver = 0;
	o->sec0 = o->sec1 = o->sec2 = o->sec3 = 0;
	o->code_addr = o->cfg_addr = 0;
	o->data = 0;
	if (size < 68)
		return 1;
	if (le32(f) != 0xAA55AA55U)
		return 2;
	if (le32(f + 4) != 1U)
		return 3;
	if (f[8] != 0x36 || f[9] != 0x39)	/* DCHIP_ID_0/1 for FTM5 */
		return 4;
	o->fw_ver = le32(f + 16);
	o->cfg_ver = le32(f + 24);
	o->sec0 = le32(f + 44);
	o->sec1 = le32(f + 48);
	o->sec2 = le32(f + 52);
	o->sec3 = le32(f + 56);
	dim = o->sec0 + o->sec1 + o->sec2 + o->sec3;
	if (dim + 64U + 4U != size || size < 284)
		return 5;
	o->data = f + 64;
	pg_code = f[280];
	pg_panel = f[281];
	pg_cx = f[282];
	pg_cfg = f[283];
	o->code_addr = 0x00000000U;
	if (!pg_code || !pg_panel || !pg_cx || !pg_cfg) {
		o->cfg_addr = 0x00007C00U;
	} else {
		o->cfg_addr = ((pg_code + pg_panel + pg_cx) * 4096U) / 4U;
	}
	return 0;
}

static int fts_w6(uint8_t a, uint8_t d)
{
	uint8_t b[6];

	b[0] = 0xfa; b[1] = 0x20; b[2] = 0x00; b[3] = 0x00; b[4] = a; b[5] = d;
	return bb_xfer(FTS_ADDR, b, 6, 0, 0);
}

/* 0 ready, 1 timeout/bus error */
static int fts_wait_flash(uint8_t type)
{
	uint8_t cmd[5], rd[2];

	cmd[0] = 0xfa; cmd[1] = 0x20; cmd[2] = 0x00; cmd[3] = 0x00; cmd[4] = type;
	for (unsigned i = 0; i < FLASH_RETRY; i++) {
		rd[0] = 0x80;
		if (!bb_xfer(FTS_ADDR, cmd, 5, rd, 2) && !(rd[0] & 0x80))
			return 0;
		delay_ms(FLASH_WAIT_MS);
	}
	return 1;
}

static int fts_dma_start(void)
{
	static const uint8_t cmd[12] = { 0xfa, 0x20, 0x00, 0x00, 0x6b, 0x00, 0x40, 0x42, 0x0f, 0x00, 0x00, 0xc0 };

	if (bb_xfer(FTS_ADDR, cmd, 12, 0, 0))
		return 1;
	return fts_wait_flash(0x71);
}

/* fillFlash(): stage 32-byte pieces in RAM at 0x00100000, then DMA them into flash at `address` (word address) */
static int fts_fill(uint32_t address, const uint8_t *data, uint32_t size, uint32_t *done_total, uint32_t total)
{
	uint32_t remaining = size, wheel = 0;
	uint8_t buf[5 + DMA_CHUNK], cfg[12];

	while (remaining > 0) {
		uint32_t block = 0, addr = 0x00100000U, words, a;

		while (block < FLASH_CHUNK && remaining > 0) {
			uint32_t n = remaining >= DMA_CHUNK ? DMA_CHUNK : remaining;

			if (block + n > FLASH_CHUNK)
				n = FLASH_CHUNK - block;
			buf[0] = 0xfa;
			buf[1] = (uint8_t)(addr >> 24); buf[2] = (uint8_t)(addr >> 16);
			buf[3] = (uint8_t)(addr >> 8); buf[4] = (uint8_t)addr;
			for (uint32_t i = 0; i < n; i++)
				buf[5 + i] = data[i];
			if (bb_xfer(FTS_ADDR, buf, 5 + n, 0, 0))
				return 1;
			addr += n;
			data += n;
			remaining -= n;
			block += n;
		}
		words = block / 4U - 1U;
		a = address + (wheel * FLASH_CHUNK) / 4U;
		cfg[0] = 0xfa; cfg[1] = 0x20; cfg[2] = 0x00; cfg[3] = 0x00; cfg[4] = 0x72; cfg[5] = 0x00; cfg[6] = 0x00;
		cfg[7] = (uint8_t)a; cfg[8] = (uint8_t)(a >> 8);
		cfg[9] = (uint8_t)words; cfg[10] = (uint8_t)(words >> 8);
		cfg[11] = 0x00;
		if (bb_xfer(FTS_ADDR, cfg, 12, 0, 0))
			return 2;
		if (fts_dma_start())
			return 3;
		*done_total += block;
		wheel++;
		bn_step(7, *done_total, total, "BURNING TOUCH FIRMWARE - DO NOT POWER OFF");
	}
	return 0;
}

/* fts_system_reset(): HW reg 0x20000024 <- 0x81, then wait up to 1.5 s for the controller-ready event (0x03).
 * No event is not an error (no firmware running), like the stock code. Returns 1 if the event was seen. */
static int fts_sys_reset(void)
{
	static const uint8_t rst[6] = { 0xfa, 0x20, 0x00, 0x00, 0x24, 0x81 };
	uint8_t cmd = 0x86, ev[8];

	if (bb_xfer(FTS_ADDR, rst, 6, 0, 0))
		return -1;
	for (unsigned t = 0; t < 75; t++) {
		delay_ms(20);
		memset_b(ev, 0, sizeof(ev));
		if (!bb_xfer(FTS_ADDR, &cmd, 1, ev, 8) && ev[0] == 0x03)
			return 1;
	}
	return 0;
}

/* erase page by page, SKIP_PANEL_CX_INIT: the panel-init and CX pages stay (page numbers from the file's organisation
 * bytes at 280..283, or the defaults 26-27 and 28-30), everything else is erased */
static int fts_erase(const uint8_t *f)
{
	uint8_t mask[4] = { 0, 0, 0, 0 }, cmd2[9], cmd1[6], cmd[6];
	unsigned panel_s = 26, panel_e = 27, cx_s = 28, cx_e = 30;

	if (f[280] && f[281] && f[282] && f[283]) {
		panel_s = f[280];
		panel_e = f[281] > 1 ? panel_s + f[281] - 1U : panel_s;
		cx_s = panel_e + 1;
		cx_e = f[282] > 1 ? cx_s + f[282] - 1U : cx_s;
	}
	for (unsigned i = cx_s; i <= cx_e; i++)
		mask[i / 8] |= (uint8_t)(1U << (i % 8));
	for (unsigned i = panel_s; i <= panel_e; i++)
		mask[i / 8] |= (uint8_t)(1U << (i % 8));
	cmd2[0] = 0xfa; cmd2[1] = 0x20; cmd2[2] = 0x00; cmd2[3] = 0x01; cmd2[4] = 0x28;
	for (unsigned i = 0; i < 4; i++)
		cmd2[5 + i] = (uint8_t)(0xffU & ~mask[i]);
	cmd1[0] = 0xfa; cmd1[1] = 0x20; cmd1[2] = 0x00; cmd1[3] = 0x00; cmd1[4] = 0x6b; cmd1[5] = 0x00;
	cmd[0] = 0xfa; cmd[1] = 0x20; cmd[2] = 0x00; cmd[3] = 0x00; cmd[4] = 0x6a; cmd[5] = 0xa0;
	if (bb_xfer(FTS_ADDR, cmd2, 9, 0, 0) || bb_xfer(FTS_ADDR, cmd1, 6, 0, 0) || bb_xfer(FTS_ADDR, cmd, 6, 0, 0))
		return 1;
	return fts_wait_flash(0x6a);
}

/* flash_burn() steps 1-9. 0 ok, else 10 * step + detail */
static int fts_burn(const struct ftsfw *fw, const uint8_t *file)
{
	uint32_t done = 0, total = fw->sec0 + fw->sec1;
	static const uint8_t hold[6] = { 0xfa, 0x20, 0x00, 0x00, 0x24, 0x01 };
	int rc;

	bn_step(1, 0, total, "BURNING TOUCH FIRMWARE - DO NOT POWER OFF");
	if (fts_sys_reset() < 0)
		return 10;
	delay_ms(100);
	bn_step(2, 0, total, "BURNING TOUCH FIRMWARE - DO NOT POWER OFF");
	if (bb_xfer(FTS_ADDR, hold, 6, 0, 0))
		return 20;
	if (fts_w6(0x1b, 0x66) || fts_w6(0x68, 0x13))	/* UVLO + auto power down */
		return 30;
	if (fts_w6(0x25, 0x20) || fts_w6(0x6b, 0x00))	/* flash unlock */
		return 40;
	if (fts_w6(0xde, 0x03))				/* erase unlock */
		return 50;
	bn_step(6, 0, total, "BURNING TOUCH FIRMWARE - ERASING");
	if (fts_erase(file))
		return 60;
	rc = fts_fill(fw->code_addr, fw->data, fw->sec0, &done, total);	/* 7) program */
	if (rc)
		return 70 + rc;
	rc = fts_fill(fw->cfg_addr, fw->data + fw->sec0, fw->sec1, &done, total);	/* 8) config */
	if (rc)
		return 80 + rc;
	bn_step(9, done, total, "BURNING TOUCH FIRMWARE - RESET");
	if (fts_sys_reset() < 0)
		return 90;
	return 0;
}
#endif /* MI8_FTS_FW */

/* Burn the embedded touch firmware if the chip's version differs (r = the 8-byte chip id block read before). */
static void fts_maybe_burn(uint8_t *r)
{
#ifdef MI8_FTS_FW
	struct ftsfw fw;
	uint8_t w[5];
	uint32_t fsize = (uint32_t)(fts_fw_end - fts_fw_start);
	int prc = fts_parse(fts_fw_start, fsize, &fw);
	uint32_t chip_fw = (uint32_t)r[4] | ((uint32_t)r[5] << 8);
	int rc;

	pair("FWFILE", -1, "parse=", (uint32_t)prc, "fw=", fw.fw_ver);
	pair(" ", -1, "cfg=", fw.cfg_ver, "sec0=", fw.sec0);
	pair(" ", -1, "sec1=", fw.sec1, "sec2=", fw.sec2);
	pair("CHIPFW", -1, "fw=", chip_fw, "burn=", (uint32_t)(!prc && fw.fw_ver != chip_fw));
	flush_log();
	if (!prc && fw.fw_ver != chip_fw) {
		int brc;

		bn_i = nl;
		pair("BURN", -1, "step=", 0, "done=", 0);
		pair(" ", -1, "total=", fw.sec0 + fw.sec1, 0, 0);
		brc = fts_burn(&fw, fts_fw_start);
		bn_i = -1;
		pair("BURNRC", -1, "rc=", (uint32_t)brc, 0, 0);
		delay_ms(300);
		memset_b(r, 0, 8);
		w[0] = 0xfa; w[1] = 0x20; w[2] = 0x00; w[3] = 0x00; w[4] = 0x00;
		rc = bb_xfer(FTS_ADDR, w, 5, r, 8);
		pair("NEWFW", -1, "rc=", (uint32_t)rc, "fw=", (uint32_t)r[4] | ((uint32_t)r[5] << 8));
		pair(" ", -1, "b0-3=", le32(r), "b4-7=", le32(r + 4));
		flush_log();
	}
#else
	(void)r;
	pair("FWFILE", -1, "none=", 1, 0, 0);	/* no mi8/fw/st_fts_e1.ftb at build time: the chip keeps its own firmware */
#endif
}

/* one timed window: poll like before (0x86 x 32 bytes while the irq line is low, else 0x85 every 200 ms) */
static void run_window(int w, const char *title, unsigned seconds, unsigned *irq_low, unsigned *polls, unsigned *events)
{
	uint8_t cmd, one[8];

	for (unsigned t = 0; t < seconds * 50U; t++) {
		int pending = !line_get(31);

		if (pending) {
			unsigned rem = 0, n;

			(*irq_low)++;
			(*polls)++;
			n = fts_read_fifo(fifo_buf, &rem);
			if (n == 0xffffffffU) {
				bad86++;
			} else {
				ok86++;
				rem_last = rem;
				if (rem > rem_max)
					rem_max = rem;
				L[raw_i].av = le32(fifo_buf);	L[raw_i].bv = le32(fifo_buf + 4);
				L[raw_i + 1].av = le32(fifo_buf + 8);	L[raw_i + 1].bv = le32(fifo_buf + 12);
				for (unsigned k = 0; k < n; k++) {
					const uint8_t *e = fifo_buf + 8 * k;

					if (!e[0])
						continue;
					nz86++;
					(*events)++;
					fts_show_event(e, *events);
					if (e[0] == 0x13 || e[0] == 0x23 || e[0] == 0x33)
						win_event(w, e);
					else if (e[0] == 0x43)
						note_status(e);
				}
			}
			if (line_get(31))
				hi_after++;
		} else if ((t % 10) == 0) {
			cmd = 0x85;
			memset_b(one, 0, sizeof(one));
			(*polls)++;
			if (bb_xfer(FTS_ADDR, &cmd, 1, one, 8)) {
				bad85++;
			} else {
				ok85++;
				if (one[0]) {
					nz85++;
					(*events)++;
					fts_show_event(one, *events);
					if (one[0] == 0x13 || one[0] == 0x23 || one[0] == 0x33)
						win_event(w, one);
				}
			}
		}
		if ((t % 25) == 24) {
			L[xy_i + 2].av = *polls;
			L[xy_i + 2].bv = *irq_low;
			st_update(*irq_low, *polls);
			render(C_BLUE, title);
			draw_pts();
			flush_log();
		}
		delay_ms(20);
	}
}

void mi8_touch_probe(void)
{
	uint8_t w[5], r[8], ev[8];
	int rc;
	unsigned irq_low = 0, polls = 0, events = 0;

	nl = 0;
	tick_i = -1;
	ev_i = xy_i = st_i = win_i = stat_i = -1;
	rem_max = rem_last = stat_n = 0;
	pt_next = pt_valid = 0;
	ok85 = bad85 = ok86 = bad86 = nz85 = nz86 = hi_after = 0;
	msg("TOUCH", "mi8 touch v15: fw burn + touch");
	pair("PIN", 1, "cfg=", rd32(pin_cfg(31)), "io=", rd32(pin_cfg(31) + 4));
	/* Both touch rails, as Android does (DT: fts vdd = disp_vddio_vreg on gpio23, avdd = pm8998_l28 3.3 V via RPMh).
	 * v9-v11 skipped the avdd vote on the wrong assumption "the chip ACKs, so avdd is on": the digital side answers on vdd
	 * alone, but the analog sensing needs avdd, which is why scan mode was echoed and no touch was ever reported. */
	pair("VDDIO", 1, "ok=", (uint32_t)vddio_enable(), 0, 0);
	rc = rh_enable_l28();
	pair("RAIL", -1, "rc=", (uint32_t)rc, 0, 0);
	flush_log();
	delay_ms(20);
	/* release the touch pins like sweet: irq input pull-up, reset output high; then a reset pulse and wait for boot */
	touch_gpio(31, 0, 3, 3, 0);
	touch_gpio(32, 0, 3, 3, 1);
	bb_setup(33, 34);
	delay_ms(20);
	wr32(pin_cfg(32) + 4, rd32(pin_cfg(32) + 4) & ~2U);	/* reset low */
	delay_ms(10);
	wr32(pin_cfg(32) + 4, rd32(pin_cfg(32) + 4) | 2U);	/* reset high */
	delay_ms(300);
	pair("IDLE", -1, "sda=", (uint32_t)line_get(33), "scl=", (uint32_t)line_get(34));
	pair("IRQ", -1, "gpio31=", (uint32_t)line_get(31), 0, 0);
	flush_log();

	rc = bb_xfer(FTS_ADDR, 0, 0, 0, 0);
	pair("ACK49", -1, "rc=", (uint32_t)rc, 0, 0);
	/* hardware register 0x20000000 (chip id) through the FTS5 "HW reg read" command 0xFA + 4-byte address */
	w[0] = 0xfa; w[1] = 0x20; w[2] = 0x00; w[3] = 0x00; w[4] = 0x00;
	memset_b(r, 0, sizeof(r));
	rc = bb_xfer(FTS_ADDR, w, 5, r, 8);
	pair("CHIPID", -1, "rc=", (uint32_t)rc, "b0-3=", le32(r));
	pair(" ", -1, "b4-7=", le32(r + 4), 0, 0);
	/* event FIFO: 0x86 = read all (first 8 bytes), expect "controller ready" 0x03.. after the reset */
	w[0] = 0x86;
	memset_b(ev, 0, sizeof(ev));
	rc = bb_xfer(FTS_ADDR, w, 1, ev, 8);
	pair("BOOTEV", -1, "rc=", (uint32_t)rc, "b0-3=", le32(ev));
	pair(" ", -1, "b4-7=", le32(ev + 4), "irq=", (uint32_t)line_get(31));
	fts_maybe_burn(r);
	ev_i = nl;
	for (int k = 0; k < EV_LINES; k++)
		pair("EVT", k, "b0-3=", 0, "b4-7=", 0);
	xy_i = nl;
	pair("XY", -1, "x=", 0, "y=", 0);
	pair(" ", -1, "events=", 0, 0, 0);
	pair("POLLS", -1, "n=", 0, "irqlow=", 0);
	st_i = nl;
	pair("ST85", -1, "ok=", 0, "bad=", 0);
	pair("ST86", -1, "ok=", 0, "bad=", 0);
	pair("NZ", -1, "n85=", 0, "n86=", 0);
	pair("IRQHI", -1, "after=", 0, "low=", 0);
	pair(" ", -1, "polls=", 0, 0, 0);
	raw_i = nl;
	pair("RAW86", -1, "b0-3=", 0, "b4-7=", 0);
	pair("RAW86B", -1, "b8-11=", 0, "b12-15=", 0);
	pair("RAW85", -1, "b0-3=", 0, "b4-7=", 0);
	flush_log();

	/* v12 on a real phone: with both rails on the chip streams ~180 events/s, two alternating records
	 * `23 11 5D E3 54 00 00 1E` / `23 01 D0 63 54 00 00 1D`: decoded as ST fts5 motion points they sit at fixed x,y while
	 * the last byte wobbles, and the owner reported that touching changed nothing. This build runs four timed windows
	 * with on-screen instructions and per-window statistics (count, max byte5, min/max x and y by the fts5 decode), and
	 * draws a marker at the last two decoded points (white = newest, yellow = previous; coordinates drawn unscaled).
	 * If x/y follow your finger the decode is right; if the stats are identical in every window the stream is not touch. */
	cmd_scan[0] = 0xa0; cmd_scan[1] = 0x00; cmd_scan[2] = 0xff;
	rc = bb_xfer(FTS_ADDR, cmd_scan, 3, 0, 0);
	pair("SCANCMD", -1, "rc=", (uint32_t)rc, 0, 0);
	stat_i = nl;
	pair("STAT", -1, "b0-3=", 0, "b4-7=", 0);
	pair(" ", -1, "n=", 0, "remmax=", 0);
	/* v13 on a real phone: byte 7 of every event (0x1c..0x1f) is the ST "events remaining in the FIFO" count, so the FIFO was
	 * saturated by constant records for three fixed points at z = 0 (touch ids 0, 1 and 2) in every window, touched or not.
	 * Stock flow here: flush the FIFO (A4 00 01), wait for the panel to be untouched, force calibration (A4 02 <mask>;
	 * the stock log shows "Mutual negative detect Force cal" right after Sense ON). CAL0 counts touch events in a hands-off
	 * period BEFORE the force calibration, CAL1 AFTER it. If CAL1 is far below CAL0 the ghosts were a bad baseline. */
	delay_ms(200);
	{
		uint8_t flush[3], fcal[3];
		unsigned c0, c1;

		flush[0] = 0xa4; flush[1] = 0x00; flush[2] = 0x01;
		rc = bb_xfer(FTS_ADDR, flush, 3, 0, 0);
		pair("FLUSH", -1, "rc=", (uint32_t)rc, 0, 0);
		render(C_RED, "HANDS OFF THE SCREEN (counting)");
		c0 = count_touch_events(6000);
		pair("CAL0", -1, "n=", c0, "remmax=", rem_max);
		fcal[0] = 0xa4; fcal[1] = 0x02; fcal[2] = 0x05;	/* force cal, mutual-sense touch + self-sense touch */
		rc = bb_xfer(FTS_ADDR, fcal, 3, 0, 0);
		pair("FCAL", -1, "rc=", (uint32_t)rc, 0, 0);
		render(C_RED, "HANDS OFF: force calibration");
		delay_ms(1500);
		rc = bb_xfer(FTS_ADDR, flush, 3, 0, 0);
		rem_max = 0;
		c1 = count_touch_events(6000);
		pair("CAL1", -1, "n=", c1, "remmax=", rem_max);
		render(C_BLUE, "calibration done");
		flush_log();
		delay_ms(1500);
	}
	win_i = nl;
	for (int k = 0; k < 4; k++) {
		pair("WIN", k, "n=", 0, "zmax=", 0);
		pair(" ", -1, "x0=", 0xffff, "x1=", 0);
		pair(" ", -1, "y0=", 0xffff, "y1=", 0);
	}
	delay_ms(50);
	run_window(0, "A: DO NOT TOUCH (hold by the edges)", 10, &irq_low, &polls, &events);
	run_window(1, "B: TOUCH TOP-LEFT CORNER ONLY", 12, &irq_low, &polls, &events);
	run_window(2, "C: TOUCH BOTTOM-RIGHT CORNER ONLY", 12, &irq_low, &polls, &events);
	run_window(3, "D: DRAG ONE FINGER SLOWLY DOWN", 12, &irq_low, &polls, &events);
	st_update(irq_low, polls);
	render(C_GREEN, "touch v15: done, rebooting");
	draw_pts();
	flush_log();
	delay_ms(20000);
}

/* iOS boot path (called from shim/loader.c once a payload is found, before XNU is entered): everything the touch chip needs
 * that XNU's driver must not do: vdd (gpio23) + avdd (pm8998_l28 via RPMh), reset pulse, firmware burn if the chip's version
 * differs, scan mode "Sense ON" and a FIFO flush. XNU's mi8_touch.c then only talks to the chip. Nothing here is fatal:
 * if a step fails the boot continues without touch. Takes about 40 s when the firmware has to be burned (every cold boot). */
void mi8_touch_bringup(void)
{
	uint8_t w[5], r[8], ev[8], scan[3], flush[3];
	int rc, vd, rail;

	nl = 0;
	tick_i = -1;
	st_i = ev_i = xy_i = win_i = stat_i = -1;
#ifdef MI8_FTS_FW
	bn_i = -1;
#endif
	msg("TOUCH", "iOS boot: touch bring-up");
	vd = vddio_enable();
	pair("VDDIO", 1, "ok=", (uint32_t)vd, 0, 0);
	rail = rh_enable_l28();
	pair("RAIL", -1, "rc=", (uint32_t)rail, 0, 0);
	flush_log();
	delay_ms(20);
	touch_gpio(31, 0, 3, 3, 0);
	touch_gpio(32, 0, 3, 3, 1);
	bb_setup(33, 34);
	delay_ms(20);
	wr32(pin_cfg(32) + 4, rd32(pin_cfg(32) + 4) & ~2U);	/* reset low */
	delay_ms(10);
	wr32(pin_cfg(32) + 4, rd32(pin_cfg(32) + 4) | 2U);	/* reset high */
	delay_ms(300);
	rc = bb_xfer(FTS_ADDR, 0, 0, 0, 0);
	pair("ACK49", -1, "rc=", (uint32_t)rc, 0, 0);
	w[0] = 0xfa; w[1] = 0x20; w[2] = 0x00; w[3] = 0x00; w[4] = 0x00;
	memset_b(r, 0, sizeof(r));
	rc = bb_xfer(FTS_ADDR, w, 5, r, 8);
	pair("CHIPID", -1, "rc=", (uint32_t)rc, "b0-3=", le32(r));
	pair(" ", -1, "b4-7=", le32(r + 4), 0, 0);
	if (!rc) {
		w[0] = 0x86;
		memset_b(ev, 0, sizeof(ev));
		(void)bb_xfer(FTS_ADDR, w, 1, ev, 8);	/* controller-ready event */
		fts_maybe_burn(r);
		scan[0] = 0xa0; scan[1] = 0x00; scan[2] = 0xff;	/* Sense ON */
		rc = bb_xfer(FTS_ADDR, scan, 3, 0, 0);
		pair("SENSE", -1, "rc=", (uint32_t)rc, 0, 0);
		delay_ms(200);
		flush[0] = 0xa4; flush[1] = 0x00; flush[2] = 0x01;	/* FIFO flush */
		rc = bb_xfer(FTS_ADDR, flush, 3, 0, 0);
		pair("FLUSH", -1, "rc=", (uint32_t)rc, 0, 0);
		for (unsigned i = 0; i < 16 && !line_get(31); i++) {	/* drain what is still queued */
			unsigned rem = 0;

			if (fts_read_fifo(fifo_buf, &rem) == 0xffffffffU)
				break;
		}
		pair("IRQ", -1, "gpio31=", (uint32_t)line_get(31), 0, 0);
	}
	flush_log();
	render(C_BLUE, "touch ready - starting iOS");
	delay_ms(800);
}

void mi8_panic_log(const char *stage, uint64_t slot, uint64_t esr, uint64_t elr, uint64_t far)
{
	msg("PANIC", stage);
	pair("SLOT", -1, "n=", (uint32_t)slot, "esr=", (uint32_t)esr);
	pair(" ", -1, "elr=", (uint32_t)elr, "far=", (uint32_t)far);
	flush_log();
}
