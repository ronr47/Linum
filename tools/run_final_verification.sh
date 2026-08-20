#!/usr/bin/env bash
set -euo pipefail

cd /home/ron/linum

echo "============================================================"
echo " 🛡️ RUNNING COMPREHENSIVE LINUM TRUTH GATE VERIFICATION"
echo "============================================================"

./linum_truth_gate.sh

echo ""
echo "============================================================"
echo " 🧪 RUNNING ALL EMISSION TARGET BENCHMARKS"
echo "============================================================"

# Test LLVM IR
linum test_main.linum --emit llvm -o /tmp/test_main.ll
echo "[✔] LLVM IR Emission: OK"

# Test Assembly
linum test_main.linum --emit asm -o /tmp/test_main.s
echo "[✔] Assembly Emission: OK"

# Test BPF
linum test_main.linum --emit bpf -o /tmp/test_main_bpf.o
echo "[✔] BPF Object Emission: OK"

# Test Object file emission (System Backend)
linum test_main.linum --emit obj -o /tmp/test_main.o
echo "[✔] Native Object Emission: OK"

# Clean temporary artifacts
rm -f /tmp/test_main.* /tmp/test_main_bpf.o

echo ""
echo "============================================================"
echo " [✨] ALL 4 EMISSION TARGETS VERIFIED & OPERATIONAL"
echo "============================================================"
