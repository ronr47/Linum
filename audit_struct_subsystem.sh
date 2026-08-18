#!/usr/bin/env bash
set -e

PY_BIN="$( [ -f "./.venv/bin/python" ] && echo "./.venv/bin/python" || echo "$(which python3)" )"

$PY_BIN - <<'PY_EOF'
import ast
from pathlib import Path

def print_section(title):
    print(f"\n{'='*25} {title} {'='*25}")

# 1. Inspect AST for Struct Declarations and Field Access Nodes
print_section("1. AST NODES FOR STRUCTS (src/ast/nodes.py)")
ast_path = Path("src/ast/nodes.py")
if ast_path.exists():
    tree = ast.parse(ast_path.read_text())
    struct_nodes = [n.name for n in tree.body if isinstance(n, ast.ClassDef) and any(k in n.name.lower() for k in ["struct", "field", "member", "record", "access"])]
    print("Struct-related AST classes found:", struct_nodes if struct_nodes else "None (Ready for implementation)")

# 2. Inspect Semantic Types for Aggregate / Struct Types
print_section("2. SEMANTIC TYPE DEFINITIONS (src/semantic/types.py)")
types_path = Path("src/semantic/types.py")
if types_path.exists():
    tree = ast.parse(types_path.read_text())
    type_classes = [n.name for n in tree.body if isinstance(n, ast.ClassDef)]
    print("Semantic type classes found:", type_classes)

# 3. Inspect CFG Instruction set for Field Offset / Aggregates
print_section("3. CFG INSTRUCTIONS (src/lowering/cfg.py)")
cfg_path = Path("src/lowering/cfg.py")
if cfg_path.exists():
    tree = ast.parse(cfg_path.read_text())
    ir_classes = [n.name for n in tree.body if isinstance(n, ast.ClassDef) and n.name.startswith("Ir")]
    print("Available IR instructions:", ir_classes)

print_section("AUDIT COMPLETE")
PY_EOF
