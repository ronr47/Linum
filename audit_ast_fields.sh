#!/usr/bin/env bash
set -e

PY_BIN="$( [ -f "./.venv/bin/python" ] && echo "./.venv/bin/python" || echo "$(which python3)" )"

$PY_BIN - <<'PY_EOF'
import ast
from pathlib import Path

ast_file = Path("src/ast/nodes.py")
tree = ast.parse(ast_file.read_text())

print(f"{'='*25} AST NODE FIELD MAPPINGS {'='*25}")
for node in tree.body:
    if isinstance(node, ast.ClassDef):
        fields = []
        for item in node.body:
            if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                fields.append(item.target.id)
            elif isinstance(item, ast.FunctionDef) and item.name == "__init__":
                init_args = [arg.arg for arg in item.args.args if arg.arg != "self"]
                print(f"Class {node.name} (__init__): {init_args}")
        if fields:
            print(f"Class {node.name} (dataclass): {fields}")
PY_EOF
