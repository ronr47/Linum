import unittest
from linum.frontend.lexer import Lexer
from linum.frontend.parser import Parser
from linum.semantic.types import SymbolContext, FunctionContract, PRIMITIVE_INTEGER, PRIMITIVE_BOOLEAN, OwnershipMode
from linum.ast.nodes import FunctionDecl
from linum.lowering.cfg import CfgBuilder, CfgVerifier
from linum.lowering.ssa import SsaConverter, SsaVerifier

class TestLinumFrontend(unittest.TestCase):
    def test_lexer_and_parser_integration(self):
        source_code = """
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
        lexer = Lexer(source_code)
        tokens = lexer.tokenize()
        parser = Parser(tokens)
        ast_body = parser.parse_block()
        
        contract = FunctionContract("parsed_pipeline", (), PRIMITIVE_INTEGER, OwnershipMode.COPY)
        ast_func = FunctionDecl(contract, ast_body)
        
        ctx = SymbolContext()
        ctx.bind("%uninit_stub", PRIMITIVE_INTEGER, OwnershipMode.COPY)
        ctx.bind("%cond_reg", PRIMITIVE_BOOLEAN, OwnershipMode.COPY)
        ctx.bind("%val_42", PRIMITIVE_INTEGER, OwnershipMode.COPY)
        ctx.bind("%val_99", PRIMITIVE_INTEGER, OwnershipMode.COPY)
        
        sem_func = ast_func.check_contract(ctx)
        
        builder = CfgBuilder()
        cfg = builder.lower_function(sem_func)
        CfgVerifier.verify(cfg.blocks)
        
        converter = SsaConverter(cfg, {"q": "INTEGER"})
        ssa_func = converter.convert()
        
        merge_blocks = [
            block
            for block in ssa_func.blocks.values()
            if len(block.phis) == 1
        ]

        self.assertEqual(len(merge_blocks), 1)
        SsaVerifier.verify(ssa_func, {"q": "INTEGER"})

if __name__ == "__main__":
    unittest.main()
