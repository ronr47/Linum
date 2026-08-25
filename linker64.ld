ENTRY(_start)

SECTIONS
{
    . = 1M;

    .text : ALIGN(4K) {
        *(.multiboot_header)
        *(.text*)
    }

    .rodata : ALIGN(4K) {
        *(.rodata*)
    }

    .data : ALIGN(64) {
        *(.data*)
    }

    .bss : ALIGN(64) {
        *(COMMON)
        *(.bss*)
    }

    /DISCARD/ : {
        *(.comment)
        *(.eh_frame)
    }
}
