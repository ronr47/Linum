#!/usr/bin/env bash
set -euo pipefail

echo "============================================================"
echo " 🔍 PROBING sdb3 (231G) AND sdb5 (200G) SIGNATURES"
echo "============================================================"

sudo blkid /dev/sdb3 /dev/sdb5 || true
sudo file -s /dev/sdb3 /dev/sdb5 || true

sudo mkdir -p /mnt/sdb3_target /mnt/sdb5_target

for part in /dev/sdb3 /dev/sdb5; do
    echo -e "\n[*] Testing mount for $part..."
    for fs in ext4 btrfs xfs f2fs ntfs-3g vfat; do
        if sudo mount -t "$fs" -o ro "$part" /mnt/sdb3_target 2>/dev/null; then
            echo "  [★] Mounted $part successfully as $fs"
            ls -lah /mnt/sdb3_target/ | head -n 25
            echo "  ▶ Searching for core targets..."
            sudo find /mnt/sdb3_target/ -maxdepth 5 \( -iname "*monolight*" -o -iname "*glk*" -o -iname "*gkl*" -o -iname "*hyper-tower*" -o -iname "*vortex*" -o -iname "*sophia*" \) 2>/dev/null || true
            sudo umount /mnt/sdb3_target
            break
        fi
    done
done

sudo rmdir /mnt/sdb3_target /mnt/sdb5_target 2>/dev/null || true
