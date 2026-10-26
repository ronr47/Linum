#!/usr/bin/env python3
"""Stage 0 R2 Compiler CLI: Ingestion, AST extraction, and contract validation."""

import sys
from pathlib import Path

# Ensure repository root is on sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
from src.frontend.lexer import Lexer
from src.frontend.parser import Parser


def inspect_source(file_path: Path):
    if not file_path.exists():
        print(f"[-] Error: Source file {file_path} not found.")
        sys.exit(1)

    with open(file_path, "r", encoding="utf-8") as f:
        src = f.read()

    tokens = Lexer(src).tokenize()
    parser = Parser(tokens)
    mod = parser.parse_module()

    print(f"=== R2 Module: {mod.name} ===")
    print(f"Total Declarations: {len(mod.declarations)}")

    for decl in mod.declarations:
        if hasattr(decl, "name") and hasattr(decl, "contracts"):
            contracts_str = ", ".join(f"[{c.kind}: {c.expr}]" for c in decl.contracts) if decl.contracts else "None"
            params_str = ", ".join(f"{p[0]}: {p[1].domain or ''} {p[1].name}" for p in decl.params)
            print(f"  fn {decl.name}({params_str}) -> Contracts: {contracts_str}")
        elif hasattr(decl, "name") and hasattr(decl, "fields"):
            print(f"  struct {decl.name} ({len(decl.fields)} fields)")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: r2c_stage0.py <path/to/source.r2>")
        sys.exit(1)
    inspect_source(Path(sys.argv[1]))
