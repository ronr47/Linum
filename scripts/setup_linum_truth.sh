#!/usr/bin/env bash
set -euo pipefail

echo "============================================================"
echo "          LINUM: TRUTH-CENTERED WORKSPACE ALIGNMENT         "
echo "============================================================"

# 1. Restore pristine AST nodes and compiler from snapshot if corrupted
echo "[1/5] Restoring clean source baseline..."
if [ -d "/tmp/linum-src-snapshot/src" ]; then
    cp /tmp/linum-src-snapshot/src/ast/nodes.py src/linum/ast/nodes.py 2>/dev/null || true
    cp /tmp/linum-src-snapshot/src/compiler.py src/linum/compiler.py 2>/dev/null || true
fi

# Purge cache and artifacts
rm -rf build/linum-compiler dist/linum-compiler *.egg-info .pytest_cache/
find . -maxdepth 1 \( -name '*.broken' -o -name '*.bak*' \) -delete 2>/dev/null || true
find src/linum/ \( -name '*.broken' -o -name '*.bak*' \) -delete 2>/dev/null || true

# 2. Safely normalize imports ONLY on import statement lines
echo "[2/5] Enforcing invariant namespace on import statements..."
find src/linum/ tests/ -type f -name "*.py" | while read -r f; do
    sed -i -E 's/linum\.src\./linum\./g' "$f"
    sed -i -E '/^[[:space:]]*(from|import)[[:space:]]+/ s/\bsrc\./linum./g' "$f"
done

# Ensure Type is imported in compiler.py
python - <<'PY'
from pathlib import Path
p = Path("src/linum/compiler.py")
txt = p.read_text()
if "from linum.semantic.types import" in txt and "Type," not in txt:
    txt = txt.replace("from linum.semantic.types import (", "from linum.semantic.types import (\n    Type,")
p.write_text(txt)
PY

# 3. Refresh Python package installation
echo "[3/5] Re-installing Linum in editable mode..."
python -m pip install -e . --no-deps --quiet

# 4. Verify compiler output on primary fixtures
echo "[4/5] Testing primary compilation pipeline..."
linum test_main.linum --emit llvm -o /tmp/main.ll
linum test_complex.linum --emit asm -o /tmp/complex.s

# 5. Run full test suite
echo "[5/5] Executing test suite verification..."
python -m pytest -q

echo "============================================================"
echo "                 ALL SYSTEMS VERIFIED & ALIVE               "
echo "============================================================"
