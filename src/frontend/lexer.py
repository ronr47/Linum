"""Stage 0 R2 Lexer: Explicit systems syntax tokenization."""

import enum
import re
from typing import List, NamedTuple, Optional


class TokenType(enum.Enum):
    # Keywords
    MODULE = "MODULE"
    CONST = "CONST"
    ENUM = "ENUM"
    STRUCT = "STRUCT"
    FN = "FN"
    LET = "LET"
    VAR = "VAR"
    IF = "IF"
    ELSE = "ELSE"
    WHILE = "WHILE"
    RETURN = "RETURN"
    UNSAFE = "UNSAFE"
    AS = "AS"
    PRE = "PRE"
    POST = "POST"
    PRESERVES = "PRESERVES"

    # Memory Domain Specifiers
    RAM = "RAM"
    MMIO = "MMIO"
    IOPORT = "IOPORT"
    CAP = "CAP"

    # Literals & Identifiers
    IDENT = "IDENT"
    INT_LIT = "INT_LIT"
    BYTE_LIT = "BYTE_LIT"
    BOOL_LIT = "BOOL_LIT"

    # Operators & Delimiters
    LPAREN = "("
    RPAREN = ")"
    LBRACE = "{"
    RBRACE = "}"
    LBRACKET = "["
    RBRACKET = "]"
    LANGLE = "<"
    RANGLE = ">"
    COMMA = ","
    COLON = ":"
    SEMICOLON = ";"
    ARROW = "->"
    ATTR = "#"

    # Arithmetic / Logical / Bitwise
    ASSIGN = "="
    EQ = "=="
    NEQ = "!="
    LE = "<="
    GE = ">="
    ADD = "+"
    SUB = "-"
    BIT_OR = "|"
    BIT_AND = "&"
    BIT_XOR = "^"
    BIT_NOT = "~"
    SHL = "<<"
    SHR = ">>"
    NOT = "!"

    EOF = "EOF"


class Token(NamedTuple):
    type: TokenType
    value: any
    line: int
    col: int


KEYWORDS = {
    "module": TokenType.MODULE,
    "const": TokenType.CONST,
    "enum": TokenType.ENUM,
    "struct": TokenType.STRUCT,
    "fn": TokenType.FN,
    "let": TokenType.LET,
    "var": TokenType.VAR,
    "if": TokenType.IF,
    "else": TokenType.ELSE,
    "while": TokenType.WHILE,
    "return": TokenType.RETURN,
    "unsafe": TokenType.UNSAFE,
    "as": TokenType.AS,
    "pre": TokenType.PRE,
    "post": TokenType.POST,
    "preserves": TokenType.PRESERVES,
    "ram": TokenType.RAM,
    "mmio": TokenType.MMIO,
    "ioport": TokenType.IOPORT,
    "cap": TokenType.CAP,
    "true": TokenType.BOOL_LIT,
    "false": TokenType.BOOL_LIT,
}


class Lexer:
    def __init__(self, source: str):
        self.source = source
        self.len = len(source)
        self.pos = 0
        self.line = 1
        self.col = 1

    def _peek(self, offset: int = 0) -> str:
        idx = self.pos + offset
        return self.source[idx] if idx < self.len else "\0"

    def _advance(self) -> str:
        ch = self._peek()
        self.pos += 1
        if ch == "\n":
            self.line += 1
            self.col = 1
        else:
            self.col += 1
        return ch

    def tokenize(self) -> List[Token]:
        tokens: List[Token] = []

        while self.pos < self.len:
            ch = self._peek()

            # Whitespace
            if ch in " \t\r\n":
                self._advance()
                continue

            # Line comments (//)
            if ch == "/" and self._peek(1) == "/":
                while self.pos < self.len and self._peek() != "\n":
                    self._advance()
                continue

            start_col = self.col
            start_line = self.line

            # Byte literal b'A'
            if ch == "b" and self._peek(1) == "'":
                self._advance()  # b
                self._advance()  # '
                val = ord(self._advance())
                if self._peek() == "'":
                    self._advance()
                tokens.append(Token(TokenType.BYTE_LIT, val, start_line, start_col))
                continue

            # Hex numbers 0x...
            if ch == "0" and self._peek(1) in "xX":
                num_str = ""
                self._advance()  # 0
                self._advance()  # x
                while self._peek() in "0123456789abcdefABCDEF_":
                    c = self._advance()
                    if c != "_":
                        num_str += c
                tokens.append(Token(TokenType.INT_LIT, int(num_str, 16), start_line, start_col))
                continue

            # Decimal numbers
            if ch.isdigit():
                num_str = ""
                while self._peek().isdigit() or self._peek() == "_":
                    c = self._advance()
                    if c != "_":
                        num_str += c
                tokens.append(Token(TokenType.INT_LIT, int(num_str, 10), start_line, start_col))
                continue

            # Identifiers and keywords
            if ch.isalpha() or ch == "_":
                ident = ""
                while self._peek().isalnum() or self._peek() == "_":
                    ident += self._advance()
                if ident in KEYWORDS:
                    val = True if ident == "true" else False if ident == "false" else ident
                    tokens.append(Token(KEYWORDS[ident], val, start_line, start_col))
                else:
                    tokens.append(Token(TokenType.IDENT, ident, start_line, start_col))
                continue

            # Multi-character operators
            if ch == "-" and self._peek(1) == ">":
                self._advance(); self._advance()
                tokens.append(Token(TokenType.ARROW, "->", start_line, start_col))
                continue
            if ch == "=" and self._peek(1) == "=":
                self._advance(); self._advance()
                tokens.append(Token(TokenType.EQ, "==", start_line, start_col))
                continue
            if ch == "!" and self._peek(1) == "=":
                self._advance(); self._advance()
                tokens.append(Token(TokenType.NEQ, "!=", start_line, start_col))
                continue
            if ch == "<" and self._peek(1) == "=":
                self._advance(); self._advance()
                tokens.append(Token(TokenType.LE, "<=", start_line, start_col))
                continue
            if ch == ">" and self._peek(1) == "=":
                self._advance(); self._advance()
                tokens.append(Token(TokenType.GE, ">=", start_line, start_col))
                continue
            if ch == "<" and self._peek(1) == "<":
                self._advance(); self._advance()
                tokens.append(Token(TokenType.SHL, "<<", start_line, start_col))
                continue
            if ch == ">" and self._peek(1) == ">":
                self._advance(); self._advance()
                tokens.append(Token(TokenType.SHR, ">>", start_line, start_col))
                continue

            # Single-character tokens
            single = {
                "(": TokenType.LPAREN,
                ")": TokenType.RPAREN,
                "{": TokenType.LBRACE,
                "}": TokenType.RBRACE,
                "[": TokenType.LBRACKET,
                "]": TokenType.RBRACKET,
                "<": TokenType.LANGLE,
                ">": TokenType.RANGLE,
                ",": TokenType.COMMA,
                ":": TokenType.COLON,
                ";": TokenType.SEMICOLON,
                "#": TokenType.ATTR,
                "=": TokenType.ASSIGN,
                "+": TokenType.ADD,
                "-": TokenType.SUB,
                "|": TokenType.BIT_OR,
                "&": TokenType.BIT_AND,
                "^": TokenType.BIT_XOR,
                "~": TokenType.BIT_NOT,
                "!": TokenType.NOT,
            }
            if ch in single:
                self._advance()
                tokens.append(Token(single[ch], ch, start_line, start_col))
                continue

            # Unknown byte skip
            self._advance()

        tokens.append(Token(TokenType.EOF, "", self.line, self.col))
        return tokens
