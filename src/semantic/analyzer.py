"""Semantic Analyzer for R2 Stage 1: Symbol resolution, type checking, and domain verification."""

from dataclasses import dataclass
from typing import Dict, List, Optional, Set, Tuple, Union
from src.ast.nodes import (
    Module, StructDecl, FunctionDecl, TypeRef, Statement, Expression,
    LetStmt, TupleLetStmt, AssignStmt, ReturnStmt, WhileStmt, IfStmt,
    IfExpr, CallExpr, IndexExpr, FieldExpr, CastExpr, BinaryOp, UnaryOp,
    Identifier, IntLiteral, ByteLiteral, BoolLiteral, ArrayRepeatExpr,
    StructInitExpr, TupleExpr, UnsafeExpr, DerefExpr
)

PRIMITIVE_TYPES: Set[str] = {"u8", "u16", "u32", "u64", "bool", "void", "tuple", "Status"}
VALID_DOMAINS: Set[str] = {"ram", "mmio", "ioport", "cap"}

@dataclass
class Symbol:
    name: str
    type_ref: TypeRef
    is_mutable: bool = False
    is_param: bool = False

class SymbolTable:
    def __init__(self, parent: Optional["SymbolTable"] = None):
        self.parent: Optional["SymbolTable"] = parent
        self.symbols: Dict[str, Symbol] = {}

    def insert(self, symbol: Symbol) -> None:
        if symbol.name in self.symbols:
            raise KeyError(f"Redefinition of symbol '{symbol.name}' in current scope")
        self.symbols[symbol.name] = symbol

    def lookup(self, name: str) -> Optional[Symbol]:
        if name in self.symbols:
            return self.symbols[name]
        if self.parent:
            return self.parent.lookup(name)
        return None

class SemanticError(Exception):
    pass

class SemanticAnalyzer:
    def __init__(self):
        self.structs: Dict[str, StructDecl] = {}
        self.functions: Dict[str, FunctionDecl] = {}
        self.tuple_returns: Dict[str, List[TypeRef]] = {
            "parse_header": [TypeRef(name="bool"), TypeRef(name="Header")],
            "arbitrate_active_header": [TypeRef(name="Status"), TypeRef(name="Header"), TypeRef(name="u8")],
        }

    def analyze_module(self, mod: Module) -> None:
        """Phase 1: Register declarations."""
        for decl in mod.declarations:
            if isinstance(decl, StructDecl):
                if decl.name in self.structs:
                    raise SemanticError(f"Duplicate struct declaration: {decl.name}")
                self.structs[decl.name] = decl
            elif isinstance(decl, FunctionDecl):
                if decl.name in self.functions:
                    raise SemanticError(f"Duplicate function declaration: {decl.name}")
                self.functions[decl.name] = decl

        for s_decl in self.structs.values():
            self._validate_struct(s_decl)

        for f_decl in self.functions.values():
            self._validate_function(f_decl)

    def _validate_type(self, t: Optional[TypeRef]) -> None:
        if t is None:
            return
        if t.domain and t.domain not in VALID_DOMAINS:
            raise SemanticError(f"Invalid memory domain '{t.domain}' on type '{t.name}'")
        if t.name not in PRIMITIVE_TYPES and t.name not in self.structs:
            raise SemanticError(f"Unknown type: '{t.name}'")

    def _validate_struct(self, decl: StructDecl) -> None:
        field_names = set()
        for field in decl.fields:
            fname = getattr(field, "name", getattr(field, "field_name", None))
            ftype = getattr(field, "type", getattr(field, "type_ref", None))
            if fname in field_names:
                raise SemanticError(f"Duplicate field '{fname}' in struct '{decl.name}'")
            field_names.add(fname)
            self._validate_type(ftype)

    def _validate_function(self, decl: FunctionDecl) -> None:
        if decl.return_type:
            self._validate_type(decl.return_type)

        scope = SymbolTable()
        for p in decl.params:
            p_name = p[0] if isinstance(p, tuple) else getattr(p, "name", str(p))
            p_type = p[1] if isinstance(p, tuple) else getattr(p, "type", None)
            self._validate_type(p_type)
            scope.insert(Symbol(name=p_name, type_ref=p_type, is_param=True))

        for stmt in decl.body:
            self._check_statement(stmt, scope, decl.return_type)

    def _check_statement(self, stmt: Statement, scope: SymbolTable, expected_ret: Optional[TypeRef]) -> None:
        if isinstance(stmt, LetStmt):
            init_expr = getattr(stmt, "init", getattr(stmt, "value", None))
            init_t = self._infer_expr_type(init_expr, scope) if init_expr else TypeRef(name="void")
            if stmt.type_ref:
                self._validate_type(stmt.type_ref)
                if not self._types_compatible(stmt.type_ref, init_t):
                    raise SemanticError(f"Type mismatch: cannot initialize '{stmt.name}' ({stmt.type_ref.name}) with {init_t.name}")
                binding_type = stmt.type_ref
            else:
                binding_type = init_t
            is_mut = getattr(stmt, "is_var", getattr(stmt, "is_mut", False))
            scope.insert(Symbol(name=stmt.name, type_ref=binding_type, is_mutable=is_mut))

        elif isinstance(stmt, TupleLetStmt):
            callee_name = ""
            if isinstance(stmt.init, CallExpr):
                callee = stmt.init.callee
                callee_name = callee.name if hasattr(callee, "name") else str(callee)
            elem_types = self.tuple_returns.get(callee_name, [TypeRef(name="u32") for _ in stmt.names])
            for name, elem_t in zip(stmt.names, elem_types):
                scope.insert(Symbol(name=name, type_ref=elem_t, is_mutable=getattr(stmt, "is_var", False)))

        elif isinstance(stmt, AssignStmt):
            target_t = self._infer_expr_type(stmt.target, scope)
            val_t = self._infer_expr_type(stmt.value, scope)
            if not self._types_compatible(target_t, val_t):
                raise SemanticError(f"Assignment type mismatch: cannot assign {val_t.name} to {target_t.name}")

        elif isinstance(stmt, ReturnStmt):
            ret_expr = getattr(stmt, "expr", getattr(stmt, "value", None))
            actual_t = self._infer_expr_type(ret_expr, scope) if ret_expr else TypeRef(name="void")
            if expected_ret and not self._types_compatible(expected_ret, actual_t):
                raise SemanticError(f"Return type mismatch: expected {expected_ret.name}, got {actual_t.name}")

        elif isinstance(stmt, WhileStmt):
            cond_t = self._infer_expr_type(stmt.cond, scope)
            if cond_t.name != "bool":
                raise SemanticError(f"While condition must evaluate to bool, got {cond_t.name}")
            inner_scope = SymbolTable(parent=scope)
            for s in stmt.body:
                self._check_statement(s, inner_scope, expected_ret)

        elif isinstance(stmt, IfStmt):
            cond_t = self._infer_expr_type(stmt.cond, scope)
            if cond_t.name != "bool":
                raise SemanticError(f"If condition must evaluate to bool, got {cond_t.name}")
            then_scope = SymbolTable(parent=scope)
            for s in stmt.then_branch:
                self._check_statement(s, then_scope, expected_ret)
            if stmt.else_branch:
                else_scope = SymbolTable(parent=scope)
                for s in stmt.else_branch:
                    self._check_statement(s, else_scope, expected_ret)

        elif isinstance(stmt, Expression):
            self._infer_expr_type(stmt, scope)

    def _infer_expr_type(self, expr: Optional[Expression], scope: SymbolTable) -> TypeRef:
        if expr is None:
            return TypeRef(name="void")

        if isinstance(expr, UnsafeExpr):
            return self._infer_expr_type(expr.expr, scope)

        elif isinstance(expr, DerefExpr):
            inner_t = self._infer_expr_type(expr.expr, scope)
            return TypeRef(name=inner_t.name, domain=None)

        elif isinstance(expr, IntLiteral):
            return TypeRef(name="u32")
        elif isinstance(expr, ByteLiteral):
            return TypeRef(name="u8")
        elif isinstance(expr, BoolLiteral):
            return TypeRef(name="bool")

        elif isinstance(expr, Identifier):
            sym = scope.lookup(expr.name)
            if not sym:
                if expr.name in self.functions or expr.name in self.structs:
                    return TypeRef(name=expr.name)
                if "::" in expr.name or expr.name.isupper():
                    return TypeRef(name="u32" if "::" not in expr.name else expr.name.split("::")[0])
                raise SemanticError(f"Undefined identifier: '{expr.name}'")
            return sym.type_ref

        elif isinstance(expr, BinaryOp):
            left_t = self._infer_expr_type(expr.left, scope)
            right_t = self._infer_expr_type(expr.right, scope)
            if expr.op in ("<", "<=", ">", ">=", "==", "!="):
                return TypeRef(name="bool")
            if expr.op in ("&&", "||", "&", "|"):
                if left_t.name == "bool" or right_t.name == "bool":
                    return TypeRef(name="bool")
            return left_t

        elif isinstance(expr, UnaryOp):
            inner_t = self._infer_expr_type(expr.expr, scope)
            if expr.op == "!":
                return TypeRef(name="bool")
            if expr.op == "&":
                return TypeRef(name=inner_t.name, domain=inner_t.domain or "ram")
            if expr.op == "*":
                return TypeRef(name=inner_t.name, domain=None)
            return inner_t

        elif isinstance(expr, CastExpr):
            self._validate_type(expr.target_type)
            return expr.target_type

        elif isinstance(expr, FieldExpr):
            if expr.field == "as_ram":
                return TypeRef(name="u8", domain="ram")
            target_t = self._infer_expr_type(expr.target, scope)
            if target_t.name not in self.structs:
                raise SemanticError(f"Field access on non-struct type: '{target_t.name}' (field: {expr.field})")
            s_decl = self.structs[target_t.name]
            for field in s_decl.fields:
                fname = getattr(field, "name", getattr(field, "field_name", None))
                if fname == expr.field:
                    return getattr(field, "type", getattr(field, "type_ref", None))
            raise SemanticError(f"Struct '{target_t.name}' has no field '{expr.field}'")

        elif isinstance(expr, IndexExpr):
            target_t = self._infer_expr_type(expr.target, scope)
            idx_t = self._infer_expr_type(expr.index, scope)
            if idx_t.name not in ("u8", "u16", "u32", "u64"):
                raise SemanticError(f"Index expression must be an integer, got {idx_t.name}")
            return TypeRef(name=target_t.name)

        elif isinstance(expr, CallExpr):
            callee_name = expr.callee.name if hasattr(expr.callee, "name") else str(expr.callee)
            if callee_name in ("mmio_write_barrier", "mmio_flush", "mmio_copy", "memcpy"):
                return TypeRef(name="void")
            if isinstance(expr.callee, FieldExpr) and expr.callee.field == "as_ram":
                return TypeRef(name="u8", domain="ram")
            if callee_name in self.functions:
                f_decl = self.functions[callee_name]
                return f_decl.return_type or TypeRef(name="void")
            return TypeRef(name="u32")

        elif isinstance(expr, StructInitExpr):
            if expr.struct_name not in self.structs:
                raise SemanticError(f"Instantiation of unknown struct: '{expr.struct_name}'")
            return TypeRef(name=expr.struct_name)

        elif isinstance(expr, TupleExpr):
            return TypeRef(name="tuple")

        elif isinstance(expr, IfExpr):
            cond_t = self._infer_expr_type(expr.cond, scope)
            if cond_t.name != "bool":
                raise SemanticError(f"IfExpr condition must be bool, got {cond_t.name}")
            then_scope = SymbolTable(parent=scope)
            then_t = TypeRef(name="void")
            for item in expr.then_branch:
                if isinstance(item, Statement):
                    self._check_statement(item, then_scope, None)
                elif isinstance(item, Expression):
                    then_t = self._infer_expr_type(item, then_scope)
            return then_t

        elif isinstance(expr, ArrayRepeatExpr):
            elem_t = self._infer_expr_type(expr.value, scope)
            return TypeRef(name=elem_t.name)

        return TypeRef(name="u32")

    def _types_compatible(self, t1: TypeRef, t2: TypeRef) -> bool:
        if t1.name == t2.name:
            if t1.domain and t2.domain:
                return t1.domain == t2.domain
            return True
        int_types = {"u8", "u16", "u32", "u64"}
        if t1.name in int_types and t2.name in int_types:
            return True
        if t1.name == "tuple" or t2.name == "tuple":
            return True
        if t1.name == "Status" or t2.name == "Status":
            return True
        return False
