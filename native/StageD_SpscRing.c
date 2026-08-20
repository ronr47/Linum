#define _GNU_SOURCE

#include <errno.h>
#include <pthread.h>
#include <sched.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stddef.h>
#include <time.h>

#define RING_SIZE   2048u
#define FRAME_LEN   98u
#define CACHE_LINE  64u
#define ITERATIONS  1000000u

struct RingFrame {
    uint32_t frame_index;
    uint32_t data_len;
    uint8_t  payload[FRAME_LEN];
} __attribute__((aligned(CACHE_LINE)));

struct alignas_tail {
    uint32_t value;
    uint8_t pad[CACHE_LINE - sizeof(uint32_t)];
} __attribute__((aligned(CACHE_LINE)));

struct alignas_head {
    uint32_t value;
    uint8_t pad[CACHE_LINE - sizeof(uint32_t)];
} __attribute__((aligned(CACHE_LINE)));

struct FrameRingBuffer {
    struct alignas_tail tail;
    struct alignas_head head;

    uint32_t mask;
    uint8_t reserved[CACHE_LINE - sizeof(uint32_t)];

    struct RingFrame slots[RING_SIZE];
} __attribute__((aligned(CACHE_LINE)));

struct WorkerArgs {
    struct FrameRingBuffer *rb;
};

static inline int
ring_enqueue(struct FrameRingBuffer *rb,
             uint32_t frame_index,
             const uint8_t *payload)
{
    const uint32_t tail =
        __atomic_load_n(&rb->tail.value, __ATOMIC_RELAXED);

    const uint32_t head =
        __atomic_load_n(&rb->head.value, __ATOMIC_ACQUIRE);

    if ((uint32_t)(tail - head) >= RING_SIZE) {
        return 0;
    }

    const uint32_t slot = tail & rb->mask;

    rb->slots[slot].frame_index = frame_index;
    rb->slots[slot].data_len = FRAME_LEN;
    memcpy(rb->slots[slot].payload, payload, FRAME_LEN);

    __atomic_store_n(
        &rb->tail.value,
        tail + 1u,
        __ATOMIC_RELEASE
    );

    return 1;
}

static inline int
ring_dequeue(struct FrameRingBuffer *rb,
             struct RingFrame *out)
{
    const uint32_t head =
        __atomic_load_n(&rb->head.value, __ATOMIC_RELAXED);

    const uint32_t tail =
        __atomic_load_n(&rb->tail.value, __ATOMIC_ACQUIRE);

    if (head == tail) {
        return 0;
    }

    const uint32_t slot = head & rb->mask;

    memcpy(
        out,
        &rb->slots[slot],
        sizeof(*out)
    );

    __atomic_store_n(
        &rb->head.value,
        head + 1u,
        __ATOMIC_RELEASE
    );

    return 1;
}

static void *
producer_thread(void *arg)
{
    struct WorkerArgs *args = arg;
    struct FrameRingBuffer *rb = args->rb;

    uint8_t payload[FRAME_LEN];
    memset(payload, 0x55, sizeof(payload));

    for (uint32_t i = 0; i < ITERATIONS;) {
        if (ring_enqueue(rb, i, payload)) {
            ++i;
        } else {
            sched_yield();
        }
    }

    return NULL;
}

static void *
consumer_thread(void *arg)
{
    struct WorkerArgs *args = arg;
    struct FrameRingBuffer *rb = args->rb;

    struct RingFrame frame;

    uint32_t consumed = 0;

    while (consumed < ITERATIONS) {
        if (ring_dequeue(rb, &frame)) {
            if (frame.frame_index != consumed) {
                fprintf(
                    stderr,
                    "[-] Ordering violation: expected=%u got=%u\n",
                    consumed,
                    frame.frame_index
                );
                return NULL;
            }

            ++consumed;
        } else {
            sched_yield();
        }
    }

    return NULL;
}

static void
print_layout(void)
{
    printf("[*] Stage D SPSC Cache-Separated Ring\n");
    printf("    -> RingFrame size      : %zu bytes\n",
           sizeof(struct RingFrame));
    printf("    -> RingFrame alignment : %zu bytes\n",
           _Alignof(struct RingFrame));
    printf("    -> Ring slots          : %u\n",
           RING_SIZE);
    printf("    -> Payload bytes       : %u\n",
           FRAME_LEN);
    printf("    -> Ring bytes          : %zu\n",
           sizeof(struct FrameRingBuffer));

    printf(
        "    -> head cacheline addr : %zu mod 64\n",
        ((size_t)offsetof(struct FrameRingBuffer, head)) % CACHE_LINE
    );

    printf(
        "    -> tail cacheline addr : %zu mod 64\n",
        ((size_t)offsetof(struct FrameRingBuffer, tail)) % CACHE_LINE
    );
}

int main(void)
{
    struct FrameRingBuffer *rb =
        aligned_alloc(
            CACHE_LINE,
            sizeof(struct FrameRingBuffer)
        );

    if (!rb) {
        perror("aligned_alloc");
        return 1;
    }

    memset(rb, 0, sizeof(*rb));
    rb->mask = RING_SIZE - 1u;

    print_layout();

    pthread_t producer;
    pthread_t consumer;

    struct WorkerArgs args = {
        .rb = rb
    };

    printf(
        "[*] Starting %u producer/consumer transfers...\n",
        ITERATIONS
    );

    const int p =
        pthread_create(
            &producer,
            NULL,
            producer_thread,
            &args
        );

    const int c =
        pthread_create(
            &consumer,
            NULL,
            consumer_thread,
            &args
        );

    if (p != 0 || c != 0) {
        fprintf(
            stderr,
            "[-] pthread_create failed: producer=%d consumer=%d\n",
            p,
            c
        );
        free(rb);
        return 1;
    }

    pthread_join(producer, NULL);
    pthread_join(consumer, NULL);

    const uint32_t final_tail =
        __atomic_load_n(
            &rb->tail.value,
            __ATOMIC_ACQUIRE
        );

    const uint32_t final_head =
        __atomic_load_n(
            &rb->head.value,
            __ATOMIC_ACQUIRE
        );

    printf(
        "[+] Final head=%u tail=%u occupancy=%u\n",
        final_head,
        final_tail,
        final_tail - final_head
    );

    if (final_head != ITERATIONS ||
        final_tail != ITERATIONS) {
        fprintf(stderr,
                "[-] Ring completion invariant failed.\n");
        free(rb);
        return 1;
    }

    printf(
        "[+] Stage D SPSC lock-free transfer invariant PASSED.\n"
    );

    free(rb);
    return 0;
}
