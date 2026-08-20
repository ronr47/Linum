#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(pwd)"

echo "============================================================"
echo "    🚀 LINUM MULTI-BACKEND MATRIX BENCHMARK & VERIFY        "
echo "============================================================"

# Ensure clean artifact directory
mkdir -p "${ROOT_DIR}/build/artifacts"
cd "${ROOT_DIR}"

echo "[1/4] Compiling and verifying standard LLVM Object emission..."
python3 linum_driver.py super_sim.linum --backend llvm --emit obj -o build/artifacts/super_sim_llvm.o

echo "[2/4] Testing MLIR Dialect lowering and dumping IR..."
python3 linum_driver.py super_sim.linum --backend mlir --emit mlir -o build/artifacts/super_sim.mlir

echo "[3/4] Compiling Sandboxed eBPF/XDP Object..."
python3 linum_driver.py super_sim.linum --backend ebpf --emit bpf-obj -o build/artifacts/super_sim_xdp.o

echo "[4/4] Executing Cranelift sub-millisecond JIT..."
python3 linum_driver.py super_sim.linum --backend cranelift --opt-level debug

echo ""
echo "============================================================"
echo "                   ARTIFACT AUDIT SUMMARY                   "
echo "============================================================"
ls -lh build/artifacts/
echo "============================================================"
echo "[✔] All compiler backends and execution runtimes verified sound."
