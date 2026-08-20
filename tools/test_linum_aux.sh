#!/usr/bin/env bash
set -e
export PATH="${HOME}/.local/bin:${PATH}"

echo "=== TEST 5: NASM x86_64 ASSEMBLY (.asm) ==="
cat << 'ASM' > test5.asm
default rel
global main
extern printf

section .rodata
    fmt db "[✔] NASM Assembly Engine: SysV ABI Machine Code OK", 10, 0

section .text
main:
    push rbp
    mov rbp, rsp
    lea rdi, [fmt]
    xor eax, eax
    call printf wrt ..plt
    xor eax, eax
    pop rbp
    ret
ASM
linum test5.asm

echo -e "\n=== TEST 6: C++ SOURCE (.cpp) ==="
cat << 'CPP' > test6.cpp
#include <iostream>
#include <vector>
#include <numeric>

int main() {
    std::vector<int> data = {100, 200, 13};
    int sum = std::accumulate(data.begin(), data.end(), 0);
    std::cout << "[✔] Clang++ Engine: Vector Invariant Result = " << sum << std::endl;
    return 0;
}
CPP
linum test6.cpp

# Clean up artifacts
rm -f test5* test6*
