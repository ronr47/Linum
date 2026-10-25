#!/usr/bin/env python3
"""PB-011: Verification suite for Stage 0 R2 Lexer and Parser on proofboot_pb010.r2."""

import unittest
from pathlib import Path
from src.frontend.lexer import Lexer, TokenType
from src.frontend.parser import Parser

PB010_PATH = Path(__file__).resolve().parent.parent / "proofboot_pb010.r2"


class TestStage0Parser(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not PB010_PATH.exists():
            raise unittest.SkipTest(f"{PB010_PATH} not found")
        with open(PB010_PATH, "r", encoding="utf-8") as f:
            cls.source = f.read()

    def test_lexer_tokenizes_memory_domains(self):
        code = "fn test(p: mmio<u8>, q: ram<u32>) -> Status"
        tokens = Lexer(code).tokenize()
        types = [t.type for t in tokens]
        self.assertIn(TokenType.MMIO, types)
        self.assertIn(TokenType.RAM, types)
        self.assertIn(TokenType.LANGLE, types)
        self.assertIn(TokenType.RANGLE, types)

    def test_lexer_tokenizes_invariants(self):
        code = "fn step(x: u32) -> u32 pre: x > 0 post: ret >= x preserves: [RBP, RSP]"
        tokens = Lexer(code).tokenize()
        types = [t.type for t in tokens]
        self.assertIn(TokenType.PRE, types)
        self.assertIn(TokenType.POST, types)
        self.assertIn(TokenType.PRESERVES, types)

    def test_parse_pb010_module(self):
        tokens = Lexer(self.source).tokenize()
        parser = Parser(tokens)
        mod = parser.parse_module()

        self.assertEqual(mod.name, "proofboot.pb010")
        fn_names = [d.name for d in mod.declarations if hasattr(d, "name") and hasattr(d, "contracts")]

        self.assertIn("crc32", fn_names)
        self.assertIn("constant_time_eq", fn_names)
        self.assertIn("parse_header", fn_names)
        self.assertIn("arbitrate_active_header", fn_names)
        self.assertIn("commit_transition", fn_names)

        # Check explicit contracts extracted on commit_transition
        commit_fn = next(d for d in mod.declarations if getattr(d, "name", None) == "commit_transition")
        contract_kinds = [c.kind for c in commit_fn.contracts]
        self.assertIn("pre", contract_kinds)
        self.assertIn("post", contract_kinds)


if __name__ == "__main__":
    unittest.main()
