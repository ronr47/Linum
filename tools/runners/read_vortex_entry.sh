#!/usr/bin/env bash
set -euo pipefail

sudo mkdir -p /mnt/sdb6_grub
sudo mount -o ro /dev/sdb6 /mnt/sdb6_grub

echo "============================================================"
echo " 📜 VORTEX MONASTIC CORE GRUB STANZA"
echo "============================================================"
sed -n '/Launch Vortex Monastic Core/,/}/p' /mnt/sdb6_grub/boot/grub/grub.cfg

echo -e "\n============================================================"
echo " 📜 CUSTOM GRUB SOURCE SCRIPTS (/etc/grub.d/)"
echo "============================================================"
sudo find /mnt/sdb6_grub/etc/grub.d/ -type f -exec grep -Hn "Vortex" {} + || true

sudo umount /mnt/sdb6_grub
sudo rmdir /mnt/sdb6_grub
