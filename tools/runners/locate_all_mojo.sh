#!/usr/bin/env bash
set -euo pipefail

echo "============================================================"
echo " 🔍 LOCATING MOJO & MODULAR BINARIES ON sda3 & sdb6"
echo "============================================================"

# Check mounted sda3
if [ -d "/mnt/ubuntu_sda3" ]; then
    echo "  ▶ Scanning /mnt/ubuntu_sda3 for mojo binaries:"
    sudo find /mnt/ubuntu_sda3/ -name "mojo" -type f 2>/dev/null || true
fi

# Mount and check sdb6
sudo mkdir -p /mnt/sdb6_tools
if sudo mount -o ro /dev/sdb6 /mnt/sdb6_tools 2>/dev/null; then
    echo "  ▶ Scanning /dev/sdb6 for mojo & modular:"
    sudo find /mnt/sdb6_tools/home/ /mnt/sdb6_tools/root/ /mnt/sdb6_tools/opt/ /mnt/sdb6_tools/usr/ \
        \( -name "mojo" -o -name "modular" -o -name "pixi" \) -type f 2>/dev/null || true
    sudo umount /mnt/sdb6_tools
fi
sudo rmdir /mnt/sdb6_tools 2>/dev/null || true
