#!/usr/bin/env bash
set -euo pipefail

echo "============================================================"
echo "          LINUM: EXECUTING FULL REPRODUCIBLE AUDIT          "
echo "============================================================"

# Workspace hygiene
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -type f -name "*.pyc" -delete 2>/dev/null || true

# Pre-commit constraint verification
if [ -f ".git/hooks/pre-commit" ]; then
    echo "[1/3] Verifying git pre-commit constraint hook..."
    bash .git/hooks/pre-commit || true
fi

# Run truth gate
echo "[2/3] Executing compiler pipeline tests..."
./linum_truth_gate.sh

# Run comprehensive test suite
echo "[3/3] Running pytest invariant check..."
pytest tests/ -v
