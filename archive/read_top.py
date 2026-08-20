file_path = "tests/test_program_pipeline.py"
with open(file_path, "r") as f:
    content = f.read()
print("\n".join(content.splitlines()[:40]))
