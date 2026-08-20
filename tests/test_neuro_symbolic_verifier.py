import pytest
pytestmark = pytest.mark.heavy

from linum.ast.nodes import (
    FunctionDecl, BlockStmt, LetStmt, AssignStmt, MoveStmt, IfStmt,
    ReturnStmt, IdentifierExpr, CallExpr
)
# ... The rest of your exact test cases follow down the file ...

from linum.semantic.types import (
    FunctionContract, PRIMITIVE_INTEGER, PRIMITIVE_BOOLEAN, OwnershipMode, Type, SymbolContext
)
from linum.semantic.verifier import NeuroSymbolicAstVerifier, SemanticVerificationError

def test_verifier_accepts_sound_ast():
    contract = FunctionContract("sound_func", (), PRIMITIVE_INTEGER, OwnershipMode.COPY)
    body = BlockStmt([
        LetStmt("x", PRIMITIVE_INTEGER, IdentifierExpr("%val_42")),
        ReturnStmt(IdentifierExpr("x"))
    ])
    func = FunctionDecl(contract, body)
    
    ctx = SymbolContext()
    ctx.bind("%val_42", PRIMITIVE_INTEGER, OwnershipMode.COPY)
    
    verifier = NeuroSymbolicAstVerifier(ctx)
    assert verifier.verify_function(func) is True

def test_verifier_rejects_hallucinated_identifier():
    contract = FunctionContract("hallucinated_func", (), PRIMITIVE_INTEGER, OwnershipMode.COPY)
    body = BlockStmt([
        LetStmt("x", PRIMITIVE_INTEGER, IdentifierExpr("undefined_ghost_symbol")),
        ReturnStmt(IdentifierExpr("x"))
    ])
    func = FunctionDecl(contract, body)
    
    verifier = NeuroSymbolicAstVerifier()
    with pytest.raises(SemanticVerificationError, match="Hallucinated or undefined identifier"):
        verifier.verify_function(func)

def test_verifier_rejects_non_boolean_if_predicate():
    contract = FunctionContract("bad_if_func", (), PRIMITIVE_INTEGER, OwnershipMode.COPY)
    body = BlockStmt([
        LetStmt("num", PRIMITIVE_INTEGER, IdentifierExpr("%val_42")),
        IfStmt(
            IdentifierExpr("num"), # Error: integer used directly as boolean predicate
            BlockStmt([AssignStmt("num", IdentifierExpr("%val_99"))]),
            BlockStmt([AssignStmt("num", IdentifierExpr("%val_0"))])
        ),
        ReturnStmt(IdentifierExpr("num"))
    ])
    func = FunctionDecl(contract, body)
    
    ctx = SymbolContext()
    ctx.bind("%val_42", PRIMITIVE_INTEGER, OwnershipMode.COPY)
    ctx.bind("%val_99", PRIMITIVE_INTEGER, OwnershipMode.COPY)
    ctx.bind("%val_0", PRIMITIVE_INTEGER, OwnershipMode.COPY)

    verifier = NeuroSymbolicAstVerifier(ctx)
    with pytest.raises(SemanticVerificationError, match="must evaluate to BOOLEAN"):
        verifier.verify_function(func)

def test_verifier_rejects_move_from_unbound_variable():
    contract = FunctionContract("unbound_move", (), PRIMITIVE_INTEGER, OwnershipMode.COPY)
    body = BlockStmt([
        MoveStmt("dest_handle", "non_existent_source"),
        ReturnStmt(IdentifierExpr("dest_handle"))
    ])
    func = FunctionDecl(contract, body)
    
    verifier = NeuroSymbolicAstVerifier()
    with pytest.raises(SemanticVerificationError, match="Move from undefined linear resource"):
        verifier.verify_function(func)
