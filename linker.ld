ENTRY(_start)
PHDRS {
    text PT_LOAD FLAGS(5);
    rodata PT_LOAD FLAGS(4);
}
SECTIONS {
    . = 0x400000;
    .text : ALIGN(64) { *(.text._start) *(.text*) } :text
    . = ALIGN(64);
    .rodata : ALIGN(64) { *(.rodata*) } :rodata
    /DISCARD/ : {
        *(.comment) *(.note*) *(.eh_frame*) *(.interp) *(.dynamic)
    }
}
