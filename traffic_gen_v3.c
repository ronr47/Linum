/* ============================================================================
 * FILENAME: traffic_gen_v3.c
 * Topology-Aware Vectorized Load Generator
 * ============================================================================ */

#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h>
#include <unistd.h>
#include <errno.h>
#include <pthread.h>
#include <sched.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <time.h>

#define BATCH_SIZE 32
#define PAYLOAD_SIZE 64

int main(int argc, char **argv) {
    uint64_t total_packets = (argc > 1) ? atoll(argv[1]) : 1000000;
    int port = (argc > 2) ? atoi(argv[2]) : 9999;
    int target_core = (argc > 3) ? atoi(argv[3]) : -1;
    const char *target_ip = (argc > 4) ? argv[4] : "127.0.0.1";

    long nprocs = sysconf(_SC_NPROCESSORS_ONLN);

    if (target_core >= 0) {
        if (target_core < nprocs) {
            cpu_set_t cpuset;
            CPU_ZERO(&cpuset);
            CPU_SET(target_core, &cpuset);
            int ret = pthread_setaffinity_np(pthread_self(), sizeof(cpu_set_t), &cpuset);
            if (ret == 0) {
                printf("[*] Generator pinned to Core %d\n", target_core);
            } else {
                fprintf(stderr, "[WARN] pthread_setaffinity_np to Core %d failed: %s\n", target_core, strerror(ret));
            }
        } else {
            printf("[*] Target core %d exceeds online cores (%ld). Running OS-managed unpinned.\n", target_core, nprocs);
        }
    } else {
        printf("[*] Running unpinned across available CPUs.\n");
    }

    int sock_fd = socket(AF_INET, SOCK_DGRAM, 0);
    if (sock_fd < 0) { perror("socket"); return 1; }

    int sndbuf = 16 * 1024 * 1024;
    setsockopt(sock_fd, SOL_SOCKET, SO_SNDBUF, &sndbuf, sizeof(sndbuf));

    struct sockaddr_in addr;
    memset(&addr, 0, sizeof(addr));
    addr.sin_family = AF_INET;
    addr.sin_addr.s_addr = inet_addr(target_ip);
    addr.sin_port = htons(port);

    struct mmsghdr msgs[BATCH_SIZE];
    struct iovec iovecs[BATCH_SIZE];
    uint8_t payload_buf[BATCH_SIZE][PAYLOAD_SIZE];

    for (int i = 0; i < BATCH_SIZE; i++) {
        memset(payload_buf[i], 0x5A, PAYLOAD_SIZE);
        iovecs[i].iov_base = payload_buf[i];
        iovecs[i].iov_len = PAYLOAD_SIZE;
        msgs[i].msg_hdr.msg_iov = &iovecs[i];
        msgs[i].msg_hdr.msg_iovlen = 1;
        msgs[i].msg_hdr.msg_name = &addr;
        msgs[i].msg_hdr.msg_namelen = sizeof(addr);
        msgs[i].msg_hdr.msg_control = NULL;
        msgs[i].msg_hdr.msg_controllen = 0;
        msgs[i].msg_hdr.msg_flags = 0;
    }

    printf("=========================================================\n");
    printf(" TRAFFIC_GEN_V3 :: HIGH-SPEED VECTORIZED INGRESS LOAD    \n");
    printf("=========================================================\n");
    printf("[*] Destination: %s:%d | Packets: %lu | Batch Size: %d\n", target_ip, port, total_packets, BATCH_SIZE);

    struct timespec start, end;
    clock_gettime(CLOCK_MONOTONIC_RAW, &start);

    uint64_t sent = 0;
    while (sent < total_packets) {
        uint64_t remaining = total_packets - sent;
        int current_batch = (remaining < BATCH_SIZE) ? (int)remaining : BATCH_SIZE;

        int res = sendmmsg(sock_fd, msgs, current_batch, 0);
        if (res > 0) {
            sent += (uint64_t)res;
        } else if (res < 0) {
            if (errno == EAGAIN || errno == EWOULDBLOCK || errno == ENOBUFS) {
#if defined(__aarch64__)
                __asm__ __volatile__("yield");
#elif defined(__x86_64__)
                __asm__ __volatile__("pause");
#endif
                continue;
            }
            perror("[CRITICAL] sendmmsg fatal error");
            break;
        }
    }

    clock_gettime(CLOCK_MONOTONIC_RAW, &end);
    double elapsed = (end.tv_sec - start.tv_sec) + (end.tv_nsec - start.tv_nsec) / 1e9;
    double pps = (elapsed > 0.0) ? ((double)sent / elapsed) : 0.0;

    printf("[✓] Transmitted: %lu pkts | Elapsed: %.4f s | Line Rate: %'.0f pkt/sec\n", sent, elapsed, pps);
    printf("=========================================================\n");

    close(sock_fd);
    return 0;
}
