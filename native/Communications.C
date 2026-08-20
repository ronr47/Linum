#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <string.h>

int main(void) {
    int pipefd[2]; // Two elements tracking Read [0] and Write [1] pipelines
    char buffer[32];
    memset(buffer, 0, sizeof(buffer));
    
    // Instantiate POSIX inter-process communication conduit (SYS_pipe)
    if (pipe(pipefd) == -1) { 
        perror("[-] Inter-process channel crash"); 
        exit(1); 
    }
    
    // Write down to vector [1] and pull back out from vector [0]
    write(pipefd[1], "KERNEL_CHAN_ALPHA", 17);
    read(pipefd[0], buffer, 17);
    
    printf("[+] Category V: Pipe Communications Verified: %s\n", buffer);
    close(pipefd[0]);
    close(pipefd[1]);
    return 0;
}
