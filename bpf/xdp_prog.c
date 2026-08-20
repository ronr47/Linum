#include <linux/bpf.h>
#include <linux/types.h>
#include <bpf/bpf_helpers.h>
#include <linux/if_ether.h>
#include <linux/ip.h>

char _license[] SEC("license") = "GPL";

/* 
 * Structure 1: Race-Free Keyed Tracker
 */
struct {
    __uint(type, BPF_MAP_TYPE_HASH);
    __uint(max_entries, 1024);
    __type(key, __u32);   /* Key = IPv4 Source Address */
    __type(value, __u64); /* Value = Frame Counter */
} telemetry_map SEC(".maps");

/* 
 * Structure 2: Socket Redirection Matrix
 * Max entries set to 2 to handle our bidirectional veth queue layout cleanly.
 */
struct {
    __uint(type, BPF_MAP_TYPE_XSKMAP);
    __uint(max_entries, 2);
    __type(key, __u32);   /* Key = RX Queue Index */
    __type(value, __u32); /* Value = XSK File Descriptor */
} xsks_map SEC(".maps");

SEC("xdp")
int xdp_prog(struct xdp_md *ctx)
{
    void *data_end = (void *)(long)ctx->data_end;
    void *data     = (void *)(long)ctx->data;

    /* Layer 2: Fast Boundary Interrelation Check */
    struct ethhdr *eth = data;
    if ((void *)(eth + 1) > data_end) {
        return XDP_PASS;
    }

    /* Filter out non-IPv4 noise early */
    if (eth->h_proto != __constant_htons(ETH_P_IP)) {
        return XDP_PASS;
    }

    /* Layer 3: Bounds Validation */
    struct iphdr *iph = (void *)(eth + 1);
    if ((void *)(iph + 1) > data_end) {
        return XDP_PASS;
    }

    /* Extract the source network identity */
    __u32 ip_src = iph->saddr;
    __u64 *counter;

    /* Secure State Mutation Pipeline */
    counter = bpf_map_lookup_elem(&telemetry_map, &ip_src);
    if (counter) {
        __sync_fetch_and_add(counter, 1);
    } else {
        __u64 initial_value = 1;
        long err = bpf_map_update_elem(&telemetry_map, &ip_src, &initial_value, BPF_NOEXIST);
        if (err < 0) {
            counter = bpf_map_lookup_elem(&telemetry_map, &ip_src);
            if (counter) {
                __sync_fetch_and_add(counter, 1);
            }
        }
    }

    /* 
     * THE REDIRECT HOOK
     * If an active AF_XDP socket descriptor is registered inside xsks_map at the 
     * current queue index slot, the kernel will shunt the frame straight to userspace.
     * Fallback to XDP_PASS if the socket matrix slot is currently unpopulated.
     */
    return bpf_redirect_map(&xsks_map, ctx->rx_queue_index, XDP_PASS);
}
