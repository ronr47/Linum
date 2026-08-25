/* Force explicit section mapping with allocations enabled */
.section .multiboot, "a"
.align 4
.long 0x1BADB002               /* Multiboot Magic */
.long 0x00                     /* Flags */
.long -(0x1BADB002 + 0x00)     /* Checksum (must sum to zero) */

.section .text
.global _start
.extern microkernel_init

_start:
    cli
    mov $0x100000, %rsp       /* Set the stack boundary at the 1MB ceiling */
    call microkernel_init     /* FFI jump to your microkernel logic */

.hang:
    cli
    hlt
    jmp .hang
