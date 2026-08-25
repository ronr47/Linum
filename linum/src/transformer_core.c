/* linum.transformer_core.c // Bare-Metal Ultra-Low-Latency Kernel Engine */
#include <stdint.h>
#include <stddef.h>
#include <math.h>

#define CACHE_LINE 64
#define ALIGN_64 __attribute__((aligned(CACHE_LINE)))
#define HEAD_DIM 64
#define ATTN_WINDOW 32

/* Zero-Debt Explicit Enum Serialization across FFI Boundaries */
typedef enum ALIGN_64 {
    LINUM_SYS_UNINITIALIZED = 0xAA00FF00,
    LINUM_SYS_COMPUTING     = 0xAA00FF01,
    LINUM_SYS_SUCCESS       = 0xAA00FF02,
    LINUM_SYS_E_PTR_FAULT   = 0xEE000001,
    LINUM_SYS_E_ALIGN_FAULT = 0xEE000002,
    LINUM_SYS_E_BOUND_FAULT = 0xEE000003
} linum_syscall_status_t;

/**
 * High-performance, zero-allocation sliding-window attention loop.
 * Verified to run with deterministic timing loops and zero dynamic allocations.
 */
ALIGN_64 linum_syscall_status_t linum_vector_attention_stream(
    const float* __restrict__ query,  // [SeqLen * HEAD_DIM], align 64
    const float* __restrict__ key,    // [SeqLen * HEAD_DIM], align 64
    const float* __restrict__ value,  // [SeqLen * HEAD_DIM], align 64
    float* __restrict__ output,       // [SeqLen * HEAD_DIM], align 64
    const uint32_t seq_len
) {
    /* Adversarial Memory Check: Pointer Integrity Verification */
    if (!query || !key || !value || !output) return LINUM_SYS_E_PTR_FAULT;
    if (((uintptr_t)query  & 0x3F) != 0) return LINUM_SYS_E_ALIGN_FAULT;
    if (((uintptr_t)key    & 0x3F) != 0) return LINUM_SYS_E_ALIGN_FAULT;
    if (((uintptr_t)value  & 0x3F) != 0) return LINUM_SYS_E_ALIGN_FAULT;
    if (((uintptr_t)output & 0x3F) != 0) return LINUM_SYS_E_ALIGN_FAULT;

    const float scale_factor = 1.0f / sqrtf((float)HEAD_DIM);

    /* Main Execution Graph Track */
    for (uint32_t idx = 0; idx < seq_len; idx++) {
        float softmax_scores[ATTN_WINDOW] ALIGN_64 = {0.0f};
        float max_score = -INFINITY;

        const uint32_t window_start = (idx >= ATTN_WINDOW) ? (idx - ATTN_WINDOW + 1) : 0;
        const uint32_t active_elements = idx - window_start + 1;

        /* Pass 1: Vectorized Dot Product over Sliding Context Windows */
        for (uint32_t jdx = window_start; jdx <= idx; jdx++) {
            float accumulator = 0.0f;
            const uint32_t q_stride = idx * HEAD_DIM;
            const uint32_t k_stride = jdx * HEAD_DIM;

            #pragma unroll(8)
            for (uint32_t dim = 0; dim < HEAD_DIM; dim++) {
                accumulator += query[q_stride + dim] * key[k_stride + dim];
            }

            float final_score = accumulator * scale_factor;
            softmax_scores[jdx - window_start] = final_score;
            if (final_score > max_score) {
                max_score = final_score;
            }
        }

        /* Pass 2: In-place Normalized Softmax Array Transformations */
        float sum_accumulator = 0.0f;
        for (uint32_t jdx = 0; jdx < active_elements; jdx++) {
            softmax_scores[jdx] = expf(softmax_scores[jdx] - max_score);
            sum_accumulator += softmax_scores[jdx];
        }

        const float inverted_sum = 1.0f / (sum_accumulator + 1e-7f);
        for (uint32_t jdx = 0; jdx < active_elements; jdx++) {
            softmax_scores[jdx] *= inverted_sum;
        }

        /* Pass 3: Project Value Elements into Output Vector Blocks */
        const uint32_t out_stride = idx * HEAD_DIM;
        for (uint32_t dim = 0; dim < HEAD_DIM; dim++) {
            output[out_stride + dim] = 0.0f;
        }

        for (uint32_t jdx = window_start; jdx <= idx; jdx++) {
            const float weight = softmax_scores[jdx - window_start];
            const uint32_t v_stride = jdx * HEAD_DIM;

            #pragma unroll(8)
            for (uint32_t dim = 0; dim < HEAD_DIM; dim++) {
                output[out_stride + dim] += weight * value[v_stride + dim];
            }
        }
    }

    return LINUM_SYS_SUCCESS;
}
