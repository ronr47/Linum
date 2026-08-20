#!/usr/bin/env bash
set -euo pipefail

echo "=== Wiring SystemBackendLinker to LLVM Opt Pipeline ==="

python - <<'PY'
from pathlib import Path

llvm_path = Path("src/linum/lowering/llvm.py")
llvm_code = llvm_path.read_text(encoding="utf-8")

old_linker = """    @staticmethod
    def compile_to_assembly(llvm_ir: str) -> str:
        proc = subprocess.run(
            ["llc", "-O0", "-o", "-"],
            input=llvm_ir,
            text=True,
            capture_output=True
        )"""

# Update to -O2 with SROA / mem2reg optimization
new_linker = """    @staticmethod
    def compile_to_assembly(llvm_ir: str, opt_level: str = "-O2") -> str:
        # Run through LLVM optimizer pipe before code generation
        opt_proc = subprocess.run(
            ["opt", opt_level, "-S"],
            input=llvm_ir,
            text=True,
            capture_output=True
        )
        optimized_ir = opt_proc.stdout if opt_proc.returncode == 0 else llvm_ir

        proc = subprocess.run(
            ["llc", opt_level, "-o", "-"],
            input=optimized_ir,
            text=True,
            capture_output=True
        )"""

if "def compile_to_assembly" in llvm_code:
    llvm_code = llvm_code.replace(
        '["llc", "-O0", "-o", "-"]',
        '["opt", "-O2", "-S"]'
    )
    llvm_path.write_text(llvm_code, encoding="utf-8")
    print("LLVM Linker wired to Optimization pipeline.")
PY

./linum_truth_gate.sh
