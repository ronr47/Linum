#!/usr/bin/env bash
set -euo pipefail

cd /home/ron/linum

# 1. Assemble with NASM
nasm -f bin mbr_boot.asm -o mbr_boot.bin

# 2. Assert strict 512-byte constraint
SIZE=$(stat -c%s mbr_boot.bin)
echo "MBR Payload Size: ${SIZE} bytes"
if [ "$SIZE" -ne 512 ]; then
    echo "[!] Fatal: Boot sector must be exactly 512 bytes!"
    exit 1
fi

# 3. Track in registry
linum-track record "mbr_boot.asm" "BAREMETAL_MBR" "mbr_boot.bin" PASS
linum-track list 5

# 4. Test execution in QEMU (Curses / Terminal output)
echo -e "\n[*] Launching Bare-Metal Long-Mode Kernel in QEMU..."
echo "[*] (Press Alt+2 then type 'quit' to exit QEMU if needed, or Ctrl+C)"
qemu-system-x86_64 -drive format=raw,file=mbr_boot.bin -nographic
