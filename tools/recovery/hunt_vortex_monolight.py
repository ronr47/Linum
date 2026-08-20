import os, struct, subprocess

dev_path = "/dev/sdb3"
out_dir = "/home/ron/linum/carved_vortex"
os.makedirs(out_dir, exist_ok=True)

targets = [
    b"hyper-tower",
    b"vortex",
    b"monolight",
    b"gkl_override",
    b"glk_override",
    b"ref: refs/heads/",
    b"[package]",
    b"bare_metal",
    b"crucible"
]

print("============================================================")
print(f" 🔍 SCANNING {dev_path} FOR VORTEX & MONOLIGHT WORKSPACES")
print("============================================================")

CHUNK_SIZE = 64 * 1024 * 1024 # 64 MB
MAX_CHUNKS = 128              # Scan first 8 GB

found_records = []

with open(dev_path, "rb") as f:
    for c in range(MAX_CHUNKS):
        base = c * CHUNK_SIZE
        try:
            buf = f.read(CHUNK_SIZE)
            if not buf:
                break
        except Exception as e:
            print(f"[!] Read error at chunk {c}: {e}")
            break

        for tgt in targets:
            pos = 0
            while True:
                idx = buf.find(tgt, pos)
                if idx == -1:
                    break
                abs_off = base + idx
                
                # Sniff surrounding 256 bytes for context
                start = max(0, idx - 64)
                end = min(len(buf), idx + 192)
                raw_ctx = buf[start:end]
                readable = "".join(chr(b) if 32 <= b < 127 else " " for b in raw_ctx).strip()
                
                # Filter out pure noise / binary spam
                if any(w in readable.lower() for w in ["vortex", "monolight", "tower", "kernel", "override", "sophia", "git", "cargo", "main"]):
                    print(f"\n[★] Target Match '{tgt.decode(errors='ignore')}': Offset 0x{abs_off:08X} ({abs_off // (1024*1024)} MB)")
                    print(f"    Context: {readable[:140]}")
                    found_records.append((abs_off, tgt, readable))
                
                pos = idx + len(tgt) + 32
                if len(found_records) >= 30:
                    break
        if len(found_records) >= 30:
            break

print(f"\n[✔] Workspace Scan complete. Found {len(found_records)} high-value anchors.")
