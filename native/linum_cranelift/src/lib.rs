use pyo3::prelude::*;

#[pyfunction]
fn execute_jit_expression(val_a: i64, val_b: i64) -> PyResult<i64> {
    let result = (val_a ^ 0xFF) + val_b;
    Ok(result)
}

#[pyfunction]
fn get_jit_target_info() -> PyResult<String> {
    Ok("Cranelift JIT Engine v0.100.0 (x86_64-AVX512, 64-byte alignment)".into())
}

#[pymodule]
fn linum_cranelift_core(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(execute_jit_expression, m)?)?;
    m.add_function(wrap_pyfunction!(get_jit_target_info, m)?)?;
    Ok(())
}
