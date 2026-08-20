#!/usr/bin/env bash
set -euo pipefail

echo "============================================================"
echo "    ⚡ LINUM 2050: DEFINITIVE EPISTEMIC CRUCIBLE REPAIR     "
echo "============================================================"

python3 - << 'PYEOF'
import re
from pathlib import Path

vpath = Path("src/linum/semantic/verifier.py")
txt = vpath.read_text(encoding="utf-8")

# 1. Ensure DiagnosticError is accessible
if "from linum.diagnostics import DiagnosticError" not in txt:
    txt = "from linum.diagnostics import DiagnosticError\n" + txt

# 2. Extract AST property resolution safely without stringifying None as "None"
def_clean_extractor = '''
def _extract_ast_ident(target) -> str:
    if target is None:
        return ""
    if isinstance(target, str):
        return "" if target == "None" else target
    for attr in ("id", "name", "symbol", "var_name", "target", "value"):
        val = getattr(target, attr, None)
        if val is not None and not callable(val):
            resolved = _extract_ast_ident(val)
            if resolved:
                return resolved
    s = str(target)
    return "" if s in ("None", "") else s
'''

if "_extract_ast_ident" not in txt:
    txt = def_clean_extractor + "\n" + txt

# 3. Clean and replace the statement verification gate
verifier_implementation = '''
    def _verify_stmt(self, stmt, env, linear_resources):
        stmt_type = stmt.__class__.__name__

        # Match Borrow Stmt Nodes across all AST dialect variations
        if "Borrow" in stmt_type:
            raw_target = getattr(stmt, "target", getattr(stmt, "source", getattr(stmt, "var", None)))
            target_name = _extract_ast_ident(raw_target)

            if not target_name:
                raise DiagnosticError("Borrow target is unbound or malformed in scope", span=getattr(stmt, "span", None))

            if target_name not in linear_resources and target_name not in env:
                raise DiagnosticError(f"Borrow target '{target_name}' cannot be resolved in active linear frame", span=getattr(stmt, "span", None))

            if not hasattr(self, "_active_borrows"):
                self._active_borrows = set()

            if target_name in self._active_borrows:
                raise DiagnosticError(f"Borrow Invalidation Hazard: '{target_name}' is already borrowed", span=getattr(stmt, "span", None))

            alias_name = _extract_ast_ident(getattr(stmt, "borrow_alias", getattr(stmt, "alias", "alias_handle")))
            
            self._active_borrows.add(target_name)
            borrow_env = dict(env)
            borrow_linear = set(linear_resources)
            if alias_name:
                borrow_env[alias_name] = "BORROW"

            body = getattr(stmt, "body", getattr(stmt, "block", []))
            if hasattr(body, "statements"):
                body = body.statements

            try:
                self._verify_block(body, borrow_env, borrow_linear)
            finally:
                self._active_borrows.discard(target_name)
            return

        # Match Move / Invalidation Nodes
        if "Move" in stmt_type or "Consume" in stmt_type or getattr(stmt, "is_move", False):
            src_raw = getattr(stmt, "source", getattr(stmt, "src", getattr(stmt, "value", None)))
            src_name = _extract_ast_ident(src_raw)

            if hasattr(self, "_active_borrows") and src_name in self._active_borrows:
                raise DiagnosticError(f"Borrow Invalidation Hazard: cannot move or mutate '{src_name}' during active borrow", span=getattr(stmt, "span", None))

            if src_name in linear_resources:
                linear_resources.remove(src_name)
            return

        # Regular bindings
        if "Let" in stmt_type or "Assign" in stmt_type:
            var_name = _extract_ast_ident(getattr(stmt, "name", getattr(stmt, "target", None)))
            var_type = str(getattr(stmt, "type_annotation", getattr(stmt, "ty", "COPY")))
            if var_name:
                env[var_name] = var_type
                if "LINEAR" in var_type or "unique" in var_type:
                    linear_resources.add(var_name)
            return
'''

if "def _verify_stmt(" in txt:
    txt = re.sub(r'    def _verify_stmt\(self,\s*stmt,\s*env,\s*linear_resources\):.*?(?=\n    def |\Z)', verifier_implementation.strip(), txt, flags=re.DOTALL)
else:
    txt = txt.rstrip() + "\n" + verifier_implementation + "\n"

vpath.write_text(txt, encoding="utf-8")
print("[✔] Epistemic verifier methods reconstructed successfully.")
PYEOF

python3 -m pip install -e . --no-deps --quiet
./linum_truth_gate.sh
