import re

boot_path = "/home/ron/linum/boot64_unified.asm"

with open(boot_path, "r") as f:
    lines = f.readlines()

# Extract and isolate data block strings from the footer matrix
clean_asm_lines = []
data_block_accumulators = []
is_extracting_data = False

for line in lines:
    if "BOOT_DRIVE:" in line or "msg_mbr:" in line or "gdt32_start:" in line:
        is_extracting_data = True
    if "times 510" in line:
        is_extracting_data = False
        
    if is_extracting_data:
        data_block_accumulators.append(line)
    else:
        # Prevent double-insertions by keeping non-data labels intact
        if not any(x in line for x in ["gdt32_", "gdt64_", "BOOT_DRIVE", "msg_mbr"]):
            clean_asm_lines.append(line)

# Reconstruct a safe layout by inserting our data definitions right before the 32-bit boundary switch
reconstructed_assembly = []
data_inserted = False

for line in clean_asm_lines:
    if "[BITS 32]" in line and not data_inserted:
        reconstructed_assembly.append("\n; --- Real/Protected Mode Statically Aligned Data Sector ---\n")
        reconstructed_assembly.extend(data_block_accumulators)
        reconstructed_assembly.append("\n")
        data_inserted = True
    reconstructed_assembly.append(line)

# Append the standard master boot record boot sector signature to the footer
reconstructed_assembly.append("times 510 - ($ - $$) db 0\ndw 0xAA55\n")

with open(boot_path, "w") as f:
    f.writelines(reconstructed_assembly)

print("[✔] Bootloader data sector repositioned inside the 16-bit address boundary layout space.")
