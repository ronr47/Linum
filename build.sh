#!/bin/sh
set -e

rm -f boot.o microkernel.o io.o kernel.elf

echo '[1/5] compiling boot.S'
gcc -m32 -ffreestanding -fno-pie -fno-pic \
    -O3 -Wall -Wextra -mno-red-zone \
    -c boot.S -o boot.o

echo '[2/5] compiling microkernel.c'
gcc -m32 -ffreestanding -fno-pie -fno-pic \
    -O3 -Wall -Wextra -mno-red-zone \
    -c microkernel.c -o microkernel.o

echo '[3/5] compiling io.c'
gcc -m32 -ffreestanding -fno-pie -fno-pic \
    -O3 -Wall -Wextra -mno-red-zone \
    -c io.c -o io.o

echo '[4/5] linking kernel'
ld -m elf_i386 -T linker.ld \
    -o kernel.elf boot.o microkernel.o io.o -nostdlib

echo
echo '=== SYMBOLS ==='
nm -n kernel.elf | grep -E 'linum_entry|kernel_main'

echo
echo '=== ELF HEADER ==='
readelf -h kernel.elf | grep -E 'Class|Machine|Entry'

echo
echo '=== SECTIONS ==='
objdump -h kernel.elf | grep -E '\.(multiboot|text|rodata|data|bss)'

echo
echo '=== PROGRAM HEADERS ==='
readelf -lW kernel.elf

echo
echo '=== MULTIBOOT CHECK ==='
grub-file --is-x86-multiboot kernel.elf
echo "grub-file exit: $?"

echo
echo '[5/5] build complete'
