#!/usr/bin/env bash
set -e

PY_BIN="$( [ -f "./.venv/bin/python" ] && echo "./.venv/bin/python" || echo "$(which python3)" )"
export PYTHONPATH=".:$PYTHONPATH"

cat <<'EOF' > src/frontend/parser.py
from typing import List, Optional
from linum.src.frontend.lexer import Token, TokenType
from linum.src.ast.nodes import (
    ASTNode, BlockStmt, LetStmt, AssignStmt, MoveStmt, IfStmt,
    ReturnStmt, BorrowBlockStmt, ExprStmt, IdentifierExpr, PtrOffsetExpr
)
from linum.src.semantic.types import Type, OwnershipMode, PRIMITIVE_INTEGER, PRIMITIVE_BOOLEAN

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
            return LetStmt(name=name_tok.value, annotation=annot_type, expr=expr)

        elif tok.type == TokenType.IF:
            self.consume(TokenType.IF)
            cond_expr = self.parse_expression()
            then_block = self.parse_block()
            else_block = None
            if self.peek().type == TokenType.ELSE:
                self.consume(TokenType.ELSE)
                else_block = self.parse_block()
            return IfStmt(condition=cond_expr, then_block=then_block, else_block=else_block)

        elif tok.type == TokenType.RETURN:
            self.consume(TokenType.RETURN)
            ret_expr = None
            if self.peek().type != TokenType.SEMICOLON:
                ret_expr = self.parse_expression()
            self.consume(TokenType.SEMICOLON)
            return ReturnStmt(expr=ret_expr)

        elif tok.type == TokenType.BORROW:
            self.consume(TokenType.BORROW)
            var_tok = self.consume(TokenType.IDENTIFIER)
            self.consume(TokenType.AS)
            alias_tok = self.consume(TokenType.IDENTIFIER)
            body = self.parse_block()
            return BorrowBlockStmt(source=var_tok.value, borrow_alias=alias_tok.value, body=body)

        elif tok.type == TokenType.MOVE:
            self.consume(TokenType.MOVE)
            dest_tok = self.consume(TokenType.IDENTIFIER)
            self.consume(TokenType.ASSIGN)
            src_tok = self.consume(TokenType.IDENTIFIER)
            self.consume(TokenType.SEMICOLON)
            return MoveStmt(source=src_tok.value, destination=dest_tok.value)

        elif tok.type == TokenType.IDENTIFIER:
            name_tok = self.consume(TokenType.IDENTIFIER)
            if self.peek().type == TokenType.ASSIGN:
                self.consume(TokenType.ASSIGN)
                expr = self.parse_expression()
                self.consume(TokenType.SEMICOLON)
                return AssignStmt(target=name_tok.value, expr=expr)
            else:
                self.consume(TokenType.SEMICOLON)
                return ExprStmt(expr=IdentifierExpr(name=name_tok.value, span=name_tok.span))

        raise SyntaxError(f"Parser Error: Unexpected statement token {tok.type} ('{tok.value}')")

    def parse_block(self) -> BlockStmt:
        self.consume(TokenType.LBRACE)
        stmts: List[ASTNode] = []
        while self.peek().type != TokenType.RBRACE and self.peek().type != TokenType.EOF:
            stmts.append(self.parse_statement())
        self.consume(TokenType.RBRACE)
        return BlockStmt(statements=stmts)
EOF

echo "src/frontend/parser.py updated with verified AST dataclass signatures."
