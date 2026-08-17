from pathlib import Path

import pytest

from linum.src.compiler import compile_source


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
    with pytest.raises(TypeError):
        compile_source(
            load("linear_move_fail.linum"),
            "linear_fail",
        )
