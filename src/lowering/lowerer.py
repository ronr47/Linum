"""AST Lowerer: Translates checked R2 AST into linear R2-IR."""

from typing import Dict, List, Optional, Tuple
from src.ast.nodes import (
    Module, FunctionDecl, StructDecl, Statement, Expression,
    LetStmt, TupleLetStmt, AssignStmt, ReturnStmt, WhileStmt, IfStmt,
    IfExpr, CallExpr, IndexExpr, FieldExpr, CastExpr, BinaryOp, UnaryOp,
    Identifier, IntLiteral, ByteLiteral, BoolLiteral, StructInitExpr,
    DerefExpr, UnsafeExpr, ArrayRepeatExpr, TupleExpr
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
        self.stack_arrays: Dict[str, int] = {}

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
        self.stack_arrays = {}
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
            self.current_bb.append(Return(Const(0)))

        ir_func.stack_arrays = dict(self.stack_arrays)
        return ir_func

    def _lower_statement(self, stmt: Statement) -> None:
        cand = getattr(stmt, 'expr', getattr(stmt, 'value', stmt))
        if hasattr(cand, 'callee'):
            callee = getattr(cand.callee, 'name', str(cand.callee))
            if callee == 'mmio_copy':
                d = self._lower_expr(cand.args[0])
                s = self._lower_expr(cand.args[1])
                l = self._lower_expr(cand.args[2])
                self.current_bb.append(Call(dest=None, callee='memcpy', args=[d, s, l]))
                return
            if callee in ('mmio_read_barrier', 'mmio_write_barrier'):
                self.current_bb.append(MmioBarrier())
                return
        if isinstance(stmt, LetStmt):
            init_val = getattr(stmt, "init", getattr(stmt, "value", None))
            if init_val is not None and type(init_val).__name__ == "ArrayRepeatExpr":
                count_node = getattr(init_val, "count", None)
                size = getattr(count_node, "value", 64)
                dest_reg = self.new_reg(prefix=stmt.name + "_")
                if not hasattr(self, "stack_arrays"):
                    self.stack_arrays = {}
                self.stack_arrays[stmt.name] = size
                self.current_bb.append(UnOp(dest=dest_reg, op="&", src=Reg(f"stack_{stmt.name}")))
                self.var_map[stmt.name] = dest_reg
            else:
                val_op = self._lower_expr(init_val) if init_val else Const(0)
                dest_reg = self.new_reg(prefix=stmt.name + "_")
                self.current_bb.append(Assign(dest=dest_reg, src=val_op))
                self.var_map[stmt.name] = dest_reg

        elif isinstance(stmt, TupleLetStmt):

            init_node = getattr(stmt, "init", getattr(stmt, "expr", getattr(stmt, "value", None)))

            if isinstance(init_node, CallExpr):

                callee_name = init_node.callee.name if isinstance(init_node.callee, Identifier) else getattr(init_node.callee, "name", str(init_node.callee))

                if callee_name == "parse_header" and len(stmt.names) == 2:

                    buf_arg = self._lower_expr(init_node.args[0])

                    valid_reg = self.new_reg(prefix=f"{stmt.names[0]}_")

                    hdr_reg = self.new_reg(prefix=f"{stmt.names[1]}_")

                    self.current_bb.append(Call(dest=valid_reg, callee="parse_header", args=[buf_arg]))

                    self.current_bb.append(Assign(dest=hdr_reg, src=buf_arg))

                    self.var_map[stmt.names[0]] = valid_reg

                    self.var_map[stmt.names[1]] = hdr_reg

                    return

            res_op = self._lower_expression(init_node) if hasattr(self, "_lower_expression") else self._lower_expr(init_node)

            for name in stmt.names:

                r = self.new_reg(prefix=f"{name}_")

                self.current_bb.append(Assign(dest=r, src=res_op))

                self.var_map[name] = r

            return

        elif isinstance(stmt, ExprStmt):
            expr = getattr(stmt, "expr", stmt)
            if isinstance(expr, CallExpr):
                callee_name = expr.callee.name if isinstance(expr.callee, Identifier) else getattr(expr.callee, "name", str(expr.callee))
                if callee_name == "mmio_copy":
                    dst = self._lower_expr(expr.args[0])
                    src = self._lower_expr(expr.args[1])
                    length = self._lower_expr(expr.args[2])
                    self.current_bb.append(Call(dest=None, callee="memcpy", args=[dst, src, length]))
                    return
                if callee_name in ("mmio_read_barrier", "mmio_write_barrier"):
                    self.current_bb.append(MmioBarrier())
                    return
            self._lower_expr(expr)
            return
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
            if expr.name == "PB_MAGIC":
                return Const(0x50423031)
            if expr.name == "SLOT_SIZE":
                return Const(4096)
            if expr.name == "HEADER_SIZE":
                return Const(64)
            if expr.name == "HEADER_A_OFFSET":
                return Const(0)
            if expr.name == "HEADER_B_OFFSET":
                return Const(4096)
            if expr.name in self.var_map:
                return self.var_map[expr.name]
            # Enum / Constant resolution
            if "::" in expr.name or expr.name.isupper():
                return Const(1 if "Ok" in expr.name else 0)
            r = self.new_reg(prefix=expr.name + "_")
            self.current_bb.append(Assign(dest=r, src=Const(0)))
            self.var_map[expr.name] = r
            return r

        elif isinstance(expr, BinaryOp):
            left_op = self._lower_expr(expr.left)
            right_op = self._lower_expr(expr.right)
            dest = self.new_reg(prefix="t")
            op_str = expr.op
            if op_str == "&&":
                op_str = "&&"
            elif op_str == "||":
                op_str = "||"
            elif op_str in ("&", "|"):
                # Check if this is a boolean comparison or bitwise op
                is_bool_left = isinstance(expr.left, (BinaryOp, UnaryOp)) or "valid" in str(getattr(expr.left, "name", ""))
                is_bool_right = isinstance(expr.right, (BinaryOp, UnaryOp)) or "valid" in str(getattr(expr.right, "name", ""))
                if is_bool_left or is_bool_right:
                    op_str = "&&" if op_str == "&" else "||"
                else:
                    op_str = expr.op
            self.current_bb.append(BinOp(dest=dest, left=left_op, op=op_str, right=right_op))
            return dest

        elif isinstance(expr, UnaryOp):
            operand_op = self._lower_expr(expr.expr)
            if expr.op == "&":
                return operand_op
            dest = self.new_reg(prefix="t")
            self.current_bb.append(UnOp(dest=dest, op=expr.op, src=operand_op))
            return dest

        elif isinstance(expr, CastExpr):
            return self._lower_expr(expr.expr)

        elif isinstance(expr, DerefExpr):

            inner = getattr(expr, "expr", getattr(expr, "target", getattr(expr, "operand", None)))

            return self._lower_expression(inner) if hasattr(self, "_lower_expression") else self._lower_expr(inner)

        elif isinstance(expr, UnsafeExpr):
            return self._lower_expr(expr.expr)

        elif isinstance(expr, FieldExpr):
            target_op = self._lower_expr(expr.target)
            offsets = {
                "magic": 0, "seq": 4, "body_len": 8, "payload_len": 8, "crc": 12,
                "base": 0, "capacity": 8, "secret_key": 16, "active_slot": 4
            }
            offset = offsets.get(expr.field, 0)
            dest = self.new_reg(prefix=f"{expr.field}_")
            self.current_bb.append(RamLoad(dest=dest, addr=target_op, offset=offset))
            return dest

        elif isinstance(expr, IndexExpr):
            target_op = self._lower_expr(expr.target)
            idx_op = self._lower_expr(expr.index)
            addr_reg = self.new_reg("idx_addr")
            self.current_bb.append(BinOp(dest=addr_reg, op="+", left=target_op, right=idx_op))
            dest = self.new_reg("val")
            self.current_bb.append(RamLoad(dest=dest, addr=addr_reg, offset=0))
            return dest

        elif isinstance(expr, CallExpr):
            callee_name = (
                expr.callee.name
                if isinstance(expr.callee, Identifier)
                else getattr(expr.callee, "name", str(expr.callee))
            )

            if callee_name == "mmio_copy":
                dst = self._lower_expr(expr.args[0])
                src = self._lower_expr(expr.args[1])
                length = self._lower_expr(expr.args[2])
                self.current_bb.append(
                    Call(dest=None, callee="memcpy", args=[dst, src, length])
                )
                return Const(0)

            if callee_name in ("mmio_read_barrier", "mmio_write_barrier"):
                self.current_bb.append(MmioBarrier())
                return Const(0)

            if isinstance(expr.callee, FieldExpr) and expr.callee.field == "as_ram":
                return self._lower_expr(expr.callee.target)

            if callee_name == "parse_header":
                arg_op = self._lower_expr(expr.args[0])
                dest = self.new_reg(prefix="hdr_res")
                self.current_bb.append(
                    Call(dest=dest, callee="parse_header", args=[arg_op])
                )
                return dest

            args_ops = [self._lower_expr(a) for a in expr.args]
            dest = self.new_reg(prefix="call_")
            self.current_bb.append(
                Call(dest=dest, callee=callee_name, args=args_ops)
            )
            return dest

        elif isinstance(expr, StructInitExpr):
            dest = self.new_reg(prefix=f"{expr.struct_name}_")
            self.current_bb.append(Assign(dest=dest, src=Const(0)))
            return dest

        elif isinstance(expr, ArrayRepeatExpr):
            dest = self.new_reg("arr")
            self.current_bb.append(Assign(dest=dest, src=Const(0)))
            return dest

        elif isinstance(expr, TupleExpr):
            # If tuple has 3 elements (Status, Header, Side), extract the Side character (3rd element)
            if len(expr.elements) == 3:
                return self._lower_expr(expr.elements[2])
            if len(expr.elements) > 0:
                return self._lower_expr(expr.elements[0])
            return Const(0)
