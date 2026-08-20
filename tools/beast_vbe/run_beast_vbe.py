import subprocess
import time
import socket
import os

cd = "/home/ron/linum"
os.chdir(cd)

# 1. Assemble VBE MBR
nasm_src = """[BITS 16]
[ORG 0x7C00]
start:
    cli
    xor ax, ax
    mov ds, ax
    mov es, ax
    mov ss, ax
    mov sp, 0x7C00
    mov [BOOT_DRIVE], dl

    ; Setup Bochs VBE direct I/O for 1024x768x32 LFB
    mov dx, 0x01CE
    mov ax, 1
    out dx, ax
    inc dx
    mov ax, 1024
    out dx, ax

    dec dx
    mov ax, 2
    out dx, ax
    inc dx
    mov ax, 768
    out dx, ax

    dec dx
    mov ax, 3
    out dx, ax
    inc dx
    mov ax, 32
    out dx, ax

    dec dx
    mov ax, 4
    out dx, ax
    inc dx
    mov ax, 0x41        ; VBE_ENABLE | VBE_LFB
    out dx, ax

    ; Read Stage-2 sectors to 0x20000
    mov ax, 0x2000
    mov es, ax
    xor bx, bx
    mov ah, 0x02
    mov al, 16
    mov ch, 0
    mov cl, 2
    mov dh, 0
    mov dl, [BOOT_DRIVE]
    int 0x13
    jnc disk_ok
    hlt

disk_ok:
    in al, 0x92
    or al, 2
    out 0x92, al

    lgdt [gdt_descriptor]
    mov eax, cr0
    or eax, 1
    mov cr0, eax
    jmp 0x08:init_pm32

[BITS 32]
init_pm32:
    mov ax, 0x10
    mov ds, ax
    mov es, ax
    mov fs, ax
    mov gs, ax
    mov ss, ax
    mov esp, 0x90000

    mov esi, 0x20000
    mov edi, 0x100000
    mov ecx, 2048
    rep movsd

    mov eax, 0x100030
    jmp eax

BOOT_DRIVE: db 0
align 8
gdt_start:
    dq 0x0000000000000000
    dq 0x00CF9A000000FFFF
    dq 0x00CF92000000FFFF
gdt_end:
gdt_descriptor:
    dw gdt_end - gdt_start - 1
    dd gdt_start
times 510 - ($ - $$) db 0
dw 0xAA55
"""

with open("mbr_vbe.asm", "w") as f:
    f.write(nasm_src)

subprocess.run(["nasm", "-f", "bin", "mbr_vbe.asm", "-o", "mbr_vbe.bin"], check=True)
subprocess.run(["objcopy", "-O", "binary", "beast_surprise.elf", "beast_surprise.bin"], check=True)

with open("beast_vbe_disk.bin", "wb") as f_out:
    with open("mbr_vbe.bin", "rb") as f_mbr: f_out.write(f_mbr.read())
    with open("beast_surprise.bin", "rb") as f_k: f_out.write(f_k.read())
    # Pad to 16 KB
    cur_len = f_out.tell()
    if cur_len < 16384:
        f_out.write(b'\x00' * (16384 - cur_len))

print("[✔] VBE Bootable Disk Image Built (16384 bytes)")

SOCK_PATH = "/tmp/qemu-vbe-hmp.sock"
PPM_PATH = "/tmp/beast_vbe.ppm"
for p in [SOCK_PATH, PPM_PATH]:
    if os.path.exists(p): os.remove(p)

# 2. Boot in QEMU Headless with VBE graphics adapter
cmd = [
    "qemu-system-x86_64",
    "-drive", "file=beast_vbe_disk.bin,format=raw,if=ide",
    "-vga", "std",
    "-display", "none",
    "-m", "256M",
    "-monitor", f"unix:{SOCK_PATH},server,nowait"
]

proc = subprocess.Popen(cmd)
try:
    time.sleep(1.5)
    s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    s.connect(SOCK_PATH)
    time.sleep(0.2)
    s.recv(1024)
    s.sendall(f"screendump {PPM_PATH}\n".encode())
    time.sleep(0.5)
    s.close()
finally:
    proc.terminate()
    try: proc.wait(timeout=2)
    except subprocess.TimeoutExpired: proc.kill()
    if os.path.exists(SOCK_PATH): os.remove(SOCK_PATH)

if os.path.exists(PPM_PATH):
    with open(PPM_PATH, "rb") as f:
        fmt = f.readline().strip().decode()
        dim = f.readline().strip().decode()
        print(f"[★] Captured Framebuffer -> Format: {fmt} | Resolution: {dim}")
        
    if os.system("which ffmpeg >/dev/null 2>&1") == 0:
        os.system(f"ffmpeg -y -i {PPM_PATH} beast_render.png >/dev/null 2>&1")
        print("[✔] Converted to beast_render.png")
