from pathlib import Path
import re

src_dir = Path("linum/src")
for p in src_dir.glob("**/*.py"):
    content = p.read_text()
    if "stub" in content.lower() or "matrix" in content.lower() or "det" in content.lower():
        print(f"=== {p} ===")
        for line in content.splitlines():
            if any(k in line.lower() for k in ["stub", "matrix", "det", "%"]):
                print(f"  {line}")
