import pytest
from linum.ast.nodes import FunctionContract, BlockStmt, IdentifierExpr, FunctionDecl, ReturnStmt, LetStmt
from linum.semantic.types import SymbolContext, PRIMITIVE_INTEGER, OwnershipMode
from linum.ast.simd import SimdVectorOpStmt
from linum.lowering.cfg import CfgBuilder
from linum.lowering.ssa import SsaConverter
from linum.lowering.llvm import LlvmEmitter

def test_simd_hardware_register_generation_string():
    """Statically verifies backend emission matches packed primitive architectural instructions."""
    contract = FunctionContract("simd_codegen_test", (), PRIMITIVE_INTEGER, OwnershipMode.COPY)
    
    op_stmt = SimdVectorOpStmt(
        op="ADD",
        dest_ptr=IdentifierExpr("res_ptr"),
        src1_ptr=IdentifierExpr("a_ptr"),
        src2_ptr=IdentifierExpr("b_ptr"),
        width=4
    )
    
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
    cfg = CfgBuilder().lower_function(sem_func)
    
    var_types = {"res_ptr": "ptr", "a_ptr": "ptr", "b_ptr": "ptr", "val_target": "INTEGER"}
    ssa = SsaConverter(cfg, var_types).convert()
    llvm_ir = LlvmEmitter(contract).emit(ssa, var_types)
    
    # Enforce strict compliance for target register structures
    assert "load <4 x i32>" in llvm_ir
    assert "add <4 x i32>" in llvm_ir
    assert "store <4 x i32>" in llvm_ir
    print("✅ Direct vector register mapping verified structurally.")
