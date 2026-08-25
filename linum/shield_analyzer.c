/* ==============================================================================
 * LINUM ADAPTIVE NETWORK RECONNAISSANCE ENGINE & DDOS SHIELD
 * Zero-Copy Driver-Level Protocol Parsing and Threshold Enforcement
 * ============================================================================== */

#include <linux/bpf.h>
#include <linux/types.h>
#include <bpf/bpf_helpers.h>
#include <linux/if_ether.h>
#include <linux/ip.h>

char _license[] SEC("license") = "GPL";

/* Telemetry Tracker: Counts packets and stores protocol metrics per IP source */
struct ip_stat {
    __u64 total_packets;
    __u64 tcp_packets;
    __u64 udp_packets;
    __u64 blocked_packets;
};

/* The Security State Storage: Map ID anchor */
struct {
    __uint(type, BPF_MAP_TYPE_HASH);
    __uint(max_entries, 2048);
    __type(key, __u32);
    __type(value, struct ip_stat);
} tracker_matrix SEC(".maps");

SEC("xdp")
int security_orchestrator(struct xdp_md *ctx)
{
    void *data_end = (void *)(long)ctx->data_end;
    void *data     = (void *)(long)ctx->data;

    // 1. Layer 2: Parse Ethernet Frame safely
    struct ethhdr *eth = data;
    if ((void *)(eth + 1) > data_end) {
        return XDP_PASS;
    }

    // Isolate pure IPv4 payloads
    if (eth->h_proto != __constant_htons(ETH_P_IP)) {
        return XDP_PASS;
    }

    // 2. Layer 3: Deep Scan IPv4 Header
    struct iphdr *iph = (void *)(eth + 1);
    if ((void *)(iph + 1) > data_end) {
        return XDP_PASS;
    }

    __u32 ip_src = iph->saddr;
    __u8 protocol = iph->protocol;

    // 3. Database Matrix Query and Creation State
    struct ip_stat *stats = bpf_map_lookup_elem(&tracker_matrix, &ip_src);
    if (!stats) {
        struct ip_stat init_entry = {1, 0, 0, 0};
        if (protocol == IPPROTO_TCP) init_entry.tcp_packets = 1;
        if (protocol == IPPROTO_UDP) init_entry.udp_packets = 1;
        
        bpf_map_update_elem(&tracker_matrix, &ip_src, &init_entry, BPF_NOEXIST);
        return XDP_PASS;
    }

    // 4. Threshold Mitigation Guard (DDoS Shield Activation Point)
    // If an individual host hammers your interface with more than 5000 frames, flag it as a threat
    if (stats->total_packets > 5000) {
        __sync_fetch_and_add(&stats->blocked_packets, 1);
        return XDP_DROP; // Drop packet instantly at hardware driver layer
    }

    // 5. Metric Analysis Classification Loop
    __sync_fetch_and_add(&stats->total_packets, 1);
    if (protocol == IPPROTO_TCP) {
        __sync_fetch_and_add(&stats->tcp_packets, 1);
    } else if (protocol == IPPROTO_UDP) {
        __sync_fetch_and_add(&stats->udp_packets, 1);
    }

    return XDP_PASS;
}
