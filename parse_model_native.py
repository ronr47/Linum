#!/usr/bin/env python3
import struct
import os

MODEL_PATH = "/home/ron/linum/models/model.gguf"
MAGIC = b'GGUF'

def inspect_gguf():
    print("============================================================")
    print(" 🧠 LINUM NATIVE GGUF MODEL INSPECTOR")
    print("============================================================")
    
    if not os.path.exists(MODEL_PATH):
        print(f"[!] Error: Model not found at {MODEL_PATH}")
        return

    file_size = os.path.getsize(MODEL_PATH)
    print(f"[*] Target Model : {MODEL_PATH}")
    print(f"[*] Size         : {file_size / (1024*1024):.2f} MB")

    with open(MODEL_PATH, "rb") as f:
        magic = f.read(4)
        if magic != MAGIC:
            print(f"[!] Invalid GGUF magic header: {magic!r}")
            return
        
        version = struct.unpack("<I", f.read(4))[0]
        tensor_count = struct.unpack("<Q", f.read(8))[0]
        metadata_kv_count = struct.unpack("<Q", f.read(8))[0]

        print(f"    [✔] Magic Header   : {magic.decode('utf-8')}")
        print(f"    [✔] GGUF Version   : v{version}")
        print(f"    [✔] Tensor Count   : {tensor_count}")
        print(f"    [✔] Metadata KVs   : {metadata_kv_count}")
        print("------------------------------------------------------------")
        print(" [✔] MODEL HEADERS PARSED SUCCESSFULLY • MEM-MAP READY")
        print("============================================================")

if __name__ == "__main__":
    inspect_gguf()
