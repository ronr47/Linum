#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <sys/socket.h>
#include <arpa/inet.h>
#include <netinet/ether.h>
#include <linux/if_packet.h>
#include <net/ethernet.h>

#define BUFFER_SIZE 65536

int main(void) {
    int sock_raw = socket(AF_PACKET, SOCK_RAW, htons(ETH_P_ALL));
    if (sock_raw < 0) {
        perror("Socket Error (Are you root?)");
        return 1;
    }

    unsigned char *buffer = (unsigned char *)malloc(BUFFER_SIZE);
    printf("msniff listening for raw packets...\n");

    for (int i = 0; i < 5; i++) { // Capture 5 packets for demonstration
        ssize_t data_size = recvfrom(sock_raw, buffer, BUFFER_SIZE, 0, NULL, NULL);
        if (data_size < 0) {
            perror("Recvfrom error");
            break;
        }

        struct ethhdr *eth = (struct ethhdr *)buffer;
        printf("Packet Captured: Length: %zd bytes | Protocol: 0x%04x\n", 
               data_size, ntohs(eth->h_proto));
    }

    free(buffer);
    close(sock_raw);
    return 0;
}
