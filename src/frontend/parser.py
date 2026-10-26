"""Stage 0 R2 Recursive-Descent Parser."""

from typing import List, Optional
from src.frontend.lexer import Token, TokenType
from src.ast.nodes import (
    TypeRef, Expression, IntLiteral, ByteLiteral, BoolLiteral, Identifier,
    BinaryOp, UnaryOp, CastExpr, CallExpr, IndexExpr, FieldExpr,
    UnsafeExpr, DerefExpr, TupleExpr, ArrayRepeatExpr,
    Statement, LetStmt, AssignStmt, WhileStmt, IfStmt, ReturnStmt,
    Contract, FunctionDecl, StructDecl, StructField, Module,
    TupleLetStmt,
    StructFieldInit, StructInitExpr, IfExpr,
)


class Parser:
    def __init__(self, tokens: List[Token]):
        self.tokens = tokens
        self.pos = 0

    def _peek(self, offset: int = 0) -> Token:
        idx = self.pos + offset
        return self.tokens[idx] if idx < len(self.tokens) else self.tokens[-1]

    def _peek_ahead(self, offset: int = 1):
        idx = self.pos + offset
        if idx < len(self.tokens):
            return self.tokens[idx]
        return self.tokens[-1]

    def _match(self, *types: TokenType) -> bool:
        if self._peek().type in types:
            self.pos += 1
            return True
        return False

    def _expect(self, token_type: TokenType) -> Token:
        t = self._peek()
        if t.type != token_type:
            raise SyntaxError(f"Expected {token_type.name} at line {t.line}:{t.col}, got {t.type.name} ({t.value})")
        self.pos += 1
        return t

    def parse_module(self) -> Module:
        mod_name = "main"
        if self._match(TokenType.MODULE):
            parts = [self._expect(TokenType.IDENT).value]
            while self._match(TokenType.DOT):
                parts.append(self._expect(TokenType.IDENT).value)
            self._expect(TokenType.SEMICOLON)
            mod_name = ".".join(parts)

        decls = []
        while self._peek().type != TokenType.EOF:
            # Skip top-level attributes #[packed, repr(C)]
            if self._peek().type == TokenType.ATTR:
                self.pos += 1
                self._expect(TokenType.LBRACKET)
                while self._peek().type not in (TokenType.RBRACKET, TokenType.EOF):
                    self.pos += 1
                self._expect(TokenType.RBRACKET)

            tok = self._peek()
            if tok.type == TokenType.FN:
                decls.append(self._parse_function())
            elif tok.type == TokenType.STRUCT:
                decls.append(self._parse_struct())
            elif tok.type in (TokenType.CONST, TokenType.ENUM):
                # Consume declarations to next closing brace or semicolon
                self._skip_to_stmt_end()
            else:
                self.pos += 1

        return Module(name=mod_name, declarations=decls)

    def _skip_to_stmt_end(self):
        depth = 0
        while self._peek().type != TokenType.EOF:
            if self._peek().type == TokenType.LBRACE:
                depth += 1
            elif self._peek().type == TokenType.RBRACE:
                depth -= 1
                if depth == 0:
                    self.pos += 1
                    return
            elif self._peek().type == TokenType.SEMICOLON and depth == 0:
                self.pos += 1
                return
            self.pos += 1

    def _parse_type(self) -> TypeRef:
        # Check domain types: ram<T>, mmio<T>, ioport<T>, cap<T>
        if self._peek().type in (TokenType.RAM, TokenType.MMIO, TokenType.IOPORT, TokenType.CAP):
            domain = self._peek().value.lower()
            self.pos += 1
            self._expect(TokenType.LANGLE)
            inner = self._parse_type()
            self._expect(TokenType.RANGLE)
            return TypeRef(name=inner.name, domain=domain)

        # Array [T; N]
        if self._match(TokenType.LBRACKET):
            elem = self._parse_type()
            self._expect(TokenType.SEMICOLON)
            sz_tok = self._expect(TokenType.INT_LIT)
            self._expect(TokenType.RBRACKET)
            return TypeRef(name=elem.name, is_array=True, array_size=sz_tok.value)

        tok = self._expect(TokenType.IDENT)
        name = tok.value
        while self._match(TokenType.DCOLON):
            name = f"{name}::{self._expect(TokenType.IDENT).value}"
        return TypeRef(name=name)

    def _parse_struct(self) -> StructDecl:
        self._expect(TokenType.STRUCT)
        name = self._expect(TokenType.IDENT).value
        self._expect(TokenType.LBRACE)
        fields = []
        while self._peek().type not in (TokenType.RBRACE, TokenType.EOF):
            f_name = self._expect(TokenType.IDENT).value
            self._expect(TokenType.COLON)
            t_ref = self._parse_type()
            self._expect(TokenType.COMMA)
            fields.append(StructField(name=f_name, type_ref=t_ref))
        self._expect(TokenType.RBRACE)
        return StructDecl(name=name, fields=fields)

    def _parse_function(self) -> FunctionDecl:
        self._expect(TokenType.FN)
        name = self._expect(TokenType.IDENT).value
        self._expect(TokenType.LPAREN)
        params = []
        while self._peek().type not in (TokenType.RPAREN, TokenType.EOF):
            p_name = self._expect(TokenType.IDENT).value
            self._expect(TokenType.COLON)
            p_type = self._parse_type()
            params.append((p_name, p_type))
            if not self._match(TokenType.COMMA):
                break
        self._expect(TokenType.RPAREN)

        ret_type = None
        if self._match(TokenType.ARROW):
            # Check for tuple or single return type
            if self._match(TokenType.LPAREN):
                self._parse_type()
                while self._match(TokenType.COMMA):
                    self._parse_type()
                self._expect(TokenType.RPAREN)
                ret_type = TypeRef(name="tuple")
            else:
                ret_type = self._parse_type()

        # Parse Contracts (pre:, post:, preserves:)
        contracts = []
        while self._peek().type in (TokenType.PRE, TokenType.POST, TokenType.PRESERVES):
            kind_tok = self._peek()
            self.pos += 1
            self._expect(TokenType.COLON)
            # Consume contract expression up to next contract or {
            expr_tokens = []
            while self._peek().type not in (TokenType.PRE, TokenType.POST, TokenType.PRESERVES, TokenType.LBRACE, TokenType.EOF):
                expr_tokens.append(self._peek().value)
                self.pos += 1
            contracts.append(Contract(kind=kind_tok.value, expr=" ".join(str(v) for v in expr_tokens)))

        # Parse body
        body = []
        self._expect(TokenType.LBRACE)
        while self._peek().type not in (TokenType.RBRACE, TokenType.EOF):
            stmt = self._parse_statement()
            if stmt:
                body.append(stmt)
        self._expect(TokenType.RBRACE)

        return FunctionDecl(name=name, params=params, return_type=ret_type, contracts=contracts, body=body)

    def _parse_statement(self) -> Optional[Statement]:
        tok = self._peek()

        if self._match(TokenType.LET) or self._match(TokenType.VAR):
            is_var = (tok.type == TokenType.VAR)

            if self._match(TokenType.LPAREN):
                names = [self._expect(TokenType.IDENT).value]
                while self._match(TokenType.COMMA):
                    names.append(self._expect(TokenType.IDENT).value)
                self._expect(TokenType.RPAREN)
                self._expect(TokenType.ASSIGN)
                init_expr = self._parse_expr()
                self._expect(TokenType.SEMICOLON)
                return TupleLetStmt(
                    names=names,
                    init=init_expr,
                    is_var=is_var,
                )

            name = self._expect(TokenType.IDENT).value
            t_ref = None
            if self._match(TokenType.COLON):
                t_ref = self._parse_type()
            self._expect(TokenType.ASSIGN)
            init_expr = self._parse_expr()
            self._expect(TokenType.SEMICOLON)
            return LetStmt(
                name=name,
                type_ref=t_ref,
                init=init_expr,
                is_var=is_var,
            )

        if self._match(TokenType.WHILE):
            cond = self._parse_expr()
            self._expect(TokenType.LBRACE)
            body = []
            while self._peek().type not in (TokenType.RBRACE, TokenType.EOF):
                s = self._parse_statement()
                if s: body.append(s)
            self._expect(TokenType.RBRACE)
            return WhileStmt(cond=cond, body=body)

        if self._match(TokenType.IF):
            cond = self._parse_expr()
            self._expect(TokenType.LBRACE)
            then_b = []
            while self._peek().type not in (TokenType.RBRACE, TokenType.EOF):
                s = self._parse_statement()
                if s: then_b.append(s)
            self._expect(TokenType.RBRACE)
            else_b = None
            if self._match(TokenType.ELSE):
                self._expect(TokenType.LBRACE)
                else_b = []
                while self._peek().type not in (TokenType.RBRACE, TokenType.EOF):
                    s = self._parse_statement()
                    if s: else_b.append(s)
                self._expect(TokenType.RBRACE)
            return IfStmt(cond=cond, then_branch=then_b, else_branch=else_b)

        if self._match(TokenType.RETURN):
            expr = None
            if self._peek().type != TokenType.SEMICOLON:
                expr = self._parse_expr()
            self._expect(TokenType.SEMICOLON)
            return ReturnStmt(expr=expr)

        # Expression statement or assignment
        expr = self._parse_expr()
        if self._match(TokenType.ASSIGN):
            val = self._parse_expr()
            self._expect(TokenType.SEMICOLON)
            return AssignStmt(target=expr, value=val)

        self._match(TokenType.SEMICOLON)
        return None

    def _parse_expr(self) -> Expression:
        return self._parse_relational()

    def _parse_relational(self) -> Expression:
        expr = self._parse_additive()
        while self._peek().type in (TokenType.EQ, TokenType.NEQ, TokenType.LE, TokenType.GE, TokenType.LANGLE, TokenType.RANGLE):
            op = self._peek().value
            self.pos += 1
            right = self._parse_additive()
            expr = BinaryOp(left=expr, op=op, right=right)
        return expr

    def _parse_additive(self) -> Expression:
        expr = self._parse_bitwise()
        while self._peek().type in (TokenType.ADD, TokenType.SUB):
            op = self._peek().value
            self.pos += 1
            right = self._parse_bitwise()
            expr = BinaryOp(left=expr, op=op, right=right)
        return expr

    def _parse_bitwise(self) -> Expression:
        expr = self._parse_multiplicative()
        while self._peek().type in (TokenType.BIT_OR, TokenType.BIT_AND, TokenType.BIT_XOR, TokenType.SHL, TokenType.SHR):
            op = self._peek().value
            self.pos += 1
            right = self._parse_multiplicative()
            expr = BinaryOp(left=expr, op=op, right=right)
        return expr

    def _parse_multiplicative(self) -> Expression:
        expr = self._parse_unary()
        while self._peek().type == TokenType.STAR:
            op = self._peek().value
            self.pos += 1
            right = self._parse_unary()
            expr = BinaryOp(left=expr, op=op, right=right)
        return expr

    def _parse_unary(self) -> Expression:
        if self._match(TokenType.UNSAFE):
            self._expect(TokenType.LBRACE)
            expr = self._parse_expr()
            self._expect(TokenType.RBRACE)
            return UnsafeExpr(expr=expr)

        if self._match(TokenType.BIT_AND):
            return UnaryOp(op="&", expr=self._parse_unary())

        if self._match(
            TokenType.BIT_NOT, TokenType.NOT, TokenType.SUB
        ):
            op = self.tokens[self.pos - 1].value
            return UnaryOp(op=op, expr=self._parse_unary())

        if self._match(TokenType.STAR):
            return DerefExpr(expr=self._parse_unary())

        return self._parse_postfix()

    def _parse_postfix(self) -> Expression:
        expr = self._parse_primary()
        while True:
            if self._match(TokenType.LBRACKET):
                idx = self._parse_expr()
                self._expect(TokenType.RBRACKET)
                expr = IndexExpr(target=expr, index=idx)
            elif self._match(TokenType.LPAREN):
                args = []
                while self._peek().type not in (TokenType.RPAREN, TokenType.EOF):
                    args.append(self._parse_expr())
                    if not self._match(TokenType.COMMA):
                        break
                self._expect(TokenType.RPAREN)
                expr = CallExpr(callee=expr, args=args)
            elif self._match(TokenType.DOT):
                f_name = self._expect(TokenType.IDENT).value
                expr = FieldExpr(target=expr, field=f_name)
            elif self._match(TokenType.AS):
                target_type = self._parse_type()
                expr = CastExpr(expr=expr, target_type=target_type)
            else:
                break
        return expr

    def _parse_primary(self) -> Expression:
        if self._match(TokenType.IF):
            cond = self._parse_expr()
            self._expect(TokenType.LBRACE)
            then_body = []
            while not self._match(TokenType.RBRACE):
                if self._peek().type == TokenType.EOF:
                    raise SyntaxError(f"Unterminated block in if-expression at {self._peek().line}:{self._peek().col}")
                if self._peek().type in (TokenType.LET, TokenType.RETURN, TokenType.WHILE):
                    then_body.append(self._parse_statement())
                else:
                    expr_item = self._parse_expr()
                    self._match(TokenType.SEMICOLON)
                    then_body.append(expr_item)
            else_body = None
            if self._match(TokenType.ELSE):
                if self._peek().type == TokenType.IF:
                    else_body = [self._parse_primary()]
                else:
                    self._expect(TokenType.LBRACE)
                    else_body = []
                    while not self._match(TokenType.RBRACE):
                        if self._peek().type == TokenType.EOF:
                            raise SyntaxError(f"Unterminated else block in if-expression at {self._peek().line}:{self._peek().col}")
                        if self._peek().type in (TokenType.LET, TokenType.RETURN, TokenType.WHILE):
                            else_body.append(self._parse_statement())
                        else:
                            expr_item = self._parse_expr()
                            self._match(TokenType.SEMICOLON)
                            else_body.append(expr_item)
            return IfExpr(cond=cond, then_branch=then_body, else_branch=else_body)

        tok = self._peek()
        if self._match(TokenType.INT_LIT):
            return IntLiteral(value=tok.value)
        elif self._match(TokenType.BYTE_LIT):
            return ByteLiteral(value=tok.value)
        elif self._match(TokenType.BOOL_LIT):
            return BoolLiteral(value=tok.value)
        elif self._match(TokenType.IDENT):
            name = tok.value
            while self._match(TokenType.DCOLON):
                name = f"{name}::{self._expect(TokenType.IDENT).value}"

            is_struct = False
            if self._peek().type == TokenType.LBRACE:
                t1 = self._peek_ahead(1)
                t2 = self._peek_ahead(2)
                if t1.type == TokenType.RBRACE or (t1.type == TokenType.IDENT and t2.type == TokenType.COLON):
                    is_struct = True

            if is_struct and self._match(TokenType.LBRACE):
                fields = []
                while self._peek().type not in (TokenType.RBRACE, TokenType.EOF):
                    f_name = self._expect(TokenType.IDENT).value
                    self._expect(TokenType.COLON)
                    f_val = self._parse_expr()
                    fields.append(StructFieldInit(name=f_name, value=f_val))
                    if not self._match(TokenType.COMMA):
                        break
                self._expect(TokenType.RBRACE)
                return StructInitExpr(struct_name=name, fields=fields)
            else:
                return Identifier(name=name)
        elif self._match(TokenType.LPAREN):
            # Empty tuple ()
            if self._match(TokenType.RPAREN):
                return TupleExpr(elements=[]) if "TupleExpr" else None
            first_expr = self._parse_expr()
            if self._match(TokenType.COMMA):
                elements = [first_expr]
                while not self._match(TokenType.RPAREN):
                    elements.append(self._parse_expr())
                    if not self._match(TokenType.COMMA):
                        self._expect(TokenType.RPAREN)
                        break
                return TupleExpr(elements=elements)
            self._expect(TokenType.RPAREN)
            return first_expr
        elif self._match(TokenType.LBRACKET):
            elements = []
            while self._peek().type not in (TokenType.RBRACKET, TokenType.EOF):
                elem = self._parse_expr()
                if self._match(TokenType.SEMICOLON):
                    count_expr = self._parse_expr()
                    self._expect(TokenType.RBRACKET)
                    return ArrayRepeatExpr(value=elem, count=count_expr)
                elements.append(elem)
                if not self._match(TokenType.COMMA):
                    break
            self._expect(TokenType.RBRACKET)
            return ArrayLiteral(elements=elements)
        else:
            raise SyntaxError(
                f"Expected expression at line {tok.line}:{tok.col}, got {tok.type.name} ({tok.value})"
            )