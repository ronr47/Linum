from typing import List, Optional
from linum.src.frontend.lexer import Token, TokenType
from linum.src.diagnostics.span import SourceSpan
from linum.src.semantic.types import Type, OwnershipMode, PRIMITIVE_INTEGER, PRIMITIVE_BOOLEAN
from linum.src.ast.nodes import ASTNode, IdentifierExpr, LetStmt, AssignStmt, MoveStmt, ExprStmt, ReturnStmt, BlockStmt, BorrowBlockStmt, IfStmt

class Parser:
    def __init__(self, tokens: List[Token]):
        self.tokens = tokens
        self.pos = 0
        
    def peek(self) -> Token:
        return self.tokens[self.pos]
        
    def token_span(self, tok: Token) -> SourceSpan:
        return SourceSpan(
            line=tok.line,
            column=tok.column,
            length=len(tok.value),
        )


    def consume(self, expected: TokenType) -> Token:
        tok = self.peek()
        if tok.type != expected:
            raise SyntaxError(f"Parser Error: Expected token {expected}, got {tok.type} ('{tok.value}') on line {tok.line}")
        self.pos += 1
        return tok
        
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
        raise SyntaxError(f"Parser Error: Invalid type specification parsing token {tok.type}")

    def parse_statement(self) -> ASTNode:
        tok = self.peek()
        if tok.type == TokenType.LET:
            self.consume(TokenType.LET)
            name = self.consume(TokenType.IDENTIFIER).value
            self.consume(TokenType.COLON)
            ty = self.parse_type()
            self.consume(TokenType.ASSIGN)
            expr = self.parse_expression()
            self.consume(TokenType.SEMI)
            return LetStmt(name, ty, expr)
            
        elif tok.type == TokenType.IDENTIFIER:
            name = self.consume(TokenType.IDENTIFIER).value
            if self.peek().type == TokenType.ASSIGN:
                self.consume(TokenType.ASSIGN)
                expr = self.parse_expression()
                self.consume(TokenType.SEMI)
                return AssignStmt(name, expr)
            elif self.peek().type == TokenType.MOVE:
                self.consume(TokenType.MOVE)
                dest = self.consume(TokenType.IDENTIFIER).value
                self.consume(TokenType.SEMI)
                return MoveStmt(name, dest)
                
        elif tok.type == TokenType.RETURN:
            self.consume(TokenType.RETURN)
            expr = None
            if self.peek().type != TokenType.SEMI:
                expr = self.parse_expression()
            self.consume(TokenType.SEMI)
            return ReturnStmt(expr)
            
        elif tok.type == TokenType.BORROW:
            self.consume(TokenType.BORROW)
            src = self.consume(TokenType.IDENTIFIER).value
            self.consume(TokenType.AS)
            alias = self.consume(TokenType.IDENTIFIER).value
            body = self.parse_block()
            return BorrowBlockStmt(src, alias, body)
            
        elif tok.type == TokenType.IF:
            self.consume(TokenType.IF)
            cond = self.parse_expression()
            then_b = self.parse_block()
            self.consume(TokenType.ELSE)
            else_b = self.parse_block()
            return IfStmt(cond, then_b, else_b)
            
        raise SyntaxError(f"Parser Error: Unexpected statement head token token {tok.type}")

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
            return IdentifierExpr(
                tok.value,
                self.token_span(tok),
            )
        elif tok.type == TokenType.REG:
            self.consume(TokenType.REG)
            return IdentifierExpr(
                tok.value,
                self.token_span(tok),
            )
        raise SyntaxError(f"Parser Error: Invalid primary expression token token {tok.type}")
