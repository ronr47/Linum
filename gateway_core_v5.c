/* ============================================================================
 * FILENAME: gateway_core_v5.c
 * ARCHITECTURE: Production-Grade Sequencer Core & Audit Harness
 * STANDARD: Strict C11 Concurrency (_Atomic, acquire/release, raw monotonic timing)
 * ============================================================================ */

#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <stdbool.h>
#include <string.h>
#include <unistd.h>
#include <errno.h>
#include <fcntl.h>
#include <pthread.h>
#include <sched.h>
#include <stdatomic.h>
#include <signal.h>
#include <sys/mman.h>
#include <sys/socket.h>
#include <sys/types.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <time.h>

#define CACHE_LINE_SIZE       64
#define SPSC_CAPACITY         65536
#define SPSC_MASK             (SPSC_CAPACITY - 1)
#define JOURNAL_SLOTS         1048576  // 1,048,576 slots (256 MB buffer)
#define JOURNAL_MASK          (JOURNAL_SLOTS - 1)
#define BATCH_INGRESS_SZ      32
#define PAYLOAD_MAX_BYTES     256
#define MAX_PAYLOAD_BODY      (PAYLOAD_MAX_BYTES - 32)
#define HIST_BUCKETS_US       1000     // 0 to 999 microseconds

typedef struct __attribute__((aligned(CACHE_LINE_SIZE))) {
    uint64_t ingress_seq;
    uint64_t accepted_seq;
    uint64_t t0_ingress_ns;       // Exact per-packet ingress timestamp (ns)
    uint32_t payload_len;
    uint32_t client_ip;
    uint8_t  payload[MAX_PAYLOAD_BODY];
} wire_frame_t;

_Static_assert(sizeof(wire_frame_t) == 256, "wire_frame_t must be exactly 256 bytes");

typedef struct {
    _Alignas(CACHE_LINE_SIZE) _Atomic uint64_t write_index;
    uint8_t pad0[CACHE_LINE_SIZE - sizeof(_Atomic uint64_t)];

    _Alignas(CACHE_LINE_SIZE) _Atomic uint64_t read_index;
    uint8_t pad1[CACHE_LINE_SIZE - sizeof(_Atomic uint64_t)];

    _Alignas(CACHE_LINE_SIZE) wire_frame_t slots[SPSC_CAPACITY];
} spsc_ring_t;

/* Global State */
static spsc_ring_t g_ring;
static wire_frame_t *g_circular_journal = NULL;
static _Atomic bool g_running = true;

/* Telemetry Counters */
static _Atomic uint64_t g_stat_ingress_pkts = 0;
static _Atomic uint64_t g_stat_accepted_pkts = 0;
static _Atomic uint64_t g_stat_journaled_pkts = 0;
static _Atomic uint64_t g_stat_journal_overwrites = 0;
static _Atomic uint64_t g_stat_dropped_backpressure = 0;
static _Atomic uint64_t g_stat_dropped_oversize = 0;

/* Latency Tracking (Owned exclusively by consumer) */
static uint64_t g_hist_us[HIST_BUCKETS_US] = {0};
static uint64_t g_overflow_count = 0;
static uint64_t g_max_latency_ns = 0;

static inline uint64_t get_time_ns(void) {
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC_RAW, &ts);
    return ((uint64_t)ts.tv_sec * 1000000000ULL) + (uint64_t)ts.tv_nsec;
}

static void enforce_core_affinity(int core_id) {
    cpu_set_t cpuset;
    CPU_ZERO(&cpuset);
    CPU_SET(core_id, &cpuset);
    int ret = pthread_setaffinity_np(pthread_self(), sizeof(cpu_set_t), &cpuset);
    if (ret != 0) {
        fprintf(stderr, "[WARN] Could not pin to core %d (error %d). Check system topology.\n", core_id, ret);
    }
}

static void sigint_handler(int sig) {
    (void)sig;
    atomic_store_explicit(&g_running, false, memory_order_release);
}

static void print_audit_report(void) {
    uint64_t ingress = atomic_load_explicit(&g_stat_ingress_pkts, memory_order_relaxed);
    uint64_t accepted = atomic_load_explicit(&g_stat_accepted_pkts, memory_order_relaxed);
    uint64_t journaled = atomic_load_explicit(&g_stat_journaled_pkts, memory_order_relaxed);
    uint64_t overwrites = atomic_load_explicit(&g_stat_journal_overwrites, memory_order_relaxed);
    uint64_t drop_bp = atomic_load_explicit(&g_stat_dropped_backpressure, memory_order_relaxed);
    uint64_t drop_size = atomic_load_explicit(&g_stat_dropped_oversize, memory_order_relaxed);

    printf("\n=========================================================\n");
    printf("         GATEWAY V5 SCIENTIFIC EXECUTION AUDIT           \n");
    printf("=========================================================\n");
    printf("Kernel Ingress Processed: %lu\n", ingress);
    printf("Accepted by Gateway     : %lu (%.2f%%)\n", accepted, ingress ? (accepted * 100.0 / ingress) : 0.0);
    printf("Committed to Sequence   : %lu\n", journaled);
    printf("Journal Overwrites      : %lu (slots cycled)\n", overwrites);
    printf("Dropped (Backpressure)  : %lu\n", drop_bp);
    printf("Dropped (Oversized/Bad) : %lu\n", drop_size);
    printf("---------------------------------------------------------\n");

    if (journaled > 0) {
        uint64_t p50_target = journaled * 50 / 100;
        uint64_t p90_target = journaled * 90 / 100;
        uint64_t p95_target = journaled * 95 / 100;
        uint64_t p99_target = journaled * 99 / 100;
        uint64_t p999_target = journaled * 999 / 1000;

        uint64_t accum = 0;
        int p50 = -1, p90 = -1, p95 = -1, p99 = -1, p999 = -1;

        for (int i = 0; i < HIST_BUCKETS_US; i++) {
            accum += g_hist_us[i];
            if (p50 == -1 && accum >= p50_target) p50 = i;
            if (p90 == -1 && accum >= p90_target) p90 = i;
            if (p95 == -1 && accum >= p95_target) p95 = i;
            if (p99 == -1 && accum >= p99_target) p99 = i;
            if (p999 == -1 && accum >= p999_target) p999 = i;
        }

        printf("TRUE TRANSIT LATENCY (T0 Ingress -> T4 Sequencer Commit):\n");
        printf("  p50     : %d µs\n", p50);
        printf("  p90     : %d µs\n", p90);
        printf("  p95     : %d µs\n", p95);
        printf("  p99     : %d µs\n", p99);
        printf("  p99.9   : %d µs\n", p999);
        printf("  Max     : %.3f µs\n", (double)g_max_latency_ns / 1000.0);
        printf("  Over 1ms: %lu pkts (%.3f%%)\n", g_overflow_count, (g_overflow_count * 100.0) / journaled);
    }
    printf("=========================================================\n");
}

void *sequencer_consumer_worker(void *arg) {
    (void)arg;
    enforce_core_affinity(1);

    uint64_t journal_seq = 0;

    while (atomic_load_explicit(&g_running, memory_order_relaxed)) {
        uint64_t current_read = atomic_load_explicit(&g_ring.read_index, memory_order_relaxed);
        uint64_t current_write = atomic_load_explicit(&g_ring.write_index, memory_order_acquire);

        if (current_read == current_write) {
#if defined(__aarch64__)
            __asm__ __volatile__("yield");
#elif defined(__x86_64__)
            __asm__ __volatile__("pause");
#endif
            continue;
        }

        uint64_t slot_idx = current_read & SPSC_MASK;
        wire_frame_t *frame = &g_ring.slots[slot_idx];

        // 1. Write to Circular Journal
        uint64_t j_idx = journal_seq & JOURNAL_MASK;
        if (journal_seq >= JOURNAL_SLOTS) {
            atomic_fetch_add_explicit(&g_stat_journal_overwrites, 1, memory_order_relaxed);
        }
        g_circular_journal[j_idx] = *frame;
        journal_seq++;
        atomic_fetch_add_explicit(&g_stat_journaled_pkts, 1, memory_order_relaxed);

        // 2. High-Precision Latency Accounting
        uint64_t t4_commit_ns = get_time_ns();
        if (t4_commit_ns >= frame->t0_ingress_ns) {
            uint64_t delta_ns = t4_commit_ns - frame->t0_ingress_ns;
            if (delta_ns > g_max_latency_ns) {
                g_max_latency_ns = delta_ns;
            }

            uint64_t delta_us = delta_ns / 1000ULL;
            if (delta_us < HIST_BUCKETS_US) {
                g_hist_us[delta_us]++;
            } else {
                g_overflow_count++;
            }
        }

        // 3. Release SPSC Slot
        atomic_store_explicit(&g_ring.read_index, current_read + 1, memory_order_release);
    }
    return NULL;
}

void run_ingress_worker(int sock_fd) {
    enforce_core_affinity(0);

    struct mmsghdr msgs[BATCH_INGRESS_SZ];
    struct iovec iovecs[BATCH_INGRESS_SZ];
    uint8_t packet_buffers[BATCH_INGRESS_SZ][PAYLOAD_MAX_BYTES];
    struct sockaddr_in src_addrs[BATCH_INGRESS_SZ];

    memset(msgs, 0, sizeof(msgs));
    for (int i = 0; i < BATCH_INGRESS_SZ; i++) {
        iovecs[i].iov_base = packet_buffers[i];
        iovecs[i].iov_len = PAYLOAD_MAX_BYTES;
        msgs[i].msg_hdr.msg_iov = &iovecs[i];
        msgs[i].msg_hdr.msg_iovlen = 1;
        msgs[i].msg_hdr.msg_name = &src_addrs[i];
    }

    uint64_t global_ingress_seq = 0;
    uint64_t global_accepted_seq = 0;

    while (atomic_load_explicit(&g_running, memory_order_relaxed)) {
        for (int i = 0; i < BATCH_INGRESS_SZ; i++) {
            msgs[i].msg_hdr.msg_namelen = sizeof(struct sockaddr_in);
            msgs[i].msg_hdr.msg_controllen = 0;
            msgs[i].msg_hdr.msg_flags = 0;
        }

        int pkts = recvmmsg(sock_fd, msgs, BATCH_INGRESS_SZ, MSG_DONTWAIT, NULL);
        if (pkts <= 0) {
            if (errno == EAGAIN || errno == EWOULDBLOCK) {
#if defined(__aarch64__)
                __asm__ __volatile__("yield");
#elif defined(__x86_64__)
                __asm__ __volatile__("pause");
#endif
                continue;
            }
            continue;
        }

        for (int i = 0; i < pkts; i++) {
            uint64_t pkt_ingress_ns = get_time_ns(); // Precise per-packet timestamp
            uint64_t in_seq = ++global_ingress_seq;
            atomic_fetch_add_explicit(&g_stat_ingress_pkts, 1, memory_order_relaxed);

            size_t pkt_len = msgs[i].msg_len;
            if (pkt_len > MAX_PAYLOAD_BODY || pkt_len == 0) {
                atomic_fetch_add_explicit(&g_stat_dropped_oversize, 1, memory_order_relaxed);
                continue;
            }

            uint64_t current_write = atomic_load_explicit(&g_ring.write_index, memory_order_relaxed);
            uint64_t current_read = atomic_load_explicit(&g_ring.read_index, memory_order_acquire);

            if ((current_write - current_read) >= SPSC_CAPACITY) {
                atomic_fetch_add_explicit(&g_stat_dropped_backpressure, 1, memory_order_relaxed);
                continue;
            }

            uint64_t slot_idx = current_write & SPSC_MASK;
            wire_frame_t *frame = &g_ring.slots[slot_idx];

            frame->ingress_seq = in_seq;
            frame->accepted_seq = ++global_accepted_seq;
            frame->t0_ingress_ns = pkt_ingress_ns;
            frame->payload_len = (uint32_t)pkt_len;
            frame->client_ip = src_addrs[i].sin_addr.s_addr;
            memcpy(frame->payload, packet_buffers[i], pkt_len);

            atomic_fetch_add_explicit(&g_stat_accepted_pkts, 1, memory_order_relaxed);
            atomic_store_explicit(&g_ring.write_index, current_write + 1, memory_order_release);
        }
    }
}

int main(int argc, char **argv) {
    int port = (argc > 1) ? atoi(argv[1]) : 9999;
    signal(SIGINT, sigint_handler);

    atomic_init(&g_ring.write_index, 0);
    atomic_init(&g_ring.read_index, 0);

    // 1. Allocate & Prefault 256 MB Circular Journal Buffer
    size_t journal_bytes = sizeof(wire_frame_t) * JOURNAL_SLOTS;
    g_circular_journal = (wire_frame_t *)mmap(NULL, journal_bytes,
                                              PROT_READ | PROT_WRITE,
                                              MAP_PRIVATE | MAP_ANONYMOUS | MAP_POPULATE, -1, 0);
    if (g_circular_journal == MAP_FAILED) {
        perror("[CRITICAL] mmap journal allocation failed");
        exit(1);
    }
    
    // Explicit resident commit
    memset(g_circular_journal, 0, journal_bytes);
    mlock(g_circular_journal, journal_bytes);

    // 2. Configure Non-Blocking Socket
    int sock_fd = socket(AF_INET, SOCK_DGRAM | SOCK_NONBLOCK, 0);
    int req_rcvbuf = 32 * 1024 * 1024;
    setsockopt(sock_fd, SOL_SOCKET, SO_RCVBUF, &req_rcvbuf, sizeof(req_rcvbuf));

    struct sockaddr_in addr;
    memset(&addr, 0, sizeof(addr));
    addr.sin_family = AF_INET;
    addr.sin_addr.s_addr = INADDR_ANY;
    addr.sin_port = htons(port);
    if (bind(sock_fd, (struct sockaddr *)&addr, sizeof(addr)) < 0) {
        perror("[CRITICAL] bind failed");
        exit(1);
    }

    pthread_t consumer_thread;
    pthread_create(&consumer_thread, NULL, sequencer_consumer_worker, NULL);

    printf("[READY] Gateway V5 Active on :%d (Core 0: Ingress | Core 1: Sequencer)\n", port);
    run_ingress_worker(sock_fd);

    pthread_join(consumer_thread, NULL);
    print_audit_report();

    munmap(g_circular_journal, journal_bytes);
    close(sock_fd);
    return 0;
}
