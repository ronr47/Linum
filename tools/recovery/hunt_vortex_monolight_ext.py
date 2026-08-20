import os

dev_path = "/dev/sdb3"
targets = [b"vortex_workstation", b"monolight", b"gkl_override", b"glk_override"]

print("============================================================")
print(" 🔍 EXTENDED SCAN: VORTEX_WORKSTATION & MONOLIGHT")
print("============================================================")

CHUNK_SIZE = 64 * 1024 * 1024
START_CHUNK = 70 # Start at ~4.48 GB mark
MAX_CHUNKS = 200 # Scan through 12.8 GB

with open(dev_path, "rb") as f:
    for c in range(START_CHUNK, MAX_CHUNKS):
        base = c * CHUNK_SIZE
        f.seek(base)
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
                start = max(0, idx - 40)
                end = min(len(buf), idx + 160)
                raw_ctx = buf[start:end]
                readable = "".join(chr(b) if 32 <= b < 127 else " " for b in raw_ctx).strip()
                print(f"[★] Match '{tgt.decode()}': Offset 0x{abs_off:08X} ({abs_off // (1024*1024)} MB)")
                print(f"    Context: {readable[:140]}")
                pos = idx + len(tgt) + 32
