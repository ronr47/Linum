"""R2 Intermediate Representation (R2-IR) Data Structures and Instruction Set."""

from dataclasses import dataclass, field
from typing import List, Optional, Union

# Value operands
@dataclass
class Reg:
    name: str

    def __repr__(self) -> str:
        return f"%{self.name}"

@dataclass
class Const:
    value: int
    bit_width: int = 32

    def __repr__(self) -> str:
        return f"${self.value}"

Operand = Union[Reg, Const]

# IR Instructions
class Instruction:
    pass

@dataclass
class Assign(Instruction):
    dest: Reg
    src: Operand

    def __repr__(self) -> str:
        return f"{self.dest} = {self.src}"

@dataclass
class BinOp(Instruction):
    dest: Reg
    op: str
    left: Operand
    right: Operand

    def __repr__(self) -> str:
        return f"{self.dest} = {self.left} {self.op} {self.right}"

@dataclass
class UnOp(Instruction):
    dest: Reg
    op: str
    src: Operand

    def __repr__(self) -> str:
        return f"{self.dest} = {self.op}{self.src}"

@dataclass
class RamLoad(Instruction):
    dest: Reg
    addr: Operand
    offset: int = 0

    def __repr__(self) -> str:
        return f"{self.dest} = load.ram [{self.addr} + {self.offset}]"

@dataclass
class RamStore(Instruction):
    addr: Operand
    src: Operand
    offset: int = 0

    def __repr__(self) -> str:
        return f"store.ram [{self.addr} + {self.offset}], {self.src}"

@dataclass
class MmioLoad(Instruction):
    dest: Reg
    addr: Operand
    offset: int = 0

    def __repr__(self) -> str:
        return f"{self.dest} = load.mmio [{self.addr} + {self.offset}]"

@dataclass
class MmioStore(Instruction):
    addr: Operand
    src: Operand
    offset: int = 0

    def __repr__(self) -> str:
        return f"store.mmio [{self.addr} + {self.offset}], {self.src}"

@dataclass
class MmioBarrier(Instruction):
    kind: str = "write"

    def __repr__(self) -> str:
        return f"barrier.mmio {self.kind}"

@dataclass
class Call(Instruction):
    dest: Optional[Reg]
    callee: str
    args: List[Operand]

    def __repr__(self) -> str:
        args_str = ", ".join(str(a) for a in self.args)
        if self.dest:
            return f"{self.dest} = call @{self.callee}({args_str})"
        return f"call @{self.callee}({args_str})"

@dataclass
class Jump(Instruction):
    target: str

    def __repr__(self) -> str:
        return f"jump bb_{self.target}"

@dataclass
class BranchIf(Instruction):
    cond: Operand
    true_target: str
    false_target: str

    def __repr__(self) -> str:
        return f"br {self.cond}, bb_{self.true_target}, bb_{self.false_target}"

@dataclass
class Return(Instruction):
    val: Optional[Operand] = None

    def __repr__(self) -> str:
        return f"ret {self.val}" if self.val is not None else "ret"

@dataclass
class Assert(Instruction):
    cond: Operand
    msg: str = ""

    def __repr__(self) -> str:
        return f"assert {self.cond} ; {self.msg}"

# Basic block & Function containers
@dataclass
class BasicBlock:
    label: str
    instructions: List[Instruction] = field(default_factory=list)

    def append(self, inst: Instruction) -> None:
        self.instructions.append(inst)

@dataclass
class IRFunction:
    name: str
    params: List[Reg]
    blocks: List[BasicBlock] = field(default_factory=list)

@dataclass
class IRModule:
    name: str
    functions: List[IRFunction] = field(default_factory=list)
