#!/usr/bin/env bash
set -eo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
BOLD='\033[1m'
NC='\033[0m'

echo -e "${CYAN}============================================================${NC}"
echo -e "${CYAN}${BOLD}   LINUM COMPLETE SYSTEM INVENTORY & HEALTH AUDIT GATE      ${NC}"
echo -e "${CYAN}============================================================${NC}"

# ------------------------------------------------------------------------------
# 1. TOOLCHAINS, COMPILERS & EMULATORS AUDIT
# ------------------------------------------------------------------------------
echo -e "\n${BOLD}[1/5] Auditing Core Compilers, Assemblers & Silicon Toolchains...${NC}"

check_tool() {
    local name="$1"
    local cmd="$2"
    if command -v "$cmd" >/dev/null 2>&1; then
        local ver
        ver=$($cmd --version 2>&1 | head -n 1)
        echo -e "  [✔] ${GREEN}${name}${NC} (${cmd}): ${ver}"
    else
        echo -e "  [✘] ${RED}${name}${NC} (${cmd}): NOT INSTALLED"
    fi
}

check_tool "GCC C Compiler" "gcc"
check_tool "G++ C++ Compiler" "g++"
check_tool "Clang / LLVM" "clang"
check_tool "NASM Assembler" "nasm"
check_tool "GNU Linker (ld)" "ld"
check_tool "Rust Compiler" "rustc"
check_tool "Cargo Package Manager" "cargo"
check_tool "Zig Toolchain" "zig"
check_tool "Python 3 Engine" "python3"
check_tool "QEMU x86_64 Emulator" "qemu-system-x86_64"
check_tool "Readelf Inspection Tool" "readelf"
check_tool "Objdump Binary Tool" "objdump"
check_tool "Hexdump Utility" "hexdump"

# ------------------------------------------------------------------------------
# 2. BARE-METAL & KERNEL ARTIFACTS INTEGRITY CHECK
# ------------------------------------------------------------------------------
echo -e "\n${BOLD}[2/5] Auditing Bare-Metal Bootloader, Kernel & Disk Images...${NC}"
cd /home/ron/linum || cd ~

check_file() {
    local path="$1"
    local desc="$2"
    if [ -f "$path" ]; then
        local sz
        sz=$(ls -lh "$path" | awk '{print $5}')
        echo -e "  [✔] ${GREEN}${path}${NC} (${sz}) - ${desc}"
    else
        echo -e "  [✘] ${RED}${path}${NC} - MISSING (${desc})"
    fi
}

check_file "boot64_unified.asm" "Multiboot/Long-Mode Unified ASM Source"
check_file "kernel64.elf" "ELF64 Exokernel Binary"
check_file "boot64.bin" "512-Byte Raw Boot Sector"
check_file "os_unified_disk.bin" "64KB Live QEMU Exokernel Disk"
check_file "disk.img" "8MB Raw MBR Test Drive"
check_file "linker64.ld" "x86_64 Kernel Linker Script"
check_file "kernel64_unified.c" "Unified C Kernel Source"

# Verify 0xAA55 Magic Signature on active disk images
if [ -f "os_unified_disk.bin" ]; then
    SIG=$(hexdump -v -e '/1 "%02x "' -s 510 -n 2 os_unified_disk.bin | tr -d ' ')
    if [ "$SIG" = "55aa" ]; then
        echo -e "  [✔] ${GREEN}os_unified_disk.bin MBR Signature${NC}: 0xAA55 (VALID)"
    else
        echo -e "  [✘] ${RED}os_unified_disk.bin MBR Signature${NC}: INVALID ($SIG)"
    fi
fi

# ------------------------------------------------------------------------------
# 3. HIGH-SPEED STORAGE & HARNESS LAYER (fx-harness & io_uring)
# ------------------------------------------------------------------------------
echo -e "\n${BOLD}[3/5] Auditing High-Throughput I/O & Micro-Daemons...${NC}"

check_file "batch_engine.cpp" "Batched io_uring Direct I/O Read Engine"
check_file "storage_engine.cpp" "Single-Operation Direct-IO io_uring Engine"
check_file "fx-harness/build.zig" "Zig Build Configuration"
check_file "fx-harness/src/main.zig" "Isolated Environment TCP Daemon & Carver"

if [ -f "fx-harness/zig-out/bin/fx-lightweight" ]; then
    check_file "fx-harness/zig-out/bin/fx-lightweight" "Compiled 41KB Lightweight Agent Daemon"
fi

# ------------------------------------------------------------------------------
# 4. SDB SECTOR RECOVERY & CARVED DUMPS
# ------------------------------------------------------------------------------
echo -e "\n${BOLD}[4/5] Auditing Forensic Recovery & Carved Partitions (/home/ron/sdb_*)...${NC}"

if [ -d "/home/ron/sdb_dumps" ]; then
    echo -e "  [✔] ${GREEN}/home/ron/sdb_dumps${NC} directory detected:"
    ls -lh /home/ron/sdb_dumps 2>/dev/null | awk '{if (NR>1) print "      -> " $9 " (" $5 ")"}'
else
    echo -e "  [i] /home/ron/sdb_dumps: Not generated yet."
fi

if [ -d "/home/ron/sdb_extracted" ]; then
    FILE_COUNT=$(find /home/ron/sdb_extracted -type f 2>/dev/null | wc -l)
    echo -e "  [✔] ${GREEN}/home/ron/sdb_extracted${NC} (${FILE_COUNT} extracted files present)"
fi

# ------------------------------------------------------------------------------
# 5. TEST SUITES & VALIDATION GATES STATUS
# ------------------------------------------------------------------------------
echo -e "\n${BOLD}[5/5] Auditing Verification Scripts & Test Infrastructure...${NC}"

check_file "deep_audit_targets.sh" "3-Target Matrix Gate (AVX-512, eBPF-XDP, QEMU)"
check_file "full_toolchain_audit.sh" "Master Toolchain & Fiber Execution Gate"
check_file "linum_truth_gate.sh" "Reproducible Invariant Test Suite"
check_file "capture_fiber_run.py" "QEMU Fiber Log Capture Harness"

echo -e "\n${GREEN}============================================================${NC}"
echo -e "${GREEN}${BOLD}  ✓ SYSTEM AUDIT COMPLETE: ALL ARTIFACTS SCANNED AND INDEXED${NC}"
echo -e "${GREEN}============================================================${NC}"
