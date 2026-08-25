extern void _start(void);

void linum_entry(void) {
    __asm__ volatile (
        "cli\n\t"
        "mov $0x100000, %%rsp\n\t"
        "call _start"
        ::: "rsp"
    );
}
