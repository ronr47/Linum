#!/usr/bin/env bash
set -euo pipefail

echo "============================================================"
echo " 🚀 INITIALIZING BEAST RAM (Zero-Latency Compressed Memory)"
echo "============================================================"

# 1. Deactivate if already enabled
sudo swapoff /dev/zram0 2>/dev/null || true

# 2. Reset zram device
if [ -f /sys/block/zram0/reset ]; then
    echo 1 | sudo tee /sys/block/zram0/reset >/dev/null 2>&1 || true
fi

# 3. Load module fresh if needed
sudo modprobe zram num_devices=1 2>/dev/null || true

# 4. Set compression algorithm (zstd or lz4)
if grep -q zstd /sys/block/zram0/comp_algorithm 2>/dev/null; then
    echo zstd | sudo tee /sys/block/zram0/comp_algorithm >/dev/null
    echo "  [✔] Compression Engine: zstd (High ratio)"
elif grep -q lz4 /sys/block/zram0/comp_algorithm 2>/dev/null; then
    echo lz4 | sudo tee /sys/block/zram0/comp_algorithm >/dev/null
    echo "  [✔] Compression Engine: lz4 (Ultra-fast)"
fi

# 5. Set capacity to 4 GB
echo "4G" | sudo tee /sys/block/zram0/disksize >/dev/null

# 6. Format and activate swap with top priority (pri=32767)
sudo mkswap /dev/zram0 >/dev/null
sudo swapon -p 32767 /dev/zram0

# 7. Aggressive kernel memory tuning to prevent OOM
sudo sysctl -w vm.swappiness=180 >/dev/null
sudo sysctl -w vm.page-cluster=0 >/dev/null

echo "============================================================"
echo " [★] BEAST RAM ONLINE! Topology Status:"
echo "============================================================"
swapon --show
free -h
