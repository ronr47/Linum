import unittest
from linum.src.semantic.types import Type, OwnershipMode, ParameterContract, FunctionContract, SymbolContext, PRIMITIVE_INTEGER, PRIMITIVE_BOOLEAN
from linum.src.semantic.analyzer import SemFunctionDecl
from linum.src.ast.nodes import IdentifierExpr, LetStmt, AssignStmt, MoveStmt, ReturnStmt, BlockStmt, IfStmt, FunctionDecl
from linum.src.lowering.cfg import CfgBuilder, CfgVerifier
from linum.src.lowering.ssa import SsaConverter, SsaVerifier
from linum.src.lowering.llvm import LlvmEmitter, SystemBackendLinker

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
