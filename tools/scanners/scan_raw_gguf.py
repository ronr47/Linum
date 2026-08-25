#!/usr/init/env python3
import os

PARTITIONS = ['/dev/sdb2', '/dev/sdb3', '/dev/sdb5']
MAGIC = b'GGUF'

def scan_raw_slices():
    print("============================================================")
    print(" 🔎 SCANNING RAW SDB PARTITIONS FOR GGUF MAGIC HEADERS")
    print("============================================================")
    
    for part in PARTITIONS:
        print(f"[*] Probing raw blocks on {part}...")
        try:
            with open(part, "rb") as f:
                header = f.read(4)
                if header == MAGIC:
                    print(f"    [✔] FOUND GGUF SIGNATURE AT OFFSET 0 OF {part}!")
                else:
                    print(f"    [-] No immediate header at 0x0 (found: {header!r}). Searching blocks...")
                    found_at = -1
                    chunk_size = 1024 * 1024  # 1MB chunks
                    for offset in range(0, 50 * 1024 * 1024, chunk_size):
                        f.seek(offset)
                        chunk = f.read(chunk_size)
                        idx = chunk.find(MAGIC)
                        if idx != -1:
                            found_at = offset + idx
                            break
                    if found_at != -1:
                        print(f"    [✔] Found GGUF alignment at offset {found_at} (0x{found_at:X}) in {part}!")
                    else:
                        print(f"    [-] No GGUF magic found in initial blocks of {part}.")
        except PermissionError:
            print(f"    [!] Permission denied opening {part}. Run with sudo.")
        except Exception as e:
            print(f"    [!] Error reading {part}: {e}")

if __name__ == "__main__":
    scan_raw_slices()
