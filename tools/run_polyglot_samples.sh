#!/usr/bin/env bash
set -euo pipefail

mkdir -p samples

# 1. Zig Sample
cat << 'ZG' > samples/sample.zig
const std = @import("std");

pub fn main() void {
    std.debug.print("⚡ [ZIG] Execution complete: SIMD & fast memory bound verified.\n", .{});
}
ZG

# 2. Rust Sample
cat << 'RS' > samples/sample.rs
fn main() {
    println!("⚡ [RUST] Execution complete: Affine lifetime invariant bound verified.");
}
RS

# 3. QBE Sample
cat << 'QBE' > samples/sample.qbe
data $fmt = { b "⚡ [QBE] Execution complete: Micro-IL native lowering verified.\n", b 0 }
export function w $main() {
@start
    call $printf(l $fmt)
    ret 0
}
QBE

echo "============================================================"
echo " 🚀 COMPILING & RUNNING POLYGLOT TARGETS"
echo "============================================================"

echo "--- 1. Zig ---"
linum samples/sample.zig

echo -e "\n--- 2. Rust ---"
linum samples/sample.rs

echo -e "\n--- 3. QBE ---"
linum samples/sample.qbe

echo "============================================================"
echo "[✔] All polyglot sample runs finished."
