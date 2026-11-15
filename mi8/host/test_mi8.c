/* Host test for shim/mi8.c: fake MMIO + fake ramoops, checks the pstore layout. */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include "console.h"
#include "mi8.h"

volatile uint32_t *con_fb;
uint32_t con_stride4 = 1080;
static int renders, mdp_writes;
static char screen_titles[8][64];

void con_clear(uint32_t bg) { (void)bg; }
void con_skip(void) {}
void con_hex(const char *l, uint64_t v) { (void)l; (void)v; }
void con_str(const char *l, const char *s) { if (!strcmp(l, "MI8") && renders < 8) strcpy(screen_titles[renders++], s); }
void con_hex2(const char *l, const char *a, uint32_t va, const char *b, uint32_t vb) { (void)l; (void)a; (void)va; (void)b; (void)vb; }

static uint8_t ram[2][0x40000];
static uint32_t fake_fb[1080 * 2248];
static uint32_t regs_sspp0_active = 1;
static uint64_t tick;

uint64_t ticks(void) { return tick += 1000; }
uint64_t tfreq(void) { return 19200000; }
uint64_t host_rsr(const char *n)
{
	if (!strcmp(n, "midr_el1")) return 0x51df8030;
	if (!strcmp(n, "mpidr_el1")) return 0x81000000;
	if (!strcmp(n, "id_aa64mmfr0_el1")) return 0x00100122;
	if (!strcmp(n, "currentel")) return 4;
	if (!strcmp(n, "sctlr_el1")) return 0x30d00800;
	return 0;
}


/* --- RPMh fakes: apps_rsc DRV2, cmd-db with one VRM entry "ldoa28", TCS bank that completes on trigger --- */
static uint32_t dbmem[0xdc0 / 4], tcsm[0x3000 / 4], irq_st, irq_en_fake, trig;
static void rh_fake_init(void)
{
	dbmem[0] = 1; dbmem[1] = 0x0c0330db;
	dbmem[8 / 4] = 0x00000004;			/* header 0: slave 4 (VRM), entries offset 0 */
	dbmem[12 / 4] = 0x00010100;			/* aux offset 0x100, count 1 */
	dbmem[144 / 4] = 0x616f646c; dbmem[148 / 4] = 0x00003832;	/* "ldoa28" */
	dbmem[160 / 4] = 0x00040600;			/* VRM address */
}
static int in_win(uintptr_t a, uintptr_t base, uintptr_t size) { return a >= base && a < base + size; }
static uint32_t rh_rd(uintptr_t a, int *hit)
{
	*hit = 1;
	if (a == 0x179e0000UL) return 0x00020000;
	if (a == 0x179e0004UL) return 1;
	if (a == 0x179e000cUL) return (8U << 12) | (16U << 27);
	if (a == 0x0c3f000cUL) return 0x85fe0000;
	if (a == 0x0c3f0010UL) return 0xdc0;
	if (in_win(a, 0x85fe0000UL, 0xdc0)) return dbmem[(a - 0x85fe0000UL) / 4];
	if (in_win(a, 0x179e0d00UL, 0x3000)) {
		unsigned off = (unsigned)(a - 0x179e0d00UL), t = off / 0x2a0, r = off % 0x2a0;
		if (off == 0x00) return irq_en_fake;
		if (off == 0x04) return irq_st;
		if (r == 0x18) return 1;				/* idle */
		if (r >= 0x3c && r < 0x3c + 3 * 0x14 && ((r - 0x3c) % 0x14) == 0) return trig ? 0x10100 : 0;
		(void)t;
		return tcsm[off / 4];
	}
	*hit = 0;
	return 0;
}
static int rh_wr(uintptr_t a, uint32_t v)
{
	if (!in_win(a, 0x179e0d00UL, 0x3000)) return 0;
	unsigned off = (unsigned)(a - 0x179e0d00UL), t = off / 0x2a0, r = off % 0x2a0;
	if (off == 0x00) { irq_en_fake = v; return 1; }
	if (off == 0x08) { irq_st &= ~v; return 1; }
	if (r == 0x14 && (v & (1U << 24))) { trig = 1; irq_st |= 1U << t; }
	tcsm[off / 4] = v;
	return 1;
}

#define TLMM_N 0x03900000UL
static uint32_t pcfg[160], pout[160];

/* --- I2C slave model on SDA = gpio33, SCL = gpio34: FTS-like device at 0x49, reg 0x80 returns 36 01 02 03 ... --- */
enum { S_IDLE, S_ADDR, S_ACKA, S_WR, S_ACKW, S_RD, S_MACK, S_IGN };
static int st = S_IDLE, bits, rw, slave_low, regptr = -1, rdi, expect_reg, mack, ncmd, cmd0, ev_calls, sense_on, burned, wtotal;
static unsigned wsum;
static FILE *burn_log;
static unsigned char evbuf[8];
static int queued, ghost_on = 1, cmdb[64];
static unsigned shift;
static int last_sda = 1, last_scl = 1;

static int master_low(unsigned pin) { return (pcfg[pin] & 0x200) && !(pout[pin] & 1); }
static int line_sda(void) { return !master_low(33) && !slave_low; }
static int line_scl(void) { return !master_low(34); }
static unsigned char rdbyte(void)
{
	if (cmd0 == 0xFA) return (unsigned char[]){0x36, 0x39, 0x03, 0x00, (unsigned char)(burned ? 0x51 : 0x54), 0x00, 0x39, 0x19}[rdi & 7];	/* chip id block */
	if (cmd0 == 0x85 || cmd0 == 0x86) return evbuf[rdi & 7];
	return 0xA5;
}
static void prep_read(void)
{
	memset(evbuf, 0, sizeof(evbuf));
	if (cmd0 == 0x85 || cmd0 == 0x86) {
		ev_calls++;
		if (ev_calls == 1) {							/* controller ready after reset */
			evbuf[0] = 0x03; evbuf[1] = 0x01;
		} else if (sense_on && ghost_on) {						/* ghost record, FIFO "remaining" = 3 */
			unsigned char g[8] = { 0x23, 0x11, 0x5D, 0xE3, 0x54, 0x00, 0x00, 0x03 };
			memcpy(evbuf, g, 8);
		} else if (sense_on && queued > 0) {					/* a real touch at x=0x123 y=0x456 */
			unsigned char t[8] = { 0x13, 0x01, 0x23, 0x61, 0x45, 0x10, 0, 0 };
			memcpy(evbuf, t, 8);
			queued--;
		}
		if (sense_on && !ghost_on && (ev_calls % 9) == 0) queued = 3;
	}
}

static void slave_step(void)
{
	int sda = line_sda(), scl = line_scl();

	if (scl && last_scl && last_sda && !sda) { st = S_ADDR; bits = 0; shift = 0; expect_reg = 1; }	/* START */
	else if (scl && last_scl && !last_sda && sda) {
		if ((st == S_WR || st == S_ACKW) && ncmd == 3 && cmd0 == 0xA0) sense_on = 1;	/* scan mode command */
		if ((st == S_WR || st == S_ACKW) && ncmd == 1 && cmd0 == 0x93) sense_on = 1;
		if ((st == S_WR || st == S_ACKW) && rw == 0) {
			if (wtotal == 6 && cmdb[0] == 0xFA && cmdb[4] == 0x24 && cmdb[5] == 0x81) ev_calls = 0;	/* system reset */
			if (wtotal == 12 && cmdb[4] == 0x6B && cmdb[11] == 0xC0) { burned = 1; ghost_on = 0; }	/* flash DMA start */
			if (burn_log && cmdb[0] == 0xFA) {
				fprintf(burn_log, "W %d ", wtotal);
				for (int i = 0; i < 12 && i < wtotal; i++) fprintf(burn_log, "%02x", cmdb[i]);
				fprintf(burn_log, " %u\n", wsum);
			}
		}
		if ((st == S_WR || st == S_ACKW) && ncmd == 3 && cmd0 == 0xA4) {
			if (cmdb[1] == 0x00 && cmdb[2] == 0x01) queued = 0;			/* FIFO flush */
			if (cmdb[1] == 0x02) { ghost_on = 0; queued = 0; }			/* force calibration clears the ghosts */
		}
		st = S_IDLE; slave_low = 0;
	}				/* STOP */
	else if (scl && !last_scl) {										/* rising */
		if (st == S_ADDR || st == S_WR) { shift = (shift << 1) | (unsigned)sda; bits++; }
		else if (st == S_MACK) mack = !sda;
	} else if (!scl && last_scl) {										/* falling */
		if (st == S_ADDR && bits == 8) {
			rw = shift & 1;
			if ((shift >> 1) == 0x49) { st = S_ACKA; slave_low = 1; } else st = S_IGN;
		} else if (st == S_ACKA) {
			slave_low = 0;
			if (rw) { st = S_RD; bits = 0; rdi = 0; prep_read(); slave_low = !(rdbyte() & 0x80); } else { st = S_WR; bits = 0; shift = 0; }
		} else if (st == S_WR && bits == 8) {
			if (expect_reg) { regptr = (int)shift; expect_reg = 0; cmd0 = (int)shift; cmdb[0] = cmd0; ncmd = 1; wtotal = 1; wsum = 0; }
			else { if (ncmd < 64) cmdb[ncmd++] = (int)shift; wtotal++; if (wtotal > 5) wsum += shift; }
			st = S_ACKW; slave_low = 1;
		} else if (st == S_ACKW) { slave_low = 0; st = S_WR; bits = 0; shift = 0; }
		else if (st == S_RD) {
			bits++;
			if (bits == 8) { slave_low = 0; st = S_MACK; }
			else if (bits > 0) slave_low = !((rdbyte() >> (7 - bits)) & 1);
		} else if (st == S_MACK) {
			if (mack) { rdi++; st = S_RD; bits = 0; slave_low = !(rdbyte() & 0x80); } else { st = S_IGN; slave_low = 0; }
		}
	}
	last_sda = line_sda(); last_scl = line_scl();
}

uint32_t rd32(uintptr_t a)
{
	{ int hit; uint32_t v = rh_rd(a, &hit); if (hit) return v; }
	if (a == 0x0ae00000UL + 0x5000 + 0x14 && regs_sspp0_active) return 0x9d400000;
	if (a == 0x0ae00000UL + 0x5000 + 0x2c && regs_sspp0_active) return 0x10e0;
	if (a == 0x0ae00000UL + 0x5000 + 0x30 && regs_sspp0_active) return 0x000236ff;
	if (a == 0x0ae00000UL + 0x5000 + 0x00 && regs_sspp0_active) return 0x08c80438;
	if (a == 0x0ae00000UL) return 0x40000000;
	if (a >= TLMM_N && a < TLMM_N + 160 * 0x1000UL) {	/* TLMM north tile: cfg at pin*0x1000, io at +4 */
		unsigned pin = (unsigned)((a - TLMM_N) / 0x1000), off = (unsigned)((a - TLMM_N) % 0x1000);
		if (off == 0) return pcfg[pin];
		if (off == 4) {
			unsigned in = (pcfg[pin] & 0x200) ? (pout[pin] & 1) : 1;
			if (pin == 31) in = (sense_on && (ghost_on || queued > 0)) ? 0 : 1;	/* irq low while events are queued */
			if (pin == 33) in = (unsigned)line_sda();
			if (pin == 34) in = (unsigned)line_scl();
			return in | (pout[pin] << 1);
		}
	}
	return 0;
}

void wr32(uintptr_t a, uint32_t v)
{
	if (rh_wr(a, v)) return;
	if (a >= 0xb0120000UL && a < 0xb0160000UL) { memcpy(&ram[1][a - 0xb0120000UL], &v, 4); return; }
	if (a >= 0xb0100000UL && a < 0xb0140000UL) { memcpy(&ram[0][a - 0xb0100000UL], &v, 4); return; }
	if (a >= TLMM_N && a < TLMM_N + 160 * 0x1000UL) {
		unsigned pin = (unsigned)((a - TLMM_N) / 0x1000), off = (unsigned)((a - TLMM_N) % 0x1000);
		if (off == 0) pcfg[pin] = v;
		if (off == 4) pout[pin] = (v >> 1) & 1;
		if (pin == 33 || pin == 34) slave_step();
		return;
	}
	if (a >= 0x0ae00000UL && a < 0x0af00000UL) mdp_writes++;	/* v2 must never write the display block */
}
void wr8(uintptr_t a, uint8_t v)
{
	if (a >= 0xb0120000UL && a < 0xb0160000UL) ram[1][a - 0xb0120000UL] = v;
	else if (a >= 0xb0100000UL && a < 0xb0140000UL) ram[0][a - 0xb0100000UL] = v;
	else { fprintf(stderr, "stray wr8 %lx\n", (unsigned long)a); exit(2); }
}

static int check_zone(const uint8_t *z, const char *want)
{
	uint32_t sig, start, size;
	memcpy(&sig, z, 4); memcpy(&start, z + 4, 4); memcpy(&size, z + 8, 4);
	if (sig != 0x43474244 || start != 0 || size == 0 || size > 0x40000 - 12) { printf("bad header sig=%x start=%u size=%u\n", sig, start, size); return 1; }
	char *txt = malloc(size + 1); memcpy(txt, z + 12, size); txt[size] = 0;
	int ok = strstr(txt, want) != NULL;
	if (!ok) printf("missing '%s'\n", want);
	free(txt);
	return !ok;
}

int main(void)
{
	int bad = 0;
	if (getenv("BURN_LOG")) burn_log = fopen(getenv("BURN_LOG"), "w");
	if (getenv("BRINGUP")) {		/* iOS boot path: shim/loader.c calls mi8_touch_bringup() before XNU */
		uint32_t sz; char *txt;
		rh_fake_init();
		pcfg[22] = 1; pcfg[24] = 1;
		con_fb = fake_fb; con_stride4 = 1080;
		mi8_touch_bringup();
		bad += check_zone(ram[0], "TOUCH iOS boot: touch bring-up");
		bad += check_zone(ram[0], "VDDIO1 ok=00000001");
		bad += check_zone(ram[0], "RAIL rc=00000000");
		bad += check_zone(ram[0], "ACK49 rc=00000000");
		bad += check_zone(ram[0], "CHIPID rc=00000000 b0-3=00033936");
		bad += check_zone(ram[0], "SENSE rc=00000000");
		bad += check_zone(ram[0], "FLUSH rc=00000000");
#ifdef MI8_FTS_FW
		bad += check_zone(ram[0], "BURNRC rc=00000000");
		bad += check_zone(ram[0], "NEWFW rc=00000000 fw=00000051");
#else
		bad += check_zone(ram[0], "FWFILE none=00000001");
#endif
		(void)sz; (void)txt;
		puts(bad ? "FAIL (bringup)" : "PASS (bringup)");
		return bad;
	}
	/* Zone A and B overlap (B starts 0x20000 into A's console zone, as on real hardware); both must be valid
	 * from their own start, so check the combined effect through separate buffers: ram[1] mirrors the B copy. */
	mi8_diag(0x9c000000UL ? 0x85a00000UL : 0);
	bad += check_zone(ram[0], "SSPP0 addr=9d400000");
	bad += check_zone(ram[1], "SSPP0 addr=9d400000");
	bad += check_zone(ram[0], "ystr=000010e0");
	bad += check_zone(ram[0], "FBUSE base=9d400000 str4=00000438");
	bad += check_zone(ram[0], "PP0C cnt=");
	if (renders != 4 || mdp_writes != 0) { printf("renders=%d mdp_writes=%d\n", renders, mdp_writes); bad++; }
	if ((uintptr_t)con_fb != 0x9d400000 || con_stride4 != 1080) { printf("fb=%p stride4=%u\n", (void *)con_fb, con_stride4); bad++; }
	printf("titles: %s | %s | %s | %s\n", screen_titles[0], screen_titles[1], screen_titles[2], screen_titles[3]);

	rh_fake_init();
	pcfg[22] = 1; pcfg[24] = 1;	/* neighbours of gpio23 are mapped in the north tile */
	con_fb = fake_fb; con_stride4 = 1080;	/* the real pointer from mi8_diag is a phone address */
	mi8_touch_probe();
	if (getenv("DEBUG_DUMP")) { uint32_t sz; memcpy(&sz, ram[0] + 8, 4); fwrite(ram[0] + 12, 1, sz, stdout); }
	rh_fake_init();
	bad += check_zone(ram[0], "TOUCH mi8 touch v15: fw burn + touch");
	bad += check_zone(ram[0], "V23 hi=00000001 lo=00000000");
	bad += check_zone(ram[0], "VDDIO1 ok=00000001");
	bad += check_zone(ram[0], "RAIL rc=00000000");
	bad += check_zone(ram[0], "L28 addr=00040600");
	bad += check_zone(ram[0], "RHTCS0 idle=00000001");
	bad += check_zone(ram[0], "IDLE sda=00000001 scl=00000001");
	bad += check_zone(ram[0], "ACK49 rc=00000000");
	bad += check_zone(ram[0], "CHIPID rc=00000000 b0-3=00033936");
	bad += check_zone(ram[0], "BOOTEV rc=00000000 b0-3=00000103");
	bad += check_zone(ram[0], "EVT0 b0-3=61230113 b4-7=00001045");
	bad += check_zone(ram[0], "XY x=00000123 y=00000456");
	bad += check_zone(ram[0], "SCANCMD rc=00000000");
	bad += check_zone(ram[0], "FLUSH rc=00000000");
	bad += check_zone(ram[0], "FCAL rc=00000000");
#ifdef MI8_FTS_FW
	bad += check_zone(ram[0], "FWFILE parse=00000000 fw=00000051");
	bad += check_zone(ram[0], "CHIPFW fw=00000054 burn=00000001");
	bad += check_zone(ram[0], "BURNRC rc=00000000");
	bad += check_zone(ram[0], "NEWFW rc=00000000 fw=00000051");
#else
	{ /* ghosts before force cal, (almost) none after it */
		uint32_t sz; memcpy(&sz, ram[0] + 8, 4);
		char *txt = malloc(sz + 1); memcpy(txt, ram[0] + 12, sz); txt[sz] = 0;
		unsigned c0 = 0, c1 = 0; char *p0 = strstr(txt, "CAL0 n="), *p1 = strstr(txt, "CAL1 n=");
		if (!p0 || !p1 || sscanf(p0, "CAL0 n=%x", &c0) != 1 || sscanf(p1, "CAL1 n=%x", &c1) != 1 || !(c0 > 20 && c1 < c0 / 4)) { printf("CAL0=%u CAL1=%u\n", c0, c1); bad++; }
		free(txt);
	}
#endif
	bad += check_zone(ram[0], "WIN1 n=");
	if (fake_fb[1110 * 1080 + 291] != 0xffffffffU) { printf("marker missing at x=291 y=1110: %08x\n", fake_fb[1110 * 1080 + 291]); bad++; }
	bad += check_zone(ram[0], "RAW86 b0-3=");
	bad += check_zone(ram[0], "ST86 ok=");
	/* no active pipe */
	regs_sspp0_active = 0; renders = 0; mdp_writes = 0; con_fb = 0; con_stride4 = 1080;
	mi8_diag(0);
	bad += check_zone(ram[0], "no active SSPP");
	mi8_panic_log("gic", 0, 0x96000010, 0xffff, 0x1234);
	bad += check_zone(ram[0], "PANIC gic");
	puts(bad ? "FAIL" : "PASS");
	return bad;
}
