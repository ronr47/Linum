#include "pmm.h"

// Define the absolute physical memory bitmap array space
uint64_t physical_memory_bitmap[BITMAP_ARRAY_SIZE] = {0};

void pmm_mark_frame_allocated(uintptr_t physical_address) {
    uint64_t frame_index = physical_address / PAGE_SIZE;
    uint64_t bitmap_index = frame_index / 64;
    uint64_t bit_shift = frame_index % 64;

    physical_memory_bitmap[bitmap_index] |= (1ULL << bit_shift);
}

uintptr_t pmm_allocate_free_frame(void) {
    for (size_t i = 0; i < BITMAP_ARRAY_SIZE; i++) {
        // Skip instantly if all 64 frames in this chunk are allocated
        if (physical_memory_bitmap[i] == 0xFFFFFFFFFFFFFFFFULL) {
            continue;
        }

        // Search the individual bits inside this active slice
        for (int bit = 0; bit < 64; bit++) {
            if (!(physical_memory_bitmap[i] & (1ULL << bit))) {
                // Free frame isolated. Mark it allocated immediately.
                physical_memory_bitmap[i] |= (1ULL << bit);
                
                uint64_t calculation_index = (i * 64) + bit;
                return (uintptr_t)(calculation_index * PAGE_SIZE);
            }
        }
    }
    return (uintptr_t)-1; // Out of Physical Memory (OOM Condition)
}

void pmm_free_frame(uintptr_t physical_address) {
    uint64_t frame_index = physical_address / PAGE_SIZE;
    uint64_t bitmap_index = frame_index / 64;
    uint64_t bit_shift = frame_index % 64;

    physical_memory_bitmap[bitmap_index] &= ~(1ULL << bit_shift);
}
