/* Linker script for M30s boot shim */
ENTRY(_start)

SECTIONS
{
	. = 0;
	.text.head :
	{
		*(.text.head)
	}

	.text :
	{
		*(.text*)
	}

	.rodata :
	{
		*(.rodata*)
	}

	.data :
	{
		*(.data*)
	}

	.bss :
	{
		_bss_start = .;
		*(.bss*)
		*(COMMON)
		_bss_end = .;
	}

	_end = .;
}