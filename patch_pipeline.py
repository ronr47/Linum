import re

# 1. Update src/backend/c99.py
with open("src/backend/c99.py", "r") as f:
    c99_code = f.read()

# Ensure string.h is included
if "#include <string.h>" not in c99_code:
    c99_code = c99_code.replace("#include <stddef.h>", "#include <stddef.h>\n#include <string.h>")

# Ensure stack arrays are emitted at function prologue
prologue_target = "lines = [f\"{proto} {\"]"
prologue_patch = """lines = [f\"{proto} {\"]
        stack_arrays = getattr(fn, "stack_arrays", {})
        for name, size in stack_arrays.items():
            lines.append(f"    uint8_t stack_{name}[{size}];")
            lines.append(f"    memset(stack_{name}, 0, {size});")"""

if "stack_arrays = getattr(fn" not in c99_code and prologue_target in c99_code:
    c99_code = c99_code.replace(prologue_target, prologue_patch)

# Ensure UnOp '&' generates address-of
old_unop = 'elif isinstance(inst, UnOp):'
new_unop = """elif isinstance(inst, UnOp):
            if inst.op == "&":
                return f"{inst.dest.name} = (uintptr_t)(&({self._fmt_op(inst.src)}))" """
if 'if inst.op == "&":' not in c99_code and old_unop in c99_code:
    c99_code = c99_code.replace(old_unop, new_unop)

# Ensure RamLoad enforces byte-level pointer arithmetic
old_ramload = """elif isinstance(inst, RamLoad):
            if "val" in inst.dest.name or "byte" in inst.dest.name:
                return f"{inst.dest.name} = (uintptr_t)(*((volatile const uint8_t*)({self._fmt_op(inst.addr)} + {inst.offset})))"
            return f"{inst.dest.name} = (uintptr_t)(*((volatile const uint32_t*)({self._fmt_op(inst.addr)} + {inst.offset})))" """

new_ramload = """elif isinstance(inst, RamLoad):
            addr_calc = f"((const uint8_t*)((uintptr_t)({self._fmt_op(inst.addr)})) + {inst.offset})"
            if "val" in inst.dest.name or "byte" in inst.dest.name:
                return f"{inst.dest.name} = (uintptr_t)(*((volatile const uint8_t*){addr_calc}))"
            return f"{inst.dest.name} = (uintptr_t)(*((volatile const uint32_t*)(const void*){addr_calc}))" """

if "addr_calc =" not in c99_code:
    c99_code = re.sub(r"elif isinstance\(inst, RamLoad\):.*?return f\"\{inst\.dest\.name\}.*?\)\)\)\"", new_ramload, c99_code, flags=re.DOTALL)

with open("src/backend/c99.py", "w") as f:
    f.write(c99_code)
print("[+] src/backend/c99.py patched.")

# 2. Update src/lowering/lowerer.py
with open("src/lowering/lowerer.py", "r") as f:
    low = f.read()

# Initialize stack_arrays
if "self.stack_arrays: Dict[str, int] = {}" not in low:
    low = low.replace(
        "self.var_map: Dict[str, Operand] = {}",
        "self.var_map: Dict[str, Operand] = {}\n        self.stack_arrays: Dict[str, int] = {}"
    )

# Reset & attach stack_arrays on IRFunction
if "self.stack_arrays = {}" not in low:
    low = low.replace("self.var_map = {}", "self.var_map = {}\n        self.stack_arrays = {}")
if "ir_func.stack_arrays" not in low:
    low = low.replace("return ir_func", "ir_func.stack_arrays = dict(self.stack_arrays)\n        return ir_func")

# Intercept LetStmt initializing an ArrayRepeatExpr
old_let_block = re.search(r"elif isinstance\(stmt, LetStmt\):.*?(?=elif isinstance\(stmt,)", low, re.DOTALL)
if old_let_block:
    new_let_code = """elif isinstance(stmt, LetStmt):
        init_node = getattr(stmt, "init", getattr(stmt, "value", None))
        if isinstance(init_node, ArrayRepeatExpr):
            size = init_node.count.value if hasattr(init_node.count, "value") else 64
            reg = self.new_reg(prefix=f"{stmt.name}_")
            self.stack_arrays[stmt.name] = size
            self.current_bb.append(UnOp(dest=reg, op="&", src=Reg(f"stack_{stmt.name}")))
            self.var_map[stmt.name] = reg
            return
        val_op = self._lower_expression(init_node) if hasattr(self, "_lower_expression") else self._lower_expr(init_node)
        reg = self.new_reg(prefix=f"{stmt.name}_")
        self.current_bb.append(Assign(dest=reg, src=val_op))
        self.var_map[stmt.name] = reg
        return
    """
    low = low[:old_let_block.start()] + new_let_code + low[old_let_block.end():]

# Intercept TupleLetStmt
old_tup_block = re.search(r"elif isinstance\(stmt, TupleLetStmt\):.*?(?=elif isinstance\(stmt,|$)", low, re.DOTALL)
if old_tup_block:
    new_tup_code = """elif isinstance(stmt, TupleLetStmt):
        val_node = getattr(stmt, "init", getattr(stmt, "expr", getattr(stmt, "value", None)))
        res_op = self._lower_expression(val_node) if hasattr(self, "_lower_expression") else self._lower_expr(val_node)
        for name in stmt.names:
            r = self.new_reg(prefix=f"{name}_")
            self.current_bb.append(Assign(dest=r, src=res_op))
            self.var_map[name] = r
        return
    """
    low = low[:old_tup_block.start()] + new_tup_code + low[old_tup_block.end():]

# Intercept mmio_copy and barriers in CallExpr
old_call_block = re.search(r"elif isinstance\(expr, CallExpr\):.*?(?=elif isinstance\(expr,|$)", low, re.DOTALL)
if old_call_block:
    call_snippet = old_call_block.group(0)
    if "mmio_copy" not in call_snippet:
        new_call_code = """elif isinstance(expr, CallExpr):
        if expr.callee == "mmio_copy":
            dst_op = self._lower_expression(expr.args[0]) if hasattr(self, "_lower_expression") else self._lower_expr(expr.args[0])
            src_op = self._lower_expression(expr.args[1]) if hasattr(self, "_lower_expression") else self._lower_expr(expr.args[1])
            len_op = self._lower_expression(expr.args[2]) if hasattr(self, "_lower_expression") else self._lower_expr(expr.args[2])
            self.current_bb.append(Call(dest=None, callee="memcpy", args=[dst_op, src_op, len_op]))
            return Const(0)
        if expr.callee in ("mmio_read_barrier", "mmio_write_barrier"):
            self.current_bb.append(MmioBarrier())
            return Const(0)
        """ + call_snippet[len("elif isinstance(expr, CallExpr):"):]
        low = low[:old_call_block.start()] + new_call_code + low[old_call_block.end():]

with open("src/lowering/lowerer.py", "w") as f:
    f.write(low)
print("[+] src/lowering/lowerer.py patched.")
