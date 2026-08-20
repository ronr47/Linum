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

    ; 1. Initialize COM1 Serial Port (0x3F8, 115200 baud, 8N1)
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

    mov si, msg_mbr
    call uart_puts16

    ; 2. Load 64 sectors of Kernel payload from disk into 0x10000 (0x1000:0x0000)
    mov ax, 0x1000
    mov es, ax
    xor bx, bx
    mov ah, 0x02
    mov al, 64
    mov ch, 0
    mov cl, 2
    mov dh, 0
    mov dl, [BOOT_DRIVE]
    int 0x13
    jnc disk_loaded
    hlt

disk_loaded:
    ; 3. Enable A20 Line
    in al, 0x92
    or al, 2
    out 0x92, al

    ; 4. Enter 32-bit Protected Mode
    lgdt [gdt32_descriptor]
    mov eax, cr0
    or eax, 1
    mov cr0, eax
    jmp 0x08:pm32_entry

uart_puts16:
    lodsb
    test al, al
    jz .done
    mov dx, 0x3FD
.wait:
    in al, dx
    test al, 0x20
    jz .wait
    mov dx, 0x3F8
    mov al, [si-1]
    out dx, al
    jmp uart_puts16
.done:
    ret

; ==============================================================================
; 32-BIT PROTECTED MODE (Setup Paging & Enable Hardware SSE)
; ==============================================================================
[BITS 32]
pm32_entry:
    mov ax, 0x10
    mov ds, ax
    mov es, ax
    mov fs, ax
    mov gs, ax
    mov ss, ax
    mov esp, 0x7C00

    ; Zero out 16 KB for page tables at 0x70000
    mov edi, 0x70000
    xor eax, eax
    mov ecx, 4096
    rep stosd

    ; PML4[0] at 0x70000 -> PDPT at 0x71000
    mov dword [0x70000], 0x71003
    ; PDPT[0] at 0x71000 -> PageDirectory at 0x72000
    mov dword [0x71000], 0x72003

    ; PageDirectory[0..7] at 0x72000 -> 8 x 2MB huge pages (0 to 16 MB identity mapped)
    mov dword [0x72000], 0x00000083
    mov dword [0x72008], 0x00200083
    mov dword [0x72010], 0x00400083
    mov dword [0x72018], 0x00600083
    mov dword [0x72020], 0x00800083
    mov dword [0x72028], 0x00A00083
    mov dword [0x72030], 0x00C00083
    mov dword [0x72038], 0x00E00083

    ; 5. Enable PAE, OSFXSR (SSE), and OSXMMEXCPT in CR4
    mov eax, cr4
    or eax, (1 << 5) | (1 << 9) | (1 << 10)
    mov cr4, eax

    ; 6. Enable MP and clear EM in CR0
    mov eax, cr0
    and eax, ~(1 << 2)          ; Clear EM (Emulation)
    or eax, (1 << 1)            ; Set MP (Monitor Coprocessor)
    mov cr0, eax

    ; 7. Enable LME (Long Mode Enable) in EFER MSR
    mov ecx, 0xC0000080
    rdmsr
    or eax, (1 << 8)
    wrmsr

    ; 8. Load CR3 with PML4 Base
    mov eax, 0x70000
    mov cr3, eax

    ; 9. Enable Paging (PG)
    mov eax, cr0
    or eax, (1 << 31)
    mov cr0, eax

    ; 10. Load 64-bit GDT & Jump into Long Mode
    lgdt [gdt64_descriptor]
    jmp 0x08:long_mode_entry

[BITS 64]
long_mode_entry:
    mov ax, 0x10
    mov ds, ax
    mov es, ax
    mov fs, ax
    mov gs, ax
    mov ss, ax
    mov rsp, 0x80000

    mov rax, 0x10000
    jmp rax

BOOT_DRIVE: db 0
msg_mbr: db "[+] STAGE-1 (MBR): Booting 64-bit Long Mode Exokernel...", 13, 10, 0

align 8
gdt32_start:
    dq 0x0000000000000000
    dq 0x00CF9A000000FFFF       ; 32-bit Code (0x08)
    dq 0x00CF92000000FFFF       ; 32-bit Data (0x10)
gdt32_end:

gdt32_descriptor:
    dw gdt32_end - gdt32_start - 1
    dd gdt32_start

align 8
gdt64_start:
    dq 0x0000000000000000       ; Null
    dq 0x00209A0000000000       ; 64-bit Code (0x08)
    dq 0x0000920000000000       ; 64-bit Data (0x10)
gdt64_end:

gdt64_descriptor:
    dw gdt64_end - gdt64_start - 1
    dd gdt64_start

times 510 - ($ - $$) db 0
dw 0xAA55
