import os

dev_path = "/dev/sdb2"
out_dir = "/home/ron/linum/carved_sophia"
os.makedirs(out_dir, exist_ok=True)

offsets = [0x23AC23A0, 0x36E16A58, 0x42DEC150]

print("============================================================")
print(" 🔍 EXTRACTING SOPHIA DATA BLOCKS FROM /dev/sdb2")
print("============================================================")

with open(dev_path, "rb") as f:
    for idx, off in enumerate(offsets):
        # Seek 4 KB before hit to grab the full record context
        start_off = max(0, off - 4096)
        f.seek(start_off)
        raw_bytes = f.read(65536) # 64 KB chunk
        
        fname = os.path.join(out_dir, f"sophia_chunk_{idx}_0x{off:08X}.bin")
        with open(fname, "wb") as out_f:
            out_f.write(raw_bytes)
            
        print(f"\n[★] Dumped chunk #{idx} to {fname}")
        
        # Extract ASCII/UTF-8 strings longer than 10 characters
        lines = []
        cur = []
        for b in raw_bytes:
            if 32 <= b <= 126 or b in (10, 13, 9):
                cur.append(chr(b))
            else:
                if len(cur) >= 10:
                    lines.append("".join(cur))
                cur = []
        if len(cur) >= 10:
            lines.append("".join(cur))
            
        # Filter for relevant keywords
        hits = [l for l in lines if any(k in l.lower() for k in ["sophia", "app", "def", "fn", "import", "class", "let", "const"])]
        print(f"    ▶ Relevant strings found ({len(hits)} lines):")
        for h in hits[:12]:
            print(f"      {h.strip()}")
