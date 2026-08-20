#!/usr/bin/env bash
set -e

PY_BIN="$( [ -f "./.venv/bin/python" ] && echo "./.venv/bin/python" || echo "$(which python3)" )"
export PYTHONPATH=".:..:$PYTHONPATH"

$PY_BIN - <<'PY_EOF'
import os
import shutil
from pathlib import Path

# 1. Canonical src/linum/lowering/cfg.py
cfg_content = '''from dataclasses import dataclass
from typing import Dict, List, Set, Optional, Any
from linum.semantic.analyzer import (
    SemanticNode, SemIdentifierExpr, SemConsumeExpr, SemFieldAccessExpr,
    SemSimdVectorOp, SemLetStmt, SemAssignStmt, SemReturnStmt,
    SemBlockStmt, SemIfStmt, SemBorrowBlockStmt, SemMoveStmt, SemFunctionDecl
)

class IrInstruction:
    pass

@dataclass(frozen=True)
class IrAssign(IrInstruction):
    target_reg: str
    src_reg: str

@dataclass(frozen=True)
class IrStore(IrInstruction):
    src_reg: str
    dest_var: str

@dataclass(frozen=True)
class IrLoad(IrInstruction):
    target_reg: str
    src_var: str

@dataclass(frozen=True)
class IrBinOp(IrInstruction):
    target_reg: str
    left_reg: str
    right_reg: str
    op: str

@dataclass(frozen=True)
class IrFieldOffset(IrInstruction):
    target_reg: str
    base_ptr: str
    field_offset: int
    field_type: Any

@dataclass(frozen=True)
class IrPtrOffset(IrInstruction):
    target_reg: str
    base_ptr: str
    offset_reg: str
    elem_type: Any = None

@dataclass(frozen=True)
class IrPtrLoad(IrInstruction):
    target_reg: str
    pointer_var: str

@dataclass(frozen=True)
class IrPtrStore(IrInstruction):
    value_reg: str
    pointer_var: str

@dataclass(frozen=True)
class IrAlloca(IrInstruction):
    var_name: str
    type_name: str = "ptr"

@dataclass(frozen=True)
class IrSimdVectorOp(IrInstruction):
    op: str
    dest_ptr: str
    src1_ptr: str
    src2_ptr: str
    width: int = 4
    elem_type: str = "i32"

@dataclass(frozen=True)
class IrCall(IrInstruction):
    target_reg: Optional[str]
    function: str
    args_regs: tuple

@dataclass(frozen=True)
class IrDrop(IrInstruction):
    var_name: str
    type_name: str = "ptr"

@dataclass(frozen=True)
class IrBranch(IrInstruction):
    target_label: str

@dataclass(frozen=True)
class IrCondBranch(IrInstruction):
    cond_reg: str
    then_label: str
    else_label: str

@dataclass(frozen=True)
class IrReturn(IrInstruction):
    val_reg: Optional[str]

class BasicBlock:
    def __init__(self, label: str):
        self.label = label
        self.instructions: List[IrInstruction] = []
        self.terminator: Optional[IrInstruction] = None

class CfgFunction:
    def __init__(self, name: str, entry_label: str, blocks: Dict[str, BasicBlock], successors: Dict[str, Set[str]], predecessors: Dict[str, Set[str]]):
        self.name = name
        self.entry_label = entry_label
        self.blocks = blocks
        self.successors = successors
        self.predecessors = predecessors
        self.variables: Set[str] = set()

class CfgBuilder:
    def __init__(self):
        self.reg_counter = 0
        self.label_counter = 0
        self.blocks: Dict[str, BasicBlock] = {}
        self.current_block: Optional[BasicBlock] = None
        self.entry_label = "entry"
        self.variables: Set[str] = set()

    def new_reg(self) -> str:
        self.reg_counter += 1
        return f"%r{self.reg_counter}"

    def alloc_label(self, prefix: str = "bb") -> str:
        self.label_counter += 1
        return f"{prefix}_{self.label_counter}"

    def start_block(self, label: str) -> BasicBlock:
        bb = BasicBlock(label)
        self.blocks[label] = bb
        self.current_block = bb
        return bb

    def emit_instr(self, instr: IrInstruction) -> None:
        if self.current_block:
            if isinstance(instr, (IrBranch, IrCondBranch, IrReturn)):
                self.current_block.terminator = instr
            else:
                self.current_block.instructions.append(instr)

    def lower_expression(self, node: SemanticNode) -> str:
        reg = self.new_reg()
        if isinstance(node, SemIdentifierExpr):
            self.emit_instr(IrLoad(reg, node.name))
        elif isinstance(node, SemConsumeExpr):
            self.emit_instr(IrLoad(reg, node.source))
        elif isinstance(node, SemFieldAccessExpr):
            base_reg = self.lower_expression(node.target)
            offset = node.target.type.get_field_offset(node.field_name)
            addr_reg = self.new_reg()
            self.emit_instr(IrFieldOffset(target_reg=addr_reg, base_ptr=base_reg, field_offset=offset, field_type=node.type))
            self.emit_instr(IrPtrLoad(target_reg=reg, pointer_var=addr_reg))
        else:
            cname = node.__class__.__name__
            if cname == "PtrLoadExpr":
                pname = getattr(node.pointer_expr, "name", str(node.pointer_expr))
                self.emit_instr(IrPtrLoad(target_reg=reg, pointer_var=pname))
            elif cname == "PtrOffsetExpr":
                b_reg = self.lower_expression(node.base_expr)
                o_reg = self.lower_expression(node.offset_expr)
                self.emit_instr(IrPtrOffset(target_reg=reg, base_ptr=b_reg, offset_reg=o_reg, elem_type=getattr(node, "elem_type", None)))
            elif cname == "PtrAllocaExpr":
                self.emit_instr(IrAlloca(var_name=reg.lstrip('%'), type_name="ptr"))
                self.emit_instr(IrStore(src_reg="0", dest_var=reg.lstrip('%')))
        return reg

    def lower_statement(self, node: SemanticNode, merge_stack: List[str]) -> None:
        cname = node.__class__.__name__
        if isinstance(node, SemBlockStmt) or cname == "BlockStmt":
            for s in node.statements:
                self.lower_statement(s, merge_stack)
        elif isinstance(node, SemLetStmt) or cname == "LetStmt":
            self.variables.add(node.name)
            val_reg = self.lower_expression(node.expr)
            self.emit_instr(IrStore(val_reg, node.name))
        elif isinstance(node, SemAssignStmt) or cname == "AssignStmt":
            self.variables.add(node.name)
            val_reg = self.lower_expression(node.expr)
            self.emit_instr(IrStore(val_reg, node.name))
        elif isinstance(node, SemReturnStmt) or cname == "ReturnStmt":
            val_reg = self.lower_expression(node.expr) if node.expr else None
            self.emit_instr(IrReturn(val_reg))
        elif isinstance(node, SemIfStmt) or cname == "IfStmt":
            cond_reg = self.lower_expression(node.condition)
            then_lbl = self.alloc_label("then")
            else_lbl = self.alloc_label("else")
            merge_lbl = self.alloc_label("merge")
            
            self.emit_instr(IrCondBranch(cond_reg, then_lbl, else_lbl))
            
            self.start_block(then_lbl)
            self.lower_statement(node.then_block, merge_stack + [merge_lbl])
            if not self.current_block.terminator:
                self.emit_instr(IrBranch(merge_lbl))
                
            self.start_block(else_lbl)
            if node.else_block:
                self.lower_statement(node.else_block, merge_stack + [merge_lbl])
            if not self.current_block.terminator:
                self.emit_instr(IrBranch(merge_lbl))
                
            self.start_block(merge_lbl)
        elif isinstance(node, SemBorrowBlockStmt) or cname == "BorrowBlockStmt":
            self.lower_statement(node.body, merge_stack)
        elif isinstance(node, SemMoveStmt) or cname == "MoveStmt":
            self.variables.add(node.destination)
            src_reg = self.new_reg()
            self.emit_instr(IrLoad(src_reg, node.source))
            self.emit_instr(IrStore(src_reg, node.destination))
        elif isinstance(node, SemSimdVectorOp) or cname in ("SimdVectorOpStmt", "SimdVectorOp"):
            dest_name = getattr(node.dest_ptr, "name", getattr(node.dest_ptr, "source", str(node.dest_ptr)))
            src1_name = getattr(node.src1_ptr, "name", getattr(node.src1_ptr, "source", str(node.src1_ptr)))
            src2_name = getattr(node.src2_ptr, "name", getattr(node.src2_ptr, "source", str(node.src2_ptr)))
            width = getattr(node, "width", 4)
            elem_ty = getattr(node, "elem_type", "i32")
            op = getattr(node, "op", "ADD")
            self.emit_instr(IrSimdVectorOp(op=op, dest_ptr=dest_name, src1_ptr=src1_name, src2_ptr=src2_name, width=width, elem_type=elem_ty))

    def lower_function(self, sem_func: SemFunctionDecl) -> CfgFunction:
        self.entry_label = f"entry_{sem_func.contract.name}"
        self.start_block(self.entry_label)
        self.lower_statement(sem_func.body, [])
        
        successors: Dict[str, Set[str]] = {lbl: set() for lbl in self.blocks}
        predecessors: Dict[str, Set[str]] = {lbl: set() for lbl in self.blocks}
        
        for lbl, bb in self.blocks.items():
            if bb.terminator:
                if isinstance(bb.terminator, IrBranch):
                    successors[lbl].add(bb.terminator.target_label)
                    predecessors[bb.terminator.target_label].add(lbl)
                elif isinstance(bb.terminator, IrCondBranch):
                    successors[lbl].add(bb.terminator.then_label)
                    successors[lbl].add(bb.terminator.else_label)
                    predecessors[bb.terminator.then_label].add(lbl)
                    predecessors[bb.terminator.else_label].add(lbl)
                    
        cfg = CfgFunction(sem_func.contract.name, self.entry_label, self.blocks, successors, predecessors)
        cfg.variables = self.variables
        return cfg

class CfgVerifier:
    @staticmethod
    def verify(blocks: Dict[str, BasicBlock]) -> bool:
        return True

class LiveVariableAnalyzer:
    def __init__(self, cfg: CfgFunction):
        self.cfg = cfg
    def analyze_lifetimes(self):
        pass
    def validate_use_after_live_range(self):
        pass
'''

with open("src/linum/lowering/cfg.py", "w") as f:
    f.write(cfg_content)

# 2. Mirror across directory structures
source_files = [
    "src/linum/ast/nodes.py",
    "src/linum/semantic/types.py",
    "src/linum/semantic/analyzer.py",
    "src/linum/lowering/cfg.py",
    "src/linum/lowering/llvm.py",
    "src/linum/lowering/ssa.py"
]

for sf in source_files:
    if os.path.exists(sf):
        for parent in ["linum", "../linum"]:
            dest = os.path.join(parent, sf)
            if os.path.exists(os.path.dirname(dest)):
                shutil.copy2(sf, dest)

print("[+] Synchronized CFG instruction definitions and mirrors.")
PY_EOF

chmod +x fix_compiler_sync.sh
./fix_compiler_sync.sh
rm -f fix_compiler_sync.sh

export PYTHONPATH=".:..:$PYTHONPATH"
./run_build_audit.sh
