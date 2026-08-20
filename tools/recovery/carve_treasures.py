import subprocess
import os
import struct

dev_path = "/dev/sdb2"
out_dir = "/home/ron/linum/carved_sdb2"
os.makedirs(out_dir, exist_ok=True)

offsets = [
    0x02188800, # 34.3 MB
    0x02900800, # 41.9 MB
    0x03F0F800, # 64.5 MB
    0x05E9E800, # 96.8 MB
    0x06103800, # 99.3 MB
    0x06144800, # 99.6 MB
]

print("============================================================")
print(" 🎁 UNVEILING CARVED TREASURES FROM /dev/sdb2")
print("============================================================")

with open(dev_path, "rb") as f:
    for idx, off in enumerate(offsets):
        f.seek(off)
        header = f.read(64)
        if not header.startswith(b"\x7fELF"):
            continue
        
        e_type, e_machine, e_version, e_entry, e_phoff, e_shoff, e_flags, e_ehsize, e_phentsize, e_phnum, e_shentsize, e_shnum, e_shstrndx = struct.unpack(
            "<HHIQQQIHHHHHH", header[16:64]
        )
        
        if e_shoff > 0 and e_shnum > 0:
            total_size = e_shoff + (e_shnum * e_shentsize)
        elif e_phoff > 0 and e_phnum > 0:
            total_size = e_phoff + (e_phnum * e_phentsize) + 131072
        else:
            total_size = 512 * 1024
            
        f.seek(off)
        data = f.read(min(total_size, 16 * 1024 * 1024))
        
        fname = os.path.join(out_dir, f"target_{idx}_0x{off:08X}.elf")
        with open(fname, "wb") as out_f:
            out_f.write(data)
            
        print(f"\n[★] Artifact #{idx} Carved: {fname}")
        print(f"    ▶ Size: {len(data):,} bytes | Entry Point: 0x{e_entry:X} | Headers: {e_phnum} phdr / {e_shnum} shdr")
        
        res_file = subprocess.run(["file", "-b", fname], capture_output=True, text=True).stdout.strip()
        print(f"    ▶ Binary Class: {res_file}")
        
        res_str = subprocess.run(["strings", "-a", fname], capture_output=True, text=True).stdout.splitlines()
        
        keywords = ["sophia", "kernel", "crucible", "vortex", "jit", "ebpf", "quantum", "linum", "baremetal", "hypervisor", "runtime", "payload", "root", "dev_"]
        special_tags = [s for s in res_str if any(kw in s.lower() for kw in keywords)]
        general_clues = [s for s in res_str if len(s) >= 8 and not s.startswith("_") and not s.startswith(".") and " " in s][:8]
        
        if special_tags:
            print(f"    ★ KEY TAGS: {special_tags[:10]}")
        if general_clues:
            print(f"    ▶ STRINGS : {general_clues[:6]}")

print("\n============================================================")
print(" [✔] Carving complete. All extracted binaries in ./carved_sdb2/")
print("============================================================")
