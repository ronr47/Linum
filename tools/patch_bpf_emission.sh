#!/usr/bin/env bash
set -euo pipefail

cd /home/ron/linum

echo "[1/3] Patching BPF Clang invocation in src/linum/cli.py..."
python3 - << 'PY_EOF'
with open("src/linum/cli.py", "r", encoding="utf-8") as f:
    content = f.read()

old_cmd = 'cmd = ["clang", "-O2", "-target", "bpf", "-c", "-", "-o", out_file]'
new_cmd = 'cmd = ["clang", "-O2", "-target", "bpf", "-x", "ir", "-c", "-", "-o", out_file]'

if old_cmd in content:
    content = content.replace(old_cmd, new_cmd)
    with open("src/linum/cli.py", "w", encoding="utf-8") as f:
        f.write(content)
    print("[+] Successfully added '-x ir' flag to BPF compilation command.")
else:
    print("[!] Target string not found or already patched.")
PY_EOF

echo "[2/3] Reinstalling package in editable mode..."
python -m pip install -e . --no-deps --quiet

echo "[3/3] Testing BPF object emission..."
linum test_main.linum --emit bpf -o /tmp/main_xdp.o

echo "------------------------------------------------------------"
echo "[*] Inspecting emitted BPF object:"
file /tmp/main_xdp.o
readelf -h /tmp/main_xdp.o | grep -E "Class|Machine|Type" || llvm-readelf -h /tmp/main_xdp.o | grep -E "Class|Machine|Type"
echo "============================================================"
echo "[✔] eBPF/XDP target emission verified."
