# linum/src/lowering/cfg.py
from dataclasses import dataclass, field
from typing import Dict, List, Set, Tuple, Optional
from linum.src.semantic.analyzer import SemanticNode, SemBlockStmt, SemLetStmt, SemAssignStmt, SemMoveStmt, SemExprStmt, SemReturnStmt, SemBorrowBlockStmt, SemIfStmt, SemIdentifierExpr, SemConsumeExpr, SemCallExpr, SemFunctionDecl

class IrInstruction: pass
@dataclass(frozen=True)
class IrAlloca(IrInstruction): var_name: str; type_name: str
@dataclass(frozen=True)
class IrParam(IrInstruction): target_reg: str; param_name: str; type_name: str
@dataclass(frozen=True)
class IrLoad(IrInstruction): target_reg: str; src_var: str
@dataclass(frozen=True)
class IrStore(IrInstruction): src_reg: str; dest_var: str
@dataclass(frozen=True)
class IrCall(IrInstruction): target_reg: Optional[str]; function: str; args_regs: Tuple[str, ...]
@dataclass(frozen=True)
class IrDrop(IrInstruction): var_name: str; type_name: str
@dataclass(frozen=True)
class IrBranch(IrInstruction): target_label: str
@dataclass(frozen=True)
class IrCondBranch(IrInstruction): cond_reg: str; then_label: str; else_label: str
@dataclass(frozen=True)
class IrReturn(IrInstruction): val_reg: Optional[str]

class BasicBlock:
    def __init__(self, label: str):
        self.label: str = label
        self.instructions: List[IrInstruction] = []
        self.terminator: Optional[IrInstruction] = None
    def emit(self, instr: IrInstruction) -> None:
        if self.terminator is not None: raise RuntimeError(f"CFG Integrity Failure after terminator in block '{self.label}'")
        if isinstance(instr, (IrBranch, IrCondBranch, IrReturn)): self.terminator = instr
        self.instructions.append(instr)

@dataclass
class CfgFunction:
    name: str
    entry_block: str
    blocks: Dict[str, BasicBlock]
    successors: Dict[str, Set[str]] = field(default_factory=dict)
    predecessors: Dict[str, Set[str]] = field(default_factory=dict)
    def compute_topology(self) -> None:
        self.successors = {lbl: set() for lbl in self.blocks}
        self.predecessors = {lbl: set() for lbl in self.blocks}
        for lbl, bb in self.blocks.items():
            if isinstance(bb.terminator, IrBranch):
                self.successors[lbl].add(bb.terminator.target_label)
                self.predecessors[bb.terminator.target_label].add(lbl)
            elif isinstance(bb.terminator, IrCondBranch):
                self.successors[lbl].add(bb.terminator.then_label)
                self.successors[lbl].add(bb.terminator.else_label)
                self.predecessors[bb.terminator.then_label].add(lbl)
                self.predecessors[bb.terminator.else_label].add(lbl)

class CfgBuilder:
    def __init__(self):
        self.blocks: Dict[str, BasicBlock] = {}
        self.current_bb: Optional[BasicBlock] = None
        self.bb_counter = 0
        self.reg_counter = 0
    def new_label(self, prefix: str) -> str:
        self.bb_counter += 1
        return f"{prefix}_{self.bb_counter}"
    def new_reg(self) -> str:
        self.reg_counter += 1
        return f"%r{self.reg_counter}"
    def emit_block(self, label: str) -> BasicBlock:
        bb = BasicBlock(label)
        self.blocks[label] = bb
        self.current_bb = bb
        return bb
    def emit_instr(self, instr: IrInstruction) -> None:
        if self.current_bb is None: raise RuntimeError("CFG Builder State Malfunction: Out of bounds instruction emission.")
        self.current_bb.emit(instr)
    def lower_function(self, sem_decl: SemFunctionDecl) -> CfgFunction:
        self.blocks.clear()
        self.bb_counter = 0
        self.reg_counter = 0
        entry_label = f"entry_{sem_decl.contract.name}"
        self.emit_block(entry_label)
        for param in sem_decl.contract.parameters:
            self.emit_instr(IrAlloca(param.name, param.type.name))
            arg_reg = self.new_reg()
            self.emit_instr(IrParam(arg_reg, param.name, param.type.name))
            self.emit_instr(IrStore(arg_reg, param.name))
        self.lower_statement(sem_decl.body, [])
        return CfgFunction(name=sem_decl.contract.name, entry_block=entry_label, blocks=dict(self.blocks))
    def lower_statement(self, node: SemanticNode, merge_stack: List[str]) -> None:
        if self.current_bb is not None and self.current_bb.terminator is not None: return
        if isinstance(node, SemBlockStmt):
            for stmt in node.statements:
                self.lower_statement(stmt, merge_stack)
                if self.current_bb is not None and self.current_bb.terminator is not None: return
            for drop in node.local_drops: self.emit_instr(IrDrop(drop.name, drop.type.name))
        elif isinstance(node, SemLetStmt):
            expr_reg = self.lower_expression(node.expr)
            self.emit_instr(IrAlloca(node.name, node.type.name))
            self.emit_instr(IrStore(expr_reg, node.name))
        elif isinstance(node, SemAssignStmt):
            expr_reg = self.lower_expression(node.expr)
            self.emit_instr(IrStore(expr_reg, node.target))
        elif isinstance(node, SemMoveStmt):
            tmp_reg = self.new_reg()
            self.emit_instr(IrLoad(tmp_reg, node.source))
            self.emit_instr(IrStore(tmp_reg, node.destination))
        elif isinstance(node, SemExprStmt): self.lower_expression(node.expr)
        elif isinstance(node, SemReturnStmt):
            ret_reg = self.lower_expression(node.expr) if node.expr is not None else None
            for drop in node.scope_drops_at_return: self.emit_instr(IrDrop(drop.name, drop.type.name))
            self.emit_instr(IrReturn(ret_reg))
        elif isinstance(node, SemBorrowBlockStmt):
            self.emit_instr(IrAlloca(node.borrow_alias, "REFERENCE"))
            tmp_reg = self.new_reg()
            self.emit_instr(IrLoad(tmp_reg, node.source))
            self.emit_instr(IrStore(tmp_reg, node.borrow_alias))
            self.lower_statement(node.body, merge_stack)
        elif isinstance(node, SemIfStmt):
            cond_reg = self.lower_expression(node.condition)
            then_label = self.new_label("then")
            else_label = self.new_label("else")
            merge_label = self.new_label("if_merge")
            self.emit_instr(IrCondBranch(cond_reg, then_label, else_label))
            self.emit_block(then_label)
            self.lower_statement(node.then_block, merge_stack + [merge_label])
            then_has_term = self.current_bb.terminator is not None
            if not then_has_term:
                for drop in node.then_drops: self.emit_instr(IrDrop(drop.name, drop.type.name))
                self.emit_instr(IrBranch(merge_label))
            self.emit_block(else_label)
            self.lower_statement(node.else_block, merge_stack + [merge_label])
            else_has_term = self.current_bb.terminator is not None
            if not else_has_term:
                for drop in node.else_drops: self.emit_instr(IrDrop(drop.name, drop.type.name))
                self.emit_instr(IrBranch(merge_label))
            if not (then_has_term and else_has_term): self.emit_block(merge_label)
    def lower_expression(self, node: SemanticNode) -> str:
        reg = self.new_reg()
        if isinstance(node, SemIdentifierExpr): self.emit_instr(IrLoad(reg, node.name))
        elif isinstance(node, SemConsumeExpr): self.emit_instr(IrLoad(reg, node.source))
        elif isinstance(node, SemCallExpr):
            arg_regs = [self.lower_expression(arg.expr) for arg in node.arguments]
            target_reg = reg if node.result_type is not None else None
            self.emit_instr(IrCall(target_reg, node.function, tuple(arg_regs)))
            if target_reg is None: return ""
        return reg

class CfgVerifier:
    @staticmethod
    def verify(blocks: Dict[str, BasicBlock]) -> None:
        if not blocks: raise ValueError("CFG Verification Failed: Graph contains no blocks.")
        for label, bb in blocks.items():
            if not bb.instructions: raise ValueError(f"CFG Verification Failed: Block '{label}' has zero instructions.")
            if bb.terminator is None: raise ValueError(f"CFG Verification Failed: Block '{label}' is missing a terminator.")
            term_count = sum(1 for inst in bb.instructions if isinstance(inst, (IrBranch, IrCondBranch, IrReturn)))
            if term_count > 1: raise ValueError(f"CFG Verification Failed: Block '{label}' has multiple terminators ({term_count}).")
            if bb.instructions[-1] != bb.terminator: raise ValueError(f"CFG Verification Failed: Instructions found after terminator in block '{label}'.")
            if isinstance(bb.terminator, IrBranch):
                if bb.terminator.target_label not in blocks: raise ValueError(f"CFG Verification Failed: Block '{label}' targets non-existent block '{bb.terminator.target_label}'.")
            elif isinstance(bb.terminator, IrCondBranch):
                if bb.terminator.then_label not in blocks: raise ValueError(f"CFG Verification Failed: Block '{label}' targets non-existent then label '{bb.terminator.then_label}'.")
                if bb.terminator.else_label not in blocks: raise ValueError(f"CFG Verification Failed: Block '{label}' targets non-existent else label '{bb.terminator.else_label}'.")
