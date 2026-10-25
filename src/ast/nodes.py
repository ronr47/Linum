"""AST node definitions for R2 Core."""

from dataclasses import dataclass
from typing import List, Optional, Any


@dataclass
class TypeRef:
    name: str
    domain: Optional[str] = None  # 'ram', 'mmio', 'ioport', 'cap'
    is_array: bool = False
    array_size: Optional[int] = None


@dataclass
class Expression:
    pass


@dataclass
class IntLiteral(Expression):
    value: int


@dataclass
class ByteLiteral(Expression):
    value: int


@dataclass
class BoolLiteral(Expression):
    value: bool


@dataclass
class Identifier(Expression):
    name: str


@dataclass
class BinaryOp(Expression):
    left: Expression
    op: str
    right: Expression


@dataclass
class UnaryOp(Expression):
    op: str
    expr: Expression


@dataclass
class CastExpr(Expression):
    expr: Expression
    target_type: TypeRef


@dataclass
class CallExpr(Expression):
    callee: str
    args: List[Expression]


@dataclass
class IndexExpr(Expression):
    target: Expression
    index: Expression


@dataclass
class FieldExpr(Expression):
    target: Expression
    field: str


@dataclass
class Statement:
    pass


@dataclass
class LetStmt(Statement):
    name: str
    type_ref: Optional[TypeRef]
    init: Expression
    is_var: bool = False


@dataclass
class AssignStmt(Statement):
    target: Expression
    value: Expression


@dataclass
class WhileStmt(Statement):
    cond: Expression
    body: List[Statement]


@dataclass
class IfStmt(Statement):
    cond: Expression
    then_branch: List[Statement]
    else_branch: Optional[List[Statement]] = None


@dataclass
class ReturnStmt(Statement):
    expr: Optional[Expression]


@dataclass
class Contract:
    kind: str  # 'pre', 'post', 'preserves'
    expr: Any


@dataclass
class FunctionDecl:
    name: str
    params: List[tuple[str, TypeRef]]
    return_type: Optional[TypeRef]
    contracts: List[Contract]
    body: List[Statement]


@dataclass
class StructField:
    name: str
    type_ref: TypeRef


@dataclass
class StructDecl:
    name: str
    fields: List[StructField]
    is_packed: bool = False


@dataclass
class Module:
    name: str
    declarations: List[Any]
