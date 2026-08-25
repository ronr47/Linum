#include <stdint.h>

extern void pmm_free_block(uint64_t bit_index);

struct E820Entry {
    uint64_t base_addr;
    uint64_t length;
    uint32_t type;
    uint32_t extended_attributes;
} __attribute__((packed));

uint64_t e820_init_pmm(struct E820Entry* map, uint32_t entry_count) {
    uint64_t total_ram = 0;
    for (uint32_t i = 0; i < entry_count; i++) {
        if (map[i].type == 1) {
            total_ram += map[i].length;
            uint64_t start_addr = (map[i].base_addr + 0xFFF) & ~0xFFF;
            uint64_t end_addr = (map[i].base_addr + map[i].length) & ~0xFFF;
            for (uint64_t addr = start_addr; addr < end_addr; addr += 0x1000) {
                pmm_free_block(addr / 0x1000);
            }
        }
    }
    return total_ram;
}
