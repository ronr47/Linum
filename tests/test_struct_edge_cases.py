import pytest
from linum.ast.nodes import FunctionDecl, BlockStmt, LetStmt, ReturnStmt, IdentifierExpr, FieldAccessExpr
from linum.semantic.types import (
    SymbolContext,
    FunctionContract,
    PRIMITIVE_INTEGER,
    PRIMITIVE_BOOLEAN,
    OwnershipMode,
    Type,
    StructType,
)
from linum.lowering.cfg import CfgBuilder
from linum.lowering.ssa import SsaConverter, SsaVerifier
from linum.lowering.llvm import LlvmEmitter, SystemBackendLinker

def test_nested_struct_offset_calculation():
    """Validates multi-level field access: outer.inner.val."""
    inner_struct = StructType("Inner", {"flag": PRIMITIVE_BOOLEAN, "data": PRIMITIVE_INTEGER})
    outer_struct = StructType("Outer", {"header": inner_struct, "tail": PRIMITIVE_INTEGER})

    contract = FunctionContract("nested_struct_test", (), PRIMITIVE_INTEGER, OwnershipMode.COPY)
    
    body = BlockStmt([
        LetStmt("out", outer_struct, IdentifierExpr("%out_ptr")),
        LetStmt("inner_obj", inner_struct, FieldAccessExpr(IdentifierExpr("out"), "header")),
        LetStmt("val", PRIMITIVE_INTEGER, FieldAccessExpr(IdentifierExpr("inner_obj"), "data")),
        ReturnStmt(IdentifierExpr("val"))
    ])
    ast_func = FunctionDecl(contract, body)

    ctx = SymbolContext()
    ctx.bind("%out_ptr", outer_struct, OwnershipMode.COPY)

    sem_func = ast_func.check_contract(ctx)
    cfg = CfgBuilder().lower_function(sem_func)
    
    var_types = {"out": "ptr", "inner_obj": "ptr", "val": "INTEGER"}
    ssa = SsaConverter(cfg, var_types).convert()
    SsaVerifier.verify(ssa, var_types)

    llvm = LlvmEmitter(contract).emit(ssa, var_types)
    linker = SystemBackendLinker()
    assert linker.verify_llvm_ir(llvm) is True

def test_invalid_struct_field_rejection():
    """Validates TypeError when querying a non-existent field on a struct."""
    point_type = StructType("Point", {"x": PRIMITIVE_INTEGER, "y": PRIMITIVE_INTEGER})
    contract = FunctionContract("invalid_field", (), PRIMITIVE_INTEGER, OwnershipMode.COPY)

    body = BlockStmt([
        LetStmt("pt", point_type, IdentifierExpr("%pt_ptr")),
        LetStmt("z", PRIMITIVE_INTEGER, FieldAccessExpr(IdentifierExpr("pt"), "z")),
        ReturnStmt(IdentifierExpr("z"))
    ])
    ast_func = FunctionDecl(contract, body)

    ctx = SymbolContext()
    ctx.bind("%pt_ptr", point_type, OwnershipMode.COPY)

    from linum.semantic.errors import NeuroSymbolicDiagnosticError
    with pytest.raises(NeuroSymbolicDiagnosticError, match="has no field 'z'|Valid structural fields"):
        ast_func.check_contract(ctx)

def test_neuro_symbolic_repair_suggestion():
    """Validates that wrong field lookups offer an intelligent string repair suggestion."""
    import pytest
    from linum.semantic.errors import NeuroSymbolicDiagnosticError
    
    point_type = StructType("Point", {"x": PRIMITIVE_INTEGER, "y": PRIMITIVE_INTEGER})
    contract = FunctionContract("repair_test", (), PRIMITIVE_INTEGER, OwnershipMode.COPY)

    body = BlockStmt([
        LetStmt("pt", point_type, IdentifierExpr("%pt_ptr")),
        LetStmt("z", PRIMITIVE_INTEGER, FieldAccessExpr(IdentifierExpr("pt"), "x_typo")),
        ReturnStmt(IdentifierExpr("z"))
    ])
    ast_func = FunctionDecl(contract, body)

    ctx = SymbolContext()
    ctx.bind("%pt_ptr", point_type, OwnershipMode.COPY)

    with pytest.raises(NeuroSymbolicDiagnosticError, match="Did you mean '.x'|Valid structural fields"):
        ast_func.check_contract(ctx)
