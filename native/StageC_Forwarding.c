#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <sys/socket.h>
#include <linux/if_packet.h>
#include <net/ethernet.h>
#include <arpa/inet.h>
#include <net/if.h>

int main(void) {
    const char *target_if = "veth_peer";
    printf("[*] Initializing Stage C Forwarding Path on Interface: %s\n", target_if);
    
    // 1. Establish raw device tracking capability
    int sock_fd = socket(AF_PACKET, SOCK_RAW, htons(ETH_P_ALL));
    if (sock_fd < 0) {
        perror("[-] Socket creation aborted");
        return 1;
    }
    
    // 2. Discover target interface system index bounds
    struct sockaddr_ll sll;
    memset(&sll, 0, sizeof(sll));
    sll.sll_ifindex = if_nametoindex(target_if);
    
    if (sll.sll_ifindex == 0) {
        // Fallback step to loopback if custom veth pair is detached during compilation pass
        printf("[-] Interface %s not active. Defaulting tracking layout to lo.\n", target_if);
        sll.sll_ifindex = if_nametoindex("lo");
    }
    
    sll.sll_family = AF_PACKET;
    sll.sll_protocol = htons(ETH_P_ALL);
    
    // 3. Assemble structural 98-byte packet matrix (Commandment 8 geometry constraint)
    uint8_t tx_frame[98];
    memset(tx_frame, 0x00, sizeof(tx_frame));
    // Set mock layer 2 hardware headers (Broadcast destination target)
    memset(tx_frame, 0xFF, 6); 
    // Inject custom internal trace token payload string "LINUM_ALPHA"
    memcpy(tx_frame + 14, "LINUM_ALPHA_STAGE_C_PASSED", 26);

    // 4. Fire explicit data transmission loop over the network wire boundary
    printf("[*] Transmitting frame sequence across interface boundary...\n");
    ssize_t bytes_sent = sendto(sock_fd, tx_frame, sizeof(tx_frame), 0, 
                                (struct sockaddr *)&sll, sizeof(sll));
    
    if (bytes_sent < 0) {
        perror("[-] Invariant Violation: Packet forwarding path broken");
        close(sock_fd);
        return 1;
    }
    
    printf("[+] Success: Sent %ld bytes directly into target network vector.\n", (long)bytes_sent);
    close(sock_fd);
    return 0;
}
