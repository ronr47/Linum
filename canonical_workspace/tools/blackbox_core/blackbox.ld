ENTRY(_start)

PHDRS
{
    text PT_LOAD FLAGS(5);
    rodata PT_LOAD FLAGS(4);
    data PT_LOAD FLAGS(6);
}

SECTIONS
{
    . = 0x400000;

    .text : ALIGN(65536) {
        *(.text .text.*)
    } :text

    .rodata : ALIGN(65536) {
        *(.rodata .rodata.*)
    } :rodata

    .data : ALIGN(65536) {
        *(.data .data.*)
        *(.bss .bss.*)
    } :data

    /DISCARD/ : {
        *(.comment)
        *(.note*)
        *(.eh_frame*)
    }
}
