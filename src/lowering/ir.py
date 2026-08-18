from dataclasses import dataclass
from typing import List, Tuple, Optional, Dict
from linum.src.semantic.types import Type, OwnershipMode, PRIMITIVE_INTEGER, PRIMITIVE_BOOLEAN

@dataclass(frozen=True)
class TypedReg:
    name: str
    version: Optional[int]
    ty: Type
    ownership: OwnershipMode = OwnershipMode.COPY

    @property
    def llvm_name(self) -> str:
        if self.version is not None:
            return f"%{self.name}.{self.version}"
        if self.name.startswith('%'):
            return self.name
        return f"%{self.name}"

    @property
    def llvm_type(self) -> str:
        tname = self.ty.name.strip().lower()
        if tname in ("ptr", "raw_ptr", "pointer"):
            return "ptr"
        elif tname in ("boolean", "bool", "i1"):
            return "i1"
        elif tname in ("void",):
            return "void"
        return "i64"

class TypedIrInstruction:
    pass

@dataclass
class TypedIrPhi(TypedIrInstruction):
    result: TypedReg
    incomings: List[Tuple[str, TypedReg]]

@dataclass
class TypedIrAssign(TypedIrInstruction):
    target_reg: TypedReg
    src_reg: TypedReg

@dataclass
class TypedIrStore(TypedIrInstruction):
    dest_reg: TypedReg
    src_reg: TypedReg

@dataclass
class TypedIrLoad(TypedIrInstruction):
    target_reg: TypedReg
    src_reg: TypedReg

@dataclass
class TypedIrBinOp(TypedIrInstruction):
    target_reg: TypedReg
    left_reg: TypedReg
    right_reg: TypedReg
    op: str

@dataclass
class TypedIrPtrOffset(TypedIrInstruction):
    target_reg: TypedReg
    base_ptr: TypedReg
    offset_reg: TypedReg
    elem_type: Type = Type("i8", OwnershipMode.COPY)

@dataclass
class TypedIrPtrLoad(TypedIrInstruction):
    target_reg: TypedReg
    pointer_var: TypedReg

@dataclass
class TypedIrPtrStore(TypedIrInstruction):
    pointer_var: TypedReg
    value_reg: TypedReg

@dataclass
class TypedIrCall(TypedIrInstruction):
    target_reg: Optional[TypedReg]
    function: str
    args_regs: List[TypedReg]

@dataclass
class TypedIrDrop(TypedIrInstruction):
    var_name: TypedReg

@dataclass
class TypedIrBranch(TypedIrInstruction):
    target_label: str

@dataclass
class TypedIrCondBranch(TypedIrInstruction):
    cond_reg: TypedReg
    then_label: str
    else_label: str

@dataclass
class TypedIrReturn(TypedIrInstruction):
    val_reg: Optional[TypedReg]

@dataclass
class TypedBasicBlock:
    label: str
    phis: List[TypedIrPhi]
    instructions: List[TypedIrInstruction]
    terminator: Optional[TypedIrInstruction]

@dataclass
class TypedIrFunction:
    name: str
    entry_label: str
    blocks: Dict[str, TypedBasicBlock]
    return_type: Type
    parameters: List[TypedReg]

@dataclass
class TypedIrFieldOffset(TypedIrInstruction):
    target_reg: TypedReg
    base_ptr: TypedReg
    field_offset: int
    field_type: Type
