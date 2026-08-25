    .text
    .globl pmm_mark_frame_allocated
    .globl pmm_allocate_free_frame
    .globl pmm_free_frame
    .globl physical_memory_bitmap

    .data
# 128 MB of physical memory = 32,768 frames.
# 32,768 bits / 64 = 512 words.
# 512 * 8 bytes = 4096 bytes (1 page).
    .comm physical_memory_bitmap, 4096, 16

    .text

# void pmm_mark_frame_allocated(unsigned long frame_number)
# Sets the bit for a frame to 1 (allocated).
pmm_mark_frame_allocated:
    pushq %rbp
    movq %rsp, %rbp
    
    # edi = frame_number
    
    # Calculate word index: frame_number / 64
    movl %edi, %eax
    sarl $6, %eax
    
    # Calculate bit offset: frame_number % 64
    movl %edi, %ecx
    andl $63, %ecx
    
    # Load the word
    movq physical_memory_bitmap(,%rax,8), %rdx
    
    # Set the bit: rdx |= (1 << rcx)
    movq $1, %rax
    shll %cl, %eax      # eax = 1 << bit_offset
    movl %eax, %esi     # Save mask in esi
    movq %rdx, %rax     # Copy word to rax
    btsq %rcx, %rax     # Set bit in rax
    
    # Store back
    movq %rax, physical_memory_bitmap(,%rdx,8) # Wait, rdx is the OLD word. 
    # We need the word index in rdx for the addressing mode.
    # Let's save word index in rbx.
    
    # Actually, let's just use rbx for word index.
    movl %edi, %ebx
    sarl $6, %ebx       # ebx = word index
    
    movq physical_memory_bitmap(,%rbx,8), %rax
    movl %edi, %ecx
    andl $63, %ecx
    movq $1, %rdx
    shll %cl, %edx
    orl %edx, %eax
    movq %rax, physical_memory_bitmap(,%rbx,8)
    
    popq %rbp
    retq

# unsigned long pmm_allocate_free_frame()
# Returns physical address of first free frame, or -1.
pmm_allocate_free_frame:
    pushq %rbp
    pushq %rbx
    pushq %rcx
    pushq %rdx
    movq %rsp, %rbp
    
    xorl %eax, %eax     # eax = current word index
    xorl %ebx, %ebx     # ebx = current word index (save)

.search_word:
    # Load word
    movq physical_memory_bitmap(,%rax,8), %rcx
    
    # Check if word is all 1s (0xFFFFFFFFFFFFFFFF)
    cmpq $-1, %rcx
    je .next_word
    
    # Find first zero bit
    notq %rcx
    bsfq %rcx, %rdx     # rdx = bit offset of first 0
    jc .next_word       # If carry set, no zero bits
    
    # Found a zero bit at %rdx
    # Mark it as allocated
    movq $1, %rax
    shll %dl, %eax      # eax = 1 << bit_offset
    movl %eax, %esi     # esi = mask
    
    # Load old word (using ebx as word index)
    movq physical_memory_bitmap(,%rbx,8), %rax
    orl %esi, %eax      # Set bit
    
    # Store back
    movq %rax, physical_memory_bitmap(,%rbx,8)
    
    # Calculate physical address: (word_index * 64 + bit_index) * 4096
    movq %rbx, %rax
    shlq $6, %rax       # rax = word_index * 64
    addq %rdx, %rax     # rax = word_index * 64 + bit_index
    shlq $12, %rax      # rax = physical address
    
    movq %rax, %rax     # Return in rax
    
    popq %rdx
    popq %rcx
    popq %rbx
    popq %rbp
    retq

.next_word:
    incq %rax           # Increment word index
    movq %rax, %rbx     # Save as ebx
    cmpq $512, %rax     # 512 words = 128MB
    jb .search_word
    
    # Not found
    movq $-1, %rax
    popq %rdx
    popq %rcx
    popq %rbx
    popq %rbp
    retq

# Free frame: clears the bit
pmm_free_frame:
    pushq %rbp
    movq %rsp, %rbp
    
    # edi = frame number
    movl %edi, %eax
    sarl $6, %eax       # word index
    
    movl %edi, %ecx
    andl $63, %ecx      # bit offset
    
    # Clear bit: rdx & ~(1 << bit)
    movq $1, %rax
    shll %cl, %eax      # eax = 1 << bit
    movq %rax, %rdx
    notq %rdx           # rdx = ~(1 << bit)
    
    movq physical_memory_bitmap(,%rax,8), %rax # Load word (rax is word index? No, eax is word index)
    # Wait, eax is word index.
    movq physical_memory_bitmap(,%rax,8), %rdx
    andq %rdx, %rax     # Clear bit
    movq %rax, physical_memory_bitmap(,%rax,8) # Store back
    
    popq %rbp
    retq
