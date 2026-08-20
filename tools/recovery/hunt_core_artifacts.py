import os, sys

dev_path = "/dev/sdb3"
keywords = [
    b"monolight",
    b"hyper-tower-server",
    b"vortex_workstation",
    b"gkl_override",
    b"glk_override",
    b"gkl",
    b"glk",
    b"sophia"
]

print("============================================================")
print(f" 🔍 SCANNING {dev_path} (231 GB) FOR CORE WORKSPACES")
print("============================================================")

CHUNK_SIZE = 32 * 1024 * 1024  # 32 MB chunks
MAX_CHUNKS = 128               # Scan first 4 GB

hits = 0
with open(dev_path, "rb") as f:
    for c in range(MAX_CHUNKS):
        base = c * CHUNK_SIZE
        try:
            buf = f.read(CHUNK_SIZE)
            if not buf:
                break
        except Exception as e:
            print(f"[!] Read error: {e}")
            break

        for kw in keywords:
            pos = 0
            while True:
                idx = buf.find(kw, pos)
                if idx == -1:
                    break
                abs_off = base + idx
                start = max(0, idx - 40)
                end = min(len(buf), idx + 100)
                snippet = "".join(chr(b) if 32 <= b < 127 else "·" for b in buf[start:end])
                print(f"[★] Found '{kw.decode()}': Offset 0x{abs_off:08X} ({abs_off // (1024*1024)} MB)")
                print(f"    Snippet: {snippet}")
                hits += 1
                pos = idx + len(kw) + 16
                if hits >= 25:
                    break
        if hits >= 25:
            break

print(f"\n[✔] Initial slice scan complete. Matches: {hits}")
