.intel_syntax noprefix
.text
.globl linum_vector_attention_stream
.type linum_vector_attention_stream, @function

# Signature:
# uint32_t linum_vector_attention_stream(
#     const float* q (RDI), 
#     const float* k (RSI), 
#     const float* v (RDX), 
#     float* out (RCX), 
#     uint32_t len (R8D)
# )
linum_vector_attention_stream:
    # 1. Null-pointer safety check
    test rdi, rdi
    jz .e_ptr_fault
    test rsi, rsi
    jz .e_ptr_fault
    test rdx, rdx
    jz .e_ptr_fault
    test rcx, rcx
    jz .e_ptr_fault

    # 2. 64-byte alignment check (Axiom 2)
    test rdi, 0x3F
    jnz .e_align_fault
    test rsi, 0x3F
    jnz .e_align_fault
    test rdx, 0x3F
    jnz .e_align_fault
    test rcx, 0x3F
    jnz .e_align_fault

    # 3. Vector computation loop (out[i] = (q[i] * k[i]) * v[i])
    xor rax, rax
    mov r9d, r8d
    shr r9d, 2          # Process 4 floats (128-bit SSE) per iteration
    jz .tail_scalar

.loop_simd:
    movups xmm0, [rdi + rax*4]      # Load Q
    movups xmm1, [rsi + rax*4]      # Load K
    mulps  xmm0, xmm1               # Score = Q * K
    movups xmm2, [rdx + rax*4]      # Load V
    mulps  xmm0, xmm2               # Attention Output = Score * V
    movups [rcx + rax*4], xmm0      # Store Out
    add rax, 4
    dec r9d
    jnz .loop_simd

.tail_scalar:
    mov r9d, r8d
    and r9d, 3          # Remaining elements
    jz .success

.loop_scalar:
    movss xmm0, [rdi + rax*4]
    mulss xmm0, [rsi + rax*4]
    mulss xmm0, [rdx + rax*4]
    movss [rcx + rax*4], xmm0
    inc rax
    dec r9d
    jnz .loop_scalar

.success:
    mov eax, 0x00000000             # LINUM_SYS_SUCCESS (0)
    ret

.e_ptr_fault:
    mov eax, 0xEE000001             # LINUM_SYS_E_PTR_FAULT
    ret

.e_align_fault:
    mov eax, 0xEE000002             # LINUM_SYS_E_ALIGN_FAULT
    ret
