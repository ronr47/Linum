#!/bin/bash
set -e 

echo "================================================================="
echo "🔨 COMPILING BARE-METAL KERNEL MODULES"
echo "================================================================="

echo "[+] Assembling boot stub layout..."
clang -m32 -c beast/kernel/boot.s -o beast/kernel/boot.o

echo "[+] Linking object modules into final flat ELF image..."
ld -m elf_i386 -T beast/kernel/linker.ld -o beast/kernel/beast.elf \
    beast/kernel/boot.o \
    beast/kernel/kernel.o \
    beast/kernel/interrupts.o \
    beast/kernel/keyboard_matrix.o \
    beast/kernel/vga_stream.o

echo -e "\n================================================================="
echo "🖥️ LAUNCHING TARGET MACHINE INSTANCE (QEMU)"
echo "================================================================="
qemu-system-i386 -kernel beast/kernel/beast.elf
