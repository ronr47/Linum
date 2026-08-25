global _start
section .text
_start:
    mov rdi, 42
    add rdi, 42
    xor rdi, 0xAA

    mov rax, 60
    syscall
