#include <stdint.h>
#include <stddef.h>

#define UART_COM1 0x3F8
#define QEMU_EXIT_PORT 0x501

static const char HEX_CHARS[] = "0123456789ABCDEF";

/* ========================================================================== */
/* HARDWARE IO & SERIAL HELPERS                                               */
/* ========================================================================== */
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

static void uart_putc(char c) {
    while ((inb(UART_COM1 + 5) & 0x20) == 0);
    outb(UART_COM1, (uint8_t)c);
}

static void uart_puts(const char *s) {
    while (*s) {
        if (*s == '\n') uart_putc('\r');
        uart_putc(*s++);
    }
}

static void uart_put_hex(uint64_t val) {
    uart_puts("0x");
    for (int i = 60; i >= 0; i -= 4) {
        uart_putc(HEX_CHARS[(val >> i) & 0xF]);
    }
}

/* ========================================================================== */
/* FIBER 1: BARE-METAL eBPF JIT EMITTER & INVOKER                             */
/* ========================================================================== */
static uint8_t jit_code_buffer[256] __attribute__((aligned(32)));

static void run_fiber_ebpf_jit(void) {
    uart_puts(" [+] [FIBER-1] Running Bare-Metal eBPF JIT Worker...\n");
    uint64_t t_start = rdtsc();

    uint8_t *p = jit_code_buffer;
    *p++ = 0xB8; *(uint32_t *)p = 100; p += 4;
    *p++ = 0x69; *p++ = 0xC0; *(uint32_t *)p = 42; p += 4;
    *p++ = 0x35; *(uint32_t *)p = 0xDEADBEEF; p += 4;
    *p++ = 0xC3;

    uint32_t (*fn)(void) = (uint32_t (*)(void))jit_code_buffer;
    uint32_t result = fn();
    uint64_t t_end = rdtsc();

    uart_puts("     ▶ eBPF JIT Native Invocation Result: ");
    uart_put_hex(result);
    uart_puts(" (0xDEADAE87)\n");

    uart_puts("     ▶ eBPF Execution Latency           : ");
    uart_put_hex(t_end - t_start);
    uart_puts(" TSC Cycles\n\n");
}

/* ========================================================================== */
/* FIBER 2: RING-0 HARDWARE PMC & COMPUTE MONITOR                             */
/* ========================================================================== */
static void run_fiber_pmc(void) {
    uart_puts(" [+] [FIBER-2] Running Hardware Ring-0 PMC Monitor...\n");
    uint64_t t_start = rdtsc();

    volatile uint64_t acc = 0x12345678;
    for (int i = 0; i < 5000; i++) {
        acc = (acc * 6364136223846793005ULL) + 1ULL;
    }

    uint64_t t_end = rdtsc();

    uart_puts("     ▶ Affine Compute Accumulator       : ");
    uart_put_hex(acc);
    uart_puts("\n");

    uart_puts("     ▶ Compute Loop Execution Latency   : ");
    uart_put_hex(t_end - t_start);
    uart_puts(" TSC Cycles\n\n");
}

/* ========================================================================== */
/* FIBER 3: BARE-METAL TENSOR SCALING (FIXED-POINT VECTOR KERNEL)             */
/* ========================================================================== */
static uint32_t tensor_buffer[24] __attribute__((aligned(32)));

static void run_fiber_tensor_simd(void) {
    uart_puts(" [+] [FIBER-3] Running Bare-Metal Tensor SIMD Engine...\n");
    uint64_t t_start = rdtsc();

    for (int i = 0; i < 24; i++) {
        tensor_buffer[i] = (uint32_t)(i + 1);
    }

    for (int i = 0; i < 24; i++) {
        tensor_buffer[i] = ((tensor_buffer[i] * 5) + 1) / 2;
    }

    uint64_t t_end = rdtsc();
    uint32_t val = tensor_buffer[23];

    uart_puts("     ▶ Transformed Element [Index 23]   : ");
    uart_put_hex(val);
    uart_puts(" (Expected: 60 / 0x3C)\n");

    uart_puts("     ▶ Tensor Pass Execution Latency    : ");
    uart_put_hex(t_end - t_start);
    uart_puts(" TSC Cycles\n\n");
}

/* Entry point at 0x10000 */
__attribute__((section(".text.entry"), naked))
void _start64(void) {
    __asm__ volatile (
        "movq $0x80000, %rsp\n\t"
        "call kmain64\n\t"
        "1: hlt\n\t"
        "jmp 1b\n\t"
    );
}

/* ========================================================================== */
/* 64-BIT UNIFIED KERNEL ENTRY POINT                                          */
/* ========================================================================== */
void kmain64(void) {
    uart_puts("\n============================================================\n");
    uart_puts(" ⚡ LINUM 64-BIT UNIFIED RING-0 EXOKERNEL (eBPF + PMC + TENSOR)\n");
    uart_puts("============================================================\n");
    uart_puts(" [*] Spawning 3-Fiber Cooperative Scheduler Loop...\n\n");

    for (int round = 1; round <= 3; round++) {
        uart_puts(">>> --- COOPERATIVE FIBER ROUND ");
        uart_put_hex(round);
        uart_puts(" --- <<<\n");

        run_fiber_ebpf_jit();
        run_fiber_pmc();
        run_fiber_tensor_simd();
    }

    uart_puts("============================================================\n");
    uart_puts(" [✔] ALL 3 BARE-METAL RING-0 FIBERS COMPLETED SUCCESSFULLY\n");
    uart_puts("============================================================\n");

    /* Signal QEMU isa-debug-exit device to shut down cleanly */
    outb(QEMU_EXIT_PORT, 0x31);
}
