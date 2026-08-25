/* ============================================================================
 * FILENAME: gateway_core_v2.c
 * ARCHITECTURE: Production-Grade SPSC Sequencer & Ingress Engine
 * STANDARD: Strict C11 Concurrency (_Atomic, acquire/release, aligned_alloc)
 * TARGET: Linux aarch64 / x86_64
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
#include <assert.h>
#include <sys/mman.h>
#include <sys/socket.h>
#include <sys/types.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <time.h>

#define CACHE_LINE_SIZE       64
#define RING_BUFFER_CAP       65536
#define RING_BUFFER_MASK      (RING_BUFFER_CAP - 1)
#define BATCH_INGRESS_SZ      32
#define PAYLOAD_MAX_BYTES     256
#define MAX_PAYLOAD_BODY      (PAYLOAD_MAX_BYTES - 32)
#define MMAP_LOG_SIZE         (64 * 1024 * 1024)
#define HISTOGRAM_BUCKETS     1000 // 0 to 999 microseconds

/* --- STRUCT DEFINITIONS & STRICT PADDING --- */

typedef struct __attribute__((aligned(CACHE_LINE_SIZE))) {
    uint64_t ingress_seq;         // Sequence at ingress
    uint64_t accepted_seq;        // Sequence when passed backpressure
    uint64_t t0_ingress_tsc;      // Kernel/Batch read timestamp
    uint32_t payload_len;         // Exact payload bytes
    uint32_t client_ip;           // IPv4 address
    uint8_t  payload[MAX_PAYLOAD_BODY]; // Contiguous inline payload
} wire_frame_t;

_Static_assert(sizeof(wire_frame_t) == 256, "wire_frame_t must be exactly 256 bytes (4 cache lines)");

/*
 * C11-compliant lock-free SPSC queue with cache-line-isolated atomic indices.
 */
typedef struct {
    _Alignas(CACHE_LINE_SIZE) _Atomic uint64_t write_index;
    uint8_t pad0[CACHE_LINE_SIZE - sizeof(_Atomic uint64_t)];

    _Alignas(CACHE_LINE_SIZE) _Atomic uint64_t read_index;
    uint8_t pad1[CACHE_LINE_SIZE - sizeof(_Atomic uint64_t)];

    _Alignas(CACHE_LINE_SIZE) wire_frame_t slots[RING_BUFFER_CAP];
} spsc_ring_t;

/* Global Engine State */
static spsc_ring_t g_ring;
static uint8_t *g_mmap_journal = NULL;
static size_t g_journal_offset = 0;
static _Atomic bool g_running = true;

/* Metrics & Telemetry */
static _Atomic uint64_t g_stat_ingress_pkts = 0;
static _Atomic uint64_t g_stat_accepted_pkts = 0;
static _Atomic uint64_t g_stat_dropped_backpressure = 0;
static _Atomic uint64_t g_stat_dropped_oversize = 0;
static _Atomic uint64_t g_stat_journal_full_drops = 0;
static uint64_t g_latency_hist[HISTOGRAM_BUCKETS] = {0};

/* --- CYCLE TIMER --- */

static inline uint64_t get_hardware_cycles(void) {
#if defined(__aarch64__)
    uint64_t tsc;
    __asm__ __volatile__("mrs %0, cntvct_el0" : "=r"(tsc));
    return tsc;
#elif defined(__x86_64__)
    uint32_t lo, hi;
    __asm__ __volatile__("rdtsc" : "=a"(lo), "=d"(hi));
    return ((uint64_t)hi << 32) | lo;
#else
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC_RAW, &ts);
    return (uint64_t)ts.tv_sec * 1000000000ULL + ts.tv_nsec;
#endif
}

static inline uint64_t get_timer_frequency_hz(void) {
#if defined(__aarch64__)
    uint64_t freq;
    __asm__ __volatile__("mrs %0, cntfrq_el0" : "=r"(freq));
    return freq;
#else
    return 2400000000ULL; // 2.4 GHz nominal baseline
#endif
}

/* --- HARDWARE PINNING & RESIDENCY INITIALIZATION --- */

static void enforce_core_affinity(int core_id) {
    cpu_set_t cpuset;
    CPU_ZERO(&cpuset);
    CPU_SET(core_id, &cpuset);
    if (pthread_setaffinity_np(pthread_self(), sizeof(cpu_set_t), &cpuset) != 0) {
        perror("[CRITICAL] pthread_setaffinity_np failed");
        exit(EXIT_FAILURE);
    }
}

static void initialize_and_lock_journal(int fd, size_t size) {
    if (posix_fallocate(fd, 0, size) != 0) {
        perror("[CRITICAL] posix_fallocate failed");
        exit(EXIT_FAILURE);
    }

    g_mmap_journal = (uint8_t *)mmap(NULL, size, PROT_READ | PROT_WRITE, MAP_SHARED, fd, 0);
    if (g_mmap_journal == MAP_FAILED) {
        perror("[CRITICAL] mmap journal failed");
        exit(EXIT_FAILURE);
    }

    long page_size = sysconf(_SC_PAGESIZE);
    if (page_size <= 0) page_size = 4096;

    for (size_t off = 0; off < size; off += (size_t)page_size) {
        g_mmap_journal[off] = 0;
    }

    if (mlock(g_mmap_journal, size) != 0) {
        perror("[WARN] mlock failed (requires CAP_IPC_LOCK or root). Continuing without physical RAM pinning");
    }
}

/* --- CONSUMER / SEQUENCER THREAD (CORE 1) --- */

void *sequencer_consumer_worker(void *arg) {
    (void)arg;
    enforce_core_affinity(1);

    uint64_t freq = get_timer_frequency_hz();
    uint64_t cycles_per_micro = freq / 1000000ULL;
    if (cycles_per_micro == 0) cycles_per_micro = 1;

    printf("[CORE 1] Sequencer/Journal consumer active.\n");

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

        uint64_t slot_idx = current_read & RING_BUFFER_MASK;
        wire_frame_t *frame = &g_ring.slots[slot_idx];

        // Durability / Journaling Policy: STOP-AND-DROP ON OVERFLOW
        if (g_journal_offset + sizeof(wire_frame_t) <= MMAP_LOG_SIZE) {
            memcpy(g_mmap_journal + g_journal_offset, frame, sizeof(wire_frame_t));
            g_journal_offset += sizeof(wire_frame_t);
        } else {
            atomic_fetch_add_explicit(&g_stat_journal_full_drops, 1, memory_order_relaxed);
        }

        // Latency tracking
        uint64_t t4_finish = get_hardware_cycles();
        if (t4_finish >= frame->t0_ingress_tsc) {
            uint64_t transit_micros = (t4_finish - frame->t0_ingress_tsc) / cycles_per_micro;
            if (transit_micros < HISTOGRAM_BUCKETS) {
                g_latency_hist[transit_micros]++;
            } else {
                g_latency_hist[HISTOGRAM_BUCKETS - 1]++;
            }
        }

        // Release slot to producer
        atomic_store_explicit(&g_ring.read_index, current_read + 1, memory_order_release);
    }

    return NULL;
}

/* --- INGRESS THREAD (CORE 0) --- */

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

    printf("[CORE 0] Ingress loop running.\n");

    uint64_t global_ingress_seq = 0;
    uint64_t global_accepted_seq = 0;

    while (atomic_load_explicit(&g_running, memory_order_relaxed)) {
        // Reset metadata overwritten by previous recvmmsg calls
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

        uint64_t batch_t0 = get_hardware_cycles();

        for (int i = 0; i < pkts; i++) {
            uint64_t in_seq = ++global_ingress_seq;
            atomic_fetch_add_explicit(&g_stat_ingress_pkts, 1, memory_order_relaxed);

            size_t pkt_len = msgs[i].msg_len;

            // Strict Validation: Reject malformed or oversized payloads
            if (pkt_len > MAX_PAYLOAD_BODY || pkt_len == 0) {
                atomic_fetch_add_explicit(&g_stat_dropped_oversize, 1, memory_order_relaxed);
                continue;
            }

            uint64_t current_write = atomic_load_explicit(&g_ring.write_index, memory_order_relaxed);
            uint64_t current_read = atomic_load_explicit(&g_ring.read_index, memory_order_acquire);

            // Backpressure check
            if ((current_write - current_read) >= RING_BUFFER_CAP) {
                atomic_fetch_add_explicit(&g_stat_dropped_backpressure, 1, memory_order_relaxed);
                continue;
            }

            uint64_t slot_idx = current_write & RING_BUFFER_MASK;
            wire_frame_t *frame = &g_ring.slots[slot_idx];

            frame->ingress_seq = in_seq;
            frame->accepted_seq = ++global_accepted_seq;
            frame->t0_ingress_tsc = batch_t0;
            frame->payload_len = (uint32_t)pkt_len;
            frame->client_ip = src_addrs[i].sin_addr.s_addr;
            memcpy(frame->payload, packet_buffers[i], pkt_len);

            atomic_fetch_add_explicit(&g_stat_accepted_pkts, 1, memory_order_relaxed);

            // Publish frame to sequencer
            atomic_store_explicit(&g_ring.write_index, current_write + 1, memory_order_release);
        }
    }
}

/* --- BOOTSTRAP --- */

int main(int argc, char **argv) {
    int port = (argc > 1) ? atoi(argv[1]) : 9999;

    printf("=========================================================\n");
    printf(" LINUM RUNTIME GATEWAY CORE (V2 PRODUCTION ENGINE)       \n");
    printf("=========================================================\n");

    atomic_init(&g_ring.write_index, 0);
    atomic_init(&g_ring.read_index, 0);

    int journal_fd = open("gateway_journal.bin", O_RDWR | O_CREAT | O_TRUNC, 0666);
    if (journal_fd < 0) {
        perror("[CRITICAL] Failed to open journal file");
        exit(EXIT_FAILURE);
    }
    initialize_and_lock_journal(journal_fd, MMAP_LOG_SIZE);

    int sock_fd = socket(AF_INET, SOCK_DGRAM | SOCK_NONBLOCK, 0);
    if (sock_fd < 0) {
        perror("[CRITICAL] socket creation failed");
        exit(EXIT_FAILURE);
    }

    int req_rcvbuf = 16 * 1024 * 1024;
    if (setsockopt(sock_fd, SOL_SOCKET, SO_RCVBUF, &req_rcvbuf, sizeof(req_rcvbuf)) != 0) {
        perror("[CRITICAL] setsockopt SO_RCVBUF failed");
        exit(EXIT_FAILURE);
    }

    int actual_rcvbuf = 0;
    socklen_t optlen = sizeof(actual_rcvbuf);
    getsockopt(sock_fd, SOL_SOCKET, SO_RCVBUF, &actual_rcvbuf, &optlen);
    printf("[CONFIG] Requested SO_RCVBUF: %d bytes | OS Allocated: %d bytes\n", req_rcvbuf, actual_rcvbuf);

    struct sockaddr_in addr;
    memset(&addr, 0, sizeof(addr));
    addr.sin_family = AF_INET;
    addr.sin_addr.s_addr = INADDR_ANY;
    addr.sin_port = htons(port);

    if (bind(sock_fd, (struct sockaddr *)&addr, sizeof(addr)) < 0) {
        perror("[CRITICAL] bind failed");
        exit(EXIT_FAILURE);
    }

    pthread_t consumer_thread;
    if (pthread_create(&consumer_thread, NULL, sequencer_consumer_worker, NULL) != 0) {
        perror("[CRITICAL] pthread_create failed");
        exit(EXIT_FAILURE);
    }

    printf("[READY] Gateway listening on UDP port %d.\n", port);

    run_ingress_worker(sock_fd);

    atomic_store_explicit(&g_running, false, memory_order_release);
    pthread_join(consumer_thread, NULL);

    msync(g_mmap_journal, g_journal_offset, MS_SYNC);
    munmap(g_mmap_journal, MMAP_LOG_SIZE);
    close(journal_fd);
    close(sock_fd);

    return 0;
}
