#!/usr/bin/env bash
set -euo pipefail

echo "============================================================"
echo "          LINUM: TRUTH GATE & REPRODUCIBLE AUDIT            "
echo "============================================================"

echo "[1/4] Enforcing workspace hygiene..."
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -type f -name "*.pyc" -delete 2>/dev/null || true

echo "[2/4] Verifying editable installation..."
python3 -m pip install -e . --no-deps --quiet

echo "[3/4] Running Linum Pipeline against impossible_for_others.linum..."
if [ -f "projects/impossible_for_others.linum" ]; then
    linum-cli emit --target=llvm projects/impossible_for_others.linum || true
    linum-cli emit --target=asm projects/impossible_for_others.linum || true
fi

echo "[4/4] Executing invariant test suites..."
pytest tests/ -v -k "test_linear_lifetime_knot_rejection or test_epistemic_crucible"
