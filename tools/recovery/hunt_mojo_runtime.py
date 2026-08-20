import os, sys

dev_path = "/dev/sdb"
out_dir = "/home/ron/linum/carved_mojo"
os.makedirs(out_dir, exist_ok=True)

targets = [b"mojo", b"max", b"deep_memory", b"sd_runtime", b"monolight", b"vortex_core"]

print("============================================================")
print(" 🔍 HUNTING FOR MOJO RUNTIME & STORAGE ASSETS ON /dev/sdb")
print("============================================================")

CHUNK = 32 * 1024 * 1024
# Scan across the disk in 32MB strides
with open(dev_path, "rb") as f:
    for chunk_id in range(256): # Scan first 8 GB of raw drive
        off = chunk_id * CHUNK
        f.seek(off)
        buf = f.read(CHUNK)
        if not buf:
            break
        for tgt in targets:
            pos = 0
            while True:
                idx = buf.find(tgt, pos)
                if idx == -1:
                    break
                abs_off = off + idx
                ctx = buf[max(0, idx - 40):min(len(buf), idx + 120)]
                readable = "".join(chr(b) if 32 <= b < 127 else " " for b in ctx).strip()
                if any(k in readable.lower() for k in ["mojo", "runtime", "memory", "storage", "link", "kernel", "vortex"]):
                    print(f"[★] Match '{tgt.decode()}' at 0x{abs_off:08X} ({abs_off // (1024*1024)} MB)")
                    print(f"    Context: {readable[:130]}")
                pos = idx + len(tgt) + 32
