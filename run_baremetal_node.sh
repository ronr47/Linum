#!/usr/bin/env bash
set -e

echo "[*] 1. Assembling Bootloader & Kernel..."
nasm -f bin boot64_unified.asm -o boot64.bin

echo "[*] 2. Packaging Bare-Metal Disk Image with Harness..."
# Create a 64MB raw drive image
dd if=/dev/zero of=disk.img bs=1M count=64 status=none
# Write bootloader to MBR/VBR
dd if=boot64.bin of=disk.img conv=notrunc status=none

echo "[*] 3. Launching Bare-Metal QEMU Instance..."
qemu-system-x86_64 \
    -drive format=raw,file=disk.img,if=ide \
    -m 512M \
    -netdev user,id=net0,hostfwd=tcp::8080-:8080 \
    -device e1000,netdev=net0 \
    -nographic \
    -serial mon:stdio
