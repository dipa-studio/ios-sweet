	.section .rodata
	.balign 4
	.globl fts_fw_start
fts_fw_start:
	.incbin "test.ftb"
	.globl fts_fw_end
fts_fw_end:
	.section .note.GNU-stack,"",@progbits
