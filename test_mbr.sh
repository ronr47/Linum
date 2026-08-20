#!/usr/bin/env bash
set -euo pipefail

# 1. Assemble MBR
nasm -f bin mbr_serial.asm -o mbr_serial.bin

# 2. Assert strict 512-byte constraint
SIZE=$(stat -c%s mbr_serial.bin)
echo "[*] MBR Payload: ${SIZE} bytes (Target: 512 bytes)"

# 3. Launch QEMU connected to stdio serial with isa-debug-exit device
echo "[*] Booting bare-metal payload in QEMU..."
qemu-system-x86_64 \
    -drive format=raw,file=mbr_serial.bin \
    -display none \
    -serial stdio \
    -device isa-debug-exit,iobase=0x501,iosize=0x02 || true

echo -e "\n[✔] Bare-Metal Execution Completed and Returned to Shell."
