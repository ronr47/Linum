from pathlib import Path
import inspect

# Find where load is defined or used in test_program_pipeline.py
test_file = Path("tests/test_program_pipeline.py")
content = test_file.read_text()
for line in content.splitlines():
    if "def load" in line or "load(" in line:
        print(line)

# Also look at an existing valid .linum program in tests/programs if any exist
programs_dir = Path("tests/programs")
if programs_dir.exists():
    for p in programs_dir.glob("*.linum"):
        if p.name not in ["matrix_dim_fail.linum", "matrix_det_fail.linum"]:
            print(f"--- {p.name} ---")
            print(p.read_text()[:200])
            break
