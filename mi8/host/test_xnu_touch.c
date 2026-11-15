/* Unit test for mi8/xnu/mi8_touch.c on a PC: the driver source is included directly (static functions and all) and runs against a
 * simulated FTS chip on a simulated TLMM bit-banged I2C bus. Checks the bus protocol, FIFO draining and the HID calls. */
#define MI8_TOUCH_HOST 1
#include <stdlib.h>
#include <string.h>
#include "../xnu/mi8_touch.c"

#define TLMM_N 0x03900000u
static uint32_t pcfg[160], pout[160];

/* --- I2C slave at 0x49 on SDA = gpio33, SCL = gpio34 --- */
enum { S_IDLE, S_ADDR, S_ACKA, S_WR, S_ACKW, S_RD, S_MACK, S_IGN };
static int sst = S_IDLE, bits, rw, slave_low, mack, cmd0, rdi, expect_cmd, burst, present = 1;
static unsigned shift;
static int last_sda = 1, last_scl = 1;
static uint8_t evq[40][8];
static int evn, evpos;
static uint8_t rdbuf[320];

static int master_low(unsigned pin) { return (pcfg[pin] & 0x200) && !(pout[pin] & 1); }
static int line_sda_m(void) { return !master_low(33) && !slave_low; }
static int line_scl_m(void) { return !master_low(34); }

static void prep_read(void)
{
	memset(rdbuf, 0, sizeof(rdbuf));
	if (cmd0 != 0x86)
		return;
	if (!burst) {					/* first read: one event, byte 7 low bits = events still queued */
		if (evpos < evn) {
			memcpy(rdbuf, evq[evpos], 8);
			rdbuf[7] = (uint8_t)((rdbuf[7] & 0xe0) | ((evn - evpos - 1) & 0x1f));
			evpos++;
			burst = (evn - evpos) > 0;
		}
	} else {					/* second read: everything that is left */
		for (int k = 0; evpos < evn; k++, evpos++)
			memcpy(rdbuf + 8 * k, evq[evpos], 8);
		burst = 0;
	}
}
static unsigned char rdbyte(void) { return rdi < (int)sizeof(rdbuf) ? rdbuf[rdi] : 0; }

static void slave_step(void)
{
	int sda = line_sda_m(), scl = line_scl_m();

	if (scl && last_scl && last_sda && !sda) { sst = S_ADDR; bits = 0; shift = 0; expect_cmd = 1; }	/* START */
	else if (scl && last_scl && !last_sda && sda) { sst = S_IDLE; slave_low = 0; }		/* STOP */
	else if (scl && !last_scl) {									/* rising */
		if (sst == S_ADDR || sst == S_WR) { shift = (shift << 1) | (unsigned)sda; bits++; }
		else if (sst == S_MACK) mack = !sda;
	} else if (!scl && last_scl) {									/* falling */
		if (sst == S_ADDR && bits == 8) {
			rw = shift & 1;
			if (present && (shift >> 1) == FTS_ADDR) { sst = S_ACKA; slave_low = 1; } else sst = S_IGN;
		} else if (sst == S_ACKA) {
			slave_low = 0;
			if (rw) { sst = S_RD; bits = 0; rdi = 0; prep_read(); slave_low = !(rdbyte() & 0x80); }
			else { sst = S_WR; bits = 0; shift = 0; }
		} else if (sst == S_WR && bits == 8) {
			if (expect_cmd) { cmd0 = (int)shift; expect_cmd = 0; }
			sst = S_ACKW; slave_low = 1;
		} else if (sst == S_ACKW) { slave_low = 0; sst = S_WR; bits = 0; shift = 0; }
		else if (sst == S_RD) {
			bits++;
			if (bits == 8) { slave_low = 0; sst = S_MACK; }
			else if (bits > 0) slave_low = !((rdbyte() >> (7 - bits)) & 1);
		} else if (sst == S_MACK) {
			if (mack) { rdi++; sst = S_RD; bits = 0; slave_low = !(rdbyte() & 0x80); } else { sst = S_IGN; slave_low = 0; }
		}
	}
	last_sda = line_sda_m(); last_scl = line_scl_m();
}

uint32_t host_mmio_rd(vm_offset_t a)
{
	if (a >= TLMM_N && a < TLMM_N + 160 * 0x1000UL) {
		unsigned pin = (unsigned)((a - TLMM_N) / 0x1000), off = (unsigned)((a - TLMM_N) % 0x1000);
		if (off == 0) return pcfg[pin];
		if (off == 4) {
			unsigned in = (pcfg[pin] & 0x200) ? (pout[pin] & 1) : 1;
			if (pin == 31) in = evpos < evn ? 0 : 1;			/* irq low while events are queued */
			if (pin == 33) in = (unsigned)line_sda_m();
			if (pin == 34) in = (unsigned)line_scl_m();
			return in | (pout[pin] << 1);
		}
	}
	return 0;
}
void host_mmio_wr(vm_offset_t a, uint32_t v)
{
	if (a >= TLMM_N && a < TLMM_N + 160 * 0x1000UL) {
		unsigned pin = (unsigned)((a - TLMM_N) / 0x1000), off = (unsigned)((a - TLMM_N) % 0x1000);
		if (off == 0) pcfg[pin] = v;
		if (off == 4) pout[pin] = (v >> 1) & 1;
		if (pin == 33 || pin == 34) slave_step();
	}
}
void host_delay_us(unsigned us) { (void)us; }

/* --- HID call recorder --- */
static char hid_log[64][48];
static int hid_n;
void sweet_hid_touch(int finger, int down, int x, int y)
{
	if (hid_n < 64) snprintf(hid_log[hid_n], sizeof(hid_log[0]), "%d %d %d %d", finger, down, x, y);
	hid_n++;
}

static int bad;
static void expect(const char *what, int cond) { if (!cond) { printf("FAIL: %s\n", what); bad++; } }
static void expect_hid(int i, const char *want)
{
	if (i >= hid_n || strcmp(hid_log[i], want)) { printf("FAIL: hid[%d] = '%s', want '%s'\n", i, i < hid_n ? hid_log[i] : "(none)", want); bad++; }
}
static void queue(int n, const uint8_t (*e)[8]) { memcpy(evq, e, 8u * (unsigned)n); evn = n; evpos = 0; burst = 0; }

int main(void)
{
	st.gpio = TLMM_N;
	st.xmax = 1079; st.ymax = 2247;
	st.xmax = 1079;
	for (int p = 31; p <= 34; p++) pcfg[p] = 1;		/* default: gpio, pull-down */
	touch_gpio(PIN_IRQ, 0, 3, 3, false, false);
	touch_gpio(PIN_SDA, 0, 3, 1, false, false);
	touch_gpio(PIN_SCL, 0, 3, 1, false, false);
	expect("bus idle high", line_get(PIN_SDA) == 1 && line_get(PIN_SCL) == 1 && line_get(PIN_IRQ) == 1);

	/* 1) one finger down at x=0x123 y=0x456 */
	{ const uint8_t e[1][8] = { { 0x13, 0x01, 0x23, 0x61, 0x45, 0x10, 0, 0 } };
	  queue(1, e); expect("poll 1", mi8_touch_poll_once() == 0); expect_hid(0, "0 1 291 1110"); expect("fifo drained", evpos == evn); }
	/* 2) motion for id 0 and a second finger (id 1) in one burst: first event carries 'remaining' */
	{ const uint8_t e[2][8] = { { 0x23, 0x01, 0x24, 0x61, 0x46, 0x10, 0, 0 }, { 0x13, 0x11, 0x00, 0x32, 0x30, 0x10, 0, 0 } };
	  queue(2, e); expect("poll 2", mi8_touch_poll_once() == 0); expect_hid(1, "0 1 292 1126"); expect_hid(2, "1 1 512 771"); }
	/* 3) both leave */
	{ const uint8_t e[2][8] = { { 0x33, 0x01, 0x24, 0x61, 0x46, 0x00, 0, 0 }, { 0x33, 0x11, 0x00, 0x32, 0x30, 0x00, 0, 0 } };
	  queue(2, e); expect("poll 3", mi8_touch_poll_once() == 0); expect_hid(3, "0 0 292 1126"); expect_hid(4, "1 0 512 771"); expect("no fingers", st.active == 0); }
	/* 4) a status event (0x43) and an empty queue change nothing */
	{ int before = hid_n; const uint8_t e[1][8] = { { 0x43, 0x01, 0xa0, 0x00, 0xff, 0, 0, 0 } };
	  queue(1, e); expect("poll 4", mi8_touch_poll_once() == 0); expect("status ignored", hid_n == before);
	  evn = 0; evpos = 0; expect("poll empty", mi8_touch_poll_once() == 0); expect("empty ignored", hid_n == before); }
	/* 5) coordinate scaling from a 4096-wide range */
	{ st.xmax = 4095; st.ymax = 4095; const uint8_t e[1][8] = { { 0x13, 0x01, 0x00, 0x08, 0x80, 0x10, 0, 0 } };	/* x=0x800 y=0x800 */
	  queue(1, e); expect("poll 5", mi8_touch_poll_once() == 0); expect_hid(5, "0 1 539 1123"); st.xmax = 1079; st.ymax = 2247;
	  const uint8_t l[1][8] = { { 0x33, 0x01, 0x00, 0x08, 0x80, 0x00, 0, 0 } }; queue(1, l); mi8_touch_poll_once(); }
	/* 6) a backlog of 31 events is drained in one poll (motion for id 2, last one leaves) */
	{ static uint8_t e[31][8]; int before = hid_n;
	  for (int k = 0; k < 31; k++) { uint8_t t[8] = { 0x23, 0x21, (uint8_t)(0x10 + k), 0x01, 0x20, 0x10, 0, 0 }; memcpy(e[k], t, 8); }
	  e[30][0] = 0x33;
	  queue(31, (const uint8_t (*)[8])e); expect("poll 6", mi8_touch_poll_once() == 0); expect("backlog drained", evpos == evn);
	  expect("backlog hid calls (31 events, every one reported)", hid_n - before == 31); expect("released", st.active == 0); }
	/* 7) no chip: NACK -> error */
	{ present = 0; expect("nack reported", mi8_touch_poll_once() == -1); present = 1; }
	/* 8) the bus is left idle after every transfer */
	expect("bus idle after", line_get(PIN_SDA) == 1 && line_get(PIN_SCL) == 1);

	puts(bad ? "FAIL" : "PASS");
	return bad;
}
