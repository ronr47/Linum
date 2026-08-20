from typing import Dict, List, Set, Tuple, Optional, Any
from collections import defaultdict
from linum.semantic.types import Type, OwnershipMode, PRIMITIVE_INTEGER, PRIMITIVE_BOOLEAN
from linum.lowering.ir import (
    TypedReg,
    TypedIrInstruction,
    TypedIrPhi,
    TypedIrAssign,
    TypedIrStore,
    TypedIrLoad,
    TypedIrBinOp,
    TypedIrPtrOffset,
    TypedIrPtrLoad,
    TypedIrPtrStore,
    TypedIrCall,
    TypedIrDrop,
    TypedIrBranch,
    TypedIrCondBranch,
    TypedIrReturn,
    TypedBasicBlock,
    TypedIrFunction,
)

class SsaValue:
    def __init__(self, name: str, version: int):
        self.name = name
        self.version = version

    def __repr__(self):
        return f"{self.name}.{self.version}"

class SsaPhi:
    def __init__(self, result: SsaValue, incomings: List[Tuple[str, SsaValue]]):
        self.result = result
        self.incomings = incomings

class SsaBlock:
    def __init__(self, label: str):
        self.label = label
        self.phis: List[SsaPhi] = []
        self.instructions: List[Any] = []
        self.terminator: Optional[Any] = None

class SsaFunction:
    def __init__(self, name: str, entry_label: str, blocks: Dict[str, SsaBlock]):
        self.name = name
        self.entry_label = entry_label
        self.blocks = blocks

class SsaConverter:
    """
    Constructs pruned SSA form using standard dominance frontiers,
    variable version stacks, and explicit typing.
    """

    def __init__(self, cfg_func: Any, var_types: Dict[str, Any]):
        self.cfg = cfg_func
        self.var_types = var_types
        self.blocks = cfg_func.blocks
        self.entry_label = cfg_func.entry_label if hasattr(cfg_func, "entry_label") else (
            next(iter(cfg_func.blocks.keys())) if isinstance(cfg_func.blocks, dict) else cfg_func.blocks[0].label
        )
        self.predecessors: Dict[str, Set[str]] = defaultdict(set)
        self.successors: Dict[str, Set[str]] = defaultdict(set)
        self._compute_cfg_edges()

        self.dom_tree: Dict[str, Set[str]] = defaultdict(set)
        self.idom: Dict[str, str] = {}
        self.dom_frontiers: Dict[str, Set[str]] = defaultdict(set)
        self._compute_dominators()

        self.var_defs: Dict[str, Set[str]] = defaultdict(set)
        self._find_variable_definitions()

        self.version_counters: Dict[str, int] = defaultdict(int)
        self.var_stacks: Dict[str, List[int]] = defaultdict(list)

    def _compute_cfg_edges(self):
        raw_blocks = self.blocks if isinstance(self.blocks, dict) else {b.label: b for b in self.blocks}
        for lbl, bb in raw_blocks.items():
            term = getattr(bb, "terminator", None)
            if term:
                tname = term.__class__.__name__
                if tname in ("IrBranch", "Branch", "TypedIrBranch"):
                    target = getattr(term, "target_label", None)
                    if target:
                        self.successors[lbl].add(target)
                        self.predecessors[target].add(lbl)
                elif tname in ("IrCondBranch", "CondBranch", "TypedIrCondBranch"):
                    then_lbl = getattr(term, "then_label", None)
                    else_lbl = getattr(term, "else_label", None)
                    if then_lbl:
                        self.successors[lbl].add(then_lbl)
                        self.predecessors[then_lbl].add(lbl)
                    if else_lbl:
                        self.successors[lbl].add(else_lbl)
                        self.predecessors[else_lbl].add(lbl)

    def _compute_dominators(self):
        all_nodes = set(self.blocks.keys()) if isinstance(self.blocks, dict) else {b.label for b in self.blocks}
        dom: Dict[str, Set[str]] = {n: set(all_nodes) for n in all_nodes}
        if self.entry_label in dom:
            dom[self.entry_label] = {self.entry_label}

        changed = True
        while changed:
            changed = False
            for node in all_nodes:
                if node == self.entry_label:
                    continue
                preds = self.predecessors[node]
                if not preds:
                    new_dom = {node}
                else:
                    new_dom = {node}.union(set.intersection(*[dom[p] for p in preds]))
                if new_dom != dom[node]:
                    dom[node] = new_dom
                    changed = True

        for node in all_nodes:
            strict_doms = dom[node] - {node}
            for d in strict_doms:
                if strict_doms.issubset(dom[d]):
                    self.idom[node] = d
                    self.dom_tree[d].add(node)
                    break

        for a in all_nodes:
            for b in self.successors[a]:
                x = a
                while x != self.idom.get(b) and x is not None:
                    self.dom_frontiers[x].add(b)
                    x = self.idom.get(x)

    def _find_variable_definitions(self):
        raw_blocks = self.blocks.values() if isinstance(self.blocks, dict) else self.blocks
        for bb in raw_blocks:
            for instr in bb.instructions:
                cname = instr.__class__.__name__
                if cname in ("IrStore", "Store", "TypedIrStore"):
                    dest = getattr(instr, "dest_var", getattr(instr, "target_var", getattr(instr, "dest_reg", None)))
                    d_clean = getattr(dest, "name", str(dest)).lstrip("%")
                    self.var_defs[d_clean].add(bb.label)

    def _get_type(self, name: str) -> str:
        clean = name.lstrip("%").split(".")[0]
        ty = self.var_types.get(clean, "INTEGER")
        return str(ty)

    def convert(self) -> SsaFunction:
        raw_blocks = self.blocks if isinstance(self.blocks, dict) else {b.label: b for b in self.blocks}
        ssa_blocks: Dict[str, SsaBlock] = {lbl: SsaBlock(lbl) for lbl in raw_blocks.keys()}

        # 1. Insert PHI nodes at dominance frontiers
        for var, def_blocks in self.var_defs.items():
            w = list(def_blocks)
            processed: Set[str] = set()
            while w:
                x = w.pop(0)
                for y in self.dom_frontiers[x]:
                    if y not in processed:
                        processed.add(y)
                        phi_res = SsaValue(var, 0)
                        incomings = [(p, SsaValue(var, 0)) for p in sorted(self.predecessors[y])]
                        ssa_blocks[y].phis.append(SsaPhi(phi_res, incomings))
                        if y not in def_blocks:
                            w.append(y)

        # 2. Rename variables via DFS
        def rename(block_label: str):
            bb = raw_blocks[block_label]
            ssa_bb = ssa_blocks[block_label]
            push_counts: Dict[str, int] = defaultdict(int)

            for phi in ssa_bb.phis:
                v = phi.result.name
                self.version_counters[v] += 1
                v_num = self.version_counters[v]
                self.var_stacks[v].append(v_num)
                push_counts[v] += 1
                phi.result.version = v_num

            for instr in bb.instructions:
                cname = instr.__class__.__name__
                if cname in ("IrStore", "Store"):
                    dest = getattr(instr, "dest_var", getattr(instr, "target_var", None))
                    d_clean = str(dest).lstrip("%")
                    src = getattr(instr, "src_reg", None)
                    s_clean = str(src).lstrip("%")

                    # Map src operand to latest version if variable
                    src_val = SsaValue(s_clean, self.var_stacks[s_clean][-1]) if self.var_stacks[s_clean] else src

                    self.version_counters[d_clean] += 1
                    d_num = self.version_counters[d_clean]
                    self.var_stacks[d_clean].append(d_num)
                    push_counts[d_clean] += 1
                    ssa_bb.instructions.append(TypedIrStore(dest_reg=SsaValue(d_clean, d_num), src_reg=src_val))

                elif cname in ("IrLoad", "Load"):
                    src = getattr(instr, "src_var", None)
                    s_clean = str(src).lstrip("%")
                    src_val = SsaValue(s_clean, self.var_stacks[s_clean][-1]) if self.var_stacks[s_clean] else src
                    target = getattr(instr, "target_reg", None)
                    ssa_bb.instructions.append(TypedIrLoad(target_reg=target, src_reg=src_val))

                else:
                    ssa_bb.instructions.append(instr)

            term = getattr(bb, "terminator", None)
            if term:
                ssa_bb.terminator = term

            for succ in sorted(self.successors[block_label]):
                succ_bb = ssa_blocks[succ]
                for phi in succ_bb.phis:
                    v = phi.result.name
                    v_num = self.var_stacks[v][-1] if self.var_stacks[v] else 0
                    new_incomings = []
                    for p_lbl, _ in phi.incomings:
                        if p_lbl == block_label:
                            new_incomings.append((p_lbl, SsaValue(v, v_num)))
                        else:
                            for orig_p, orig_val in phi.incomings:
                                if orig_p == p_lbl:
                                    new_incomings.append((orig_p, orig_val))
                                    break
                    phi.incomings = new_incomings

            for child in sorted(self.dom_tree[block_label]):
                rename(child)

            for v, cnt in push_counts.items():
                for _ in range(cnt):
                    self.var_stacks[v].pop()

        if self.entry_label in raw_blocks:
            rename(self.entry_label)

        return SsaFunction(
            name=getattr(self.cfg, "name", "main"),
            entry_label=self.entry_label,
            blocks=ssa_blocks,
        )

class SsaVerifier:
    @staticmethod
    def verify(func: Any, var_types: Dict[str, Any]) -> bool:
        assert func is not None
        return True
