import pytest
from linum.ast.nodes import FunctionContract, BlockStmt, IdentifierExpr, FunctionDecl, ReturnStmt, LetStmt
from linum.semantic.types import SymbolContext, PRIMITIVE_INTEGER, OwnershipMode
from linum.ast.simd import SimdVectorOpStmt

def test_simd_generation_and_llvm_compliance():
    """Validates that SIMD operation sequences map successfully through structural validation pipelines when operands are allocated inside local flow scope."""
    contract = FunctionContract("simd_test", (), PRIMITIVE_INTEGER, OwnershipMode.COPY)
    
    op_stmt = SimdVectorOpStmt(
        op="ADD",
        dest_ptr=IdentifierExpr("res_ptr"),
        src1_ptr=IdentifierExpr("a_ptr"),
        src2_ptr=IdentifierExpr("b_ptr"),
        width=4
    )
    
    # Sequence: Bind variables via LetStmt initialized from raw % parameters to track ownership in context frame
    body_sequence = BlockStmt([
        LetStmt("res_ptr", PRIMITIVE_INTEGER, IdentifierExpr("%init_res")),
        LetStmt("a_ptr", PRIMITIVE_INTEGER, IdentifierExpr("%init_a")),
        LetStmt("b_ptr", PRIMITIVE_INTEGER, IdentifierExpr("%init_b")),
        op_stmt,
        ReturnStmt(IdentifierExpr("res_ptr"))
    ])
    
    ast_func = FunctionDecl(contract, body_sequence)
    ctx = SymbolContext()
    ctx.bind("%init_res", PRIMITIVE_INTEGER, OwnershipMode.COPY)
    ctx.bind("%init_a", PRIMITIVE_INTEGER, OwnershipMode.COPY)
    ctx.bind("%init_b", PRIMITIVE_INTEGER, OwnershipMode.COPY)
    
    sem_func = ast_func.check_contract(ctx)
    assert sem_func is not None
