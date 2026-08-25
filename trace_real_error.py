import ast
import inspect
import pathlib
import re
import traceback

path = pathlib.Path("src/linum/cli.py")
text = path.read_text()

print("=== CLI exception handlers ===")
for i, line in enumerate(text.splitlines(), 1):
    if "except Exception" in line or "internal error" in line:
        print(f"{i}: {line}")

print("\n=== CFG lowering entry points ===")
cfg = pathlib.Path("src/linum/lowering/cfg.py")
for i, line in enumerate(cfg.read_text().splitlines(), 1):
    if "def lower_" in line or "sem_decl" in line or ".type" in line:
        print(f"{i}: {line}")

print("\n=== LLVM lowering type accesses ===")
llvm = pathlib.Path("src/linum/lowering/llvm.py")
for i, line in enumerate(llvm.read_text().splitlines(), 1):
    if ".type" in line or "var_types" in line or "_type_to_llvm" in line:
        print(f"{i}: {line}")

print("\n=== AST/semantic tuple-producing code ===")
for root in ("src/linum/semantic", "src/linum/ast", "src/linum"):
    root_path = pathlib.Path(root)
    if not root_path.exists():
        continue

    for p in root_path.rglob("*.py"):
        try:
            lines = p.read_text().splitlines()
        except Exception:
            continue

        for i, line in enumerate(lines, 1):
            if re.search(r"return\s+\([^)]*,[^)]*\)", line):
                print(f"{p}:{i}: {line.strip()}")
