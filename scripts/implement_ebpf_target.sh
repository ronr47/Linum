#!/usr/bin/env bash
set -euo pipefail

echo "=== Implementing Linum eBPF/XDP Target Lowering ==="

python - <<'PY'
from pathlib import Path

cli_path = Path("src/linum/cli.py")
cli_code = cli_path.read_text(encoding="utf-8")

# Add 'bpf' to emit choices
if "'bpf'" not in cli_code:
    cli_code = cli_code.replace(
        'choices=["llvm", "asm", "obj"]',
        'choices=["llvm", "asm", "obj", "bpf"]'
    )
    
bpf_handler = """        elif opts.emit == "bpf":
            out_file = opts.output if opts.output else str(input_path.with_suffix(".o"))
            # Compile via Clang BPF target directly from emitted LLVM IR
            import subprocess
            cmd = ["clang", "-O2", "-target", "bpf", "-c", "-", "-o", out_file]
            proc = subprocess.run(cmd, input=llvm_ir.encode("utf-8"), capture_output=True)
            if proc.returncode != 0:
                raise RuntimeError(f"BPF compilation failed: {proc.stderr.decode('utf-8')}")
            return 0"""

if 'elif opts.emit == "bpf":' not in cli_code:
    cli_code = cli_code.replace(
        '        elif opts.emit == "obj":',
        f'{bpf_handler}\n\n        elif opts.emit == "obj":'
    )
cli_path.write_text(cli_code, encoding="utf-8")
print("CLI updated with BPF emission target.")
PY

./linum_truth_gate.sh
