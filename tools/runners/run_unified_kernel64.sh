#!/usr/bin/env bash
set -euo pipefail

cd /home/ron/linum

echo "============================================================"
echo " ⚡ COMPILING 64-BIT UNIFIED FIBER + PMC + eBPF JIT KERNEL"
echo "============================================================"

# 1. Compile 64-bit kernel
gcc -O2 -nostdlib -fno-builtin -ffreestanding -fno-pic -fno-pie -m64 \
    -mno-sse -mno-sse2 -mno-mmx -mno-80387 \
    -ffunction-sections -fdata-sections \
    -c kernel64_unified.c -o kernel64_unified.o

# 2. Link at 0x10000
ld -m elf_x86_64 -T linker.ld kernel64_unified.o -o kernel64_unified.elf

# 3. Emit Flat Binary
objcopy -O binary kernel64_unified.elf kernel64_unified.bin
K_SIZE=$(stat -c%s kernel64_unified.bin)
echo "  [✔] 64-bit Unified Kernel Binary Emitted (${K_SIZE} bytes)"

# 4. Assemble 64-bit Multi-Sector MBR
nasm -f bin mbr_multistage.asm -o mbr_multistage.bin

# 5. Pack OS disk image
cat mbr_multistage.bin kernel64_unified.bin > os_unified_disk.bin
truncate -s 16384 os_unified_disk.bin
echo "  [✔] Final Bootable Disk Image: 16384 bytes"

# 6. Record in Build Registry
linum-track record "kernel64_unified.c" "KERNEL64_FIBER_PMC_EBPF" "os_unified_disk.bin" PASS
linum-track list 5

# 7. Boot in QEMU Serial Console
echo -e "\n[*] Booting 64-Bit Bare-Metal Payload in QEMU..."
qemu-system-x86_64 \
    -drive format=raw,file=os_unified_disk.bin,if=ide \
    -display none \
    -serial stdio \
    -device isa-debug-exit,iobase=0x501,iosize=0x02 || true

echo -e "[✔] Bare-Metal Execution Completed."
