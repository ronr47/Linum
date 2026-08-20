import re
from dataclasses import dataclass


@dataclass(frozen=True)
class Matrix:
    rows: tuple[tuple[int, ...], ...]

    @property
    def shape(self):
        return (len(self.rows), len(self.rows[0]))

    def __post_init__(self):
        if not self.rows:
            raise ValueError("matrix cannot be empty")
        width = len(self.rows[0])
        if width == 0 or any(len(row) != width for row in self.rows):
            raise ValueError("matrix rows must have equal width")


@dataclass(frozen=True)
class Name:
    value: str


@dataclass(frozen=True)
class MatrixLiteral:
    rows: tuple[tuple[int, ...], ...]


@dataclass(frozen=True)
class Binary:
    op: str
    left: object
    right: object


@dataclass(frozen=True)
class Call:
    name: str
    arg: object


TOKEN = re.compile(r'\s*(det|[A-Za-z_][A-Za-z0-9_]*|\d+|[=()\[\],*+-])')


def tokenize(source):
    pos = 0
    tokens = []

    while pos < len(source):
        match = TOKEN.match(source, pos)
        if not match:
            raise SyntaxError(
                f"unexpected character at position {pos}: {source[pos]!r}"
            )
        tokens.append(match.group(1))
        pos = match.end()

    return tokens


class Parser:
    def __init__(self, source):
        self.tokens = tokenize(source)
        self.pos = 0

    def peek(self):
        if self.pos >= len(self.tokens):
            return None
        return self.tokens[self.pos]

    def take(self, expected=None):
        token = self.peek()

        if token is None:
            raise SyntaxError("unexpected end of input")

        if expected is not None and token != expected:
            raise SyntaxError(f"expected {expected!r}, got {token!r}")

        self.pos += 1
        return token

    def expression(self):
        node = self.term()

        while self.peek() in ("+", "-"):
            op = self.take()
            node = Binary(op, node, self.term())

        return node

    def term(self):
        node = self.primary()

        while self.peek() == "*":
            self.take("*")
            node = Binary("*", node, self.primary())

        return node

    def primary(self):
        token = self.peek()

        if token == "det":
            self.take("det")
            self.take("(")
            arg = self.expression()
            self.take(")")
            return Call("det", arg)

        if token == "[":
            return self.matrix_literal()

        if token == "(":
            self.take("(")
            node = self.expression()
            self.take(")")
            return node

        if token and token[0].isalpha():
            return Name(self.take())

        raise SyntaxError(f"unexpected token {token!r}")

    def matrix_literal(self):
        self.take("[")

        rows = []

        while True:
            self.take("[")
            values = []

            while True:
                values.append(int(self.take()))
                if self.peek() != ",":
                    break
                self.take(",")

            self.take("]")
            rows.append(tuple(values))

            if self.peek() != ",":
                break
            self.take(",")

        self.take("]")

        return MatrixLiteral(tuple(rows))


def matmul(a, b):
    ar, ac = a.shape
    br, bc = b.shape

    if ac != br:
        raise TypeError(
            f"matrix multiplication dimension mismatch: "
            f"{ar}x{ac} * {br}x{bc}"
        )

    return Matrix(tuple(
        tuple(
            sum(a.rows[i][k] * b.rows[k][j] for k in range(ac))
            for j in range(bc)
        )
        for i in range(ar)
    ))


def determinant(m):
    if m.shape != (2, 2):
        raise TypeError(
            f"det currently requires Matrix<2,2>, "
            f"got Matrix<{m.shape[0]},{m.shape[1]}>"
        )

    return m.rows[0][0] * m.rows[1][1] - m.rows[0][1] * m.rows[1][0]


def evaluate(node, env):
    if isinstance(node, MatrixLiteral):
        return Matrix(node.rows)

    if isinstance(node, Name):
        if node.value not in env:
            raise NameError(f"unknown matrix: {node.value}")
        return env[node.value]

    if isinstance(node, Binary):
        left = evaluate(node.left, env)
        right = evaluate(node.right, env)

        if node.op == "*":
            return matmul(left, right)

        raise TypeError(f"unsupported operator: {node.op}")

    if isinstance(node, Call):
        if node.name != "det":
            raise TypeError(f"unknown function: {node.name}")
        return determinant(evaluate(node.arg, env))

    raise TypeError(f"unsupported AST node: {node!r}")


def parse_program(source):
    env = {}
    statements = [
        line.strip()
        for line in source.splitlines()
        if line.strip()
    ]

    result = None

    for statement in statements:
        if "=" in statement:
            name, expression = statement.split("=", 1)
            name = name.strip()
            env[name] = evaluate(Parser(expression.strip()).expression(), env)
        else:
            result = evaluate(Parser(statement).expression(), env)

    return result


if __name__ == "__main__":
    import sys

    source = sys.stdin.read()

    result = parse_program(source)

    if isinstance(result, int):
        print(result)
    elif isinstance(result, Matrix):
        print(result.rows)
    else:
        print(result)
