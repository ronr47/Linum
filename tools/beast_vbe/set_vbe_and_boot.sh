#!/usr/bin/env bash
set -euo pipefail

cd /home/ron/linum

# Add VBE mode switch (1024x768x32, LFB enabled, BXT_ENABLE) into MBR
cat << 'ASMEOD' > mbr_beast_vbe.asm
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

    ; 2. Configure Bochs/QEMU VBE Direct I/O (1024x768x32 LFB)
    ; Index 1 = XRES (1024)
    mov dx, 0x01CE
    mov ax, 1
    out dx, ax
    inc dx
    mov ax, 1024
    out dx, ax

    ; Index 2 = YRES (768)
    dec dx
    mov ax, 2
    out dx, ax
    inc dx
    mov ax, 768
    out dx, ax

    ; Index 3 = BPP (32)
    dec dx
    mov ax, 3
    out dx, ax
    inc dx
    mov ax, 32
    out dx, ax

    ; Index 4 = ENABLE | LFB (0x01 | 0x40 = 0x41)
    dec dx
    mov ax, 4
    out dx, ax
    inc dx
    mov ax, 0x41
    out dx, ax

    ; 3. Read Stage-2 payload into low buffer at 0x2000:0x0000 (0x20000 physical)
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
    hlt

disk_ok:
    ; 4. Enable A20 Line
    in al, 0x92
    or al, 2
    out 0x92, al

    ; 5. Load GDT & Enter 32-bit Protected Mode
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

    ; Copy payload from 0x20000 to 0x100000
    mov esi, 0x20000
    mov edi, 0x100000
    mov ecx, 2048
    rep movsd

    ; Jump to beast_surprise entry point
    mov eax, 0x100030
    jmp eax

BOOT_DRIVE: db 0

align 8
gdt_start:
    dq 0x0000000000000000
    dq 0x00CF9A000000FFFF         ; 32-bit Code (0x08)
    dq 0x00CF92000000FFFF         ; 32-bit Data (0x10)
gdt_end:

gdt_descriptor:
    dw gdt_end - gdt_start - 1
    dd gdt_start

times 510 - ($ - $$) db 0
dw 0xAA55
ASMEOD

# Assemble and rebuild disk
nasm -f bin mbr_beast_vbe.asm -o mbr_beast_vbe.bin
objcopy -O binary beast_surprise.elf beast_surprise.bin
cat mbr_beast_vbe.bin beast_surprise.bin > beast_disk.bin
truncate -s 16384 beast_disk.bin

# Run screendump test
python3 capture_beast_screen.py
