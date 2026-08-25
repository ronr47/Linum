#ifndef VORTEX_ENGINE_H
#define VORTEX_ENGINE_H

#include <stddef.h>
#include <stdint.h>

// 1. THE FOUNDATIONAL CONSTANTS
#define COGNITIVE_SANDBOX_SIZE 0x4000000  // 64 Megabytes flat constraint
#define INSTRUCTION_ALIGNMENT 64          // Direct CPU Cache Line Match

// 2. EXPLICIT MEMORY OWNERSHIP SPANS
// The core invariant: The caller owns the memory; the module transforms it.
typedef struct {
    uint64_t base;
    uint64_t length;
    uint64_t capacity;
} VortexSpan;

// 3. THE UNIFIED MEMORY ARENA
typedef struct {
    uint8_t* execution_runway;
    size_t   write_cursor;
    uint32_t execution_velocity;
} MemoryArena;

// 4. PIN-HOLE MODULE INTERFACES
// Module 1: Core Network Ingest (Target < 45ns, zero heap allocations)
uint64_t ingest_packet(VortexSpan target);

// Module 2: Vector Ledger Matrix (Sequential write preservation on 64-byte grids)
uint8_t* append_vector(VortexSpan destination, const uint8_t* source, uint64_t length);

// Module 3: Tensor Inference Pipeline (In-place arithmetic transformation)
uint64_t evaluate_matrix(VortexSpan input, VortexSpan output);

// 5. RUNTIME LIFECYCLE MANAGEMENT
MemoryArena initialize_arena(void);
int pin_execution_core(unsigned int core_id);
void jump_to_runway(uint8_t* runway_address);

#endif // VORTEX_ENGINE_H
