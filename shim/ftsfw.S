/* Embeds the touch controller firmware (the ROM's st_fts_e1.ftb) for the Mi 8 touch probe. Only assembled when
 * mi8/fw/st_fts_e1.ftb exists (mi8/build-mi8.sh copies it next to the objects and passes -I). */
	.section .rodata.ftsfw, "a"
	.balign 4
	.globl	fts_fw_start
fts_fw_start:
	.incbin	"st_fts_e1.ftb"
	.globl	fts_fw_end
fts_fw_end:
