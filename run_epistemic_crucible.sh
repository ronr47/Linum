#!/usr/bin/env bash
set -euo pipefail

echo "=============================================================================="
echo "    ⚡ LINUM 2050: THE EPISTEMIC STRESS CRUCIBLE (AI REMEDY TEST)             "
echo "=============================================================================="

# 1. Deploy the dual-failure fixture (Linear Knot + Hallucination Breach)
cat << 'LNM_EOF' > tests/programs/epistemic_fracture_knot.linum
{
    let linear_root : LINEAR = %uninit_stub;
    borrow linear_root as alias_handle {
        move premature_sink = linear_root;
        let speculative_escape : COPY = %val_42;
    }
    return %val_0;
}
LNM_EOF

# 2. Write the verification test module
cat << 'TEST_EOF' > tests/test_epistemic_crucible.py
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
TEST_EOF

# 3. Execute the full gate to verify 100% sound rejection & pass metrics
./linum_truth_gate.sh
