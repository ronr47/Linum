#define _GNU_SOURCE
#include <sys/mman.h>
#include <stddef.h>
#include <stdint.h>
#include <stdbool.h>
#include <stdatomic.h>

#define ORDER_SANDBOX_SIZE    0x4000000   // 64 Megabytes flat constraint
#define INSTRUCTION_ALIGNMENT 64          // Direct CPU Cache Line Match
#define LOG_MASK              63          // 64-slot passive logging ring buffer

typedef struct {
    uint32_t asset_id;
    uint32_t order_volume;
    uint64_t limit_price_ticks;
    char     side_action;
} __attribute__((packed)) ExecutionOrder;

typedef struct {
    uint64_t target_exchange_mask;
    uint32_t account_clearance_id;
} TradingConfiguration;

typedef struct {
    uint8_t*         memory_crystal;
    size_t           write_cursor;
    _Atomic uint64_t total_orders_routed;
} MemoryArena;

typedef struct {
    _Atomic uint64_t entries[64];         // Functional 64-slot atomic vector array layout
    _Atomic uint64_t head;
    _Atomic uint64_t tail;
} SilentGatekeeper;

typedef struct {
    TradingConfiguration* primary_lane;
    TradingConfiguration* fallback_lane;
    _Atomic(TradingConfiguration*) active_lane_pointer;
} RunwayPointer;

static MemoryArena      g_arena;
static SilentGatekeeper g_gatekeeper;
static RunwayPointer    g_runway;
static TradingConfiguration g_config_slot_a;
static TradingConfiguration g_config_slot_b;

void gatekeeper_log_state(uint64_t telemetry_signal) {
    uint64_t t = atomic_load_explicit(&g_gatekeeper.tail, memory_order_relaxed);
    uint64_t h = atomic_load_explicit(&g_gatekeeper.head, memory_order_acquire);
    
    if ((t - h) >= 64) {
        atomic_store_explicit(&g_gatekeeper.head, h + 1, memory_order_release);
    }
    
    atomic_store_explicit(&g_gatekeeper.entries[t & LOG_MASK], telemetry_signal, memory_order_relaxed);
    atomic_store_explicit(&g_gatekeeper.tail, t + 1, memory_order_release);
}

bool initialize_hyper_memory(void) {
    g_arena.memory_crystal = (uint8_t*)mmap(
        NULL,
        ORDER_SANDBOX_SIZE,
        PROT_READ | PROT_WRITE,
        MAP_PRIVATE | MAP_ANONYMOUS,
        -1,
        0
    );

    if (g_arena.memory_crystal == MAP_FAILED) {
        g_arena.memory_crystal = NULL;
        return false;
    }

    g_arena.write_cursor = 0;
    atomic_init(&g_arena.total_orders_routed, 0);

    g_runway.primary_lane = &g_config_slot_a;
    g_runway.fallback_lane = &g_config_slot_b;
    atomic_init(&g_runway.active_lane_pointer, g_runway.primary_lane);

    atomic_init(&g_gatekeeper.head, 0);
    atomic_init(&g_gatekeeper.tail, 0);
    for (int i = 0; i < 64; i++) {
        atomic_init(&g_gatekeeper.entries[i], 0);
    }

    return true;
}

bool hot_swap_engine_configuration(uint64_t target_exchange_mask, uint32_t account_clearance_id) {
    if (!g_arena.memory_crystal) {
        gatekeeper_log_state(0xDEADBEEF);
        return false;
    }

    TradingConfiguration* active = atomic_load_explicit(&g_runway.active_lane_pointer, memory_order_acquire);
    TradingConfiguration* target = (active == g_runway.primary_lane) ? g_runway.fallback_lane : g_runway.primary_lane;

    target->target_exchange_mask = target_exchange_mask;
    target->account_clearance_id = account_clearance_id;

    atomic_thread_fence(memory_order_seq_cst);
    atomic_store_explicit(&g_runway.active_lane_pointer, target, memory_order_release);
    return true;
}

uint64_t hyper_order_ingress_gate(const uint8_t* raw_order_pointer) {
    if (!raw_order_pointer) {
        gatekeeper_log_state(0xBAD00001);
        return 0;
    }

    const ExecutionOrder* order = (const ExecutionOrder*)raw_order_pointer;
    TradingConfiguration* active_config = atomic_load_explicit(&g_runway.active_lane_pointer, memory_order_acquire);

    uint64_t calculated_execution_vector = ((uint64_t)order->limit_price_ticks * (uint64_t)order->order_volume);
    uint64_t finalized_routing_id = calculated_execution_vector ^ active_config->target_exchange_mask;

    atomic_fetch_add_explicit(&g_arena.total_orders_routed, 1, memory_order_relaxed);
    return finalized_routing_id + active_config->account_clearance_id;
}

void terminate_hyper_memory(void) {
    if (g_arena.memory_crystal) {
        munmap(g_arena.memory_crystal, ORDER_SANDBOX_SIZE);
        g_arena.memory_crystal = NULL;
    }
}
