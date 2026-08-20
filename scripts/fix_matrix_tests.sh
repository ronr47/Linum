#!/bin/bash

# Overwrite matrix_dim_fail.linum without the '-> i64' syntax
cat << 'INNER_EOF' > tests/programs/matrix_dim_fail.linum
fn main() {
    let A: matrix = matrix_new_dim_mismatch_placeholder;
    let B: matrix = matrix_new_dim_mismatch_placeholder;
    let C: matrix = A * B;
    return 0;
}
INNER_EOF

# Overwrite matrix_det_fail.linum without the '-> i64' syntax
cat << 'INNER_EOF' > tests/programs/matrix_det_fail.linum
fn main() {
    let A: matrix = matrix_new_non_square_placeholder;
    let C: i64 = det(A);
    return 0;
}
INNER_EOF

echo "Test programs successfully updated without arrow return signatures."
