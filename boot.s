.section .text
.global _start

_start:
    # 1. Initialize the baseline stack framework pointer boundary
    movq $0x90000, %rsp
    
    # 2. Clear flags register state to normalize execution parameters
    pushq $0
    popfq

    # 3. Call the memory allocator check or jump straight to main loop
    xorq %rdi, %rdi
    
halt_loop:
    cli              # Disable hardware maskable interrupts
    hlt              # Halt the execution core until reset
    jmp halt_loop    # Absolute fallback loop catch boundary
