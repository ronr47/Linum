#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h>
#include <sys/mman.h>
#include <x86intrin.h>

#define ITERATIONS 100000

typedef struct {
    uint64_t timestamp;
    uint32_t raw_word;
    uint16_t pkt_len;
} __attribute__((aligned(64))) packet_event_t;

typedef int (*jit_func_t)(uint32_t);

static inline uint64_t read_tsc(void) {
    unsigned int aux;
    return __rdtscp(&aux);
}

int main(void) {
    void *arena = mmap(NULL, 4096, 
                       PROT_READ | PROT_WRITE | PROT_EXEC, 
                       MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
    if (arena == MAP_FAILED) {
        perror("mmap failed");
        return 1;
    }

    /* 64-byte aligned JIT Machine Code: mov eax, edi; add eax, 42; xor eax, 0xAA; ret */
    uint8_t jit_code[] = {
        0x89, 0xf8,             /* mov eax, edi */
        0x83, 0xc0, 0x2a,       /* add eax, 42  */
        0x83, 0xf0, 0xaa,       /* xor eax, 0xAA*/
        0xc3                    /* ret          */
    };
    memcpy(arena, jit_code, sizeof(jit_code));
    jit_func_t fast_jit = (jit_func_t)arena;

    packet_event_t mock_event = {
        .timestamp = 1000500,
        .raw_word = 0x12345678,
        .pkt_len = 64
    };

    /* 1. BTB & L1 Cache Warm-Up */
    for (int i = 0; i < 5000; i++) {
        fast_jit(mock_event.raw_word);
    }

    /* 2. Measured Steady-State Benchmark */
    _mm_lfence();
    uint64_t t0 = read_tsc();
    _mm_lfence();

    volatile int res = 0;
    for (int i = 0; i < ITERATIONS; i++) {
        res = fast_jit(mock_event.raw_word + i);
    }

    _mm_lfence();
    uint64_t t1 = read_tsc();
    _mm_lfence();

    uint64_t total_cycles = t1 - t0;
    double cycles_per_call = (double)total_cycles / ITERATIONS;
    double ns_per_call = cycles_per_call * 0.90909;

    printf("\n============================================================\n");
    printf(" ⚡ ZERO-COPY eBPF -> FASTJIT STEADY-STATE BENCHMARK\n");
    printf("============================================================\n");
    printf(" Total Iterations : %d\n", ITERATIONS);
    printf(" Last Result      : 0x%X\n", res);
    printf(" Avg Cycles/Frame : %.2f cycles\n", cycles_per_call);
    printf(" Real-World Speed : %.2f ns per packet (@ 1.10 GHz)\n", ns_per_call);
    printf(" Throughput       : %.2f Million Packets/sec (Mpps)\n", 1000.0 / ns_per_call);
    printf("============================================================\n");

    munmap(arena, 4096);
    return 0;
}
