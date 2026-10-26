#include <stdint.h>
#include <stddef.h>

static inline int64_t sys_write(int fd, const void *buf, size_t count) {
    int64_t ret;
    __asm__ volatile (
        "mov $1, %%rax\n\t"
        "syscall"
        : "=a"(ret)
        : "D"((int64_t)fd), "S"(buf), "d"(count)
        : "rcx", "r11", "memory"
    );
    return ret;
}

static inline void sys_exit(int code) {
    __asm__ volatile (
        "mov $60, %%rax\n\t"
        "syscall"
        : : "D"((int64_t)code) : "rax", "rcx", "r11"
    );
}

size_t strlen(const char *s) {
    size_t len = 0;
    while (s[len]) len++;
    return len;
}

int puts(const char *s) {
    size_t len = strlen(s);
    sys_write(1, s, len);
    sys_write(1, "\n", 1);
    return (int)(len + 1);
}

void *memset(void *s, int c, size_t n) {
    uint8_t *p = (uint8_t *)s;
    while (n--) *p++ = (uint8_t)c;
    return s;
}

void *memcpy(void *dest, const void *src, size_t n) {
    uint8_t *d = (uint8_t *)dest;
    const uint8_t *s = (const uint8_t *)src;
    while (n--) *d++ = *s++;
    return dest;
}

static void print_uint_hex(uint32_t val) {
    char buf[9] = "00000000";
    const char hex[] = "0123456789ABCDEF";
    for (int i = 7; i >= 0; i--) {
        buf[i] = hex[val & 0xF];
        val >>= 4;
    }
    sys_write(1, buf, 8);
}

static void print_uint_dec(uint32_t val) {
    if (val == 0) {
        sys_write(1, "0", 1);
        return;
    }
    char buf[12];
    int idx = 11;
    buf[idx--] = '\0';
    while (val > 0) {
        buf[idx--] = '0' + (val % 10);
        val /= 10;
    }
    sys_write(1, &buf[idx + 1], 11 - idx);
}

int printf(const char *format, ...) {
    __builtin_va_list args;
    __builtin_va_start(args, format);
    while (*format) {
        if (*format == '%' && *(format + 1)) {
            format++;
            if (*format == 's') {
                const char *s = __builtin_va_arg(args, const char *);
                if (!s) s = "(null)";
                sys_write(1, s, strlen(s));
            } else if (*format == 'd' || *format == 'u') {
                uint32_t val = __builtin_va_arg(args, uint32_t);
                print_uint_dec(val);
            } else if (*format == 'x' || *format == 'X') {
                uint32_t val = __builtin_va_arg(args, uint32_t);
                print_uint_hex(val);
            } else if (*format == 'c') {
                char c = (char)__builtin_va_arg(args, int);
                sys_write(1, &c, 1);
            } else if (*format == '%') {
                sys_write(1, "%", 1);
            }
        } else {
            sys_write(1, format, 1);
        }
        format++;
    }
    __builtin_va_end(args);
    return 0;
}

void __assert_fail(const char *expr, const char *file, int line) {
    sys_write(2, "[!] ASSERTION FAILED: ", 22);
    sys_write(2, expr, strlen(expr));
    sys_write(2, " at ", 4);
    sys_write(2, file, strlen(file));
    sys_write(2, ":", 1);
    print_uint_dec(line);
    sys_write(2, "\n", 1);
    sys_exit(1);
}

extern int main(void);

void _start(void) {
    int ret = main();
    sys_exit(ret);
}
