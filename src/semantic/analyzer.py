# linum/src/semantic/analyzer.py
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Dict, List, Set, Tuple, Optional
from linum.src.semantic.types import Type, OwnershipMode, FunctionContract, SymbolContext

class OwnerState(Enum):
    UNINITIALIZED = auto()
    OWNED = auto()
    MOVED = auto()
    DEAD = auto()

@dataclass(frozen=True)
class BorrowCapability:
    id: int
    source: str
    alias: str

@dataclass(frozen=True)
class DropAction:
    name: str
    type: Type

@dataclass
class FlowState:
    ownership: Dict[str, OwnerState] = field(default_factory=dict)
    active_borrows: Dict[str, Set[BorrowCapability]] = field(default_factory=dict)
    drops: List[DropAction] = field(default_factory=list)
    has_returned: bool = False

    def clone(self) -> "FlowState":
        return FlowState(
            ownership=dict(self.ownership),
            active_borrows={k: set(v) for k, v in self.active_borrows.items()},
            drops=list(self.drops),
            has_returned=self.has_returned
        )

    def strict_lattice_join(self, other: "FlowState", ctx: "SymbolContext") -> "FlowState":
        if self.has_returned and not other.has_returned:
            return other.clone()
        if other.has_returned and not self.has_returned:
            return self.clone()
        if self.has_returned and other.has_returned:
            res = self.clone()
            return res

        merged_ownership: Dict[str, OwnerState] = {}
        all_keys = set(self.ownership.keys()) | set(other.ownership.keys())

        for k in all_keys:
            s_state = self.ownership.get(k, OwnerState.UNINITIALIZED)
            o_state = other.ownership.get(k, OwnerState.UNINITIALIZED)

            if s_state != o_state:
                # Retrieve variable ownership mode from context if available
                try:
                    _, mode = ctx.lookup(k)
                except Exception:
                    mode = None

                if mode != OwnershipMode.COPY:
                    raise TypeError(
                        f"Asymmetric Branch Ownership Divergence: Variable '{k}' "
                        f"has inconsistent ownership states across control-flow branches "
                        f"({s_state.name} vs {o_state.name})."
                    )
            merged_ownership[k] = s_state

        merged_borrows: Dict[str, Set[BorrowCapability]] = {}
        for k in set(self.active_borrows.keys()) | set(other.active_borrows.keys()):
            s_b = self.active_borrows.get(k, set())
            o_b = other.active_borrows.get(k, set())
            merged_borrows[k] = set(s_b | o_b)

        return FlowState(
            ownership=merged_ownership,
            active_borrows=merged_borrows,
            drops=list(self.drops) + [d for d in other.drops if d not in self.drops],
            has_returned=False
        )

def strict_lattice_join(mode: OwnershipMode, left: OwnerState, right: OwnerState) -> OwnerState:
    if mode == OwnershipMode.COPY: return OwnerState.OWNED
    if mode == OwnershipMode.LINEAR:
        if left != right: raise TypeError(f"Linear Convergence Invariant Violated: {left.name} != {right.name}")
        return left
    if mode == OwnershipMode.AFFINE:
        if left == right: return left
        return OwnerState.MOVED if OwnerState.MOVED in (left, right) else OwnerState.DEAD
    raise TypeError(f"Unknown ownership mode: {mode}")

def join_borrows(name: str, left: Set[BorrowCapability], right: Set[BorrowCapability]) -> Set[BorrowCapability]:
    if left != right: raise TypeError(f"Borrow Convergence Invariant Violated on '{name}'")
    return set(left)

class SemanticNode: pass
@dataclass(frozen=True)
class SemIdentifierExpr(SemanticNode): name: str; type: Type
@dataclass(frozen=True)
class SemConsumeExpr(SemanticNode): source: str; type: Type

@dataclass(frozen=True)
class SemPtrOffsetExpr(SemanticNode):
    base_ptr: SemanticNode
    offset: SemanticNode
    type: Type
@dataclass(frozen=True)
class SemCallArg(SemanticNode): expr: SemanticNode; mode: OwnershipMode; borrowed: bool; source_name: Optional[str]
@dataclass(frozen=True)
class SemCallExpr(SemanticNode): function: str; arguments: Tuple[SemCallArg, ...]; result_type: Optional[Type]
@dataclass(frozen=True)
class SemLetStmt(SemanticNode): name: str; type: Type; expr: SemanticNode
@dataclass(frozen=True)
class SemMoveStmt(SemanticNode): source: str; destination: str; type: Type
@dataclass(frozen=True)
class SemAssignStmt(SemanticNode): target: str; expr: SemanticNode
@dataclass(frozen=True)
class SemExprStmt(SemanticNode): expr: SemanticNode
@dataclass(frozen=True)
class SemReturnStmt(SemanticNode): expr: Optional[SemanticNode]; scope_drops_at_return: Tuple[DropAction, ...]
@dataclass(frozen=True)
class SemBlockStmt(SemanticNode): statements: List[SemanticNode]; local_drops: List[DropAction]
@dataclass(frozen=True)
class SemBorrowBlockStmt(SemanticNode): source: str; borrow_alias: str; capability_id: Optional[int]; body: SemBlockStmt
@dataclass(frozen=True)
class SemIfStmt(SemanticNode): condition: SemanticNode; then_block: SemBlockStmt; else_block: SemBlockStmt; then_drops: List[DropAction]; else_drops: List[DropAction]
@dataclass(frozen=True)
class SemFunctionDecl(SemanticNode): contract: FunctionContract; body: SemBlockStmt
