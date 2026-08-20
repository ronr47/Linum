import os

dev_path = "/dev/sdb"
out_dir = "/home/ron/linum/recovered_pyramids_full"
os.makedirs(out_dir, exist_ok=True)

# High-precision anchor offsets confirmed by forensic scans
anchors = [
    (0x72DECDB9, "ring_buffer_pipeline_mojo"),
    (0x72E159FF, "monastic_linker_and_objs"),
    (0x72EA749A, "max_tensor_unsafe_ptr_mojo"),
    (0x79CA7EAD, "gemini_engine_main_mojo"),
    (0x79CC8230, "max_pipeline_runner_mojo"),
    (0x79CDB8CC, "pyramids_multi_lang_makefile"),
    (0x7AD638CC, "host_native_standalone_mojo"),
    (0x849E5DCF, "orion_sync_lowlatency_script"),
    (0x8DE29823, "gemini_vulkan_sysctl_profile")
]

print("============================================================")
print(" 🏛️ CARVING COMPLETE PYRAMIDS & MONASTIC CORE TREES")
print("============================================================")

with open(dev_path, "rb") as f:
    for off, label in anchors:
        start_off = max(0, off - 2048)
        f.seek(start_off)
        raw = f.read(32768)
        
        # Clean printable text into coherent source lines
        lines = []
        cur = []
        for b in raw:
            if 32 <= b <= 126 or b in (10, 13, 9):
                cur.append(chr(b))
            else:
                if len(cur) >= 12:
                    lines.append("".join(cur))
                cur = []
        if len(cur) >= 12:
            lines.append("".join(cur))
            
        full_text = "\n".join(lines)
        fname = os.path.join(out_dir, f"{label}_0x{off:08X}.txt")
        with open(fname, "w") as out_f:
            out_f.write(full_text)
            
        print(f"[★] Carved Artifact: {fname}")
        for l in [line for line in lines if len(line.strip()) > 20][:3]:
            print(f"    ▶ {l.strip()[:100]}")

print("\n============================================================")
print(f" [✔] Full source tree reconstruction written to: {out_dir}")
print("============================================================")
