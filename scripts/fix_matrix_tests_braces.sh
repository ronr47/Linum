#!/bin/bash

# Overwrite matrix_dim_fail.linum with braced block syntax
cat << 'INNER_EOF' > tests/programs/matrix_dim_fail.linum
{
    let A: matrix = matrix_new_dim_mismatch_placeholder;
    let B: matrix = matrix_new_dim_mismatch_placeholder;
    let C: matrix = A * B;
}
INNER_EOF

# Overwrite matrix_det_fail.linum with braced block syntax
cat << 'INNER_EOF' > tests/programs/matrix_det_fail.linum
{
    let A: matrix = matrix_new_non_square_placeholder;
    let C: i64 = det(A);
}
INNER_EOF

echo "Test programs successfully updated with outer curly braces."
