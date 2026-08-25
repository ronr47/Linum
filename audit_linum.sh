#!/bin/bash
echo "===================================================="
echo "LINUM WORKSPACE AUDIT: DISCOVERING EXECUTION FILES"
echo "===================================================="

echo "[*] Scanning for executable files and binaries..."
find . -maxdepth 3 -type f -executable -not -path '*/.*' -not -path './*sh'

echo "[*] Scanning for LLVM IR (.ll) and Bitcode (.bc) files..."
find . -maxdepth 3 -type f \( -name "*.ll" -o -name "*.bc" \)

echo "[*] Scanning for compiled object files (.o)..."
find . -maxdepth 3 -type f -name "*.o"

echo "[*] Scanning for source components and scripts..."
find . -maxdepth 3 -type f \( -name "*.c" -o -name "*.s" -o -name "*.sh" \)

echo "===================================================="
echo "AUDIT COMPLETE. Awaiting further direction, Master."
echo "===================================================="
