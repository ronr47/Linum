from pathlib import Path

matrix_dim_code = """fn main() {
    let A: matrix = invalid_dim_a;
    let B: matrix = invalid_dim_b;
    let C: matrix = A * B;
}
"""
Path("tests/programs/matrix_dim_fail.linum").write_text(matrix_dim_code)

matrix_det_code = """fn main() {
    let A: matrix = non_square_matrix;
    let C = det(A);
}
"""
Path("tests/programs/matrix_det_fail.linum").write_text(matrix_det_code)

print("SUCCESS: Matrix validation test programs correctly generated.")
