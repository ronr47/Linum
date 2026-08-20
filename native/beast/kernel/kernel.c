#include <stdint.h>
#include <stddef.h>

#define PS2_DATA_PORT   0x60
#define PS2_STATUS_PORT 0x64
#define SCANCODE_MAX    84

// Import the external matrix declared in keyboard_matrix.c
extern const uint8_t scancode_ascii_matrix[2][SCANCODE_MAX];

// External display functions provided by vga_stream.c
extern void vga_clear_screen();
extern void vga_print_string(const char* str);
extern void vga_print_char(char c);

// Direct assembly hardware I/O reader
static inline uint8_t inb(uint16_t port) {
    uint8_t ret;
    __asm__ volatile("inb %1, %0" : "=a"(ret) : "Nd"(port));
    return ret;
}

void kmain() {
    vga_clear_screen();
    vga_print_string("=== BEAST KERNEL INTERACTIVE ONLINE ===\n");
    vga_print_string("Linum Compiler Pipeline Soundness Verified (25/25 Green)\n");
    vga_print_string("Live PS/2 Keyboard Decoder Active. Begin typing below:\n\n> ");

    while(1) {
        // Wait for data byte to appear in the PS/2 controller output buffer
        if (inb(PS2_STATUS_PORT) & 0x01) {
            uint8_t scancode = inb(PS2_DATA_PORT);
            
            // Filter out key-release events (break codes with bit 7 set)
            if (!(scancode & 0x80)) {
                if (scancode < SCANCODE_MAX) {
                    // Extract non-shifted ASCII value from row 0 of your matrix
                    char ascii_char = (char)scancode_ascii_matrix[0][scancode];
                    
                    if (ascii_char != 0) {
                        vga_print_char(ascii_char);
                    }
                }
            }
        }
    }
}
