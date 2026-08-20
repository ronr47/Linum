#!/usr/bin/env bash
set -euo pipefail

echo "============================================================"
echo " 🔍 BLOCK DEVICE & PARTITION TOPOLOGY"
echo "============================================================"
lsblk -o NAME,SIZE,FSTYPE,TYPE,MOUNTPOINTS,LABEL,UUID

echo -e "\n============================================================"
echo " 🔍 LOCAL ELFs IN ~/linum"
echo "============================================================"
cd /home/ron/linum
for elf in $(find . -maxdepth 2 -type f -name "*.elf"); do
    echo "--- File: $elf ---"
    readelf -h -l "$elf" 2>/dev/null | grep -E "(Class|Type|Machine|Entry point|LOAD)" || true
done

echo -e "\n============================================================"
echo " 🔍 SEARCHING POTENTIAL UBUNTU PARTITIONS (sdb2, sdc2, etc.)"
echo "============================================================"
sudo mkdir -p /mnt/audit_target

for part in $(lsblk -lnpo NAME,TYPE | awk '$2=="part" {print $1}'); do
    echo "[*] Checking partition: $part"
    if sudo mount -o ro "$part" /mnt/audit_target 2>/dev/null; then
        echo "  [✔] Mounted $part successfully"
        if [ -d "/mnt/audit_target/home" ] || [ -f "/mnt/audit_target/vmlinuz" ] || [ -f "/mnt/audit_target/etc/os-release" ]; then
            echo "  [★] Detected OS installation on $part:"
            [ -f /mnt/audit_target/etc/os-release ] && grep "PRETTY_NAME" /mnt/audit_target/etc/os-release || true
            echo "  ▶ Searching for candidate baremetal .elf files..."
            sudo find /mnt/audit_target/ -maxdepth 4 -type f -name "*.elf" 2>/dev/null || true
        fi
        sudo umount /mnt/audit_target
    else
        echo "  [-] Could not mount $part (might be swap, LVM, or unsupported FS)"
    fi
done

sudo rmdir /mnt/audit_target
