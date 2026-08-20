from dataclasses import dataclass
from linum.ast.nodes import ASTNode
from linum.semantic.types import Type

@dataclass
class BraidGeneratorStmt(ASTNode):
    """
    AST node for Non-Abelian Anyon Spacetime Braid Generation.
    Syntax: braid_sequence <target_qubit> operations <braid_generators>
    """
    qubit_id: str
    generators: list  # Sequence of braid operators, e.g., [1, -1, 2, -2] (sigma indices)

    def check_with_contract(self, ctx, flow_state, next_borrow_id, contract):
        # 1. Enforce that the quantum strand target is initialized in the active context frame
        if self.qubit_id not in flow_state.ownership:
            from linum.semantic.errors import NeuroSymbolicDiagnosticError
            raise NeuroSymbolicDiagnosticError(
                message=f"Topological Dislocation: Qubit strand '{self.qubit_id}' is unbound in the active multi-braid horizon.",
                invalid_field=self.qubit_id,
                available_fields=list(flow_state.ownership.keys())
            )

        # 2. Mathematically check braid sequence invariance (Prevent self-annihilation errors)
        # Generators must contain non-zero integer indices tracking valid crossing pathways
        for op in self.generators:
            if not isinstance(op, int) or op == 0:
                from linum.semantic.errors import NeuroSymbolicDiagnosticError
                raise NeuroSymbolicDiagnosticError(
                    message=f"Geometric Anomaly: Invalid braid generator index '{op}'. Crossing pathways must be non-zero integer sigma matrices.",
                    invalid_field=str(op),
                    available_fields=["1", "-1", "2", "-2"]
                )

        return flow_state, self
