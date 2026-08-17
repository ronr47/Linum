# linum/src/lowering/ssa.py
from dataclasses import dataclass, field
from typing import Dict, List, Set, Tuple, Optional
from linum.src.lowering.cfg import IrInstruction, IrAlloca, IrParam, IrLoad, IrStore, IrCall, IrDrop, IrBranch, IrCondBranch, IrReturn, BasicBlock, CfgFunction

@dataclass(frozen=True)
class SsaValue:
    name: str
    version: int
    def spill(self) -> str:
        return f"%{self.name}.{self.version}" if self.version >= 0 else f"%{self.name}"

@dataclass(frozen=True)
class SsaPhi:
    result: SsaValue
    incomings: Tuple[Tuple[str, SsaValue], ...]

@dataclass
class SsaBlock:
    label: str
    phis: List[SsaPhi] = field(default_factory=list)
    instructions: List[IrInstruction] = field(default_factory=list)
    terminator: Optional[IrInstruction] = None

@dataclass
class SsaFunction:
    name: str
    entry_block: str
    blocks: Dict[str, SsaBlock]

class DominanceEngine:
    def __init__(self, cfg: CfgFunction):
        self.cfg = cfg
        self.doms: Dict[str, Set[str]] = {}
        self.idoms: Dict[str, Optional[str]] = {}
        self.tree: Dict[str, Set[str]] = {lbl: set() for lbl in cfg.blocks}
        self.frontiers: Dict[str, Set[str]] = {lbl: set() for lbl in cfg.blocks}
        self._compute_dominators()
        self._compute_immediate_dominators()
        self._compute_dominance_frontiers()
    def _compute_dominators(self) -> None:
        all_labels = set(self.cfg.blocks.keys())
        entry = self.cfg.entry_block
        self.doms = {lbl: set(all_labels) for lbl in all_labels}
        self.doms[entry] = {entry}
        changed = True
        while changed:
            changed = False
            for lbl in all_labels:
                if lbl == entry: continue
                preds = self.cfg.predecessors.get(lbl, set())
                if not preds: intersected = {lbl}
                else:
                    p_list = list(preds)
                    intersected = set(self.doms[p_list[0]])
                    for p in p_list[1:]: intersected.intersection_update(self.doms[p])
                    intersected.add(lbl)
                if intersected != self.doms[lbl]:
                    self.doms[lbl] = intersected
                    changed = True
    def _compute_immediate_dominators(self) -> None:
        for lbl in self.cfg.blocks:
            if lbl == self.cfg.entry_block: continue
            strict_doms = self.doms[lbl] - {lbl}
            for d in strict_doms:
                if all(d not in (self.doms[other] - {other}) for other in strict_doms if other != d):
                    self.idoms[lbl] = d
                    self.tree[d].add(lbl)
                    break
    def _compute_dominance_frontiers(self) -> None:
        for lbl, bb in self.cfg.blocks.items():
            preds = self.cfg.predecessors.get(lbl, set())
            if len(preds) >= 2:
                for p in preds:
                    runner = p
                    while runner != self.idoms[lbl]:
                        self.frontiers[runner].add(lbl)
                        runner = self.idoms[runner]

class SsaConverter:
    def __init__(self, cfg: CfgFunction, var_types: Dict[str, str]):
        self.cfg = cfg
        self.cfg.compute_topology()
        self.dom_engine = DominanceEngine(cfg)
        self.var_types = var_types
        self.variables: Set[str] = set(var_types.keys())
        self.def_blocks: Dict[str, Set[str]] = {v: set() for v in self.variables}
        self._analyze_defs()
        self.phi_placements: Dict[str, Set[str]] = {lbl: set() for lbl in cfg.blocks}
        self._place_phis()
        self.ssa_blocks: Dict[str, SsaBlock] = {lbl: SsaBlock(lbl) for lbl in cfg.blocks}
        self.counter: Dict[str, int] = {v: 0 for v in self.variables}
        self.stack: Dict[str, List[SsaValue]] = {v: [SsaValue(v, -1)] for v in self.variables}
        self.phi_placeholders: Dict[str, Dict[str, SsaValue]] = {lbl: {} for lbl in cfg.blocks}
        self.phi_incoming_accumulators: Dict[str, Dict[str, List[Tuple[str, SsaValue]]]] = {lbl: {v: [] for v in self.variables} for lbl in cfg.blocks}
    def _analyze_defs(self) -> None:
        for lbl, bb in self.cfg.blocks.items():
            for instr in bb.instructions:
                if isinstance(instr, IrStore) and instr.dest_var in self.variables: self.def_blocks[instr.dest_var].add(lbl)
    def _place_phis(self) -> None:
        for var in self.variables:
            w = list(self.def_blocks[var])
            added: Set[str] = set()
            while w:
                x = w.pop(0)
                for y in self.dom_engine.frontiers[x]:
                    if y not in added:
                        self.phi_placements[y].add(var)
                        added.add(y)
                        if y not in self.def_blocks[var]: w.append(y)
    def convert(self) -> SsaFunction:
        self._rename(self.cfg.entry_block)
        for lbl, ssa_bb in self.ssa_blocks.items():
            for var in sorted(self.phi_placements[lbl]):
                res_val = self.phi_placeholders[lbl][var]
                incomings = tuple(self.phi_incoming_accumulators[lbl][var])
                ssa_bb.phis.append(SsaPhi(result=res_val, incomings=incomings))
        return SsaFunction(name=self.cfg.name, entry_block=self.cfg.entry_block, blocks=self.ssa_blocks)
    def _rename(self, lbl: str) -> None:
        ssa_bb = self.ssa_blocks[lbl]
        src_bb = self.cfg.blocks[lbl]
        pushed_count: Dict[str, int] = {v: 0 for v in self.variables}
        for var in sorted(self.phi_placements[lbl]):
            self.counter[var] += 1
            nv = SsaValue(var, self.counter[var])
            self.stack[var].append(nv)
            self.phi_placeholders[lbl][var] = nv
            pushed_count[var] += 1
        for instr in src_bb.instructions:
            if isinstance(instr, IrAlloca) and instr.var_name in self.variables: continue
            elif isinstance(instr, IrStore) and instr.dest_var in self.variables:
                self.counter[instr.dest_var] += 1
                nv = SsaValue(instr.dest_var, self.counter[instr.dest_var])
                self.stack[instr.dest_var].append(nv)
                pushed_count[instr.dest_var] += 1
                ssa_bb.instructions.append(IrStore(instr.src_reg, nv.spill()))
            elif isinstance(instr, IrLoad) and instr.src_var in self.variables:
                curr_val = self.stack[instr.src_var][-1]
                ssa_bb.instructions.append(IrLoad(instr.target_reg, curr_val.spill()))
            else:
                if instr == src_bb.terminator: ssa_bb.terminator = instr
                ssa_bb.instructions.append(instr)
        for succ in sorted(self.cfg.successors.get(lbl, set())):
            for var in sorted(self.phi_placements[succ]):
                curr_val = self.stack[var][-1]
                self.phi_incoming_accumulators[succ][var].append((lbl, curr_val))
        for child in sorted(self.dom_engine.tree[lbl]): self._rename(child)
        for var, count in pushed_count.items():
            for _ in range(count): self.stack[var].pop()

class SsaVerifier:
    @staticmethod
    def verify(func: SsaFunction, var_types: Dict[str, str]) -> None:
        defined_values: Set[str] = set()
        for lbl, bb in func.blocks.items():
            for phi in bb.phis:
                if phi.result.spill() in defined_values: raise ValueError(f"SSA Integrity Defect: Duplicate register {phi.result.spill()}")
                defined_values.add(phi.result.spill())
            for instr in bb.instructions:
                if isinstance(instr, IrStore) and "." in instr.dest_var:
                    if instr.dest_var in defined_values: raise ValueError(f"SSA Integrity Defect: Multiply-defined register {instr.dest_var}")
                    defined_values.add(instr.dest_var)
        for lbl, bb in func.blocks.items():
            for phi in bb.phis:
                for pred_lbl, src_val in phi.incomings:
                    if pred_lbl not in func.blocks: raise ValueError(f"SSA Block Link Defect: Predecessor block '{pred_lbl}' vanished.")
                    if src_val.version >= 0 and src_val.spill() not in defined_values: raise ValueError(f"SSA Use-Before-Def Defect inside PHI incoming: Unbound trace {src_val.spill()}")
            for instr in bb.instructions:
                if isinstance(instr, IrLoad) and "." in instr.src_var:
                    if instr.src_var not in defined_values: raise ValueError(f"SSA Use-Before-Def Defect: Unbound use trace {instr.src_var}")
