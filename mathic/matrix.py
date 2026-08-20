from dataclasses import dataclass


@dataclass(frozen=True)
class Matrix2x2:
    a00: float
    a01: float
    a10: float
    a11: float

    def __matmul__(self, other: "Matrix2x2") -> "Matrix2x2":
        return Matrix2x2(
            self.a00 * other.a00 + self.a01 * other.a10,
            self.a00 * other.a01 + self.a01 * other.a11,
            self.a10 * other.a00 + self.a11 * other.a10,
            self.a10 * other.a01 + self.a11 * other.a11,
        )

    def determinant(self) -> float:
        return self.a00 * self.a11 - self.a01 * self.a10


def main():
    A = Matrix2x2(1, 2, 3, 4)
    B = Matrix2x2(5, 6, 7, 8)

    C = A @ B

    print("C =", C)
    print("det(C) =", C.determinant())


if __name__ == "__main__":
    main()
