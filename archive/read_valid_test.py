file_path = "tests/test_program_pipeline.py"
with open(file_path, "r") as f:
    content = f.read()

# Grab the first 40 lines of the file to see working compile_source inputs
print("\n".join(content.splitlines()[:40]))
