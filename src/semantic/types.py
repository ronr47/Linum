# linum/src/semantic/types.py
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Dict, List, Set, Tuple, Optional

class OwnershipMode(Enum):
    LINEAR = auto()
    AFFINE = auto()
    COPY = auto()

@dataclass(frozen=True)
class Type:
    name: str
    mode: OwnershipMode
    params: Tuple["Type", ...] = ()
    extra: Optional[str] = None

PRIMITIVE_BOOLEAN = Type("BOOLEAN", OwnershipMode.COPY)
PRIMITIVE_INTEGER = Type("INTEGER", OwnershipMode.COPY)

class SymbolContext:
    def __init__(self):
        self.scopes: List[Dict[str, Tuple[Type, OwnershipMode]]] = [{}]
        self.functions: Dict[str, "FunctionContract"] = {}

    def enter_scope(self) -> None:
        self.scopes.append({})

    def exit_scope(self) -> None:
        if len(self.scopes) <= 1:
            raise RuntimeError("Internal Compiler Error: Scope stack underflow.")
        self.scopes.pop()

    def bind(self, name: str, ty: Type, mode: OwnershipMode) -> None:
        if name in self.scopes[-1]:
            raise TypeError(f"Redefinition Error: Variable '{name}' already declared.")
        self.scopes[-1][name] = (ty, mode)

    def lookup(self, name: str) -> Tuple[Type, OwnershipMode]:
        for scope in reversed(self.scopes):
            if name in scope:
                return scope[name]
        raise TypeError(f"Semantic Error: Identifier '{name}' is completely unbound.")

    def register_function(self, name: str, contract: "FunctionContract") -> None:
        self.functions[name] = contract

    def lookup_function(self, name: str) -> "FunctionContract":
        if name not in self.functions:
            raise TypeError(f"Semantic Error: Function '{name}' is completely unbound.")
        return self.functions[name]

    def get_current_scope_bindings(self) -> List[str]:
        return list(self.scopes[-1].keys())

    def is_assignable(self, source: Type, target: Type) -> bool:
        return source.name == target.name and source.params == target.params and source.extra == target.extra

@dataclass(frozen=True)
class ParameterContract:
    name: str
    type: Type
    mode: OwnershipMode
    borrowed: bool = False

@dataclass(frozen=True)
class FunctionContract:
    name: str
    parameters: Tuple[ParameterContract, ...]
    return_type: Optional[Type]
    return_mode: Optional[OwnershipMode]
class RawPointerType(Type):
    def __init__(self, base_type: Type, is_mutable: bool):
        super().__init__(f'*' + ('mut ' if is_mutable else 'const ') + base_type.name, OwnershipMode.COPY)
        self.base_type = base_type
        self.is_mutable = is_mutable


class StructType(Type):
    """
    Represents a composite struct type with ordered fields and byte layouts.
    If any field is LINEAR, the struct inherits LINEAR ownership mode.
    """
    def __init__(self, name: str, fields: Dict[str, Type], mode: Optional[OwnershipMode] = None):
        field_offsets: Dict[str, int] = {}
        curr_offset = 0
        inferred_mode = OwnershipMode.COPY
        
        for fname, fty in fields.items():
            field_offsets[fname] = curr_offset
            curr_offset += 8
            if getattr(fty, "mode", OwnershipMode.COPY) == OwnershipMode.LINEAR:
                inferred_mode = OwnershipMode.LINEAR

        resolved_mode = mode if mode is not None else inferred_mode
        super().__init__(name=name, mode=resolved_mode)
        
        object.__setattr__(self, "field_types", fields)
        object.__setattr__(self, "field_offsets", field_offsets)
        object.__setattr__(self, "size_bytes", curr_offset)

    def get_field_offset(self, field_name: str) -> int:
        offsets = getattr(self, "field_offsets", {})
        if field_name not in offsets:
            raise KeyError(f"Struct '{self.name}' has no field '{field_name}'")
        return offsets[field_name]

    def get_field_type(self, field_name: str) -> Type:
        ftypes = getattr(self, "field_types", {})
        if field_name not in ftypes:
            raise KeyError(f"Struct '{self.name}' has no field '{field_name}'")
        return ftypes[field_name]