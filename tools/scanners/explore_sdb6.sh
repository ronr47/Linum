#!/usr/bin/env bash
set -euo pipefail

echo "============================================================"
echo " 🔍 DEEP EXPLORATION OF /dev/sdb6"
echo "============================================================"

sudo mkdir -p /mnt/sdb6_target
sudo mount -o ro /dev/sdb6 /mnt/sdb6_target

echo -e "\n[*] Contents of /cat EOF bash set e.txt on sdb6:"
cat "/mnt/sdb6_target/cat EOF bash set e.txt" || true

echo -e "\n[*] Full tree of /developer on sdb6:"
sudo ls -lahR /mnt/sdb6_target/developer/ || true

echo -e "\n[*] Home directories on sdb6:"
sudo ls -lah /mnt/sdb6_target/home/ || true
sudo find /mnt/sdb6_target/home/ -maxdepth 4 2>/dev/null | head -n 40 || true

echo -e "\n[*] Searching /mnt/sdb6_target for git repos, source files, and builds:"
sudo find /mnt/sdb6_target/developer/ /mnt/sdb6_target/home/ /mnt/sdb6_target/root/ \
    -maxdepth 5 \( -name "*.c" -o -name "*.rs" -o -name "*.asm" -o -name "Cargo.toml" -o -name "Makefile" -o -name "*.sh" -o -name "*.bin" -o -name "*.elf" \) 2>/dev/null || true

echo -e "\n[*] Searching for keywords (monolight, glk, gkl, hyper-tower, vortex, sophia):"
sudo grep -rIn --exclude-dir={proc,sys,dev,lib,lib64,usr,var} -E "monolight|glk_override|gkl_override|hyper-tower|vortex_workstation|sophia" /mnt/sdb6_target/developer /mnt/sdb6_target/home /mnt/sdb6_target/etc 2>/dev/null | head -n 30 || true

sudo umount /mnt/sdb6_target
sudo rmdir /mnt/sdb6_target
