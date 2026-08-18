#!/usr/bin/env bash
set -e

PY_BIN="$( [ -f "./.venv/bin/python" ] && echo "./.venv/bin/python" || echo "$(which python3)" )"
export PYTHONPATH=".:$PYTHONPATH"

echo "=== Running Full Pytest Suite across All Modules ==="
$PY_BIN -m pytest -vv

echo "=== Running Toolchain Build Audit Report ==="
./run_build_audit.sh
