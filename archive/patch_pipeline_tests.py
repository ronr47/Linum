from pathlib import Path

file_path = Path("tests/test_program_pipeline.py")
content = file_path.read_text()

# Cut off everything after line 350 to clear previous broken test injections
lines = content.splitlines()
output_lines = lines[:350]

new_content = """
def test_matrix_dimension_mismatch_rejection():
    \"\"\"Verify linum rejects multiplying non-conforming matrix dimensions.\"\"\"
    with pytest.raises(DiagnosticError, match="matrix multiplication dimension mismatch"):
        compile_source(load("matrix_dim_fail.linum"), "matrix_dim_fail")

def test_matrix_non_square_determinant_rejection():
    \"\"\"Verify linum rejects computing a determinant on non-square matrices.\"\"\"
    with pytest.raises(DiagnosticError, match="det expects a square matrix"):
        compile_source(load("matrix_det_fail.linum"), "matrix_det_fail")
"""

file_path.write_text("\n".join(output_lines) + new_content + "\n")
print("Clean test harness references applied via program loader.")
