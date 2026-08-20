/* Generated Automatically by LINUM — DO NOT EDIT MANUALLY */
#include <linux/bpf.h>
#include <linux/types.h>
#include <bpf/bpf_helpers.h>
#include <linux/if_ether.h>
#include <linux/ip.h>

char _license[] SEC("license") = "GPL";

struct {
    __uint(type, BPF_MAP_TYPE_HASH);
    __uint(max_entries, 1024);
    __type(key, __u32);
    __type(value, __u64);
} telemetry_map SEC(".maps");

struct {
    __uint(type, BPF_MAP_TYPE_XSKMAP);
    __uint(max_entries, 2);
    __type(key, __u32);
    __type(value, __u32);
} xsks_map SEC(".maps");

SEC("xdp")
int xdp_prog(struct xdp_md *ctx)
{
    void *data_end = (void *)(long)ctx->data_end;
    void *data     = (void *)(long)ctx->data;

    struct ethhdr *eth = data;
    if ((void *)(eth + 1) > data_end) {
        return XDP_PASS;
    }

    if (eth->h_proto != __constant_htons(ETH_P_IP)) {
        return XDP_PASS;
    }

    struct iphdr *iph = (void *)(eth + 1);
    if ((void *)(iph + 1) > data_end) {
        return XDP_PASS;
    }

    __u32 ip_src = iph->saddr;
    __u64 *counter;

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

    return bpf_redirect_map(&xsks_map, ctx->rx_queue_index, XDP_PASS);
}
