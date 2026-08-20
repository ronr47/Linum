#!/usr/bin/env bash
set -e

PY_BIN="$( [ -f "./.venv/bin/python" ] && echo "./.venv/bin/python" || echo "$(which python3)" )"
export PYTHONPATH=".:$PYTHONPATH"

cat <<'EOF' > src/frontend/lexer.py
import re
from enum import Enum, auto
from typing import List, Optional
from linum.diagnostics import SourceSpan

class TokenType(Enum):
    LET = auto()
    IF = auto()
    ELSE = auto()
    RETURN = auto()
    BORROW = auto()
    AS = auto()
    MOVE = auto()
    
    IDENTIFIER = auto()
    REG = auto()
    
    ASSIGN = auto()
    LBRACE = auto()
    RBRACE = auto()
    COLON = auto()
    SEMICOLON = auto()
    COMMA = auto()
    
    PLUS = auto()
    MINUS = auto()
    
    STAR = auto()
    EOF = auto()

class Token:
    def __init__(self, type: TokenType, value: str, span: SourceSpan):
        self.type = type
        self.value = value
        self.span = span

    def __repr__(self):
        return f"Token({self.type}, {self.value!r}, {self.span})"

class Lexer:
    RULES = [
        (TokenType.LET, r'\blet\b'),
        (TokenType.IF, r'\bif\b'),
        (TokenType.ELSE, r'\belse\b'),
        (TokenType.RETURN, r'\breturn\b'),
        (TokenType.BORROW, r'\bborrow\b'),
        (TokenType.AS, r'\bas\b'),
        (TokenType.MOVE, r'\bmove\b'),
        
        (TokenType.REG, r'%[a-zA-Z_0-9]+'),
        (TokenType.IDENTIFIER, r'[a-zA-Z_][a-zA-Z_0-9]*'),
        
        (TokenType.PLUS, r'\+'),
        (TokenType.MINUS, r'-'),
        
        (TokenType.ASSIGN, r'='),
        (TokenType.LBRACE, r'\{'),
        (TokenType.RBRACE, r'\}'),
        (TokenType.COLON, r':'),
        (TokenType.SEMICOLON, r';'),
        (TokenType.COMMA, r','),
        (TokenType.STAR, r'\*'),
    ]

    def __init__(self, source: str):
        self.source = source
        self.length = len(source)
        self.pos = 0
        self.line = 1
        self.col = 1

    def tokenize(self) -> List[Token]:
        tokens: List[Token] = []
        while self.pos < self.length:
            # Skip whitespace
            m = re.match(r'[ \t\r\n]+', self.source[self.pos:])
            if m:
                text = m.group(0)
                newlines = text.count('\n')
                if newlines > 0:
                    self.line += newlines
                    self.col = len(text.rsplit('\n', 1)[1]) + 1
                else:
                    self.col += len(text)
                self.pos += len(text)
                continue

            # Skip comments
            if self.source[self.pos:].startswith('//'):
                newline_pos = self.source.find('\n', self.pos)
                if newline_pos == -1:
                    break
                self.pos = newline_pos + 1
                self.line += 1
                self.col = 1
                continue

            matched = False
            for tok_type, pattern in self.RULES:
                m = re.match(pattern, self.source[self.pos:])
                if m:
                    val = m.group(0)
                    span = SourceSpan(self.line, self.col, len(val))
                    tokens.append(Token(tok_type, val, span))
                    self.pos += len(val)
                    self.col += len(val)
                    matched = True
                    break

            if not matched:
                raise SyntaxError(
                    f"Lexer Error: Unexpected character '{self.source[self.pos]}' at line {self.line}, col {self.col}"
                )

        tokens.append(Token(TokenType.EOF, "", SourceSpan(self.line, self.col, 0)))
        return tokens
EOF

cat <<'EOF' > src/frontend/parser.py
from typing import List, Optional
from linum.frontend.lexer import Token, TokenType
from linum.ast.nodes import (
    ASTNode, BlockStmt, LetStmt, AssignStmt, MoveStmt, IfStmt,
    ReturnStmt, BorrowBlockStmt, ExprStmt, IdentifierExpr, PtrOffsetExpr
)
from linum.semantic.types import Type, OwnershipMode, PRIMITIVE_INTEGER, PRIMITIVE_BOOLEAN

class Parser:
    def __init__(self, tokens: List[Token]):
        self.tokens = tokens
        self.pos = 0

    def peek(self) -> Token:
        if self.pos < len(self.tokens):
            return self.tokens[self.pos]
        return self.tokens[-1]

    def consume(self, expected_type: Optional[TokenType] = None) -> Token:
        tok = self.peek()
        if expected_type and tok.type != expected_type:
            raise SyntaxError(
                f"Parser Error: Expected token {expected_type}, got {tok.type} ('{tok.value}') at {tok.span}"
            )
        self.pos += 1
        return tok

    def parse_type(self) -> Type:
        tok = self.peek()
        if tok.type == TokenType.IDENTIFIER:
            val = tok.value
            self.consume(TokenType.IDENTIFIER)
            if val == "INTEGER":
                return PRIMITIVE_INTEGER
            elif val == "BOOLEAN":
                return PRIMITIVE_BOOLEAN
            elif val == "ptr":
                return Type("ptr", OwnershipMode.COPY)
            elif val == "COPY":
                return PRIMITIVE_INTEGER
            elif val in ("LINEAR", "LINEAR_RES"):
                return Type("LINEAR_RES", OwnershipMode.LINEAR)
            elif val in ("AFFINE", "AFFINE_RES"):
                return Type("AFFINE_RES", OwnershipMode.AFFINE)
            return Type(val, OwnershipMode.COPY)
        raise SyntaxError(f"Parser Error: Invalid type specification parsing token {tok.type}")

    def parse_expression(self) -> ASTNode:
        tok = self.peek()
        if tok.type == TokenType.REG:
            base_tok = self.consume(TokenType.REG)
            expr = IdentifierExpr(base_tok.value, span=base_tok.span)
        elif tok.type == TokenType.IDENTIFIER:
            base_tok = self.consume(TokenType.IDENTIFIER)
            expr = IdentifierExpr(base_tok.value, span=base_tok.span)
        else:
            raise SyntaxError(f"Parser Error: Unexpected token in expression: {tok.type}")

        # Check for binary pointer/arithmetic offset: expr + offset or expr - offset
        if self.peek().type in (TokenType.PLUS, TokenType.MINUS):
            op_tok = self.consume()
            right_tok = self.peek()
            if right_tok.type == TokenType.REG:
                r_expr = IdentifierExpr(self.consume(TokenType.REG).value, span=right_tok.span)
            elif right_tok.type == TokenType.IDENTIFIER:
                r_expr = IdentifierExpr(self.consume(TokenType.IDENTIFIER).value, span=right_tok.span)
            else:
                raise SyntaxError(f"Parser Error: Expected operand after '{op_tok.value}'")
            return PtrOffsetExpr(expr, r_expr, span=base_tok.span)

        return expr

    def parse_statement(self) -> ASTNode:
        tok = self.peek()

        if tok.type == TokenType.LET:
            self.consume(TokenType.LET)
            name_tok = self.consume(TokenType.IDENTIFIER)
            self.consume(TokenType.COLON)
            annot_type = self.parse_type()
            self.consume(TokenType.ASSIGN)
            expr = self.parse_expression()
            self.consume(TokenType.SEMICOLON)
            return LetStmt(name=name_tok.value, annotation=annot_type, expr=expr, span=name_tok.span)

        elif tok.type == TokenType.IF:
            self.consume(TokenType.IF)
            cond_expr = self.parse_expression()
            then_block = self.parse_block()
            else_block = None
            if self.peek().type == TokenType.ELSE:
                self.consume(TokenType.ELSE)
                else_block = self.parse_block()
            return IfStmt(condition=cond_expr, then_block=then_block, else_block=else_block, span=tok.span)

        elif tok.type == TokenType.RETURN:
            self.consume(TokenType.RETURN)
            ret_expr = None
            if self.peek().type != TokenType.SEMICOLON:
                ret_expr = self.parse_expression()
            self.consume(TokenType.SEMICOLON)
            return ReturnStmt(expr=ret_expr, span=tok.span)

        elif tok.type == TokenType.BORROW:
            self.consume(TokenType.BORROW)
            var_tok = self.consume(TokenType.IDENTIFIER)
            self.consume(TokenType.AS)
            alias_tok = self.consume(TokenType.IDENTIFIER)
            body = self.parse_block()
            return BorrowBlockStmt(var_name=var_tok.value, alias=alias_tok.value, body=body, span=var_tok.span)

        elif tok.type == TokenType.MOVE:
            self.consume(TokenType.MOVE)
            dest_tok = self.consume(TokenType.IDENTIFIER)
            self.consume(TokenType.ASSIGN)
            src_tok = self.consume(TokenType.IDENTIFIER)
            self.consume(TokenType.SEMICOLON)
            return MoveStmt(destination=dest_tok.value, source=src_tok.value, span=dest_tok.span)

        elif tok.type == TokenType.IDENTIFIER:
            name_tok = self.consume(TokenType.IDENTIFIER)
            if self.peek().type == TokenType.ASSIGN:
                self.consume(TokenType.ASSIGN)
                expr = self.parse_expression()
                self.consume(TokenType.SEMICOLON)
                return AssignStmt(name=name_tok.value, expr=expr, span=name_tok.span)
            else:
                self.consume(TokenType.SEMICOLON)
                return ExprStmt(expr=IdentifierExpr(name_tok.value, span=name_tok.span), span=name_tok.span)

        raise SyntaxError(f"Parser Error: Unexpected statement token {tok.type} ('{tok.value}')")

    def parse_block(self) -> BlockStmt:
        self.consume(TokenType.LBRACE)
        stmts: List[ASTNode] = []
        while self.peek().type != TokenType.RBRACE and self.peek().type != TokenType.EOF:
            stmts.append(self.parse_statement())
        self.consume(TokenType.RBRACE)
        return BlockStmt(statements=stmts)
EOF

echo "src/frontend/lexer.py and src/frontend/parser.py restored with explicit PLUS/MINUS operator tokens."
