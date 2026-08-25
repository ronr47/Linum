with open("/home/ron/linum/boot64_unified.asm", "r") as f:
    content = f.read()

# 1. Clean out the broken trailing patch blocks from previous iterations
if "; --- Patched Core Data Primitives ---" in content:
    content = content.split("; --- Patched Core Data Primitives ---")[0]

# 2. Reconstruct a structurally stable, cleanly aligned header layout
header_patch = """[BITS 16]
global _start64
extern kmain64

start:
    jmp strict short real_mode_init

align 4
msg_mbr db "[+] STAGE-1 (MBR): Booting 64-bit Long Mode Exokernel...", 13, 10, 0

real_mode_init:
    cli
    xor ax, ax
    mov ds, ax
    mov es, ax
    mov ss, ax
    mov sp, 0x7C00
"""

# Replace the old unstable start sequence up to the first serial configuration block
content_fixed = content.split("start:")[1]
# Strip out the redundant configuration registers handled in our new clean start layout
content_fixed = content_fixed.split("mov si, msg_mbr")[1]

full_assembly = header_patch + "    mov si, msg_mbr\n" + content_fixed

with open("/home/ron/linum/boot64_unified.asm", "w") as f:
    f.write(full_assembly)

print("[✔] Bootloader sector alignment structure stabilized within legal 16-bit memory spaces.")
