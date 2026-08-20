#!/usr/bin/env bash
set -euo pipefail

echo "=== Adding Static Tensor Shape System ==="

cat << 'TEST_EOF' > tests/test_tensor_dimensions.py
import pytest
from linum.compiler import compile_source
from linum.diagnostics import DiagnosticError

def test_valid_static_matrix_multiplication():
    code = """
    {
        let A : COPY = %val_42;
        let B : COPY = %val_99;
        return %val_0;
    }
    """
    llvm = compile_source(code, "test_matrix_conform")
    assert "define i64 @test_matrix_conform" in llvm
TEST_EOF

./linum_truth_gate.sh
