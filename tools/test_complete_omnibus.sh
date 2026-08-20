cat << 'EOF' > test_complete_omnibus.sh
#!/usr/bin/env bash
set -euo pipefail
export PATH="${HOME}/.local/bin:${HOME}/.cargo/bin:${PATH}"

echo "============================================================"
echo " 🧪 LINUM MULTI-BACKEND OMNIBUS VERIFICATION"
echo "============================================================"

echo "--- 1. Rust Source (.rs) ---"
cat << 'RS' > test_sample.rs
fn main() { println!("[✔] Rust backend working"); }
RS
linum test_sample.rs

echo -e "\n--- 2. Zig Source (.zig) ---"
cat << 'ZG' > test_sample.zig
const std = @import("std");
pub fn main() void {
    std.debug.print("[✔] Zig backend working\n", .{});
}
ZG
linum test_sample.zig

echo -e "\n--- 3. LLVM SSA IR (.ll) ---"
cat << 'LL' > test_sample.ll
target triple = "x86_64-pc-linux-gnu"
@msg = private unnamed_addr constant [29 x i8] c"[✔] LLVM 21 IR backend OK\0A\00", align 1
declare i32 @printf(ptr nocapture readonly, ...)
define i32 @main() {
  %call = call i32 (ptr, ...) @printf(ptr @msg)
  ret i32 0
}
LL
linum test_sample.ll

echo -e "\n--- 4. QBE Intermediate Language (.qbe) ---"
cat << 'QBE' > test_sample.qbe
data $fmt = { b "[✔] QBE IL backend working\n", b 0 }
export function w $main() {
@start
    call $printf(l $fmt)
    ret 0
}
QBE
linum test_sample.qbe

echo -e "\n--- 5. C Source (.c) ---"
cat << 'C' > test_sample.c
#include <stdio.h>
int main(void) {
    printf("[✔] Clang C backend working\n");
    return 0;
}
C
linum test_sample.c

echo -e "\n--- 6. Z3 SMT Prover (.smt2) ---"
cat << 'SMT' > test_sample.smt2
(declare-const a Int)
(declare-const b Int)
(assert (= (+ a b) 42))
(assert (> a 10))
(check-sat)
SMT
linum test_sample.smt2

# Clean up test artifacts
rm -f test_sample*

echo ""
echo "============================================================"
echo " [✔] All backend pathways successfully verified."
echo "============================================================"
EOF

chmod +x test_complete_omnibus.sh
./test_complete_omnibus.sh