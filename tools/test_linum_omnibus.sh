#!/usr/bin/env bash
set -e
export PATH="${HOME}/.local/bin:${PATH}"

echo "=== TEST 1: RUST SOURCE (.rs) ==="
cat << 'RS' > test1.rs
fn main() { println!("[✔] Rust Backend: Invariant 313 Bound"); }
RS
linum test1.rs

echo -e "\n=== TEST 2: LLVM 21 NATIVE SSA IR (.ll) ==="
cat << 'LL' > test2.ll
target triple = "x86_64-pc-linux-gnu"
@msg = private unnamed_addr constant [40 x i8] c"[✔] LLVM 21 IR: Direct SSA Invariant\0A\00", align 1
declare i32 @printf(ptr nocapture readonly, ...)
define i32 @main() {
  %call = call i32 (ptr, ...) @printf(ptr @msg)
  ret i32 0
}
LL
linum test2.ll

echo -e "\n=== TEST 3: QBE INTERMEDIATE LANGUAGE (.qbe) ==="
cat << 'QBE' > test3.qbe
data $fmt = { b "[✔] QBE Engine: Lightweight Lowering OK\n", b 0 }
export function w $main() {
@start
    call $printf(l $fmt)
    ret 0
}
QBE
linum test3.qbe

echo -e "\n=== TEST 4: C SOURCE (.c) ==="
cat << 'C' > test4.c
#include <stdio.h>
int main(void) {
    printf("[✔] Clang / C Engine: AVX-512 Vector Unit Online\n");
    return 0;
}
C
linum test4.c

# Clean up generated artifacts
rm -f test1 test1.rs test2 test2.ll test3 test3.qbe test3.s test4 test4.c
