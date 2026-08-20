import pytest
from linum.ast.regge import ReggeSimplexStmt
from linum.ast.quantum import QuantumSymmetricLoopStmt
from linum.ast.nodes import BlockStmt
from linum.c_auditor import CAuditor
from linum.semantic.errors import NeuroSymbolicDiagnosticError

def test_regge_euler_characteristic_success():
    node = ReggeSimplexStmt(
        complex_id="sphere_s2",
        edge_lengths={"e1": 1.0, "e2": 1.0, "e3": 1.0},
        faces=[("e1", "e2", "e3")]
    )
    # Sphere S^2: V=4, E=6, F=4 -> chi = 4 - 6 + 4 = 2
    assert node.verify_euler_characteristic(vertices=4, edges=6, faces=4, expected_chi=2) is True

def test_regge_euler_characteristic_violation():
    node = ReggeSimplexStmt(
        complex_id="collapsed_complex",
        edge_lengths={"e1": 1.0, "e2": 1.0, "e3": 1.0},
        faces=[("e1", "e2", "e3")]
    )
    with pytest.raises(NeuroSymbolicDiagnosticError, match="Topological Simplex Collapse"):
        node.verify_euler_characteristic(vertices=4, edges=5, faces=4, expected_chi=2)

def test_quantum_unitary_invariant_success():
    node = QuantumSymmetricLoopStmt(
        state_token="psi_0",
        body=BlockStmt(statements=[])
    )
    pauli_x = [[0, 1], [1, 0]]
    assert node.verify_unitary_matrix(pauli_x) is True

def test_quantum_unitary_invariant_violation():
    node = QuantumSymmetricLoopStmt(
        state_token="psi_leaky",
        body=BlockStmt(statements=[])
    )
    bad_gate = [[1, 1], [0, 1]]
    with pytest.raises(NeuroSymbolicDiagnosticError, match="Quantum Unitary Invariant Broken"):
        node.verify_unitary_matrix(bad_gate)

def test_c_auditor_patch_synthesis():
    auditor = CAuditor()
    patch = auditor.synthesize_repair_patch("tests/valid_audit_sample.linum")
    assert "No patch required" in patch or "Auto-Synthesized" in patch
