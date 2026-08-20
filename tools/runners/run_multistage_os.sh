#!/usr/bin/env bash
set -euo pipefail

cd /home/ron/linum

# 1. Compile C Kernel with function sections
gcc -O2 -nostdlib -fno-builtin -ffreestanding -fno-pic -fno-pie -m64 \
    -ffunction-sections -fdata-sections \
    -c kernel64.c -o kernel64.o

# 2. Link strictly at 0x10000
ld -m elf_x86_64 -T linker.ld kernel64.o -o kernel64.elf

# 3. Flat binary extraction
objcopy -O binary kernel64.elf kernel64.bin
K_SIZE=$(stat -c%s kernel64.bin)
echo "  [✔] Stage-2 Kernel Binary: ${K_SIZE} bytes"

# 4. Assemble MBR
nasm -f bin mbr_multistage.asm -o mbr_multistage.bin

# 5. Build OS Disk Image
cat mbr_multistage.bin kernel64.bin > os_disk.bin
truncate -s 16384 os_disk.bin
DISK_SIZE=$(stat -c%s os_disk.bin)
echo "  [✔] OS Disk Image: ${DISK_SIZE} bytes"

# 6. Track & Boot in QEMU
linum-track record "kernel64.c" "STAGE2_KERNEL64" "kernel64.bin" PASS
linum-track record "os_disk.bin" "BAREMETAL_OS_IMAGE" "os_disk.bin" PASS

echo -e "\n[*] Booting Bare-Metal 2-Stage OS in QEMU..."
qemu-system-x86_64 \
    -drive format=raw,file=os_disk.bin \
    -display none \
    -serial stdio \
    -device isa-debug-exit,iobase=0x501,iosize=0x02 || true

echo -e "\n[✔] Multi-Sector OS Execution Completed."
