#include <stdint.h>
#include <stddef.h>

#define IDT_ENTRIES 256
#define PIC1_COMMAND 0x20
#define PIC1_DATA    0x21
#define PIC2_COMMAND 0xA0
#define PIC2_DATA    0xA1

typedef struct {
    uint16_t base_low;
    uint16_t selector;
    uint8_t  zero;
    uint8_t  flags;
    uint16_t base_high;
} __attribute__((packed)) idt_entry_t;

typedef struct {
    uint16_t limit;
    uint32_t base;
} __attribute__((packed)) idt_ptr_t;

static idt_entry_t idt[IDT_ENTRIES];
static idt_ptr_t idt_ptr;

extern void vga_print(const char *str);
extern uint8_t translate_scancode(uint8_t scancode);
extern void vga_putchar(char c);

static inline void outb(uint16_t port, uint8_t val) {
    __asm__ volatile ("outb %0, %1" : : "a"(val), "Nd"(port));
}

static inline uint8_t inb(uint16_t port) {
    uint8_t ret;
    __asm__ volatile ("inb %1, %0" : "=a"(ret) : "Nd"(port));
    return ret;
}

void pic_remap(void) {
    uint8_t a1 = inb(PIC1_DATA);
    uint8_t a2 = inb(PIC2_DATA);

    outb(PIC1_COMMAND, 0x11);
    outb(PIC2_COMMAND, 0x11);
    
    outb(PIC1_DATA, 0x20); 
    outb(PIC2_DATA, 0x28); 
    
    outb(PIC1_DATA, 0x04);
    outb(PIC2_DATA, 0x02);
    
    outb(PIC1_DATA, 0x01);
    outb(PIC2_DATA, 0x01);
    
    outb(PIC1_DATA, a1);
    outb(PIC2_DATA, a2);
}

void keyboard_handler_main(void) {
    uint8_t scancode = inb(0x60);
    uint8_t ascii = translate_scancode(scancode);
    if (ascii) {
        vga_putchar(ascii);
    }
    outb(PIC1_COMMAND, 0x20);
}

void init_interrupts(void) {
    pic_remap();

    idt_ptr.limit = sizeof(idt_entry_t) * IDT_ENTRIES - 1;
    idt_ptr.base = (uint32_t)&idt;

    outb(PIC1_DATA, inb(PIC1_DATA) & ~(1 << 1));

    __asm__ volatile ("lidt (%0)" : : "r"(&idt_ptr));
    __asm__ volatile ("sti");
}
