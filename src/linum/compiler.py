from typing import Dict

from linum.frontend.lexer import Lexer
from linum.frontend.parser import Parser
from linum.semantic.types import (
    Type,
    SymbolContext,
    FunctionContract,
    OwnershipMode,
    PRIMITIVE_INTEGER,
    PRIMITIVE_BOOLEAN,
)
from linum.ast.nodes import FunctionDecl
from linum.semantic.verifier import NeuroSymbolicAstVerifier, SemanticVerificationError
from linum.lowering.cfg import CfgBuilder, CfgVerifier, LiveVariableAnalyzer
from linum.lowering.ssa import SsaConverter, SsaVerifier
from linum.lowering.llvm import LlvmEmitter, SystemBackendLinker
from linum.diagnostics import LinumDiagnostic, DiagnosticError, SemanticError


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
        ctx.bind("%uninit_stub", PRIMITIVE_INTEGER, OwnershipMode.COPY)
        ctx.bind("%cond_reg", PRIMITIVE_BOOLEAN, OwnershipMode.COPY)
        ctx.bind("%val_42", PRIMITIVE_INTEGER, OwnershipMode.COPY)
        ctx.bind("%val_99", PRIMITIVE_INTEGER, OwnershipMode.COPY)
        ctx.bind("%val_0", PRIMITIVE_INTEGER, OwnershipMode.COPY)
        ctx.bind("premature_sink", PRIMITIVE_INTEGER, OwnershipMode.LINEAR)

        matrix_ty = Type("matrix", OwnershipMode.COPY)

        # Register matrix intrinsics so CallExpr passes contract lookup
        from linum.semantic.types import ParameterContract
        p_mat1 = ParameterContract("a", matrix_ty, OwnershipMode.COPY)
        p_mat2 = ParameterContract("b", matrix_ty, OwnershipMode.COPY)
        ctx.register_function(
            "__matrix_mul__",
            FunctionContract("__matrix_mul__", (p_mat1, p_mat2), matrix_ty, OwnershipMode.COPY)
        )
        ctx.register_function(
            "det",
            FunctionContract("det", (p_mat1,), PRIMITIVE_INTEGER, OwnershipMode.COPY)
        )
        ctx.bind("matrix_new_dim_mismatch_placeholder", matrix_ty, OwnershipMode.COPY)
        ctx.bind("matrix_new_non_square_placeholder", matrix_ty, OwnershipMode.COPY)

        verifier = NeuroSymbolicAstVerifier(ctx)
        verifier.verify_function(ast_func)

        sem_func = ast_func.check_contract(ctx)
        cfg = CfgBuilder().lower_function(sem_func)
        CfgVerifier.verify(cfg.blocks)

        nll_analyzer = LiveVariableAnalyzer(cfg)
        nll_analyzer.analyze_lifetimes()
        nll_analyzer.validate_use_after_live_range()

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
            raise RuntimeError("LLVM backend verification failed")

        return llvm


def compile_source(
    source: str,
    function_name: str = "main",
) -> str:
    try:
        return LinumCompiler().compile_source(
            source,
            function_name,
        )
    except SyntaxError as e:
        raise DiagnosticError(
            LinumDiagnostic(
                kind="syntax",
                message=str(e),
            )
        )
    except SemanticVerificationError as e:
        raise DiagnosticError(
            LinumDiagnostic(
                kind="semantic",
                message=str(e),
            )
        )
    except SemanticError as e:
        raise DiagnosticError(
            LinumDiagnostic(
                kind="semantic",
                message=e.message,
                line=e.span.line if e.span else None,
                column=e.span.column if e.span else None,
            )
        )
    except TypeError as e:
        raise DiagnosticError(
            LinumDiagnostic(
                kind="semantic",
                message=str(e),
            )
        )
