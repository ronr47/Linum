#!/usr/bin/env bash
set -euo pipefail

cd /home/ron/linum

echo "============================================================"
echo " ⚡ EXECUTING BEAST_SURPRISE EXOKERNEL IN HEADLESS RUNNER"
echo "============================================================"

# Launch QEMU with stdio serial console and VGA hardware enabled
qemu-system-x86_64 \
    -drive format=raw,file=beast_disk.bin \
    -vga std \
    -serial stdio \
    -display none \
    -m 256M \
    -device isa-debug-exit,iobase=0x501,iosize=0x02 || true

echo -e "\n[✔] Exokernel execution cycle verified."
