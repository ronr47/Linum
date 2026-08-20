#!/bin/bash
echo "[*] Restoring Hardened Freestanding Matrix Parameters (Baseline 10)..."

# Force real-time low-latency kernel polling parameters
sudo sysctl -w net.core.busy_poll=50
sudo sysctl -w net.core.busy_read=50

# Re-apply packet descriptor capabilities to compiled binary vectors
sudo setcap cap_net_raw+ep /home/ron/linum/linum_stage_c_exec 2>/dev/null || true

echo "[+] System parameters synced. Launching lock-free pipeline on Core 1..."
taskset -c 1 ./linum_lockfree_exec
