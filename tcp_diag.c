#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <string.h>
#include <errno.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <sys/time.h>

#define BRIDGE_HOST "127.0.0.1"
#define BRIDGE_PORT 8888

void send_cmd(int sock, const char *cmd) {
    char buf[512];
    write(sock, cmd, strlen(cmd));
    write(sock, "\r", 1);
    printf(">> %s\n", cmd);

    usleep(250000); // 250ms for adapter buffer processing

    memset(buf, 0, sizeof(buf));
    int n = read(sock, buf, sizeof(buf) - 1);
    if (n > 0) {
        printf("<< %s\n", buf);
    } else {
        printf("<< [NO RESPONSE / TIMEOUT]\n");
    }
}

int main(int argc, char **argv) {
    int port = (argc > 1) ? atoi(argv[1]) : BRIDGE_PORT;

    int sock = socket(AF_INET, SOCK_STREAM, 0);
    if (sock < 0) {
        perror("[-] socket(AF_INET) failed");
        return 1;
    }

    struct sockaddr_in saddr;
    memset(&saddr, 0, sizeof(saddr));
    saddr.sin_family = AF_INET;
    saddr.sin_port = htons(port);
    inet_pton(AF_INET, BRIDGE_HOST, &saddr.sin_addr);

    struct timeval tv = { .tv_sec = 4, .tv_usec = 0 };
    setsockopt(sock, SOL_SOCKET, SO_RCVTIMEO, (const char*)&tv, sizeof(tv));

    printf("[*] Connecting to local TCP bridge at %s:%d...\n", BRIDGE_HOST, port);
    if (connect(sock, (struct sockaddr *)&saddr, sizeof(saddr)) < 0) {
        printf("[-] connect() failed: %s (errno=%d)\n", strerror(errno), errno);
        printf("[!] Make sure the TCP server is running in your Android bridge app.\n");
        close(sock);
        return 1;
    }

    printf("[+] Connected to adapter bridge!\n\n");

    // Adapter initialisation
    send_cmd(sock, "ATZ");    // Reset
    send_cmd(sock, "ATE0");   // Echo off
    send_cmd(sock, "ATI");    // Firmware ID
    send_cmd(sock, "ATRV");   // Voltage at OBD Pin 16

    // Navara CAN sync & module check
    send_cmd(sock, "ATSP0");  // Auto-search protocol
    send_cmd(sock, "0100");   // OBD Service 01 PID 00

    close(sock);
    printf("[*] Session closed.\n");
    return 0;
}
