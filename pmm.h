#ifndef PMM_H
#define PMM_H

/* Self-contained low-level integer primitive overrides */
typedef unsigned long long uint64_t;
typedef unsigned long long uintptr_t;
typedef unsigned long long size_t;

#define PAGE_SIZE           4096
#define TOTAL_TRACKED_PAGES 1048576  // Accounts for up to 4 GiB of Physical RAM
#define BITMAP_ARRAY_SIZE   (TOTAL_TRACKED_PAGES / 64)

// External declaration of tracking data space
extern uint64_t physical_memory_bitmap[BITMAP_ARRAY_SIZE];

// Interface functions for physical core allocation
void pmm_mark_frame_allocated(uintptr_t physical_address);
uintptr_t pmm_allocate_free_frame(void);
void pmm_free_frame(uintptr_t physical_address);

#endif // PMM_H
