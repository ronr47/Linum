#!/usr/bin/env bash
set -euo pipefail

echo "============================================================"
echo "          LINUM: TRUTH GATE & REPRODUCIBLE AUDIT            "
echo "============================================================"

# 1. Hygiene & Artifact Purge
echo "[1/4] Enforcing workspace hygiene..."
rm -rf build/linum-compiler dist/linum-compiler *.egg-info .pytest_cache/
find . -maxdepth 1 \( -name '*.broken' -o -name '*.bak*' \) -delete 2>/dev/null || true
find src/linum/ \( -name '*.broken' -o -name '*.bak*' \) -delete 2>/dev/null || true

# 2. Package Installation Invariant
echo "[2/4] Verifying editable installation..."
python -m pip install -e . --no-deps --quiet

# 3. Direct Binary Compilation Checks
echo "[3/4] Testing CLI direct emission (LLVM & ASM)..."
linum test_main.linum --emit llvm -o /tmp/main.ll
linum test_complex.linum --emit asm -o /tmp/complex.s

# 4. Full Pytest Suite Verification
echo "[4/4] Executing invariant test suites..."
python -m pytest -q

echo "============================================================"
echo "      VERIFIED: ZERO DRIFT, ZERO LEAKS, 100% PASSING        "
echo "============================================================"
