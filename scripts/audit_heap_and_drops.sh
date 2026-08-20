#!/usr/bin/env bash
set -e

PY_BIN="$( [ -f "./.venv/bin/python" ] && echo "./.venv/bin/python" || echo "$(which python3)" )"

$PY_BIN - <<'PY_EOF'
import ast
from pathlib import Path

def print_section(title):
    print(f"\n{'='*25} {title} {'='*25}")

# 1. Audit Semantic Ownership Modes & Types
print_section("1. SEMANTIC TYPES & OWNERSHIP (src/linum/semantic/types.py)")
types_file = Path("src/linum/semantic/types.py")
if types_file.exists():
    tree = ast.parse(types_file.read_text())
    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            print(f"[Class] {node.name}")
            for item in node.body:
                if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                    print(f"  Field: {item.target.id}")
                elif isinstance(item, ast.Assign):
                    for target in item.targets:
                        if isinstance(target, ast.Name):
                            print(f"  Constant/Assign: {target.id}")

# 2. Audit AST Statements/Expressions for Alloc/Free
print_section("2. AST NODES (src/linum/ast/nodes.py)")
ast_file = Path("src/linum/ast/nodes.py")
if ast_file.exists():
    tree = ast.parse(ast_file.read_text())
    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            print(f"[AST Class] {node.name}")

# 3. Audit CFG Instruction classes related to Drop/Call/Alloc
print_section("3. CFG INSTRUCTIONS (src/linum/lowering/cfg.py)")
cfg_file = Path("src/linum/lowering/cfg.py")
if cfg_file.exists():
    tree = ast.parse(cfg_file.read_text())
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and (node.name.startswith("Ir") or "Analyzer" in node.name or "Verifier" in node.name):
            fields = []
            for item in node.body:
                if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                    fields.append(item.target.id)
            print(f"[CFG Class] {node.name} -> fields: {fields}")

# 4. Audit Existing External Declarations in LLVM Emitter
print_section("4. LLVM EMITTER RUNTIME CALLS (src/linum/lowering/llvm.py)")
llvm_file = Path("src/linum/lowering/llvm.py")
if llvm_file.exists():
    content = llvm_file.read_text()
    for kw in ["declare", "malloc", "free", "__drop_linear_resource", "IrDrop", "IrCall"]:
        count = content.count(kw)
        print(f"Occurrences of '{kw}': {count}")

print_section("AUDIT COMPLETE")
PY_EOF
