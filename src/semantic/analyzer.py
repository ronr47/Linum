"""Semantic Analyzer for R2 Stage 1: Symbol resolution, type checking, and domain verification."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple, Union
from src.ast.nodes import (
    Module, StructDecl, FunctionDecl, TypeRef, Statement, Expression, LetStmt, AssignStmt, ReturnStmt, WhileStmt, IfStmt, IfExpr, CallExpr, IndexExpr, FieldExpr, CastExpr, BinaryOp, UnaryOp, Identifier, IntLiteral, ByteLiteral, BoolLiteral, ArrayRepeatExpr
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

    def analyze_module(self, mod: Module) -> None:
        """Phase 1: Register top-level struct and function declarations."""
        for decl in mod.declarations:
            if isinstance(decl, StructDecl):
                if decl.name in self.structs:
                    raise SemanticError(f"Duplicate struct declaration: {decl.name}")
                self.structs[decl.name] = decl
            elif isinstance(decl, FunctionDecl):
                if decl.name in self.functions:
                    raise SemanticError(f"Duplicate function declaration: {decl.name}")
                self.functions[decl.name] = decl

        # Phase 2: Validate struct field types
        for s_name, s_decl in self.structs.items():
            self._validate_struct(s_decl)

        # Phase 3: Validate function signatures, memory domains, and contracts
        for f_name, f_decl in self.functions.items():
            self._validate_function(f_decl)

    def _validate_type(self, t: TypeRef) -> None:
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
        # Validate return type
        if decl.return_type:
            self._validate_type(decl.return_type)

        # Validate params
        scope = SymbolTable()
        for p in decl.params:
            p_name = p[0] if isinstance(p, tuple) else getattr(p, "name", str(p))
            p_type = p[1] if isinstance(p, tuple) else getattr(p, "type", None)
            self._validate_type(p_type)
            scope.insert(Symbol(name=p_name, type_ref=p_type, is_param=True))

        # Contracts validation (pre / post)
        if hasattr(decl, "contracts") and decl.contracts:
            contract_scope = SymbolTable(parent=scope)
            if decl.return_type:
                contract_scope.insert(Symbol(name="ret", type_ref=decl.return_type))
            # Parameters and invariants are bound for contract inspection
