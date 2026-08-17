import re
from enum import Enum, auto
from typing import List, NamedTuple


class TokenType(Enum):
    STAR = auto()
    MUT = auto()
    CONST = auto()
    LET = auto()
    IF = auto()
    ELSE = auto()
    RETURN = auto()
    MOVE = auto()
    CONSUME = auto()
    BORROW = auto()
    AS = auto()

    TYPE_LINEAR = auto()
    TYPE_AFFINE = auto()
    TYPE_COPY = auto()

    REG = auto()
    IDENTIFIER = auto()

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
    column: int
    offset: int


class Lexer:
    def __init__(self, source: str):
        self.source = source
        self.tokens: List[Token] = []
        self.line = 1
        self.column = 1

    def advance_position(self, text: str):
        for ch in text:
            if ch == "\n":
                self.line += 1
                self.column = 1
            else:
                self.column += 1

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

            if self.source[pos] == "\n":
                self.advance_position("\n")
                pos += 1
                continue

            if self.source[pos].isspace():
                self.advance_position(self.source[pos])
                pos += 1
                continue

            matched = False

            for token_type, regex in rules:
                match = re.match(
                    regex,
                    self.source[pos:],
                )

                if match:
                    val = match.group(0)

                    self.tokens.append(
                        Token(
                            token_type,
                            val,
                            self.line,
                            self.column,
                            pos,
                        )
                    )

                    self.advance_position(val)
                    pos += len(val)

                    matched = True
                    break

            if not matched:
                raise SyntaxError(
                    f"Lexer Error: Unknown sequence "
                    f"'{self.source[pos]}' at line {self.line}, "
                    f"column {self.column}"
                )

        self.tokens.append(
            Token(
                TokenType.EOF,
                "",
                self.line,
                self.column,
                pos,
            )
        )

        return self.tokens
