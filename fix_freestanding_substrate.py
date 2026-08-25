import re

# --- STEP 1: Inject Bare-Metal expf into kernel64_unified.c ---
kernel_path = "/home/ron/linum/kernel64_unified.c"
with open(kernel_path, "r") as f:
    k_content = f.read()

# Taylor Series custom approximation of expf for freestanding environments
expf_implementation = """
// Freestanding Taylor Series approximation of exponentiation for float streams
float expf(float x) {
    // Handle base-level bounds checking to avoid hardware numeric blowouts
    if (x < -20.0f) return 0.0f;
    if (x > 20.0f) x = 20.0f; 
    float sum = 1.0f;
    float term = 1.0f;
    for (int i = 1; i <= 8; i++) {
        term *= x / (float)i;
        sum += term;
    }
    return sum;
}
"""

if "float expf" not in k_content:
    # Inject right below include headers
    include_end_idx = k_content.find("#include <stddef.h>") + len("#include <stddef.h>")
    k_content = k_content[:include_end_idx] + "\n" + expf_implementation + k_content[include_end_idx:]
    with open(kernel_path, "w") as f:
        f.write(k_content)
    print("[✔] Freestanding expf symbol injected into unified kernel core.")

# --- STEP 2: Enforce Segment Isolation in boot64_unified.asm ---
boot_path = "/home/ron/linum/boot64_unified.asm"
with open(boot_path, "r") as f:
    boot_lines = f.readlines()

# Re-insert distinct sections to safeguard real-mode relative address widths
new_boot_lines = []
for line in boot_lines:
    if "SECTION .text" in line:
        continue # Remove previous generic definition
    if "[BITS 16]" in line:
        new_boot_lines.append("[BITS 16]\nSECTION .text.entry\n")
        continue
    if "[BITS 32]" in line:
        new_boot_lines.append("[BITS 32]\nSECTION .text\n")
        continue
    new_boot_lines.append(line)

with open(boot_path, "w") as f:
    f.writelines(new_boot_lines)
print("[✔] boot64_unified.asm separated into isolated .text.entry and .text buckets.")
