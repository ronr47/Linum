#include <stdint.h>

void _start(void) {
    // These structural pointers pass through safely without local bash interference
    volatile uint32_t *uart = (volatile uint32_t *)0x09000000;
    *uart = 0x41; // Send 'A' directly to hardware space
    
    // Explicit inline assembly remains un-parsed by host terminal environment
    __asm__ __volatile__("hlt");
}
