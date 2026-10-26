#!/usr/bin/env python3
"""Unified R2 Compiler Driver (r2c)."""

import argparse
import sys
from pathlib import Path

# Repository root anchoring
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.frontend.lexer import Lexer
from src.frontend.parser import Parser
from src.semantic.analyzer import SemanticAnalyzer
from src.lowering.lowerer import Lowerer
from src.lowering.printer import format_ir_module

def compile_source(source_path: Path, args: argparse.Namespace) -> int:
    if not source_path.exists():
        print(f"[-] Error: file '{source_path}' does not exist.", file=sys.stderr)
        return 1

    source_text = source_path.read_text(encoding="utf-8")

    # Stage 0: Lexing & Parsing
    tokens = Lexer(source_text).tokenize()
    if args.dump_tokens:
        for t in tokens:
            print(f"  {t.type.name:<16} {t.value!r}")
        return 0

    parser = Parser(tokens)
    module_ast = parser.parse_module()
    if args.dump_ast:
        for decl in module_ast.declarations:
            print(decl)
        return 0

    # Stage 1: Semantic Analysis
    analyzer = SemanticAnalyzer()
    analyzer.analyze_module(module_ast)
    if args.check:
        print(f"[OK] Semantic verification passed: {source_path}")
        return 0

    # Stage 2: Lowering to R2-IR
    lowerer = Lowerer()
    ir_module = lowerer.lower_module(module_ast)

    if args.emit_ir or not args.output:
        print(format_ir_module(ir_module))
        return 0

    if args.output:
        out_path = Path(args.output)
        out_path.write_text(format_ir_module(ir_module), encoding="utf-8")
        print(f"[OK] IR written to {out_path}")

    return 0

def main() -> None:
    ap = argparse.ArgumentParser(description="R2 Compiler Driver (r2c)")
    ap.add_argument("source", type=Path, help="Path to .r2 source file")
    ap.add_argument("--dump-tokens", action="store_true", help="Print lexer token stream and exit")
    ap.add_argument("--dump-ast", action="store_true", help="Print parsed AST declarations and exit")
    ap.add_argument("--check", action="store_true", help="Run semantic checks without lowering")
    ap.add_argument("--emit-ir", action="store_true", help="Emit linear R2-IR to stdout")
    ap.add_argument("-o", "--output", type=str, help="Output destination file")

    args = ap.parse_args()
    try:
        sys.exit(compile_source(args.source, args))
    except Exception as e:
        print(f"[-] Compilation error: {e}", file=sys.stderr)
        sys.exit(2)

if __name__ == "__main__":
    main()
