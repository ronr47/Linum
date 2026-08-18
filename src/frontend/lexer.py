import re
from enum import Enum, auto
from typing import List, Optional
from linum.src.diagnostics import SourceSpan

class TokenType(Enum):
    STRUCT = auto()
    DOT = auto()
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
        (TokenType.STRUCT, r'\bstruct\b'),
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
        
        (TokenType.DOT, r'\.'),
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
