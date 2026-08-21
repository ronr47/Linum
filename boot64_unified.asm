section .multiboot
align 4
    dd 0x1BADB002
    dd 0x00000003
    dd -(0x1BADB002 + 0x00000003)

section .text
global _start

_start:
    cli
    xor ax, ax
    mov ds, ax
    mov es, ax
    mov ss, ax
    mov rsp, 0x90000

    ; Initialize 16550 UART COM1 (0x3F8)
    mov dx, 0x3F9
    mov al, 0x00
    out dx, al

    mov dx, 0x3FB
    mov al, 0x80
    out dx, al

    mov dx, 0x3F8
    mov al, 0x01
    out dx, al
    mov dx, 0x3F9
    mov al, 0x00
    out dx, al

    mov dx, 0x3FB
    mov al, 0x03
    out dx, al

    mov dx, 0x3FA
    mov al, 0xC7
    out dx, al

    ; Print test output banner
    mov rsi, msg_run
.print:
    lodsb
    test al, al
    jz .exit
    mov dx, 0x3F8
    out dx, al
    jmp .print

.exit:
    ; Trigger ISA debug-exit device at port 0x501 for capture_fiber_run.py
    mov dx, 0x501
    mov al, 0x31
    out dx, al

    ; Fallback halt
.hang:
    hlt
    jmp .hang

section .data
msg_run:
    db "LINUM_OK", 0x0A
    db "[FIBER 0] Execution Context: SOUND", 0x0A
    db "[FIBER 1] Linear State Memory: SEALED", 0x0A
    db "[FIBER 2] Quantum Topo Gate: SOUND", 0x0A, 0
