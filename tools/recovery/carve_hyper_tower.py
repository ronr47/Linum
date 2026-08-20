import os, sys, re

dev_path = "/dev/sdb3"
out_dir = "/home/ron/linum/recovered_hyper_tower"
os.makedirs(out_dir, exist_ok=True)

# Target base offset around 4251 MB (0x109B00000)
BASE_OFFSET = 0x109B00000
SPAN_BYTES = 64 * 1024 * 1024 # 64 MB chunk to cover the whole project region

print("============================================================")
print(" 📦 CARVING HYPER-TOWER-SERVER ARTIFACTS FROM /dev/sdb3")
print("============================================================")

with open(dev_path, "rb") as f:
    f.seek(BASE_OFFSET)
    data = f.read(SPAN_BYTES)

print(f"[✔] Read {len(data):,} bytes from offset 0x{BASE_OFFSET:X}")

# 1. Carve Markdown / Design Docs
doc_matches = re.finditer(rb"(#+ .*?hyper-tower-server[\s\S]{100,2000}?)(?=\x00|\n\n\n)", data)
for idx, m in enumerate(doc_matches):
    doc_text = m.group(1).decode("utf-8", errors="ignore")
    doc_file = os.path.join(out_dir, f"doc_spec_{idx}.md")
    with open(doc_file, "w") as df:
        df.write(doc_text)
    print(f"\n[★] Recovered Specification Doc #{idx} -> {doc_file}")
    print("    " + "\n    ".join(doc_text.splitlines()[:6]))

# 2. Carve Cargo.toml files
cargo_matches = re.finditer(rb"(\[package\][\s\S]{10,800}?name\s*=\s*\"[^\"]+\"[\s\S]{10,2000}?)(?=\x00|\n\n\n)", data)
for idx, m in enumerate(cargo_matches):
    toml_text = m.group(1).decode("utf-8", errors="ignore")
    toml_file = os.path.join(out_dir, f"Cargo_{idx}.toml")
    with open(toml_file, "w") as tf:
        tf.write(toml_text)
    print(f"\n[★] Recovered Cargo.toml #{idx} -> {toml_file}")
    for line in toml_text.splitlines()[:5]:
        print(f"    {line}")

# 3. Carve Rust source files (containing pub fn or fn main)
rs_matches = re.finditer(rb"((?:use [^\n]+;\n)+(?:#\[[^\n]+\]\n)*(?:pub )?(?:fn|struct|enum|impl) [\s\S]{100,4000}?)(?=\x00{2,}|\n\n\n\n)", data)
for idx, m in enumerate(rs_matches):
    rs_text = m.group(1).decode("utf-8", errors="ignore")
    if "hyper_tower" in rs_text or "jni" in rs_text or "ffi" in rs_text or "server" in rs_text:
        rs_file = os.path.join(out_dir, f"recovered_src_{idx}.rs")
        with open(rs_file, "w") as rf:
            rf.write(rs_text)
        print(f"\n[★] Recovered Rust Source #{idx} -> {rs_file} ({len(rs_text)} chars)")
        print("    " + "\n    ".join(rs_text.splitlines()[:4]))

print("\n============================================================")
print(f" [✔] Carving complete. All files saved to {out_dir}")
print("============================================================")
