[BITS 16]
[ORG 0x7C00]

start:
    cli
    xor ax, ax
    mov ds, ax
    mov es, ax
    mov ss, ax
    mov sp, 0x7C00

    ; 1. Enable A20 Line via Fast A20 Gate
    in al, 0x92
    or al, 2
    out 0x92, al

    ; 2. Load Global Descriptor Table
    lgdt [gdt_descriptor]

    ; 3. Enter 32-bit Protected Mode
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

    ; 4. Build Identity Paging (4-Level Page Tables for x86-64)
    ; Clear 16KB for PML4, PDPT, PD, PT at 0x1000
    mov edi, 0x1000
    xor eax, eax
    mov ecx, 4096
    rep stosd

    ; Link PML4 -> PDPT -> PD -> 2MB Identity Page
    mov dword [0x1000], 0x2003      ; PML4[0] -> PDPT
    mov dword [0x2000], 0x3003      ; PDPT[0] -> PD
    mov dword [0x3000], 0x00000083  ; PD[0]   -> 2MB Page (Identity map 0-2MB, PS=1)

    ; Load CR3 (PML4 Base)
    mov eax, 0x1000
    mov cr3, eax

    ; Enable PAE (Physical Address Extension) in CR4
    mov eax, cr4
    or eax, (1 << 5)
    mov cr4, eax

    ; Enable Long Mode in EFER MSR
    mov ecx, 0xC0000080
    rdmsr
    or eax, (1 << 8)
    wrmsr

    ; Enable Paging in CR0 -> Enters 64-bit Compatibility / Long Mode
    mov eax, cr0
    or eax, (1 << 31)
    mov cr0, eax

    ; Jump to 64-bit Code Segment
    jmp 0x18:init_lm64

[BITS 64]
init_lm64:
    ; 5. Pure Bare-Metal Execution
    ; Run the affine transform: (0x12345678 + 42) ^ 0xAA
    mov edi, 0x12345678
    mov eax, edi
    add eax, 42
    xor eax, 0xAA

    ; 6. Write status to VGA Text Buffer (0xB8000)
    ; 'O' (0x4F) and 'K' (0x4B) with Green/Black attribute (0x02)
    mov rbx, 0xB8000
    mov word [rbx], 0x024F        ; 'O'
    mov word [rbx + 2], 0x024B    ; 'K'

halt_loop:
    hlt
    jmp halt_loop

; --- GDT Setup ---
align 8
gdt_start:
    dq 0x0000000000000000         ; Null Descriptor
    ; 32-bit Code Segment (0x08)
    dq 0x00CF9A000000FFFF
    ; 32-bit Data Segment (0x10)
    dq 0x00CF92000000FFFF
    ; 64-bit Code Segment (0x18)
    dq 0x00AF9A000000FFFF
gdt_end:

gdt_descriptor:
    dw gdt_end - gdt_start - 1
    dd gdt_start

; --- Boot Sector Padding (Exactly 512 bytes) ---
times 510 - ($ - $$) db 0
dw 0xAA55
