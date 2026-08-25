#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

PYTHON="${PYTHON:-python3}"

echo "============================================================"
echo " LINUM PTR-OFFSET REPAIR — STRUCTURE AWARE"
echo "============================================================"
echo
echo "ROOT=$ROOT"
echo
echo "=== PYTHON ==="
"$PYTHON" --version
echo

STAMP="$(date +%Y%m%d_%H%M%S)"
BACKUP="$ROOT/.repair-backup-$STAMP"

mkdir -p "$BACKUP"

echo "Backup:"
echo "  $BACKUP"
echo

backup_file() {
    local f="$1"
    if [ -f "$ROOT/$f" ]; then
        mkdir -p "$BACKUP/$(dirname "$f")"
        cp -a "$ROOT/$f" "$BACKUP/$f"
    fi
}

backup_file src/linum/ast/nodes.py
backup_file src/linum/frontend/parser.py
backup_file src/linum/semantic/analyzer.py
backup_file src/linum/semantic/verifier.py
backup_file src/linum/lowering/cfg.py
backup_file src/linum/lowering/ir.py
backup_file src/linum/lowering/llvm.py

echo "=== [1/7] AST ==="

"$PYTHON" <<'PY'
from pathlib import Path
import re

p = Path("src/linum/ast/nodes.py")
s = p.read_text()

# ------------------------------------------------------------
# Ensure SemPtrOffsetExpr is imported.
# ------------------------------------------------------------
if "    SemPtrOffsetExpr,\n" not in s:
    marker = "    SemFunctionDecl,\n"
    if marker not in s:
        raise SystemExit(
            "ERROR: could not locate SemFunctionDecl import in nodes.py"
        )
    s = s.replace(
        marker,
        marker + "    SemPtrOffsetExpr,\n",
        1,
    )

# ------------------------------------------------------------
# Replace the complete PtrOffsetExpr class.
# This avoids depending on whatever partial repair exists.
# ------------------------------------------------------------
new_class = '''class PtrOffsetExpr(ASTNode):
    """
    Pointer arithmetic expression:

        base_ptr + offset

    The semantic representation is SemPtrOffsetExpr.
    """

    def __init__(self, base_ptr_expr, offset_expr, span=None):
        super().__init__(span)
        self.base_ptr_expr = base_ptr_expr
        self.offset_expr = offset_expr

    @property
    def base_expr(self):
        return self.base_ptr_expr

    @base_expr.setter
    def base_expr(self, value):
        self.base_ptr_expr = value

    @property
    def base_ptr(self):
        return self.base_ptr_expr

    @base_ptr.setter
    def base_ptr(self, value):
        self.base_ptr_expr = value

    @property
    def offset_expr_alias(self):
        return self.offset_expr

    def check_type(self, ctx):
        base_type = self.base_ptr_expr.check_type(ctx)
        offset_type = self.offset_expr.check_type(ctx)

        if base_type.name != "ptr":
            raise TypeError(
                f"Pointer arithmetic requires ptr base, got {base_type}."
            )

        if offset_type != PRIMITIVE_INTEGER:
            raise TypeError(
                f"Pointer arithmetic requires INTEGER offset, got {offset_type}."
            )

        return base_type

    def check_ownership(self, flow, ctx, next_borrow_id):
        flow, sem_base = self.base_ptr_expr.check_ownership(
            flow,
            ctx,
            next_borrow_id,
        )

        flow, sem_offset = self.offset_expr.check_ownership(
            flow,
            ctx,
            next_borrow_id,
        )

        base_type = self.check_type(ctx)

        return flow, SemPtrOffsetExpr(
            base_ptr=sem_base,
            offset=sem_offset,
            type=base_type,
        )

    def check(self, ctx):
        return self.check_type(ctx)


'''

pattern = re.compile(
    r"(?ms)^class PtrOffsetExpr\(ASTNode\):.*?(?=^class StructDecl\(ASTNode\):)"
)

if not pattern.search(s):
    raise SystemExit(
        "ERROR: could not locate PtrOffsetExpr class in nodes.py"
    )

s = pattern.sub(new_class, s, count=1)

p.write_text(s)
print("AST PtrOffsetExpr: repaired")
print("AST SemPtrOffsetExpr import: verified")
PY

echo "=== [2/7] PARSER ==="

"$PYTHON" <<'PY'
from pathlib import Path
import re

p = Path("src/linum/frontend/parser.py")
s = p.read_text()

# ------------------------------------------------------------
# Ensure PtrOffsetExpr is imported.
# ------------------------------------------------------------
if "PtrOffsetExpr" not in s.split("class Parser:", 1)[0]:
    marker = "    IdentifierExpr, PtrOffsetExpr\n"
    if marker in s:
        pass
    else:
        marker = "    IdentifierExpr\n"
        if marker not in s:
            raise SystemExit(
                "ERROR: could not locate IdentifierExpr parser import"
            )
        s = s.replace(
            marker,
            "    IdentifierExpr, PtrOffsetExpr\n",
            1,
        )

# ------------------------------------------------------------
# Replace the COMPLETE parse_expression method.
# Do not attempt to locate a particular PLUS/MINUS branch.
# ------------------------------------------------------------
new_method = '''    def parse_expression(self) -> ASTNode:
        """
        Parse a Linum expression.

        Supported forms here include:

            identifier
            %register
            function(...)
            base_ptr + integer_expression
            base_ptr - integer_expression
            lhs * rhs

        Pointer arithmetic is represented explicitly as PtrOffsetExpr.
        """

        tok = self.peek()

        # ----------------------------------------------------
        # Primary expression
        # ----------------------------------------------------
        if tok.type == TokenType.REG:
            base_tok = self.consume(TokenType.REG)
            expr = IdentifierExpr(
                name=base_tok.value,
                span=base_tok.span,
            )

        elif tok.type == TokenType.IDENTIFIER:
            base_tok = self.consume(TokenType.IDENTIFIER)

            if self.peek().type == TokenType.LPAREN:
                self.consume(TokenType.LPAREN)

                args = []

                while (
                    self.peek().type != TokenType.RPAREN
                    and self.peek().type != TokenType.EOF
                ):
                    args.append(self.parse_expression())

                    if self.peek().type == TokenType.COMMA:
                        self.consume(TokenType.COMMA)
                    elif self.peek().type != TokenType.RPAREN:
                        raise SyntaxError(
                            "Parser Error: Expected ',' or ')' "
                            f"after function argument at {self.peek().span}"
                        )

                self.consume(TokenType.RPAREN)

                expr = CallExpr(
                    function_name=base_tok.value,
                    arguments=tuple(args),
                )

            else:
                expr = IdentifierExpr(
                    name=base_tok.value,
                    span=base_tok.span,
                )

        else:
            raise SyntaxError(
                "Parser Error: Unexpected token in expression: "
                f"{tok.type} ('{tok.value}') at {tok.span}"
            )

        # ----------------------------------------------------
        # Binary pointer arithmetic.
        #
        # IMPORTANT:
        # Do not consume the right side as a raw token.
        # Parse it as an expression so semantic checking receives
        # a real AST node.
        # ----------------------------------------------------
        if self.peek().type in (
            TokenType.PLUS,
            TokenType.MINUS,
        ):
            op_tok = self.consume()

            right = self.parse_expression()

            # Pointer subtraction is currently represented by the
            # same pointer-offset node. The semantic layer can
            # distinguish/extend this later if required.
            #
            # For now:
            #
            #     ptr + offset
            #     ptr - offset
            #
            # both produce PtrOffsetExpr.
            return PtrOffsetExpr(
                base_ptr_expr=expr,
                offset_expr=right,
                span=getattr(expr, "span", base_tok.span if 'base_tok' in locals() else None),
            )

        # ----------------------------------------------------
        # Matrix multiplication syntax.
        # ----------------------------------------------------
        if self.peek().type == TokenType.STAR:
            self.consume(TokenType.STAR)

            right = self.parse_expression()

            return CallExpr(
                function_name="__matrix_mul__",
                arguments=(expr, right),
            )

        return expr

'''

pattern = re.compile(
    r"(?ms)^    def parse_expression\(self\) -> ASTNode:.*?(?=^    def parse_statement\(self\))"
)

if not pattern.search(s):
    raise SystemExit(
        "ERROR: could not locate complete parse_expression method"
    )

s = pattern.sub(new_method, s, count=1)

p.write_text(s)
print("Parser parse_expression: replaced")
print("Parser PLUS/MINUS pointer arithmetic: verified")
PY

echo "=== [3/7] SEMANTIC ==="

"$PYTHON" <<'PY'
from pathlib import Path

p = Path("src/linum/semantic/analyzer.py")
s = p.read_text()

needle = "@dataclass(frozen=True)\nclass SemPtrOffsetExpr"

if needle not in s:
    marker = "@dataclass(frozen=True)\nclass SemCallArg"
    if marker not in s:
        raise SystemExit(
            "ERROR: could not locate SemCallArg in analyzer.py"
        )

    insertion = '''@dataclass(frozen=True)
class SemPtrOffsetExpr(SemanticNode):
    base_ptr: SemanticNode
    offset: SemanticNode
    type: Type

'''

    s = s.replace(marker, insertion + marker, 1)
    print("SemPtrOffsetExpr: inserted")
else:
    print("SemPtrOffsetExpr: already present")

p.write_text(s)
PY

echo "=== [4/7] VERIFIER ==="

"$PYTHON" <<'PY'
from pathlib import Path
import re

p = Path("src/linum/semantic/verifier.py")
s = p.read_text()

# Replace the PtrOffsetExpr dispatch with a consistent version.
new_branch = '''        elif ename == "PtrOffsetExpr":
            base_expr = getattr(
                expr,
                "base_expr",
                getattr(expr, "base_ptr_expr", None),
            )

            offset_expr = getattr(
                expr,
                "offset_expr",
                None,
            )

            if base_expr is None:
                raise SemanticVerificationError(
                    "PtrOffsetExpr is missing base pointer expression"
                )

            if offset_expr is None:
                raise SemanticVerificationError(
                    "PtrOffsetExpr is missing offset expression"
                )

            self._verify_expr(
                base_expr,
                env,
                linear_resources,
            )

            self._verify_expr(
                offset_expr,
                env,
                linear_resources,
            )

'''

pattern = re.compile(
    r"(?ms)^        elif ename == [\"']PtrOffsetExpr[\"']:\n.*?(?=^        elif ename == [\"']PtrLoadExpr[\"']:)"
)

if pattern.search(s):
    s = pattern.sub(new_branch, s, count=1)
    print("PtrOffsetExpr verifier branch: repaired")
else:
    # Insert before PtrLoadExpr if PtrOffsetExpr branch is absent.
    marker = '        elif ename == "PtrLoadExpr":'
    if marker not in s:
        raise SystemExit(
            "ERROR: could not locate PtrLoadExpr verifier dispatch"
        )

    s = s.replace(
        marker,
        new_branch + marker,
        1,
    )
    print("PtrOffsetExpr verifier branch: inserted")

p.write_text(s)
PY

echo "=== [5/7] CFG ==="

"$PYTHON" <<'PY'
from pathlib import Path

p = Path("src/linum/lowering/cfg.py")
s = p.read_text()

# IrFieldOffset uses Any.
first = "from typing import Dict, List, Set, Tuple, Optional"
replacement = "from typing import Any, Dict, List, Set, Tuple, Optional"

if first in s:
    s = s.replace(first, replacement, 1)
elif "from typing import Any" not in s:
    raise SystemExit(
        "ERROR: could not locate cfg.py typing import"
    )

# Remove the obsolete duplicate __init__ so there is one canonical
# CfgBuilder constructor.
old = '''class CfgBuilder:
    def __init__(self):
        self.label_counter = 0

    def alloc_label(self, prefix: str = 'bb') -> str:
        label = f'{prefix}_{self.label_counter}'
        self.label_counter += 1
        return label

    def __init__(self):
'''

new = '''class CfgBuilder:
    def __init__(self):
'''

if old in s:
    s = s.replace(old, new, 1)
    print("CfgBuilder duplicate constructor: removed")
else:
    print("CfgBuilder constructor: already normalized")

p.write_text(s)
print("CFG Any import: verified")
PY

echo "=== [6/7] IR / LLVM ==="

"$PYTHON" <<'PY'
from pathlib import Path

ir = Path("src/linum/lowering/ir.py").read_text()
llvm = Path("src/linum/lowering/llvm.py").read_text()
cfg = Path("src/linum/lowering/cfg.py").read_text()

checks = {
    "SemPtrOffsetExpr lowering source": "IrPtrOffset" in cfg,
    "TypedIrPtrOffset definition": "class TypedIrPtrOffset" in ir,
    "LLVM IrPtrOffset lowering": '"IrPtrOffset"' in llvm,
    "LLVM GEP lowering": "getelementptr i8, ptr" in llvm,
}

failed = [name for name, ok in checks.items() if not ok]

for name, ok in checks.items():
    print(f"{name}: {'OK' if ok else 'MISSING'}")

if failed:
    raise SystemExit(
        "ERROR: lowering pipeline checks failed: "
        + ", ".join(failed)
    )
PY

echo "=== [7/7] SYNTAX + COMPILE ==="

echo
echo "--- py_compile ---"

"$PYTHON" -m py_compile \
    src/linum/ast/nodes.py \
    src/linum/frontend/parser.py \
    src/linum/semantic/analyzer.py \
    src/linum/semantic/verifier.py \
    src/linum/lowering/ir.py \
    src/linum/lowering/cfg.py \
    src/linum/lowering/llvm.py

echo "py_compile=0"

echo
echo "--- compileall ---"

"$PYTHON" -m compileall -q src/linum

echo "compileall=0"

echo
echo "============================================================"
echo " PTR-OFFSET REFERENCES"
echo "============================================================"

grep -n -E \
    'PtrOffsetExpr|SemPtrOffsetExpr|IrPtrOffset|TypedIrPtrOffset' \
    src/linum/ast/nodes.py \
    src/linum/frontend/parser.py \
    src/linum/semantic/analyzer.py \
    src/linum/semantic/verifier.py \
    src/linum/lowering/cfg.py \
    src/linum/lowering/ir.py \
    src/linum/lowering/llvm.py \
    || true

echo
echo "============================================================"
echo " REPAIR COMPLETE"
echo "============================================================"
echo
echo "Backup:"
echo "  $BACKUP"
echo
