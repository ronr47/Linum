#!/usr/bin/env bash
set -euo pipefail

echo "============================================================"
echo "         LINUM: APPLYING CRUCIBLE TRUTH REPAIR              "
echo "============================================================"

VERIFIER_PATH="src/linum/semantic/verifier.py"

if [ ! -f "$VERIFIER_PATH" ]; then
    echo "[-] Error: Verifier file not found at $VERIFIER_PATH"
    exit 1
fi

# Apply the topological knot & borrow target resolution repair
python3 - << 'PYEOF'
import re
from pathlib import Path

target_file = Path("src/linum/semantic/verifier.py")
content = target_file.read_text(encoding="utf-8")

# Replacement pattern for visit_BorrowBlockStmt handling
replacement = '''    def visit_BorrowBlockStmt(self, node):
        target_raw = getattr(node, "target", None)
        target_ident = getattr(target_raw, "id", None) or getattr(target_raw, "name", None) or (str(target_raw) if target_raw is not None else None)
        
        if not target_ident or target_ident == "None":
            raise DiagnosticError("Borrow target is unbound or malformed in scope", span=getattr(node, "span", None))
        
        if hasattr(self, "manifold") and self.manifold is not None:
            if hasattr(self.manifold, "is_live") and not self.manifold.is_live(target_ident):
                raise DiagnosticError(f"Borrow target '{target_ident}' does not exist in the active linear frame", span=getattr(node, "span", None))
            if hasattr(self.manifold, "has_active_exclusive_borrow") and self.manifold.has_active_exclusive_borrow(target_ident):
                raise DiagnosticError(f"Borrow Invalidation Hazard: '{target_ident}' is already locked in a linear knot", span=getattr(node, "span", None))
            if hasattr(self.manifold, "bind_borrow"):
                self.manifold.bind_borrow(target_ident, getattr(node, "borrow_id", 0), getattr(node, "span", None))
'''

# Replace existing visit_BorrowBlockStmt method
pattern = r'    def visit_BorrowBlockStmt\(self,\s*node\):.*?(?=\n    def |\Z)'
if re.search(pattern, content, flags=re.DOTALL):
    new_content = re.sub(pattern, replacement, content, count=1, flags=re.DOTALL)
    target_file.write_text(new_content, encoding="utf-8")
    print("  [✔] Repaired BorrowBlockStmt attribute dispatch in " + str(target_file))
else:
    print("  [!] visit_BorrowBlockStmt pattern not matched directly; appending patch.")
    target_file.write_text(content + "\n" + replacement, encoding="utf-8")
PYEOF

echo "[✔] Epistemic verifier patch complete."
