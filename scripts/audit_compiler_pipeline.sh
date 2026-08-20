#!/usr/bin/env bash
set -e

PY_BIN="$( [ -f "./.venv/bin/python" ] && echo "./.venv/bin/python" || echo "$(which python3)" )"

$PY_BIN - <<'PY_EOF'
from pathlib import Path

compiler_file = Path("src/compiler.py")
print("================== src/compiler.py Content Audit ==================")
if compiler_file.exists():
    print(compiler_file.read_text())
else:
    print("src/compiler.py not found.")
PY_EOF
