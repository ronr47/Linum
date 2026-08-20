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

    ; 1. Initialize COM1 Serial Port (0x3F8)
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

    mov si, msg_boot
    call print_serial_16

    ; 2. Read Stage-2 payload into low buffer at 0x2000:0x0000 (0x20000 physical)
    mov ax, 0x2000
    mov es, ax
    xor bx, bx

    mov ah, 0x02
    mov al, 16          ; Read 16 sectors (8 KB)
    mov ch, 0
    mov cl, 2
    mov dh, 0
    mov dl, [BOOT_DRIVE]
    int 0x13
    jnc disk_ok

    mov si, msg_err
    call print_serial_16
    hlt

disk_ok:
    mov si, msg_loaded
    call print_serial_16

    ; 3. Enable A20 Line
    in al, 0x92
    or al, 2
    out 0x92, al

    ; 4. Load 32-bit GDT & Enter Protected Mode
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
    mov esp, 0x90000

    ; 5. Copy loaded payload from low buffer (0x20000) to 1MB Barrier (0x100000)
    mov esi, 0x20000
    mov edi, 0x100000
    mov ecx, 2048       ; 2048 dwords = 8192 bytes
    rep movsd

    ; 6. Jump directly to beast_surprise entry point at 0x100030
    mov eax, 0x100030
    jmp eax

BOOT_DRIVE: db 0
msg_boot:   db 13, 10, "[+] MBR: Booting 32-bit Protected Mode Loader...", 13, 10, 0
msg_loaded: db "[+] MBR: beast_surprise payload loaded, jumping to 0x100030...", 13, 10, 0
msg_err:    db "[!] Disk Read Error!", 13, 10, 0

align 8
gdt_start:
    dq 0x0000000000000000
    ; 32-bit Code Segment (0x08, Base=0, Limit=4GB)
    dq 0x00CF9A000000FFFF
    ; 32-bit Data Segment (0x10, Base=0, Limit=4GB)
    dq 0x00CF92000000FFFF
gdt_end:

gdt_descriptor:
    dw gdt_end - gdt_start - 1
    dd gdt_start

times 510 - ($ - $$) db 0
dw 0xAA55
