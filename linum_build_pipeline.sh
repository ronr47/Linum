#!/usr/bin/env bash
# linum_build_pipeline.sh - Formal Compiler Dependency Verification Script

set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
LINUM="${ROOT}/bin/linum"
BUILD="${ROOT}/build"

mkdir -p "${BUILD}"

# Verify source file assets are initialized on the floor
touch "${ROOT}/src/ingress_rules.lnm" "${ROOT}/src/telemetry.lnm"

printf '%s\n' '=== LINUM COMPILATION PASS ==='
"${LINUM}" \
    --target=bpf \
    --emit-c \
    "${ROOT}/src/ingress_rules.lnm" \
    -o "${BUILD}/xdp_prog.c"

"${LINUM}" \
    --target=host \
    --emit-header \
    "${ROOT}/src/telemetry.lnm" \
    -o "${BUILD}/linum_types.h"

printf '%s\n' '=== KERNEL BOUNDARY BPF LOWERING ==='
clang \
    -O2 \
    -g \
    -Wall \
    -Wextra \
    -target bpf \
    -I/usr/include/x86_64-linux-gnu \
    -I"${BUILD}" \
    -c "${BUILD}/xdp_prog.c" \
    -o "${BUILD}/xdp_prog.o"

printf '%s\n' '=== USERSPACE DATA-PLANE BUILD ==='
gcc \
    -O2 \
    -Wall \
    -Wextra \
    -I"${BUILD}" \
    "${ROOT}/xsk_consumer.c" \
    -o "${BUILD}/xsk_consumer" \
    -lxdp -lbpf

printf '%s\n' '=== GENERATED ARTIFACT SIGNATURES ==='
file "${BUILD}/xdp_prog.o" "${BUILD}/xsk_consumer"

printf '%s\n' '=== THE METRIC TRUTH SYSTEM (SHA256) ==='
sha256sum \
    "build/xdp_prog.c" \
    "build/linum_types.h" \
    "build/xdp_prog.o" \
    "build/xsk_consumer"
