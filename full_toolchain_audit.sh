#!/usr/bin/env bash
set -euo pipefail

cd /home/ron/linum

echo "============================================================"
echo " 🛠️  1. COMPILER, ASSEMBLER & TOOLCHAIN VERSIONS"
echo "============================================================"
gcc --version | head -n 1
nasm -v || echo "nasm: not installed"
ld --version | head -n 1
rustc --version || echo "rustc: not installed"
cargo --version || echo "cargo: not installed"
python3 --version
qemu-system-x86_64 --version | head -n 1

echo -e "\n============================================================"
echo " 🔨 2. BUILDING MISSING ARTIFACTS"
echo "============================================================"
if [[ ! -f "kernel64.elf" || ! -f "os_unified_disk.bin" ]]; then
    echo "[*] Triggering build_and_run_64.sh..."
    /home/ron/linum/build_and_run_64.sh
else
    echo "[✔] All required binaries already present."
fi

echo -e "\n============================================================"
echo " 📦 3. BINARY ARTIFACTS & SIZES"
echo "============================================================"
ls -lh boot64.bin kernel64.bin kernel64.elf os_unified_disk.bin 2>/dev/null || true

echo -e "\n============================================================"
echo " 🔍 4. ELF ENTRY POINT & SECTION HEADERS"
echo "============================================================"
readelf -h kernel64.elf | grep -E "Entry point|Type|Machine"
readelf -l kernel64.elf | grep -E "LOAD|Entry"

echo -e "\n============================================================"
echo " ⚡ 5. QEMU LIVE FIBER EXECUTION"
echo "============================================================"
python3 /home/ron/linum/capture_fiber_run.py
