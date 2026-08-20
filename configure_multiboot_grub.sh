#!/usr/bin/env bash
set -euo pipefail

echo "============================================================"
echo " 🌐 CONFIGURING MULTI-BOOT: WIN10 (sda7) + UBUNTU (sda3) + EXOKERNEL"
echo "============================================================"

# 1. Detect UUIDs for sda7 (Windows 10) and sda3 (Ubuntu)
WIN_UUID=$(sudo blkid -s UUID -o value /dev/sda7 2>/dev/null || echo "")
UBUNTU_UUID=$(sudo blkid -s UUID -o value /dev/sda3 2>/dev/null || echo "")

echo "  ▶ Windows 10 Partition (/dev/sda7) UUID: ${WIN_UUID}"
echo "  ▶ Ubuntu Host Partition (/dev/sda3) UUID: ${UBUNTU_UUID}"

# 2. Append entries to /etc/grub.d/40_custom
sudo tee -a /etc/grub.d/40_custom > /dev/null << GRUB_EOF

# --- WINDOWS 10 CHAINLOADER (sda7) ---
menuentry "Windows 10 (on /dev/sda7)" --class windows --class os {
    insmod part_gpt
    insmod ntfs
    search --no-floppy --fs-uuid --set=root ${WIN_UUID}
    chainloader /EFI/Microsoft/Boot/bootmgfw.efi
}

# --- DEDICATED UBUNTU WORKSTATION (sda3) ---
menuentry "Ubuntu Linux LTS (on /dev/sda3)" --class ubuntu --class gnu-linux --class os {
    insmod part_gpt
    insmod ext2
    search --no-floppy --fs-uuid --set=root ${UBUNTU_UUID}
    linux /boot/vmlinuz root=UUID=${UBUNTU_UUID} ro quiet splash nomodeset i8042.nopnp=1
    initrd /boot/initrd.img
}

# --- BARE-METAL 64-BIT EXOKERNEL (eBPF + PMC + Tensor SIMD) ---
menuentry "Linum 64-bit Bare-Metal Engine" --class custom {
    insmod part_gpt
    insmod ext2
    set root='hd0,gpt8'
    linux /home/ron/linum/kernel64.bin
}
GRUB_EOF

echo "  [✔] Custom GRUB stanzas appended."
echo "============================================================"
echo " 🚀 Rebuilding Master GRUB Configuration Array"
echo "============================================================"
sudo update-grub
