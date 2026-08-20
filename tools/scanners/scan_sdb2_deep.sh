#!/usr/bin/env bash
set -euo pipefail

echo "============================================================"
echo " 🔍 DEEP FORENSIC & KERNEL AUDIT ON /dev/sdb2"
echo "============================================================"

# 1. Inspect raw filesystem signature and partition block header
sudo blkid /dev/sdb2 || true
sudo file -s /dev/sdb2 || true

# 2. Try mounting with different filesystem drivers
sudo mkdir -p /mnt/sdb2_target
MOUNTED=0

for fs in ext4 ext3 ext2 btrfs xfs f2fs ntfs-3g vfat iso9660; do
    if sudo mount -t "$fs" -o ro /dev/sdb2 /mnt/sdb2_target 2>/dev/null; then
        echo "  [★] Successfully mounted /dev/sdb2 as filesystem: $fs"
        MOUNTED=1
        break
    fi
done

if [ "$MOUNTED" -eq 1 ]; then
    echo -e "\n[*] Root directory listing on /dev/sdb2:"
    ls -lah /mnt/sdb2_target/ | head -n 30
    
    echo -e "\n[*] Searching for kernels, ELFs, ISOs, and development tools on /dev/sdb2..."
    sudo find /mnt/sdb2_target/ -maxdepth 4 -type f \( -name "*.elf" -o -name "*.bin" -o -name "*.iso" -o -name "vmlinuz*" -o -name "*.img" \) 2>/dev/null | head -n 50 || true
    
    sudo umount /mnt/sdb2_target
else
    echo "  [-] Standard filesystem mount unsuccessful."
    echo "  ▶ Performing Raw Sector Carving & ELF Magic Header Scan (First 500 MB of /dev/sdb2)..."
    
    # Check for Multiboot Header (0x1BADB002 / 0x2BADB002) and ELF Magic (\x7FELF)
    sudo python3 -c '
import os, sys

dev_path = "/dev/sdb2"
print("[*] Streaming raw blocks from", dev_path, "...")
try:
    with open(dev_path, "rb") as f:
        # Read first 128 MB in 1MB chunks
        for mb in range(128):
            chunk = f.read(1024 * 1024)
            if not chunk:
                break
            
            # Check for ELF Magic
            pos = 0
            while True:
                idx = chunk.find(b"\x7fELF", pos)
                if idx == -1:
                    break
                abs_offset = mb * 1024 * 1024 + idx
                arch = "64-bit" if chunk[idx+4] == 2 else "32-bit"
                elf_type = int.from_bytes(chunk[idx+16:idx+18], "little")
                print(f"  [★] Found Raw ELF Header at Offset: 0x{abs_offset:08X} ({abs_offset // 1024} KB) | Arch: {arch} | Type: {elf_type}")
                pos = idx + 4

            # Check for Multiboot Magic (0x1BADB002)
            idx_mb = chunk.find(b"\x02\xb0\xad\x1b")
            if idx_mb != -1:
                abs_offset = mb * 1024 * 1024 + idx_mb
                print(f"  [★] Found Multiboot Kernel Header at Offset: 0x{abs_offset:08X}")
except PermissionError:
    print("[!] Root access required to read raw block device.")
except Exception as e:
    print("[!]", e)
'
fi

sudo rmdir /mnt/sdb2_target 2>/dev/null || true
