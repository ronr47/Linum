typedef unsigned int uint32_t;
typedef unsigned long long uint64_t;

const uint32_t linum_multiboot_magic = 0x1BADB002;
const uint32_t linum_multiboot_flags = 0x00000000;
const uint32_t linum_multiboot_check = 0xE4524FFE;
const uint32_t linum_multiboot_pad00 = 0x00000000;

extern void microkernel_init(void);

void _start(void) {
    microkernel_init();
}
