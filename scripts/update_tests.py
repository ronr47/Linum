import pytest

def test_matrix_dimension_mismatch_rejection(pipeline):
    invalid_dimension_code = """
    let A: i64 = ((1, 2), (3, 4), (5, 6));
    let B: i64 = ((1, 2), (3, 4));
    let C = A * B;
    """
    with pytest.raises(DiagnosticError, match="matrix multiplication dimension mismatch"):
        pipeline.run(invalid_dimension_code)

def test_matrix_non_square_determinant_rejection(pipeline):
    non_square_code = """
    let A: i64 = ((1, 2, 3), (4, 5, 6));
    det(A);
    """
    with pytest.raises(DiagnosticError, match="det expects a square matrix"):
        pipeline.run(non_square_code)
