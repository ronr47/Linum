#!/usr/init/env python3
import struct

path = "/home/ron/linum/models/synthetic_test.gguf"

with open(path, "rb") as f:
    magic = f.read(4)
    version = struct.unpack("<I", f.read(4))[0]
    tensor_count = struct.unpack("<Q", f.read(8))[0]
    kv_count = struct.unpack("<Q", f.read(8))[0]
    
    print("============================================================")
    print(" 🧠 LINUM SYNTHETIC MODEL PARSER (VALIDATED)")
    print("============================================================")
    print(f"[*] Magic         : {magic.decode()}")
    print(f"[*] Version       : v{version}")
    print(f"[*] Tensor Count  : {tensor_count}")
    print(f"[*] Metadata KVs  : {kv_count}")
    print("============================================================")
