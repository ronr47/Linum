#!/usr/bin/env bash
set -euo pipefail

cd /home/ron/linum

echo "============================================================"
echo " 🔍 LINUM SYSTEM AUDIT: REPO, BINARIES & QEMU VERIFICATION"
echo "============================================================"

echo "▶ 1. Checking 64-bit ELF Entry Point..."
readelf -h kernel64.elf | grep -E "Entry point|Type|Machine"

echo -e "\n▶ 2. Verifying Partition Multi-Boot Targets..."
sudo grep -E "menuentry 'Windows|menuentry 'Ubuntu" /boot/grub/grub.cfg | head -n 3

echo -e "\n▶ 3. Running Live QEMU 3-Fiber Execution Test..."
python3 /home/ron/linum/capture_fiber_run.py
