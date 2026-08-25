#include <linux/bpf.h>
#include <bpf/bpf_helpers.h>

SEC("xdp")
int xdp_metamorphic_hook(struct xdp_md *ctx) {
    void *data = (void *)(long)ctx->data;
    void *data_end = (void *)(long)ctx->data_end;
    
    if (data + 64 > data_end)
        return XDP_PASS;

    unsigned long long *val = (unsigned long long *)data;
    *val = (*val + 42) ^ 0xAA;
    
    return XDP_PASS;
}
char _license[] SEC("license") = "GPL";
