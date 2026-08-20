#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <sys/wait.h>

int main(void) {
    pid_t pid = fork();

    if (pid < 0) {
        perror("fork failed");
        exit(EXIT_FAILURE);
    } else if (pid == 0) {
        // Child process
        char *args[] = {"/bin/ls", "-l", NULL};
        execve(args[0], args, NULL);
        perror("execve failed");
        _exit(EXIT_FAILURE);
    } else {
        // Parent process
        int status;
        waitpid(pid, &status, 0);
        printf("Child process terminated with status: %d\n", status);
    }
    return 0;
}
