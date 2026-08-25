#!/usr/bin/env bash
set -e

echo "=== [1/2] Compiling Linum Multi-Target Compiler Core ==="
rustc linum_unified/src/compiler_core.rs -o linum_unified/linum_core_bin

echo "=== [2/2] Running Multi-Target Emission Verification ==="
./linum_unified/linum_core_bin

echo "========================================================="
echo " LINUM UNIFIED MULTI-TARGET PIPELINE VERIFIED SUCCESSFULLY"
echo "========================================================="
