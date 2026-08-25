#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <fcntl.h>
#include <sys/mman.h>
#include <sys/stat.h>
#include <unistd.h>
#include <pthread.h>

typedef struct {
    const char *data;
    size_t size;
    const char *query;
    int thread_id;
} ThreadArg;

void *search_chunk(void *arg) {
    ThreadArg *targ = (ThreadArg *)arg;
    const char *line_start = targ->data;
    const char *end = targ->data + targ->size;
    size_t qlen = strlen(targ->query);

    while (line_start < end) {
        const char *line_end = memchr(line_start, '\n', end - line_start);
        if (!line_end) line_end = end;

        if ((size_t)(line_end - line_start) >= qlen) {
            for (const char *p = line_start; p <= line_end - qlen; p++) {
                if (memcmp(p, targ->query, qlen) == 0) {
                    fwrite(line_start, 1, line_end - line_start, stdout);
                    putchar('\n');
                    break;
                }
            }
        }
        line_start = line_end + 1;
    }
    return NULL;
}

int main(int argc, char *argv[]) {
    if (argc != 3) {
        fprintf(stderr, "Usage: %s <query> <file>\n", argv[0]);
        return 1;
    }

    int fd = open(argv[2], O_RDONLY);
    if (fd < 0) {
        perror("open failed");
        return 1;
    }

    struct stat sb;
    if (fstat(fd, &sb) < 0) {
        perror("fstat failed");
        close(fd);
        return 1;
    }

    const char *map = mmap(NULL, sb.st_size, PROT_READ, MAP_PRIVATE, fd, 0);
    if (map == MAP_FAILED) {
        perror("mmap failed");
        close(fd);
        return 1;
    }

    pthread_t thread;
    ThreadArg targ = {map, (size_t)sb.st_size, argv[1], 0};
    pthread_create(&thread, NULL, search_chunk, &targ);
    pthread_join(thread, NULL);

    munmap((void *)map, sb.st_size);
    close(fd);
    return 0;
}
