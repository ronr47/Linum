#!/usr/bin/env bash
set -euo pipefail

echo "=== 1. HOST ENVIRONMENT TELEMETRY ==="
ARCH=$(uname -m)
echo "Reported Architecture: ${ARCH}"

AS_BIN=""
LD_BIN=""

if [[ "${ARCH}" == "aarch64" || "${ARCH}" == "arm64" ]]; then
    AS_BIN=$(command -v as || true)
    LD_BIN=$(command -v ld || true)
elif command -v aarch64-linux-gnu-as >/dev/null 2>&1; then
    AS_BIN="aarch64-linux-gnu-as"
    LD_BIN="aarch64-linux-gnu-ld"
    echo "Host is not native AArch64; using cross-toolchain: ${AS_BIN}"
else
    echo "ERROR: No suitable AArch64 assembler found."
    echo "On Debian/Ubuntu: apt-get install binutils OR binutils-aarch64-linux-gnu"
    echo "On Termux:        pkg install binutils"
    exit 1
fi

echo "Assembler: ${AS_BIN}"
echo "Linker:    ${LD_BIN}"

if [[ -z "${AS_BIN}" || -z "${LD_BIN}" ]]; then
    echo "ERROR: Toolchain resolution failed."
    exit 1
fi

echo "=== 2. EMITTING SOURCE ==="
cat << 'ASM_EOF' > mini_ai.s
.global _start

.section .rodata
    .align 3
msg_stable:
    .ascii "1\n"
    .equ MSG_STABLE_LEN, . - msg_stable

msg_anomaly:
    .ascii "0\n"
    .equ MSG_ANOMALY_LEN, . - msg_anomaly

.section .text
_start:
    // Sensory input: X0 = 5
    mov     x0, #5

    // Kernel parameters: W = 3, B = -4
    mov     x1, #3
    mov     x2, #-4

    // Linear projection: Y = (X * W) + B
    mul     x3, x0, x1
    adds    x3, x3, x2

    // Activation threshold check
    ble     .L_anomaly

.L_stable:
    adr     x1, msg_stable
    mov     x2, #MSG_STABLE_LEN
    b       .L_emit

.L_anomaly:
    adr     x1, msg_anomaly
    mov     x2, #MSG_ANOMALY_LEN

.L_emit:
    mov     x0, #1          // STDOUT_FILENO
    mov     x8, #64         // sys_write (Linux AArch64)
    svc     #0

    mov     x0, #0          // exit code 0
    mov     x8, #93         // sys_exit (Linux AArch64)
    svc     #0
ASM_EOF

echo "=== 3. COMPILATION & LINKING ==="
"${AS_BIN}" -o mini_ai.o mini_ai.s
"${LD_BIN}" -s -o mini_ai.elf mini_ai.o
rm -f mini_ai.o
echo "Binary successfully linked: $(ls -l mini_ai.elf)"

echo "=== 4. EXECUTION ==="
if [[ "${ARCH}" == "aarch64" || "${ARCH}" == "arm64" ]]; then
    ./mini_ai.elf
elif command -v qemu-aarch64 >/dev/null 2>&1; then
    echo "Executing under QEMU User Space Emulation:"
    qemu-aarch64 ./mini_ai.elf
else
    echo "Cross-compiled successfully. Target is AArch64; install 'qemu-user' to test on x86_64."
fi
