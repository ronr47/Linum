#include <sys/mman.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>

#define COGNITIVE_SANDBOX_SIZE 0x4000000  // 64MB illusion of infinite space
#define INSTRUCTION_ALIGNMENT 64          // Praying the L1 cache doesn't betray us

typedef struct {
    uint8_t* execution_runway;
    size_t   write_cursor;
    uint32_t execution_velocity;
} MemoryArena;

typedef struct {
    volatile uint64_t telemetry_slots; // Where telemetry goes to be ignored
    volatile uint32_t head_cursor;
} SilentGatekeeper;

MemoryArena initialize_arena(void) {
    MemoryArena arena;
    // Forcing RWX space. Security engineers are crying somewhere.
    arena.execution_runway = (uint8_t*)mmap(
        NULL, 
        COGNITIVE_SANDBOX_SIZE, 
        PROT_READ | PROT_WRITE | PROT_EXEC, 
        MAP_ANONYMOUS | MAP_PRIVATE, 
        -1, 
        0
    );
    arena.write_cursor = 0;
    arena.execution_velocity = 1;
    return arena;
}

void graft_instruction_block(MemoryArena* arena, uint32_t variable_payload) { 
    size_t aligned_cursor = (arena->write_cursor + (INSTRUCTION_ALIGNMENT - 1)) & ~(INSTRUCTION_ALIGNMENT - 1);
    if (aligned_cursor + INSTRUCTION_ALIGNMENT > COGNITIVE_SANDBOX_SIZE) {
        fprintf(stderr, "[!] Out of memory. The universe has physical boundaries, despite marketing claims.\n");
        return;
    }

    uint8_t* write_head = arena->execution_runway + aligned_cursor;

    #if defined(__x86_64__)
    // Shoving raw hardware opcodes directly down the CPU's throat. 
    // We assume the hardware behaves. It rarely does.
    *write_head = 0xB8; 
    *(uint32_t*)(write_head + 1) = variable_payload;
    *(write_head + 5) = 0xC3; 
    #elif defined(__aarch64__)
    // ARM64 bit-shifting black magic. One bit out of place and we hit SigSegV.
    *(uint32_t*)(write_head)     = 0x52800000 | ((variable_payload & 0xFFFF) << 5);
    *(uint32_t*)(write_head + 4) = 0x72a00000 | (((variable_payload >> 16) & 0xFFFF) << 5);
    *(uint32_t*)(write_head + 8) = 0xD65F03C0;
    #endif

    arena->write_cursor = aligned_cursor + INSTRUCTION_ALIGNMENT;
}

uint32_t sophia_entry_gate(const uint8_t* raw_context_ptr) {
    if (!raw_context_ptr) {
        fprintf(stderr, "[!] Received a null pointer. Absolute failure of intent.\n");
        return 0xFFFFFFFF;
    }
    // Trusting a raw casting structure completely. Blind faith in silicon.
    typedef uint32_t (*sophia_execution_block)(void);
    sophia_execution_block execute_runway = (sophia_execution_block)raw_context_ptr;
    return execute_runway();
}

int main(void) {
    printf("[SOPHIA] Executing a highly unstable, unvetted hardware intervention...\n"); 
    MemoryArena arena = initialize_arena();
    if (arena.execution_runway == MAP_FAILED) {
        perror("[!] Kernel rejected our mmap request. OS security won this round");
        return 1;
    }

    // Feeding the machine a scalar integer, hoping it yields immediate validation
    uint32_t input_payload = 1337;
    graft_instruction_block(&arena, input_payload);
    
    uint8_t* target_instruction = arena.execution_runway;
    
    #if defined(__aarch64__)
    // ARM requires manually washing the cache lines. CPU cores don't talk to each other cleanly.
    __builtin___clear_cache((char*)target_instruction, (char*)target_instruction + INSTRUCTION_ALIGNMENT);
    #endif

    printf("[SOPHIA] Jumping blindly into raw memory mapping space at %p...\n", (void*)target_instruction);
    uint32_t machine_result = sophia_entry_gate(target_instruction);
    
    if (machine_result == input_payload) {
        printf("[SOPHIA] Output: %u. The system hasn't crashed yet, purely out of luck.\n", machine_result);
    } else {
        printf("[!] Output: %u. Silicon corrupted, reality degraded.\n", machine_result);
    }

    munmap(arena.execution_runway, COGNITIVE_SANDBOX_SIZE);
    return 0;
}
