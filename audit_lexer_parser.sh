#!/usr/bin/env bash
set -e

PY_BIN="$( [ -f "./.venv/bin/python" ] && echo "./.venv/bin/python" || echo "$(which python3)" )"

$PY_BIN - <<'PY_EOF'
from pathlib import Path

print("=== src/frontend/lexer.py ===")
print(Path("src/frontend/lexer.py").read_text())

print("\n=== src/frontend/parser.py ===")
print(Path("src/frontend/parser.py").read_text())
PY_EOF
