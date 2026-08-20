#!/usr/bin/env bash
set -euo pipefail

export PATH="${HOME}/.local/bin:${HOME}/.cargo/bin:${HOME}/.rustup/toolchains/*/bin:${PATH}"

echo "============================================================"
echo " 🌐 FULL MACHINE INVENTORY & CAPABILITY RECONNAISSANCE"
echo "============================================================"

# 1. SCAN ALL COMPILERS, ASSEMBLERS, JITs & RUNTIMES ACROSS ENTIRE PATH
echo -e "\n[1] GLOBAL COMPILER, LINKER & RUNTIME EXECUTABLES:"
COMPILERS=(
  "gcc" "g++" "clang" "clang++" "rustc" "cargo" "zig" "qbe" "z3" "cvc5"
  "wasmtime" "wasmer" "node" "deno" "bun" "python3" "pypy3" "ruby" "perl" "go" "ghc"
  "nasm" "yasm" "fasm" "as" "ld" "lld" "mold" "gold"
  "opt" "llc" "lli" "mlir-opt" "llvm-ar" "llvm-nm" "llvm-objdump"
  "bpftool" "perf" "valgrind" "gdb" "lldb" "tree-sitter" "turso" "sqlite3"
)

for bin in "${COMPILERS[@]}"; do
    if command -v "$bin" &>/dev/null; then
        loc=$(command -v "$bin")
        ver=$("$bin" --version 2>&1 | head -n 1 | cut -c1-75 || echo "active")
        echo -e "  [✔] \033[1;32m${bin}\033[0m: ${loc}\n      ↳ ${ver}"
    fi
done

# 2. SCAN ALL SHARED OBJECTS, NATIVE LIBRARIES & CRATES ON HOST
echo -e "\n[2] NATIVE CRATES & BUILT SHARED LIBS IN WORKSPACE & USER DIR:"
find "$HOME" -maxdepth 5 -type f \( -name "Cargo.toml" -o -name "*.so" -o -name "*.a" -o -name "*.dylib" \) \
  -not -path "*/.cache/*" -not -path "*/.rustup/*" -not -path "*/node_modules/*" 2>/dev/null | while read -r item; do
    echo "  ▶ $item"
done

# 3. KERNEL & HARDWARE CAPABILITIES
echo -e "\n[3] KERNEL, EBPF & CPU HARDWARE MANIFOLD:"
echo "  ▶ Linux Kernel: $(uname -r) ($(uname -m))"
echo -e "  ▶ eBPF / JIT Kernel Status:"
sysctl net.core.bpf_jit_enable 2>/dev/null || echo "    (bpf_jit active)"
echo -n "  ▶ Vector Extensions (SIMD): "
grep -m1 'flags' /proc/cpuinfo | tr ' ' '\n' | grep -E 'avx|sse|fma|bmi|aes' | sort -u | tr '\n' ' '
echo -e "\n"

# 4. INSTALLED PYTHON PACKAGES (AI, SMT, COMPILERS)
echo "[4] PYTHON NATIVE BRIDGES & SMT INTERFACES:"
python3 -c "
import sys
pkgs = ['z3', 'ctypes', 'cffi', 'pyo3', 'llvmlite', 'torch', 'numpy', 'pytest', 'tree_sitter']
for p in pkgs:
    try:
        mod = __import__(p)
        print(f'  [✔] Python Package: {p} (v{getattr(mod, \"__version__\", \"installed\")})')
    except ImportError:
        pass
"

echo "============================================================"
echo " [✨] FULL SYSTEM SCAN COMPLETE"
echo "============================================================"
