#!/bin/bash
set -e

echo "[$] Null_Pointer: Forging memory-safe Rust boundary for Firecracker..."

cd ~/linum

# Initialize cargo project if Cargo.toml doesn't exist
if [ ! -f Cargo.toml ]; then
    cargo init --lib --name safe_wrapper
fi

# Configure Cargo.toml for staticlib generation
cat << 'CARGO' > Cargo.toml
[package]
name = "safe_wrapper"
version = "0.1.0"
edition = "2021"

[lib]
name = "safe_wrapper"
crate-type = ["staticlib"]
CARGO

# Write the safe memory wrapper source code
cat << 'RUST' > src/lib.rs
use std::slice;

#[no_mangle]
pub extern "C" fn sanitize_memory_region(ptr: *mut u8, len: usize) -> i32 {
    if ptr.is_null() || len == 0 {
        return -1;
    }
    
    // Create a safe slice over the raw pointer domain
    let memory_slice = unsafe { slice::from_raw_parts_mut(ptr, len) };
    
    // Perform a sterile sanitization pass
    for byte in memory_slice.iter_mut() {
        if *byte == 0xFF {
            *byte = 0x00;
        }
    }
    
    0 // Success status code
}
RUST

# Build the static library target using correct quiet flag
cargo build --release --quiet
echo "[$] Success: Memory-safe static library forged at target/release/libsafe_wrapper.a"
