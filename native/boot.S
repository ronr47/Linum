.section .note.pvh, "a", @note
    .align 4
    .long 4             /* namesz ("Xen\0") */
    .long 4             /* descsz (sizeof(pvh_start)) */
    .long 18            /* type (XEN_ELFNOTE_PHYS32_ENTRY) */
    .ascii "Xen\0"      /* name */
    .long _start        /* desc (32-bit physical entry address) */

.section .text.boot, "ax", @progbits
.code32
.global _start
_start:
    cli
    cld

    /* Set up stack */
    mov $stack_top, %esp

    /* Load 64-bit GDT */
    lgdt (gdt64_ptr)

    /* Enable PAE */
    mov %cr4, %eax
    or $(1 << 5), %eax
    mov %eax, %cr4

    /* Point CR3 to identity page table (level 4) */
    mov $pml4_table, %eax
    mov %eax, %cr3

    /* Enable Long Mode in EFER MSR */
    mov $0xC0000080, %ecx
    rdmsr
    or $(1 << 8), %eax
    wrmsr

    /* Enable Paging & Protected Mode in CR0 */
    mov %cr0, %eax
    or $(1 << 31 | 1 << 0), %eax
    mov %eax, %cr0

    /* Far jump into 64-bit code segment */
    ljmp $0x08, $long_mode_start

.code64
long_mode_start:
    /* Reload data segment registers */
    mov $0x10, %ax
    mov %ax, %ds
    mov %ax, %es
    mov %ax, %ss
    mov %ax, %fs
    mov %ax, %gs

    /* Set 64-bit stack pointer */
    lea stack_top(%rip), %rsp

    /* Jump to C kernel main */
    call kmain

hang:
    hlt
    jmp hang

/* --- Minimal Page Tables for 0-2MB Identity Mapping --- */
.section .data
.align 4096
pml4_table:
    .quad pdpt_table + 0x03     /* Present + Writable */
    .fill 511, 8, 0

pdpt_table:
    .quad page_dir + 0x03       /* Present + Writable */
    .fill 511, 8, 0

page_dir:
    .quad 0x000000 | 0x83       /* 2MB Huge Page (Present + Writable + PageSize) */
    .fill 511, 8, 0

/* --- Minimal 64-bit GDT --- */
.align 16
gdt64:
    .quad 0                     /* Null descriptor */
    .quad 0x00209A0000000000    /* 64-bit Code Segment (0x08) */
    .quad 0x0000920000000000    /* 64-bit Data Segment (0x10) */
gdt64_end:

gdt64_ptr:
    .word gdt64_end - gdt64 - 1
    .long gdt64

.section .bss
.align 16
stack_bottom:
    .skip 16384
stack_top:
