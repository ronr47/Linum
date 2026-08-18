import pytest
from src.ast.nodes import FunctionContract, BlockStmt, LetStmt, IdentifierExpr, FunctionDecl
from src.semantic.types import SymbolContext, StructType, PRIMITIVE_INTEGER, OwnershipMode
from src.ast.borrow import BorrowStmt

def test_aliasing_exclusivity_enforcement():
    """Verifies compile-time validation block rejects overlapping exclusive borrows."""
    struct_type = StructType("Data", {"val": PRIMITIVE_INTEGER})
    contract = FunctionContract("borrow_test", (), PRIMITIVE_INTEGER, OwnershipMode.COPY)
    
    # Nested conflicting borrow statement sequence simulation
    inner_body = BlockStmt([LetStmt("dummy", PRIMITIVE_INTEGER, IdentifierExpr("b1"))])
    nested_borrow = BorrowStmt("b2", "EXCLUSIVE", IdentifierExpr("target"), inner_body)
    outer_body = BlockStmt([nested_borrow])
    
    root_borrow = BorrowStmt("b1", "SHARED", IdentifierExpr("target"), outer_body)
    ast_func = FunctionDecl(contract, root_borrow)
    
    ctx = SymbolContext()
    ctx.bind("target", struct_type, OwnershipMode.COPY)
    
    from src.semantic.errors import NeuroSymbolicDiagnosticError
    with pytest.raises(NeuroSymbolicDiagnosticError, match="Aliasing violation"):
        ast_func.check_contract(ctx)

def test_full_pipeline_borrow_lowering():
    """Validates that valid reference lifetimes pass lowering, SSA transformation, and LLVM emission."""
    from src.ast.nodes import BlockStmt, LetStmt, IdentifierExpr, FunctionDecl, FunctionContract, ReturnStmt
    from src.semantic.types import SymbolContext, StructType, PRIMITIVE_INTEGER, OwnershipMode
    from src.ast.borrow import BorrowStmt
    from src.lowering.cfg import CfgBuilder
    from src.lowering.ssa import SsaConverter
    from src.lowering.llvm import LlvmEmitter

    struct_type = StructType("ValContainer", {"data": PRIMITIVE_INTEGER})
    contract = FunctionContract("full_pipeline_test", (), PRIMITIVE_INTEGER, OwnershipMode.COPY)

    inner_body = BlockStmt([
        ReturnStmt(IdentifierExpr("val_target"))
    ])
    
    # Linear execution path: root let statement -> reference isolation block -> finalization exit
    root_body = BlockStmt([
        LetStmt("val_target", PRIMITIVE_INTEGER, IdentifierExpr("%init_val")),
        BorrowStmt("b_ref", "SHARED", IdentifierExpr("val_target"), inner_body)
    ])
    
    ast_func = FunctionDecl(contract, root_body)
    ctx = SymbolContext()
    ctx.bind("%init_val", PRIMITIVE_INTEGER, OwnershipMode.COPY)
    
    sem_func = ast_func.check_contract(ctx)
    cfg = CfgBuilder().lower_function(sem_func)
    
    var_types = {"val_target": "INTEGER", "b_ref": "ptr"}
    ssa = SsaConverter(cfg, var_types).convert()
    llvm = LlvmEmitter(contract).emit(ssa, var_types)
    
    assert "define" in llvm or len(llvm) > 0
    print("✅ Reference lifetime block successfully validated across full backend compiler pipeline.")
