#define PORT_COM1 0x3F8

static inline void outb(unsigned short port, unsigned char val)
{
    asm volatile ("outb %0, %1" : : "a"(val), "Nd"(port));
}

static inline unsigned char inb(unsigned short port)
{
    unsigned char ret;
    asm volatile ("inb %1, %0" : "=a"(ret) : "Nd"(port));
    return ret;
}

void put_char(char c)
{
    while ((inb(PORT_COM1 + 5) & 0x20) == 0)
        ;

    outb(PORT_COM1, (unsigned char)c);
}

void print_serial(const char *str)
{
    while (*str)
        put_char(*str++);
}
