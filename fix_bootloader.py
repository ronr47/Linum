import re

bootloader_path = "/home/ron/linum/boot64_unified.asm"

with open(bootloader_path, "r") as f:
    lines = f.readlines()

# Force strict size constraints on the jumps throwing phase errors
for i, line in enumerate(lines):
    if "jnc disk_loaded" in line:
        lines[i] = "    jnc strict short disk_loaded\n"

# Verify if msg_mbr is declared at the bottom. If missing, append it safely.
content = "".join(lines)
if "msg_mbr" not in content.splitlines()[-20:]: # Check footer metrics
    # Locate an appropriate padding boundary or append to the end before section shifts
    msg_block = """
; --- Patched Core Data Primitives ---
msg_mbr: db "[+] STAGE-1 (MBR): Booting 64-bit Long Mode Exokernel...", 13, 10, 0
"""
    lines.append(msg_block)

with open(bootloader_path, "w") as f:
    f.writelines(lines)

print("[✔] boot64_unified.asm modified to use strict short branch targets and injected msg_mbr data array descriptor.")
