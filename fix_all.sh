#!/usr/bin/env bash
set -euo pipefail

echo "== 1. Restore cli.py from git =="
git restore -- src/linum/cli.py

echo "== 2. Patch CFG tuple handling safely =="

python3 - <<'PY'
from pathlib import Path

path = Path("src/linum/lowering/cfg.py")
text = path.read_text()

# Normalize the parameter object first.  Some semantic representations
# arrive as (node, metadata/type) tuples.
old = """        for param in sem_decl.contract.parameters:
            ptype = param.type[0] if isinstance(param.type, tuple) else param.type
            self.emit_instr(IrAlloca(param.name, ptype.name))
            arg_reg = self.new_reg()
            self.emit_instr(IrParam(arg_reg, param.name, ptype.name))
            self.emit_instr(IrStore(arg_reg, param.name))"""

new = """        for param in sem_decl.contract.parameters:
            if isinstance(param, tuple):
                param = param[0]

            ptype = param.type
            if isinstance(ptype, tuple):
                ptype = ptype[0]

            self.emit_instr(IrAlloca(param.name, ptype.name))
            arg_reg = self.new_reg()
            self.emit_instr(IrParam(arg_reg, param.name, ptype.name))
            self.emit_instr(IrStore(arg_reg, param.name))"""

if old in text:
    text = text.replace(old, new)
else:
    print("WARNING: expected CFG parameter block not found")

path.write_text(text)
PY

echo "== 3. Show remaining suspicious tuple/type accesses =="
grep -nE '\.type|contract\.parameters|isinstance\(.*tuple' \
    src/linum/lowering/cfg.py || true

echo "== 4. Syntax-check modified Python files =="
python3 -m py_compile \
    src/linum/cli.py \
    src/linum/lowering/cfg.py \
    src/linum/lowering/llvm.py

echo "== 5. Run compiler =="
linum src/unified_orchestrator.linum \
    --emit obj \
    -o build/unified_ultimate.o
