import pytest
from src.ast.nodes import FunctionContract, BlockStmt, IdentifierExpr, FunctionDecl, ReturnStmt, LetStmt
from src.semantic.types import SymbolContext, PRIMITIVE_BOOLEAN, OwnershipMode
from src.semantic.errors import NeuroSymbolicDiagnosticError
from src.ast.regge import ReggeSimplexStmt

def test_valid_regge_triangulation_compilation():
    """Validates that a geometrically flat and physically consistent simplicial complex passes triangle constraints."""
    contract = FunctionContract("regge_pipeline", (), PRIMITIVE_BOOLEAN, OwnershipMode.COPY)
    
    metric_stmt = ReggeSimplexStmt(
        complex_id="s_foam",
        edge_lengths={"e1": 3.0, "e2": 4.0, "e3": 5.0},
        faces=[("e1", "e2", "e3")]
    )
    
    body = BlockStmt([
        LetStmt("s_foam", PRIMITIVE_BOOLEAN, IdentifierExpr("%init_complex")),
        metric_stmt,
        ReturnStmt(IdentifierExpr("s_foam"))
    ])
    
    ast_func = FunctionDecl(contract, body)
    ctx = SymbolContext()
    ctx.bind("%init_complex", PRIMITIVE_BOOLEAN, OwnershipMode.COPY)
    
    sem_func = ast_func.check_contract(ctx)
    assert sem_func is not None

def test_invalid_triangle_inequality_rejection():
    """Validates that un-formable geometric faces are caught and rejected immediately."""
    contract = FunctionContract("collapsed_foam", (), PRIMITIVE_BOOLEAN, OwnershipMode.COPY)
    
    # 1.0 + 2.0 <= 10.0 -> Breaks flat or curved geometric spatial rules entirely
    metric_stmt = ReggeSimplexStmt(
        complex_id="s_foam",
        edge_lengths={"e1": 1.0, "e2": 2.0, "e3": 10.0},
        faces=[("e1", "e2", "e3")]
    )
    
    body = BlockStmt([
        LetStmt("s_foam", PRIMITIVE_BOOLEAN, IdentifierExpr("%init_complex")),
        metric_stmt,
        ReturnStmt(IdentifierExpr("s_foam"))
    ])
    
    ast_func = FunctionDecl(contract, body)
    ctx = SymbolContext()
    ctx.bind("%init_complex", PRIMITIVE_BOOLEAN, OwnershipMode.COPY)
    
    with pytest.raises(NeuroSymbolicDiagnosticError, match="Simplicial Singularity"):
        ast_func.check_contract(ctx)
