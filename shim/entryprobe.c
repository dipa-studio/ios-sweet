/* Optional stages of entryprobe.S, using the real shim platform reader. */
#include <stdint.h>
#include "entryprobe_config.h"
#include "board.h"
#include "fdt.h"
#include "logstore.h"
#include "mmu.h"
#if defined(ENTRY_EL1_DISPLAY)
#include "console.h"
#include "display.h"
#endif
#if defined(ENTRY_LOADER_PROBE)
#include "loader.h"
#include "diag.h"
#if defined(ENTRY_UFS_TEST) || defined(ENTRY_UFS_INIT)
#include "ufs.h"
#endif
static char *loader_banner;

void diag_stage(const char *name, uint64_t a, uint64_t b)
{
	/* Preserve the loader's last completed checkpoint in Linux's banner.
	 * The XNU entry replaces VBAR; after that, this fallback is unavailable. */
	unsigned n = name[0] == 'S' && name[1] >= '0' && name[1] <= '9' ?
	    (unsigned)(name[1] - '0') : 0;
	static const char hex[] = "0123456789abcdef";
	unsigned offsets[] = { ENTRY_STAGE, ENTRY_FAR, ENTRY_PC };
	uint64_t values[] = { 0x80u + n, a, b };
	for (unsigned j = 0; j < 3; j++)
		for (unsigned i = 0; i < 16; i++)
			loader_banner[offsets[j] + i] = hex[(values[j] >> (60 - i * 4)) & 15];
}

void diag_arm_sentinels(uint64_t virt, uint64_t phys, uint64_t size)
{
	(void)virt; (void)phys; (void)size;
#ifdef ENTRY_XNU_VECTOR_PA
	/* Diagnostic only, before MMU enable: keep XNU's VBAR write, but
	 * redirect each early spin vector to the same slot of our recorder.
	 * No stack is needed; XNU's SP may already hold an unmapped KVA. */
	extern const unsigned char probe_vectors[];
	volatile uint32_t *vectors = (volatile uint32_t *)ENTRY_XNU_VECTOR_PA;
	for (unsigned slot = 0; slot < 16; slot++) {
		uint64_t target = (uintptr_t)probe_vectors + slot * 128;
		volatile uint32_t *v = vectors + slot * 32;
		v[0] = 0xd2800010 | ((target & 0xffff) << 5); /* movz x16 */
		v[1] = 0xf2a00010 | (((target >> 16) & 0xffff) << 5);
		v[2] = 0xf2c00010 | (((target >> 32) & 0xffff) << 5);
		v[3] = 0xf2e00010 | (((target >> 48) & 0xffff) << 5);
		v[4] = 0xd61f0200; /* br x16 */
	}
#endif
#if defined(ENTRY_XNU_HIGH_VECTOR_PA) && defined(ENTRY_XNU_SELECTIVE)
	/* Keep every normal XNU vector. The EL1t and EL1h synchronous slots
	 * get a stub for the diagnostic BRK; with ENTRY_EL0_SYSCALL the EL0
	 * AArch64 synchronous slot (8) gets the same stub for the userspace
	 * syscall checkpoint. All other exceptions forward to the original
	 * handlers. The relay body is copied to slot 12 (AArch32 EL0 sync),
	 * unused by arm64 userspace. */
	extern const uint32_t probe_sel_stub[], probe_sel_stub_end[];
	extern const uint32_t probe_sel_forward[], probe_sel_relay_branch[];
	extern const uint32_t probe_mmu_vector[], probe_mmu_identity[], probe_mmu_physical[];
	extern const uint32_t probe_mmu_recorder[], probe_mmu_literals_end[];
	extern const unsigned char probe_vectors[];
	uintptr_t hv = ENTRY_XNU_HIGH_VECTOR_PA;
	uintptr_t relay = hv + 12 * 128;
	uint64_t relay_va = ENTRY_XNU_HIGH_VECTOR_VA + 12 * 128;
	uintptr_t fwd_off = (uintptr_t)probe_sel_forward - (uintptr_t)probe_sel_stub;
	uintptr_t relay_off = (uintptr_t)probe_sel_relay_branch - (uintptr_t)probe_sel_stub;
	unsigned stub_words = ((uintptr_t)probe_sel_stub_end - (uintptr_t)probe_sel_stub) / 4;
	static const unsigned sync_slots[] = { 0, 4, 8 };
	unsigned sync_count = 2;
#ifdef ENTRY_EL0_SYSCALL
	sync_count = 3;
#endif
	for (unsigned si = 0; si < sync_count; si++) {
		unsigned slot_index = sync_slots[si];
		uintptr_t slot = hv + slot_index * 128;
		uint64_t slot_va = ENTRY_XNU_HIGH_VECTOR_VA + slot_index * 128;
		uint32_t insn = *(volatile uint32_t *)slot;
		if ((insn & 0xfc000000) != 0x14000000)
			continue;
		/* Decode the original B target in virtual-address space. Both
		 * stub branches are direct Bs patched here: a br through a GPR
		 * would corrupt the interrupted context on the forward path. */
		int64_t off = ((int64_t)(insn & 0x03ffffff) << 38) >> 36;
		int64_t delta = (int64_t)(slot_va + (uint64_t)off) -
		    (int64_t)(slot_va + fwd_off);
		int64_t relay_delta = (int64_t)relay_va - (int64_t)(slot_va + relay_off);
		if ((delta & 3) || delta < -(1 << 27) || delta >= (1 << 27) ||
		    (relay_delta & 3) || relay_delta < -(1 << 27) || relay_delta >= (1 << 27))
			continue;
		for (unsigned i = 0; i < stub_words; i++)
			((volatile uint32_t *)slot)[i] = probe_sel_stub[i];
		*(volatile uint32_t *)(slot + fwd_off) =
		    0x14000000u | (((uint32_t)(delta >> 2)) & 0x03ffffffu);
		*(volatile uint32_t *)(slot + relay_off) =
		    0x14000000u | (((uint32_t)(relay_delta >> 2)) & 0x03ffffffu);
	}
	unsigned rwords = ((uintptr_t)probe_mmu_literals_end - (uintptr_t)probe_mmu_vector) / 4;
	for (unsigned i = 0; i < rwords; i++)
		((volatile uint32_t *)relay)[i] = probe_mmu_vector[i];
	*(volatile uint64_t *)(relay +
	    ((uintptr_t)probe_mmu_physical - (uintptr_t)probe_mmu_vector)) =
	    relay + ((uintptr_t)probe_mmu_identity - (uintptr_t)probe_mmu_vector);
	*(volatile uint64_t *)(relay +
	    ((uintptr_t)probe_mmu_recorder - (uintptr_t)probe_mmu_vector)) =
	    (uintptr_t)probe_vectors;
#elif defined(ENTRY_XNU_HIGH_VECTOR_PA)
	/* Shared-table mode restores the still-intact bootstrap TTBR0 before
	 * switching to the physical alias. The per-slot mode requires TTBR0
	 * to remain active. Configured cache cleanup precedes the recorder. */
	extern const uint32_t probe_mmu_vector[], probe_mmu_vector_end[];
	extern const uint32_t probe_mmu_identity[], probe_mmu_physical[], probe_mmu_recorder[];
	unsigned words = ((uintptr_t)probe_mmu_vector_end - (uintptr_t)probe_mmu_vector) / 4;
#ifdef ENTRY_XNU_RESTORE_TTBR0
	uintptr_t dst = ENTRY_XNU_HIGH_VECTOR_PA;
	volatile uint32_t *v = (volatile uint32_t *)dst;
	for (unsigned i = 0; i < words; i++)
		v[i] = probe_mmu_vector[i];
	*(volatile uint64_t *)(dst + (uintptr_t)probe_mmu_physical - (uintptr_t)probe_mmu_vector) =
	    dst + (uintptr_t)probe_mmu_identity - (uintptr_t)probe_mmu_vector;
	*(volatile uint64_t *)(dst + (uintptr_t)probe_mmu_recorder - (uintptr_t)probe_mmu_vector) =
	    (uintptr_t)probe_vectors;
#else
	for (unsigned slot = 0; slot < 16; slot++) {
		uintptr_t dst = ENTRY_XNU_HIGH_VECTOR_PA + slot * 128;
		volatile uint32_t *v = (volatile uint32_t *)dst;
		for (unsigned i = 0; i < words; i++)
			v[i] = probe_mmu_vector[i];
		*(volatile uint64_t *)(dst + (uintptr_t)probe_mmu_physical - (uintptr_t)probe_mmu_vector) =
		    dst + (uintptr_t)probe_mmu_identity - (uintptr_t)probe_mmu_vector;
		*(volatile uint64_t *)(dst + (uintptr_t)probe_mmu_recorder - (uintptr_t)probe_mmu_vector) =
		    (uintptr_t)probe_vectors + slot * 128;
	}
#endif
#endif
}
#endif
#if defined(ENTRY_XNU)
#include "loader.h"
#endif

static void field(char *banner, unsigned offset, uint64_t value)
{
	static const char hex[] = "0123456789abcdef";
	for (unsigned i = 0; i < 16; i++)
		banner[offset + i] = hex[(value >> (60 - i * 4)) & 15];
}

#ifdef ENTRY_UFS_REGS
/* Read-only UFSHCI snapshot for the XNU root-device bring-up. The diagnostic
 * recorder overwrites stage/fault/esr/far/pc/x0/x16/spsr, so reuse the four
 * fields the EL1-XNU record otherwise fills with board data:
 *   gicd   = CAP << 32 | VER
 *   vtimer = HCS << 32 | HCE
 *   fb     = UTRLBAU << 32 | UTRLBA
 *   dtb    = UTRLDBR << 32 | UTRLRSR
 * CAP bit 24 is 64AS (64-bit DMA); HCE bit 0 plus HCS DP/UTRLRDY gate the
 * takeover. No register is written, and the UFS host is still in LK's state. */
static void
entryprobe_ufs_snapshot(char *banner)
{
	volatile uint32_t *u = (volatile uint32_t *)(uintptr_t)brd.ufs_base;
	uint32_t cap = u[0x00 / 4], ver = u[0x08 / 4];
	uint32_t hcs = u[0x30 / 4], hce = u[0x34 / 4];
	uint32_t ba = u[0x50 / 4], bau = u[0x54 / 4];
	uint32_t dbr = u[0x58 / 4], rsr = u[0x60 / 4];

	field(banner, ENTRY_GICD, ((uint64_t)cap << 32) | ver);
	field(banner, ENTRY_VTIMER, ((uint64_t)hcs << 32) | hce);
	field(banner, ENTRY_FB, ((uint64_t)bau << 32) | ba);
	field(banner, ENTRY_DTB, ((uint64_t)dbr << 32) | rsr);
}
#endif

#ifdef ENTRY_USB_SNAPSHOT
/* Read-only MTU3 snapshot at LK handoff. The addresses come from the live
 * usb0 node (compatible mediatek,mtu3; reg-names mac, ippc), so nothing is
 * written and no SoC constant is assumed. Two 32-bit registers per field,
 * lower address in the high half. Field order is USB_FIELDS in
 * tools/mkentryprobe.py; stage is (0x60 << 16) | code:
 *   0 ok, 1 no MTU3 node, 2 unusable mac/ippc reg,
 *   3 device power domain down, MAC left unread.
 * The stage stays 0x5f if a read faults, so a partial snapshot is visible.
 * IPPC lives in the always-on infra block; the MAC may be clock-gated while
 * SSUSB_IP_DEV_PDN is set, so its reads are skipped in that case. */
static void
entryprobe_usb_snapshot(uintptr_t dtb, char *banner)
{
	char path[192];
	uint64_t mac = 0, mac_size = 0, ippc = 0, ippc_size = 0;

	field(banner, ENTRY_STAGE, 0x5f);
	if (!fdt_find_compatible(dtb, "mediatek,mtu3", path, sizeof(path))) {
		field(banner, ENTRY_STAGE, 0x6001);
		return;
	}
	if (!fdt_reg_n(dtb, path, 0, &mac, &mac_size) ||
	    !fdt_reg_n(dtb, path, 1, &ippc, &ippc_size) || !mac || !ippc) {
		field(banner, ENTRY_STAGE, 0x6002);
		return;
	}

	volatile uint32_t *i = (volatile uint32_t *)(uintptr_t)ippc;
	volatile uint32_t *m = (volatile uint32_t *)(uintptr_t)mac;

	field(banner, ENTRY_GICD, ((uint64_t)i[0x00 / 4] << 32) | i[0x04 / 4]);
	field(banner, ENTRY_VTIMER, ((uint64_t)i[0x08 / 4] << 32) | i[0x0c / 4]);
	field(banner, ENTRY_FB, ((uint64_t)i[0x10 / 4] << 32) | i[0x14 / 4]);
	field(banner, ENTRY_DTB, ((uint64_t)i[0x18 / 4] << 32) | i[0x40 / 4]);
	field(banner, ENTRY_SCTLR, ((uint64_t)i[0x30 / 4] << 32) | i[0x50 / 4]);
	field(banner, ENTRY_ESR, ((uint64_t)i[0x8c / 4] << 32) | i[0x98 / 4]);
	field(banner, ENTRY_FAR, ((uint64_t)i[0xa0 / 4] << 32) | i[0xa4 / 4]);
	if (i[0x08 / 4] & 1) {
		field(banner, ENTRY_STAGE, 0x6003);
		return;
	}

	field(banner, ENTRY_PC, ((uint64_t)m[0x0800 / 4] << 32) | m[0x0c84 / 4]);
	field(banner, ENTRY_FAULT, ((uint64_t)m[0x2404 / 4] << 32) | m[0x240c / 4]);
	field(banner, ENTRY_X0, ((uint64_t)m[0x141c / 4] << 32) | m[0x1534 / 4]);
	field(banner, ENTRY_X16, ((uint64_t)m[0x0000 / 4] << 32) | m[0x0004 / 4]);
	field(banner, ENTRY_SPSR, ((uint64_t)m[0x0100 / 4] << 32) | m[0x0108 / 4]);
	field(banner, ENTRY_STAGE, 0x6000);
}
#endif

#ifdef ENTRY_UFS_INIT
static void
entryprobe_ufs_init(char *banner)
{
	init_ufs_link(ENTRY_UFS_QUERY_MODE);
	field(banner, ENTRY_STAGE, 0x79);
	field(banner, ENTRY_ESR, ufs_test_stage);
	field(banner, ENTRY_FAR, ufs_test_info[0]);
	field(banner, ENTRY_X0, ufs_test_info[3]);	/* post-sense TUR */
	field(banner, ENTRY_X16, ufs_test_info[4]);	/* first SMC a0 */
	field(banner, ENTRY_DTB, ufs_test_info[5]);	/* device-init stage */
	field(banner, ENTRY_GICD, ufs_test_info[6]);	/* last query result */
	field(banner, ENTRY_VTIMER, ufs_test_info[7]);	/* query IDN/index/value */
	field(banner, ENTRY_FB, ufs_test_info[1]);	/* first TUR */
	field(banner, ENTRY_SPSR, ufs_test_info[2]);	/* REQUEST SENSE + sense data */
}
#endif

#ifdef ENTRY_UFS_TEST
/* Run the shim's own low-memory-UTRL takeover, TUR, READ CAPACITY and GPT
 * scan from the probe, then record the packed result. The XNU driver's UTRL
 * sits above 4 GiB; this distinguishes an address problem from a host that
 * stops processing commands after LK. The recorder fields are free at
 * el1-load (no XNU jump, no exception). */
static void
entryprobe_ufs_test(char *banner)
{
	test_ufs();
	/* The test results replace the pre-test snapshot fields. TUR and READ
	 * CAPACITY are packed as rc | OCS<<8 | status<<16 | resp0<<24 |
	 * resp6<<32 | resp7<<40. */
	field(banner, ENTRY_GICD, ufs_test_info[0]);
	field(banner, ENTRY_VTIMER, ufs_test_info[1]);
	field(banner, ENTRY_FB, ufs_test_info[2]);
	field(banner, ENTRY_DTB, ufs_test_info[3]);
	field(banner, ENTRY_X0, ufs_test_info[4]);
	field(banner, ENTRY_X16, ufs_test_info[5]);
	field(banner, ENTRY_SPSR, ufs_test_info[6]);
	field(banner, ENTRY_FAULT, ufs_test_info[7]);
	field(banner, ENTRY_ESR, ufs_test_stage);
}
#endif

void entryprobe_display(uint64_t dtb, char *banner);
#if defined(ENTRY_DISPLAY_KICK)
void entryprobe_display_kick(uint64_t dtb, char *banner);
#endif

void entryprobe_timer(uint64_t *dctlr, uint64_t *redist, uint64_t *flags);
void entryprobe_irq(uint64_t redist, uint64_t *count, uint64_t *last, uint64_t *rc);
#ifdef ENTRY_GPUEB_SNAPSHOT
void entryprobe_gpueb(uintptr_t dtb, char *banner);
#endif

void entryprobe_board(uint64_t dtb, char *banner)
{
#if defined(ENTRY_EL1_DISPLAY)
	field(banner, ENTRY_STAGE, 0x70);
#endif
	if (!board_probe((uintptr_t)dtb)) {
		field(banner, ENTRY_STAGE, 0xff);
		return;
	}
	field(banner, ENTRY_GICD, brd.gicd);
	field(banner, ENTRY_VTIMER, brd.vtimer_intid);
	field(banner, ENTRY_FB, brd.fb_base);
	field(banner, ENTRY_STAGE, 2);
#if defined(ENTRY_USB_SNAPSHOT)
	entryprobe_usb_snapshot((uintptr_t)dtb, banner);
#endif
#if defined(ENTRY_GPUEB_SNAPSHOT)
	entryprobe_gpueb((uintptr_t)dtb, banner);
#endif
#if defined(ENTRY_EL1_DISPLAY)
	/* Exercise the full shim's console/display at EL1, then return through
	 * HVC to the saved EL2 Linux entry. Exceptions carry ESR/FAR/PC into
	 * this same-boot banner instead of disappearing behind the LK logo. */
	uint64_t sctlr;
	__asm__ volatile("mrs %0, sctlr_el1" : "=r"(sctlr));
	field(banner, ENTRY_SCTLR, sctlr);
	field(banner, ENTRY_STAGE, 0x71);
	con_target((volatile uint32_t *)(uintptr_t)brd.fb_base);
	con_w = brd.fb_w;
	con_h = brd.fb_h;
	con_stride = brd.fb_stride;
	con_bgr = brd.fb_bgr;
	con_clear(BLUE);
	con_str("SWEET", "EL1 DISPLAY PROBE");
	field(banner, ENTRY_STAGE, 0x72);
	int rc = display_probe(dtb, brd.fb_base, brd.fb_stride);
	field(banner, ENTRY_ESR, display_error());
	field(banner, ENTRY_FAR, rc);
	field(banner, ENTRY_STAGE, 0x73);
	if (rc) {
		display_refresh();
		field(banner, ENTRY_STAGE, 0x74);
#if defined(ENTRY_LOADER_PROBE)
		loader_banner = banner;
#if defined(ENTRY_UFS_REGS)
		entryprobe_ufs_snapshot(banner);
#endif
#if defined(ENTRY_UFS_TEST)
		entryprobe_ufs_test(banner);
#endif
#if defined(ENTRY_UFS_INIT)
		entryprobe_ufs_init(banner);
#endif
		const char *why = loader_boot(dtb);
		con_str("LOADER", why);
		display_refresh();
		field(banner, ENTRY_STAGE, 0x7f);
#endif
	}
#else
#if ENTRY_LEVEL == 6
#if defined(ENTRY_XNU)
	/* Use the hardware-validated kick path to put a known image on the
	 * panel, then load the XNU payload with the real shim loader instead
	 * of returning to the stock Linux kernel. */
	entryprobe_display_kick(dtb, banner);
	loader_boot((uintptr_t)dtb);
	for (;;)
		__asm__ volatile("wfe");
#elif defined(ENTRY_DISPLAY_KICK)
	entryprobe_display_kick(dtb, banner);
#else
	entryprobe_display(dtb, banner);
#endif
	/* The display snapshot is intentionally read-only and does not progress
	 * into the MMU/timer/IRQ stages used by the other probe levels. */
#else
#if ENTRY_LEVEL == 2
	/* Unlike reboot-based experiments, /proc/pl_lk is read by Linux in
	 * THIS boot, before another preloader/LK run can replace its buffer. */
	logstore_mark("entry-probe", dtb, brd.vtimer_intid);
	field(banner, ENTRY_STAGE, 3);
#endif
#if ENTRY_LEVEL >= 3
	uint64_t el, sctlr, mmfr0;
	__asm__ volatile("mrs %0, CurrentEL" : "=r"(el));
	__asm__ volatile("mrs %0, sctlr_el1" : "=r"(sctlr));
	__asm__ volatile("mrs %0, id_aa64mmfr0_el1" : "=r"(mmfr0));
	field(banner, ENTRY_FAR, mmfr0);
	if (el != 4 || (sctlr & 1) || ((mmfr0 >> 20) & 15) == 0) {
		field(banner, ENTRY_STAGE, 0xfe);
		return;
	}
	struct mmu_info info;
	field(banner, ENTRY_STAGE, 4);
	int rc = mmu_enable(&info, brd.fb_base);
	field(banner, ENTRY_ESR, (uint32_t)rc);
	if (rc)
		return;
	field(banner, ENTRY_STAGE, 5);
	field(banner, ENTRY_FAR, mmu_probe((uintptr_t)entryprobe_board));
	field(banner, ENTRY_PC, info.sctlr_after);
#if ENTRY_LEVEL >= 4
	uint64_t dctlr, redist, flags;
	field(banner, ENTRY_STAGE, 6);
	entryprobe_timer(&dctlr, &redist, &flags);
	field(banner, ENTRY_ESR, dctlr);
	field(banner, ENTRY_FAR, redist);
	field(banner, ENTRY_PC, flags);
	field(banner, ENTRY_STAGE, 7);
#if ENTRY_LEVEL >= 5
	uint64_t irq_count, irq_last, irq_rc;
	field(banner, ENTRY_STAGE, 8);
	entryprobe_irq(redist, &irq_count, &irq_last, &irq_rc);
	field(banner, ENTRY_ESR, irq_rc);
	field(banner, ENTRY_FAR, irq_count);
	field(banner, ENTRY_PC, irq_last);
	field(banner, ENTRY_STAGE, 9);
#endif
#endif
#endif
#endif
#endif /* !ENTRY_EL1_DISPLAY */
}
