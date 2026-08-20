import os, sys, subprocess

dev_path = "/dev/sdb2"
keywords = [b"sophia", b"SOPHIA", b"crucible", b"recovered_vortex", b"linum_fastjit"]

print("============================================================")
print(" 🔍 HUNTING FOR SOPHIA & CODE ARTIFACTS ON /dev/sdb2")
print("============================================================")

CHUNK_MB = 16
CHUNK_BYTES = CHUNK_MB * 1024 * 1024

found_hits = []

with open(dev_path, "rb") as f:
    # Scan first 2 GB of partition
    for chunk_idx in range(128):
        offset_base = chunk_idx * CHUNK_BYTES
        try:
            buf = f.read(CHUNK_BYTES)
            if not buf:
                break
        except Exception as e:
            print(f"[!] Read error at chunk {chunk_idx}: {e}")
            break

        for kw in keywords:
            pos = 0
            while True:
                idx = buf.find(kw, pos)
                if idx == -1:
                    break
                abs_offset = offset_base + idx
                # Extract surrounding ASCII snippet
                start = max(0, idx - 40)
                end = min(len(buf), idx + 80)
                snippet = "".join(chr(b) if 32 <= b < 127 else "·" for b in buf[start:end])
                
                print(f"[★] Match '{kw.decode()}': Offset 0x{abs_offset:08X} ({abs_offset // (1024*1024)} MB)")
                print(f"    Snippet: {snippet}")
                
                found_hits.append((abs_offset, kw.decode()))
                pos = idx + len(kw) + 16
                if len(found_hits) >= 20:
                    break
        if len(found_hits) >= 20:
            break

print(f"\n[✔] Scan complete. Total matches found: {len(found_hits)}")
