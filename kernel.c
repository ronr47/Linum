/**
 * @file kernel.c
 * @brief Linum Kernel Main Entry Point
 * @context Bare-metal x86_64 Long Mode
 */

#include <stdint.h>

// External function prototypes from our memory modules
struct E820Entry;
extern uint64_t e820_init_pmm(struct E820Entry* map, uint32_t entry_count);
extern void pmm_init(uint64_t* bitmap_memory, uint64_t total_memory);

/**
 * Kernel main entry point called by the bootloader/stubs.
 */
void kernel_main(void) {
    // Architectural Assumption: 
    // Firmware memory map and bitmap location are passed or mapped at known safe addresses.
    struct E820Entry* boot_e820_map = (struct E820Entry*)0x500; // Example BIOS map location
    uint32_t boot_e820_entries = 6;                           // Example entry count

    // Place the PMM bitmap safely after typical lower-memory regions (e.g., at 1MB mark)
    uint64_t* pmm_bitmap_target = (uint64_t*)0x100000; 

    // Assume 32MB total RAM for initial bringup if dynamic detection is deferred
    uint64_t assumed_total_ram = 32 * 1024 * 1024; 

    // 1. Initialize the Physical Memory Manager bitmap tracker
    pmm_init(pmm_bitmap_target, assumed_total_ram);

    // 2. Parse E820 map and free usable blocks into the PMM
    e820_init_pmm(boot_e820_map, boot_e820_entries);

    // Hang or proceed to multitasking / vmm setup
    while (1) {
        __asm__ __volatile__("hlt");
    }
}
