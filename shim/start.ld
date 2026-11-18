
ENTRY(_head)

SECTIONS
{
    . = 0;

    .text : {
        KEEP(*(.text.head))
        *(.text*)
    }

    .rodata : {
        *(.rodata*)
    }

    .data : {
        *(.data*)
    }

    . = ALIGN(16);

    _bss_start = .;

    .bss (NOLOAD) : {
        *(.bss*)
        *(COMMON)
    }

    . = ALIGN(4096);
    . += 0x4000;
    _stack_top = .;

    _end = .;

    /DISCARD/ : {
        *(.comment)
        *(.note*)
        *(.eh_frame*)
    }
}
