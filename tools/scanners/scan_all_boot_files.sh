#!/usr/bin/env bash
set -euo pipefail

echo "============================================================"
echo " 🔍 COMPREHENSIVE BOOT & INITRD SCAN (sda & sdb)"
echo "============================================================"

sudo mkdir -p /mnt/boot_audit

# 1. Check sdb6 /boot
echo -e "\n[*] Inspecting /boot on /dev/sdb6 (Debian/Ubuntu Root):"
if sudo mount -o ro /dev/sdb6 /mnt/boot_audit 2>/dev/null; then
    ls -lah /mnt/boot_audit/boot/
    
    # Check grub.cfg for custom kernel stanzas (monolight, glk, beast, etc.)
    if [ -f /mnt/boot_audit/boot/grub/grub.cfg ]; then
        echo -e "\n  ▶ GRUB Menu Entries on sdb6:"
        grep -E "menuentry |linux |initrd " /mnt/boot_audit/boot/grub/grub.cfg | head -n 30 || true
    fi
    
    # Inspect EFI files if present
    if [ -d /mnt/boot_audit/boot/efi ]; then
        sudo find /mnt/boot_audit/boot/efi -type f 2>/dev/null || true
    fi
    sudo umount /mnt/boot_audit
fi

# 2. Check sda1 / sda3 / sda6 boot files
for dev in /dev/sda1 /dev/sda3 /dev/sda6 /dev/sdb1; do
    echo -e "\n[*] Checking $dev for boot/EFI structures:"
    if sudo mount -o ro "$dev" /mnt/boot_audit 2>/dev/null; then
        sudo find /mnt/boot_audit -maxdepth 3 \( -name "vmlinuz*" -o -name "initrd*" -o -name "*.efi" -o -name "*.cfg" -o -name "*.bin" -o -name "*.img" \) 2>/dev/null || true
        sudo umount /mnt/boot_audit
    fi
done

sudo rmdir /mnt/boot_audit 2>/dev/null || true
