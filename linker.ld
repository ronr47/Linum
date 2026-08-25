ENTRY(linum_entry)

SECTIONS
{
    . = 1M;

    .multiboot ALIGN(4) :
    {
        KEEP(*(.multiboot))
    }

    .text ALIGN(16) :
    {
        *(.text)
        *(.text.*)
    }

    .rodata ALIGN(4) :
    {
        *(.rodata)
        *(.rodata.*)
    }

    .data ALIGN(4) :
    {
        *(.data)
        *(.data.*)
    }

    .bss ALIGN(16) :
    {
        *(COMMON)
        *(.bss)
        *(.bss.*)
    }

    /DISCARD/ :
    {
        *(.eh_frame)
        *(.comment)
        *(.note*)
        *(.got*)
        *(.plt*)
    }
}
