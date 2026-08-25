#define _GNU_SOURCE
#include "vortex_engine.h"
#include <sys/mman.h>
#include <sched.h>

#define __NR_sched_setaffinity 203

// Direct system call wrapper for thread affinity isolation (Bypassing glibc overhead)
static inline long sys_set_affinity(unsigned int pid, size_t len, unsigned long* mask) {
    long ret;
    __asm__ volatile (
        "syscall"
        : "=a" (ret)
        : "0" (__NR_sched_setaffinity), "r" ((uint64_t)pid), "r" ((uint64_t)len), "r" ((uint64_t)mask)
        : "rcx", "r11", "memory"
    );
    return ret;
}

int pin_execution_core(unsigned int core_id) {
    unsigned long cpu_mask = 1UL << core_id;
    long result = sys_set_affinity(0, sizeof(cpu_mask), &cpu_mask);
    return (result == 0) ? 0 : -1;
}

MemoryArena initialize_arena(void) {
    MemoryArena arena;
    // Provisioning phase: Pre-allocating virtual memory sandbox
    arena.execution_runway = (uint8_t*)mmap(NULL, 
                                            COGNITIVE_SANDBOX_SIZE, 
                                            PROT_READ | PROT_WRITE | PROT_EXEC, 
                                            MAP_ANONYMOUS | MAP_PRIVATE | MAP_NORESERVE, 
                                            -1, 
                                            0);
    if (arena.execution_runway == MAP_FAILED) {
        arena.execution_runway = ((void*)0);
        arena.write_cursor = 0;
        arena.execution_velocity = 0;
        return arena;
    }
    arena.write_cursor = 0;
    arena.execution_velocity = 1;
    return arena;
}

// Atomic or indirect dispatch trampoline execution target
typedef void (*execution_target_t)(void);

void jump_to_runway(uint8_t* runway_address) {
    execution_target_t target = (execution_target_t)runway_address;
    
    // Enforce memory barrier and instruction cache synchronization
    __asm__ volatile (
        "lfence" ::: "memory"
    );
    
    target();
}

// Module Stubs conforming to VortexSpan ownership semantics
uint64_t ingest_packet(VortexSpan target) {
    if (target.length < 64 || (target.base % INSTRUCTION_ALIGNMENT) != 0) {
        return 1; // Non-compliant boundary state
    }
    // Zero-allocation frame ingestion logic mapped to target.base
    return 0;
}

uint8_t* append_vector(VortexSpan destination, const uint8_t* source, uint64_t length) {
    if (length > destination.capacity) {
        return ((void*)0); // Guard against overflow violations
    }
    uint8_t* dest_ptr = (uint8_t*)(destination.base + destination.length);
    // Direct memory streaming without heap allocation
    for (uint64_t i = 0; i < length; i++) {
        dest_ptr[i] = source[i];
    }
    return dest_ptr;
}

uint64_t evaluate_matrix(VortexSpan input, VortexSpan output) {
    if (input.length != output.capacity) {
        return 1;
    }
    // In-place vector transformation mapping directly across cache lines
    const uint64_t* in_ptr = (const uint64_t*)input.base;
    uint64_t* out_ptr = (uint64_t*)output.base;
    
    for (size_t i = 0; i < (input.length / sizeof(uint64_t)); i++) {
        out_ptr[i] = in_ptr[i]; // Direct register-aligned flow
    }
    return 0;
}
