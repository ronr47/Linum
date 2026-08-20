import re
import sys
from dataclasses import dataclass

@dataclass(frozen=True)
class Num:
    value: int

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
            raise SyntaxError(f"Unexpected character at {pos}")
        tokens.append(match.group(1))
        pos = match.end()
    return tokens

class Parser:
    def __init__(self, source):
        self.tokens = tokenize(source)
        self.pos = 0

    def peek(self):
        return self.tokens[self.pos] if self.pos < len(self.tokens) else None

    def take(self, expected=None):
        tok = self.peek()
        if tok is None:
            raise SyntaxError("Unexpected EOF")
        if expected and tok != expected:
            raise SyntaxError(f"Expected {expected}, got {tok}")
        self.pos += 1
        return tok

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
        tok = self.peek()
        if tok == "det":
            self.take("det")
            self.take("(")
            arg = self.expression()
            self.take(")")
            return Call("det", arg)
        if tok == "[":
            return self.matrix_literal()
        if tok == "(":
            self.take("(")
            node = self.expression()
            self.take(")")
            return node
        if tok and tok.isdigit():
            return Num(int(self.take()))
        if tok and tok.isidentifier():
            return Name(self.take())
        raise SyntaxError(f"Unexpected token {tok}")

    def matrix_literal(self):
        self.take("[")
        rows = []
        while self.peek() != "]":
            rows.append(self.row_literal())
            if self.peek() == ",":
                self.take(",")
        self.take("]")
        return MatrixLiteral(tuple(rows))

    def row_literal(self):
        self.take("[")
        elements = []
        while self.peek() != "]":
            token = self.take()
            if token == "-":
                elements.append(-int(self.take()))
            else:
                elements.append(int(token))
            if self.peek() == ",":
                self.take(",")
        self.take("]")
        return tuple(elements)

def mat_add(a, b):
    return (
        ("add", a[0], b[0]),
        ("add", a[1], b[1]),
        ("add", a[2], b[2]),
        ("add", a[3], b[3]),
    )

def mat_sub(a, b):
    return (
        ("sub", a[0], b[0]),
        ("sub", a[1], b[1]),
        ("sub", a[2], b[2]),
        ("sub", a[3], b[3]),
    )

def mat_mul(a, b):
    return (
        ("add", ("mul", a[0], b[0]), ("mul", a[1], b[2])),
        ("add", ("mul", a[0], b[1]), ("mul", a[1], b[3])),
        ("add", ("mul", a[2], b[0]), ("mul", a[3], b[2])),
        ("add", ("mul", a[2], b[1]), ("mul", a[3], b[3])),
    )

def determinant(m):
    return ("sub", ("mul", m[0], m[3]), ("mul", m[1], m[2]))

def lower_node(node, env):
    if isinstance(node, Num):
        return node.value

    if isinstance(node, Name):
        if node.value not in env:
            raise NameError(f"Undefined variable: {node.value}")
        return env[node.value]

    if isinstance(node, MatrixLiteral):
        # Flatten a [[a, b], [c, d]] literal down to a 4-tuple of IR terms
        return (node.rows[0][0], node.rows[0][1], node.rows[1][0], node.rows[1][1])

    if isinstance(node, Binary):
        left = lower_node(node.left, env)
        right = lower_node(node.right, env)

        if node.op == "*":
            return mat_mul(left, right)
        if node.op == "+":
            return mat_add(left, right)
        if node.op == "-":
            return mat_sub(left, right)

    if isinstance(node, Call):
        if node.name == "det":
            arg = lower_node(node.arg, env)
            return determinant(arg)

    raise TypeError(f"Unsupported AST configuration: {node}")

def emit_expr(expr, lines, counter):
    if isinstance(expr, int):
        return str(expr)
    if isinstance(expr, str) and expr.startswith("%"):
        return expr

    op, left, right = expr
    lhs = emit_expr(left, lines, counter)
    rhs = emit_expr(right, lines, counter)

    reg = f"%r{counter[0]}"
    counter[0] += 1

    llvm_op = {"add": "add", "mul": "mul", "sub": "sub"}[op]
    lines.append(f"  {reg} = {llvm_op} i32 {lhs}, {rhs}")
    return reg

def compile_source(source_text):
    env = {}
    lines = [
        "; Target and Builtins setup",
        "@fmt = private unnamed_addr constant [4 x i8] c\"%d\\0A\\00\"",
        "declare i32 @printf(ptr, ...)",
        "",
        "define i32 @main() {",
        "entry:",
    ]
    
    counter = [0]
    statements = [line.strip() for line in source_text.splitlines() if line.strip()]
    
    last_result_reg = None
    
    for statement in statements:
        if "=" in statement:
            name, expr_str = statement.split("=", 1)
            name = name.strip()
            ast = Parser(expr_str.strip()).expression()
            env[name] = lower_node(ast, env)
        else:
            ast = Parser(statement).expression()
            lowered_ir = lower_node(ast, env)
            
            if isinstance(lowered_ir, tuple) and len(lowered_ir) == 4:
                # If the final statement is a matrix, let's print all 4 elements
                # For simplicity, we calculate them all into registers here
                regs = [emit_expr(e, lines, counter) for e in lowered_ir]
                for r in regs:
                    lines.append(f"  call i32 (ptr, ...) @printf(ptr @fmt, i32 {r})")
                last_result_reg = "0"
            else:
                last_result_reg = emit_expr(lowered_ir, lines, counter)
                lines.append(f"  call i32 (ptr, ...) @printf(ptr @fmt, i32 {last_result_reg})")
                
    if last_result_reg is None:
        last_result_reg = "0"
        
    lines += [
        "  ret i32 0",
        "}",
    ]
    return "\n".join(lines)

if __name__ == "__main__":
    import sys
    source = sys.stdin.read()
    print(compile_source(source))
