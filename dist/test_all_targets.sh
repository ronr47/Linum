#!/bin/sh
set -e

echo "=== [1/2] Testing Native AArch64 Target ==="
make clean
make proofboot_runner
./proofboot_runner

echo ""
echo "=== [2/2] Cross-Compiling and Executing Static x86_64 Target via QEMU ==="
CLANG_INC=$(clang -print-resource-dir)/include

clang -target x86_64-unknown-linux-gnu \
      -static \
      -nostdinc \
      -nostdlib \
      -fno-builtin \
      -isystem include \
      -isystem "$CLANG_INC" \
      -Wall -Wextra -Wno-unused-variable -Wno-unused-label -O2 \
      -Wl,-e,_start \
      proofboot_pb010.c test_runner.c runtime_x86_64.c \
      -o proofboot_runner_x86_64

file proofboot_runner_x86_64
qemu-x86_64 ./proofboot_runner_x86_64

echo ""
echo "[OK] Multi-device verification passed (AArch64 + x86_64)!"
