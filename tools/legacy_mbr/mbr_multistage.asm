[BITS 16]
[ORG 0x7C00]

start:
    cli
    xor ax, ax
    mov ds, ax
    mov es, ax
    mov ss, ax
    mov sp, 0x7C00

    mov [BOOT_DRIVE], dl

    ; 1. Setup COM1 Serial Port (0x3F8)
    mov dx, 0x3F9
    xor al, al
    out dx, al
    mov dx, 0x3FB
    mov al, 0x80
    out dx, al
    mov dx, 0x3F8
    mov al, 0x01
    out dx, al
    mov dx, 0x3F9
    xor al, al
    out dx, al
    mov dx, 0x3FB
    mov al, 0x03
    out dx, al

    mov si, msg_stage1
    call print_serial_16

    ; 2. Read Stage-2 Kernel (Sectors 2..15 -> 0x10000)
    mov ax, 0x1000
    mov es, ax
    xor bx, bx

    mov ah, 0x02
    mov al, 14
    mov ch, 0
    mov cl, 2
    mov dh, 0
    mov dl, [BOOT_DRIVE]
    int 0x13
    jnc disk_ok

    mov si, msg_disk_err
    call print_serial_16
    hlt

disk_ok:
    mov si, msg_loaded
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
.wait:
    in al, dx
    test al, 0x20
    jz .wait
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
    mov fs, ax
    mov gs, ax
    mov ss, ax

    ; 5. 4-Level Paging (0-4MB Identity Map)
    mov edi, 0x1000
    xor eax, eax
    mov ecx, 4096
    rep stosd

    mov dword [0x1000], 0x2003      ; PML4 -> PDPT
    mov dword [0x2000], 0x3003      ; PDPT -> PD
    mov dword [0x3000], 0x00000083  ; PD[0] -> 2MB (PS=1)
    mov dword [0x3008], 0x00200083  ; PD[1] -> Next 2MB (0-4MB)

    mov eax, 0x1000
    mov cr3, eax

    mov eax, cr4
    or eax, (1 << 5)                ; PAE
    mov cr4, eax

    mov ecx, 0xC0000080             ; EFER MSR
    rdmsr
    or eax, (1 << 8)                ; LME
    wrmsr

    mov eax, cr0
    or eax, (1 << 31)               ; Paging
    mov cr0, eax

    jmp 0x18:init_lm64

[BITS 64]
init_lm64:
    mov ax, 0x10
    mov ds, ax
    mov es, ax
    mov ss, ax

    ; 6. Set 64-bit Stack Pointer (RSP) to 0x70000 (Safe, 16-byte aligned)
    mov rsp, 0x70000

    ; 7. Direct Jump to Stage-2 Kernel at 0x10000
    mov rax, 0x10000
    jmp rax

BOOT_DRIVE: db 0
msg_stage1:   db 13, 10, "[+] STAGE-1 (MBR): Booting and Initializing UART...", 13, 10, 0
msg_loaded:   db "[+] STAGE-1 (MBR): Sectors 2..15 Loaded to 0x10000 via BIOS INT 13h.", 13, 10, 0
msg_disk_err: db "[!] Disk Read Error!", 13, 10, 0

align 8
gdt_start:
    dq 0x0000000000000000
    dq 0x00CF9A000000FFFF         ; 32-bit Code (0x08)
    dq 0x00CF92000000FFFF         ; 32-bit Data (0x10)
    dq 0x00AF9A000000FFFF         ; 64-bit Code (0x18)
gdt_end:

gdt_descriptor:
    dw gdt_end - gdt_start - 1
    dd gdt_start

times 510 - ($ - $$) db 0
dw 0xAA55
