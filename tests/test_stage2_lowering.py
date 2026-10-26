import unittest
from pathlib import Path
from src.frontend.lexer import Lexer
from src.frontend.parser import Parser
from src.semantic.analyzer import SemanticAnalyzer
from src.lowering.lowerer import Lowerer
from src.lowering.ir import (
    IRModule, IRFunction, BasicBlock, BinOp, BranchIf, Jump, Return
)

class TestStage2Lowering(unittest.TestCase):
    def setUp(self):
        self.pb010_path = Path("proofboot_pb010.r2")
        self.assertTrue(self.pb010_path.exists())
        src = self.pb010_path.read_text(encoding="utf-8")
        self.mod = Parser(Lexer(src).tokenize()).parse_module()
        # Verify semantic gate passes before lowering
        analyzer = SemanticAnalyzer()
        analyzer.analyze_module(self.mod)

    def test_lower_pb010_module(self):
        lowerer = Lowerer()
        ir_mod = lowerer.lower_module(self.mod)
        self.assertIsInstance(ir_mod, IRModule)
        self.assertEqual(len(ir_mod.functions), 5)

        fn_names = [f.name for f in ir_mod.functions]
        self.assertIn("crc32", fn_names)
        self.assertIn("constant_time_eq", fn_names)
        self.assertIn("parse_header", fn_names)
        self.assertIn("arbitrate_active_header", fn_names)
        self.assertIn("commit_transition", fn_names)

    def test_lower_branching_structure(self):
        src = """
        fn test_branch(x: u32) -> u32 {
            if x > 10 {
                return 1;
            } else {
                return 0;
            }
        }
        """
        mod = Parser(Lexer(src).tokenize()).parse_module()
        lowerer = Lowerer()
        ir_mod = lowerer.lower_module(mod)
        self.assertEqual(len(ir_mod.functions), 1)
        fn = ir_mod.functions[0]
        # Should have entry, then, else, merge blocks
        self.assertGreaterEqual(len(fn.blocks), 3)
        # Entry block should end with a BranchIf
        has_branch = any(isinstance(inst, BranchIf) for b in fn.blocks for inst in b.instructions)
        self.assertTrue(has_branch)

if __name__ == "__main__":
    unittest.main()
