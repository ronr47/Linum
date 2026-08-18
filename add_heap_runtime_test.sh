#!/usr/bin/env bash
set -e

PY_BIN="$( [ -f "./.venv/bin/python" ] && echo "./.venv/bin/python" || echo "$(which python3)" )"
export PYTHONPATH=".:$PYTHONPATH"

$PY_BIN - <<'PY_EOF'
from pathlib import Path

test_file = Path("tests/test_program_pipeline.py")
content = test_file.read_text()

if "test_heap_allocation_and_free_pipeline" not in content:
    new_tests = '''

def test_heap_allocation_and_free_pipeline():
    """Validates dynamic heap allocation (malloc), pointer mutation, and explicit deallocation (free)."""
    from linum.src.lowering.cfg import BasicBlock, CfgFunction, IrCall, IrPtrStore, IrPtrLoad, IrReturn
    from linum.src.lowering.ssa import SsaConverter, SsaVerifier
    from linum.src.lowering.llvm import LlvmEmitter, SystemBackendLinker
    from linum.src.semantic.types import FunctionContract, PRIMITIVE_INTEGER, OwnershipMode

    entry_bb = BasicBlock("entry_heap")
    entry_bb.instructions = [
        IrCall(target_reg="%raw_buf", function="malloc", args_regs=("%size_bytes",)),
        IrPtrStore(value_reg="%val_42", pointer_var="%raw_buf"),
        IrPtrLoad(target_reg="%loaded_val", pointer_var="%raw_buf"),
        IrCall(target_reg=None, function="free", args_regs=("%raw_buf",)),
        IrReturn(val_reg="%loaded_val")
    ]
    entry_bb.terminator = IrReturn(val_reg="%loaded_val")

    blocks = {"entry_heap": entry_bb}
    successors = {"entry_heap": set()}
    predecessors = {"entry_heap": set()}
    cfg = CfgFunction("heap_lifecycle_test", "entry_heap", blocks, successors, predecessors)

    var_types = {"raw_buf": "ptr", "loaded_val": "INTEGER"}
    ssa = SsaConverter(cfg, var_types).convert()
    SsaVerifier.verify(ssa, var_types)

    contract = FunctionContract("heap_lifecycle_test", (), PRIMITIVE_INTEGER, OwnershipMode.COPY)
    llvm = LlvmEmitter(contract).emit(ssa, var_types)

    assert "declare noalias ptr @malloc(i64)" in llvm
    assert "declare void @free(ptr)" in llvm
    assert "call ptr @malloc(i64 %size_bytes_arg)" in llvm
    assert "call void @free(ptr %raw_buf)" in llvm

    linker = SystemBackendLinker()
    assert linker.verify_llvm_ir(llvm) is True


def test_linear_resource_drop_emission():
    """Validates automatic drop insertion (__drop_linear_resource) for linear resources."""
    from linum.src.lowering.cfg import BasicBlock, CfgFunction, IrDrop, IrReturn
    from linum.src.lowering.ssa import SsaConverter, SsaVerifier
    from linum.src.lowering.llvm import LlvmEmitter, SystemBackendLinker
    from linum.src.semantic.types import FunctionContract, PRIMITIVE_INTEGER, OwnershipMode

    entry_bb = BasicBlock("entry_drop")
    entry_bb.instructions = [
        IrDrop(var_name="%linear_handle", type_name="ptr"),
        IrReturn(val_reg="%val_42")
    ]
    entry_bb.terminator = IrReturn(val_reg="%val_42")

    blocks = {"entry_drop": entry_bb}
    successors = {"entry_drop": set()}
    predecessors = {"entry_drop": set()}
    cfg = CfgFunction("linear_drop_test", "entry_drop", blocks, successors, predecessors)

    var_types = {"linear_handle": "ptr", "val_42": "INTEGER"}
    ssa = SsaConverter(cfg, var_types).convert()
    SsaVerifier.verify(ssa, var_types)

    contract = FunctionContract("linear_drop_test", (), PRIMITIVE_INTEGER, OwnershipMode.COPY)
    llvm = LlvmEmitter(contract).emit(ssa, var_types)

    assert "declare void @__drop_linear_resource(ptr)" in llvm
    assert "call void @__drop_linear_resource(ptr %linear_handle_arg)" in llvm

    linker = SystemBackendLinker()
    assert linker.verify_llvm_ir(llvm) is True
'''
    test_file.write_text(content + new_tests)
    print("  [+] Added heap allocation & linear drop pipeline tests.")
else:
    print("  [.] Heap allocation tests already present.")
PY_EOF

echo "Running pytest across all suites..."
$PY_BIN -m pytest -vv
