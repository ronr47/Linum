"""Stage 0 R2 Recursive-Descent Parser."""

from typing import List, Optional
from src.frontend.lexer import Token, TokenType
from src.ast.nodes import (
    TypeRef, Expression, IntLiteral, ByteLiteral, BoolLiteral, Identifier,
    BinaryOp, UnaryOp, CastExpr, CallExpr, IndexExpr, FieldExpr,
    Statement, LetStmt, AssignStmt, WhileStmt, IfStmt, ReturnStmt,
    Contract, FunctionDecl, StructDecl, StructField, Module
)


class Parser:
    def __init__(self, tokens: List[Token]):
        self.tokens = tokens
        self.pos = 0

    def _peek(self, offset: int = 0) -> Token:
        idx = self.pos + offset
        return self.tokens[idx] if idx < len(self.tokens) else self.tokens[-1]

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
            parts = []
            while True:
                parts.append(self._expect(TokenType.IDENT).value)
                if self._match(TokenType.IDENT): # handle dot separated if tokenized
                    continue
                # Check for module separator
                if self._peek().value == ".":
                    self.pos += 1
                    continue
                break
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
        return TypeRef(name=tok.value)

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
            name = self._expect(TokenType.IDENT).value
            t_ref = None
            if self._match(TokenType.COLON):
                t_ref = self._parse_type()
            self._expect(TokenType.ASSIGN)
            init_expr = self._parse_expr()
            self._expect(TokenType.SEMICOLON)
            return LetStmt(name=name, type_ref=t_ref, init=init_expr, is_var=is_var)

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
        expr = self._parse_unary()
        while self._peek().type in (TokenType.BIT_OR, TokenType.BIT_AND, TokenType.BIT_XOR, TokenType.SHL, TokenType.SHR):
            op = self._peek().value
            self.pos += 1
            right = self._parse_unary()
            expr = BinaryOp(left=expr, op=op, right=right)
        return expr

    def _parse_unary(self) -> Expression:
        if self._peek().type in (TokenType.BIT_NOT, TokenType.NOT, TokenType.SUB):
            op = self._peek().value
            self.pos += 1
            return UnaryOp(op=op, expr=self._parse_unary())
        return self._parse_primary()

    def _parse_primary(self) -> Expression:
        tok = self._peek()

        if self._match(TokenType.INT_LIT):
            return IntLiteral(value=tok.value)
        if self._match(TokenType.BYTE_LIT):
            return ByteLiteral(value=tok.value)
        if self._match(TokenType.BOOL_LIT):
            return BoolLiteral(value=tok.value)

        if self._match(TokenType.IDENT):
            name = tok.value
            if self._match(TokenType.LPAREN):
                args = []
                while self._peek().type not in (TokenType.RPAREN, TokenType.EOF):
                    args.append(self._parse_expr())
                    if not self._match(TokenType.COMMA):
                        break
                self._expect(TokenType.RPAREN)
                return CallExpr(callee=name, args=args)
            return Identifier(name=name)

        if self._match(TokenType.LPAREN):
            e = self._parse_expr()
            self._expect(TokenType.RPAREN)
            return e

        # Fallback for unparsed expressions
        self.pos += 1
        return Identifier(name=f"/* raw:{tok.value} */")
