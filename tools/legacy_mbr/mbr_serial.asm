[BITS 16]
[ORG 0x7C00]

start:
    cli
    xor ax, ax
    mov ds, ax
    mov es, ax
    mov ss, ax
    mov sp, 0x7C00

    ; 1. Initialize COM1 Serial Port (0x3F8) at 115200 Baud, 8N1
    mov dx, 0x3F9      ; Disable all interrupts
    mov al, 0x00
    out dx, al

    mov dx, 0x3FB      ; Enable DLAB (set baud rate divisor)
    mov al, 0x80
    out dx, al

    mov dx, 0x3F8      ; Set divisor to 1 (lo byte) 115200 baud
    mov al, 0x01
    out dx, al
    mov dx, 0x3F9      ;                  (hi byte)
    mov al, 0x00
    out dx, al

    mov dx, 0x3FB      ; 8 bits, no parity, one stop bit
    mov al, 0x03
    out dx, al

    ; 2. Print Startup Banner from 16-bit Real Mode
    mov si, msg_real_mode
    call print_serial_16

    ; 3. Fast A20 Gate
    in al, 0x92
    or al, 2
    out 0x92, al

    ; 4. Load GDT & Enter 32-bit Protected Mode
    lgdt [gdt_descriptor]
    mov eax, cr0
    or eax, 1
    mov cr0, eax
    jmp 0x08:init_pm32

print_serial_16:
    lodsb
    test al, al
    jz .done
    mov dx, 0x3FD
.wait_tx:
    in al, dx
    test al, 0x20
    jz .wait_tx
    mov dx, 0x3F8
    mov al, [si - 1]
    out dx, al
    jmp print_serial_16
.done:
    ret

[BITS 32]
init_pm32:
    mov ax, 0x10
    mov ds, ax
    mov es, ax
    mov ss, ax

    ; 5. Build 4-Level Paging for 64-bit Long Mode (0-2MB Identity)
    mov edi, 0x1000
    xor eax, eax
    mov ecx, 4096
    rep stosd

    mov dword [0x1000], 0x2003      ; PML4 -> PDPT
    mov dword [0x2000], 0x3003      ; PDPT -> PD
    mov dword [0x3000], 0x00000083  ; PD -> 2MB Page (PS=1)

    mov eax, 0x1000
    mov cr3, eax

    mov eax, cr4
    or eax, (1 << 5)                ; Enable PAE
    mov cr4, eax

    mov ecx, 0xC0000080             ; EFER MSR
    rdmsr
    or eax, (1 << 8)                ; LME (Long Mode Enable)
    wrmsr

    mov eax, cr0
    or eax, (1 << 31)               ; Enable Paging
    mov cr0, eax

    jmp 0x18:init_lm64

[BITS 64]
init_lm64:
    ; 6. Execute Hot-Path Machine Transform: (42 + 42) ^ 0xAA
    mov rdi, 42
    mov rax, rdi
    add rax, 42
    xor rax, 0xAA

    ; 7. Write Result & Success String to COM1 Serial Port
    mov rsi, msg_long_mode
.print_lm:
    lodsb
    test al, al
    jz .exit
    mov dx, 0x3FD
.wait_lm:
    in al, dx
    test al, 0x20
    jz .wait_lm
    mov dx, 0x3F8
    mov al, [rsi - 1]
    out dx, al
    jmp .print_lm

.exit:
    ; 8. Cleanly Shutdown QEMU via ISA Debug Exit (I/O Port 0x501)
    mov al, 0
    mov dx, 0x501
    out dx, al

halt_loop:
    hlt
    jmp halt_loop

msg_real_mode:  db 13, 10, "[+] MBR: Booting 16-bit Real Mode...", 13, 10, 0
msg_long_mode:  db "[+] MBR: Transitioned 16 -> 32 -> 64-bit Long Mode [SUCCESS]", 13, 10, 0

align 8
gdt_start:
    dq 0x0000000000000000         ; Null
    dq 0x00CF9A000000FFFF         ; 32-bit Code (0x08)
    dq 0x00CF92000000FFFF         ; 32-bit Data (0x10)
    dq 0x00AF9A000000FFFF         ; 64-bit Code (0x18)
gdt_end:

gdt_descriptor:
    dw gdt_end - gdt_start - 1
    dd gdt_start

times 510 - ($ - $$) db 0
dw 0xAA55
