import argparse
import sys
import os
from pathlib import Path
from typing import List, Optional

from linum.src.compiler import compile_source
from linum.src.lowering.llvm import SystemBackendLinker
from linum.src.diagnostics import DiagnosticError

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="linum",
        description="Linum Programming Language Compiler Driver"
    )
    parser.add_argument(
        "input",
        nargs="?",
        help="Input Linum source file (.linum)"
    )
    parser.add_argument(
        "-o", "--output",
        help="Output target file path (defaults to stdout for text, or <input>.<ext>)"
    )
    parser.add_argument(
        "--emit",
        choices=["llvm", "asm", "obj"],
        default="llvm",
        help="Target compilation artifact: 'llvm' (LLVM IR), 'asm' (assembly), or 'obj' (object file). Default: llvm"
    )
    parser.add_argument(
        "-f", "--function",
        default="main",
        help="Entry point function name (default: main)"
    )
    return parser

def main(args: Optional[List[str]] = None) -> int:
    parser = build_parser()
    opts = parser.parse_args(args)

    if not opts.input:
        parser.print_help(sys.stderr)
        return 1

    input_path = Path(opts.input)
    if not input_path.exists():
        sys.stderr.write(f"linum: error: input file not found: '{opts.input}'\n")
        return 1

    try:
        source_code = input_path.read_text(encoding="utf-8")
    except Exception as e:
        sys.stderr.write(f"linum: error: failed to read '{opts.input}': {e}\n")
        return 1

    try:
        llvm_ir = compile_source(source_code, function_name=opts.function)
    except DiagnosticError as e:
        diag = e.diagnostic
        loc = f":{diag.line}:{diag.column}" if diag.line is not None else ""
        sys.stderr.write(f"{opts.input}{loc}: error [{diag.kind}]: {diag.message}\n")
        return 1
    except Exception as e:
        sys.stderr.write(f"linum: internal error: {e}\n")
        return 1

    try:
        if opts.emit == "llvm":
            if opts.output:
                Path(opts.output).write_text(llvm_ir, encoding="utf-8")
            else:
                sys.stdout.write(llvm_ir)
            return 0

        elif opts.emit == "asm":
            asm_code = SystemBackendLinker.compile_to_assembly(llvm_ir)
            if opts.output:
                Path(opts.output).write_text(asm_code, encoding="utf-8")
            else:
                sys.stdout.write(asm_code)
            return 0

        elif opts.emit == "obj":
            out_file = opts.output if opts.output else str(input_path.with_suffix(".o"))
            SystemBackendLinker.compile_to_object(llvm_ir, out_file)
            return 0

    except Exception as e:
        sys.stderr.write(f"linum: backend error: {e}\n")
        return 1

    return 0

if __name__ == "__main__":
    sys.exit(main())
