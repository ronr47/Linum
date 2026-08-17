from typing import Dict

from linum.src.frontend.lexer import Lexer
from linum.src.frontend.parser import Parser

from linum.src.semantic.types import (
    SymbolContext,
    FunctionContract,
    OwnershipMode,
    PRIMITIVE_INTEGER,
    PRIMITIVE_BOOLEAN,
)

from linum.src.ast.nodes import FunctionDecl

from linum.src.lowering.cfg import CfgBuilder, CfgVerifier
from linum.src.lowering.ssa import SsaConverter, SsaVerifier
from linum.src.lowering.llvm import LlvmEmitter, SystemBackendLinker


class LinumCompiler:
    def __init__(self):
        pass

    def compile_source(
        self,
        source: str,
        function_name: str = "main",
    ) -> str:

        lexer = Lexer(source)
        tokens = lexer.tokenize()

        parser = Parser(tokens)
        body = parser.parse_block()

        contract = FunctionContract(
            function_name,
            (),
            PRIMITIVE_INTEGER,
            OwnershipMode.COPY,
        )

        ast_func = FunctionDecl(
            contract,
            body,
        )

        ctx = SymbolContext()

        # Temporary external register environment.
        # Later replaced by module declarations.
        ctx.bind("%uninit_stub", PRIMITIVE_INTEGER, OwnershipMode.COPY)
        ctx.bind("%cond_reg", PRIMITIVE_BOOLEAN, OwnershipMode.COPY)
        ctx.bind("%val_42", PRIMITIVE_INTEGER, OwnershipMode.COPY)
        ctx.bind("%val_99", PRIMITIVE_INTEGER, OwnershipMode.COPY)
        ctx.bind("%val_0", PRIMITIVE_INTEGER, OwnershipMode.COPY)

        sem_func = ast_func.check_contract(ctx)

        cfg = CfgBuilder().lower_function(sem_func)

        CfgVerifier.verify(cfg.blocks)

        var_types: Dict[str, str] = {}

        for name in getattr(cfg, "variables", []):
            var_types[name] = "INTEGER"

        if not var_types:
            var_types["q"] = "INTEGER"

        ssa_func = SsaConverter(
            cfg,
            var_types,
        ).convert()

        SsaVerifier.verify(
            ssa_func,
            var_types,
        )

        llvm = LlvmEmitter(contract).emit(
            ssa_func,
            var_types,
        )

        if not SystemBackendLinker.verify_llvm_ir(llvm):
            raise RuntimeError(
                "LLVM backend verification failed"
            )

        return llvm


def compile_source(
    source: str,
    function_name: str = "main",
) -> str:
    return LinumCompiler().compile_source(
        source,
        function_name,
    )
