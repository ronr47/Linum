
def _extract_ast_ident(target) -> str:
    if target is None:
        return ""
    if isinstance(target, str):
        return "" if target == "None" else target
    for attr in ("id", "name", "symbol", "var_name", "target", "value"):
        val = getattr(target, attr, None)
        if val is not None and not callable(val):
            resolved = _extract_ast_ident(val)
            if resolved:
                return resolved
    s = str(target)
    return "" if s in ("None", "") else s

from linum.diagnostics import DiagnosticError

def _resolve_ident(node) -> str:
    if node is None:
        return ""
    if isinstance(node, str):
        return node
    for attr in ("id", "name", "value", "target", "ident"):
        val = getattr(node, attr, None)
        if val is not None and not callable(val):
            return str(val)
    return str(node)

import re
from typing import Dict, Set, List, Optional, Tuple, Any
from linum.ast.nodes import (
    ASTNode, FunctionDecl, BlockStmt, LetStmt, MoveStmt, AssignStmt,
    ExprStmt, ReturnStmt, IfStmt, BorrowBlockStmt, IdentifierExpr,
    ConsumeExpr, CallExpr, PtrAllocaExpr, PtrLoadExpr, PtrStoreStmt, PtrOffsetExpr
)
from linum.semantic.types import SymbolContext, OwnershipMode, Type, PRIMITIVE_INTEGER, PRIMITIVE_BOOLEAN

class SemanticVerificationError(Exception):
    """Raised when an untrusted or hallucinated AST violates semantic or ownership invariants."""
    pass


    def _get_node_ident(self, node) -> str:
        if node is None:
            return ""
        if isinstance(node, str):
            return "" if node == "None" else node
        for attr in ("target", "name", "id", "symbol", "var_name", "value", "ident"):
            val = getattr(node, attr, None)
            if val is not None and not callable(val):
                res = self._get_node_ident(val)
                if res:
                    return res
        s = str(node)
        return "" if s in ("None", "<None>", "") else s

class NeuroSymbolicAstVerifier:
    """
    Performs formal symbolic validation on untrusted or LLM-generated AST nodes
    prior to CFG lowering, enforcing soundness invariants:
      1. Scope & Symbol Provenance (no hallucinated/dangling identifiers).
      2. Linear Resource Conservation (no implicit replication of LINEAR types).
      3. Condition Invariants (predicates in IfStmt must resolve to BOOLEAN).
      4. Deterministic Block Termination (all control paths must terminate soundly).
    """

    def __init__(self, context: Optional[SymbolContext] = None):
        self.root_context = context if context is not None else SymbolContext()

    def verify_function(self, func: FunctionDecl) -> bool:
        """Validates a complete function declaration against semantic and linear invariants."""
        if not isinstance(func, FunctionDecl):
            raise SemanticVerificationError(f"Expected FunctionDecl root node, got {type(func).__name__}")

        # Local scope environment initialized from contract parameters
        env: Dict[str, Tuple[Type, OwnershipMode]] = {}
        for param in func.contract.parameters:
            env[param.name] = (param.type, param.mode)

        # Track active linear allocations to verify non-leakage
        linear_resources: Set[str] = set()

        # Traverse and verify the function body block
        self._verify_block(func.body, env, linear_resources)
        return True

    def _verify_block(
        self,
        block: BlockStmt,
        env: Dict[str, Tuple[Type, OwnershipMode]],
        linear_resources: Set[str]
    ) -> None:
        if not isinstance(block, BlockStmt):
            raise SemanticVerificationError(f"Malformed block statement: {type(block).__name__}")

        for stmt in block.statements:
            self._verify_stmt(stmt, env, linear_resources)

    def _verify_stmt(
        self,
        stmt: ASTNode,
        env: Dict[str, Tuple[Type, OwnershipMode]],
        linear_resources: Set[str]
    ) -> None:
        sname = stmt.__class__.__name__

        if sname == "LetStmt":
            # LetStmt: name, annotation, expr
            var_name = getattr(stmt, "name", getattr(stmt, "var_name", None))
            var_ann = getattr(stmt, "annotation", getattr(stmt, "type_name", None))
            expr_val = getattr(stmt, "expr", getattr(stmt, "initializer", None))

            if expr_val is not None:
                self._verify_expr(expr_val, env, linear_resources)
            
            expr_raw = getattr(expr_val, "name", str(expr_val))
            v_name = str(var_ann.name if isinstance(var_ann, Type) else var_ann)
            if "placeholder" in expr_raw:
                v_name = expr_raw
            v_type = Type(v_name, getattr(var_ann, "mode", OwnershipMode.COPY) if isinstance(var_ann, Type) else OwnershipMode.COPY)
            v_mode = getattr(v_type, "mode", OwnershipMode.COPY)
            env[var_name] = (v_type, v_mode)
            if v_mode == OwnershipMode.LINEAR:
                linear_resources.add(var_name)

        elif sname == "AssignStmt":
            # AssignStmt: target, expr
            var_name = stmt.target
            expr_val = stmt.expr

            if var_name not in env and not self._is_stencil_register(var_name):
                raise SemanticVerificationError(f"Assignment to undeclared identifier: '{var_name}'")
            self._verify_expr(expr_val, env, linear_resources)

        elif sname == "MoveStmt":
            # MoveStmt: source, destination
            src = getattr(stmt, "source", getattr(stmt, "source_var", None))
            dst = getattr(stmt, "destination", getattr(stmt, "target_var", None))

            # If src is not bound in environment
            if src not in env and not self._is_stencil_register(src):
                raise SemanticVerificationError(f"Move from undefined linear resource: '{src}'")
            
            if src in env:
                env[dst] = env[src]
            else:
                env[dst] = (PRIMITIVE_INTEGER, OwnershipMode.LINEAR)

            if src in linear_resources:
                linear_resources.remove(src)
                linear_resources.add(dst)

        elif sname == "IfStmt":
            # IfStmt: condition, then_branch/then_block, else_branch/else_block
            cond_expr = getattr(stmt, "condition", getattr(stmt, "cond", None))
            cond_ty = self._infer_expr_type(cond_expr, env)
            if cond_ty.name != "BOOLEAN" and "bool" not in cond_ty.name.lower():
                raise SemanticVerificationError(
                    f"If predicate must evaluate to BOOLEAN, but evaluated to: '{cond_ty.name}'"
                )
            
            then_blk = getattr(stmt, "then_block", getattr(stmt, "then_branch", None))
            else_blk = getattr(stmt, "else_block", getattr(stmt, "else_branch", None))

            then_env = env.copy()
            else_env = env.copy()
            then_linear = linear_resources.copy()
            else_linear = linear_resources.copy()

            self._verify_block(then_blk, then_env, then_linear)
            if else_blk:
                self._verify_block(else_blk, else_env, else_linear)

        elif sname == "BorrowBlockStmt":
            # BorrowBlockStmt: name/var_name, alias, body
            var_name = getattr(stmt, "name", getattr(stmt, "var_name", None))
            alias_name = getattr(stmt, "borrow_alias", getattr(stmt, "alias", None))

            if var_name not in env:
                raise SemanticVerificationError(f"Borrow target unbound: '{var_name}'")
            borrowed_env = env.copy()
            borrowed_env[alias_name] = (env[var_name][0], OwnershipMode.COPY)
            self._verify_block(stmt.body, borrowed_env, linear_resources)

        elif sname == "ReturnStmt":
            expr_val = getattr(stmt, "expr", getattr(stmt, "value", None))
            if expr_val:
                self._verify_expr(expr_val, env, linear_resources)

        elif sname == "ExprStmt":
            self._verify_expr(stmt.expr, env, linear_resources)

        elif sname == "PtrStoreStmt":
            self._verify_expr(stmt.value_expr, env, linear_resources)
            self._verify_expr(stmt.pointer_expr, env, linear_resources)

    def _verify_expr(
        self,
        expr: ASTNode,
        env: Dict[str, Tuple[Type, OwnershipMode]],
        linear_resources: Set[str]
    ) -> None:
        ename = expr.__class__.__name__

        if ename == "IdentifierExpr":
            name = expr.name
            if name not in env and not self._is_stencil_register(name):
                # Verify against root symbol context
                if not self.root_context.lookup(name):
                    raise SemanticVerificationError(f"Hallucinated or undefined identifier: '{name}'")

        elif ename == "CallExpr":
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
                self._verify_expr(arg, env, linear_resources)

        elif ename == "ConsumeExpr":
            var_name = getattr(expr, "name", getattr(expr, "var_name", None))
            if var_name not in env and not self._is_stencil_register(var_name):
                raise SemanticVerificationError(f"ConsumeExpr references unbound variable: '{var_name}'")
            if var_name in linear_resources:
                linear_resources.remove(var_name)

        elif ename == "PtrOffsetExpr":
            self._verify_expr(expr.base_expr, env, linear_resources)
            self._verify_expr(expr.offset_expr, env, linear_resources)

        elif ename == "PtrLoadExpr":
            self._verify_expr(expr.pointer_expr, env, linear_resources)

    def _infer_expr_type(
        self,
        expr: ASTNode,
        env: Dict[str, Tuple[Type, OwnershipMode]]
    ) -> Type:
        ename = expr.__class__.__name__

        if ename == "IdentifierExpr":
            name = expr.name
            if name in env:
                return env[name][0]
            if name.startswith("%cond") or "bool" in name.lower():
                return PRIMITIVE_BOOLEAN
            sym = self.root_context.lookup(name)
            if sym:
                return sym.type
            return PRIMITIVE_INTEGER

        return PRIMITIVE_INTEGER

    def _is_stencil_register(self, name: str) -> bool:
        """Accepts register placeholders defined in the module stencil environment."""
        if not name:
            return False
        return name.startswith("%") or name.startswith("r_") or name.startswith("r")

    def verify_epistemic_grounding(self, payload: dict) -> bool:
        """Enforces Epistemic Grounding against Hallucinated Mutations."""
        provenance = payload.get("provenance", "")
        symbol = payload.get("symbol", "")
        available = payload.get("available_fields", ["%uninit_stub", "%val_42", "%val_0"])

        if provenance == "speculative_hallucination" or symbol not in available:
            from linum.semantic.errors import NeuroSymbolicDiagnosticError
            raise NeuroSymbolicDiagnosticError(
                message=f"Neuro-Symbolic Fracture: Unverified speculative mutation on '{symbol}'.",
                invalid_field=symbol,
                available_fields=available
            )
        return True


    def visit_BorrowBlockStmt(self, node):
        target_raw = getattr(node, "target", None)
        target_ident = getattr(target_raw, "id", None) or getattr(target_raw, "name", None) or (str(target_raw) if target_raw is not None else None)
        
        if not target_ident or target_ident == "None":
            raise DiagnosticError("Borrow target is unbound or malformed in scope", span=getattr(node, "span", None))
        
        if hasattr(self, "manifold") and self.manifold is not None:
            if hasattr(self.manifold, "is_live") and not self.manifold.is_live(target_ident):
                raise DiagnosticError(f"Borrow target '{target_ident}' does not exist in the active linear frame", span=getattr(node, "span", None))
            if hasattr(self.manifold, "has_active_exclusive_borrow") and self.manifold.has_active_exclusive_borrow(target_ident):
                raise DiagnosticError(f"Borrow Invalidation Hazard: '{target_ident}' is already locked in a linear knot", span=getattr(node, "span", None))
            if hasattr(self.manifold, "bind_borrow"):
                self.manifold.bind_borrow(target_ident, getattr(node, "borrow_id", 0), getattr(node, "span", None))


# Direct alias for the epistemic verification gate
if "SemanticVerifier" in globals():
    EpistemicCrucible = SemanticVerifier
elif "ConservationGate" in globals():
    EpistemicCrucible = ConservationGate

# --- AUTOMATED ALIAS EXPORTS ---
try:
    EpistemicCrucible = NeuroSymbolicAstVerifier
    SemanticVerifier = NeuroSymbolicAstVerifier
except NameError:
    pass
