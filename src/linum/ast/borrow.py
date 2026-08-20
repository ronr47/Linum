from dataclasses import dataclass
from linum.ast.nodes import ASTNode

@dataclass
class BorrowStmt(ASTNode):
    """
    AST representation of a reference validation barrier matching Linum contract execution semantics.
    """
    ref_name: str
    mode: str  # 'SHARED' | 'EXCLUSIVE'
    source: ASTNode
    body: ASTNode

    def check_with_contract(self, ctx, flow_state, next_borrow_id, contract):
        # 1. Evaluate context type requirements
        source_type = self.source.check_type(ctx)
        
        # 2. Trigger validation tracking boundary inside SymbolContext
        ctx.push_borrow_scope(self.ref_name, self.source, self.mode)
        
        try:
            # 3. Propagate down the internal flow state checking mechanics
            final_flow, sem_body = self.body.check_with_contract(
                ctx, 
                flow_state, 
                next_borrow_id, 
                contract
            )
        finally:
            ctx.pop_borrow_scope(self.ref_name)
            
        return final_flow, sem_body
