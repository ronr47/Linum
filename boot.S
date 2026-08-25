.code32

.section .multiboot,"a"
.align 4

.long 0x1BADB002
.long 0x00000000
.long -(0x1BADB002 + 0x00000000)

.section .text
.globl linum_entry
.type linum_entry, @function
.extern kernel_main

linum_entry:
    cli

    # Temporary kernel stack at 2 MiB.
    movl $0x200000, %esp

    # kernel_main(12, 16)
    pushl $16
    pushl $12
    call kernel_main

.hang:
    hlt
    jmp .hang

.size linum_entry, .-linum_entry
