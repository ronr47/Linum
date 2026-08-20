from pathlib import Path
programs_dir = Path("tests/programs")
for p in programs_dir.glob("*.linum"):
    content = p.read_text()
    if "%" in content or "matrix" in content or "det" in content:
        print(f"=== {p.name} ===")
        print(content)
