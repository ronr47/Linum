import re

kernel_path = "/home/ron/linum/kernel64_unified.c"

with open(kernel_path, "r") as f:
    content = f.read()

# Locate the 3-round execution constraint loop loop structure
old_loop = "for (uint64_t round = 1; round <= 3; round++) {"
new_loop = "for (uint64_t round = 1; round <= 1000; round++) {"

if old_loop in content:
    content = content.replace(old_loop, new_loop)
    with open(kernel_path, "w") as f:
        f.write(content)
    print("[✔] Exokernel Profile Depth successfully expanded to 1,000 hardware compilation rounds.")
else:
    print("[!] Target loop pattern not matched. Verify your manual kernel source state entries.")
