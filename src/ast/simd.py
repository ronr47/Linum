from dataclasses import dataclass
from src.ast.nodes import ASTNode

@dataclass
class SimdVectorOpStmt(ASTNode):
    """
    AST representation for localized SIMD array acceleration.
    """
    op: str             # "ADD" | "SUB" | "MUL" | "DIV"
    dest_ptr: ASTNode
    src1_ptr: ASTNode
    src2_ptr: ASTNode
    width: int          # Element capacity count (e.g., 4, 8)

    def check_with_contract(self, ctx, flow_state, next_borrow_id, contract):
        # Validate data flows via local ownership verification matrices
        flow_state, sem_dest = self.dest_ptr.check_ownership(flow_state, ctx, next_borrow_id)
        flow_state, sem_src1 = self.src1_ptr.check_ownership(flow_state, ctx, next_borrow_id)
        flow_state, sem_src2 = self.src2_ptr.check_ownership(flow_state, ctx, next_borrow_id)
        return flow_state, self
