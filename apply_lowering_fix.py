import sys

# --- 1. Patch src/backend/c99.py ---
with open("src/backend/c99.py", "r") as f:
    c99_lines = f.readlines()

new_c99 = []
for line in c99_lines:
    if line.strip() == '#include <stddef.h>':
        new_c99.append(line)
        new_c99.append('#include <string.h>\n')
    elif 'lines = [f"{proto} {"]' in line:
        indent = line[:len(line) - len(line.lstrip())]
        new_c99.append(line)
        new_c99.append(f'{indent}stack_arrays = getattr(fn, "stack_arrays", {{}})\n')
        new_c99.append(f'{indent}for name, size in stack_arrays.items():\n')
        new_c99.append(f'{indent}    lines.append(f"    uint8_t stack_{{name}}[{{size}}];")\n')
        new_c99.append(f'{indent}    lines.append(f"    memset(stack_{{name}}, 0, {{size}});")\n')
    elif 'elif isinstance(inst, UnOp):' in line:
        indent = line[:len(line) - len(line.lstrip())]
        new_c99.append(line)
        new_c99.append(f'{indent}    if inst.op == "&":\n')
        new_c99.append(f'{indent}        return f"{{inst.dest.name}} = (uintptr_t)(&({{self._fmt_op(inst.src)}}))"\n')
    else:
        new_c99.append(line)

with open("src/backend/c99.py", "w") as f:
    f.writelines(new_c99)
print("[+] src/backend/c99.py patched cleanly.")

# --- 2. Patch src/lowering/lowerer.py ---
with open("src/lowering/lowerer.py", "r") as f:
    low_lines = f.readlines()

new_low = []
i = 0
while i < len(low_lines):
    line = low_lines[i]

    # Initialize self.stack_arrays in Lowerer.__init__
    if 'self.var_map: Dict[str, Operand] = {}' in line:
        indent = line[:len(line) - len(line.lstrip())]
        new_low.append(line)
        new_low.append(f'{indent}self.stack_arrays: Dict[str, int] = {{}}\n')
        i += 1
        continue

    # Reset in lower_function
    if line.strip() == 'self.var_map = {}':
        indent = line[:len(line) - len(line.lstrip())]
        new_low.append(line)
        new_low.append(f'{indent}self.stack_arrays = {{}}\n')
        i += 1
        continue

    # Attach stack_arrays to IRFunction
    if line.strip() == 'return ir_func':
        indent = line[:len(line) - len(line.lstrip())]
        new_low.append(f'{indent}ir_func.stack_arrays = dict(self.stack_arrays)\n')
        new_low.append(line)
        i += 1
        continue

    # Intercept LetStmt initializing an ArrayRepeatExpr
    if line.strip() == 'elif isinstance(stmt, LetStmt):':
        indent = line[:len(line) - len(line.lstrip())]
        new_low.append(line)
        new_low.append(f'{indent}    init_node = getattr(stmt, "init", getattr(stmt, "value", None))\n')
        new_low.append(f'{indent}    if isinstance(init_node, ArrayRepeatExpr):\n')
        new_low.append(f'{indent}        size = init_node.count.value if hasattr(init_node.count, "value") else 64\n')
        new_low.append(f'{indent}        reg = self.new_reg(prefix=f"{{stmt.name}}_")\n')
        new_low.append(f'{indent}        self.stack_arrays[stmt.name] = size\n')
        new_low.append(f'{indent}        self.current_bb.append(UnOp(dest=reg, op="&", src=Reg(f"stack_{{stmt.name}}")))\n')
        new_low.append(f'{indent}        self.var_map[stmt.name] = reg\n')
        new_low.append(f'{indent}        return\n')
        i += 1
        continue

    # Intercept TupleLetStmt safely using stmt.init
    if line.strip() == 'elif isinstance(stmt, TupleLetStmt):':
        indent = line[:len(line) - len(line.lstrip())]
        new_low.append(line)
        new_low.append(f'{indent}    init_node = getattr(stmt, "init", getattr(stmt, "expr", getattr(stmt, "value", None)))\n')
        new_low.append(f'{indent}    res_op = self._lower_expression(init_node) if hasattr(self, "_lower_expression") else self._lower_expr(init_node)\n')
        new_low.append(f'{indent}    for name in stmt.names:\n')
        new_low.append(f'{indent}        r = self.new_reg(prefix=f"{{name}}_")\n')
        new_low.append(f'{indent}        self.current_bb.append(Assign(dest=r, src=res_op))\n')
        new_low.append(f'{indent}        self.var_map[name] = r\n')
        new_low.append(f'{indent}    return\n')
        # Skip original body of TupleLetStmt until the next elif/else
        i += 1
        while i < len(low_lines) and not (low_lines[i].startswith(indent + 'elif ') or low_lines[i].startswith(indent + 'else:')):
            i += 1
        continue

    # Intercept mmio_copy in CallExpr
    if line.strip() == 'elif isinstance(expr, CallExpr):':
        indent = line[:len(line) - len(line.lstrip())]
        new_low.append(line)
        new_low.append(f'{indent}    if expr.callee == "mmio_copy":\n')
        new_low.append(f'{indent}        dst_op = self._lower_expression(expr.args[0]) if hasattr(self, "_lower_expression") else self._lower_expr(expr.args[0])\n')
        new_low.append(f'{indent}        src_op = self._lower_expression(expr.args[1]) if hasattr(self, "_lower_expression") else self._lower_expr(expr.args[1])\n')
        new_low.append(f'{indent}        len_op = self._lower_expression(expr.args[2]) if hasattr(self, "_lower_expression") else self._lower_expr(expr.args[2])\n')
        new_low.append(f'{indent}        self.current_bb.append(Call(dest=None, callee="memcpy", args=[dst_op, src_op, len_op]))\n')
        new_low.append(f'{indent}        return Const(0)\n')
        new_low.append(f'{indent}    if expr.callee in ("mmio_read_barrier", "mmio_write_barrier"):\n')
        new_low.append(f'{indent}        self.current_bb.append(MmioBarrier())\n')
        new_low.append(f'{indent}        return Const(0)\n')
        i += 1
        continue

    new_low.append(line)
    i += 1

with open("src/lowering/lowerer.py", "w") as f:
    f.writelines(new_low)
print("[+] src/lowering/lowerer.py patched cleanly.")
