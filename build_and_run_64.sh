#!/usr/bin/env bash
set -euo pipefail

cd /home/ron/linum

# 1. Assemble MBR
nasm -f bin boot64_unified.asm -o boot64.bin

# 2. Compile C Kernel
gcc -m64 -O3 -mno-red-zone -Wall -Wextra -ffreestanding -fno-pie -fno-stack-protector \
    -c kernel64_unified.c -o kernel64.o

# 3. Link flat binary using linker64.ld
ld -m elf_x86_64 -T linker64.ld -o kernel64.elf kernel64.o
objcopy -O binary kernel64.elf kernel64.bin

# 4. Construct bootable image (512B MBR + Kernel payload)
cat boot64.bin kernel64.bin > os_unified_disk.bin
truncate -s 65536 os_unified_disk.bin

echo "  [✔] os_unified_disk.bin built successfully ($(stat -c%s os_unified_disk.bin) bytes)"

# 5. Run serial verification in QEMU
python3 /home/ron/linum/capture_fiber_run.py
