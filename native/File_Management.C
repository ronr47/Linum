#include <stdio.h>
#include <stdlib.h>
#include <fcntl.h>
#include <unistd.h>
#include <string.h>

int main(void) {
    const char *path = "sys_matrix_test.txt";
    const char *data = "System Call Framework Base 10\n";
    
    // Low-level direct handle creation (SYS_open)
    int fd = open(path, O_CREAT | O_WRONLY | O_TRUNC, 0644);
    if (fd < 0) { perror("[-] File create failed"); exit(1); }
    
    // Explicit I/O write (SYS_write)
    write(fd, data, strlen(data));
    close(fd);
    printf("[+] Category II: File created and validated successfully.\n");
    return 0;
}
