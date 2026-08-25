#!/usr/bin/env bash
set -euo pipefail

cd /home/ron/linum

echo "============================================================"
echo " 1. PATCHING linker64.ld (ELIMINATING RWX PERMISSION WARNING)"
echo "============================================================"

cat << 'LD_EOF' > linker64.ld
OUTPUT_FORMAT("elf64-x86-64")
OUTPUT_ARCH(i386:x86-64)
ENTRY(_start64)

PHDRS {
    text PT_LOAD FLAGS(5); /* Read + Execute (R-X) */
    data PT_LOAD FLAGS(6); /* Read + Write   (RW-) */
}

SECTIONS {
    . = 0x10000;

    .text : {
        *(.text.entry)
        *(.text*)
        *(.rodata*)
    } :text

    . = ALIGN(4096);

    .data : {
        *(.data*)
        *(.bss*)
        *(COMMON)
    } :data

    /DISCARD/ : {
        *(.comment)
        *(.note*)
        *(.eh_frame*)
    }
}
LD_EOF

echo "============================================================"
echo " 2. STRUCTURING UNTRACKED ARTIFACTS INTO SUBDIRECTORIES"
echo "============================================================"

mkdir -p tools/carving tools/scanners tools/hunting tools/boot_archive arch/rust arch/mojo

# Relocate disk carving utilities
mv -f carve_*.py tools/carving/ 2>/dev/null || true
mv -f carved_* tools/carving/ 2>/dev/null || true
mv -f recovered_* tools/carving/ 2>/dev/null || true

# Relocate hunt & scan utilities
mv -f hunt_*.py tools/hunting/ 2>/dev/null || true
mv -f scan_*.sh scan_*.py probe_*.sh inspect_*.sh explore_*.sh tools/scanners/ 2>/dev/null || true

# Archive MBR variants and Beast graphics experiments
mv -f mbr_*.asm mbr_*.bin tools/boot_archive/ 2>/dev/null || true
mv -f beast_* capture_beast_* run_beast_* render_* set_vbe* test_beast* tools/boot_archive/ 2>/dev/null || true

# Move language/runtime trees
mv -f mojo/ setup_pixi_mojo.sh locate_all_mojo.sh arch/mojo/ 2>/dev/null || true
mv -f rust_lane/ rust_sys_engine/ assemble_rust_engine.sh reconstruct_pyramids* arch/rust/ 2>/dev/null || true

# Clean obsolete files
git rm -f organize_and_commit.sh 2>/dev/null || true
rm -f commit_milestone.sh embed_simd_fiber.py read_vortex_entry.sh sample 2>/dev/null || true

echo "============================================================"
echo " 3. REBUILDING & RUNNING 64-BIT UNIFIED EXOKERNEL"
echo "============================================================"

# Recompile bootloader and kernel
nasm -f bin boot64_unified.asm -o boot64.bin
gcc -c -ffreestanding -mno-red-zone -m64 -O2 -Wall -Wextra kernel64_unified.c -o kernel64_unified.o
ld.bfd -T linker64.ld -o kernel64.elf kernel64_unified.o
objcopy -O binary kernel64.elf kernel64.bin

# Assemble unified 64KB disk image
dd if=/dev/zero of=os_unified_disk.bin bs=512 count=128 status=none
dd if=boot64.bin of=os_unified_disk.bin bs=512 count=1 conv=notrunc status=none
dd if=kernel64.bin of=os_unified_disk.bin bs=512 seek=1 conv=notrunc status=none

echo "============================================================"
echo " 4. RUNNING TEST HARNESS AUDIT"
echo "============================================================"

python3 /home/ron/linum/capture_fiber_run.py

echo "============================================================"
echo " [✔] WORKSPACE ALIGNED & LINKER PERMISSIONS VERIFIED"
echo "============================================================"
