import pytest
from linum.ast.nodes import FunctionContract, BlockStmt, IdentifierExpr, FunctionDecl, ReturnStmt, LetStmt
from linum.semantic.types import SymbolContext, PRIMITIVE_BOOLEAN, PRIMITIVE_INTEGER, OwnershipMode
from linum.semantic.errors import NeuroSymbolicDiagnosticError
from linum.ast.biology import BioSynthesisPayloadStmt

def test_valid_wetware_sequence_compilation():
    """Validates that a correctly mapped biological payload passes structural sequence check boundaries."""
    # Sourced contract synchronized with target type: return primitive boolean to align with %marker_sig
    contract = FunctionContract("crispr_payload", (), PRIMITIVE_BOOLEAN, OwnershipMode.COPY)
    
    bio_stmt = BioSynthesisPayloadStmt(
        condition_name="is_cancerous",
        target_sequence="ATGACCCTGAGCTAG",  
        action="APOPTOSIS"
    )
    
    body = BlockStmt([
        LetStmt("is_cancerous", PRIMITIVE_BOOLEAN, IdentifierExpr("%marker_sig")),
        bio_stmt,
        ReturnStmt(IdentifierExpr("%marker_sig"))
    ])
    
    ast_func = FunctionDecl(contract, body)
    ctx = SymbolContext()
    ctx.bind("%marker_sig", PRIMITIVE_BOOLEAN, OwnershipMode.COPY)
    
    sem_func = ast_func.check_contract(ctx)
    assert sem_func is not None

def test_invalid_genetic_base_rejection():
    """Validates that the compiler intercepts and rejects sequences corrupted with invalid base pairs."""
    contract = FunctionContract("corrupted_payload", (), PRIMITIVE_BOOLEAN, OwnershipMode.COPY)
    
    bio_stmt = BioSynthesisPayloadStmt(
        condition_name="is_cancerous",
        target_sequence="ATGCZXTAG", 
        action="TRANSCRIPTION_BLOCK"
    )
    
    body = BlockStmt([
        LetStmt("is_cancerous", PRIMITIVE_BOOLEAN, IdentifierExpr("%marker_sig")),
        bio_stmt,
        ReturnStmt(IdentifierExpr("%marker_sig"))
    ])
    
    ast_func = FunctionDecl(contract, body)
    ctx = SymbolContext()
    ctx.bind("%marker_sig", PRIMITIVE_BOOLEAN, OwnershipMode.COPY)
    
    with pytest.raises(NeuroSymbolicDiagnosticError, match="Genetic Corruption"):
        ast_func.check_contract(ctx)
