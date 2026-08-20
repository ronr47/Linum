from expr import parse, Num, Name, Binary, Call


MATRICES = {
    "A": (1, 2, 3, 4),
    "B": (5, 6, 7, 8),
}


def matmul(a, b):
    return (
        ("add", ("mul", a[0], b[0]), ("mul", a[1], b[2])),
        ("add", ("mul", a[0], b[1]), ("mul", a[1], b[3])),
        ("add", ("mul", a[2], b[0]), ("mul", a[3], b[2])),
        ("add", ("mul", a[2], b[1]), ("mul", a[3], b[3])),
    )


def determinant(m):
    return ("sub", ("mul", m[0], m[3]), ("mul", m[1], m[2]))


def lower(node):
    if isinstance(node, Num):
        return node.value

    if isinstance(node, Name):
        if node.value not in MATRICES:
            raise ValueError(f"unknown matrix: {node.value}")
        return MATRICES[node.value]

    if isinstance(node, Binary):
        left = lower(node.left)
        right = lower(node.right)

        if node.op == "*":
            return matmul(left, right)

        raise ValueError(f"unsupported operator: {node.op}")

    if isinstance(node, Call):
        if node.name != "det":
            raise ValueError(f"unknown function: {node.name}")

        value = lower(node.arg)

        if not isinstance(value, tuple) or len(value) != 4:
            raise TypeError("det expects a 2x2 matrix")

        return determinant(value)

    raise TypeError(f"unsupported AST node: {node!r}")


def emit_expr(expr, lines, counter):
    if isinstance(expr, int):
        return str(expr)

    op, left, right = expr

    lhs = emit_expr(left, lines, counter)
    rhs = emit_expr(right, lines, counter)

    reg = f"%r{counter[0]}"
    counter[0] += 1

    llvm_op = {
        "add": "add",
        "mul": "mul",
        "sub": "sub",
    }[op]

    lines.append(f"  {reg} = {llvm_op} i32 {lhs}, {rhs}")
    return reg


def compile_source(source):
    ast = parse(source)
    mathematical_ir = lower(ast)

    lines = [
        "; generated from: " + source,
        "",
        "define i32 @main() {",
        "entry:",
    ]

    result = emit_expr(mathematical_ir, lines, [0])

    lines += [
        f"  ret i32 {result}",
        "}",
        "",
    ]

    return "\n".join(lines)


if __name__ == "__main__":
    import sys

    source = sys.argv[1] if len(sys.argv) > 1 else "det(A * B)"
    print(compile_source(source))
