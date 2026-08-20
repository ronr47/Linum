OUTPUT_FORMAT("elf64-x86-64")
ENTRY(_start64)

SECTIONS
{
    . = 0x10000;

    .text.entry : {
        *(.text.entry)
    }

    .text : {
        *(.text*)
    }

    .rodata : {
        *(.rodata*)
    }

    .data : {
        *(.data*)
    }

    .bss : {
        *(.bss*)
        *(COMMON)
    }
}
