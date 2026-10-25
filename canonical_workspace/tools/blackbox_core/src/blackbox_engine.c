#define _GNU_SOURCE
#include <fcntl.h>
#include <unistd.h>
#include <sys/mman.h>
#include <sys/stat.h>
#include <stdint.h>
#include <stddef.h>

static void sys_print(int fd, const char *str) {
    size_t len = 0;
    while (str[len]) len++;
    write(fd, str, len);
}

static void sys_print_hex64(uint64_t val) {
    const char hex_chars[] = "0123456789abcdef";
    char buf[19];
    buf[0] = '0';
    buf[1] = 'x';
    for (int i = 15; i >= 0; i--) {
        buf[2 + (15 - i)] = hex_chars[(val >> (i * 4)) & 0xF];
    }
    buf[18] = '\0';
    sys_print(1, buf);
}

static void sys_print_dec(uint64_t val) {
    char buf[21];
    int idx = 20;
    buf[idx--] = '\0';
    if (val == 0) {
        buf[idx--] = '0';
    } else {
        while (val > 0) {
            buf[idx--] = (char)('0' + (val % 10));
            val /= 10;
        }
    }
    sys_print(1, &buf[idx + 1]);
}

static int inspect_pe(const uint8_t *data, size_t size) {
    if (size < 0x40) {
        sys_print(2, "[-] Target image too small for DOS header\n");
        return 1;
    }

    if (data[0] != 'M' || data[1] != 'Z') {
        sys_print(2, "[-] Invalid DOS signature (expected MZ)\n");
        return 2;
    }

    uint32_t e_lfanew = *(const uint32_t *)(data + 0x3C);
    if ((size_t)e_lfanew + 24 > size) {
        sys_print(2, "[-] e_lfanew out of bounds\n");
        return 3;
    }

    const uint8_t *nt = data + e_lfanew;
    if (nt[0] != 'P' || nt[1] != 'E' || nt[2] != 0 || nt[3] != 0) {
        sys_print(2, "[-] Invalid NT signature (expected PE\\0\\0)\n");
        return 4;
    }

    uint16_t machine = *(const uint16_t *)(nt + 4);
    uint16_t num_sections = *(const uint16_t *)(nt + 6);
    uint16_t opt_hdr_size = *(const uint16_t *)(nt + 20);

    sys_print(1, "[+] PE Image Identified\n");
    sys_print(1, "    Machine Architecture: ");
    sys_print_hex64(machine);
    sys_print(1, "\n    Section Count:        ");
    sys_print_dec(num_sections);
    sys_print(1, "\n");

    if (machine != 0x8664 && machine != 0xAA64) {
        sys_print(2, "[-] Reject: Machine must be x86_64 (0x8664) or AArch64 (0xAA64)\n");
        return 5;
    }

    const uint8_t *opt = nt + 24;
    uint16_t magic = *(const uint16_t *)opt;
    if (magic != 0x020B) {
        sys_print(2, "[-] Reject: Optional header magic != 0x020B (not PE32+)\n");
        return 6;
    }

    uint32_t entry_point_rva = *(const uint32_t *)(opt + 16);
    uint64_t image_base = *(const uint64_t *)(opt + 24);

    sys_print(1, "    ImageBase:            ");
    sys_print_hex64(image_base);
    sys_print(1, "\n    EntryPoint RVA:       ");
    sys_print_hex64(entry_point_rva);
    sys_print(1, "\n");

    size_t sec_table_offset = (size_t)e_lfanew + 24 + opt_hdr_size;
    if (sec_table_offset + ((size_t)num_sections * 40) > size) {
        sys_print(2, "[-] Section header table exceeds file boundary\n");
        return 7;
    }

    for (uint16_t i = 0; i < num_sections; i++) {
        const uint8_t *sec = data + sec_table_offset + (i * 40);
        uint32_t virt_size = *(const uint32_t *)(sec + 8);
        uint32_t virt_addr = *(const uint32_t *)(sec + 12);
        uint32_t raw_size  = *(const uint32_t *)(sec + 16);
        uint32_t raw_ptr   = *(const uint32_t *)(sec + 20);

        if ((size_t)raw_ptr + raw_size > size) {
            sys_print(2, "[!] Section raw data bounds violated\n");
            return 8;
        }

        if (entry_point_rva >= virt_addr && entry_point_rva < (virt_addr + virt_size)) {
            uint32_t ep_phys = entry_point_rva - virt_addr + raw_ptr;
            sys_print(1, "    EntryPoint Physical:  ");
            sys_print_hex64(ep_phys);
            sys_print(1, "\n");
        }
    }

    sys_print(1, "[+] Canonical Truth Code Target Achieved.\n");
    return 0x42;
}

int main(int argc, char **argv) {
    sys_print(1, "[*] BlackBox Core Standalone Binary Forensic Substrate (Native)\n");
    if (argc < 2) {
        sys_print(2, "[-] Usage: blackbox_engine <pe_binary_path>\n");
        return 1;
    }

    int fd = open(argv[1], O_RDONLY);
    if (fd < 0) {
        sys_print(2, "[-] Failed to open target binary\n");
        return 2;
    }

    struct stat st;
    if (fstat(fd, &st) < 0 || st.st_size == 0) {
        close(fd);
        sys_print(2, "[-] Empty or unreadable file descriptor\n");
        return 3;
    }

    size_t file_size = (size_t)st.st_size;
    uint8_t *map_addr = (uint8_t *)mmap(NULL, file_size, PROT_READ | PROT_WRITE, MAP_PRIVATE, fd, 0);
    close(fd);

    if (map_addr == MAP_FAILED) {
        sys_print(2, "[-] Memory mapping failed\n");
        return 4;
    }

    if (mprotect(map_addr, file_size, PROT_READ) != 0) {
        munmap(map_addr, file_size);
        sys_print(2, "[-] W^X mprotect seal failure\n");
        return 5;
    }

    int rc = inspect_pe(map_addr, file_size);
    munmap(map_addr, file_size);
    return rc;
}
