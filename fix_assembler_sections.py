bootloader_path = "/home/ron/linum/boot64_unified.asm"

with open(bootloader_path, "r") as f:
    lines = f.readlines()

# Clean out any leftover variations of raw origin declarations
filtered_lines = []
for line in lines:
    if "org 0x" in line.lower() or "[org" in line.lower():
        continue
    filtered_lines.append(line)

# Ensure it starts with the correct section wrapper layout for object file emission
if "[BITS 16]" in filtered_lines[0]:
    filtered_lines.insert(1, "SECTION .text\n")

with open(bootloader_path, "w") as f:
    f.writelines(filtered_lines)

print("[✔] boot64_unified.asm section attributes re-aligned for object file compilation.")
