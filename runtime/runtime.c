#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <inttypes.h>

typedef struct {
    int64_t tag;
    int64_t payload;
    uint8_t active;
} LinearPacket;

static int64_t g_active_allocations = 0;

void* alloc_packet(int64_t seed) {
    LinearPacket* pkt = (LinearPacket*)malloc(sizeof(LinearPacket));
    if (!pkt) return NULL;
    pkt->tag = seed;
    pkt->payload = seed * 10;
    pkt->active = 1;
    g_active_allocations++;
    printf("[RUNTIME] alloc_packet(seed=%" PRId64 ") -> %p (Active: %" PRId64 ")\n",
           seed, (void*)pkt, g_active_allocations);
    return (void*)pkt;
}

int64_t inspect_packet_header(void* ptr) {
    if (!ptr) return 0;
    LinearPacket* pkt = (LinearPacket*)ptr;
    return pkt->tag;
}

void* transform_packet(void* ptr, int64_t step) {
    if (!ptr) return NULL;
    LinearPacket* pkt = (LinearPacket*)ptr;
    pkt->payload += step;
    return (void*)pkt;
}

int64_t dispatch_worker(void* ptr, int64_t worker_id) {
    if (!ptr) return 0;
    LinearPacket* pkt = (LinearPacket*)ptr;
    int64_t res = pkt->payload + worker_id;
    pkt->active = 0;
    free(pkt);
    g_active_allocations--;
    return res;
}

int64_t finalize_and_free(void* ptr) {
    if (!ptr) return 0;
    LinearPacket* pkt = (LinearPacket*)ptr;
    int64_t tag = pkt->tag;
    pkt->active = 0;
    free(pkt);
    g_active_allocations--;
    return tag;
}

void __drop_linear_resource(void* ptr) {
    if (ptr) {
        free(ptr);
        g_active_allocations--;
    }
}

int64_t add(int64_t a, int64_t b) { return a + b; }
int64_t lt(int64_t a, int64_t b) { return a < b; }
int64_t gt(int64_t a, int64_t b) { return a > b; }

extern int64_t golden_pipeline_entry(int64_t seed);

int main(int argc, char** argv) {
    printf("========================================\n");
    printf(" LINUM DETERMINISTIC RUNTIME EXECUTION  \n");
    printf("========================================\n");
    int64_t seed = 42;
    int64_t result = golden_pipeline_entry(seed);
    printf("----------------------------------------\n");
    printf("[RESULT] %" PRId64 "\n", result);
    printf("[LEAK CHECK] Outstanding allocations: %" PRId64 "\n", g_active_allocations);
    printf("========================================\n");
    if (g_active_allocations != 0) return 1;
    return 0;
}
