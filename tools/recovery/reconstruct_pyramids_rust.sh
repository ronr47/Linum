#!/usr/bin/env bash
set -euo pipefail

cd /home/ron/linum
mkdir -p rust_sys_engine/src

# 1. Generate Cargo Configuration
cat << 'TOML' > rust_sys_engine/Cargo.toml
[package]
name = "rust_sys_engine"
version = "0.1.0"
edition = "2021"

[lib]
crate-type = ["cdylib", "rlib"]

[dependencies]
libc = "0.2"
TOML

# 2. Reconstruct Hardware Tensor Transform Implementation
cat << 'RUST' > rust_sys_engine/src/lib.rs
use std::slice;

#[repr(C)]
pub struct TensorDimensions {
    pub dims: *const usize,
    pub rank: usize,
}

#[no_mangle]
pub unsafe extern "C" fn execute_hardware_tensor_transform(
    data_ptr: *mut f32,
    dimensions: TensorDimensions,
) -> i32 {
    if data_ptr.is_null() || dimensions.dims.is_null() || dimensions.rank == 0 {
        return -1;
    }

    let shape = slice::from_raw_parts(dimensions.dims, dimensions.rank);
    let total_elements: usize = shape.iter().product();

    let tensor_slice = slice::from_raw_parts_mut(data_ptr, total_elements);

    // Apply high-throughput affine scaling vector transform
    for val in tensor_slice.iter_mut() {
        *val = (*val * 2.5) + 1.25;
    }

    0
}
RUST

echo "[*] Compiling librust_sys_engine.so..."
cargo build --release --manifest-path rust_sys_engine/Cargo.toml

# Copy compiled shared object for direct Mojo / C linking
mkdir -p ./target/release
cp rust_sys_engine/target/release/librust_sys_engine.so ./target/release/
echo "[✔] librust_sys_engine.so compiled and placed in ./target/release/"
