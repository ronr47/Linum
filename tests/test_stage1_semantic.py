import unittest
from pathlib import Path
from src.frontend.lexer import Lexer
from src.frontend.parser import Parser
from src.ast.nodes import TypeRef, FunctionDecl
from src.semantic.analyzer import SemanticAnalyzer, SemanticError

class TestStage1Semantic(unittest.TestCase):
    def setUp(self):
        self.pb010_path = Path("proofboot_pb010.r2")
        self.assertTrue(self.pb010_path.exists(), "proofboot_pb010.r2 must exist")
        src = self.pb010_path.read_text(encoding="utf-8")
        self.mod = Parser(Lexer(src).tokenize()).parse_module()

    def test_semantic_analysis_pb010_module(self):
        analyzer = SemanticAnalyzer()
        analyzer.analyze_module(self.mod)
        self.assertEqual(len(analyzer.structs), 3)
        self.assertEqual(len(analyzer.functions), 5)
        self.assertIn("Header", analyzer.structs)
        self.assertIn("SlotEnvelope", analyzer.structs)
        self.assertIn("StorageDevice", analyzer.structs)

    def test_reject_duplicate_struct(self):
        bad_src = """
        struct Point { x: u32, }
        struct Point { y: u32, }
        """
        mod = Parser(Lexer(bad_src).tokenize()).parse_module()
        analyzer = SemanticAnalyzer()
        with self.assertRaises(SemanticError):
            analyzer.analyze_module(mod)

    def test_reject_unknown_type(self):
        bad_src = """
        fn invalid_type_fn(buf: NonExistentType) -> void {}
        """
        mod = Parser(Lexer(bad_src).tokenize()).parse_module()
        analyzer = SemanticAnalyzer()
        with self.assertRaises(SemanticError):
            analyzer.analyze_module(mod)

    def test_reject_invalid_domain_on_ast(self):
        # Directly construct AST node with invalid domain to test domain isolation gate
        bad_fn = FunctionDecl(
            name="test_fn",
            params=[("ptr", TypeRef(name="u8", domain="untrusted_dom"))],
            return_type=TypeRef(name="void"),
            contracts=[],
            body=[]
        )
        analyzer = SemanticAnalyzer()
        with self.assertRaises(SemanticError):
            analyzer._validate_function(bad_fn)

if __name__ == "__main__":
    unittest.main()
