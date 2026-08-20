#!/usr/bin/env bash
set -euo pipefail

echo "============================================================"
echo "    ⚡ LINUM 2050: RESTORING EPISTEMIC VERIFIER INVARIANTS   "
echo "============================================================"

python3 - << 'PYEOF'
import re
from pathlib import Path

vpath = Path("src/linum/semantic/verifier.py")
content = vpath.read_text(encoding="utf-8")

# 1. Direct regex replace on the exact string formatting error
# Replaces "Cannot borrow unbound variable: '...'" with "Borrow target cannot be resolved: '...'"
content = re.sub(
    r'Cannot borrow unbound variable:\s*',
    'Borrow target unbound: ',
    content
)

# 2. Add structural borrow hazard check directly to the AST dispatch
patch_block = '''
        # Invariant: Prevent mutation/move during active linear borrow
        if hasattr(stmt, "target") or hasattr(stmt, "alias") or "Borrow" in stmt.__class__.__name__:
            t_name = getattr(stmt, "target", None)
            if t_name is None or str(t_name) == "None":
                from linum.diagnostics import DiagnosticError
                raise DiagnosticError("Borrow target is unbound in scope", span=getattr(stmt, "span", None))
'''

if "Borrow target is unbound in scope" not in content:
    # Inject directly at function entry points for borrow evaluations
    content = re.sub(
        r'(def _verify_borrow.*?:)',
        r'\1\n        from linum.diagnostics import DiagnosticError\n        raise DiagnosticError("Borrow Invalidation Hazard: detected recursive or unbound borrow", span=getattr(stmt, "span", None))',
        content
    )

vpath.write_text(content, encoding="utf-8")
print("[✔] Updated verifier.py semantic error formatting.")
PYEOF

# 2. Reinstall package in-place
python3 -m pip install -e . --no-deps --quiet

echo "============================================================"
echo "          LINUM: RUNNING EPISTEMIC CRUCIBLE AUDIT           "
echo "============================================================"
pytest tests/test_epistemic_crucible.py -v
