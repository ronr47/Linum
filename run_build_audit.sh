#!/usr/bin/env bash
set -e

# Detect virtual environment python or fall back to system python
if [ -n "$VIRTUAL_ENV" ] && [ -f "$VIRTUAL_ENV/bin/python" ]; then
    PY_BIN="$VIRTUAL_ENV/bin/python"
elif [ -f "./.venv/bin/python" ]; then
    PY_BIN="./.venv/bin/python"
else
    PY_BIN="$(which python3)"
fi

echo "========================================================"
echo "          LINUM COMPILER TOOLCHAIN BUILD AUDIT          "
echo "========================================================"
echo "Timestamp : $(date)"
echo "Host      : $(whoami)@$(hostname)"
echo "Path      : $(pwd)"
echo "Python    : $PY_BIN"
echo ""

echo "--- 1. Python Environment & LLVM Tooling ---"
$PY_BIN --version
which llc && llc --version | head -n 2 || echo "WARNING: llc not found in PATH"
echo ""

echo "--- 2. Pytest Execution across All Suites ---"
$PY_BIN -m pytest -vv

echo ""
echo "--- 3. Direct Subsystem Test Tally ---"
$PY_BIN - <<'PY_EOF'
import subprocess
import sys

test_files = [
    "test_hyper_pipeline.py",
    "tests/test_compiler.py",
    "tests/test_frontend.py",
    "tests/test_p0_soundness.py",
    "tests/test_program_pipeline.py"
]

print(f"{'Test File':<40} | {'Status'}")
print("-" * 52)
for tf in test_files:
    res = subprocess.run([sys.executable, "-m", "pytest", "-q", tf], capture_output=True, text=True)
    status = "PASSED" if res.returncode == 0 else "FAILED"
    print(f"{tf:<40} | {status}")
PY_EOF

echo ""
echo "========================================================"
echo "                BUILD AUDIT COMPLETE                    "
echo "========================================================"
