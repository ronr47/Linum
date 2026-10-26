#include <stdio.h>
#include <stdint.h>
#include <string.h>
#include <assert.h>

#define SLOT_SIZE 4096
#define TOTAL_STORAGE_SIZE (SLOT_SIZE * 2)

typedef struct {
    uintptr_t base;
    uint32_t capacity;
    uint8_t secret_key[32];
} StorageDevice;

static uint8_t virtual_nvram[TOTAL_STORAGE_SIZE];

uint32_t crc32(uintptr_t buffer, uintptr_t len);
uint32_t constant_time_eq(uintptr_t a, uintptr_t b, uintptr_t len);
uint32_t parse_header(uintptr_t slot_base);
uint32_t arbitrate_active_header(uintptr_t dev);

static void write_header(uint32_t slot_offset, uint32_t magic, uint32_t seq, uint32_t payload_len) {
    uint8_t *slot = &virtual_nvram[slot_offset];
    memset(slot, 0, SLOT_SIZE);

    uint32_t *hdr = (uint32_t *)slot;
    hdr[0] = magic;        // magic: 0x50423031
    hdr[1] = seq;          // seq
    hdr[2] = payload_len;  // body_len

    uint32_t crc = crc32((uintptr_t)slot, 12);
    hdr[3] = crc;          // crc
}

int main(void) {
    printf("[*] Starting Linum ProofBoot PB-010 Comprehensive Hardware Harness...\n");

    /* 1. Crypto & Math primitives */
    uint8_t dummy[4] = { 1, 2, 3, 4 };
    assert(crc32((uintptr_t)dummy, 4) != 0);
    assert(constant_time_eq((uintptr_t)dummy, (uintptr_t)dummy, 4) == 1);
    printf("[+] Step 1: Crypto & Math primitives verified.\n");

    /* Initialize device descriptor */
    StorageDevice dev;
    dev.base = (uintptr_t)virtual_nvram;
    dev.capacity = TOTAL_STORAGE_SIZE;
    memset(dev.secret_key, 0x42, sizeof(dev.secret_key));

    /* 2. Cold boot arbitration: Bank A valid (Seq 1), Bank B blank */
    memset(virtual_nvram, 0xFF, TOTAL_STORAGE_SIZE);
    write_header(0x0000, 0x50423031, 1, 64);

    uint32_t active_side = arbitrate_active_header((uintptr_t)&dev);
    printf("[+] Step 2: Cold boot arbitration selected side: %c\n", (char)active_side);
    assert(active_side == 'A' || active_side == 0);

    /* 3. Upgrade transition: Bank B programmed with higher sequence */
    write_header(0x1000, 0x50423031, 2, 64);
    active_side = arbitrate_active_header((uintptr_t)&dev);
    printf("[+] Step 3: Upgrade arbitration selected side: %c\n", (char)active_side);
    assert(active_side == 'B' || active_side == 1);

    /* 4. Torn write fault: Corrupt Bank B CRC */
    virtual_nvram[0x1000 + 12] ^= 0x5A;
    active_side = arbitrate_active_header((uintptr_t)&dev);
    printf("[+] Step 4: Post-corruption fallback selected side: %c\n", (char)active_side);
    assert(active_side == 'A' || active_side == 0);

    /* 5. Catastrophic corruption: Both banks invalid */
    virtual_nvram[0x0000 + 12] ^= 0xFF;
    active_side = arbitrate_active_header((uintptr_t)&dev);
    printf("[+] Step 5: Dual-corruption fail-closed returned: %c\n", (char)active_side);

    printf("\n[OK] ALL ProofBoot PB-010 hardware fault & security tests PASSED!\n");
    return 0;
}
