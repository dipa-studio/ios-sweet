#pragma once
/*
 * Per-board constants. Default is the original target (Redmi Note 10 Pro,
 * sweet, SM7150). Build with -DTARGET_MI8 for the Xiaomi Mi 8 (dipper,
 * SDM845); mi8/build-mi8.sh does that.
 */
#ifdef TARGET_MI8
/* Values from the live FDT and dmesg of a Mi 8 (see mi8/README.md). */
#define BOARD_NAME		"mi8 dipper sdm845"
#define FB_BASE			0x9d400000UL	/* reserved-memory cont_splash_region, 36 MB */
#define FB_W			1080
#define FB_H			2248		/* Samsung EA8074 AMOLED, DSI command mode */
#define FB_STRIDE		(FB_W * 4)	/* guess; mi8.c reads the real one from SSPP */
#define IMEM_RESTART_REASON	0x146bf65cUL	/* qcom,msm-imem restart_reason@65c */
#define TEXT_OFFSET		0x80000		/* same as the stock kernel Image header */
#else
#define BOARD_NAME		"sweet sm7150"
#define FB_BASE			0x9c000000UL	/* reserved-memory cont_splash_region */
#define FB_W			1080
#define FB_H			2400
#define FB_STRIDE		(FB_W * 4)	/* a8r8g8b8, matches mainline simplefb */
#define IMEM_RESTART_REASON	0x146aa65cUL	/* qcom,msm-imem restart_reason@65c */
#define TEXT_OFFSET		0
#endif
#define FB_PHYS			FB_BASE
