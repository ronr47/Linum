import pytest
from linum.compiler import LinumCompiler
from linum.lowering.cfg import CfgBuilder
from linum.lowering.ssa import SsaConverter, SsaVerifier
from linum.lowering.llvm import LlvmEmitter, SystemBackendLinker
from linum.semantic.types import (
    SymbolContext,
    FunctionContract,
    PRIMITIVE_INTEGER,
    PRIMITIVE_BOOLEAN,
    OwnershipMode,
    Type,
)
from linum.frontend.lexer import Lexer
from linum.frontend.parser import Parser
from linum.ast.nodes import FunctionDecl

def test_nested_diamond_pointer_phi_convergence():
    """Validates that a variable assigned pointers across nested control-flow diamonds converges to 'phi ptr'."""
    source_program = """
    {
        let res : ptr = %raw_base;
        if %cond_outer {
            if %cond_inner {
                res = %raw_branch_a;
            } else {
                res = %raw_branch_b;
            }
        } else {
            res = %raw_branch_c;
        }
        return %val_0;
    }
    """
    contract = FunctionContract("nested_ptr_convergence", (), PRIMITIVE_INTEGER, OwnershipMode.COPY)
    tokens = Lexer(source_program).tokenize()
    body = Parser(tokens).parse_block()
    ast_func = FunctionDecl(contract, body)

    ctx = SymbolContext()
    ctx.bind("%raw_base", Type("ptr", OwnershipMode.COPY), OwnershipMode.COPY)
    ctx.bind("%raw_branch_a", Type("ptr", OwnershipMode.COPY), OwnershipMode.COPY)
    ctx.bind("%raw_branch_b", Type("ptr", OwnershipMode.COPY), OwnershipMode.COPY)
    ctx.bind("%raw_branch_c", Type("ptr", OwnershipMode.COPY), OwnershipMode.COPY)
    ctx.bind("%cond_outer", PRIMITIVE_BOOLEAN, OwnershipMode.COPY)
    ctx.bind("%cond_inner", PRIMITIVE_BOOLEAN, OwnershipMode.COPY)
    ctx.bind("%val_0", PRIMITIVE_INTEGER, OwnershipMode.COPY)

    sem_func = ast_func.check_contract(ctx)
    cfg = CfgBuilder().lower_function(sem_func)

    var_types = {"res": "ptr"}
    ssa = SsaConverter(cfg, var_types).convert()
    SsaVerifier.verify(ssa, var_types)

    llvm = LlvmEmitter(contract).emit(ssa, var_types)

    assert "phi ptr" in llvm, "Failed to infer pointer phi node type across nested branches."
    assert "phi i64" not in [line for line in llvm.splitlines() if "%res" in line], "Detected incorrect integer phi typing for pointer variable."
    
    linker = SystemBackendLinker()
    assert linker.verify_llvm_ir(llvm) is True, "LLVM validation failed for nested pointer phi convergence."

def test_cyclic_loop_pointer_phi_convergence():
    """Validates that back-edge assignments inside cyclic CFG loops converge to 'phi ptr'."""
    from linum.lowering.cfg import BasicBlock, CfgFunction, IrStore, IrLoad, IrBranch, IrCondBranch, IrReturn

    entry_bb = BasicBlock("entry")
    entry_bb.instructions = [IrStore(src_reg="%ptr_init", dest_var="p"), IrBranch(target_label="loop_header")]
    entry_bb.terminator = IrBranch(target_label="loop_header")

    header_bb = BasicBlock("loop_header")
    header_bb.instructions = [IrCondBranch(cond_reg="%loop_cond", then_label="loop_body", else_label="loop_exit")]
    header_bb.terminator = IrCondBranch(cond_reg="%loop_cond", then_label="loop_body", else_label="loop_exit")

    body_bb = BasicBlock("loop_body")
    body_bb.instructions = [IrStore(src_reg="%ptr_next", dest_var="p"), IrBranch(target_label="loop_header")]
    body_bb.terminator = IrBranch(target_label="loop_header")

    exit_bb = BasicBlock("loop_exit")
    exit_bb.instructions = [IrLoad(target_reg="%p_final", src_var="p"), IrReturn(val_reg="%val_0")]
    exit_bb.terminator = IrReturn(val_reg="%val_0")

    blocks = {"entry": entry_bb, "loop_header": header_bb, "loop_body": body_bb, "loop_exit": exit_bb}
    successors = {"entry": {"loop_header"}, "loop_header": {"loop_body", "loop_exit"}, "loop_body": {"loop_header"}, "loop_exit": set()}
    predecessors = {"entry": set(), "loop_header": {"entry", "loop_body"}, "loop_body": {"loop_header"}, "loop_exit": {"loop_header"}}

    cfg_func = CfgFunction("loop_ptr_phi", "entry", blocks, successors, predecessors)
    var_types = {"p": "ptr"}
    ssa = SsaConverter(cfg_func, var_types).convert()
    SsaVerifier.verify(ssa, var_types)

    contract = FunctionContract("loop_ptr_phi", (), PRIMITIVE_INTEGER, OwnershipMode.COPY)
    llvm = LlvmEmitter(contract).emit(ssa, var_types)

    assert "phi ptr" in llvm
    linker = SystemBackendLinker()
    assert linker.verify_llvm_ir(llvm) is True
