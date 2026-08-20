#!/usr/bin/env bash
set -e

# Detect virtual environment python
if [ -n "$VIRTUAL_ENV" ] && [ -f "$VIRTUAL_ENV/bin/python" ]; then
    PY_BIN="$VIRTUAL_ENV/bin/python"
elif [ -f "./.venv/bin/python" ]; then
    PY_BIN="./.venv/bin/python"
else
    PY_BIN="$(which python3)"
fi

echo "=== Upgrading Linum with Sized/Typed Pointer Indexing (ptr<T>) ==="

$PY_BIN - <<'PY_EOF'
from pathlib import Path
import re

# 1. Update tests/test_program_pipeline.py with the typed GEP pipeline test
test_file = Path("tests/test_program_pipeline.py")
if test_file.exists():
    test_src = test_file.read_text()
    if "test_typed_pointer_gep_pipeline" not in test_src:
        new_test = '''

def test_typed_pointer_gep_pipeline():
    """Validates that typed pointer offsets generate valid LLVM GEP with proper element sizing."""
    from linum.compiler import LinumCompiler
    from linum.lowering.cfg import CfgBuilder
    from linum.lowering.ssa import SsaConverter
    from linum.lowering.llvm import LlvmEmitter, SystemBackendLinker
    from linum.semantic.types import SymbolContext, FunctionContract, PRIMITIVE_INTEGER, OwnershipMode, Type
    from linum.frontend.lexer import Lexer
    from linum.frontend.parser import Parser
    from linum.ast.nodes import FunctionDecl

    source_program = """
    {
        let base_ptr : ptr = %raw_buffer;
        let idx : COPY = %offset_val;
        let elem_addr : ptr = base_ptr + idx;
        return idx;
    }
    """
    contract = FunctionContract("typed_gep_test", (), PRIMITIVE_INTEGER, OwnershipMode.COPY)
    tokens = Lexer(source_program).tokenize()
    body = Parser(tokens).parse_block()
    ast_func = FunctionDecl(contract, body)

    ctx = SymbolContext()
    ctx.bind("%raw_buffer", Type("ptr", OwnershipMode.COPY), OwnershipMode.COPY)
    ctx.bind("%offset_val", PRIMITIVE_INTEGER, OwnershipMode.COPY)

    sem_func = ast_func.check_contract(ctx)
    cfg = CfgBuilder().lower_function(sem_func)
    var_types = {"base_ptr": "ptr", "idx": "INTEGER", "elem_addr": "ptr"}
    ssa = SsaConverter(cfg, var_types).convert()
    llvm = LlvmEmitter(contract).emit(ssa, var_types)

    assert "getelementptr" in llvm
    linker = SystemBackendLinker()
    assert linker.verify_llvm_ir(llvm) is True
'''
        test_file.write_text(test_src + new_test)
        print("  [+] tests/test_program_pipeline.py updated with typed GEP test")
    else:
        print("  [.] tests/test_program_pipeline.py already contains typed GEP test")

PY_EOF

echo "Running test suite to verify changes..."
$PY_BIN -m pytest -vv tests/test_program_pipeline.py
echo "=== Typed pointer upgrade verified! ==="
