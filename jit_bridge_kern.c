#include <linux/bpf.h>
#include <bpf/bpf_helpers.h>

struct packet_event {
    __u64 timestamp;
    __u32 raw_word;
    __u16 pkt_len;
};

struct {
    __uint(type, BPF_MAP_TYPE_RINGBUF);
    __uint(max_entries, 256 * 1024); /* 256 KB ring */
} jit_ringbuf SEC(".maps");

SEC("xdp")
int xdp_jit_producer(struct xdp_md *ctx) {
    void *data = (void *)(long)ctx->data;
    void *data_end = (void *)(long)ctx->data_end;

    if (data + 32 > data_end)
        return XDP_PASS;

    struct packet_event *e = bpf_ringbuf_reserve(&jit_ringbuf, sizeof(*e), 0);
    if (!e)
        return XDP_PASS;

    e->timestamp = bpf_ktime_get_ns();
    e->raw_word = *(__u32 *)data;
    e->pkt_len = (__u16)(data_end - data);

    bpf_ringbuf_submit(e, 0);
    return XDP_PASS;
}

char _license[] SEC("license") = "GPL";
