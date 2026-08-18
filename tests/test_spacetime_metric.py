import pytest
from src.ast.nodes import FunctionContract, BlockStmt, IdentifierExpr, FunctionDecl, ReturnStmt, LetStmt
from src.semantic.types import SymbolContext, PRIMITIVE_BOOLEAN, OwnershipMode
from src.semantic.errors import NeuroSymbolicDiagnosticError
from src.ast.spacetime import MetricTensorFieldStmt

def test_valid_schwarzschild_metric_compilation():
    """Validates that a structurally sound Schwarzschild geometry model passes signature criteria."""
    contract = FunctionContract("schwarzschild_pipeline", (), PRIMITIVE_BOOLEAN, OwnershipMode.COPY)
    
    # Valid 4D pseudo-Riemannian tensor component configuration
    metric_stmt = MetricTensorFieldStmt(
        tensor_id="g_munu",
        components={
            "00": "-(1 - 2*M/r)",
            "11": "1 / (1 - 2*M/r)",
            "22": "r**2",
            "33": "r**2 * sin(theta)**2"
        }
    )
    
    body = BlockStmt([
        LetStmt("g_munu", PRIMITIVE_BOOLEAN, IdentifierExpr("%init_tensor")),
        metric_stmt,
        ReturnStmt(IdentifierExpr("g_munu"))
    ])
    
    ast_func = FunctionDecl(contract, body)
    ctx = SymbolContext()
    ctx.bind("%init_tensor", PRIMITIVE_BOOLEAN, OwnershipMode.COPY)
    
    sem_func = ast_func.check_contract(ctx)
    assert sem_func is not None

def test_invalid_metric_signature_rejection():
    """Validates that dimensional collapse (missing diagonal metrics) is rejected immediately."""
    contract = FunctionContract("collapsed_metric", (), PRIMITIVE_BOOLEAN, OwnershipMode.COPY)
    
    # Missing component "33", which triggers a structural metric tensor invariant violation
    metric_stmt = MetricTensorFieldStmt(
        tensor_id="g_munu",
        components={
            "00": "-1",
            "11": "1",
            "22": "1"
        }
    )
    
    body = BlockStmt([
        LetStmt("g_munu", PRIMITIVE_BOOLEAN, IdentifierExpr("%init_tensor")),
        metric_stmt,
        ReturnStmt(IdentifierExpr("g_munu"))
    ])
    
    ast_func = FunctionDecl(contract, body)
    ctx = SymbolContext()
    ctx.bind("%init_tensor", PRIMITIVE_BOOLEAN, OwnershipMode.COPY)
    
    with pytest.raises(NeuroSymbolicDiagnosticError, match="Singularity Anomaly"):
        ast_func.check_contract(ctx)
