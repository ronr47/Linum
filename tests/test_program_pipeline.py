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

def test_unmanaged_ptr_integration_pipeline():
    """Validates full end-to-end compiler handling of raw unsafe pointer manipulations."""
    from linum.src.compiler import LinumCompiler
    from linum.src.lowering.cfg import CfgBuilder, LiveVariableAnalyzer
    from linum.src.lowering.ssa import SsaConverter, SsaVerifier
    from linum.src.lowering.llvm import LlvmEmitter, SystemBackendLinker
    from linum.src.semantic.types import SymbolContext, FunctionContract, PRIMITIVE_INTEGER, OwnershipMode

    # 1. Structural integration source mimicking raw unsafe type mutations
    source_program = """
    {
        let ptr_var : ptr = %uninit_stub;
        let q : COPY = %val_42;
        return q;
    }
    """
    
    # 2. Frame out active compiler context boundaries
    compiler = LinumCompiler()
    contract = FunctionContract("unsafe_ptr_integration", (), PRIMITIVE_INTEGER, OwnershipMode.COPY)
    
    # 3. Step execution through the toolchain pipeline
    from linum.src.frontend.lexer import Lexer
    from linum.src.frontend.parser import Parser
    from linum.src.ast.nodes import FunctionDecl
    
    tokens = Lexer(source_program).tokenize()
    body = Parser(tokens).parse_block()
    ast_func = FunctionDecl(contract, body)
    
    ctx = SymbolContext()
    ctx.bind("%uninit_stub", PRIMITIVE_INTEGER, OwnershipMode.COPY)
    ctx.bind("%val_42", PRIMITIVE_INTEGER, OwnershipMode.COPY)
    
    sem_func = ast_func.check_contract(ctx)
    cfg = CfgBuilder().lower_function(sem_func)
    
    # 4. Assert NLL liveness invariants do not throw false positives on raw pointer types
    nll = LiveVariableAnalyzer(cfg)
    nll.analyze_lifetimes()
    nll.validate_use_after_live_range()
    
    # 5. Convert to SSA and generate raw LLVM assembly
    var_types = {"ptr_var": "ptr", "q": "INTEGER"}
    ssa = SsaConverter(cfg, var_types).convert()
    SsaVerifier.verify(ssa, var_types)
    
    llvm = LlvmEmitter(contract).emit(ssa, var_types)
    
    # 6. Pass assembly directly through the opt system verifier
    linker = SystemBackendLinker()
    assert linker.verify_llvm_ir(llvm) is True, "IMPOSSIBLE: Generated unmanaged pointer IR failed LLVM validation."
    print("🟢 Unmanaged Pointer end-to-end integration integration pipeline passed flawlessly.")
