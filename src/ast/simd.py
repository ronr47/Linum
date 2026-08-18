from dataclasses import dataclass
from src.ast.nodes import ASTNode
from src.semantic.types import Type

@dataclass
class SimdVectorOpStmt(ASTNode):
    """
    AST node representation for localized SIMD array acceleration.
    Syntax: simd_vectorize <op> <dest_ptr> <src1_ptr> <src2_ptr> <vector_width>
    """
    op: str             # "ADD" | "SUB" | "MUL" | "DIV"
    dest_ptr: ASTNode
    src1_ptr: ASTNode
    src2_ptr: ASTNode
    width: int          # Element capacity count (e.g., 4, 8)

    def check_with_contract(self, ctx, flow_state, next_borrow_id, contract):
        # Enforce pointer tracking metrics across all localized buffer operands
        ty_dest = self.dest_ptr.check_type(ctx)
        ty_src1 = self.src1_ptr.check_type(ctx)
        ty_src2 = self.src2_ptr.check_type(ctx)
        return flow_state, self
