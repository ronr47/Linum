ENTRY(_start)

SECTIONS
{
    . = 1M;

    .note.pvh : {
        KEEP(*(.note.pvh))
    }

    .text ALIGN(64) : {
        *(.text.boot)
        *(.text .text.*)
    }

    .rodata ALIGN(64) : {
        *(.rodata .rodata.*)
    }

    .data ALIGN(64) : {
        *(.data .data.*)
    }

    .bss ALIGN(64) : {
        __bss_start = .;
        *(.bss .bss.*)
        *(COMMON)
        __bss_end = .;
    }

    /DISCARD/ : {
        *(.comment)
        *(.eh_frame)
    }
}
