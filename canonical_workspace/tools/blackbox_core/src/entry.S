.global _start
.text

_start:
    mov x29, #0
    mov x30, #0
    ldr x0, [sp]
    add x1, sp, #8
    and sp, x1, #-16
    bl blackbox_main
    mov x1, x0
    mov x8, #93
    svc #0
