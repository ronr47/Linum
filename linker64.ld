OUTPUT_FORMAT("elf64-x86-64")
OUTPUT_ARCH(i386:x86-64)
ENTRY(_start64)

PHDRS {
    text PT_LOAD FLAGS(5); /* Read + Execute (R-X) */
    data PT_LOAD FLAGS(6); /* Read + Write   (RW-) */
}

SECTIONS {
    . = 0x10000;

    .text : {
        *(.text.entry)
        *(.text*)
        *(.rodata*)
    } :text

    . = ALIGN(4096);

    .data : {
        *(.data*)
        *(.bss*)
        *(COMMON)
    } :data

    /DISCARD/ : {
        *(.comment)
        *(.note*)
        *(.eh_frame*)
    }
}
