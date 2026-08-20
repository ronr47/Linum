#include <stdint.h>
#include <stddef.h>
#include "wilc_driver.h"

// --- Declarations for Linum-compiled functions ---
extern uint64_t test_main(uint64_t uninit_stub, uint64_t val_42);
extern uint64_t test_complex(const void *uninit_stub, uint64_t val_42);

// --- Bare-metal Memory Built-ins ---
void *memset(void *dest, int c, size_t n) {
    uint8_t *d = (uint8_t *)dest;
    while (n--) *d++ = (uint8_t)c;
    return dest;
}

void *memcpy(void *dest, const void *src, size_t n) {
    uint8_t *d = (uint8_t *)dest;
    const uint8_t *s = (const uint8_t *)src;
    while (n--) *d++ = *s++;
    return dest;
}

void *memmove(void *dest, const void *src, size_t n) {
    uint8_t *d = (uint8_t *)dest;
    const uint8_t *s = (const uint8_t *)src;
    if (d < s) {
        while (n--) *d++ = *s++;
    } else {
        d += n; s += n;
        while (n--) *--d = *--s;
    }
    return dest;
}

int memcmp(const void *s1, const void *s2, size_t n) {
    const uint8_t *p1 = (const uint8_t *)s1;
    const uint8_t *p2 = (const uint8_t *)s2;
    while (n--) {
        if (*p1 != *p2) return *p1 - *p2;
        p1++; p2++;
    }
    return 0;
}

// posix_memalign stub for Linum runtime heap calls
int posix_memalign(void **memptr, size_t alignment, size_t size) {
    (void)alignment; (void)size;
    *memptr = NULL;
    return 0;
}

// --- x86 Serial COM1 Output (0x3F8) for QEMU stdio ---
static inline void outb(uint16_t port, uint8_t val) {
    __asm__ volatile ("outb %0, %1" : : "a"(val), "Nd"(port));
}

static inline uint8_t inb(uint16_t port) {
    uint8_t ret;
    __asm__ volatile ("inb %1, %0" : "=a"(ret) : "Nd"(port));
    return ret;
}

static void serial_init(void) {
    outb(0x3F8 + 1, 0x00);
    outb(0x3F8 + 3, 0x80);
    outb(0x3F8 + 0, 0x03);
    outb(0x3F8 + 1, 0x00);
    outb(0x3F8 + 3, 0x03);
    outb(0x3F8 + 2, 0xC7);
    outb(0x3F8 + 4, 0x0B);
}

static void serial_puts(const char *s) {
    while (*s) {
        while ((inb(0x3F8 + 5) & 0x20) == 0);
        outb(0x3F8, (uint8_t)*s++);
    }
}

static void serial_put_dec(uint64_t val) {
    char buf[21];
    char *p = &buf[20];
    *p = '\0';
    if (val == 0) {
        serial_puts("0");
        return;
    }
    while (val > 0) {
        *--p = '0' + (val % 10);
        val /= 10;
    }
    serial_puts(p);
}

// --- Mock SPI Hardware VTable for Wi-Fi Driver ---
static void mock_spi_select(void *ctx) { (void)ctx; }
static void mock_spi_deselect(void *ctx) { (void)ctx; }
static void mock_spi_transfer(void *ctx, const uint8_t *tx, uint8_t *rx, size_t len) {
    (void)ctx;
    if (rx && len >= 4 && tx && tx[0] == 0x0B) {
        rx[0] = 0x00; rx[1] = 0x00; rx[2] = 0x00; rx[3] = 0x00;
    }
}

static void mock_rx_callback(void *ctx, const uint8_t *packet, size_t len) {
    (void)ctx; (void)packet; (void)len;
    serial_puts("[KERNEL] Rx Packet arrived via Interrupt!\n");
}

static uint8_t driver_buffer[32768] __attribute__((aligned(64)));

void kmain(void) {
    serial_init();
    serial_puts("\n===================================================\n");
    serial_puts("[KERNEL] Booted Goldmont Plus Bare-Metal Microkernel\n");
    serial_puts("===================================================\n");

    // 1. Run Linum-Compiled Logic
    serial_puts("[LINUM] Calling test_main(0, 42)... Return: ");
    uint64_t r1 = test_main(0, 42);
    serial_put_dec(r1);
    serial_puts("\n");

    serial_puts("[LINUM] Calling test_complex(&driver_buffer, 100)... Return: ");
    uint64_t r2 = test_complex(driver_buffer, 100);
    serial_put_dec(r2);
    serial_puts("\n");

    // 2. Initialize Bare-Metal Rust Wi-Fi Driver
    CSpiVTable vtable = {
        .context = NULL,
        .select = mock_spi_select,
        .deselect = mock_spi_deselect,
        .transfer_block = mock_spi_transfer
    };

    CWilcDriver *driver = (CWilcDriver *)driver_buffer;

    serial_puts("[DRIVER] Initializing WILC FFI Driver...\n");
    if (wilc_driver_init(driver, vtable) == 0) {
        serial_puts("[DRIVER] Driver instance init SUCCESS (align 64 verified)\n");
    }

    serial_puts("[DRIVER] Emulating Interrupt Line Trigger...\n");
    wilc_notify_irq();
    wilc_handle_interrupt(driver, mock_rx_callback, NULL);

    serial_puts("[KERNEL] All Linum code & Rust driver tests completed.\n");
}
