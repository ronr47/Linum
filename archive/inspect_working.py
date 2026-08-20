from pathlib import Path
programs_dir = Path("tests/programs")
for p in programs_dir.glob("*.linum"):
    if p.name not in ["matrix_dim_fail.linum", "matrix_det_fail.linum"]:
        print(f"=== {p.name} ===")
        print(p.read_text())
        break
