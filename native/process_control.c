#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <sys/wait.h>
#include <sys/types.h>

int main(void) {
    pid_t pid = fork();
    if (pid < 0) {
        perror("[-] fork failed");
        exit(1);
    } else if (pid == 0) {
        char *args[] = {"/bin/ls", "-la", NULL};
        execve(args[0], args, NULL);
        perror("[-] execve failed");
        exit(1);
    } else {
        int status;
        printf("[+] Parent tracking child PID: %d\n", pid);
        wait(&status);
        printf("[+] Child terminated. Status returned: %d\n", status);
    }
    return 0;
}
