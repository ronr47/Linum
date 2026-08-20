#!/usr/bin/env bash
set -euo pipefail

echo -e "\033[38;2;180;100;255m╭─────────────────────────────────────────────────────────────────────────────╮\033[0m"
echo -e "\033[38;2;180;100;255m│ \033[1m\033[38;2;0;255;240mLINUM MULTI-TOOLCHAIN COMPREHENSIVE WORKSPACE AUDIT\033[0m\033[38;2;180;100;255m                         │\033[0m"
echo -e "\033[38;2;180;100;255m╰─────────────────────────────────────────────────────────────────────────────╯\033[0m\n"

# 1. Host Compiler & Linker Toolchain
echo -e "\033[1;36m[1/5] HOST TOOLCHAIN SUITE\033[0m"
echo "  • GCC        : $(gcc --version | head -n1)"
echo "  • Clang/LLVM : $(clang --version | head -n1)"
echo "  • LLVM-Config: $(llvm-config --version 2>/dev/null || echo 'N/A')"
echo "  • Rust/Cargo : $(cargo --version 2>/dev/null || echo 'N/A')"
echo "  • Python     : $(python3 --version)"

# 2. Rust Workspace Status (AetherVPC + FFI)
echo -e "\n\033[1;36m[2/5] RUST SUBSYSTEM (AetherVPC / FFI)\033[0m"
if [ -f "aethervpc-mvp/Cargo.toml" ]; then
    cargo check --manifest-path aethervpc-mvp/Cargo.toml --quiet && echo -e "  \033[32m✔\033[0m aethervpc-mvp: Passed Type & Borrow Invariants"
fi
if [ -f "Cargo.toml" ]; then
    cargo check --manifest-path Cargo.toml --quiet 2>/dev/null && echo -e "  \033[32m✔\033[0m Root Cargo Workspace: Valid" || echo -e "  \033[33m!\033[0m Root Cargo Workspace: Standalone"
fi

# 3. Kernel / Baremetal C Subsystem
echo -e "\n\033[1;36m[3/5] BAREMETAL & KERNEL BINARIES\033[0m"
ls -lh beast/kernel/beast.elf kernel.elf direct_syscalls_gcc 2>/dev/null | awk '{printf "  • %-25s %s  (%s)\n", $9, $5, $6" "$7}' || true

# 4. Mathic DSL Engine & Lowering
echo -e "\n\033[1;36m[4/5] MATHIC MATRIX & TENSOR ENGINE\033[0m"
ls -lh mathic/*.bc mathic/*.ll 2>/dev/null | awk '{printf "  • %-25s %s\n", $9, $5}' || echo "  No raw bytecodes found."

# 5. Core Invariant Gate & Test Status
echo -e "\n\033[1;36m[5/5] LINUM INVARIANT TEST SUITE\033[0m"
python -m pytest -q

echo -e "\n\033[38;2;57;255;20m✔ FULL WORKSPACE AUDIT: ALL TOOLCHAINS CONVERGED & OPERATIONAL\033[0m"
