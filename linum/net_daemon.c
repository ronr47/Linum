/* Bare-Metal Linux AARCH64 Syscall Self-Healing Engine */

struct timespec {
    long tv_sec;
    long tv_nsec;
};

// Raw inline assembly abstraction for 64-bit ARM Linux kernel system traps
static inline long build_syscall3(long syscall_num, long arg1, long arg2, long arg3) {
    register long x8 __asm__("x8") = syscall_num;
    register long x0 __asm__("x0") = arg1;
    register long x1 __asm__("x1") = arg2;
    register long x2 __asm__("x2") = arg3;
    __asm__ __volatile__(
        "svc #0"
        : "+r"(x0)
        : "r"(x1), "r"(x2), "r"(x8)
        : "memory"
    );
    return x0;
}

static inline long build_syscall2(long syscall_num, long arg1, long arg2) {
    return build_syscall3(syscall_num, arg1, arg2, 0);
}

static inline long build_syscall0(long syscall_num) {
    return build_syscall3(syscall_num, 0, 0, 0);
}

void execute_cmd(const char *cmd) {
    long pid = build_syscall0(57); // sys_fork
    if (pid == 0) {
        const char *filename = "/system/bin/sh";
        const char *argv[] = {filename, "-c", cmd, (void *)0};
        const char *envp[] = {(void *)0};
        build_syscall3(221, (long)filename, (long)argv, (long)envp); // sys_execve
        build_syscall2(93, 0, 0); // sys_exit if execve fails
    }
}

void _start(void) {
    struct timespec ts = {10, 0}; // 10 second delay structure
    
    while (1) {
        // Enforce automatic network profile selection directly inside the database
        execute_cmd("settings put global network_selection_mode 0 > /dev/null 2>&1");
        execute_cmd("settings delete global network_selection_name > /dev/null 2>&1");
        execute_cmd("settings delete global network_selection_short > /dev/null 2>&1");
        execute_cmd("am broadcast -a android.intent.action.ACTION_MANAGED_CONFIG_CHANGED > /dev/null 2>&1");

        build_syscall2(101, (long)&ts, 0); // sys_nanosleep
    }
}
