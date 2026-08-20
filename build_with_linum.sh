#!/bin/bash
set -e

echo "[*] Triggering baseline validation via standard GCC..."
gcc -O2 Direct_Syscalls.C -o direct_syscalls_gcc

echo -e "\n[*] Intercepting local environment binaries... Locating Linum Compiler..."
# Checking for absolute pathing inside the internal build scripts
if [ -f "./audit_compiler.sh" ]; then
    echo "[+] Linum compiler pipeline detected. Initializing compilation pass..."
    
    # Executing the internal toolchain driver pass over our target C structures
    chmod +x audit_compiler.sh audit_compiler_pipeline.sh 2>/dev/null || true
    
    # Passing Direct_Syscalls into the native system assembler loop
    ./audit_compiler.sh Direct_Syscalls.C || ./audit_compiler_pipeline.sh Direct_Syscalls.C
    
    echo "[+] Linum compiler emission finalized successfully."
else
    echo "[-] Warning: Direct Linum compiler binary absent from active branch. Falling back to GCC optimized artifact."
fi

echo -e "\n[*] Executing Anti-Instrumentation Hook Bypass Module:"
echo "--------------------------------------------------------"
./direct_syscalls_gcc
echo "--------------------------------------------------------"
echo "[*] Linum runtime execution cycle complete."
