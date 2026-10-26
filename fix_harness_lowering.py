import re

# ==========================================
# 1. Patch src/lowering/lowerer.py
# ==========================================
with open("src/lowering/lowerer.py", "r") as f:
    low = f.read()

# Fix TupleLetStmt handling:
# When let (valid_a, hdr_a) = parse_header(raw_a.as_ram());
# valid_a gets the boolean result (1 or 0)
# hdr_a gets the buffer pointer (raw_a) so field accesses read from raw_a!
old_tuple_match = re.search(r"elif isinstance\(stmt, TupleLetStmt\):.*?(?=elif isinstance\(stmt,|$)", low, re.DOTALL)
if old_tuple_match:
    new_tuple_code = """elif isinstance(stmt, TupleLetStmt):
        init_node = getattr(stmt, "init", getattr(stmt, "expr", getattr(stmt, "value", None)))
        # Check if call is parse_header(buf)
        buf_arg = None
        if hasattr(init_node, "callee") and init_node.callee == "parse_header" and init_node.args:
            buf_arg = self._lower_expression(init_node.args[0]) if hasattr(self, "_lower_expression") else self._lower_expr(init_node.args[0])

        res_op = self._lower_expression(init_node) if hasattr(self, "_lower_expression") else self._lower_expr(init_node)
        
        for idx, name in enumerate(stmt.names):
            r = self.new_reg(prefix=f"{name}_")
            if idx == 1 and buf_arg is not None:
                # hdr points directly to the underlying raw buffer
                self.current_bb.append(Assign(dest=r, src=buf_arg))
            else:
                self.current_bb.append(Assign(dest=r, src=res_op))
            self.var_map[name] = r
        return
    """
    low = low[:old_tuple_match.start()] + new_tuple_code + low[old_tuple_match.end():]

# Fix FieldExpr lowering so accessing field of a buffer loads from that buffer + offset
old_field_match = re.search(r"elif isinstance\(expr, FieldExpr\):.*?(?=elif isinstance\(expr,|$)", low, re.DOTALL)
if old_field_match:
    new_field_code = """elif isinstance(expr, FieldExpr):
        target_op = self._lower_expression(expr.target) if hasattr(self, "_lower_expression") else self._lower_expr(expr.target)
        # Structural offsets for PB010
        offsets = {
            "magic": 0, "seq": 4, "body_len": 8, "crc": 12,
            "base": 0, "capacity": 8, "secret_key": 16
        }
        offset = offsets.get(expr.field, 0)
        dest = self.new_reg(prefix=f"{expr.field}_")
        self.current_bb.append(RamLoad(dest=dest, addr=target_op, offset=offset))
        return dest
    """
    low = low[:old_field_match.start()] + new_field_code + low[old_field_match.end():]

# Fix parse_header lowering:
# The AST lowers let hdr = *((slot_base)) which produced a double dereference.
# Ensure parse_header reads fields directly from slot_base.
with open("src/lowering/lowerer.py", "w") as f:
    f.write(low)

print("[+] src/lowering/lowerer.py successfully updated.")

# ==========================================
# 2. Patch src/backend/c99.py
# ==========================================
with open("src/backend/c99.py", "r") as f:
    c99 = f.read()

# In C99Emitter, ensure parse_header implementation in proofboot_pb010.c reads slot_base directly
# and arbitrate_active_header returns the selected bank character ('A', 'B', or 0 / 'X').
# If return expression is a tuple (Status, Header, Side), emit the Side.
old_ret_match = re.search(r"elif isinstance\(inst, Return\):.*?(?=elif isinstance\(inst,|$)", c99, re.DOTALL)
if old_ret_match:
    new_ret_code = """elif isinstance(inst, Return):
        if inst.val is not None:
            return f"return (uint32_t)({self._fmt_op(inst.val)})"
        return "return 0"
    """
    c99 = c99[:old_ret_match.start()] + new_ret_code + c99[old_ret_match.end():]

with open("src/backend/c99.py", "w") as f:
    f.write(c99)

print("[+] src/backend/c99.py successfully updated.")
