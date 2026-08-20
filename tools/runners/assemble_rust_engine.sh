#!/usr/bin/env bash
set -euo pipefail

mkdir -p /home/ron/linum/rust_lane/src

# 1. Generate Cargo.toml
cat << 'TOML' > /home/ron/linum/rust_lane/Cargo.toml
[package]
name = "rust_sys_engine"
version = "0.1.0"
edition = "2021"

[lib]
crate-type = ["cdylib", "rlib"]

[dependencies]
libc = "0.2"
TOML

# 2. Generate Native Tensor SIMD Kernel
cat << 'RUST' > /home/ron/linum/rust_lane/src/lib.rs
use std::slice;

#[repr(C)]
pub struct TensorDimensions {
    pub dims: *const usize,
    pub rank: usize,
}

#[no_mangle]
pub unsafe extern "C" fn execute_hardware_tensor_transform(
    data: *mut f32,
    dimensions: TensorDimensions,
) -> i32 {
    if data.is_null() || dimensions.dims.is_null() {
        return -1;
    }

    let dims_slice = slice::from_raw_parts(dimensions.dims, dimensions.rank);
    let mut total_elements: usize = 1;
    for &d in dims_slice {
        total_elements *= d;
    }

    let buffer = slice::from_raw_parts_mut(data, total_elements);

    // High-performance vectorized transformation pass (FMA / SIMD scale)
    for elem in buffer.iter_mut() {
        *elem = (*elem * 2.5) + 0.5;
    }

    0
}
RUST

echo "[+] Compiling Rust Native Engine..."
cd /home/ron/linum/rust_lane
RUSTFLAGS="-C target-cpu=native -C opt-level=3" cargo build --release
mkdir -p /home/ron/linum/target/release
cp target/release/librust_sys_engine.so /home/ron/linum/target/release/
echo "[✔] librust_sys_engine.so ready at /home/ron/linum/target/release/"
