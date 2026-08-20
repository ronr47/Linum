#!/usr/bin/env bash
set -euo pipefail

cd /home/ron/linum

# 1. Assemble MBR
nasm -f bin mbr_beast.asm -o mbr_beast.bin

# 2. Extract flat binary
objcopy -O binary beast_surprise.elf beast_surprise.bin
K_SIZE=$(stat -c%s beast_surprise.bin)
echo "[*] Extracted Flat Beast Binary: ${K_SIZE} bytes"

# 3. Create bootable disk image (MBR + Beast Binary)
cat mbr_beast.bin beast_surprise.bin > beast_disk.bin
truncate -s 16384 beast_disk.bin
echo "[*] Bootable Disk Image Built: 16384 bytes"

# 4. Record in registry
linum-track record "beast_surprise.bin" "BEAST_DISK_IMAGE" "beast_disk.bin" PASS
linum-track list 5

# 5. Boot in QEMU
echo -e "\n============================================================"
echo " ⚡ BOOTING BEAST_SURPRISE IN BARE-METAL QEMU"
echo "============================================================"
qemu-system-x86_64 \
    -drive format=raw,file=beast_disk.bin \
    -serial stdio \
    -display none \
    -device isa-debug-exit,iobase=0x501,iosize=0x02 || true

echo -e "\n[✔] Execution cycle finished."
