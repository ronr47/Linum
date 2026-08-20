#!/usr/bin/env bash
set -euo pipefail

echo "============================================================"
echo "          LINUM: RESTORING & ALIGNING CLEAN STATE           "
echo "============================================================"

# 1. Restore pristine baseline from initial snapshot
if [ -d "/tmp/linum-src-snapshot/src" ]; then
    echo "[1/5] Restoring pristine source snapshot..."
    cp -a /tmp/linum-src-snapshot/src/* src/linum/
fi

# Purge build artifacts & temporary files
rm -rf build/linum-compiler dist/linum-compiler *.egg-info .pytest_cache/
find . -maxdepth 1 \( -name '*.broken' -o -name '*.bak*' \) -delete 2>/dev/null || true
find src/linum/ \( -name '*.broken' -o -name '*.bak*' \) -delete 2>/dev/null || true

# 2. Safely rewrite only import statements using Python AST / regex
echo "[2/5] Performing exact import normalization..."
python - <<'PY'
import re
from pathlib import Path

def clean_file(path: Path):
    text = path.read_text(encoding="utf-8")
    
    # 1. Convert 'from linum.src...' to 'from linum...'
    text = re.sub(r'\bfrom\s+linum\.src\b', 'from linum', text)
    text = re.sub(r'\bimport\s+linum\.src\b', 'import linum', text)
    
    # 2. Convert 'from src...' to 'from linum...'
    text = re.sub(r'\bfrom\s+src\b', 'from linum', text)
    text = re.sub(r'\bimport\s+src\b', 'import linum', text)
    
    # 3. Ensure Type is explicitly present in compiler.py
    if path.name == "compiler.py":
        if "from linum.semantic.types import" in text and "Type," not in text:
            text = text.replace(
                "from linum.semantic.types import (",
                "from linum.semantic.types import (\n    Type,"
            )
            
    path.write_text(text, encoding="utf-8")

for p in Path("src/linum").rglob("*.py"):
    clean_file(p)

for p in Path("tests").rglob("*.py"):
    clean_file(p)

for p in Path(".").glob("*.py"):
    clean_file(p)
PY

# 3. Reinstall package in editable mode
echo "[3/5] Installing linum package..."
python -m pip install -e . --no-deps --quiet

# 4. Verify compiler CLI directly
echo "[4/5] Testing compilation targets..."
linum test_main.linum --emit llvm -o /tmp/main.ll
linum test_complex.linum --emit asm -o /tmp/complex.s

# 5. Execute full test suite
echo "[5/5] Running pytest..."
python -m pytest -q

echo "============================================================"
echo "                 SUCCESS: 100% SUITE PASSING                "
echo "============================================================"
