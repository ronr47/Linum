file_path = "tests/test_program_pipeline.py"
with open(file_path, "r") as f:
    lines = f.readlines()

start = 300
end = 350
for i in range(start - 1, min(end, len(lines))):
    print(f"{i+1}: {lines[i]}", end="")
