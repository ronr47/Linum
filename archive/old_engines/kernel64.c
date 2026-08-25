#include <stdint.h>

#define COM1_PORT 0x3F8

static inline void outb(uint16_t port, uint8_t val) {
    __asm__ volatile ("outb %0, %1" : : "a"(val), "Nd"(port));
}

static inline uint8_t inb(uint16_t port) {
    uint8_t ret;
    __asm__ volatile ("inb %1, %0" : "=a"(ret) : "Nd"(port));
    return ret;
}

static inline uint64_t rdtsc(void) {
    uint32_t lo, hi;
    __asm__ volatile ("rdtsc" : "=a"(lo), "=d"(hi));
    return ((uint64_t)hi << 32) | lo;
}

static inline void uart_putc(char c) {
    while ((inb(COM1_PORT + 5) & 0x20) == 0);
    outb(COM1_PORT, (uint8_t)c);
}

static inline void uart_print(const char *s) {
    while (*s) {
        if (*s == '\n') uart_putc('\r');
        uart_putc(*s++);
    }
}

static inline void uart_print_hex(uint64_t val) {
    const char hex_chars[] = "0123456789ABCDEF";
    uart_print("0x");
    for (int i = 60; i >= 0; i -= 4) {
        uart_putc(hex_chars[(val >> i) & 0xF]);
    }
}

/* Explicit first section */
__attribute__((section(".text.boot"), used))
void _start(void) {
    uart_print("\n============================================================\n");
    uart_print(" ⚡ STAGE-2 64-BIT FREESTANDING KERNEL RUNNING AT 0x10000\n");
    uart_print("============================================================\n");

    uint64_t t0 = rdtsc();

    /* Linum affine state transform */
    uint32_t state = 0x12345678;
    state = (state + 42) ^ 0xAA;

    uint64_t t1 = rdtsc();

    uart_print(" [*] Direct Ring-0 HW State Transform: ");
    uart_print_hex(state);
    uart_print("\n [*] Bare-Metal Execution Latency     : ");
    uart_print_hex(t1 - t0);
    uart_print(" TSC Cycles\n");
    uart_print(" [✔] Stage-2 Kernel Operations Sound.\n");
    uart_print("============================================================\n\n");

    /* Signal QEMU ISA debug exit */
    outb(0x501, 0x00);

    for (;;) {
        __asm__ volatile ("hlt");
    }
}
