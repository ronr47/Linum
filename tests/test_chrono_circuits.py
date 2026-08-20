import pytest
from linum.ast.nodes import FunctionContract, BlockStmt, IdentifierExpr, FunctionDecl, ReturnStmt, LetStmt, AssignStmt
from linum.semantic.types import SymbolContext, PRIMITIVE_INTEGER, OwnershipMode
from linum.semantic.errors import NeuroSymbolicDiagnosticError
from linum.ast.quantum import QuantumSymmetricLoopStmt

def test_paradox_free_circuit_acceptance():
    """Validates that a chrono-loop passes compilation when entry and exit ownership identities align perfectly."""
    contract = FunctionContract("consistent_timeline", (), PRIMITIVE_INTEGER, OwnershipMode.COPY)
    
    inner_body = BlockStmt([
        AssignStmt("t_var", IdentifierExpr("%val_42"))
    ])
    
    body = BlockStmt([
        LetStmt("t_var", PRIMITIVE_INTEGER, IdentifierExpr("%init_val")),
        QuantumSymmetricLoopStmt("t_var", inner_body),
        ReturnStmt(IdentifierExpr("t_var"))
    ])
    
    ast_func = FunctionDecl(contract, body)
    ctx = SymbolContext()
    ctx.bind("%init_val", PRIMITIVE_INTEGER, OwnershipMode.COPY)
    ctx.bind("%val_42", PRIMITIVE_INTEGER, OwnershipMode.COPY)
    
    sem_func = ast_func.check_contract(ctx)
    assert sem_func is not None

def test_paradoxical_circuit_rejection():
    """Validates that a NeuroSymbolicDiagnosticError is raised if an exit state mismatch breaks chronological symmetry."""
    contract = FunctionContract("paradoxical_timeline", (), PRIMITIVE_INTEGER, OwnershipMode.COPY)
    
    # Define an active mock loop body to surgically break ownership symmetries on pass-by-copy types
    class MockLoopBody(BlockStmt):
        def check_with_contract(self, ctx, flow_state, next_borrow_id, contract):
            if "t_var" in flow_state.ownership:
                flow_state.ownership["t_var"] = "CORRUPTED_TEMPORAL_STATE"
            # Return tuple to satisfy internal semantic pipeline expectations
            return flow_state, self

    body = BlockStmt([
        LetStmt("t_var", PRIMITIVE_INTEGER, IdentifierExpr("%init_val")),
        QuantumSymmetricLoopStmt("t_var", MockLoopBody([])),
        ReturnStmt(IdentifierExpr("t_var"))
    ])
    
    ast_func = FunctionDecl(contract, body)
    ctx = SymbolContext()
    ctx.bind("%init_val", PRIMITIVE_INTEGER, OwnershipMode.COPY)
    
    with pytest.raises(NeuroSymbolicDiagnosticError, match="Temporal Paradox Detected"):
        ast_func.check_contract(ctx)
