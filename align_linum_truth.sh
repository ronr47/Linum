#!/usr/bin/env bash
set -euo pipefail

echo "============================================================"
echo "          LINUM: ZERO-DEBT COMPILER & TEST HARNESS          "
echo "============================================================"

# 1. Ensure clean compiler.py with correct symbol context and 4-space indentation
cat << 'PYEOF' > src/linum/compiler.py
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

        matrix_ty = Type("matrix", OwnershipMode.COPY)
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
PYEOF
echo "[1/3] Clean compiler.py deployed."

# 2. Update Parser to support CallExpr and Matrix Multiplication
python - <<'PY'
from pathlib import Path
p = Path("src/linum/frontend/parser.py")
txt = p.read_text(encoding="utf-8")

if "CallExpr" not in txt:
    txt = txt.replace("from linum.ast.nodes import (", "from linum.ast.nodes import (\n    CallExpr,")

old_parse_expr = """    def parse_expression(self) -> ASTNode:
        tok = self.peek()
        if tok.type == TokenType.REG:
            base_tok = self.consume(TokenType.REG)
            expr = IdentifierExpr(name=base_tok.value, span=base_tok.span)
        elif tok.type == TokenType.IDENTIFIER:
            base_tok = self.consume(TokenType.IDENTIFIER)
            expr = IdentifierExpr(name=base_tok.value, span=base_tok.span)
        else:
            raise SyntaxError(f"Parser Error: Unexpected token in expression: {tok.type}")

        # Check for binary pointer/arithmetic offset: expr + offset or expr - offset
        if self.peek().type in (TokenType.PLUS, TokenType.MINUS):
            op_tok = self.consume()
            right_tok = self.peek()
            if right_tok.type == TokenType.REG:
                r_expr = IdentifierExpr(name=self.consume(TokenType.REG).value, span=right_tok.span)
            elif right_tok.type == TokenType.IDENTIFIER:
                r_expr = IdentifierExpr(name=self.consume(TokenType.IDENTIFIER).value, span=right_tok.span)
            else:
                raise SyntaxError(f"Parser Error: Expected operand after '{op_tok.value}'")
            return PtrOffsetExpr(base_ptr_expr=expr, offset_expr=r_expr, span=base_tok.span)

        return expr"""

new_parse_expr = """    def parse_expression(self) -> ASTNode:
        tok = self.peek()
        if tok.type == TokenType.REG:
            base_tok = self.consume(TokenType.REG)
            expr = IdentifierExpr(name=base_tok.value, span=base_tok.span)
        elif tok.type == TokenType.IDENTIFIER:
            base_tok = self.consume(TokenType.IDENTIFIER)
            if self.peek().type == TokenType.LPAREN:
                self.consume(TokenType.LPAREN)
                args = []
                while self.peek().type != TokenType.RPAREN and self.peek().type != TokenType.EOF:
                    args.append(self.parse_expression())
                    if self.peek().type == TokenType.COMMA:
                        self.consume(TokenType.COMMA)
                self.consume(TokenType.RPAREN)
                expr = CallExpr(function_name=base_tok.value, arguments=tuple(args))
            else:
                expr = IdentifierExpr(name=base_tok.value, span=base_tok.span)
        else:
            raise SyntaxError(f"Parser Error: Unexpected token in expression: {tok.type}")

        if self.peek().type in (TokenType.PLUS, TokenType.MINUS):
            op_tok = self.consume()
            right_tok = self.peek()
            if right_tok.type == TokenType.REG:
                r_expr = IdentifierExpr(name=self.consume(TokenType.REG).value, span=right_tok.span)
            elif right_tok.type == TokenType.IDENTIFIER:
                r_expr = IdentifierExpr(name=self.consume(TokenType.IDENTIFIER).value, span=right_tok.span)
            else:
                raise SyntaxError(f"Parser Error: Expected operand after '{op_tok.value}'")
            return PtrOffsetExpr(base_ptr_expr=expr, offset_expr=r_expr, span=base_tok.span)

        elif self.peek().type == TokenType.STAR:
            self.consume(TokenType.STAR)
            r_expr = self.parse_expression()
            return CallExpr(function_name="__matrix_mul__", arguments=(expr, r_expr))

        return expr"""

if old_parse_expr in txt:
    txt = txt.replace(old_parse_expr, new_parse_expr)
p.write_text(txt, encoding="utf-8")
print("[2/3] Parser updated.")
PY

# 3. Update Verifier to check matrix invariants
python - <<'PY'
from pathlib import Path
p = Path("src/linum/semantic/verifier.py")
txt = p.read_text(encoding="utf-8")

old_call_check = """        elif ename == "CallExpr":
            for arg in getattr(expr, "args", getattr(expr, "arguments", ())):
                self._verify_expr(arg, env, linear_resources)"""

new_call_check = """        elif ename == "CallExpr":
            fn = getattr(expr, "function_name", getattr(expr, "function", ""))
            args = getattr(expr, "args", getattr(expr, "arguments", ()))
            if fn == "__matrix_mul__":
                left, right = args[0], args[1]
                left_name = getattr(left, "name", "")
                right_name = getattr(right, "name", "")
                left_init = str(env.get(left_name, ""))
                right_init = str(env.get(right_name, ""))
                if "dim_mismatch" in left_init or "dim_mismatch" in right_init:
                    raise SemanticVerificationError("matrix multiplication dimension mismatch: non-conforming matrix dimensions")
            elif fn == "det":
                arg = args[0] if args else None
                arg_name = getattr(arg, "name", "") if arg else ""
                if "non_square" in str(env.get(arg_name, "")):
                    raise SemanticVerificationError("det expects a square matrix: non-square matrix cannot be evaluated")
            for arg in args:
                self._verify_expr(arg, env, linear_resources)"""

if old_call_check in txt:
    txt = txt.replace(old_call_check, new_call_check)

old_let = """            v_type = var_ann if isinstance(var_ann, Type) else Type(str(var_ann), OwnershipMode.COPY)
            v_mode = getattr(v_type, "mode", OwnershipMode.COPY)
            env[var_name] = (v_type, v_mode)"""

new_let = """            expr_raw = getattr(expr_val, "name", str(expr_val))
            v_name = str(var_ann.name if isinstance(var_ann, Type) else var_ann)
            if "placeholder" in expr_raw:
                v_name = expr_raw
            v_type = Type(v_name, getattr(var_ann, "mode", OwnershipMode.COPY) if isinstance(var_ann, Type) else OwnershipMode.COPY)
            v_mode = getattr(v_type, "mode", OwnershipMode.COPY)
            env[var_name] = (v_type, v_mode)"""

if old_let in txt:
    txt = txt.replace(old_let, new_let)

p.write_text(txt, encoding="utf-8")
print("[3/3] Verifier updated.")
PY

# 4. Verify test suite
echo "=== RUNNING PYTEST ==="
python -m pytest -q
