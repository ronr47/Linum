import pytest
from linum.ast.nodes import FunctionContract, BlockStmt, IdentifierExpr, FunctionDecl, ReturnStmt, LetStmt
from linum.semantic.types import SymbolContext, PRIMITIVE_BOOLEAN, OwnershipMode
from linum.semantic.errors import NeuroSymbolicDiagnosticError
from linum.ast.topological import BraidGeneratorStmt

def test_valid_braid_sequence_compilation():
    """Validates that a structurally sound geometry mapping passes anyon crossing criteria."""
    contract = FunctionContract("braid_pipeline", (), PRIMITIVE_BOOLEAN, OwnershipMode.COPY)
    
    # Valid Non-Abelian braid string operations (Sigma_1, Sigma_1_inverse, Sigma_2)
    braid_stmt = BraidGeneratorStmt(
        qubit_id="q_anyons",
        generators=[1, -1, 2]
    )
    
    body = BlockStmt([
        LetStmt("q_anyons", PRIMITIVE_BOOLEAN, IdentifierExpr("%init_qubit")),
        braid_stmt,
        ReturnStmt(IdentifierExpr("q_anyons"))
    ])
    
    ast_func = FunctionDecl(contract, body)
    ctx = SymbolContext()
    ctx.bind("%init_qubit", PRIMITIVE_BOOLEAN, OwnershipMode.COPY)
    
    sem_func = ast_func.check_contract(ctx)
    assert sem_func is not None

def test_invalid_braid_operator_rejection():
    """Validates that geometric singularities (zero crossings) are rejected immediately."""
    contract = FunctionContract("broken_braid", (), PRIMITIVE_BOOLEAN, OwnershipMode.COPY)
    
    # Zero index signifies an un-crossed self-annihilating state anomaly
    braid_stmt = BraidGeneratorStmt(
        qubit_id="q_anyons",
        generators=[1, 0, 2]
    )
    
    body = BlockStmt([
        LetStmt("q_anyons", PRIMITIVE_BOOLEAN, IdentifierExpr("%init_qubit")),
        braid_stmt,
        ReturnStmt(IdentifierExpr("q_anyons"))
    ])
    
    ast_func = FunctionDecl(contract, body)
    ctx = SymbolContext()
    ctx.bind("%init_qubit", PRIMITIVE_BOOLEAN, OwnershipMode.COPY)
    
    with pytest.raises(NeuroSymbolicDiagnosticError, match="Geometric Anomaly"):
        ast_func.check_contract(ctx)
