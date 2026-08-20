#include <stdio.h>
#include <stdlib.h>
#include <sys/sysinfo.h>
#include <unistd.h>

int main(void) {
    struct sysinfo info;
    
    // Querying kernel metrics arena directly (SYS_sysinfo)
    if (sysinfo(&info) != 0) { perror("[-] sysinfo query failed"); exit(1); }
    
    printf("[+] Category IV: Information Vector Synced.\n");
    printf("    -> System Uptime: %ld seconds\n", info.uptime);
    printf("    -> Total RAM Buffer: %lu MB\n", info.totalram / 1024 / 1024);
    return 0;
}
