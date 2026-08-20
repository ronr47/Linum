import pytest
from linum.compiler import compile_source
from linum.diagnostics import DiagnosticError
from linum.semantic.verifier import NeuroSymbolicAstVerifier
from linum.semantic.errors import NeuroSymbolicDiagnosticError

def test_linear_lifetime_knot_rejection():
    """Verify Linum catches linear mutation/destruction during active reborrow."""
    with open("tests/programs/epistemic_fracture_knot.linum") as f:
        source = f.read()
    with pytest.raises(DiagnosticError, match="Borrow Invalidation Hazard|Borrow target"):
        compile_source(source, "epistemic_knot")

def test_stochastic_hallucination_barrier():
    """Verify Neuro-Symbolic verifier blocks hallucinated AST allocations."""
    verifier = NeuroSymbolicAstVerifier()
    poison_payload = {
        "provenance": "speculative_hallucination",
        "symbol": "%hallucinated_quantum_ptr",
        "available_fields": ["%uninit_stub", "%val_42", "%val_0"]
    }
    with pytest.raises(NeuroSymbolicDiagnosticError, match="Neuro-Symbolic Fracture"):
        verifier.verify_epistemic_grounding(poison_payload)
