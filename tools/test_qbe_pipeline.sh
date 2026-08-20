#!/usr/bin/env bash
set -e

echo "[*] Generating QBE Intermediate Representation..."
cat << 'QBE_EOF' > test.qbe
data $fmt = { b "[✔] QBE Native Engine: Execution Verified | Output: %d\n", b 0 }

export function w $main() {
@start
    %a =w copy 100
    %b =w copy 213
    %res =w add %a, %b
    call $printf(l $fmt, w %res)
    ret 0
}
QBE_EOF

echo "[*] Lowering QBE IR to x86_64 assembly..."
qbe -o test.s test.qbe

echo "[*] Linking target machine code with GCC..."
gcc test.s -o test_qbe_bin

echo "[*] Executing generated binary:"
./test_qbe_bin

rm -f test.qbe test.s test_qbe_bin
