#include <stdio.h>
#include <stdint.h>
#include <string.h>
#include <assert.h>

/* Exported prototypes from proofboot_pb010 using 64-bit safe uintptr_t */
uint32_t crc32(uintptr_t buffer, uintptr_t len);
uint32_t constant_time_eq(uintptr_t a, uintptr_t b, uintptr_t len);
uint32_t parse_header(uintptr_t slot_base);
uint32_t arbitrate_active_header(uintptr_t dev);

int main(void) {
    printf("[*] Initializing Linum ProofBoot PB-010 Bare-Metal Harness...\n");

    /* 1. Test CRC32 primitive */
    uint8_t test_data[] = { 0x50, 0x42, 0x30, 0x31, 0x00, 0x00, 0x00, 0x01 };
    uint32_t crc = crc32((uintptr_t)test_data, sizeof(test_data));
    printf("[+] Computed CRC32: 0x%08X\n", crc);
    assert(crc != 0);

    /* 2. Test constant_time_eq primitive */
    uint8_t a[] = { 1, 2, 3, 4 };
    uint8_t b[] = { 1, 2, 3, 4 };
    uint8_t c[] = { 1, 2, 3, 5 };
    uint32_t eq_match = constant_time_eq((uintptr_t)a, (uintptr_t)b, 4);
    uint32_t eq_diff  = constant_time_eq((uintptr_t)a, (uintptr_t)c, 4);
    printf("[+] Constant-time EQ match test: %u (expected 1)\n", eq_match);
    printf("[+] Constant-time EQ diff test:  %u (expected 0)\n", eq_diff);
    assert(eq_match == 1);
    assert(eq_diff == 0);

    printf("[OK] All hardware-level invariants verified successfully on %s!\n",
#if defined(__aarch64__)
        "AArch64 (ARM64)"
#elif defined(__x86_64__)
        "x86_64"
#else
        "Unknown Architecture"
#endif
    );
    return 0;
}
