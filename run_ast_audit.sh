#!/usr/bin/env bash
set -e

PY_BIN="$( [ -f "./.venv/bin/python" ] && echo "./.venv/bin/python" || echo "$(which python3)" )"

$PY_BIN - <<'PY_EOF'
import ast
from pathlib import Path

def inspect_file_ast(file_path: Path):
    print(f"\n{'='*25} AUDITING {file_path} {'='*25}")
    if not file_path.exists():
        print(f"File not found: {file_path}")
        return

    content = file_path.read_text()
    tree = ast.parse(content)

    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            print(f"\n[Class] {node.name}")
            # Find class-level annotated fields (dataclasses)
            fields = []
            for item in node.body:
                if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                    fields.append(item.target.id)
                elif isinstance(item, ast.FunctionDef) and item.name == "__init__":
                    init_args = [arg.arg for arg in item.args.args if arg.arg != "self"]
                    print(f"  __init__ args: {init_args}")
            if fields:
                print(f"  Dataclass fields: {fields}")

# 1. Audit SSA classes
inspect_file_ast(Path("src/lowering/ssa.py"))

# 2. Audit CFG classes
inspect_file_ast(Path("src/lowering/cfg.py"))

# 3. Print the exact SsaPhi definition from ssa.py
print(f"\n{'='*25} EXACT SsaPhi DEFINITION {'='*25}")
ssa_lines = Path("src/lowering/ssa.py").read_text().splitlines()
in_phi = False
for line in ssa_lines:
    if "class SsaPhi" in line:
        in_phi = True
    if in_phi:
        print(line)
        if line.strip() and not line.startswith(" ") and not line.startswith("class SsaPhi") and not line.startswith("@"):
            break
        if line.strip() == "" and in_phi:
            # check if next lines are still part of class
            pass
PY_EOF
