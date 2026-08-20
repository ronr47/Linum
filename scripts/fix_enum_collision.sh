#!/usr/bin/env bash
set -e

PY_BIN="$( [ -f "./.venv/bin/python" ] && echo "./.venv/bin/python" || echo "$(which python3)" )"
export PYTHONPATH=".:$PYTHONPATH"

$PY_BIN - <<'PY_EOF'
from pathlib import Path
import re

lexer_path = Path("src/frontend/lexer.py")
content = lexer_path.read_text()

# Replace any explicit string assignments for PLUS/MINUS in TokenType with auto()
content = re.sub(r'PLUS\s*=\s*["\']\+["\']', 'PLUS = auto()', content)
content = re.sub(r'MINUS\s*=\s*["\']\-["\']', 'MINUS = auto()', content)

# If PLUS/MINUS were not present in TokenType, ensure they are inserted using auto()
if "PLUS = auto()" not in content and "class TokenType(Enum):" in content:
    content = content.replace(
        "class TokenType(Enum):",
        "class TokenType(Enum):\n    PLUS = auto()\n    MINUS = auto()"
    )

lexer_path.write_text(content)
print("  [+] Fixed TokenType enum definition in src/frontend/lexer.py")
PY_EOF

echo "=== Retrying verify_commits_1_2.sh ==="
./verify_commits_1_2.sh
