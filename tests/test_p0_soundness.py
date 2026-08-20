import unittest
from linum.semantic.types import (
    SymbolContext,
    FunctionContract,
    ParameterContract,
    PRIMITIVE_INTEGER,
    PRIMITIVE_BOOLEAN,
    OwnershipMode,
    Type,
)
from linum.frontend.lexer import Lexer
from linum.frontend.parser import Parser
from linum.ast.nodes import (
    BlockStmt,
    LetStmt,
    IfStmt,
    IdentifierExpr,
    FunctionDecl,
    BorrowBlockStmt,
    ExprStmt,
    CallExpr,
    ReturnStmt,
)
from linum.lowering.cfg import (
    CfgFunction,
    BasicBlock,
    CfgBuilder,
    IrCondBranch,
    IrBranch,
    IrStore,
    IrLoad,
    IrReturn,
)
from linum.lowering.ssa import SsaConverter, SsaVerifier
from linum.lowering.llvm import LlvmEmitter, SystemBackendLinker


class TestLinumP0Soundness(unittest.TestCase):
    def setUp(self):
        self.TYPE_LINEAR = Type("LINEAR_RES", OwnershipMode.LINEAR)
        self.TYPE_AFFINE = Type("AFFINE_RES", OwnershipMode.AFFINE)

    def _compile_source(self, source: str, ctx: SymbolContext, contract: FunctionContract):
        tokens = Lexer(source).tokenize()
        ast_block = Parser(tokens).parse_block()
        func_decl = FunctionDecl(contract, ast_block)
        return func_decl.check_contract(ctx)

    def test_use_after_move_rejection(self):
        source = """
        {
            let a : AFFINE = %res_stub;
            let b : AFFINE = a;
            let c : AFFINE = a;
            return %val_0;
        }
        """
        ctx = SymbolContext()
        ctx.bind("%res_stub", self.TYPE_AFFINE, OwnershipMode.AFFINE)
        ctx.bind("%val_0", PRIMITIVE_INTEGER, OwnershipMode.COPY)
        contract = FunctionContract("uam_test", (), PRIMITIVE_INTEGER, OwnershipMode.COPY)

        with self.assertRaises(TypeError) as cm:
            self._compile_source(source, ctx, contract)
        self.assertIn("MOVED", str(cm.exception).upper())

    def test_linear_overwrite_leak_rejection(self):
        source = """
        {
            let a : LINEAR = %res_stub_1;
            a = %res_stub_2;
            let sink : LINEAR = a;
            return %val_0;
        }
        """
        ctx = SymbolContext()
        ctx.bind("%res_stub_1", self.TYPE_LINEAR, OwnershipMode.LINEAR)
        ctx.bind("%res_stub_2", self.TYPE_LINEAR, OwnershipMode.LINEAR)
        ctx.bind("%val_0", PRIMITIVE_INTEGER, OwnershipMode.COPY)
        contract = FunctionContract("overwrite_test", (), PRIMITIVE_INTEGER, OwnershipMode.COPY)

        with self.assertRaises(TypeError) as cm:
            self._compile_source(source, ctx, contract)
        self.assertIn("RESOURCE LEAK HAZARD", str(cm.exception).upper())

    def test_active_borrow_move_invalidation(self):
        borrow_body = BlockStmt([LetStmt("y", self.TYPE_AFFINE, IdentifierExpr("x"))])
        borrow_stmt = BorrowBlockStmt(source="x", borrow_alias="b", body=borrow_body)
        main_body = BlockStmt([
            LetStmt("x", self.TYPE_AFFINE, IdentifierExpr("%res_stub")),
            borrow_stmt,
        ])
        ctx = SymbolContext()
        ctx.bind("%res_stub", self.TYPE_AFFINE, OwnershipMode.AFFINE)
        ctx.bind("%val_0", PRIMITIVE_INTEGER, OwnershipMode.COPY)
        contract = FunctionContract("borrow_test", (), PRIMITIVE_INTEGER, OwnershipMode.COPY)

        with self.assertRaises(TypeError) as cm:
            FunctionDecl(contract, main_body).check_contract(ctx)
        self.assertIn("BORROW INVALIDATION HAZARD", str(cm.exception).upper())

    def test_nested_borrow_lifetime_restoration(self):
        inner_body = BlockStmt([
            LetStmt("obs", PRIMITIVE_INTEGER, IdentifierExpr("%val_0"))
        ])
        inner_borrow = BorrowBlockStmt(source="outer_b", borrow_alias="inner_b", body=inner_body)
        outer_body = BlockStmt([inner_borrow])
        outer_borrow = BorrowBlockStmt(source="x", borrow_alias="outer_b", body=outer_body)
        main_body = BlockStmt([
            LetStmt("x", self.TYPE_LINEAR, IdentifierExpr("%res_stub")),
            outer_borrow,
            ReturnStmt(IdentifierExpr("x")),
        ])

        ctx = SymbolContext()
        ctx.bind("%res_stub", self.TYPE_LINEAR, OwnershipMode.LINEAR)
        ctx.bind("%val_0", PRIMITIVE_INTEGER, OwnershipMode.COPY)
        contract = FunctionContract("nested_borrow_clean", (), self.TYPE_LINEAR, OwnershipMode.LINEAR)

        sem_func = FunctionDecl(contract, main_body).check_contract(ctx)
        self.assertIsNotNone(sem_func)

    def test_multi_argument_linear_transfer(self):
        callee = FunctionContract(
            "merge_linear",
            (
                ParameterContract("a", self.TYPE_LINEAR, OwnershipMode.LINEAR),
                ParameterContract("b", self.TYPE_LINEAR, OwnershipMode.LINEAR),
            ),
            PRIMITIVE_INTEGER,
            OwnershipMode.COPY,
        )
        caller_body = BlockStmt([
            LetStmt("r1", self.TYPE_LINEAR, IdentifierExpr("%res_stub_1")),
            LetStmt("r2", self.TYPE_LINEAR, IdentifierExpr("%res_stub_2")),
            LetStmt("res", PRIMITIVE_INTEGER, CallExpr("merge_linear", (IdentifierExpr("r1"), IdentifierExpr("r2")))),
            ReturnStmt(IdentifierExpr("res")),
        ])
        ctx = SymbolContext()
        ctx.bind("%res_stub_1", self.TYPE_LINEAR, OwnershipMode.LINEAR)
        ctx.bind("%res_stub_2", self.TYPE_LINEAR, OwnershipMode.LINEAR)
        ctx.register_function("merge_linear", callee)
        contract = FunctionContract("caller_test", (), PRIMITIVE_INTEGER, OwnershipMode.COPY)

        sem_func = FunctionDecl(contract, caller_body).check_contract(ctx)
        self.assertIsNotNone(sem_func)

    def test_duplicate_linear_argument_rejection(self):
        callee = FunctionContract(
            "merge_linear",
            (
                ParameterContract("a", self.TYPE_LINEAR, OwnershipMode.LINEAR),
                ParameterContract("b", self.TYPE_LINEAR, OwnershipMode.LINEAR),
            ),
            PRIMITIVE_INTEGER,
            OwnershipMode.COPY,
        )
        caller_body = BlockStmt([
            LetStmt("r1", self.TYPE_LINEAR, IdentifierExpr("%res_stub_1")),
            LetStmt("res", PRIMITIVE_INTEGER, CallExpr("merge_linear", (IdentifierExpr("r1"), IdentifierExpr("r1")))),
            ReturnStmt(IdentifierExpr("res")),
        ])
        ctx = SymbolContext()
        ctx.bind("%res_stub_1", self.TYPE_LINEAR, OwnershipMode.LINEAR)
        ctx.register_function("merge_linear", callee)
        contract = FunctionContract("duplicate_arg_test", (), PRIMITIVE_INTEGER, OwnershipMode.COPY)

        with self.assertRaises(TypeError) as cm:
            FunctionDecl(contract, caller_body).check_contract(ctx)
        self.assertIn("MOVED", str(cm.exception).upper())

    def test_pure_branch_lattice_divergence(self):
        then_block = BlockStmt([
            ExprStmt(CallExpr("consume_res", (IdentifierExpr("x"),)))
        ])
        else_block = BlockStmt([
            LetStmt("dummy", PRIMITIVE_INTEGER, IdentifierExpr("%val_0"))
        ])
        if_stmt = IfStmt(
            condition=IdentifierExpr("%cond_reg"),
            then_block=then_block,
            else_block=else_block,
        )
        main_body = BlockStmt([
            LetStmt("x", self.TYPE_LINEAR, IdentifierExpr("%res_stub")),
            if_stmt,
        ])

        ctx = SymbolContext()
        ctx.bind("%res_stub", self.TYPE_LINEAR, OwnershipMode.LINEAR)
        ctx.bind("%cond_reg", PRIMITIVE_BOOLEAN, OwnershipMode.COPY)
        ctx.bind("%val_0", PRIMITIVE_INTEGER, OwnershipMode.COPY)
        consume_contract = FunctionContract(
            "consume_res",
            (ParameterContract("val", self.TYPE_LINEAR, OwnershipMode.LINEAR),),
            PRIMITIVE_INTEGER,
            OwnershipMode.COPY,
        )
        ctx.register_function("consume_res", consume_contract)
        contract = FunctionContract("lattice_test", (), PRIMITIVE_INTEGER, OwnershipMode.COPY)

        with self.assertRaises(TypeError) as cm:
            FunctionDecl(contract, main_body).check_contract(ctx)
        err = str(cm.exception).upper()
        self.assertTrue(
            "CONVERGENCE INVARIANT" in err
            or "INVALID CALL TRANSFER" in err
            or "MOVED" in err
        )

    def test_early_return_linear_leak_rejection(self):
        source = """
        {
            let x : LINEAR = %res_stub;
            if %cond_reg {
                return %val_0;
            } else {
                let dummy : COPY = %val_0;
            }
            let sink : LINEAR = x;
            return %val_0;
        }
        """
        ctx = SymbolContext()
        ctx.bind("%res_stub", self.TYPE_LINEAR, OwnershipMode.LINEAR)
        ctx.bind("%cond_reg", PRIMITIVE_BOOLEAN, OwnershipMode.COPY)
        ctx.bind("%val_0", PRIMITIVE_INTEGER, OwnershipMode.COPY)
        contract = FunctionContract("early_leak_test", (), PRIMITIVE_INTEGER, OwnershipMode.COPY)

        with self.assertRaises(TypeError) as cm:
            self._compile_source(source, ctx, contract)
        self.assertIn("CONTRACT VIOLATION", str(cm.exception).upper())

    def test_full_pipeline_lowering_and_ssa_verification(self):
        source = """
        {
            let q : COPY = %uninit_stub;
            if %cond_reg {
                q = %val_42;
            } else {
                q = %val_99;
            }
            return q;
        }
        """
        ctx = SymbolContext()
        ctx.bind("%uninit_stub", PRIMITIVE_INTEGER, OwnershipMode.COPY)
        ctx.bind("%cond_reg", PRIMITIVE_BOOLEAN, OwnershipMode.COPY)
        ctx.bind("%val_42", PRIMITIVE_INTEGER, OwnershipMode.COPY)
        ctx.bind("%val_99", PRIMITIVE_INTEGER, OwnershipMode.COPY)
        contract = FunctionContract("pipeline_test", (), PRIMITIVE_INTEGER, OwnershipMode.COPY)

        sem_func = self._compile_source(source, ctx, contract)
        cfg = CfgBuilder().lower_function(sem_func)
        ssa = SsaConverter(cfg, {"q": "INTEGER"}).convert()
        SsaVerifier.verify(ssa, {"q": "INTEGER"})
        self.assertTrue(any(len(b.phis) == 1 for b in ssa.blocks.values()))

    def test_nested_diamond_llvm_emission_and_verification(self):
        source = """
        {
            let val : COPY = %val_0;
            if %cond_reg1 {
                if %cond_reg2 {
                    val = %val_42;
                } else {
                    val = %val_99;
                }
            } else {
                val = %val_100;
            }
            return val;
        }
        """
        ctx = SymbolContext()
        ctx.bind("%cond_reg1", PRIMITIVE_BOOLEAN, OwnershipMode.COPY)
        ctx.bind("%cond_reg2", PRIMITIVE_BOOLEAN, OwnershipMode.COPY)
        ctx.bind("%val_0", PRIMITIVE_INTEGER, OwnershipMode.COPY)
        ctx.bind("%val_42", PRIMITIVE_INTEGER, OwnershipMode.COPY)
        ctx.bind("%val_99", PRIMITIVE_INTEGER, OwnershipMode.COPY)
        ctx.bind("%val_100", PRIMITIVE_INTEGER, OwnershipMode.COPY)
        contract = FunctionContract("nested_diamond_llvm", (), PRIMITIVE_INTEGER, OwnershipMode.COPY)

        sem_func = self._compile_source(source, ctx, contract)
        cfg = CfgBuilder().lower_function(sem_func)
        var_types = {"val": "INTEGER"}
        ssa = SsaConverter(cfg, var_types).convert()
        SsaVerifier.verify(ssa, var_types)

        emitter = LlvmEmitter(contract)
        llvm_ir = emitter.emit(ssa, var_types)
        linker = SystemBackendLinker()
        self.assertTrue(linker.verify_llvm_ir(llvm_ir))

    def test_cyclic_cfg_loop_ssa_and_llvm_verification(self):
        entry_bb = BasicBlock("entry")
        entry_bb.instructions = [IrStore("%r_init", "x"), IrBranch("header")]
        entry_bb.terminator = IrBranch("header")

        header_bb = BasicBlock("header")
        header_bb.instructions = [IrCondBranch("%cond_reg", "body", "exit")]
        header_bb.terminator = IrCondBranch("%cond_reg", "body", "exit")

        body_bb = BasicBlock("body")
        body_bb.instructions = [IrStore("%r_next", "x"), IrBranch("header")]
        body_bb.terminator = IrBranch("header")

        exit_bb = BasicBlock("exit")
        exit_bb.instructions = [IrLoad("%r_final", "x"), IrReturn("%r_final")]
        exit_bb.terminator = IrReturn("%r_final")

        blocks = {"entry": entry_bb, "header": header_bb, "body": body_bb, "exit": exit_bb}
        successors = {"entry": {"header"}, "header": {"body", "exit"}, "body": {"header"}, "exit": set()}
        predecessors = {"entry": set(), "header": {"entry", "body"}, "body": {"header"}, "exit": {"header"}}

        cfg_func = CfgFunction("synthetic_loop", "entry", blocks, successors, predecessors)
        var_types = {"x": "INTEGER"}
        ssa = SsaConverter(cfg_func, var_types).convert()
        SsaVerifier.verify(ssa, var_types)

        contract = FunctionContract("synthetic_loop", (), PRIMITIVE_INTEGER, OwnershipMode.COPY)
        emitter = LlvmEmitter(contract)
        llvm_ir = emitter.emit(ssa, var_types)
        linker = SystemBackendLinker()
        self.assertTrue(linker.verify_llvm_ir(llvm_ir))


if __name__ == "__main__":
    unittest.main()
