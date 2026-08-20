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

    ; Setup Bochs VBE direct I/O for 1024x768x32 LFB
    mov dx, 0x01CE
    mov ax, 1
    out dx, ax
    inc dx
    mov ax, 1024
    out dx, ax

    dec dx
    mov ax, 2
    out dx, ax
    inc dx
    mov ax, 768
    out dx, ax

    dec dx
    mov ax, 3
    out dx, ax
    inc dx
    mov ax, 32
    out dx, ax

    dec dx
    mov ax, 4
    out dx, ax
    inc dx
    mov ax, 0x41        ; VBE_ENABLE | VBE_LFB
    out dx, ax

    ; Read Stage-2 sectors to 0x20000
    mov ax, 0x2000
    mov es, ax
    xor bx, bx
    mov ah, 0x02
    mov al, 16
    mov ch, 0
    mov cl, 2
    mov dh, 0
    mov dl, [BOOT_DRIVE]
    int 0x13
    jnc disk_ok
    hlt

disk_ok:
    in al, 0x92
    or al, 2
    out 0x92, al

    lgdt [gdt_descriptor]
    mov eax, cr0
    or eax, 1
    mov cr0, eax
    jmp 0x08:init_pm32

[BITS 32]
init_pm32:
    mov ax, 0x10
    mov ds, ax
    mov es, ax
    mov fs, ax
    mov gs, ax
    mov ss, ax
    mov esp, 0x90000

    mov esi, 0x20000
    mov edi, 0x100000
    mov ecx, 2048
    rep movsd

    mov eax, 0x100030
    jmp eax

BOOT_DRIVE: db 0
align 8
gdt_start:
    dq 0x0000000000000000
    dq 0x00CF9A000000FFFF
    dq 0x00CF92000000FFFF
gdt_end:
gdt_descriptor:
    dw gdt_end - gdt_start - 1
    dd gdt_start
times 510 - ($ - $$) db 0
dw 0xAA55
