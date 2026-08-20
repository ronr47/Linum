#include <unistd.h>
#include <sys/syscall.h>

// Bypasses standard libc wrappers using raw register mapping
long direct_write(int fd, const void *buf, size_t count) {
    long ret;
    __asm__ volatile(
        "movq %1, %%rax\n\t"  // Syscall number (SYS_write) -> RAX
        "movq %2, %%rdi\n\t"  // File Descriptor -> RDI
        "movq %3, %%rsi\n\t"  // Buffer Pointer -> RSI
        "movq %4, %%rdx\n\t"  // Buffer Length -> RDX
        "syscall\n\t"         // Invoke Kernel Ring 0 Vector
        "movq %%rax, %0"      // Store return register
        : "=r"(ret)
        : "g"((long)SYS_write), "g"((long)fd), "g"((long)buf), "g"((long)count)
        : "rax", "rdi", "rsi", "rdx", "rcx", "r11", "memory"
    );
    return ret;
}

int main(void) {
    const char msg[] = "[+] Direct Syscall Bypass Verification Successful.\n";
    direct_write(1, msg, sizeof(msg) - 1);
    
    // Invariant termination via direct exit syscall
    __asm__ volatile(
        "movq %0, %%rax\n\t"  // SYS_exit
        "xorq %%rdi, %%rdi\n\t" // status 0
        "syscall"
        :
        : "g"((long)SYS_exit)
        : "rax", "rdi"
    );
    return 0;
}
