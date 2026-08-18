import pytest
from linum.src.ast.nodes import FunctionDecl, BlockStmt, LetStmt, ReturnStmt, IdentifierExpr, FieldAccessExpr
from linum.src.semantic.types import (
    SymbolContext,
    FunctionContract,
    PRIMITIVE_INTEGER,
    OwnershipMode,
    Type,
    StructType,
)
from linum.src.lowering.cfg import CfgBuilder
from linum.src.lowering.ssa import SsaConverter, SsaVerifier
from linum.src.lowering.llvm import LlvmEmitter, SystemBackendLinker

def test_composite_struct_field_access_pipeline():
    """Validates full lowering of struct field access to LLVM GEP with proper byte offsets."""
    contract = FunctionContract("struct_field_test", (), PRIMITIVE_INTEGER, OwnershipMode.COPY)
    
    # Struct Header: { asset_id: INTEGER (offset 0), volume: INTEGER (offset 8) }
    header_type = StructType("OrderHeader", {"asset_id": PRIMITIVE_INTEGER, "volume": PRIMITIVE_INTEGER})
    
    body = BlockStmt([
        LetStmt("hdr", header_type, IdentifierExpr("%hdr_ptr")),
        LetStmt("vol", PRIMITIVE_INTEGER, FieldAccessExpr(IdentifierExpr("hdr"), "volume")),
        ReturnStmt(IdentifierExpr("vol"))
    ])
    ast_func = FunctionDecl(contract, body)

    ctx = SymbolContext()
    ctx.bind("%hdr_ptr", header_type, OwnershipMode.COPY)

    sem_func = ast_func.check_contract(ctx)
    cfg = CfgBuilder().lower_function(sem_func)
    
    var_types = {"hdr": "ptr", "vol": "INTEGER"}
    ssa = SsaConverter(cfg, var_types).convert()
    SsaVerifier.verify(ssa, var_types)

    llvm = LlvmEmitter(contract).emit(ssa, var_types)

    assert "getelementptr i8, ptr" in llvm
    assert "i64 8" in llvm  # offset of volume field
    
    linker = SystemBackendLinker()
    assert linker.verify_llvm_ir(llvm) is True

def test_linear_struct_propagation():
    """Validates that a struct containing a linear field becomes linear."""
    linear_res = Type("LINEAR_RES", OwnershipMode.LINEAR)
    record = StructType("Record", {"id": PRIMITIVE_INTEGER, "handle": linear_res})
    assert record.mode == OwnershipMode.LINEAR
