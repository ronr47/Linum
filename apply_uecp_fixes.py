import re

# ---------------------------------------------------------------------------
# 1. Fix src/backend/c99.py
# ---------------------------------------------------------------------------
with open("src/backend/c99.py", "r") as f:
    c99 = f.read()

# Add <string.h> for memset/memcpy
if "#include <string.h>" not in c99:
    c99 = c99.replace("#include <stddef.h>", "#include <stddef.h>\n#include <string.h>")

# Fix the f-string syntax error and insert stack frame allocations
target_proto = 'lines = [f"{proto} {"]'
if target_proto not in c99:
    target_proto = 'lines = [proto + " {"]'
if target_proto not in c99:
    target_proto = 'lines = [f"{proto} {{"]'

replacement_proto = """lines = [proto + " {"]
        stack_arrays = getattr(fn, "stack_arrays", {})
        for name, size in stack_arrays.items():
            lines.append(f"    uint8_t stack_{name}[{size}];")
            lines.append(f"    memset(stack_{name}, 0, {size});")"""

c99 = re.sub(r'lines = \[f?"\{proto\} ?(?:\{|\{\{)?"\]', replacement_proto, c99, count=1)

# Ensure UnOp '&' generates C address-of
if 'if inst.op == "&":' not in c99:
    c99 = c99.replace(
        'elif isinstance(inst, UnOp):',
        'elif isinstance(inst, UnOp):\n            if inst.op == "&":\n                return f"{inst.dest.name} = (uintptr_t)(&({self._fmt_op(inst.src)}))"'
    )

# Fix RamLoad byte-level calculation
old_ramload = re.search(r'elif isinstance\(inst, RamLoad\):.*?(?=elif isinstance\(inst, RamStore\))', c99, re.DOTALL)
if old_ramload:
    new_ramload = """elif isinstance(inst, RamLoad):
            addr_calc = f"((const uint8_t*)((uintptr_t)({self._fmt_op(inst.addr)})) + {inst.offset})"
            if "val" in inst.dest.name or "byte" in inst.dest.name:
                return f"{inst.dest.name} = (uintptr_t)(*((volatile const uint8_t*){addr_calc}))"
            return f"{inst.dest.name} = (uintptr_t)(*((volatile const uint32_t*)(const void*){addr_calc}))"
        """
    c99 = c99[:old_ramload.start()] + new_ramload + c99[old_ramload.end():]

with open("src/backend/c99.py", "w") as f:
    f.write(c99)
print("[+] src/backend/c99.py patched cleanly.")

# ---------------------------------------------------------------------------
# 2. Fix src/lowering/lowerer.py
# ---------------------------------------------------------------------------
with open("src/lowering/lowerer.py", "r") as f:
    low = f.read()

# Setup stack_arrays dictionary tracking
if "self.stack_arrays: Dict[str, int] = {}" not in low:
    low = low.replace(
        "self.var_map: Dict[str, Operand] = {}",
        "self.var_map: Dict[str, Operand] = {}\n        self.stack_arrays: Dict[str, int] = {}"
    )

if "self.stack_arrays = {}" not in low:
    low = low.replace("self.var_map = {}", "self.var_map = {}\n        self.stack_arrays = {}")

if "ir_func.stack_arrays" not in low:
    low = low.replace("return ir_func", "ir_func.stack_arrays = dict(self.stack_arrays)\n        return ir_func")

# Patch LetStmt for ArrayRepeatExpr handling
old_let = re.search(r'(\s+)elif isinstance\(stmt, LetStmt\):.*?(?=\n\1elif |\n\1def )', low, re.DOTALL)
if old_let:
    ind = old_let.group(1)
    new_let = f"""{ind}elif isinstance(stmt, LetStmt):
{ind}    init_node = getattr(stmt, "init", getattr(stmt, "value", None))
{ind}    if isinstance(init_node, ArrayRepeatExpr):
{ind}        size = init_node.count.value if hasattr(init_node.count, "value") else 64
{ind}        reg = self.new_reg(prefix=f"{{stmt.name}}_")
{ind}        self.stack_arrays[stmt.name] = size
{ind}        self.current_bb.append(UnOp(dest=reg, op="&", src=Reg(f"stack_{{stmt.name}}")))
{ind}        self.var_map[stmt.name] = reg
{ind}        return
{ind}    val_op = self._lower_expression(init_node) if hasattr(self, "_lower_expression") else self._lower_expr(init_node)
{ind}    reg = self.new_reg(prefix=f"{{stmt.name}}_")
{ind}    self.current_bb.append(Assign(dest=reg, src=val_op))
{ind}    self.var_map[stmt.name] = reg
{ind}    return"""
    low = low[:old_let.start()] + new_let + low[old_let.end():]

# Patch TupleLetStmt
old_tup = re.search(r'(\s+)elif isinstance\(stmt, TupleLetStmt\):.*?(?=\n\1elif |\n\1def )', low, re.DOTALL)
if old_tup:
    ind = old_tup.group(1)
    new_tup = f"""{ind}elif isinstance(stmt, TupleLetStmt):
{ind}    init_node = getattr(stmt, "init", getattr(stmt, "expr", getattr(stmt, "value", None)))
{ind}    res_op = self._lower_expression(init_node) if hasattr(self, "_lower_expression") else self._lower_expr(init_node)
{ind}    for name in stmt.names:
{ind}        r = self.new_reg(prefix=f"{{name}}_")
{ind}        self.current_bb.append(Assign(dest=r, src=res_op))
{ind}        self.var_map[name] = r
{ind}    return"""
    low = low[:old_tup.start()] + new_tup + low[old_tup.end():]

# Patch CallExpr for mmio_copy and barriers
old_call = re.search(r'(\s+)elif isinstance\(expr, CallExpr\):', low)
if old_call and "mmio_copy" not in low:
    ind = old_call.group(1)
    call_inject = f"""{ind}elif isinstance(expr, CallExpr):
{ind}    if expr.callee == "mmio_copy":
{ind}        dst_op = self._lower_expression(expr.args[0]) if hasattr(self, "_lower_expression") else self._lower_expr(expr.args[0])
{ind}        src_op = self._lower_expression(expr.args[1]) if hasattr(self, "_lower_expression") else self._lower_expr(expr.args[1])
{ind}        len_op = self._lower_expression(expr.args[2]) if hasattr(self, "_lower_expression") else self._lower_expr(expr.args[2])
{ind}        self.current_bb.append(Call(dest=None, callee="memcpy", args=[dst_op, src_op, len_op]))
{ind}        return Const(0)
{ind}    if expr.callee in ("mmio_read_barrier", "mmio_write_barrier"):
{ind}        self.current_bb.append(MmioBarrier())
{ind}        return Const(0)"""
    low = low[:old_call.start()] + call_inject + low[old_call.end():]

with open("src/lowering/lowerer.py", "w") as f:
    f.write(low)
print("[+] src/lowering/lowerer.py patched cleanly.")
