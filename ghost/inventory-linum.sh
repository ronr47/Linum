#!/usr/bin/env bash
set -euo pipefail

ROOT="/home/ron/linum"
cd "$ROOT"

echo "============================================================"
echo " LINUM NATIVE TOOLCHAIN / ENGINE INVENTORY"
echo "============================================================"

echo
echo "▶ ROOT"
pwd

echo
echo "▶ TOP-LEVEL DIRECTORIES"
find . -maxdepth 2 -type d \
    -not -path './.git*' \
    -not -path './target*' \
    -not -path './ghost*' \
    | sort

echo
echo "▶ LLVM / CLANG DISCOVERY"
find "$ROOT" "$HOME/.local" "$HOME/.cargo" \
    -type f \( \
        -name 'clang' -o \
        -name 'clang++' -o \
        -name 'llvm-*' -o \
        -name 'llc' -o \
        -name 'opt' -o \
        -name 'lld' \
    \) 2>/dev/null | sort -u

echo
echo "▶ RUST / CRANELIFT / LINUM CRATES"
find "$ROOT" -type f \
    \( -name 'Cargo.toml' -o -name 'Cargo.lock' \) \
    -not -path '*/target/*' \
    -print | sort

echo
echo "▶ LINUM-NAMED ARTIFACTS"
find "$ROOT" -type f \
    \( -iname '*linum*' -o \
       -iname '*cranelift*' -o \
       -iname '*ebpf*' -o \
       -iname '*llvm*' -o \
       -iname '*jit*' \
    \) \
    -not -path '*/.git/*' \
    -not -path '*/target/*' \
    | sort | head -500

echo
echo "▶ RELEASE BINARIES"
find "$ROOT/target" -type f -executable 2>/dev/null |
    sort | head -300

echo
echo "▶ LLVM VERSION INFORMATION"

for c in clang clang-21 clang-20 clang-19 llc opt llvm-config; do
    if command -v "$c" >/dev/null 2>&1; then
        echo
        echo "[$c]"
        command -v "$c"
        "$c" --version 2>&1 | head -3 || true
    fi
done

echo
echo "▶ RUST CRANELIFT REFERENCES"

grep -RInE \
    'cranelift|linum_cranelift|llvm|ebpf|jit' \
    Cargo.toml \
    */Cargo.toml \
    */*/Cargo.toml \
    2>/dev/null | head -300 || true

echo
echo "▶ ENVIRONMENT OVERRIDES"

env | grep -Ei \
    'PATH|LLVM|CLANG|CRANELIFT|LINUM|RUSTFLAGS|CC|CXX|LD' \
    | sort || true

echo
echo "============================================================"
echo " INVENTORY COMPLETE"
echo "============================================================"
