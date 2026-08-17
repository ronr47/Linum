from enum import Enum, auto
import re
from typing import List, NamedTuple

class TokenType(Enum):
    LET = auto()
    IF = auto()
    ELSE = auto()
    RETURN = auto()
    MOVE = auto()
    CONSUME = auto()
    BORROW = auto()
    AS = auto()
    IDENTIFIER = auto()
    REG = auto()
    TYPE_LINEAR = auto()
    TYPE_AFFINE = auto()
    TYPE_COPY = auto()
    ASSIGN = auto()
    LBRACE = auto()
    RBRACE = auto()
    LPAREN = auto()
    RPAREN = auto()
    SEMI = auto()
    COLON = auto()
    COMMA = auto()
    EOF = auto()

class Token(NamedTuple):
    type: TokenType
    value: str
    line: int

class Lexer:
    def __init__(self, source: str):
        self.source = source
        self.tokens: List[Token] = []
        self.line = 1
        
    def tokenize(self) -> List[Token]:
        rules = [
            (TokenType.LET, r'\blet\b'),
            (TokenType.IF, r'\bif\b'),
            (TokenType.ELSE, r'\belse\b'),
            (TokenType.RETURN, r'\breturn\b'),
            (TokenType.MOVE, r'\bmove\b'),
            (TokenType.CONSUME, r'\bconsume\b'),
            (TokenType.BORROW, r'\bborrow\b'),
            (TokenType.AS, r'\bas\b'),
            (TokenType.TYPE_LINEAR, r'\bLINEAR\b'),
            (TokenType.TYPE_AFFINE, r'\bAFFINE\b'),
            (TokenType.TYPE_COPY, r'\bCOPY\b'),
            (TokenType.REG, r'%[a-zA-Z_0-9]+'),
            (TokenType.IDENTIFIER, r'[a-zA-Z_][a-zA-Z_0-9]*'),
            (TokenType.ASSIGN, r'='),
            (TokenType.LBRACE, r'\{'),
            (TokenType.RBRACE, r'\}'),
            (TokenType.LPAREN, r'\('),
            (TokenType.RPAREN, r'\)'),
            (TokenType.SEMI, r';'),
            (TokenType.COLON, r':'),
            (TokenType.COMMA, r','),
        ]
        
        pos = 0
        while pos < len(self.source):
            if self.source[pos] == '\n':
                self.line += 1
                pos += 1
                continue
            if self.source[pos].isspace():
                pos += 1
                continue
                
            matched = False
            for token_type, regex in rules:
                match = re.match(regex, self.source[pos:])
                if match:
                    val = match.group(0)
                    self.tokens.append(Token(token_type, val, self.line))
                    pos += len(val)
                    matched = True
                    break
            if not matched:
                raise SyntaxError(f"Lexer Error: Unknown sequence target input mapping trace: '{self.source[pos]}' at line {self.line}")
                
        self.tokens.append(Token(TokenType.EOF, "", self.line))
        return self.tokens
