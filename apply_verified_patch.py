import sys

# -------------------------------------------------------------
# 1. Patch src/backend/c99.py
# -------------------------------------------------------------
with open("src/backend/c99.py", "r") as f:
    c99_lines = f.readlines()

new_c99 = []
for line in c99_lines:
    if line.strip() == "#include <stddef.h>":
        new_c99.append(line)
        new_c99.append("#include <string.h>\n")
    elif 'lines = [f"{proto} {"]' in line:
        new_c99.append(line)
        new_c99.append("        stack_arrays = getattr(fn, \"stack_arrays\", {})\n")
        new_c99.append("        for name, size in stack_arrays.items():\n")
        new_c99.append("            lines.append(f\"    uint8_t stack_{name}[{size}];\")\n")
        new_c99.append("            lines.append(f\"    memset(stack_{name}, 0, {size});\")\n")
    elif 'elif isinstance(inst, UnOp):' in line:
        new_c99.append(line)
        new_c99.append("            if inst.op == \"&\":\n")
        new_c99.append("                return f\"{inst.dest.name} = (uintptr_t)(&({self._fmt_op(inst.src)}))\"\n")
    elif 'elif isinstance(inst, RamLoad):' in line:
        new_c99.append(line)
        new_c99.append("            addr_calc = f\"((const uint8_t*)((uintptr_t)({self._fmt_op(inst.addr)})) + {inst.offset})\"\n")
        new_c99.append("            if \"val\" in inst.dest.name or \"byte\" in inst.dest.name:\n")
        new_c99.append("                return f\"{inst.dest.name} = (uintptr_t)(*((volatile const uint8_t*){addr_calc}))\"\n")
        new_c99.append("            return f\"{inst.dest.name} = (uintptr_t)(*((volatile const uint32_t*)(const void*){addr_calc}))\"\n")
        # Skip the original return statement lines for RamLoad
        continue
    elif 'return f"{inst.dest.name} = (uintptr_t)(*((volatile const uint8_t*)' in line or \
         'return f"{inst.dest.name} = (uintptr_t)(*((volatile const uint32_t*)' in line:
        continue
    else:
        new_c99.append(line)

with open("src/backend/c99.py", "w") as f:
    f.writelines(new_c99)
print("[+] src/backend/c99.py successfully updated.")

# -------------------------------------------------------------
# 2. Patch src/lowering/lowerer.py
# -------------------------------------------------------------
with open("src/lowering/lowerer.py", "r") as f:
    low_lines = f.readlines()

new_low = []
i = 0
while i < len(low_lines):
    line = low_lines[i]
    
    # Track stack_arrays in __init__
    if "self.var_map: Dict[str, Operand] = {}" in line:
        new_low.append(line)
        new_low.append("        self.stack_arrays: Dict[str, int] = {}\n")
        i += 1
        continue

    # Reset var_map & stack_arrays in lower_function
    if "self.var_map = {}" in line:
        new_low.append(line)
        new_low.append("        self.stack_arrays = {}\n")
        i += 1
        continue

    # Attach stack_arrays to IRFunction on return
    if "return ir_func" in line and "def lower_function" in "".join(low_lines[max(0, i-40):i]):
        new_low.append("        ir_func.stack_arrays = dict(self.stack_arrays)\n")
        new_low.append(line)
        i += 1
        continue

    # Detect LetStmt in _lower_statement
    if line.strip().startswith("elif isinstance(stmt, LetStmt):"):
        indent = line[:line.find("elif")]
        new_low.append(line)
        new_low.append(f"{indent}    init_node = getattr(stmt, 'init', getattr(stmt, 'value', None))\n")
        new_low.append(f"{indent}    if isinstance(init_node, ArrayRepeatExpr):\n")
        new_low.append(f"{indent}        size = init_node.count.value if hasattr(init_node.count, 'value') else 64\n")
        new_low.append(f"{indent}        reg = self.new_reg(prefix=f'{{stmt.name}}_')\n")
        new_low.append(f"{indent}        self.stack_arrays[stmt.name] = size\n")
        new_low.append(f"{indent}        self.current_bb.append(UnOp(dest=reg, op='&', src=Reg(f'stack_{{stmt.name}}')))\n")
        new_low.append(f"{indent}        self.var_map[stmt.name] = reg\n")
        new_low.append(f"{indent}        return\n")
        new_low.append(f"{indent}    val_op = self._lower_expression(init_node) if hasattr(self, '_lower_expression') else self._lower_expr(init_node)\n")
        new_low.append(f"{indent}    reg = self.new_reg(prefix=f'{{stmt.name}}_')\n")
        new_low.append(f"{indent}    self.current_bb.append(Assign(dest=reg, src=val_op))\n")
        new_low.append(f"{indent}    self.var_map[stmt.name] = reg\n")
        new_low.append(f"{indent}    return\n")
        # Advance through original LetStmt block until next elif/else
        i += 1
        while i < len(low_lines) and not low_lines[i].strip().startswith(("elif ", "else:", "def ")):
            i += 1
        continue

    # Detect TupleLetStmt in _lower_statement
    if line.strip().startswith("elif isinstance(stmt, TupleLetStmt):"):
        indent = line[:line.find("elif")]
        new_low.append(line)
        new_low.append(f"{indent}    init_node = getattr(stmt, 'init', getattr(stmt, 'expr', getattr(stmt, 'value', None)))\n")
        new_low.append(f"{indent}    res_op = self._lower_expression(init_node) if hasattr(self, '_lower_expression') else self._lower_expr(init_node)\n")
        new_low.append(f"{indent}    for name in stmt.names:\n")
        new_low.append(f"{indent}        r = self.new_reg(prefix=f'{{name}}_')\n")
        new_low.append(f"{indent}        self.current_bb.append(Assign(dest=r, src=res_op))\n")
        new_low.append(f"{indent}        self.var_map[name] = r\n")
        new_low.append(f"{indent}    return\n")
        i += 1
        while i < len(low_lines) and not low_lines[i].strip().startswith(("elif ", "else:", "def ")):
            i += 1
        continue

    # Detect CallExpr in _lower_expression
    if line.strip().startswith("elif isinstance(expr, CallExpr):"):
        indent = line[:line.find("elif")]
        new_low.append(line)
        new_low.append(f"{indent}    if expr.callee == 'mmio_copy':\n")
        new_low.append(f"{indent}        dst_op = self._lower_expression(expr.args[0]) if hasattr(self, '_lower_expression') else self._lower_expr(expr.args[0])\n")
        new_low.append(f"{indent}        src_op = self._lower_expression(expr.args[1]) if hasattr(self, '_lower_expression') else self._lower_expr(expr.args[1])\n")
        new_low.append(f"{indent}        len_op = self._lower_expression(expr.args[2]) if hasattr(self, '_lower_expression') else self._lower_expr(expr.args[2])\n")
        new_low.append(f"{indent}        self.current_bb.append(Call(dest=None, callee='memcpy', args=[dst_op, src_op, len_op]))\n")
        new_low.append(f"{indent}        return Const(0)\n")
        new_low.append(f"{indent}    if expr.callee in ('mmio_read_barrier', 'mmio_write_barrier'):\n")
        new_low.append(f"{indent}        self.current_bb.append(MmioBarrier())\n")
        new_low.append(f"{indent}        return Const(0)\n")
        i += 1
        continue

    new_low.append(line)
    i += 1

with open("src/lowering/lowerer.py", "w") as f:
    f.writelines(new_low)

print("[+] src/lowering/lowerer.py successfully updated.")
