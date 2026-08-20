#include <unistd.h>
#include <sys/syscall.h>
#include <stdio.h>

long direct_write_bypass(int fd, const void *buf, size_t count) {
    long ret;
    __asm__ volatile(
        "movq %1, %%rax\n\t"
        "movq %2, %%rdi\n\t"
        "movq %3, %%rsi\n\t"
        "movq %4, %%rdx\n\t"
        "syscall\n\t"
        "movq %%rax, %0"
        : "=r"(ret)
        : "g"((long)SYS_write), "g"((long)fd), "g"((long)buf), "g"((long)count)
        : "rax", "rdi", "rsi", "rdx", "rcx", "r11", "memory"
    );
    return ret;
}

int main(void) {
    const char info[] = "[+] Linum Backend: Direct Syscall Execution Successful.\n";
    direct_write_bypass(1, info, sizeof(info) - 1);
    return 0;
}
