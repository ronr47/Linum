from dataclasses import dataclass
from linum.ast.nodes import ASTNode
from linum.semantic.types import Type

@dataclass
class QuantumSymmetricLoopStmt(ASTNode):
    """
    AST representation of a Deutsch-CTC Paradox-Free Circuit Horizon.
    Syntax: chrono_horizon <state_token> in <body_block>
    """
    state_token: str
    body: ASTNode

    def check_with_contract(self, ctx, flow_state, next_borrow_id, contract):
        # 1. Capture the quantum state signature at the entry horizon boundary
        if self.state_token not in flow_state.ownership:
            from linum.semantic.errors import NeuroSymbolicDiagnosticError
            raise NeuroSymbolicDiagnosticError(
                message=f"Temporal Violation: Causal state token '{self.state_token}' is unbound at the entry horizon.",
                invalid_field=self.state_token,
                available_fields=list(flow_state.ownership.keys())
            )
            
        entry_state = flow_state.ownership[self.state_token]

        # 2. Lower statements inside the chronologically isolated basic block domain
        final_flow, sem_body = self.body.check_with_contract(ctx, flow_state, next_borrow_id, contract)

        # 3. Enforce the Invariant: Exit state profile must match the entry state profile
        exit_state = final_flow.ownership.get(self.state_token, None)
        if entry_state != exit_state:
            from linum.semantic.errors import NeuroSymbolicDiagnosticError
            # Coerce the available states explicitly to a string representation array to satisfy difflib boundaries
            raise NeuroSymbolicDiagnosticError(
                message=f"Temporal Paradox Detected: Variable '{self.state_token}' changed state ownership properties "
                        f"across the causal loop horizon. Entry: {entry_state}, Exit: {exit_state}.",
                invalid_field=str(entry_state),
                available_fields=[str(entry_state)]
            )

        return final_flow, sem_body

    def verify_unitary_matrix(self, matrix: list) -> bool:
        """Verifies unitary preservation invariant: U^dagger * U == Identity"""
        n = len(matrix)
        for i in range(n):
            for j in range(n):
                # Compute inner product between row i and column j conjugate
                sum_val = sum(matrix[i][k] * matrix[j][k] for k in range(n))
                expected = 1 if i == j else 0
                if abs(sum_val - expected) > 1e-6:
                    from linum.semantic.errors import NeuroSymbolicDiagnosticError
                    raise NeuroSymbolicDiagnosticError(
                        f"Quantum Unitary Invariant Broken: Matrix is non-unitary at index ({i}, {j})"
                    )
        return True

    def verify_unitary_matrix(self, matrix: list) -> bool:
        """Verifies unitary preservation invariant: U^dagger * U == Identity"""
        n = len(matrix)
        for i in range(n):
            for j in range(n):
                sum_val = sum(matrix[i][k] * matrix[j][k] for k in range(n))
                expected = 1 if i == j else 0
                if abs(sum_val - expected) > 1e-6:
                    from linum.semantic.errors import NeuroSymbolicDiagnosticError
                    raise NeuroSymbolicDiagnosticError(
                        f"Quantum Unitary Invariant Broken: Matrix is non-unitary at index ({i}, {j})",
                        f"({i},{j})",
                        ["UnitaryPreservingMatrix"]
                    )
        return True
