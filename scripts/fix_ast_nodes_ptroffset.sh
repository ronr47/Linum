#!/usr/bin/env bash
set -e

PY_BIN="$( [ -f "./.venv/bin/python" ] && echo "./.venv/bin/python" || echo "$(which python3)" )"
export PYTHONPATH=".:$PYTHONPATH"

$PY_BIN - <<'PY_EOF'
from pathlib import Path

nodes_path = Path("src/linum/ast/nodes.py")
nodes_src = nodes_path.read_text()

correct_ptroffset = '''class PtrOffsetExpr(ASTNode):
    def __init__(self, base_ptr_expr: ASTNode, offset_expr: ASTNode, span=None):
        super().__init__(span)
        self.base_ptr_expr = base_ptr_expr
        self.offset_expr = offset_expr

    def check_type(self, ctx):
        from linum.semantic.types import PRIMITIVE_INTEGER

        base_type = self.base_ptr_expr.check_type(ctx)
        offset_type = self.offset_expr.check_type(ctx)

        if getattr(base_type, "name", None) != "ptr":
            raise TypeError(
                f"Pointer arithmetic requires ptr base, got {base_type!r}"
            )

        if offset_type != PRIMITIVE_INTEGER:
            raise TypeError(
                f"Pointer arithmetic requires INTEGER offset, got {offset_type!r}"
            )

        return base_type

    def check_ownership(self, flow, ctx, next_borrow_id):
        from linum.semantic.analyzer import SemPtrOffsetExpr
        flow, sem_base = self.base_ptr_expr.check_ownership(flow, ctx, next_borrow_id)
        flow, sem_offset = self.offset_expr.check_ownership(flow, ctx, next_borrow_id)
        base_type = self.check_type(ctx)
        return flow, SemPtrOffsetExpr(base_ptr=sem_base, offset=sem_offset, type=base_type)

    def check(self, ctx):
        return self.check_type(ctx)
'''

import re
pattern = r'class PtrOffsetExpr\(ASTNode\):.*?(?=\nclass |\Z)'
nodes_src = re.sub(pattern, correct_ptroffset.strip(), nodes_src, flags=re.DOTALL)
nodes_path.write_text(nodes_src)
print("  [+] Fixed PtrOffsetExpr in src/linum/ast/nodes.py with super().__init__ and clean annotations.")
PY_EOF
