from pathlib import Path
import re

files = [
    "src/linum/semantic/verifier.py",
    "src/linum/semantic/types.py",
    "src/linum/frontend/parser.py",
    "src/linum/frontend/lexer.py",
]

for filename in files:
    path = Path(filename)
    if not path.exists():
        continue

    print(f"\n{'=' * 72}")
    print(filename)
    print('=' * 72)

    lines = path.read_text().splitlines()

    for i, line in enumerate(lines, 1):
        if any(x in line for x in (
            "REG",
            "IdentifierExpr",
            "_infer_expr_type",
            "lookup(",
            "dead variable",
            "lifetime",
            "env[",
            "env.get",
            "root_context",
            "bind(",
        )):
            lo = max(0, i - 2)
            hi = min(len(lines), i + 2)
            print(f"\n--- line {i} ---")
            for n in range(lo, hi):
                print(f"{n + 1:4}: {lines[n]}")
