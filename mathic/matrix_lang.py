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

def matmul(a: Matrix, b: Matrix) -> Matrix:
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

def determinant(m: Matrix) -> int:
    if m.shape != (2, 2):
        raise TypeError(
            f"det currently requires Matrix<2,2>, got Matrix<{m.shape[0]},{m.shape[1]}>"
        )
    return m.rows[0][0] * m.rows[1][1] - m.rows[0][1] * m.rows[1][0]

def main():
    A = Matrix((
        (1, 2),
        (3, 4),
    ))

    B = Matrix((
        (5, 6),
        (7, 8),
    ))

    C = matmul(A, B)

    print("A shape:", A.shape)
    print("B shape:", B.shape)
    print("C:", C.rows)
    print("det(C):", determinant(C))

if __name__ == "__main__":
    main()
