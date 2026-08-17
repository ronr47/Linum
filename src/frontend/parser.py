# linum/src/frontend/parser.py
from typing import List
from linum.src.frontend.lexer import Token, TokenType
from linum.src.semantic.types import Type, OwnershipMode, PRIMITIVE_INTEGER
from linum.src.ast.nodes import (
    ASTNode, BlockStmt, LetStmt, IfStmt, IdentifierExpr, 
    FunctionDecl, BorrowBlockStmt, ExprStmt, CallExpr, ReturnStmt, AssignStmt
)

class Parser:
    def __init__(self, tokens: List[Token]):
        self.tokens = tokens
        self.pos = 0

    def peek(self) -> Token:
        if self.pos < len(self.tokens):
            return self.tokens[self.pos]
        return Token(TokenType.EOF, "")

    def consume(self, expected_type: TokenType) -> Token:
        tok = self.peek()
        if tok.type != expected_type:
            raise SyntaxError(f"Parser Error: Expected {expected_type}, got {tok.type}")
        self.pos += 1
        return tok

    def token_span(self, tok: Token):
        return getattr(tok, 'span', None)

    def parse_type(self) -> Type:
        tok = self.peek()
        if tok.type == TokenType.TYPE_COPY:
            self.consume(TokenType.TYPE_COPY)
            return PRIMITIVE_INTEGER
        elif tok.type == TokenType.TYPE_LINEAR:
            self.consume(TokenType.TYPE_LINEAR)
            return Type("LINEAR_RES", OwnershipMode.LINEAR)
        elif tok.type == TokenType.TYPE_AFFINE:
            self.consume(TokenType.TYPE_AFFINE)
            return Type("AFFINE_RES", OwnershipMode.AFFINE)
        elif tok.type == TokenType.IDENTIFIER and tok.value == "ptr":
            self.consume(TokenType.IDENTIFIER)
            return PRIMITIVE_INTEGER
        raise SyntaxError(f"Parser Error: Invalid type specification parsing token {tok.type}")

    def parse_statement(self) -> ASTNode:
        tok = self.peek()
        if tok.type == TokenType.LET:
            self.consume(TokenType.LET)
            name_tok = self.consume(TokenType.IDENTIFIER)
            self.consume(TokenType.COLON)
            ty = self.parse_type()
            self.consume(TokenType.ASSIGN)
            expr = self.parse_expression()
            self.consume(TokenType.SEMI)
            return LetStmt(name_tok.value, ty, expr)
        elif tok.type == TokenType.IF:
            self.consume(TokenType.IF)
            cond = self.parse_expression()
            then_b = self.parse_block()
            if self.peek().type == TokenType.ELSE:
                self.consume(TokenType.ELSE)
                else_b = self.parse_block()
            else:
                else_b = BlockStmt([])
            return IfStmt(cond, then_b, else_b)
        elif tok.type == TokenType.RETURN:
            self.consume(TokenType.RETURN)
            expr = self.parse_expression()
            self.consume(TokenType.SEMI)
            return ReturnStmt(expr)
        elif tok.type == TokenType.IDENTIFIER:
            target_tok = self.consume(TokenType.IDENTIFIER)
            self.consume(TokenType.ASSIGN)
            expr = self.parse_expression()
            self.consume(TokenType.SEMI)
            # Statically instantiate AssignStmt to preserve the semantic validation layer rules
            return AssignStmt(target_tok.value, expr)
        else:
            expr = self.parse_expression()
            self.consume(TokenType.SEMI)
            return ExprStmt(expr)

    def parse_block(self) -> BlockStmt:
        self.consume(TokenType.LBRACE)
        stmts = []
        while self.peek().type != TokenType.RBRACE and self.peek().type != TokenType.EOF:
            stmts.append(self.parse_statement())
        self.consume(TokenType.RBRACE)
        return BlockStmt(stmts)

    def parse_expression(self) -> ASTNode:
        tok = self.peek()
        if tok.type == TokenType.IDENTIFIER:
            self.consume(TokenType.IDENTIFIER)
            left = IdentifierExpr(tok.value, self.token_span(tok))
            
            # Check for immediate offset operators treated as identifiers or custom tokens
            next_tok = self.peek()
            if next_tok.type == TokenType.IDENTIFIER and next_tok.value in ("+", "-"):
                self.consume(TokenType.IDENTIFIER)
                offset = self.parse_expression()
                from linum.src.ast.nodes import PtrOffsetExpr
                return PtrOffsetExpr(left, offset)
            return left
        elif tok.type == TokenType.REG:
            self.consume(TokenType.REG)
            return IdentifierExpr(tok.value, self.token_span(tok))
        raise SyntaxError(f"Parser Error: Invalid primary expression token {tok.type}")
