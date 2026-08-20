from dataclasses import dataclass
from linum.ast.nodes import ASTNode
from linum.semantic.types import Type

@dataclass
class BioSynthesisPayloadStmt(ASTNode):
    """
    AST node translating high-level conditional logic to target DNA sequences.
    Syntax: synthesis_target <condition_reg> target_sequence <base_pairs>
    """
    condition_name: str
    target_sequence: str  # Encoded using standard IUPAC nucleotides (A, C, G, T)
    action: str           # "APOPTOSIS" | "TRANSCRIPTION_BLOCK" | "REPLICATION_HALT"

    def check_with_contract(self, ctx, flow_state, next_borrow_id, contract):
        # 1. Verify biological condition variables exist inside tracking frame
        if self.condition_name not in flow_state.ownership:
            from linum.semantic.errors import NeuroSymbolicDiagnosticError
            raise NeuroSymbolicDiagnosticError(
                message=f"Biological Mutation: Condition token '{self.condition_name}' is unmapped in molecular scope.",
                invalid_field=self.condition_name,
                available_fields=list(flow_state.ownership.keys())
            )

        # 2. Mathematically check DNA nucleotide structural integrity (Strict IUPAC Validation)
        valid_nucleotides = {'A', 'C', 'G', 'T'}
        invalid_bases = [b for b in self.target_sequence if b not in valid_nucleotides]
        if invalid_bases:
            from linum.semantic.errors import NeuroSymbolicDiagnosticError
            raise NeuroSymbolicDiagnosticError(
                message=f"Genetic Corruption: Sequence contains invalid non-IUPAC bases: {invalid_bases}.",
                invalid_field="".join(invalid_bases),
                available_fields=list(valid_nucleotides)
            )

        return flow_state, self
