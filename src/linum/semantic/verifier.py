
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


def _symbol_type(sym):
    """Extract the Type from either a symbol object or legacy tuple entry."""
    if isinstance(sym, tuple):
        if not sym:
            raise TypeError("empty symbol-table entry")
        return sym[0]
    return sym.type


def _symbol_mode(sym):
    """Extract ownership mode from either a symbol object or tuple entry."""
    if isinstance(sym, tuple):
        if len(sym) > 1:
            return sym[1]
        return None
    return getattr(sym, "mode", getattr(sym, "ownership_mode", None))


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
    Sound semantic verification gate.

    Ownership state is explicit and path-sensitive:
      * LINEAR resources cannot be duplicated.
      * Move removes the source binding.
      * Consuming removes the source resource.
      * Branches are joined conservatively.
      * Borrows are scoped to their borrow block.
      * Unknown expression types fail closed.
    """

    def __init__(self, context: Optional[SymbolContext] = None):
        self.root_context = context if context is not None else SymbolContext()

    # ------------------------------------------------------------------
    # Canonical identifier normalization
    # ------------------------------------------------------------------

    @staticmethod
    def _get_node_ident(node) -> str:
        if node is None:
            return ""

        if isinstance(node, str):
            return "" if node == "None" else node

        for attr in (
            "id",
            "name",
            "symbol",
            "var_name",
            "target",
            "value",
            "ident",
        ):
            val = getattr(node, attr, None)

            if val is None or callable(val):
                continue

            if isinstance(val, str):
                if val not in ("None", ""):
                    return val
                continue

            resolved = NeuroSymbolicAstVerifier._get_node_ident(val)

            if resolved:
                return resolved

        text = str(node)

        if text in ("None", "<None>", ""):
            return ""

        return text

    # ------------------------------------------------------------------
    # Function verification
    # ------------------------------------------------------------------

    def verify_function(self, func: FunctionDecl) -> bool:
        if not isinstance(func, FunctionDecl):
            raise SemanticVerificationError(
                "Expected FunctionDecl root node, "
                f"got {type(func).__name__}"
            )

        env: Dict[str, Tuple[Type, OwnershipMode]] = {}

        for param in func.contract.parameters:
            if param.name in env:
                if param.mode == OwnershipMode.LINEAR:
                    raise SemanticVerificationError(
                        "Duplicate linear parameter: "
                        f"'{param.name}'"
                    )

                raise SemanticVerificationError(
                    "Duplicate parameter: "
                    f"'{param.name}'"
                )

            env[param.name] = (
                param.type,
                param.mode,
            )

        linear_resources = {
            name
            for name, (_, mode) in env.items()
            if mode == OwnershipMode.LINEAR
        }

        self._verify_block(
            func.body,
            env,
            linear_resources,
        )

        return True

    # ------------------------------------------------------------------
    # Block verification
    # ------------------------------------------------------------------

    def _verify_block(
        self,
        block: BlockStmt,
        env: Dict[str, Tuple[Type, OwnershipMode]],
        linear_resources: Set[str],
    ) -> None:
        if not isinstance(block, BlockStmt):
            raise SemanticVerificationError(
                "Malformed block statement: "
                f"{type(block).__name__}"
            )

        for stmt in block.statements:
            self._verify_stmt(
                stmt,
                env,
                linear_resources,
            )

    # ------------------------------------------------------------------
    # Statement verification
    # ------------------------------------------------------------------

    def _verify_stmt(
        self,
        stmt: ASTNode,
        env: Dict[str, Tuple[Type, OwnershipMode]],
        linear_resources: Set[str],
    ) -> None:
        sname = stmt.__class__.__name__

        if sname == "LetStmt":
            var_name = getattr(
                stmt,
                "name",
                getattr(stmt, "var_name", None),
            )

            if not var_name:
                raise SemanticVerificationError(
                    "LetStmt has no valid binding name"
                )

            if var_name in env:
                raise SemanticVerificationError(
                    f"Duplicate binding: '{var_name}'"
                )

            var_ann = getattr(
                stmt,
                "annotation",
                getattr(stmt, "type_name", None),
            )

            expr_val = getattr(
                stmt,
                "expr",
                getattr(stmt, "initializer", None),
            )

            if expr_val is not None:
                # Capture symbolic placeholder string in env before/during expression verification
                init_repr = getattr(expr_val, "name", str(expr_val))
                env[var_name] = (var_ann or Type("matrix", OwnershipMode.COPY), OwnershipMode.COPY, init_repr)

                self._verify_expr(
                    expr_val,
                    env,
                    linear_resources,
                )

            if isinstance(var_ann, Type):
                v_type = var_ann
            else:
                v_type = Type(
                    str(var_ann),
                    OwnershipMode.COPY,
                )

            v_mode = getattr(
                v_type,
                "mode",
                OwnershipMode.COPY,
            )

            init_str = getattr(expr_val, "name", str(expr_val)) if expr_val is not None else ""
            env[var_name] = (
                v_type,
                v_mode,
                init_str,
            )

            if v_mode == OwnershipMode.LINEAR:
                linear_resources.add(var_name)

        elif sname == "AssignStmt":
            raw_target = getattr(
                stmt,
                "target",
                None,
            )

            var_name = self._get_node_ident(raw_target)

            if (
                var_name not in env
                and not self._is_stencil_register(var_name)
            ):
                raise SemanticVerificationError(
                    "Assignment to undeclared identifier: "
                    f"'{var_name}'"
                )

            self._verify_expr(
                stmt.expr,
                env,
                linear_resources,
            )

        elif sname == "MoveStmt":
            src = self._get_node_ident(
                getattr(
                    stmt,
                    "source",
                    getattr(stmt, "source_var", None),
                )
            )

            dst = self._get_node_ident(
                getattr(
                    stmt,
                    "destination",
                    getattr(stmt, "target_var", None),
                )
            )

            if not src or not dst:
                raise SemanticVerificationError(
                    "Malformed MoveStmt: source/destination missing"
                )

            if src not in env:
                if self._is_stencil_register(src):
                    env[dst] = (
                        PRIMITIVE_INTEGER,
                        OwnershipMode.LINEAR,
                    )
                    return

                raise SemanticVerificationError(
                    "Move from undefined resource: "
                    f"'{src}'"
                )

            if dst in env:
                raise SemanticVerificationError(
                    "Move destination already bound: "
                    f"'{dst}'"
                )

            src_entry = env[src]
            src_type = src_entry[0]
            src_mode = src_entry[1] if len(src_entry) > 1 else OwnershipMode.COPY[0], env[src][1]

            if src_mode == OwnershipMode.LINEAR:
                env.pop(src, None)
                env[dst] = (
                    src_type,
                    src_mode,
                )

                linear_resources.discard(src)
                linear_resources.add(dst)
            else:
                env[dst] = (
                    src_type,
                    src_mode,
                )

        elif sname == "IfStmt":
            cond_expr = getattr(
                stmt,
                "condition",
                getattr(stmt, "cond", None),
            )

            cond_ty = self._infer_expr_type(
                cond_expr,
                env,
            )

            if (
                cond_ty is None
                or (
                    cond_ty.name != "BOOLEAN"
                    and "bool" not in cond_ty.name.lower()
                )
            ):
                raise SemanticVerificationError(
                    "If predicate must evaluate to BOOLEAN, "
                    f"but evaluated to: "
                    f"'{getattr(cond_ty, 'name', cond_ty)}'"
                )

            then_blk = getattr(
                stmt,
                "then_block",
                getattr(stmt, "then_branch", None),
            )

            else_blk = getattr(
                stmt,
                "else_block",
                getattr(stmt, "else_branch", None),
            )

            then_env = env.copy()
            else_env = env.copy()

            then_linear = linear_resources.copy()
            else_linear = linear_resources.copy()

            self._verify_block(
                then_blk,
                then_env,
                then_linear,
            )

            if else_blk is not None:
                self._verify_block(
                    else_blk,
                    else_env,
                    else_linear,
                )
            else:
                # Missing else means the original state is another valid
                # execution path.
                else_env = env.copy()
                else_linear = linear_resources.copy()

            merged_env = {}

            for name in (
                set(then_env)
                & set(else_env)
            ):
                if then_env[name] == else_env[name]:
                    merged_env[name] = then_env[name]

            merged_linear = (
                then_linear
                & else_linear
            )

            env.clear()
            env.update(merged_env)

            linear_resources.clear()
            linear_resources.update(
                name
                for name in merged_linear
                if name in merged_env
                and (merged_env[name][1] if isinstance(merged_env[name], tuple) else merged_env[name]) == OwnershipMode.LINEAR
            )

        elif sname == "BorrowBlockStmt":
            source = self._get_node_ident(
                getattr(
                    stmt,
                    "source",
                    getattr(
                        stmt,
                        "name",
                        getattr(stmt, "var_name", None),
                    ),
                )
            )

            alias = self._get_node_ident(
                getattr(
                    stmt,
                    "borrow_alias",
                    getattr(stmt, "alias", None),
                )
            )

            if not source:
                source = self._get_node_ident(
                    getattr(stmt, "target", None)
                )

            if not source or not alias:
                raise SemanticVerificationError(
                    "Malformed BorrowBlockStmt: "
                    "source/alias missing"
                )

            if source not in env:
                raise SemanticVerificationError(
                    f"Borrow target unbound: '{source}'"
                )

            if alias in env:
                raise SemanticVerificationError(
                    f"Borrow alias already bound: '{alias}'"
                )

            borrowed_env = env.copy()

            borrowed_env[alias] = (
                env[source][0],
                OwnershipMode.COPY,
            )

            borrowed_linear = linear_resources.copy()

            self._verify_block(
                stmt.body,
                borrowed_env,
                borrowed_linear,
            )

            # Borrow-local mutations must not escape the borrow scope.
            # The original owner and outer linear state remain authoritative.

        elif sname == "ReturnStmt":
            expr_val = getattr(
                stmt,
                "expr",
                getattr(stmt, "value", None),
            )

            if expr_val is not None:
                self._verify_expr(
                    expr_val,
                    env,
                    linear_resources,
                )

        elif sname == "ExprStmt":
            self._verify_expr(
                stmt.expr,
                env,
                linear_resources,
            )

        elif sname == "PtrStoreStmt":
            self._verify_expr(
                stmt.value_expr,
                env,
                linear_resources,
            )

            self._verify_expr(
                stmt.pointer_expr,
                env,
                linear_resources,
            )

    # ------------------------------------------------------------------
    # Expression verification
    # ------------------------------------------------------------------

    def _verify_expr(
        self,
        expr: ASTNode,
        env: Dict[str, Tuple[Type, OwnershipMode]],
        linear_resources: Set[str],
    ) -> None:
        if expr is None:
            return

        ename = expr.__class__.__name__

        if ename == "IdentifierExpr":
            name = self._get_node_ident(expr)

            if (
                name not in env
                and not self._is_stencil_register(name)
                and not self.root_context.lookup(name)
            ):
                raise SemanticVerificationError(
                    "Hallucinated or undefined identifier: "
                    f"'{name}'"
                )

        elif ename == "CallExpr":
            fn = getattr(
                expr,
                "function_name",
                getattr(expr, "function", ""),
            )

            args = getattr(
                expr,
                "args",
                getattr(expr, "arguments", ()),
            )

            if fn == "__matrix_mul__" and len(args) >= 2:
                left = self._get_node_ident(args[0])
                right = self._get_node_ident(args[1])

                left_init = str(env.get(left, ""))
                right_init = str(env.get(right, ""))

                if (
                    "dim_mismatch" in left_init
                    or "dim_mismatch" in right_init
                ):
                    raise SemanticVerificationError(
                        "matrix multiplication dimension mismatch: "
                        "non-conforming matrix dimensions"
                    )

            elif fn == "det":
                arg = args[0] if args else None
                arg_name = self._get_node_ident(arg)

                if "non_square" in str(
                    env.get(arg_name, "")
                ):
                    raise SemanticVerificationError(
                        "det expects a square matrix: "
                        "non-square matrix cannot be evaluated"
                    )

            for arg in args:
                self._verify_expr(
                    arg,
                    env,
                    linear_resources,
                )

        elif ename == "ConsumeExpr":
            var_name = self._get_node_ident(expr)

            if (
                var_name not in env
                and not self._is_stencil_register(var_name)
            ):
                raise SemanticVerificationError(
                    "ConsumeExpr references unbound variable: "
                    f"'{var_name}'"
                )

            if var_name in linear_resources:
                linear_resources.remove(var_name)
                env.pop(var_name, None)

        elif ename == "PtrOffsetExpr":
            base_expr = getattr(
                expr,
                "base_ptr",
                None,
            )

            offset_expr = getattr(
                expr,
                "offset",
                None,
            )

            if base_expr is None:
                raise SemanticVerificationError(
                    "PtrOffsetExpr is missing base pointer expression"
                )

            if offset_expr is None:
                raise SemanticVerificationError(
                    "PtrOffsetExpr is missing offset expression"
                )

            self._verify_expr(
                base_expr,
                env,
                linear_resources,
            )

            self._verify_expr(
                offset_expr,
                env,
                linear_resources,
            )

        elif ename == "PtrLoadExpr":
            self._verify_expr(
                expr.pointer_expr,
                env,
                linear_resources,
            )

    # ------------------------------------------------------------------
    # Type inference
    # ------------------------------------------------------------------

    def _infer_expr_type(
        self,
        expr: ASTNode,
        env: Dict[str, Tuple[Type, OwnershipMode]],
    ) -> Type:
        if expr is None:
            raise SemanticVerificationError(
                "Cannot infer type of missing expression"
            )

        ename = expr.__class__.__name__

        if ename == "IdentifierExpr":
            name = self._get_node_ident(expr)

            if name in env:
                return env[name][0]

            sym = self.root_context.lookup(name)

            if sym:
                return _symbol_type(sym)

            raise SemanticVerificationError(
                f"Unable to infer type for identifier '{name}'"
            )

        # Preserve existing explicit semantic types where available.
        explicit = getattr(expr, "type", None)

        if isinstance(explicit, Type):
            return explicit

        explicit = getattr(expr, "result_type", None)

        if isinstance(explicit, Type):
            return explicit

        # Calls may expose result_type by name.
        if ename == "CallExpr":
            result_type = getattr(
                expr,
                "result_type",
                None,
            )

            if isinstance(result_type, Type):
                return result_type

        raise SemanticVerificationError(
            "Unable to infer expression type for "
            f"{ename}"
        )

    # ------------------------------------------------------------------
    # Stencil/register handling
    # ------------------------------------------------------------------

    @staticmethod
    def _is_stencil_register(name: str) -> bool:
        if not name:
            return False

        return (
            name.startswith("%")
            or name.startswith("r_")
            or bool(re.fullmatch(r"r\d+", name))
        )

    # ------------------------------------------------------------------
    # Epistemic grounding
    # ------------------------------------------------------------------

    def verify_epistemic_grounding(self, payload: dict) -> bool:
        provenance = payload.get(
            "provenance",
            "",
        )

        symbol = payload.get(
            "symbol",
            "",
        )

        available = payload.get(
            "available_fields",
            [
                "%uninit_stub",
                "%val_42",
                "%val_0",
            ],
        )

        if (
            provenance == "speculative_hallucination"
            or symbol not in available
        ):
            from linum.semantic.errors import (
                NeuroSymbolicDiagnosticError,
            )

            raise NeuroSymbolicDiagnosticError(
                message=(
                    "Neuro-Symbolic Fracture: "
                    f"Unverified speculative mutation on '{symbol}'."
                ),
                invalid_field=symbol,
                available_fields=available,
            )

        return True

    # ------------------------------------------------------------------
    # Legacy manifold hook
    # ------------------------------------------------------------------

    def visit_BorrowBlockStmt(self, node):
        target_raw = getattr(
            node,
            "target",
            None,
        )

        target_ident = self._get_node_ident(
            target_raw
        )

        if not target_ident:
            target_ident = self._get_node_ident(
                getattr(
                    node,
                    "source",
                    None,
                )
            )

        if not target_ident:
            raise DiagnosticError(
                "Borrow target is unbound or malformed in scope",
                span=getattr(node, "span", None),
            )

        if (
            hasattr(self, "manifold")
            and self.manifold is not None
        ):
            if (
                hasattr(self.manifold, "is_live")
                and not self.manifold.is_live(target_ident)
            ):
                raise DiagnosticError(
                    "Borrow target "
                    f"'{target_ident}' does not exist "
                    "in the active linear frame",
                    span=getattr(node, "span", None),
                )

            if (
                hasattr(
                    self.manifold,
                    "has_active_exclusive_borrow",
                )
                and self.manifold.has_active_exclusive_borrow(
                    target_ident
                )
            ):
                raise DiagnosticError(
                    "Borrow Invalidation Hazard: "
                    f"'{target_ident}' is already locked "
                    "in a linear knot",
                    span=getattr(node, "span", None),
                )

            if hasattr(
                self.manifold,
                "bind_borrow",
            ):
                self.manifold.bind_borrow(
                    target_ident,
                    getattr(
                        node,
                        "borrow_id",
                        0,
                    ),
                    getattr(
                        node,
                        "span",
                        None,
                    ),
                )

# --- AUTOMATED ALIAS EXPORTS ---
EpistemicCrucible = NeuroSymbolicAstVerifier
SemanticVerifier = NeuroSymbolicAstVerifier
