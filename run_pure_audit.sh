#!/usr/bin/env bash
set -e

# Detect virtualenv python
if [ -n "$VIRTUAL_ENV" ] && [ -f "$VIRTUAL_ENV/bin/python" ]; then
    PY_BIN="$VIRTUAL_ENV/bin/python"
elif [ -f "./.venv/bin/python" ]; then
    PY_BIN="./.venv/bin/python"
else
    PY_BIN="$(which python3)"
fi

export PYTHONPATH=".:$PYTHONPATH"

echo "=========================================================="
echo "          LINUM COMPILER: READ-ONLY SUBSYSTEM AUDIT        "
echo "=========================================================="
echo "Python Binary : $PY_BIN"
echo "Timestamp     : $(date)"
echo ""

$PY_BIN - <<'PY_EOF'
import inspect
from pathlib import Path

def print_section(title):
    print(f"\n{'='*25} {title} {'='*25}")

# 1. Audit SSA Data Structures
print_section("1. SSA DEFINITIONS (src/lowering/ssa.py)")
try:
    import linum.src.lowering.ssa as ssa_mod
    for name in dir(ssa_mod):
        obj = getattr(ssa_mod, name)
        if inspect.isclass(obj) and obj.__module__ == ssa_mod.__name__:
            annotations = getattr(obj, "__annotations__", {})
            doc = inspect.getdoc(obj) or "No docstring"
            print(f"Class: {name}")
            if annotations:
                print(f"  Fields: {annotations}")
            else:
                # inspect __init__ params if not a dataclass
                init_sig = inspect.signature(obj.__init__)
                params = [p for p in init_sig.parameters if p != 'self']
                print(f"  Constructor params: {params}")
except Exception as e:
    print(f"Failed to inspect SSA module: {e}")

# 2. Audit CFG Data Structures
print_section("2. CFG DEFINITIONS (src/lowering/cfg.py)")
try:
    import linum.src.lowering.cfg as cfg_mod
    for name in dir(cfg_mod):
        obj = getattr(cfg_mod, name)
        if inspect.isclass(obj) and obj.__module__ == cfg_mod.__name__:
            if name.startswith("Ir") or "Block" in name or "Cfg" in name:
                annotations = getattr(obj, "__annotations__", {})
                init_sig = inspect.signature(obj.__init__)
                params = [p for p in init_sig.parameters if p != 'self']
                print(f"Class: {name} -> Params: {params} | Annotations: {annotations}")
except Exception as e:
    print(f"Failed to inspect CFG module: {e}")

# 3. Audit Current LLVM Emitter Implementation
print_section("3. CURRENT LLVM EMITTER (src/lowering/llvm.py)")
llvm_file = Path("src/lowering/llvm.py")
if llvm_file.exists():
    lines = llvm_file.read_text().splitlines()
    print(f"Total lines: {len(lines)}")
    # Find methods in LlvmEmitter
    emitter_methods = [l.strip() for l in lines if l.strip().startswith("def ")]
    print(f"Methods found: {emitter_methods}")
else:
    print("llvm.py does not exist")

# 4. Audit Failing Test Inputs
print_section("4. FAILING TEST DETAILS")
test_branch = Path("tests/test_program_pipeline.py")
if test_branch.exists():
    src = test_branch.read_text()
    for fn_name in ["test_branch_file_pipeline", "test_sound_linear_pipeline_lowering"]:
        if fn_name in src:
            print(f"Found test: {fn_name}")

print_section("AUDIT COMPLETE")
PY_EOF

