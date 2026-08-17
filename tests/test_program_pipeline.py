from pathlib import Path

import pytest

from linum.src.compiler import compile_source
from linum.src.diagnostics import DiagnosticError


ROOT = Path(__file__).parent / "programs"


def load(name):
    return (ROOT / name).read_text()


def test_branch_file_pipeline():
    llvm = compile_source(
        load("branch.linum"),
        "branch_test",
    )

    assert "phi i64" in llvm


def test_arithmetic_file_pipeline():
    llvm = compile_source(
        load("arithmetic.linum"),
        "arith_test",
    )

    assert "define" in llvm


def test_linear_failure_file_pipeline():
    with pytest.raises(DiagnosticError) as exc:
        compile_source(
            load("linear_move_fail.linum"),
            "linear_fail",
        )

    assert "Linear variable 'x' is leaked" in str(exc.value)
    assert "semantic" in str(exc.value)
