path = 'src/linum/cli.py'

with open(path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

new_lines = []
skip = False

for i, line in enumerate(lines):
    # Detect the beginning of the broken except block
    if "except Exception as e:" in line:
        new_lines.append(line) # Keep the except statement line
        # Force the next two lines to have perfect 4-space indentation
        new_lines.append("    import traceback\n")
        new_lines.append("    traceback.print_exc()\n")
        skip = True
        print(f"Aligned the except block at line {i+1} successfully.")
        continue
        
    # Skip the original broken unindented lines so we don't duplicate them
    if skip and ("import traceback" in line or "traceback.print_exc()" in line):
        if "traceback.print_exc()" in line:
            skip = False # Stop skipping after we pass the broken block
        continue
        
    new_lines.append(line)

with open(path, 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

print("File rewriting completed cleanly.")
