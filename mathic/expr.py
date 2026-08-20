import re
from dataclasses import dataclass


@dataclass(frozen=True)
class Num:
    value: int


@dataclass(frozen=True)
class Name:
    value: str


@dataclass(frozen=True)
class Binary:
    op: str
    left: object
    right: object


@dataclass(frozen=True)
class Call:
    name: str
    arg: object


TOKEN = re.compile(r'\s*(det|[A-Za-z_][A-Za-z0-9_]*|\d+|[()*+,-])')


def tokenize(source):
    pos = 0
    out = []
    while pos < len(source):
        m = TOKEN.match(source, pos)
        if not m:
            raise SyntaxError(f"unexpected character at {pos}: {source[pos]!r}")
        out.append(m.group(1))
        pos = m.end()
    return out


class Parser:
    def __init__(self, source):
        self.tokens = tokenize(source)
        self.pos = 0

    def peek(self):
        return self.tokens[self.pos] if self.pos < len(self.tokens) else None

    def take(self, token=None):
        got = self.peek()
        if got is None:
            raise SyntaxError("unexpected end of expression")
        if token is not None and got != token:
            raise SyntaxError(f"expected {token!r}, got {got!r}")
        self.pos += 1
        return got

    def expression(self):
        node = self.term()

        while self.peek() in ("+", "-"):
            op = self.take()
            node = Binary(op, node, self.term())

        return node

    def term(self):
        node = self.primary()

        while self.peek() == "*":
            op = self.take()
            node = Binary(op, node, self.primary())

        return node

    def primary(self):
        tok = self.take()

        if tok.isdigit():
            return Num(int(tok))

        if tok == "det":
            self.take("(")
            arg = self.expression()
            self.take(")")
            return Call("det", arg)

        if tok == "(":
            node = self.expression()
            self.take(")")
            return node

        if tok.isidentifier():
            return Name(tok)

        raise SyntaxError(f"unexpected token {tok!r}")


def parse(source):
    parser = Parser(source)
    node = parser.expression()

    if parser.peek() is not None:
        raise SyntaxError(f"unexpected token {parser.peek()!r}")

    return node


def main():
    import sys

    source = sys.argv[1] if len(sys.argv) > 1 else "det(A)"
    print(parse(source))


if __name__ == "__main__":
    main()
