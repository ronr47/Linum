#!/usr/bin/env bash
set -e

PY_BIN="$( [ -f "./.venv/bin/python" ] && echo "./.venv/bin/python" || echo "$(which python3)" )"
export PYTHONPATH=".:$PYTHONPATH"

echo "=== Running Frontend Grammar Tests ==="
$PY_BIN -m pytest tests/test_frontend.py -vv

echo "=== Running P0 Linearity & Lifetime Soundness Tests ==="
$PY_BIN -m pytest tests/test_p0_soundness.py -vv

echo "=== Running Neuro-Symbolic AST Verifier Tests ==="
$PY_BIN -m pytest tests/test_neuro_symbolic_verifier.py -vv
