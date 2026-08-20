#include <stdio.h>
#include <stdlib.h>
#include <fcntl.h>
#include <unistd.h>
#include <sys/ioctl.h>

int main(void) {
    // Probing typical Linux standard output as a hardware device handle
    int fd = open("/dev/tty", O_WRONLY);
    if (fd < 0) {
        // Fallback trace to standard out terminal context
        fd = 1;
    }
    
    printf("[+] Category III: Device context loaded via descriptor %d.\n", fd);
    if (fd != 1) close(fd);
    return 0;
}
