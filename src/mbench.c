#include <stdio.h>
#include <stdlib.h>
#include <time.h>
#include <pthread.h>
#include <unistd.h>

#define THREADS 4
#define ITERATIONS 10000

void* workload(void* arg) {
    long id = (long)arg;
    clock_t start = clock();
    
    // Simulate high-frequency memory/search ticks
    for (int i = 0; i < ITERATIONS; i++) {
        volatile int x = i * id;
        (void)x;
    }
    
    clock_t end = clock();
    double cpu_time_used = ((double) (end - start)) / CLOCKS_PER_SEC;
    printf("[Thread %ld] Completed %d cycles in %.4f seconds\n", id, ITERATIONS, cpu_time_used);
    return NULL;
}

int main() {
    pthread_t t[THREADS];
    printf("=== LINUM STACK PERFORMANCE BENCHMARK ===\n");
    clock_t total_start = clock();

    for (long i = 0; i < THREADS; i++) {
        pthread_create(&t[i], NULL, workload, (void*)i);
    }

    for (int i = 0; i < THREADS; i++) {
        pthread_join(t[i], NULL);
    }

    clock_t total_end = clock();
    printf("=== BENCHMARK COMPLETE (Total Time: %.4f seconds) ===\n", 
        ((double)(total_end - total_start)) / CLOCKS_PER_SEC);
    return 0;
}
