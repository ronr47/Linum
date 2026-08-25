typedef unsigned char uint8_t;
typedef unsigned short uint16_t;
typedef unsigned int uint32_t;

#define COM1_PORT 0x3F8

extern void hlt_loop(void) __attribute__((noreturn));
extern void microkernel_init(void);

static inline void outb(uint16_t port, uint8_t val) {
    __asm__ volatile ("outb %0, %1" : : "a"(val), "Nd"(port));
}

static inline uint8_t inb(uint16_t port) {
    uint8_t ret;
    __asm__ volatile ("inb %1, %0" : "=a"(ret) : "Nd"(port));
    return ret;
}

static inline void init_serial(void) {
    outb(COM1_PORT + 1, 0x00);
    outb(COM1_PORT + 3, 0x80);
    outb(COM1_PORT + 0, 0x03);
    outb(COM1_PORT + 1, 0x00);
    outb(COM1_PORT + 3, 0x03);
    outb(COM1_PORT + 2, 0xC7);
    outb(COM1_PORT + 4, 0x0B);
}

/* Fixed: Made a true global linkage symbol visible to microkernel.o */
void put_char(char c) {
    while ((inb(COM1_PORT + 5) & 0x20) == 0);
    outb(COM1_PORT + 0, (uint8_t)c);
}

void print_serial(const char *str) {
    for (uint32_t i = 0; str[i] != '\0'; i++) {
        put_char(str[i]);
    }
}

void kernel_main(uint32_t magic, uint32_t multiboot_info_ptr) {
    (void)multiboot_info_ptr;
    init_serial();
    
    if (magic != 0x2BADB002) {
        print_serial("\r\n[-] LINUM BOOT FAILURE: INVALID MULTIBOOT MAGIC STATUS\r\n");
        hlt_loop();
    }

    print_serial("\r\n[+] LINUM QUANTUM SUBSTRATE COREPIN DEPLOYED SUCCESSFUL.\r\n");
    print_serial("[*] Executing microkernel initialization passes...\r\n");

    microkernel_init();

    print_serial("[+] System context steady. Entering nominal execution halt state.\r\n");
    hlt_loop();
}
