#!/usr/bin/env bash
# ==============================================================================
# LINUM ENGINE INTEGRITY GATE
# Purpose: Cryptographically seals core compiler files to prevent tampering
# ==============================================================================

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[1;34m'
NC='\033[0m'

MANIFEST_FILE="$HOME/linum/build/artifacts/core_manifest.sha256"

log_status() { echo -e "${BLUE}[*] ${1}${NC}"; }
log_pass()   { echo -e "${GREEN}[✔] ${1}${NC}"; }
log_fail()   { echo -e "${RED}[✘] ${1}${NC}"; }

mkdir -p "$(dirname "$MANIFEST_FILE")"

# 1. Define Critical Execution Path Invariants
declare -a CORE_COMPONENTS=(
    "mathic/compiler.py"
    "mathic/emit_llvm.py"
    "src/verify_bounds.py"
    "native/linum_ebpf_loader"
)

generate_baseline() {
    log_status "Generating crisp cryptographic signatures for core compiler matrices..."
    > "$MANIFEST_FILE"
    for file in "${CORE_COMPONENTS[@]}"; do
        if [ -f "$file" ]; then
            sha256sum "$file" >> "$MANIFEST_FILE"
            log_status "Hashed: $file"
        fi
    done
    log_pass "Compiler validation manifest sealed successfully."
}

verify_baseline() {
    log_status "Attesting active compiler source against invariant manifest..."
    if [ ! -f "$MANIFEST_FILE" ]; then
        log_fail "Verification manifest missing. Run with '--generate' first."
        exit 1
    fi

    if sha256sum -c "$MANIFEST_FILE" > /dev/null 2>&1; then
        log_pass "All core compiler modules pass cryptographic integrity checks."
        exit 0
    else
        log_fail "SECURITY INTEGRITY BREACH: Unsanctioned code modification detected in core compiler components!"
        sha256sum -c "$MANIFEST_FILE" | grep "FAILED" || true
        exit 1
    fi
}

if [ "${1:-}" == "--generate" ]; then
    generate_baseline
else
    verify_baseline
fi
