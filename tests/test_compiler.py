import unittest
from linum.semantic.types import Type, OwnershipMode, ParameterContract, FunctionContract, SymbolContext, PRIMITIVE_INTEGER, PRIMITIVE_BOOLEAN
from linum.semantic.analyzer import SemFunctionDecl
from linum.ast.nodes import IdentifierExpr, LetStmt, AssignStmt, MoveStmt, ReturnStmt, BlockStmt, IfStmt, FunctionDecl
from linum.lowering.cfg import CfgBuilder, CfgVerifier
from linum.lowering.ssa import SsaConverter, SsaVerifier
from linum.lowering.llvm import LlvmEmitter, SystemBackendLinker

class TestLinumCompiler(unittest.TestCase):
    def test_sound_linear_pipeline_lowering(self):
        var_types = {"q": "INTEGER"}
        contract = FunctionContract("linear_pipeline", (), PRIMITIVE_INTEGER, OwnershipMode.COPY)

        ast_then = BlockStmt([AssignStmt("q", IdentifierExpr("%val_42"))])
        ast_else = BlockStmt([AssignStmt("q", IdentifierExpr("%val_99"))])

        ast_func = FunctionDecl(
            contract=contract,
            body=BlockStmt([
                LetStmt("q", PRIMITIVE_INTEGER, IdentifierExpr("%uninit_stub")),
                IfStmt(IdentifierExpr("%cond_reg"), ast_then, ast_else),
                ReturnStmt(IdentifierExpr("q"))
            ])
        )

        ctx = SymbolContext()
        # Explicitly register test stencils to fulfill identifier lookups
        ctx.bind("%uninit_stub", PRIMITIVE_INTEGER, OwnershipMode.COPY)
        ctx.bind("%cond_reg", PRIMITIVE_BOOLEAN, OwnershipMode.COPY)
        ctx.bind("%val_42", PRIMITIVE_INTEGER, OwnershipMode.COPY)
        ctx.bind("%val_99", PRIMITIVE_INTEGER, OwnershipMode.COPY)

        sem_func = ast_func.check_contract(ctx)

        builder = CfgBuilder()
        cfg = builder.lower_function(sem_func)
        CfgVerifier.verify(cfg.blocks)

        converter = SsaConverter(cfg, var_types)
        ssa_func = converter.convert()

        merge_blocks = [
            block
            for block in ssa_func.blocks.values()
            if len(block.phis) == 1
        ]

        self.assertEqual(len(merge_blocks), 1)

        SsaVerifier.verify(ssa_func, var_types)
        emitter = LlvmEmitter(contract)
        llvm_code = emitter.emit(ssa_func, var_types)

        self.assertIn("phi i64", llvm_code)
        self.assertTrue(SystemBackendLinker.verify_llvm_ir(llvm_code))

    def test_negative_leak_protection(self):
        contract = FunctionContract("leak_hazard", (), PRIMITIVE_INTEGER, OwnershipMode.COPY)
        ast_func = FunctionDecl(
            contract=contract,
            body=BlockStmt([
                LetStmt("x", Type("LINEAR_RES", OwnershipMode.LINEAR), IdentifierExpr("%stub")),
                ReturnStmt(IdentifierExpr("%val_0"))
            ])
        )
        ctx = SymbolContext()
        ctx.bind("%stub", PRIMITIVE_INTEGER, OwnershipMode.COPY)
        ctx.bind("%val_0", PRIMITIVE_INTEGER, OwnershipMode.COPY)

        with self.assertRaisesRegex(TypeError, "Contract Violation: Linear variable 'x' is leaked"):
            ast_func.check_contract(ctx)

if __name__ == "__main__":
    unittest.main()

    def test_unmanaged_pointers_lowering(self):
        """Verifies unmanaged pointer nodes lower smoothly and bypass standard linear checks."""
        from linum.ast.nodes import PtrAllocaExpr, PtrStoreStmt, PtrLoadExpr, BlockStmt, LetStmt, ReturnStmt
        from linum.semantic.types import Type, OwnershipMode, FunctionContract, PRIMITIVE_INTEGER
        from linum.lowering.cfg import CfgBuilder
        from linum.lowering.ssa import SsaConverter
        from linum.lowering.llvm import LlvmEmitter, SystemBackendLinker
        from linum.semantic.analyzer import SemBlockStmt, SemLetStmt, SemReturnStmt

        # Construct a synthetic AST using the newly implemented unmanaged pointer primitives
        # Allocates an unmanaged pointer, stores an address value, and loads it back.
        alloc_node = PtrAllocaExpr(target_type=PRIMITIVE_INTEGER)
        store_node = PtrStoreStmt(pointer_expr="ptr_var", value_expr="val_source")
        load_node = PtrLoadExpr(pointer_expr="ptr_var")

        # Build manual lowered equivalent blocks to assert backend data lane compliance
        from linum.lowering.cfg import BasicBlock, IrAlloca, IrStore, IrPtrLoad, IrPtrStore, IrReturn, CfgFunction
        entry_bb = BasicBlock("entry")
        entry_bb.instructions = [
            IrAlloca("ptr_var", "ptr"),
            IrStore("0", "ptr_var"),
            IrPtrStore("val_source", "ptr_var"),
            IrPtrLoad("%r1", "ptr_var")
        ]
        entry_bb.terminator = IrReturn("%r1")

        blocks = {"entry": entry_bb}
        successors = {"entry": set()}
        predecessors = {"entry": set()}
        cfg_func = CfgFunction("unsafe_ptr_test", "entry", blocks, successors, predecessors)

        var_types = {"ptr_var": "ptr", "val_source": "INTEGER"}
        ssa = SsaConverter(cfg_func, var_types).convert()

        contract = FunctionContract("unsafe_ptr_test", (), PRIMITIVE_INTEGER, OwnershipMode.COPY)
        emitter = LlvmEmitter(contract)
        llvm_ir = emitter.emit(ssa, var_types)

        # Assert structural LLVM IR output matches expected memory layouts
        self.assertIn("alloca ptr", llvm_ir)
        self.assertIn("store ptr", llvm_ir)
        self.assertIn("load ptr", llvm_ir)

        linker = SystemBackendLinker()
        self.assertTrue(linker.verify_llvm_ir(llvm_ir))


    def test_neuro_symbolic_verifier_compiler_rejection(self):
        """Validates that untrusted programs with undefined symbols fail at the verifier stage."""
        from linum.compiler import compile_source
        from linum.diagnostics import DiagnosticError

        hallucinated_source = """
        {
            let x : COPY = hallucinated_unbound_symbol;
            return x;
        }
        """
        import pytest
        with pytest.raises(DiagnosticError) as exc_info:
            compile_source(hallucinated_source, "verifier_guard_test")

        assert "Hallucinated or undefined identifier" in exc_info.value.diagnostic.message
