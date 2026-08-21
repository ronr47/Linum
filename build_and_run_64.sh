#!/usr/bin/env bash
# ~/linum/build_and_run_64.sh // Hardened Exokernel Builder & Linker Script
set -euo pipefail

# Step 1: Re-compile the raw C kernel module with freestanding system parameters
gcc -O3 -march=native -ffreestanding -mno-red-zone -c kernel64_unified.c -o kernel64.o --param l1-cache-line-size=64

# Step 2: Bind the bootloader assembly code block
nasm -f elf64 boot64_unified.asm -o boot64.o

# Step 3: Link objects along with the pre-compiled Vector Core matrix object
ld.bfd -T linker64.ld -o kernel64.elf boot64.o kernel64.o /home/ron/linum/src/transformer_core.o

# Step 4: Extract the execution binary blob free of debug payloads
objcopy -O binary kernel64.elf kernel64.bin

# Step 5: Package into the flat disk architecture image block
dd if=/dev/zero of=os_unified_disk.bin bs=1024 count=64 status=none
dd if=kernel64.bin of=os_unified_disk.bin conv=notrunc status=none

printf "  [✔] os_unified_disk.bin built successfully (65536 bytes)\n"
