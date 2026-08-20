from pathlib import Path

src_dir = Path("linum/src")
for p in src_dir.glob("**/*.py"):
    content = p.read_text()
    if "visit_binary" in content or "BinOp" in content or "det" in content or "matrix" in content:
        print(f"=== {p} ===")
        for line in content.splitlines():
            if any(k in line.lower() for k in ["bin", "mul", "det", "matrix", "visit", "type"]):
                print(f"  {line}")
