#!/usr/bin/env bash
set -e

PY_BIN="$( [ -f "./.venv/bin/python" ] && echo "./.venv/bin/python" || echo "$(which python3)" )"
export PYTHONPATH=".:$PYTHONPATH"

$PY_BIN - <<'PY_EOF'
from pathlib import Path

test_file = Path("tests/test_program_pipeline.py")
content = test_file.read_text()

if "test_ptr_store_and_load_deref_pipeline" not in content:
    new_test = '''

def test_ptr_store_and_load_deref_pipeline():
    """Validates raw pointer dereferencing with IrPtrStore and IrPtrLoad through LLVM lowering."""
    from linum.lowering.cfg import BasicBlock, CfgFunction, IrPtrStore, IrPtrLoad, IrReturn, IrBranch
    from linum.lowering.ssa import SsaConverter, SsaVerifier
    from linum.lowering.llvm import LlvmEmitter, SystemBackendLinker
    from linum.semantic.types import FunctionContract, PRIMITIVE_INTEGER, OwnershipMode

    entry_bb = BasicBlock("entry_deref")
    entry_bb.instructions = [
        IrPtrStore(value_reg="%val_42", pointer_var="%raw_buffer"),
        IrPtrLoad(target_reg="%loaded_res", pointer_var="%raw_buffer"),
        IrReturn(val_reg="%loaded_res")
    ]
    entry_bb.terminator = IrReturn(val_reg="%loaded_res")

    blocks = {"entry_deref": entry_bb}
    successors = {"entry_deref": set()}
    predecessors = {"entry_deref": set()}
    cfg = CfgFunction("ptr_deref_test", "entry_deref", blocks, successors, predecessors)

    var_types = {"raw_buffer": "ptr", "loaded_res": "INTEGER"}
    ssa = SsaConverter(cfg, var_types).convert()
    SsaVerifier.verify(ssa, var_types)

    contract = FunctionContract("ptr_deref_test", (), PRIMITIVE_INTEGER, OwnershipMode.COPY)
    llvm = LlvmEmitter(contract).emit(ssa, var_types)

    assert "store i64 %val_42_arg, ptr %raw_buffer_arg" in llvm
    assert "load i64, ptr %raw_buffer_arg" in llvm

    linker = SystemBackendLinker()
    assert linker.verify_llvm_ir(llvm) is True
'''
    test_file.write_text(content + new_test)
    print("  [+] Appended test_ptr_store_and_load_deref_pipeline to tests/test_program_pipeline.py")
else:
    print("  [.] test_ptr_store_and_load_deref_pipeline already exists.")
PY_EOF

echo "Running pytest over all suites..."
$PY_BIN -m pytest -vv
