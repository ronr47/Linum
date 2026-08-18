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
    parser.add_argument(
        "--audit-leak",
        action="store_true",
        help="Perform strict static resource leak and affine soundness auditing on the source file."
    )
    parser.add_argument(
        "--audit-c",
        help="Perform strict memory leak and FFI safety audit on a C source/header file."
    )
    return parser

def main(args: Optional[List[str]] = None) -> int:
    parser = build_parser()
    opts = parser.parse_args(args)

    # Handle early routing path for external C source/header audits
    if getattr(opts, "audit_c", None):
        try:
            from src.c_auditor import CAuditor
            auditor = CAuditor()
            errs = auditor.audit_source(opts.audit_c)
            if errs:
                for err in errs:
                    sys.stderr.write(f"{err.file_path}:{err.line}: error [memory-leak]: {err.message}\n")
                return 1
            sys.stdout.write(f"SUCCESS: '{opts.audit_c}' passed C FFI memory audit with 0 leaks detected.\n")
            return 0
        except Exception as e:
            sys.stderr.write(f"Driver execution error during C audit: {str(e)}\n")
            return 1

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
        if getattr(opts, "audit_leak", None):
            compile_source(source_code, function_name=opts.function)
            sys.stdout.write(f"SUCCESS: '{opts.input}' passed all Linum affine/linear leak and safety invariants.\n")
            return 0
            
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
