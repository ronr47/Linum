from dataclasses import dataclass
from typing import Dict, List, Set, Tuple, Optional

from linum.diagnostics.span import SourceSpan, UNKNOWN_SPAN
from linum.diagnostics.semantic import SemanticError

from linum.semantic.types import (
    Type,
    OwnershipMode,
    FunctionContract,
    SymbolContext,
    PRIMITIVE_BOOLEAN,
    PRIMITIVE_INTEGER,
)

from linum.semantic.analyzer import (
    SemanticNode,
    FlowState,
    OwnerState,
    BorrowCapability,
    DropAction,
    SemIdentifierExpr,
    SemConsumeExpr,
    SemCallArg,
    SemCallExpr,
    SemLetStmt,
    SemMoveStmt,
    SemAssignStmt,
    SemExprStmt,
    SemReturnStmt,
    SemBlockStmt,
    SemBorrowBlockStmt,
    SemIfStmt,
    SemFunctionDecl,
    strict_lattice_join,
    join_borrows,
)


class ASTNode:
    span: SourceSpan = UNKNOWN_SPAN

    def check_type(self, ctx: SymbolContext) -> Type:
        raise NotImplementedError()

    def check_ownership(
        self,
        flow: FlowState,
        ctx: SymbolContext,
        next_borrow_id: List[int],
    ) -> Tuple[FlowState, SemanticNode]:
        raise NotImplementedError()


@dataclass(frozen=True)
class IdentifierExpr(ASTNode):
    name: str
    span: SourceSpan = UNKNOWN_SPAN

    def check_type(self, ctx: SymbolContext) -> Type:
        ty, _ = ctx.lookup(self.name)
        return ty

    def check_ownership(
        self,
        flow: FlowState,
        ctx: SymbolContext,
        next_borrow_id: List[int],
    ) -> Tuple[FlowState, SemanticNode]:
        if self.name.startswith("%"):
            return flow, SemIdentifierExpr(
                self.name,
                self.check_type(ctx),
            )

        if self.name not in flow.ownership:
            raise TypeError(
                f"Tracking Failure: Context frame contains no trace "
                f"for variable '{self.name}'."
            )

        state = flow.ownership[self.name]

        if state in (
            OwnerState.MOVED,
            OwnerState.DEAD,
            OwnerState.UNINITIALIZED,
        ):
            raise SemanticError(
                f"Use-After-Move / Uninitialized Violation: "
                f"Variable '{self.name}' has been invalidated "
                f"({state.name}).",
                self.span,
            )

        if flow.active_borrows.get(self.name):
            raise TypeError(
                f"Borrow Invalidation Hazard: Cannot move or access "
                f"resource '{self.name}' while active borrows exist."
            )

        _, mode = ctx.lookup(self.name)
        new_flow = flow.clone()
        if mode in (OwnershipMode.LINEAR, OwnershipMode.AFFINE):
            new_flow.ownership[self.name] = OwnerState.MOVED

        return new_flow, SemIdentifierExpr(
            self.name,
            self.check_type(ctx),
        )


@dataclass(frozen=True)
class ConsumeExpr(ASTNode):
    source: str
    span: SourceSpan = UNKNOWN_SPAN

    def check_type(self, ctx: SymbolContext) -> Type:
        ty, _ = ctx.lookup(self.source)
        return ty

    def check_ownership(
        self,
        flow: FlowState,
        ctx: SymbolContext,
        next_borrow_id: List[int],
    ) -> Tuple[FlowState, SemanticNode]:
        ty, mode = ctx.lookup(self.source)

        if mode == OwnershipMode.COPY:
            return flow, SemConsumeExpr(self.source, ty)

        state = flow.ownership.get(
            self.source,
            OwnerState.DEAD,
        )

        borrows = flow.active_borrows.get(
            self.source,
            set(),
        )

        if state != OwnerState.OWNED:
            raise TypeError(
                f"Invalid Terminal Destruction: Variable "
                f"'{self.source}' is already {state.name}."
            )

        if borrows:
            raise TypeError(
                f"Aliasing Hazard: Cannot drop/consume "
                f"'{self.source}' with open active borrow traces."
            )

        new_flow = flow.clone()
        new_flow.ownership[self.source] = OwnerState.DEAD

        return new_flow, SemConsumeExpr(
            self.source,
            ty,
        )


@dataclass(frozen=True)
class CallExpr(ASTNode):
    function_name: str
    arguments: Tuple[ASTNode, ...]

    def check_type(self, ctx: SymbolContext) -> Type:
        contract = ctx.lookup_function(self.function_name)

        if contract.return_type is None:
            raise TypeError(
                f"Type Error: Function '{self.function_name}' "
                f"has no return type."
            )

        return contract.return_type

    def check_ownership(
        self,
        flow: FlowState,
        ctx: SymbolContext,
        next_borrow_id: List[int],
    ) -> Tuple[FlowState, SemanticNode]:
        contract = ctx.lookup_function(
            self.function_name
        )

        if len(self.arguments) != len(contract.parameters):
            raise TypeError(
                f"Call Contract Failure: Param count mismatch "
                f"for '{self.function_name}'."
            )

        working_flow = flow.clone()
        sem_call_args = []
        locked_borrows_for_call: Dict[
            str,
            BorrowCapability,
        ] = {}

        for expr, param in zip(
            self.arguments,
            contract.parameters,
        ):
            arg_type = expr.check_type(ctx)

            if not ctx.is_assignable(
                arg_type,
                param.type,
            ):
                raise TypeError(
                    f"Call Type Failure: Argument type "
                    f"{arg_type} incompatible with parameter "
                    f"type {param.type}."
                )

            src_name = (
                expr.name
                if isinstance(expr, IdentifierExpr)
                else None
            )

            working_flow, sem_expr = (
                expr.check_ownership(
                    working_flow,
                    ctx,
                    next_borrow_id,
                )
            )

            if not param.borrowed:
                if param.mode != OwnershipMode.COPY:
                    if src_name is None:
                        raise TypeError(
                            "Ownership Rule Error: Non-COPY "
                            "transfers require explicit variable "
                            "references."
                        )

                    src_borrows = (
                        working_flow.active_borrows.get(
                            src_name,
                            set(),
                        )
                    )

                    if src_borrows:
                        raise TypeError(
                            f"Aliasing Hazard: Cannot move parameter "
                            f"source '{src_name}' into call; active "
                            f"borrows exist."
                        )

            else:
                if src_name is None:
                    raise TypeError(
                        "Reference Error: Bounded call-site borrows "
                        "require nominal identifier expressions."
                    )

                src_state = working_flow.ownership.get(
                    src_name,
                    OwnerState.DEAD,
                )

                if src_state != OwnerState.OWNED:
                    raise TypeError(
                        f"Reference Hazard: Cannot branch out a "
                        f"borrow contract from a {src_state.name} "
                        f"resource."
                    )

                if param.mode != OwnershipMode.COPY:
                    cap_id = next_borrow_id[0]
                    next_borrow_id[0] += 1

                    synthetic_alias = (
                        f"__call_site_alias_{src_name}"
                    )

                    new_cap = BorrowCapability(
                        cap_id,
                        src_name,
                        synthetic_alias,
                    )

                    working_flow.active_borrows.setdefault(
                        src_name,
                        set(),
                    ).add(new_cap)

                    locked_borrows_for_call[
                        src_name
                    ] = new_cap

            sem_call_args.append(
                SemCallArg(
                    sem_expr,
                    param.mode,
                    param.borrowed,
                    src_name,
                )
            )

        for src_var, cap_record in (
            locked_borrows_for_call.items()
        ):
            working_flow.active_borrows[
                src_var
            ].remove(cap_record)

        return (
            working_flow,
            SemCallExpr(
                self.function_name,
                tuple(sem_call_args),
                contract.return_type,
            ),
        )


@dataclass(frozen=True)
class LetStmt(ASTNode):
    name: str
    annotation: Type
    expr: ASTNode

    def check(
        self,
        ctx: SymbolContext,
        flow: FlowState,
        next_borrow_id: List[int],
    ) -> Tuple[FlowState, SemanticNode]:
        expr_type = self.expr.check_type(ctx)

        if not (
            isinstance(self.expr, IdentifierExpr)
            and self.expr.name.startswith("%")
        ):
            if not ctx.is_assignable(
                expr_type,
                self.annotation,
            ):
                raise TypeError(
                    f"Type Boundary Error: Cannot assign "
                    f"evaluated type {expr_type} to annotation "
                    f"{self.annotation}."
                )

        new_flow, sem_expr = self.expr.check_ownership(
            flow.clone(),
            ctx,
            next_borrow_id,
        )

        ctx.bind(
            self.name,
            self.annotation,
            self.annotation.mode,
        )

        new_flow.ownership[self.name] = OwnerState.OWNED
        new_flow.active_borrows[self.name] = set()

        return (
            new_flow,
            SemLetStmt(
                self.name,
                self.annotation,
                sem_expr,
            ),
        )


@dataclass(frozen=True)
class MoveStmt(ASTNode):
    source: str
    destination: str

    def check(
        self,
        ctx: SymbolContext,
        flow: FlowState,
        next_borrow_id: List[int],
    ) -> Tuple[FlowState, SemanticNode]:
        src_type, src_mode = ctx.lookup(self.source)
        dest_type, dest_mode = ctx.lookup(
            self.destination
        )

        if not ctx.is_assignable(
            src_type,
            dest_type,
        ):
            raise TypeError(
                f"Type Boundary Error: Cannot move "
                f"'{self.source}' into incompatible target "
                f"'{self.destination}'."
            )

        if src_mode == OwnershipMode.COPY:
            new_flow = flow.clone()
            new_flow.ownership[
                self.destination
            ] = OwnerState.OWNED

            return (
                new_flow,
                SemMoveStmt(
                    self.source,
                    self.destination,
                    src_type,
                ),
            )

        src_state = flow.ownership.get(
            self.source,
            OwnerState.DEAD,
        )

        src_borrows = flow.active_borrows.get(
            self.source,
            set(),
        )

        if src_state != OwnerState.OWNED:
            raise TypeError(
                f"Invalid Transfer Operation: Cannot relocate "
                f"'{self.source}' in a {src_state.name} state."
            )

        if src_borrows:
            raise TypeError(
                f"Aliasing Hazard: Cannot move out of "
                f"'{self.source}' while active borrows remain."
            )

        new_flow = flow.clone()

        dest_state = new_flow.ownership.get(
            self.destination,
            OwnerState.UNINITIALIZED,
        )

        if dest_state == OwnerState.OWNED:
            if dest_mode == OwnershipMode.LINEAR:
                raise TypeError(
                    f"Resource Leak Hazard: Overwriting active "
                    f"linear storage pointer '{self.destination}' "
                    f"before consumption."
                )

            if dest_mode == OwnershipMode.AFFINE:
                new_flow.drops.append(
                    DropAction(
                        self.destination,
                        dest_type,
                    )
                )

        new_flow.ownership[
            self.source
        ] = OwnerState.MOVED

        new_flow.ownership[
            self.destination
        ] = OwnerState.OWNED

        return (
            new_flow,
            SemMoveStmt(
                self.source,
                self.destination,
                src_type,
            ),
        )


@dataclass(frozen=True)
class AssignStmt(ASTNode):
    target: str
    expr: ASTNode

    def check(
        self,
        ctx: SymbolContext,
        flow: FlowState,
        next_borrow_id: List[int],
    ) -> Tuple[FlowState, SemanticNode]:
        target_type, target_mode = ctx.lookup(
            self.target
        )

        expr_type = self.expr.check_type(ctx)

        if not ctx.is_assignable(
            expr_type,
            target_type,
        ):
            raise TypeError(
                "Type Boundary Error: Invalid type target "
                "assignment resolution sequence path."
            )

        new_flow = flow.clone()

        current_state = new_flow.ownership.get(
            self.target,
            OwnerState.UNINITIALIZED,
        )

        if current_state == OwnerState.OWNED:
            if target_mode == OwnershipMode.LINEAR:
                raise TypeError(
                    f"Resource Leak Hazard: Overwriting active "
                    f"linear storage pointer '{self.target}' "
                    f"before consumption."
                )

            if target_mode == OwnershipMode.AFFINE:
                new_flow.drops.append(
                    DropAction(
                        self.target,
                        target_type,
                    )
                )

        new_flow, sem_expr = self.expr.check_ownership(
            new_flow,
            ctx,
            next_borrow_id,
        )

        new_flow.ownership[
            self.target
        ] = OwnerState.OWNED

        return (
            new_flow,
            SemAssignStmt(
                self.target,
                sem_expr,
            ),
        )


@dataclass(frozen=True)
class ExprStmt(ASTNode):
    expr: ASTNode

    def check(
        self,
        ctx: SymbolContext,
        flow: FlowState,
        next_borrow_id: List[int],
    ) -> Tuple[FlowState, SemanticNode]:
        self.expr.check_type(ctx)

        new_flow, sem_expr = self.expr.check_ownership(
            flow.clone(),
            ctx,
            next_borrow_id,
        )

        return new_flow, SemExprStmt(sem_expr)


@dataclass(frozen=True)
class ReturnStmt(ASTNode):
    expr: Optional[ASTNode]

    def check(
        self,
        ctx: SymbolContext,
        flow: FlowState,
        next_borrow_id: List[int],
        current_contract: FunctionContract,
    ) -> Tuple[FlowState, SemanticNode]:
        new_flow = flow.clone()
        sem_expr = None

        if self.expr is not None:
            ret_type = self.expr.check_type(ctx)

            if current_contract.return_type is None:
                raise TypeError(
                    "Type Boundary Error: Function returns "
                    "a value but expected void."
                )

            if not ctx.is_assignable(
                ret_type,
                current_contract.return_type,
            ):
                raise TypeError(
                    f"Type Boundary Error: Expected return "
                    f"type {current_contract.return_type}, "
                    f"got {ret_type}."
                )

            ret_var_name = (
                self.expr.name
                if isinstance(
                    self.expr,
                    IdentifierExpr,
                )
                else None
            )

            new_flow, sem_expr = (
                self.expr.check_ownership(
                    new_flow,
                    ctx,
                    next_borrow_id,
                )
            )

            if (
                current_contract.return_mode
                != OwnershipMode.COPY
                and ret_var_name is not None
            ):
                new_flow.ownership[
                    ret_var_name
                ] = OwnerState.MOVED

        else:
            if current_contract.return_type is not None:
                raise TypeError(
                    f"Type Boundary Error: Function expected "
                    f"return type {current_contract.return_type}, "
                    f"got void."
                )

        deferred_return_drops: List[DropAction] = []

        for scope in reversed(ctx.scopes):
            for name, (ty, mode) in scope.items():
                if (
                    self.expr is not None
                    and isinstance(
                        self.expr,
                        IdentifierExpr,
                    )
                    and name == self.expr.name
                ):
                    continue

                state = new_flow.ownership.get(
                    name,
                    OwnerState.DEAD,
                )

                if (
                    mode == OwnershipMode.LINEAR
                    and state == OwnerState.OWNED
                ):
                    raise TypeError(
                        f"Contract Violation: Linear variable "
                        f"'{name}' is leaked upon returning."
                    )

                if (
                    mode == OwnershipMode.AFFINE
                    and state == OwnerState.OWNED
                ):
                    deferred_return_drops.append(
                        DropAction(name, ty)
                    )

        new_flow.has_returned = True

        return (
            new_flow,
            SemReturnStmt(
                sem_expr,
                tuple(deferred_return_drops),
            ),
        )


@dataclass(frozen=True)
class BlockStmt(ASTNode):
    statements: List[ASTNode]

    def check_with_contract(
        self,
        ctx: SymbolContext,
        flow: FlowState,
        next_borrow_id: List[int],
        current_contract: FunctionContract,
    ) -> Tuple[FlowState, SemBlockStmt]:
        ctx.enter_scope()

        local_flow = flow.clone()
        sem_statements = []

        for stmt in self.statements:
            if isinstance(stmt, ReturnStmt):
                local_flow, sem_stmt = stmt.check(
                    ctx,
                    local_flow,
                    next_borrow_id,
                    current_contract,
                )
            else:
                local_flow, sem_stmt = (
                    check_statement_with_contract(
                        stmt,
                        ctx,
                        local_flow,
                        next_borrow_id,
                        current_contract,
                    )
                )

            sem_statements.append(sem_stmt)

            if local_flow.has_returned:
                break

        local_bindings = ctx.get_current_scope_bindings()
        local_drops: List[DropAction] = []

        for name in local_bindings:
            ty, mode = ctx.lookup(name)

            state = local_flow.ownership.get(
                name,
                OwnerState.DEAD,
            )

            borrows = local_flow.active_borrows.get(
                name,
                set(),
            )

            if borrows:
                raise TypeError(
                    f"Scope Soundness Escape: Outstanding active "
                    f"borrows exist for local variable '{name}'."
                )

            if (
                mode == OwnershipMode.LINEAR
                and state == OwnerState.OWNED
                and not local_flow.has_returned
            ):
                raise TypeError(
                    f"Strict Ownership Invariant Leak: Linear "
                    f"resource '{name}' went out of scope while active."
                )

            if (
                mode == OwnershipMode.AFFINE
                and state == OwnerState.OWNED
                and not local_flow.has_returned
            ):
                local_drops.append(
                    DropAction(name, ty)
                )

            local_flow.ownership[name] = OwnerState.DEAD
            local_flow.ownership.pop(name, None)
            local_flow.active_borrows.pop(name, None)

        ctx.exit_scope()

        return (
            local_flow,
            SemBlockStmt(
                sem_statements,
                local_drops,
            ),
        )


@dataclass(frozen=True)
class BorrowBlockStmt(ASTNode):
    source: str
    borrow_alias: str
    body: BlockStmt

    def check_with_contract(
        self,
        ctx: SymbolContext,
        flow: FlowState,
        next_borrow_id: List[int],
        current_contract: FunctionContract,
    ) -> Tuple[FlowState, SemanticNode]:
        ty, mode = ctx.lookup(self.source)

        ctx.enter_scope()
        ctx.bind(
            self.borrow_alias,
            ty,
            OwnershipMode.COPY,
        )

        if mode == OwnershipMode.COPY:
            entry_flow = flow.clone()

            entry_flow.ownership[
                self.borrow_alias
            ] = OwnerState.OWNED

            entry_flow.active_borrows[
                self.borrow_alias
            ] = set()

            exit_flow, sem_body = (
                self.body.check_with_contract(
                    ctx,
                    entry_flow,
                    next_borrow_id,
                    current_contract,
                )
            )

            ctx.exit_scope()

            final_flow = exit_flow.clone()

            final_flow.ownership.pop(
                self.borrow_alias,
                None,
            )

            final_flow.active_borrows.pop(
                self.borrow_alias,
                None,
            )

            return (
                final_flow,
                SemBorrowBlockStmt(
                    self.source,
                    self.borrow_alias,
                    None,
                    sem_body,
                ),
            )

        if flow.ownership.get(
            self.source
        ) != OwnerState.OWNED:
            raise TypeError(
                f"Reference Hazard: Cannot open borrow handles "
                f"against a non-owned allocation pointer "
                f"'{self.source}'."
            )

        cap_id = next_borrow_id[0]
        next_borrow_id[0] += 1

        new_cap = BorrowCapability(
            cap_id,
            self.source,
            self.borrow_alias,
        )

        entry_flow = flow.clone()

        entry_flow.active_borrows.setdefault(
            self.source,
            set(),
        ).add(new_cap)

        entry_flow.ownership[
            self.borrow_alias
        ] = OwnerState.OWNED

        entry_flow.active_borrows[
            self.borrow_alias
        ] = set()

        exit_flow, sem_body = (
            self.body.check_with_contract(
                ctx,
                entry_flow,
                next_borrow_id,
                current_contract,
            )
        )

        alias_borrows = exit_flow.active_borrows.get(
            self.borrow_alias,
            set(),
        )

        if alias_borrows:
            raise TypeError(
                f"Borrow Soundness Violation: Escaping "
                f"sub-borrows exist on alias "
                f"'{self.borrow_alias}'."
            )

        exit_borrows = exit_flow.active_borrows.get(
            self.source,
            set(),
        )

        if new_cap not in exit_borrows:
            raise TypeError(
                f"Borrow Lifetime Violation for "
                f"'{self.source}': Capability target was "
                f"cleared out of scope prematurely."
            )

        ctx.exit_scope()

        final_flow = exit_flow.clone()

        final_flow.active_borrows[
            self.source
        ].remove(new_cap)

        final_flow.ownership.pop(
            self.borrow_alias,
            None,
        )

        final_flow.active_borrows.pop(
            self.borrow_alias,
            None,
        )

        return (
            final_flow,
            SemBorrowBlockStmt(
                self.source,
                self.borrow_alias,
                cap_id,
                sem_body,
            ),
        )


@dataclass(frozen=True)
class IfStmt(ASTNode):
    condition: ASTNode
    then_block: BlockStmt
    else_block: BlockStmt

    def check_with_contract(
        self,
        ctx: SymbolContext,
        flow: FlowState,
        next_borrow_id: List[int],
        current_contract: FunctionContract,
    ) -> Tuple[FlowState, SemanticNode]:
        if (
            self.condition.check_type(ctx)
            != PRIMITIVE_BOOLEAN
        ):
            raise TypeError(
                "Conditional Constraint Failure: If condition "
                "needs to evaluate as a BOOLEAN type."
            )

        base_flow, sem_cond = (
            self.condition.check_ownership(
                flow.clone(),
                ctx,
                next_borrow_id,
            )
        )

        then_entry_drops = len(base_flow.drops)

        then_flow, sem_then = (
            self.then_block.check_with_contract(
                ctx,
                base_flow.clone(),
                next_borrow_id,
                current_contract,
            )
        )

        then_branch_drops = (
            then_flow.drops[then_entry_drops:]
        )

        else_entry_drops = len(base_flow.drops)

        else_flow, sem_else = (
            self.else_block.check_with_contract(
                ctx,
                base_flow.clone(),
                next_borrow_id,
                current_contract,
            )
        )

        else_branch_drops = (
            else_flow.drops[else_entry_drops:]
        )

        if (
            then_flow.has_returned
            and else_flow.has_returned
        ):
            return (
                then_flow.clone(),
                SemIfStmt(
                    sem_cond,
                    sem_then,
                    sem_else,
                    then_branch_drops,
                    else_branch_drops,
                ),
            )

        if then_flow.has_returned:
            return (
                else_flow.clone(),
                SemIfStmt(
                    sem_cond,
                    sem_then,
                    sem_else,
                    then_branch_drops,
                    else_branch_drops,
                ),
            )

        if else_flow.has_returned:
            return (
                then_flow.clone(),
                SemIfStmt(
                    sem_cond,
                    sem_then,
                    sem_else,
                    then_branch_drops,
                    else_branch_drops,
                ),
            )

        all_keys = (
            set(then_flow.ownership.keys())
            | set(else_flow.ownership.keys())
        )

        joined_flow = FlowState()
        joined_flow.drops = list(base_flow.drops)

        for name in all_keys:
            _, mode = ctx.lookup(name)

            left_state = then_flow.ownership.get(
                name,
                OwnerState.DEAD,
            )

            right_state = else_flow.ownership.get(
                name,
                OwnerState.DEAD,
            )

            joined_flow.ownership[name] = (
                strict_lattice_join(
                    mode,
                    left_state,
                    right_state,
                )
            )

            left_borrows = (
                then_flow.active_borrows.get(
                    name,
                    set(),
                )
            )

            right_borrows = (
                else_flow.active_borrows.get(
                    name,
                    set(),
                )
            )

            joined_flow.active_borrows[name] = (
                join_borrows(
                    name,
                    left_borrows,
                    right_borrows,
                )
            )

        return (
            joined_flow,
            SemIfStmt(
                sem_cond,
                sem_then,
                sem_else,
                then_branch_drops,
                else_branch_drops,
            ),
        )


@dataclass(frozen=True)
class FunctionDecl(ASTNode):
    contract: FunctionContract
    body: BlockStmt

    def check_contract(
        self,
        ctx: SymbolContext,
        next_borrow_id: Optional[List[int]] = None,
    ) -> SemFunctionDecl:
        if next_borrow_id is None:
            next_borrow_id = [0]

        ctx.register_function(
            self.contract.name,
            self.contract,
        )

        ctx.enter_scope()

        initial_flow = FlowState()

        for param in self.contract.parameters:
            ctx.bind(
                param.name,
                param.type,
                param.mode,
            )

            initial_flow.ownership[
                param.name
            ] = OwnerState.OWNED

            initial_flow.active_borrows[
                param.name
            ] = set()

            if (
                param.borrowed
                and param.mode != OwnershipMode.COPY
            ):
                cap_id = next_borrow_id[0]
                next_borrow_id[0] += 1

                synthetic_alias = (
                    f"__arg_alias_{param.name}"
                )

                param_cap = BorrowCapability(
                    cap_id,
                    param.name,
                    synthetic_alias,
                )

                initial_flow.active_borrows[
                    param.name
                ].add(param_cap)

        final_flow, sem_body = (
            self.body.check_with_contract(
                ctx,
                initial_flow,
                next_borrow_id,
                self.contract,
            )
        )

        if (
            self.contract.return_type is not None
            and not final_flow.has_returned
        ):
            raise TypeError(
                f"Contract Failure: Function "
                f"'{self.contract.name}' missing terminating "
                f"ReturnStmt block."
            )

        for param in self.contract.parameters:
            _, mode = ctx.lookup(param.name)

            final_state = final_flow.ownership.get(
                param.name,
                OwnerState.DEAD,
            )

            final_borrows = (
                final_flow.active_borrows.get(
                    param.name,
                    set(),
                )
            )

            if (
                param.borrowed
                and param.mode != OwnershipMode.COPY
            ):
                if len(final_borrows) != 1:
                    raise TypeError(
                        f"Contract Violation: Reference borrow "
                        f"handle on parameter '{param.name}' "
                        f"escaped definition frame."
                    )

                if final_state != OwnerState.OWNED:
                    raise TypeError(
                        f"Contract Violation: Borrowed parameter "
                        f"'{param.name}' was modified or consumed."
                    )

            else:
                if final_borrows:
                    raise TypeError(
                        f"Contract Violation: Outstanding local "
                        f"borrows leak through parameter "
                        f"'{param.name}'."
                    )

                if mode == OwnershipMode.LINEAR:
                    if (
                        final_state == OwnerState.OWNED
                        and not final_flow.has_returned
                    ):
                        raise TypeError(
                            f"Contract Violation: Linear input "
                            f"parameter '{param.name}' was not consumed."
                        )

                elif mode == OwnershipMode.AFFINE:
                    if (
                        final_state == OwnerState.OWNED
                        and not final_flow.has_returned
                    ):
                        sem_body.local_drops.append(
                            DropAction(
                                param.name,
                                param.type,
                            )
                        )

        ctx.exit_scope()

        return SemFunctionDecl(
            self.contract,
            sem_body,
        )


def check_statement_with_contract(
    stmt: ASTNode,
    ctx: SymbolContext,
    flow: FlowState,
    next_borrow_id: List[int],
    current_contract: FunctionContract,
) -> Tuple[FlowState, SemanticNode]:
    if type(stmt).__name__ == "ReggeSimplexStmt": return stmt.check_with_contract(ctx, flow, next_borrow_id, current_contract)
    if type(stmt).__name__ == "MetricTensorFieldStmt": return stmt.check_with_contract(ctx, flow, next_borrow_id, current_contract)
    if type(stmt).__name__ == "BraidGeneratorStmt": return stmt.check_with_contract(ctx, flow, next_borrow_id, current_contract)
    if type(stmt).__name__ == "BioSynthesisPayloadStmt": return stmt.check_with_contract(ctx, flow, next_borrow_id, current_contract)
    if type(stmt).__name__ == "QuantumSymmetricLoopStmt": return stmt.check_with_contract(ctx, flow, next_borrow_id, current_contract)
    if type(stmt).__name__ == "SimdVectorOpStmt": return stmt.check_with_contract(ctx, flow, next_borrow_id, current_contract)
    if type(stmt).__name__ == "BorrowStmt": return stmt.check_with_contract(ctx, flow, next_borrow_id, current_contract)
    if type(stmt).__name__ == "ReggeSimplexStmt": return stmt.check_with_contract(ctx, flow, next_borrow_id, current_contract)
    if type(stmt).__name__ == "MetricTensorFieldStmt": return stmt.check_with_contract(ctx, flow, next_borrow_id, current_contract)
    if type(stmt).__name__ == "BraidGeneratorStmt": return stmt.check_with_contract(ctx, flow, next_borrow_id, current_contract)
    if type(stmt).__name__ == "BioSynthesisPayloadStmt": return stmt.check_with_contract(ctx, flow, next_borrow_id, current_contract)
    if type(stmt).__name__ == "QuantumSymmetricLoopStmt": return stmt.check_with_contract(ctx, flow, next_borrow_id, current_contract)
    if type(stmt).__name__ == "SimdVectorOpStmt": return stmt.check_with_contract(ctx, flow, next_borrow_id, current_contract)
    if type(stmt).__name__ == "BorrowStmt": return stmt.check_with_contract(ctx, flow, next_borrow_id, current_contract)
    if type(stmt).__name__ == "BorrowStmt":
        return stmt.check_with_contract(ctx, flow, next_borrow_id, current_contract)
    if isinstance(stmt, LetStmt):
        return stmt.check(
            ctx,
            flow,
            next_borrow_id,
        )

    if isinstance(stmt, AssignStmt):
        return stmt.check(
            ctx,
            flow,
            next_borrow_id,
        )

    if isinstance(stmt, MoveStmt):
        return stmt.check(
            ctx,
            flow,
            next_borrow_id,
        )

    if isinstance(stmt, ExprStmt):
        return stmt.check(
            ctx,
            flow,
            next_borrow_id,
        )

    if isinstance(stmt, BlockStmt):
        return stmt.check_with_contract(
            ctx,
            flow,
            next_borrow_id,
            current_contract,
        )

    if isinstance(stmt, BorrowBlockStmt):
        return stmt.check_with_contract(
            ctx,
            flow,
            next_borrow_id,
            current_contract,
        )

    if isinstance(stmt, IfStmt):
        return stmt.check_with_contract(
            ctx,
            flow,
            next_borrow_id,
            current_contract,
        )

    raise TypeError(
        "Unidentified AST structure node tracking vector: "
        f"{type(stmt).__name__}"
    )
class PtrAllocaExpr(ASTNode):
    def __init__(self, target_type, span=None):
        super().__init__(span)
        self.target_type = target_type

class PtrLoadExpr(ASTNode):
    def __init__(self, pointer_expr, span=None):
        super().__init__(span)
        self.pointer_expr = pointer_expr

class PtrStoreStmt(ASTNode):
    def __init__(self, pointer_expr, value_expr, span=None):
        super().__init__(span)
        self.pointer_expr = pointer_expr
        self.value_expr = value_expr
class PtrOffsetExpr(ASTNode):
    def __init__(self, base_ptr_expr, offset_expr, span=None):
        self.base_ptr_expr = base_ptr_expr
        self.offset_expr = offset_expr
        self.span = span

    @property
    def base_expr(self):
        return self.base_ptr_expr

    @base_expr.setter
    def base_expr(self, val):
        self.base_ptr_expr = val

    @property
    def base_ptr(self):
        return self.base_ptr_expr

    @base_ptr.setter
    def base_ptr(self, val):
        self.base_ptr_expr = val

    def check_type(self, ctx):
        from linum.semantic.types import PRIMITIVE_INTEGER

        base_type = self.base_ptr_expr.check_type(ctx)
        offset_type = self.offset_expr.check_type(ctx)

        if base_type.name != "ptr":
            raise TypeError(
                f"Pointer arithmetic requires ptr base, got {base_type}."
            )

        if offset_type != PRIMITIVE_INTEGER:
            raise TypeError(
                f"Pointer arithmetic requires INTEGER offset, got {offset_type}."
            )

        return base_type

    def check_ownership(self, flow, ctx, next_borrow_id):
        from linum.semantic.analyzer import SemPtrOffsetExpr
        flow, sem_base = self.base_ptr_expr.check_ownership(flow, ctx, next_borrow_id)
        flow, sem_offset = self.offset_expr.check_ownership(flow, ctx, next_borrow_id)
        base_type = self.check_type(ctx)
        try:
            sem_node = SemPtrOffsetExpr(base_ptr=sem_base, offset=sem_offset, type=base_type)
        except TypeError:
            try:
                sem_node = SemPtrOffsetExpr(base_ptr=sem_base, offset=sem_offset)
            except TypeError:
                sem_node = SemPtrOffsetExpr(sem_base, sem_offset)
        return flow, sem_node

    def check(self, ctx):
        return self.check_type(ctx)
class StructDecl(ASTNode):
    def __init__(self, name: str, fields: Dict[str, Type], span=None):
        self.name = name
        self.fields = fields
        self.span = span

    def check(self, ctx):
        from linum.semantic.types import StructType
        st = StructType(self.name, self.fields)
        ctx.bind(self.name, st, st.mode)
        return st


class FieldAccessExpr(ASTNode):
    def __init__(self, target_expr: ASTNode, field_name: str, span=None):
        self.target_expr = target_expr
        self.field_name = field_name
        self.span = span

    def check_type(self, ctx):
        target_ty = self.target_expr.check_type(ctx)
        if hasattr(target_ty, "get_field_type"):
            return target_ty.get_field_type(self.field_name)
        raise TypeError(f"Target '{target_ty!r}' is not a struct type and does not contain field '{self.field_name}'")

    def check_ownership(self, flow, ctx, next_borrow_id):
        from linum.semantic.analyzer import SemFieldAccessExpr
        flow, sem_target = self.target_expr.check_ownership(flow, ctx, next_borrow_id)
        field_ty = self.check_type(ctx)
        return flow, SemFieldAccessExpr(target=sem_target, field_name=self.field_name, type=field_ty)

    def check(self, ctx):
        return self.check_type(ctx)


class SimdVectorOpStmt(ASTNode):
    def __init__(self, op: str, dest_ptr: ASTNode, src1_ptr: ASTNode, src2_ptr: ASTNode, width: int = 4, elem_type: str = "i32", span=None):
        super().__init__(span)
        self.op = op
        self.dest_ptr = dest_ptr
        self.src1_ptr = src1_ptr
        self.src2_ptr = src2_ptr
        self.width = width
        self.elem_type = elem_type

    def check_type(self, ctx):
        return None

    def check_ownership(self, flow, ctx, next_borrow_id):
        from linum.semantic.analyzer import SemSimdVectorOp
        flow, s_dest = self.dest_ptr.check_ownership(flow, ctx, next_borrow_id)
        flow, s_src1 = self.src1_ptr.check_ownership(flow, ctx, next_borrow_id)
        flow, s_src2 = self.src2_ptr.check_ownership(flow, ctx, next_borrow_id)
        return flow, SemSimdVectorOp(op=self.op, dest_ptr=s_dest, src1_ptr=s_src1, src2_ptr=s_src2, width=self.width, elem_type=self.elem_type)

    def check(self, ctx):
        return None
