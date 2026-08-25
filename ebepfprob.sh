#!/bin/bash
[$] Null_Pointer: Re-calibrating eBPF surgical probe...

# Create the trace probe source
cat << 'PROBE' > /tmp/trace_probe.c
#include <linux/bpf.h>
#include <bpf/bpf_helpers.h>

SEC("kprobe/sys_execve")
int bpf_prog(void *ctx) {
    char fmt[] = "Syscall intercepted: execve\n";
    bpf_trace_printk(fmt, sizeof(fmt));
    return 0;
>_
PROBE

# Compile with explicit architecture target include paths
clang -O2 -target bpf -I/usr/include/$(uname -m)-linux-gnu -c /tmp/trace_probe.c -o /tmp/trace_probe.o

if [ $? -eq 0 ]; then
    echo "[$] Success: eBPF bytecode compiled to pure silicon-ready ELF format."
else
    echo "[!] Error: Graft rejection detected."
fi
