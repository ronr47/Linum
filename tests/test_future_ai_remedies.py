import pytest
from linum.semantic.verifier import NeuroSymbolicAstVerifier
from linum.semantic.errors import NeuroSymbolicDiagnosticError

def test_ai_hallucinated_pointer_mutation_rejection():
    verifier = NeuroSymbolicAstVerifier()
    hallucinated_payload = {
        "provenance": "speculative_hallucination",
        "symbol": "hallucinated_ptr",
        "available_fields": ["%uninit_stub", "%val_42", "%val_0"]
    }
    with pytest.raises(NeuroSymbolicDiagnosticError, match="Neuro-Symbolic Fracture"):
        verifier.verify_epistemic_grounding(hallucinated_payload)

def test_ai_grounded_symbolic_soundness():
    verifier = NeuroSymbolicAstVerifier()
    grounded_payload = {
        "provenance": "verified_grounding",
        "symbol": "%val_42",
        "available_fields": ["%uninit_stub", "%val_42", "%val_0"]
    }
    assert verifier.verify_epistemic_grounding(grounded_payload) is True
