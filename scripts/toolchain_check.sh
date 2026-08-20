#!/usr/bin/env bash
set -u

echo "======================================================================"
echo "          🔧 SYSTEM & BARE-METAL TOOLCHAIN AUDIT REPORT               "
echo "======================================================================"

check_tool() {
    local cmd="$1"
    local desc="$2"
    if command -v "$cmd" &> /dev/null; then
        local ver
        ver=$($cmd --version 2>&1 | head -n 1)
        printf "%-18s [ \033[32mFOUND\033[0m ] %s\n" "$cmd" "$ver"
    else
        printf "%-18s [\033[31mMISSING\033[0m] %s\n" "$cmd" "$desc"
    fi
}

echo -e "\n--- [1] RUST & LLVM TOOLCHAIN ---"
check_tool "rustc" "Rust Compiler"
check_tool "cargo" "Cargo Package Manager"
check_tool "rust-lld" "LLVM Linker (Rust built-in)"
check_tool "lld" "LLVM Linker (System)"
check_tool "ld.lld" "LLVM LLD Alias"
check_tool "clang" "Clang C/C++ Frontend"
check_tool "llc" "LLVM Static Compiler"
check_tool "llvm-link" "LLVM Bitcode Linker"
check_tool "llvm-objcopy" "LLVM Objcopy Utility"
check_tool "llvm-mc" "LLVM Machine Code Engine"

echo -e "\n--- [2] GNU BINUTILS & C COMPILERS ---"
check_tool "gcc" "GNU C Compiler"
check_tool "ld" "GNU Linker"
check_tool "objdump" "GNU Object Dump"
check_tool "readelf" "ELF Inspection Utility"
check_tool "nm" "Symbol Table Dumper"
check_tool "as" "GNU Assembler"

echo -e "\n--- [3] EMULATION & RUNTIME ---"
check_tool "qemu-system-x86_64" "QEMU x86_64 Hypervisor / Emulator"
check_tool "gdb" "GNU Debugger"

echo -e "\n--- [4] PYTHON ENVIRONMENT ---"
check_tool "python3" "Python 3 System Binary"
if [ -f "./.venv/bin/python" ]; then
    printf "%-18s [ \033[32mFOUND\033[0m ] %s\n" "./.venv/python" "$(./.venv/bin/python --version 2>&1)"
else
    printf "%-18s [\033[33mNOT FOUND\033[0m] Local .venv python\n" "./.venv/python"
fi

echo -e "\n--- [5] TARGET ARTIFACTS & WORKSPACE STATE ---"
for f in "wilc_driver.o" "wilc_driver.bc" "ffi.rs" "wilc_driver.h" "linker.ld" "kernel_entry.c" "kernel_entry.o" "x86_64-baremetal-gemic.json"; do
    if [ -f "$f" ]; then
        printf "%-26s [ \033[32mPRESENT\033[0m ] (%s bytes)\n" "$f" "$(stat -c%s "$f")"
    else
        printf "%-26s [\033[31mMISSING\033[0m]\n" "$f"
    fi
done

echo "======================================================================"
