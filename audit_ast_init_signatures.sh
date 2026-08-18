#!/usr/bin/env bash
set -e

PY_BIN="$( [ -f "./.venv/bin/python" ] && echo "./.venv/bin/python" || echo "$(which python3)" )"

$PY_BIN - <<'PY_EOF'
import ast
from pathlib import Path

tree = ast.parse(Path("src/ast/nodes.py").read_text())

print("=== AST Node Constructor Signatures (Static AST) ===")
for node in tree.body:
    if isinstance(node, ast.ClassDef):
        # Look for __init__ method
        init_func = None
        for item in node.body:
            if isinstance(item, ast.FunctionDef) and item.name == "__init__":
                init_func = item
                break
        
        if init_func:
            args = []
            for a in init_func.args.args:
                args.append(a.arg)
            # check defaults
            defaults = [None] * (len(args) - len(init_func.args.defaults)) + [d for d in init_func.args.defaults]
            sig_parts = []
            for a, d in zip(args, defaults):
                if a == "self":
                    continue
                if d is not None:
                    sig_parts.append(f"{a}=...")
                else:
                    sig_parts.append(a)
            print(f"{node.name}({', '.join(sig_parts)})")
        else:
            # Dataclass fields or inherited
            fields = []
            for item in node.body:
                if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                    fields.append(item.target.id)
            if fields:
                print(f"{node.name}[dataclass]({', '.join(fields)})")
            else:
                print(f"{node.name}()")
PY_EOF
