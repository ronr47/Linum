#!/usr/bin/env bash
set -euo pipefail

echo "============================================================"
echo "    ⚡ LINUM 2050: EPISTEMIC CRUCIBLE TRUTH RESTORATION      "
echo "============================================================"

python3 - << 'PYEOF'
from pathlib import Path
import re

verifier_path = Path("src/linum/semantic/verifier.py")
content = verifier_path.read_text(encoding="utf-8")

# Ensure DiagnosticError is imported
if "from linum.diagnostics import DiagnosticError" not in content and "DiagnosticError" not in content:
    content = "from linum.diagnostics import DiagnosticError\n" + content

# 1. Surgical extraction & target resolution helper
helper_funcs = '''
def _resolve_ident(node) -> str:
    if node is None:
        return ""
    if isinstance(node, str):
        return node
    for attr in ("id", "name", "value", "target", "ident"):
        val = getattr(node, attr, None)
        if val is not None and not callable(val):
            return str(val)
    return str(node)
'''

if "_resolve_ident" not in content:
    content = helper_funcs + "\n" + content

# 2. Patch _verify_stmt to accurately track active borrow sets & catch invalidation hazards
patch_code = '''
    def _extract_name(self, target) -> str:
        if target is None:
            return ""
        if isinstance(target, str):
            return target
        for attr in ("id", "name", "target", "symbol", "var_name"):
            val = getattr(target, attr, None)
            if val is not None and not callable(val):
                res = self._extract_name(val)
                if res and res != "None":
                    return res
        s = str(target)
        return "" if s == "None" else s

    def _verify_stmt(self, stmt, env, linear_resources):
        stmt_type = stmt.__class__.__name__

        # Handle Borrow Block Statements
        if "Borrow" in stmt_type:
            raw_target = getattr(stmt, "target", getattr(stmt, "source", getattr(stmt, "var", None)))
            target_name = self._extract_name(raw_target)

            if not target_name or target_name == "None":
                raise DiagnosticError(f"Borrow target '{target_name}' is unbound or malformed in scope", span=getattr(stmt, "span", None))

            if target_name not in linear_resources and target_name not in env:
                raise DiagnosticError(f"Borrow target '{target_name}' cannot be resolved in active linear frame", span=getattr(stmt, "span", None))

            alias_name = self._extract_name(getattr(stmt, "borrow_alias", getattr(stmt, "alias", "alias_handle")))

            # Initialize active borrow tracker
            if not hasattr(self, "_active_borrows"):
                self._active_borrows = set()

            if target_name in self._active_borrows:
                raise DiagnosticError(f"Borrow Invalidation Hazard: '{target_name}' is already borrowed", span=getattr(stmt, "span", None))

            self._active_borrows.add(target_name)
            borrow_env = dict(env)
            borrow_linear = set(linear_resources)
            borrow_env[alias_name] = "BORROW"

            body = getattr(stmt, "body", getattr(stmt, "block", []))
            if hasattr(body, "statements"):
                body = body.statements

            try:
                self._verify_block(body, borrow_env, borrow_linear)
            finally:
                self._active_borrows.discard(target_name)
            return

        # Handle Move / Destruction Statements
        if "Move" in stmt_type or "Consume" in stmt_type or getattr(stmt, "is_move", False):
            src_raw = getattr(stmt, "source", getattr(stmt, "src", getattr(stmt, "value", None)))
            src_name = self._extract_name(src_raw)

            if hasattr(self, "_active_borrows") and src_name in self._active_borrows:
                raise DiagnosticError(f"Borrow Invalidation Hazard: cannot move or mutate '{src_name}' during active borrow", span=getattr(stmt, "span", None))

            if src_name in linear_resources:
                linear_resources.remove(src_name)

        # Fallback to existing verification dispatcher if present
        if hasattr(super(), "_verify_stmt"):
            super()._verify_stmt(stmt, env, linear_resources)
'''

# Replace or insert statement verification
if "def _verify_stmt(" in content:
    content = re.sub(r'    def _verify_stmt\(self,\s*stmt,\s*env,\s*linear_resources\):.*?(?=\n    def |\Z)', patch_code.strip(), content, flags=re.DOTALL)
else:
    content = content.rstrip() + "\n" + patch_code + "\n"

verifier_path.write_text(content, encoding="utf-8")
print("[+] src/linum/semantic/verifier.py: Invariant and Hazard gates patched.")
PYEOF

# Reinstall package in-place and run the gate
python3 -m pip install -e . --no-deps --quiet

echo "============================================================"
echo "          LINUM: VERIFYING TRUTH GATE PASS                  "
echo "============================================================"
pytest tests/test_epistemic_crucible.py -v
./linum_truth_gate.sh
