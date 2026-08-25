boot_path = "/home/ron/linum/boot64_unified.asm"

with open(boot_path, "r") as f:
    content = f.read()

# Replace any ambiguous generic section calls to secure real-mode data
content = content.replace("[BITS 16]", "[BITS 16]\nSECTION .text.entry")
content = content.replace("[BITS 32]", "[BITS 32]\nSECTION .text")

# Isolate the Global Descriptor Tables out of the first 512-byte section container limits
gdt_split_marker = "align 8\ngdt32_start:"
if gdt_split_marker in content:
    parts = content.split(gdt_split_marker)
    # Wrap the table definitions into a secondary data section page block layer 
    modified_footer = "SECTION .rodata\nalign 8\ngdt32_start:" + parts[1]
    content = parts[0] + modified_footer

with open(boot_path, "w") as f:
    f.write(content)

print("[✔] Bootloader data layers successfully segregated into isolated section blocks.")
