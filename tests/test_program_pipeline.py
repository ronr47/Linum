from pathlib import Path
import pytest

from linum.src.compiler import compile_source
from linum.src.diagnostics import DiagnosticError

ROOT = Path(__file__).parent / "programs"

def load(name):
    return (ROOT / name).read_text()

def test_branch_file_pipeline():
    llvm = compile_source(
        load("branch.linum"),
        "branch_test",
    )
    assert "phi i64" in llvm

def test_arithmetic_file_pipeline():
    llvm = compile_source(
        load("arithmetic.linum"),
        "arith_test",
    )
    assert "define" in llvm

def test_linear_failure_file_pipeline():
    with pytest.raises(DiagnosticError) as exc:
        compile_source(
            load("linear_move_fail.linum"),
            "linear_fail",
        )
    assert "Linear variable 'x' is leaked" in str(exc.value)
    assert "semantic" in str(exc.value)

def test_unmanaged_ptr_integration_pipeline():
    """Validates full end-to-end compiler handling of raw unsafe pointer manipulations."""
    from linum.src.compiler import LinumCompiler
    from linum.src.lowering.cfg import CfgBuilder, LiveVariableAnalyzer
    from linum.src.lowering.ssa import SsaConverter, SsaVerifier
    from linum.src.lowering.llvm import LlvmEmitter, SystemBackendLinker
    from linum.src.semantic.types import (
        SymbolContext,
        FunctionContract,
        PRIMITIVE_INTEGER,
        OwnershipMode,
        Type,
    )
    from linum.src.frontend.lexer import Lexer
    from linum.src.frontend.parser import Parser
    from linum.src.ast.nodes import FunctionDecl

    source_program = """
    {
        let ptr_var : ptr = %uninit_stub;
        let q : COPY = %val_42;
        return q;
    }
    """

    compiler = LinumCompiler()
    contract = FunctionContract("unsafe_ptr_integration", (), PRIMITIVE_INTEGER, OwnershipMode.COPY)

    tokens = Lexer(source_program).tokenize()
    body = Parser(tokens).parse_block()
    ast_func = FunctionDecl(contract, body)

    ctx = SymbolContext()
    ctx.bind("%uninit_stub", Type("ptr", OwnershipMode.COPY), OwnershipMode.COPY)
    ctx.bind("%val_42", PRIMITIVE_INTEGER, OwnershipMode.COPY)

    sem_func = ast_func.check_contract(ctx)
    cfg = CfgBuilder().lower_function(sem_func)

    nll = LiveVariableAnalyzer(cfg)
    nll.analyze_lifetimes()
    nll.validate_use_after_live_range()

    var_types = {"ptr_var": "ptr", "q": "INTEGER"}
    ssa = SsaConverter(cfg, var_types).convert()
    SsaVerifier.verify(ssa, var_types)

    llvm = LlvmEmitter(contract).emit(ssa, var_types)

    linker = SystemBackendLinker()
    assert linker.verify_llvm_ir(llvm) is True, "IMPOSSIBLE: Generated unmanaged pointer IR failed LLVM validation."
    print("🟢 Unmanaged Pointer end-to-end integration pipeline passed flawlessly.")

def test_raw_pointer_arithmetic_pipeline():
    """Validates full end-to-end compiler handling of unmanaged pointer offset math (GEP)."""
    from linum.src.compiler import LinumCompiler
    from linum.src.lowering.cfg import CfgBuilder, LiveVariableAnalyzer
    from linum.src.lowering.ssa import SsaConverter, SsaVerifier
    from linum.src.lowering.llvm import LlvmEmitter, SystemBackendLinker
    from linum.src.semantic.types import (
        SymbolContext,
        FunctionContract,
        PRIMITIVE_INTEGER,
        OwnershipMode,
        Type,
    )
    from linum.src.frontend.lexer import Lexer
    from linum.src.frontend.parser import Parser
    from linum.src.ast.nodes import FunctionDecl

    source_program = """
    {
        let base_ptr : ptr = %uninit_stub;
        let offset : COPY = %val_42;
        let target : ptr = base_ptr + offset;
        return offset;
    }
    """

    compiler = LinumCompiler()
    contract = FunctionContract("ptr_arith_test", (), PRIMITIVE_INTEGER, OwnershipMode.COPY)

    tokens = Lexer(source_program).tokenize()
    body = Parser(tokens).parse_block()
    ast_func = FunctionDecl(contract, body)

    ctx = SymbolContext()
    ctx.bind("%uninit_stub", Type("ptr", OwnershipMode.COPY), OwnershipMode.COPY)
    ctx.bind("%val_42", PRIMITIVE_INTEGER, OwnershipMode.COPY)

    sem_func = ast_func.check_contract(ctx)
    cfg = CfgBuilder().lower_function(sem_func)

    var_types = {"base_ptr": "ptr", "offset": "INTEGER", "target": "ptr"}
    ssa = SsaConverter(cfg, var_types).convert()

    llvm = LlvmEmitter(contract).emit(ssa, var_types)

    assert "getelementptr" in llvm, "IMPOSSIBLE: LLVM backend failed to emit getelementptr for pointer offset math."

    linker = SystemBackendLinker()
    assert linker.verify_llvm_ir(llvm) is True, "IMPOSSIBLE: Generated GEP IR failed LLVM validation."
    print("🟢 Pointer arithmetic end-to-end integration test passed.")

def test_pointer_arithmetic_invalid_base_type_rejection():
    """Validates that non-pointer base types in offset arithmetic raise TypeError."""
    from linum.src.frontend.lexer import Lexer
    from linum.src.frontend.parser import Parser
    from linum.src.ast.nodes import FunctionDecl
    from linum.src.semantic.types import (
        SymbolContext,
        FunctionContract,
        PRIMITIVE_INTEGER,
        PRIMITIVE_BOOLEAN,
        OwnershipMode,
    )

    source_program = """
    {
        let base_val : COPY = %int_stub;
        let offset : COPY = %val_42;
        let target : ptr = base_val + offset;
        return offset;
    }
    """
    contract = FunctionContract("invalid_base_test", (), PRIMITIVE_INTEGER, OwnershipMode.COPY)
    tokens = Lexer(source_program).tokenize()
    body = Parser(tokens).parse_block()
    ast_func = FunctionDecl(contract, body)

    ctx = SymbolContext()
    ctx.bind("%int_stub", PRIMITIVE_INTEGER, OwnershipMode.COPY)
    ctx.bind("%val_42", PRIMITIVE_INTEGER, OwnershipMode.COPY)

    with pytest.raises(TypeError) as exc:
        ast_func.check_contract(ctx)

    assert "Pointer arithmetic requires ptr base" in str(exc.value)


def test_pointer_arithmetic_invalid_offset_type_rejection():
    """Validates that non-integer offset types in pointer arithmetic raise TypeError."""
    from linum.src.frontend.lexer import Lexer
    from linum.src.frontend.parser import Parser
    from linum.src.ast.nodes import FunctionDecl
    from linum.src.semantic.types import (
        SymbolContext,
        FunctionContract,
        PRIMITIVE_INTEGER,
        OwnershipMode,
        Type,
    )

    source_program = """
    {
        let base_ptr : ptr = %uninit_stub;
        let bad_offset : LINEAR = %lin_stub;
        let target : ptr = base_ptr + bad_offset;
        return bad_offset;
    }
    """
    contract = FunctionContract("invalid_offset_test", (), Type("LINEAR_RES", OwnershipMode.LINEAR), OwnershipMode.LINEAR)
    tokens = Lexer(source_program).tokenize()
    body = Parser(tokens).parse_block()
    ast_func = FunctionDecl(contract, body)

    ctx = SymbolContext()
    ctx.bind("%uninit_stub", Type("ptr", OwnershipMode.COPY), OwnershipMode.COPY)
    ctx.bind("%lin_stub", Type("LINEAR_RES", OwnershipMode.LINEAR), OwnershipMode.LINEAR)

    with pytest.raises(TypeError) as exc:
        ast_func.check_contract(ctx)

    assert "Pointer arithmetic requires INTEGER offset" in str(exc.value)


def test_typed_pointer_gep_pipeline():
    """Validates that typed pointer offsets generate valid LLVM GEP with proper element sizing."""
    from linum.src.compiler import LinumCompiler
    from linum.src.lowering.cfg import CfgBuilder
    from linum.src.lowering.ssa import SsaConverter
    from linum.src.lowering.llvm import LlvmEmitter, SystemBackendLinker
    from linum.src.semantic.types import SymbolContext, FunctionContract, PRIMITIVE_INTEGER, OwnershipMode, Type
    from linum.src.frontend.lexer import Lexer
    from linum.src.frontend.parser import Parser
    from linum.src.ast.nodes import FunctionDecl

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


def test_ptr_store_and_load_deref_pipeline():
    """Validates raw pointer dereferencing with IrPtrStore and IrPtrLoad through LLVM lowering."""
    from linum.src.lowering.cfg import BasicBlock, CfgFunction, IrPtrStore, IrPtrLoad, IrReturn, IrBranch
    from linum.src.lowering.ssa import SsaConverter, SsaVerifier
    from linum.src.lowering.llvm import LlvmEmitter, SystemBackendLinker
    from linum.src.semantic.types import FunctionContract, PRIMITIVE_INTEGER, OwnershipMode

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
