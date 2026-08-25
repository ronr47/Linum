/* Transpiled from pmm.linum via LINUM Pipeline */
#include <stdint.h>
#include <stddef.h>

#define PAGE_SIZE 4096
#define BITMAP_ARRAY_SIZE 32768

typedef struct __attribute__((aligned(64))) {
    uint64_t frames[BITMAP_ARRAY_SIZE];
    uint64_t total_frames;
} PhysicalMemoryBitmap;

PhysicalMemoryBitmap PMM_BITMAP = {
    .frames = {0},
    .total_frames = BITMAP_ARRAY_SIZE * 64
};

void pmm_mark_frame_allocated(uintptr_t phys_addr) {
    uintptr_t aligned_addr = phys_addr & ~(PAGE_SIZE - 1);
    uint64_t frame_index = aligned_addr / PAGE_SIZE;
    uint64_t bitmap_index = frame_index / 64;
    uint64_t bit_shift = frame_index % 64;

    if (bitmap_index < BITMAP_ARRAY_SIZE) {
        PMM_BITMAP.frames[bitmap_index] |= (1ULL << bit_shift);
    }
}

uintptr_t pmm_allocate_free_frame(void) {
    for (size_t i = 0; i < BITMAP_ARRAY_SIZE; i++) {
        if (PMM_BITMAP.frames[i] == 0xFFFFFFFFFFFFFFFFULL) {
            continue;
        }
        uint64_t inverted = ~PMM_BITMAP.frames[i];
        int bit = __builtin_ctzll(inverted);
        PMM_BITMAP.frames[i] |= (1ULL << bit);
        return (uintptr_t)(((i * 64) + bit) * PAGE_SIZE);
    }
    return (uintptr_t)-1;
}

void pmm_free_frame(uintptr_t phys_addr) {
    uintptr_t aligned_addr = phys_addr & ~(PAGE_SIZE - 1);
    uint64_t frame_index = aligned_addr / PAGE_SIZE;
    uint64_t bitmap_index = frame_index / 64;
    uint64_t bit_shift = frame_index % 64;

    if (bitmap_index < BITMAP_ARRAY_SIZE) {
        PMM_BITMAP.frames[bitmap_index] &= ~(1ULL << bit_shift);
    }
}
