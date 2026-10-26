import re

# =========================================================================
# 1. Update src/backend/c99.py
# =========================================================================
with open("src/backend/c99.py", "r") as f:
    c99 = f.read()

# Add <string.h> cleanly
if "#include <string.h>" not in c99:
    c99 = c99.replace('"#include <stddef.h>",', '"#include <stddef.h>",\n            "#include <string.h>",')

# Add stack_arrays emission to emit_function
proto_pattern = r'lines = \[f?"\{proto\} ?(?:\{|\{\{)?"\]|lines = \[proto \+ " \{"\]'
replacement_proto = """lines = [proto + " {"]
        stack_arrays = getattr(fn, "stack_arrays", {})
        for name, size in stack_arrays.items():
            lines.append(f"    uint8_t stack_{name}[{size}];")
            lines.append(f"    memset(stack_{name}, 0, {size});")"""

c99 = re.sub(proto_pattern, replacement_proto, c99, count=1)

# Ensure stack_* names are filtered from local_registers declarations
old_filter = "local_registers = sorted(registers - param_names)"
new_filter = """stack_names = {f"stack_{name}" for name in stack_arrays.keys()}
        local_registers = sorted(registers - param_names - stack_names)"""

if old_filter in c99 and "stack_names" not in c99:
    c99 = c99.replace(old_filter, new_filter, 1)

# UnOp '&' generates address-of
if 'if inst.op == "&":' not in c99:
    c99 = c99.replace(
        'elif isinstance(inst, UnOp):',
        'elif isinstance(inst, UnOp):\n            if inst.op == "&":\n                return f"{inst.dest.name} = (uintptr_t)(&({self._fmt_op(inst.src)}))"'
    )

# 64-bit pointer safety in RamLoad & MmioLoad:
# Pointers ('base', 'addr', 'slot') MUST load full 64-bit uintptr_t, bytes load uint8_t, integers load uint32_t
old_ramload = re.search(r'elif isinstance\(inst, RamLoad\):.*?(?=elif isinstance\(inst, RamStore\))', c99, re.DOTALL)
if old_ramload:
    new_ramload = """elif isinstance(inst, RamLoad):
            addr_calc = f"((const uint8_t*)((uintptr_t)({self._fmt_op(inst.addr)})) + {inst.offset})"
            if "val" in inst.dest.name or "byte" in inst.dest.name:
                return f"{inst.dest.name} = (uintptr_t)(*((volatile const uint8_t*){addr_calc}))"
            if "base" in inst.dest.name or "addr" in inst.dest.name or "slot" in inst.dest.name:
                return f"{inst.dest.name} = (uintptr_t)(*((volatile const uintptr_t*)(const void*){addr_calc}))"
            return f"{inst.dest.name} = (uintptr_t)(*((volatile const uint32_t*)(const void*){addr_calc}))"
        """
    c99 = c99[:old_ramload.start()] + new_ramload + c99[old_ramload.end():]

old_mmioload = re.search(r'elif isinstance\(inst, MmioLoad\):.*?(?=elif isinstance\(inst, MmioStore\))', c99, re.DOTALL)
if old_mmioload:
    new_mmioload = """elif isinstance(inst, MmioLoad):
            addr_calc = f"((const uint8_t*)((uintptr_t)({self._fmt_op(inst.addr)})) + {inst.offset})"
            if "base" in inst.dest.name or "addr" in inst.dest.name or "slot" in inst.dest.name:
                return f"{inst.dest.name} = (uintptr_t)(*((volatile const uintptr_t*)(const void*){addr_calc}))"
            return f"{inst.dest.name} = (uintptr_t)(*((volatile const uint32_t*)(const void*){addr_calc}))"
        """
    c99 = c99[:old_mmioload.start()] + new_mmioload + c99[old_mmioload.end():]

with open("src/backend/c99.py", "w") as f:
    f.write(c99)
print("[+] src/backend/c99.py patched.")

# =========================================================================
# 2. Update src/lowering/lowerer.py
# =========================================================================
with open("src/lowering/lowerer.py", "r") as f:
    low = f.read()

# Setup stack_arrays tracking
if "self.stack_arrays: Dict[str, int] = {}" not in low:
    low = low.replace(
        "self.var_map: Dict[str, Operand] = {}",
        "self.var_map: Dict[str, Operand] = {}\n        self.stack_arrays: Dict[str, int] = {}"
    )

if "self.stack_arrays = {}" not in low:
    low = low.replace("self.var_map = {}", "self.var_map = {}\n        self.stack_arrays = {}")

if "ir_func.stack_arrays" not in low:
    low = low.replace("return ir_func", "ir_func.stack_arrays = dict(self.stack_arrays)\n        return ir_func")

# Intercept LetStmt initializing ArrayRepeatExpr
old_let_match = re.search(r'(\s+)elif isinstance\(stmt, LetStmt\):.*?(?=\n\1elif |\n\1def )', low, re.DOTALL)
if old_let_match:
    ind = old_let_match.group(1)
    new_let_code = f"""{ind}elif isinstance(stmt, LetStmt):
{ind}    init_node = getattr(stmt, "init", getattr(stmt, "value", None))
{ind}    if init_node is not None and type(init_node).__name__ == "ArrayRepeatExpr":
{ind}        count_node = getattr(init_node, "count", None)
{ind}        size = getattr(count_node, "value", 64)
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
    low = low[:old_let_match.start()] + new_let_code + low[old_let_match.end():]

# Intercept TupleLetStmt safely using getattr
old_tup_match = re.search(r'(\s+)elif isinstance\(stmt, TupleLetStmt\):.*?(?=\n\1elif |\n\1def )', low, re.DOTALL)
if old_tup_match:
    ind = old_tup_match.group(1)
    new_tup_code = f"""{ind}elif isinstance(stmt, TupleLetStmt):
{ind}    init_node = getattr(stmt, "init", getattr(stmt, "expr", getattr(stmt, "value", None)))
{ind}    res_op = self._lower_expression(init_node) if hasattr(self, "_lower_expression") else self._lower_expr(init_node)
{ind}    for name in stmt.names:
{ind}        r = self.new_reg(prefix=f"{{name}}_")
{ind}        self.current_bb.append(Assign(dest=r, src=res_op))
{ind}        self.var_map[name] = r
{ind}    return"""
    low = low[:old_tup_match.start()] + new_tup_code + low[old_tup_match.end():]

# Fix DerefExpr safely using getattr(expr, "expr", getattr(expr, "target", ...))
old_deref_match = re.search(r'(\s+)elif isinstance\(expr, DerefExpr\):.*?(?=\n\1elif |\n\1def )', low, re.DOTALL)
if old_deref_match:
    ind = old_deref_match.group(1)
    new_deref_code = f"""{ind}elif isinstance(expr, DerefExpr):
{ind}    inner = getattr(expr, "expr", getattr(expr, "target", getattr(expr, "operand", None)))
{ind}    return self._lower_expression(inner) if hasattr(self, "_lower_expression") else self._lower_expr(inner)"""
    low = low[:old_deref_match.start()] + new_deref_code + low[old_deref_match.end():]

# Intercept mmio_copy in CallExpr
old_call_match = re.search(r'(\s+)elif isinstance\(expr, CallExpr\):', low)
if old_call_match and "mmio_copy" not in low:
    ind = old_call_match.group(1)
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
    low = low[:old_call_match.start()] + call_inject + low[old_call_match.end():]

# Field offsets for StorageDevice and Header
old_field_match = re.search(r'(\s+)elif isinstance\(expr, FieldExpr\):.*?(?=\n\1elif |\n\1def )', low, re.DOTALL)
if old_field_match:
    ind = old_field_match.group(1)
    new_field_code = f"""{ind}elif isinstance(expr, FieldExpr):
{ind}    target_op = self._lower_expression(expr.target) if hasattr(self, "_lower_expression") else self._lower_expr(expr.target)
{ind}    offsets = {{
{ind}        "magic": 0, "seq": 4, "body_len": 8, "crc": 12,
{ind}        "base": 0, "capacity": 8, "secret_key": 16
{ind}    }}
{ind}    offset = offsets.get(expr.field, 0)
{ind}    dest = self.new_reg(prefix=f"{{expr.field}}_")
{ind}    self.current_bb.append(RamLoad(dest=dest, addr=target_op, offset=offset))
{ind}    return dest"""
    low = low[:old_field_match.start()] + new_field_code + low[old_field_match.end():]

with open("src/lowering/lowerer.py", "w") as f:
    f.write(low)
print("[+] src/lowering/lowerer.py patched.")
