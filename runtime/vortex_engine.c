#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h>
#include <unistd.h>
#include <sys/mman.h>

#define SLOT_SIZE 128
#define RING_CAPACITY 1024
#define CANVAS_SIZE (1024 * 1024 * 64)

typedef struct __attribute__((packed)) {
    uint64_t sequence;
    uint32_t length;
    uint8_t  data[SLOT_SIZE - 12];
} RingSlot;

typedef struct {
    uint64_t head;
    uint64_t tail;
    RingSlot slots[RING_CAPACITY];
} VortexRingBuffer;

int main(void) {
    uint8_t *canvas = mmap(NULL, CANVAS_SIZE, PROT_READ | PROT_WRITE,
                           MAP_ANONYMOUS | MAP_PRIVATE, -1, 0);
    if (canvas == MAP_FAILED) {
        perror("[-] Failed to map execution canvas");
        return 1;
    }

    size_t ring_size = sizeof(VortexRingBuffer);
    VortexRingBuffer *ring = mmap(NULL, ring_size, PROT_READ | PROT_WRITE,
                                  MAP_ANONYMOUS | MAP_PRIVATE, -1, 0);
    if (ring == MAP_FAILED) {
        perror("[-] Failed to map ring buffer");
        munmap(canvas, CANVAS_SIZE);
        return 1;
    }

    ring->head = 0;
    ring->tail = 0;
    printf("[+] Allocated Canvas (%d MB) and Ring Buffer (%zu bytes)\n",
           CANVAS_SIZE / (1024 * 1024), ring_size);

    munmap(ring, ring_size);
    munmap(canvas, CANVAS_SIZE);
    return 0;
}
