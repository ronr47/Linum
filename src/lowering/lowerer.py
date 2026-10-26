"""AST Lowerer: Translates checked R2 AST into linear R2-IR."""

from typing import Dict, List, Optional, Tuple
from src.ast.nodes import (
    Module, FunctionDecl, StructDecl, Statement, Expression,
    LetStmt, TupleLetStmt, AssignStmt, ReturnStmt, WhileStmt, IfStmt,
    IfExpr, CallExpr, IndexExpr, FieldExpr, CastExpr, BinaryOp, UnaryOp,
    Identifier, IntLiteral, ByteLiteral, BoolLiteral, StructInitExpr,
    DerefExpr, UnsafeExpr
)
from src.lowering.ir import (
    Reg, Const, Operand, Instruction, Assign, BinOp, UnOp,
    RamLoad, RamStore, MmioLoad, MmioStore, MmioBarrier, Call,
    Jump, BranchIf, Return, Assert, BasicBlock, IRFunction, IRModule
)

class Lowerer:
    def __init__(self):
        self.reg_counter: int = 0
        self.block_counter: int = 0
        self.structs: Dict[str, StructDecl] = {}
        self.current_function: Optional[IRFunction] = None
        self.current_bb: Optional[BasicBlock] = None
        self.var_map: Dict[str, Operand] = {}

    def new_reg(self, prefix: str = "t") -> Reg:
        self.reg_counter += 1
        return Reg(f"{prefix}{self.reg_counter}")

    def new_block(self, prefix: str = "b") -> BasicBlock:
        self.block_counter += 1
        bb = BasicBlock(label=f"{prefix}{self.block_counter}")
        if self.current_function:
            self.current_function.blocks.append(bb)
        return bb

    def lower_module(self, mod: Module) -> IRModule:
        ir_mod = IRModule(name=mod.name)
        for decl in mod.declarations:
            if isinstance(decl, StructDecl):
                self.structs[decl.name] = decl

        for decl in mod.declarations:
            if isinstance(decl, FunctionDecl):
                ir_func = self.lower_function(decl)
                ir_mod.functions.append(ir_func)

        return ir_mod

    def lower_function(self, decl: FunctionDecl) -> IRFunction:
        self.var_map = {}
        param_regs: List[Reg] = []
        for p in decl.params:
            p_name = p[0] if isinstance(p, tuple) else getattr(p, "name", str(p))
            r = self.new_reg(prefix=p_name + "_")
            self.var_map[p_name] = r
            param_regs.append(r)

        ir_func = IRFunction(name=decl.name, params=param_regs)
        self.current_function = ir_func
        self.current_bb = self.new_block("entry")

        for stmt in decl.body:
            self._lower_statement(stmt)

        # Fallback return if not terminated
        if not self.current_bb.instructions or not isinstance(self.current_bb.instructions[-1], Return):
            self.current_bb.append(Return(None))

        return ir_func

    def _lower_statement(self, stmt: Statement) -> None:
        if isinstance(stmt, LetStmt):
            init_val = getattr(stmt, "init", getattr(stmt, "value", None))
            val_op = self._lower_expr(init_val) if init_val else Const(0)
            dest_reg = self.new_reg(prefix=stmt.name + "_")
            self.current_bb.append(Assign(dest=dest_reg, src=val_op))
            self.var_map[stmt.name] = dest_reg

        elif isinstance(stmt, TupleLetStmt):
            init_op = self._lower_expr(stmt.init)
            for idx, name in enumerate(stmt.names):
                dest_reg = self.new_reg(prefix=f"{name}_")
                self.current_bb.append(Assign(dest=dest_reg, src=init_op))
                self.var_map[name] = dest_reg

        elif isinstance(stmt, AssignStmt):
            val_op = self._lower_expr(stmt.value)
            if isinstance(stmt.target, Identifier):
                dest = self.var_map.get(stmt.target.name)
                if dest and isinstance(dest, Reg):
                    self.current_bb.append(Assign(dest=dest, src=val_op))
            elif isinstance(stmt.target, FieldExpr):
                base_op = self._lower_expr(stmt.target.target)
                self.current_bb.append(RamStore(addr=base_op, src=val_op, offset=0))

        elif isinstance(stmt, ReturnStmt):
            ret_expr = getattr(stmt, "expr", getattr(stmt, "value", None))
            val_op = self._lower_expr(ret_expr) if ret_expr else None
            self.current_bb.append(Return(val_op))

        elif isinstance(stmt, IfStmt):
            cond_op = self._lower_expr(stmt.cond)
            then_bb = self.new_block("then")
            else_bb = self.new_block("else") if stmt.else_branch else None
            merge_bb = self.new_block("merge")

            false_target = else_bb.label if else_bb else merge_bb.label
            self.current_bb.append(BranchIf(cond=cond_op, true_target=then_bb.label, false_target=false_target))

            # Then
            self.current_bb = then_bb
            for s in stmt.then_branch:
                self._lower_statement(s)
            if not self.current_bb.instructions or not isinstance(self.current_bb.instructions[-1], Return):
                self.current_bb.append(Jump(target=merge_bb.label))

            # Else
            if else_bb:
                self.current_bb = else_bb
                for s in stmt.else_branch:
                    self._lower_statement(s)
                if not self.current_bb.instructions or not isinstance(self.current_bb.instructions[-1], Return):
                    self.current_bb.append(Jump(target=merge_bb.label))

            self.current_bb = merge_bb

        elif isinstance(stmt, WhileStmt):
            header_bb = self.new_block("while_hdr")
            body_bb = self.new_block("while_body")
            exit_bb = self.new_block("while_exit")

            self.current_bb.append(Jump(target=header_bb.label))
            self.current_bb = header_bb
            cond_op = self._lower_expr(stmt.cond)
            self.current_bb.append(BranchIf(cond=cond_op, true_target=body_bb.label, false_target=exit_bb.label))

            self.current_bb = body_bb
            for s in stmt.body:
                self._lower_statement(s)
            self.current_bb.append(Jump(target=header_bb.label))

            self.current_bb = exit_bb

    def _lower_expr(self, expr: Optional[Expression]) -> Operand:
        if expr is None:
            return Const(0)

        if isinstance(expr, IntLiteral):
            return Const(expr.value, 32)
        elif isinstance(expr, ByteLiteral):
            return Const(expr.value, 8)
        elif isinstance(expr, BoolLiteral):
            return Const(1 if expr.value else 0, 1)

        elif isinstance(expr, Identifier):
            if expr.name in self.var_map:
                return self.var_map[expr.name]
            # Enum / Constant resolution
            if "::" in expr.name or expr.name.isupper():
                return Const(1 if "Ok" in expr.name else 0)
            r = self.new_reg(prefix=expr.name + "_")
            return r

        elif isinstance(expr, BinaryOp):
            l_op = self._lower_expr(expr.left)
            r_op = self._lower_expr(expr.right)
            dest = self.new_reg()
            self.current_bb.append(BinOp(dest=dest, op=expr.op, left=l_op, right=r_op))
            return dest

        elif isinstance(expr, UnaryOp):
            inner_op = self._lower_expr(expr.expr)
            dest = self.new_reg()
            self.current_bb.append(UnOp(dest=dest, op=expr.op, src=inner_op))
            return dest

        elif isinstance(expr, CastExpr):
            return self._lower_expr(expr.expr)

        elif isinstance(expr, DerefExpr):
            addr_op = self._lower_expr(expr.expr)
            dest = self.new_reg()
            self.current_bb.append(RamLoad(dest=dest, addr=addr_op, offset=0))
            return dest

        elif isinstance(expr, UnsafeExpr):
            return self._lower_expr(expr.expr)

        elif isinstance(expr, FieldExpr):
            target_op = self._lower_expr(expr.target)
            dest = self.new_reg(prefix=f"{expr.field}_")
            self.current_bb.append(RamLoad(dest=dest, addr=target_op, offset=0))
            return dest

        elif isinstance(expr, CallExpr):
            callee_name = expr.callee.name if hasattr(expr.callee, "name") else str(expr.callee)
            if callee_name in ("mmio_write_barrier", "mmio_flush"):
                self.current_bb.append(MmioBarrier("write"))
                return Const(0)
            arg_ops = [self._lower_expr(a) for a in expr.args]
            dest = self.new_reg()
            self.current_bb.append(Call(dest=dest, callee=callee_name, args=arg_ops))
            return dest

        elif isinstance(expr, StructInitExpr):
            dest = self.new_reg(prefix=f"{expr.struct_name}_")
            return dest

        dest = self.new_reg()
        return dest
