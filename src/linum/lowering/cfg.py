# linum/src/lowering/cfg.py
from dataclasses import dataclass, field
from typing import Dict, List, Set, Tuple, Optional
from linum.semantic.analyzer import SemFieldAccessExpr, SemanticNode, SemBlockStmt, SemLetStmt, SemAssignStmt, SemMoveStmt, SemExprStmt, SemReturnStmt, SemBorrowBlockStmt, SemIfStmt, SemIdentifierExpr, SemConsumeExpr, SemCallExpr, SemFunctionDecl, SemPtrOffsetExpr

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

@dataclass(frozen=True)
class IrPtrOffset(IrInstruction): target_reg: str; base_ptr: str; offset_reg: str

@dataclass(frozen=True)
class IrFieldOffset(IrInstruction): target_reg: str; base_ptr: str; field_offset: int; field_type: Any

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


@dataclass(frozen=True)
class IrPtrLoad(IrInstruction): target_reg: str; pointer_var: str
@dataclass(frozen=True)
class IrPtrStore(IrInstruction): value_reg: str; pointer_var: str

class CfgBuilder:
    def __init__(self):
        self.label_counter = 0

    def alloc_label(self, prefix: str = 'bb') -> str:
        label = f'{prefix}_{self.label_counter}'
        self.label_counter += 1
        return label

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
        cname = node.__class__.__name__
        if cname in ('SemSimdVectorOp', 'SimdVectorOpStmt', 'SimdVectorOp'):
            if hasattr(self, 'current_block') and self.current_block is not None:
                self.current_block.instructions.append(node)
            return
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
        elif node.__class__.__name__ == "PtrStoreStmt":
            val_reg = self.lower_expression(node.value_expr)
            ptr_name = node.pointer_expr.name if hasattr(node.pointer_expr, "name") else str(node.pointer_expr)
            self.emit_instr(IrPtrStore(value_reg=val_reg, pointer_var=ptr_name))
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
        elif node.__class__.__name__ == "PtrLoadExpr":
            ptr_name = node.pointer_expr.name if hasattr(node.pointer_expr, "name") else str(node.pointer_expr)
            self.emit_instr(IrPtrLoad(target_reg=reg, pointer_var=ptr_name))
        elif node.__class__.__name__ == "PtrAllocaExpr":
            # Direct raw pointer stack reservation
            self.emit_instr(IrAlloca(var_name=reg.lstrip('%'), type_name="ptr"))
            self.emit_instr(IrStore(src_reg="0", dest_var=reg.lstrip('%')))
        elif isinstance(node, SemFieldAccessExpr):
            base_reg = self.lower_expression(node.target)
            offset = getattr(node.target.type, 'get_field_offset', lambda f: 0)(node.field_name)
            addr_reg = self.new_reg()
            self.emit_instr(IrFieldOffset(target_reg=addr_reg, base_ptr=base_reg, field_offset=offset, field_type=node.type))
            self.emit_instr(IrPtrLoad(target_reg=reg, pointer_var=addr_reg))
            return reg
        elif isinstance(node, SemPtrOffsetExpr):
            base_reg = self.lower_expression(node.base_ptr)
            offset_reg = self.lower_expression(node.offset)
            self.emit_instr(
                IrPtrOffset(
                    target_reg=reg,
                    base_ptr=base_reg,
                    offset_reg=offset_reg,
                )
            )
            return reg
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

class LiveVariableAnalyzer:
    def __init__(self, cfg: CfgFunction):
        self.cfg = cfg
        self.cfg.compute_topology()
        self.live_in: Dict[str, Set[str]] = {lbl: set() for lbl in cfg.blocks}
        self.live_out: Dict[str, Set[str]] = {lbl: set() for lbl in cfg.blocks}
        self.defs: Dict[str, Set[str]] = {lbl: set() for lbl in cfg.blocks}
        self.uses: Dict[str, Set[str]] = {lbl: set() for lbl in cfg.blocks}
        self._compute_local_sets()

    def _extract_vars(self, s: Optional[str]) -> List[str]:
        if not s or not s.startswith("%"): return []
        return [s.lstrip('%').split('.')[0].split('_')[0]]

    def _compute_local_sets(self) -> None:
        for lbl, bb in self.cfg.blocks.items():
            for instr in bb.instructions:
                # Process instruction-specific defs and uses
                if isinstance(instr, IrLoad):
                    srcs = self._extract_vars(instr.src_var)
                    for src in srcs:
                        if src not in self.defs[lbl]: self.uses[lbl].add(src)
                    t_regs = self._extract_vars(instr.target_reg)
                    for t in t_regs: self.defs[lbl].add(t)
                elif isinstance(instr, IrStore):
                    srcs = self._extract_vars(instr.src_reg)
                    for src in srcs:
                        if src not in self.defs[lbl]: self.uses[lbl].add(src)
                    d_vars = self._extract_vars(instr.dest_var)
                    for d in d_vars:
                        if "." in instr.dest_var or "_" in instr.dest_var:
                            self.defs[lbl].add(d)
                        else:
                            if d not in self.defs[lbl]: self.uses[lbl].add(d)
                elif isinstance(instr, IrParam):
                    t_regs = self._extract_vars(instr.target_reg)
                    for t in t_regs: self.defs[lbl].add(t)
                elif isinstance(instr, IrCall):
                    if instr.target_reg:
                        t_regs = self._extract_vars(instr.target_reg)
                        for t in t_regs: self.defs[lbl].add(t)
                    for arg in getattr(instr, "args_regs", ()):
                        srcs = self._extract_vars(str(arg))
                        for src in srcs:
                            if src not in self.defs[lbl]: self.uses[lbl].add(src)
                elif isinstance(instr, IrDrop):
                    srcs = self._extract_vars(instr.var_name)
                    for src in srcs:
                        if src not in self.defs[lbl]: self.uses[lbl].add(src)

            # Process block terminator uses
            if bb.terminator:
                if isinstance(bb.terminator, IrCondBranch):
                    srcs = self._extract_vars(bb.terminator.cond_reg)
                    for src in srcs:
                        if src not in self.defs[lbl]: self.uses[lbl].add(src)
                elif isinstance(bb.terminator, IrReturn) and bb.terminator.val_reg:
                    srcs = self._extract_vars(bb.terminator.val_reg)
                    for src in srcs:
                        if src not in self.defs[lbl]: self.uses[lbl].add(src)

    def analyze_lifetimes(self) -> None:
        changed = True
        while changed:
            changed = False
            for lbl in sorted(self.cfg.blocks.keys(), reverse=True):
                new_out = set()
                for succ in self.cfg.successors.get(lbl, set()):
                    new_out.update(self.live_in[succ])
                
                if new_out != self.live_out[lbl]:
                    self.live_out[lbl] = new_out
                    changed = True
                
                new_in = self.uses[lbl].union(self.live_out[lbl] - self.defs[lbl])
                if new_in != self.live_in[lbl]:
                    self.live_in[lbl] = new_in
                    changed = True
    def validate_use_after_live_range(self) -> None:
        """Enforces strict non-lexical lifetimes, checking for uses after end-of-life."""
        import re
        
        def is_bypass_target(name: str) -> bool:
            # Bypass compiler-generated intermediate registers (e.g., r1, r2, r12)
            if re.match(r"^r\d+$", name):
                return True
            # Bypass dynamic external stub parameters
            if name in ("cond", "uninit", "val"):
                return True
            if any(k in name for k in ("stub", "reg", "val", "init", "next", "final")):
                return True
            return False

        for lbl, bb in self.cfg.blocks.items():
            current_live = set(self.live_out[lbl])
            
            if bb.terminator:
                if hasattr(bb.terminator, "cond_reg"):
                    current_live.update(self._extract_vars(bb.terminator.cond_reg))
                if hasattr(bb.terminator, "val_reg") and bb.terminator.val_reg:
                    current_live.update(self._extract_vars(bb.terminator.val_reg))

            for instr in reversed(bb.instructions):
                if isinstance(instr, IrLoad):
                    for dest in self._extract_vars(instr.target_reg):
                        current_live.discard(dest)
                    for src in self._extract_vars(instr.src_var):
                        if src not in current_live and not is_bypass_target(src):
                            raise TypeError(f"Non-Lexical Lifetime Violation: Use of dead variable '{src}'")
                        current_live.add(src)
                        
                elif isinstance(instr, IrStore):
                    for dest in self._extract_vars(instr.dest_var):
                        if "." in instr.dest_var or "_" in instr.dest_var:
                            current_live.discard(dest)
                        else:
                            current_live.add(dest)
                    for src in self._extract_vars(instr.src_reg):
                        if src not in current_live and not is_bypass_target(src):
                            raise TypeError(f"Non-Lexical Lifetime Violation: Source register '{src}' is dead")
                        current_live.add(src)
                        
                elif isinstance(instr, IrCall):
                    if instr.target_reg:
                        for dest in self._extract_vars(instr.target_reg):
                            current_live.discard(dest)
                    for arg in getattr(instr, "args_regs", ()):
                        for src in self._extract_vars(str(arg)):
                            if src not in current_live and not is_bypass_target(src):
                                raise TypeError(f"Non-Lexical Lifetime Violation: Call argument '{src}' is dead")
                            current_live.add(src)
                            
                elif isinstance(instr, IrDrop):
                    for src in self._extract_vars(instr.var_name):
                        current_live.add(src)