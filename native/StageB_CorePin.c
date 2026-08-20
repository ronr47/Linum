#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <sched.h>
#include <unistd.h>

int main(void) {
    cpu_set_t cpuset;
    CPU_ZERO(&cpuset);
    CPU_SET(1, &cpuset); // Hard-bind execution exclusively to CPU Core 1

    printf("[*] Isolating execution vector to dedicated CPU Core 1...\n");
    if (sched_setaffinity(0, sizeof(cpu_set_t), &cpuset) == -1) {
        perror("[-] Core affinity binding failed");
        return 1;
    }

    printf("[+] Thread anchored. Execution immune to OS migration latency.\n");
    return 0;
}
