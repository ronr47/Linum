#!/usr/bin/env bash
set -euo pipefail

echo "=================================================="
echo "Inspecting src/linum/cli.py (extension checks):"
echo "=================================================="
grep -n -C 5 -E "(\.linum|extension|suffix|fallback|clang)" src/linum/cli.py || true

echo ""
echo "=================================================="
echo "Inspecting src/linum/driver.py (extension checks):"
echo "=================================================="
grep -n -C 5 -E "(\.linum|extension|suffix|fallback|clang)" src/linum/driver.py || true

echo ""
echo "=================================================="
echo "Inspecting linum_truth_gate.sh (step 3/4):"
echo "=================================================="
grep -n -C 10 "Testing CLI direct emission" linum_truth_gate.sh || true
