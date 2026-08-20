#!/usr/bin/env bash
set -euo pipefail

echo "============================================================"
echo " 🔍 SCANNING EXT4 PARTITIONS ON SDB (sdb6, sdb7, sdb9, sdb10)"
echo "============================================================"

sudo mkdir -p /mnt/sdb_audit

for p in /dev/sdb6 /dev/sdb7 /dev/sdb9 /dev/sdb10; do
    echo -e "\n[*] Checking partition: $p"
    if sudo mount -o ro "$p" /mnt/sdb_audit 2>/dev/null; then
        echo "  [✔] Successfully mounted $p"
        echo "  ▶ Root items:"
        ls -lah /mnt/sdb_audit/ | head -n 15
        
        echo "  ▶ Searching for 'sophia' (case-insensitive):"
        sudo find /mnt/sdb_audit/ -iname "*sophia*" 2>/dev/null | head -n 20 || true
        
        echo "  ▶ Searching for workspace repositories or git trees:"
        sudo find /mnt/sdb_audit/ -maxdepth 3 -type d -name ".git" 2>/dev/null || true
        
        sudo umount /mnt/sdb_audit
    else
        echo "  [-] Could not mount $p"
    fi
done

sudo rmdir /mnt/sdb_audit 2>/dev/null || true
