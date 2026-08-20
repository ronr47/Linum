/* Generated Automatically by LINUM — DO NOT EDIT MANUALLY */
#ifndef LINUM_TYPES_H
#define LINUM_TYPES_H

#include <stdint.h>

/* Commandment 2: 64-byte structural boundary for AVX-512 optimization */
typedef struct __attribute__((aligned(64))) {
    uint64_t total_frames_processed;
    uint64_t total_bytes_drained;
    uint64_t stride_violations;
    uint64_t expected_next_addr;
} LinumTelemetryMetrics;

#endif /* LINUM_TYPES_H */
