#!/usr/bin/env bash
set -euo pipefail

echo "=== Aligning NeuroSymbolicDiagnosticError in Regge & Quantum ASTs ==="

# 1. Cleanly update src/linum/ast/regge.py
python - <<'PY'
from pathlib import Path
import re

p = Path("src/linum/ast/regge.py")
code = p.read_text(encoding="utf-8")

# Strip any existing verify_euler_characteristic implementations
code = re.sub(r'\n\s+def verify_euler_characteristic\(.*?\):\n\s+""".*?(?=\n\s*def|\nclass|\Z)', '', code, flags=re.DOTALL)

euler_method = """
    def verify_euler_characteristic(self, vertices: int, edges: int, faces: int, expected_chi: int = 2) -> bool:
        \"\"\"Enforces Euler-Poincaré invariant: chi = V - E + F == expected_chi\"\"\"
        actual_chi = vertices - edges + faces
        if actual_chi != expected_chi:
            from linum.semantic.errors import NeuroSymbolicDiagnosticError
            raise NeuroSymbolicDiagnosticError(
                f"Topological Simplex Collapse: Euler characteristic mismatch. Expected chi={expected_chi}, got chi={actual_chi} (V={vertices}, E={edges}, F={faces})",
                str(actual_chi),
                [str(expected_chi)]
            )
        return True
"""
code = code.rstrip() + "\n" + euler_method
p.write_text(code, encoding="utf-8")
print("  -> regge.py aligned.")
PY

# 2. Cleanly update src/linum/ast/quantum.py
python - <<'PY'
from pathlib import Path
import re

p = Path("src/linum/ast/quantum.py")
code = p.read_text(encoding="utf-8")

# Strip any existing verify_unitary_matrix implementations
code = re.sub(r'\n\s+def verify_unitary_matrix\(.*?\):\n\s+""".*?(?=\n\s*def|\nclass|\Z)', '', code, flags=re.DOTALL)

unitary_method = """
    def verify_unitary_matrix(self, matrix: list) -> bool:
        \"\"\"Verifies unitary preservation invariant: U^dagger * U == Identity\"\"\"
        n = len(matrix)
        for i in range(n):
            for j in range(n):
                sum_val = sum(matrix[i][k] * matrix[j][k] for k in range(n))
                expected = 1 if i == j else 0
                if abs(sum_val - expected) > 1e-6:
                    from linum.semantic.errors import NeuroSymbolicDiagnosticError
                    raise NeuroSymbolicDiagnosticError(
                        f"Quantum Unitary Invariant Broken: Matrix is non-unitary at index ({i}, {j})",
                        f"({i},{j})",
                        ["UnitaryPreservingMatrix"]
                    )
        return True
"""
code = code.rstrip() + "\n" + unitary_method
p.write_text(code, encoding="utf-8")
print("  -> quantum.py aligned.")
PY

# 3. Execute Truth Gate
./linum_truth_gate.sh
