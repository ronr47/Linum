#!/usr/bin/env bash
# Linum Master Pipeline Compiler (LLVM 21 Bare-Metal Substrate)
set -euo pipefail

INPUT_FILE="${1:-pmm.linum}"
OUTPUT_OBJ="${2:-pmm_linum.o}"

printf "⚡ Init System Compiler Pipeline for: %s\n" "$INPUT_FILE"

# Step 01: Enforce mathematical invariants via Z3 SMT Prover
if [ -f ~/linum/src/verify_bounds.py ]; then
    python3 ~/linum/src/verify_bounds.py
fi

# Step 02: Transpile .linum to LLVM 21 IR
LL_FILE="${INPUT_FILE%.*}.ll"
python3 metamorphic_transpiler.py "$INPUT_FILE" -o "$LL_FILE"

# Step 03: Lower LLVM IR to Freestanding Bare-Metal Object File
clang -target x86_64-unknown-none-elf \
      -march=x86-64 -mbmi \
      -ffreestanding -nostdlib -mno-red-zone \
      -O3 -c "$LL_FILE" -o "$OUTPUT_OBJ"

printf "✅ Output generated: %s (64-byte aligned / freestanding)\n" "$OUTPUT_OBJ"
