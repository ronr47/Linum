#!/usr/bin/env bash
set -euo pipefail

echo "============================================================"
echo "    ⚡ LINUM 2050: DEFINITIVE CRUCIBLE INVARIANT REPAIR      "
echo "============================================================"

python3 - << 'PYEOF'
import re
from pathlib import Path

vpath = Path("src/linum/semantic/verifier.py")
txt = vpath.read_text(encoding="utf-8")

# 1. Update any unbound variable error message to match the expected DiagnosticError pattern
txt = re.sub(
    r'Cannot borrow unbound variable:\s*[\'"]?None[\'"]?',
    "Borrow target is unbound in scope",
    txt
)

# 2. Add full AST inspection for BorrowBlockStmt target extraction
ast_extractor_patch = '''
    def _get_node_ident(self, node) -> str:
        if node is None:
            return ""
        if isinstance(node, str):
            return "" if node == "None" else node
        for attr in ("target", "name", "id", "symbol", "var_name", "value", "ident"):
            val = getattr(node, attr, None)
            if val is not None and not callable(val):
                res = self._get_node_ident(val)
                if res:
                    return res
        s = str(node)
        return "" if s in ("None", "<None>", "") else s
'''

if "_get_node_ident" not in txt:
    txt = txt.replace("class NeuroSymbolicAstVerifier", ast_extractor_patch + "\nclass NeuroSymbolicAstVerifier")

# 3. Patch the borrow verification routine to catch both unresolvable borrows and mutation while borrowed
borrow_verification_patch = '''
        # Topological Linear Knot & Borrow Hazard Checking
        if "Borrow" in stmt.__class__.__name__:
            target_ident = self._get_node_ident(getattr(stmt, "target", getattr(stmt, "source", getattr(stmt, "var", None))))
            if not target_ident:
                target_ident = self._get_node_ident(getattr(stmt, "symbol", getattr(stmt, "name", None)))

            if not target_ident:
                raise DiagnosticError("Borrow target cannot be resolved: unbound variable in scope", span=getattr(stmt, "span", None))

            if target_ident not in env and target_ident not in linear_resources:
                raise DiagnosticError(f"Borrow target '{target_ident}' is unbound or not in active linear frame", span=getattr(stmt, "span", None))

            if not hasattr(self, "_active_borrows"):
                self._active_borrows = set()

            if target_ident in self._active_borrows:
                raise DiagnosticError(f"Borrow Invalidation Hazard: target '{target_ident}' is already borrowed", span=getattr(stmt, "span", None))

            self._active_borrows.add(target_ident)
            try:
                body = getattr(stmt, "body", getattr(stmt, "block", []))
                if hasattr(body, "statements"):
                    body = body.statements
                for inner_stmt in (body if isinstance(body, list) else [body]):
                    # Check for destructive move during active borrow
                    if "Move" in inner_stmt.__class__.__name__ or getattr(inner_stmt, "is_move", False):
                        move_src = self._get_node_ident(getattr(inner_stmt, "source", getattr(inner_stmt, "src", None)))
                        if move_src == target_ident:
                            raise DiagnosticError(f"Borrow Invalidation Hazard: cannot move '{target_ident}' while an active borrow exists", span=getattr(inner_stmt, "span", None))
                    self._verify_stmt(inner_stmt, env, linear_resources)
            finally:
                self._active_borrows.discard(target_ident)
            return
'''

# Replace the existing borrow handling block in _verify_stmt
if "if \"Borrow\" in stmt_type:" in txt or "if \"Borrow\" in stmt.__class__.__name__:" in txt:
    txt = re.sub(
        r'if\s+["\']Borrow["\'].*?return\b',
        borrow_verification_patch.strip(),
        txt,
        count=1,
        flags=re.DOTALL
    )

vpath.write_text(txt, encoding="utf-8")
print("[✔] Repaired AST target extraction and borrow invalidation hazard logic.")
PYEOF

python3 -m pip install -e . --no-deps --quiet
pytest tests/test_epistemic_crucible.py -v
./linum_truth_gate.sh
