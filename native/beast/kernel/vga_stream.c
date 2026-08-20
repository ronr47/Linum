#include <stdint.h>
#include <stddef.h>

#define VGA_MEMORY_BASE     ((volatile uint16_t*)0xB8000)
#define VGA_WIDTH           80
#define VGA_HEIGHT          25
#define VGA_DEFAULT_COLOR   0x0F

typedef struct {
    uint8_t x;
    uint8_t y;
} vga_cursor_t;

static vga_cursor_t cursor = {0, 0};

void vga_clear(void) {
    for (size_t i = 0; i < VGA_WIDTH * VGA_HEIGHT; i++) {
        VGA_MEMORY_BASE[i] = (VGA_DEFAULT_COLOR << 8) | ' ';
    }
    cursor.x = 0;
    cursor.y = 0;
}

static void vga_scroll(void) {
    for (size_t y = 1; y < VGA_HEIGHT; y++) {
        for (size_t x = 0; x < VGA_WIDTH; x++) {
            VGA_MEMORY_BASE[(y - 1) * VGA_WIDTH + x] = VGA_MEMORY_BASE[y * VGA_WIDTH + x];
        }
    }
    for (size_t x = 0; x < VGA_WIDTH; x++) {
        VGA_MEMORY_BASE[(VGA_HEIGHT - 1) * VGA_WIDTH + x] = (VGA_DEFAULT_COLOR << 8) | ' ';
    }
    cursor.y = VGA_HEIGHT - 1;
}

void vga_putchar(char c) {
    if (c == '\n') {
        cursor.x = 0;
        cursor.y++;
    } else if (c == '\b') {
        if (cursor.x > 0) {
            cursor.x--;
        } else if (cursor.y > 0) {
            cursor.y--;
            cursor.x = VGA_WIDTH - 1;
        }
        VGA_MEMORY_BASE[cursor.y * VGA_WIDTH + cursor.x] = (VGA_DEFAULT_COLOR << 8) | ' ';
    } else if (c == '\t') {
        cursor.x = (cursor.x + 4) & ~3;
        if (cursor.x >= VGA_WIDTH) {
            cursor.x = 0;
            cursor.y++;
        }
    } else {
        const size_t index = cursor.y * VGA_WIDTH + cursor.x;
        VGA_MEMORY_BASE[index] = (VGA_DEFAULT_COLOR << 8) | (uint8_t)c;
        cursor.x++;
    }

    if (cursor.x >= VGA_WIDTH) {
        cursor.x = 0;
        cursor.y++;
    }

    if (cursor.y >= VGA_HEIGHT) {
        vga_scroll();
    }
}

void vga_print(const char *str) {
    while (*str) {
        vga_putchar(*str++);
    }
}
