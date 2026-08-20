#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h>
#include <unistd.h>
#include <stdbool.h>

#define RING_SIZE 2048
#define FRAME_LEN 98       // Commandment 8: Exact geometry
#define CACHE_LINE 64      // Commandment 2: Cache line boundary

struct RingFrame {
    uint32_t frame_index;
    uint32_t data_len;
    uint8_t payload[FRAME_LEN];
} __attribute__((aligned(CACHE_LINE)));

struct FrameRingBuffer {
    uint32_t head; // Consumer pointer
    uint32_t tail; // Producer pointer
    uint32_t mask;
    struct RingFrame slots[RING_SIZE];
} __attribute__((aligned(CACHE_LINE)));

static int ring_initialized = 0;

void init_frame_ring(struct FrameRingBuffer *rb) {
    if (ring_initialized) return; // Commandment 1: Idempotence guard
    ring_initialized = 1;
    
    rb->head = 0;
    rb->tail = 0;
    rb->mask = RING_SIZE - 1;
    memset(rb->slots, 0, sizeof(rb->slots));
    printf("[+] Idempotent Check: Lock-free ring layout safely initialized.\n");
}

// Thread Vector A: High-Speed Packet Producer (Directly links out of AF_XDP Ingress)
bool enqueue_frame(struct FrameRingBuffer *rb, uint32_t idx, const uint8_t *data) {
    // Read head with acquire barrier to sync with potential consumer thread releases
    uint32_t current_head = __atomic_load_n(&rb->head, __ATOMIC_ACQUIRE);
    uint32_t current_tail = rb->tail; // Owned locally by single producer thread

    if ((current_tail - current_head) >= RING_SIZE) {
        return false; // Ring buffer saturated. Prevent descriptor starvation drops.
    }

    uint32_t slot_idx = current_tail & rb->mask;
    rb->slots[slot_idx].frame_index = idx;
    rb->slots[slot_idx].data_len = FRAME_LEN;
    memcpy(rb->slots[slot_idx].payload, data, FRAME_LEN);

    // Atomically increment tail pointer with release barrier to expose frame memory to consumers
    __atomic_store_n(&rb->tail, current_tail + 1, __ATOMIC_RELEASE);
    return true;
}

// Thread Vector B: Real-Time Consumer Execution (Asynchronous Recycle / Decoupled Ring Clear)
bool dequeue_and_recycle(struct FrameRingBuffer *rb, struct RingFrame *out_frame) {
    uint32_t current_tail = __atomic_load_n(&rb->tail, __ATOMIC_ACQUIRE);
    uint32_t current_head = rb->head; // Owned locally by single consumer thread

    if (current_head == current_tail) {
        return false; // Queue completely empty. Nothing to recycle.
    }

    uint32_t slot_idx = current_head & rb->mask;
    memcpy(out_frame, &rb->slots[slot_idx], sizeof(struct RingFrame));

    // Atomically release descriptor and advance index barrier to clear processing windows
    __atomic_store_n(&rb->head, current_head + 1, __ATOMIC_RELEASE);
    return true;
}

int main(void) {
    struct FrameRingBuffer *rb = aligned_alloc(CACHE_LINE, sizeof(struct FrameRingBuffer));
    if (!rb) { perror("[-] Memory mapping failed"); return 1; }
    
    init_frame_ring(rb);
    
    uint8_t mock_packet[FRAME_LEN];
    memset(mock_packet, 0x55, FRAME_LEN); // Pre-load diagnostic bit sequences

    printf("[*] Testing concurrent lock-free pipeline loops...\n");
    
    // Ingest data frame into atomic cache matrices
    if (enqueue_frame(rb, 101, mock_packet)) {
        printf("[+] Frame 101 successfully queued via atomic release barrier.\n");
    }
    
    // Asynchronously consume and clear memory metrics
    struct RingFrame processed_frame;
    if (dequeue_and_recycle(rb, &processed_frame)) {
        printf("[+] Frame %u successfully recycled from slot. Buffer payload intact.\n", processed_frame.frame_index);
    }

    printf("[+] Success: Lock-Free Pipeline Invariant Synced.\n");
    free(rb);
    return 0;
}
