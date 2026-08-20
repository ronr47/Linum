import copy

# --- 1. Foundational Semantic States & Capabilities ---
class ResourceState:
    BOUND = "BOUND"
    MOVED = "MOVED"
    DROPPED = "DROPPED"

from src.semantic.types import OwnershipMode

class FlowState:
    LINEAR = OwnershipMode.LINEAR
    AFFINE = OwnershipMode.AFFINE
    COPY = OwnershipMode.COPY
    
    def __init__(self, default_mode=OwnershipMode.LINEAR):
        self.has_returned = False
        self.active_borrows = {}
        self.mode = default_mode
        self.bindings = {}
        # Core property map utilized by the AST validator to trace resource flags
        self.ownership = {}
        self.drops = []

    def clone(self):
        """Duplicates the flow state and tracking contexts across compilation forks."""
        cloned = FlowState(self.mode)
        cloned.bindings = copy.deepcopy(self.bindings)
        cloned.ownership = copy.deepcopy(self.ownership)
        cloned.drops = copy.deepcopy(self.drops)

        # BorrowCapability instances are identity-bearing semantic resources.
        # Clone the mapping/sets, but preserve the capability objects themselves.
        # Deep-copying them breaks nested-borrow lifetime restoration because an
        # outer capability becomes a different object after an inner flow clone.
        cloned.active_borrows = {
            name: set(borrows)
            for name, borrows in self.active_borrows.items()
        }

        cloned.has_returned = self.has_returned
        return cloned

class OwnerState:
    MOVED = 'MOVED'
    DEAD = 'DEAD'
    UNINITIALIZED = 'UNINITIALIZED'
    OWNED = "OWNED"
    BORROWED_MUT = "BORROWED_MUT"
    BORROWED_IMM = "BORROWED_IMM"
    INVALIDATED = "INVALIDATED"
    
    def __init__(self, default_state="OWNED"):
        self.state = default_state

    def clone(self):
        """Duplicates the ownership tracker state context."""
        cloned = OwnerState(self.state)
        return cloned

class BorrowCapability:
    IMMUTABLE = "IMMUTABLE"
    MUTABLE = "MUTABLE"
    EXCLUSIVE = "EXCLUSIVE"
    
    def __init__(
        self,
        name=None,
        lifetime=None,
        mutable=False,
    ):
        self.name = name
        self.lifetime = lifetime
        self.mutable = mutable
        self.capability = (
            self.MUTABLE if mutable else self.IMMUTABLE
        )

class DropAction:
    AUTO_FREE = "AUTO_FREE"
    EXPLICIT = "EXPLICIT"
    LEAK_OK = "LEAK_OK"

# --- 2. Base & Structural Semantic Nodes ---
class SemanticNode:
    """Base class for all semantically validated AST elements."""
    def __init__(self, node_type=None):
        self.node_type = node_type

class SemFunctionDecl(SemanticNode):
    """Analyzed function declaration node with validated type contracts."""
    def __init__(self, contract, body):
        super().__init__(node_type="FunctionDecl")
        self.contract = contract
        self.body = body

# --- 3. Semantic Expression Nodes ---
class SemIdentifierExpr(SemanticNode):
    def __init__(self, name: str, node_type=None):
        super().__init__(node_type=node_type)
        self.name = name

class SemConsumeExpr(SemanticNode):
    def __init__(self, target, node_type=None):
        super().__init__(node_type=node_type)
        self.target = target

class SemCallArg(SemanticNode):
    def __init__(
        self,
        expression,
        evaluation_mode,
        node_type=None,
        ownership=None,
    ):
        super().__init__(node_type=node_type)
        self.expression = expression
        self.evaluation_mode = evaluation_mode
        self.ownership = ownership

class SemCallExpr(SemanticNode):
    def __init__(self, function_name, arguments, node_type=None):
        super().__init__(node_type=node_type)
        self.function_name = function_name
        self.arguments = arguments

class SemFieldAccessExpr(SemanticNode):
    def __init__(self, base, field_name, node_type=None):
        super().__init__(node_type=node_type)
        self.base = base
        self.field_name = field_name

class SemPtrOffsetExpr(SemanticNode):
    def __init__(self, base_ptr, offset_val, node_type=None):
        super().__init__(node_type=node_type)
        self.base_ptr = base_ptr
        self.offset_val = offset_val

# --- 4. Semantic Statement Nodes ---
class SemLetStmt(SemanticNode):
    def __init__(self, name, type_tag, expression):
        super().__init__(node_type="LetStmt")
        self.name = name
        self.type_tag = type_tag
        self.expression = expression
        self.expr = expression
        self.type = type_tag

class SemMoveStmt(SemanticNode):
    def __init__(self, dest, src):
        super().__init__(node_type="MoveStmt")
        self.dest = dest
        self.src = src

class SemAssignStmt(SemanticNode):
    def __init__(self, target, expression):
        super().__init__(node_type="AssignStmt")
        self.target = target
        self.expression = expression
        self.expr = expression

class SemExprStmt(SemanticNode):
    def __init__(self, expression):
        super().__init__(node_type="ExprStmt")
        self.expression = expression

class SemReturnStmt(SemanticNode):
    def __init__(self, expression, scope_drops_at_return=()):
        super().__init__(node_type="ReturnStmt")
        self.expression = expression
        self.expr = expression
        self.scope_drops_at_return = tuple(scope_drops_at_return)

class SemBlockStmt(SemanticNode):
    def __init__(self, statements, local_drops=()):
        super().__init__(node_type="BlockStmt")
        self.statements = statements
        self.local_drops = list(local_drops)

class SemBorrowBlockStmt(SemanticNode):
    def __init__(self, source, borrow_alias, capability_id, body):
        super().__init__(node_type="BorrowBlockStmt")
        self.source = source
        self.borrow_alias = borrow_alias
        self.capability_id = capability_id
        self.body = body

        # Compatibility aliases for older semantic consumers.
        self.target = source
        self.mode = capability_id

class SemIfStmt(SemanticNode):
    def __init__(
        self,
        condition,
        then_branch,
        else_branch,
        then_branch_drops=(),
        else_branch_drops=(),
    ):
        super().__init__(node_type="IfStmt")
        self.condition = condition
        self.then_branch = then_branch
        self.else_branch = else_branch
        self.then_block = then_branch
        self.else_block = else_branch
        self.then_branch_drops = list(then_branch_drops)
        self.else_branch_drops = list(else_branch_drops)
        self.then_drops = self.then_branch_drops
        self.else_drops = self.else_branch_drops

# --- 5. Type Lattice Optimization Routines ---
def strict_lattice_join(mode, left, right):
    """Join ownership states at a control-flow convergence point."""
    if left == right:
        return left

    if mode == OwnershipMode.LINEAR:
        raise TypeError(
            f"Convergence Invariant: linear ownership diverges "
            f"between {left} and {right}."
        )

    return None

def join_borrows(name, left_borrows, right_borrows):
    """Merges linear borrow allocations across control flow graphs.

    ``name`` is part of the semantic branch-join contract.  The current
    representation stores the borrow state separately from its binding
    name, so the name is accepted explicitly but does not alter the
    intersection operation.
    """
    if hasattr(left_borrows, 'intersection'):
        return left_borrows.intersection(right_borrows)
    return left_borrows

# --- 6. Linear Resource Tracking Engine ---
class SemanticLifetimeError(Exception):
    """Raised when an asset breaches linear type guarantees."""
    pass

class LinearLifetimeAnalyzer:
    def __init__(self):
        self.registry = {}

    def bind_resource(self, name: str):
        self.registry[name] = ResourceState.BOUND

    def consume_resource(self, name: str, execution_context: str = "use"):
        if name not in self.registry:
            return
            
        current_state = self.registry[name]
        
        if current_state == ResourceState.MOVED:
            raise SemanticLifetimeError(
                f"Use-after-move violation: Linear resource '{name}' was already consumed."
            )
        elif current_state == ResourceState.DROPPED:
            raise SemanticLifetimeError(
                f"Use-after-drop violation: Linear resource '{name}' has been freed."
            )
            
        if execution_context == "move":
            self.registry[name] = ResourceState.MOVED

    def enforce_no_leaks(self):
        leaked_resources = [
            name for name, state in self.registry.items() 
            if state == ResourceState.BOUND
        ]
        if leaked_resources:
            raise SemanticLifetimeError(
                f"Contract Violation: Linear variable '{leaked_resources}' is leaked"
            )
