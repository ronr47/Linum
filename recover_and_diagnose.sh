#!/usr/bin/env bash
# ==============================================================================
# ARTIFACT RECOVERY & STRUCTURAL ELF LAYOUT AUDIT
# ==============================================================================

set -euo pipefail

BLUE='\033[1;34m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log_status() { echo -e "${BLUE}[*] ${1}${NC}"; }
log_pass()   { echo -e "${GREEN}[✔] ${1}${NC}"; }
log_fail()   { echo -e "${RED}[✘] ${1}${NC}"; }

WORKSPACE="$HOME/linum"
cd "$WORKSPACE"

echo -e "${BLUE}======================================================================${NC}"
echo -e "${BLUE}         REBUILDING SYSTEM ARTIFACTS & ANALYZING ELF HEADERS          ${NC}"
echo -e "${BLUE}======================================================================${NC}"

# 1. Re-run the local build toolchain script to restore the aarch64 binary
log_status "Triggering orchestrator build pipeline to restore AArch64 engine..."
if [ -f "./build_with_linum.sh" ]; then
    bash ./build_with_linum.sh > /dev/null 2>&1 || bash ./build.sh > /dev/null 2>&1 || true
fi

# Verify restoration
if [ -s "./build/aarch64/fx_lightweight" ]; then
    log_pass "AArch64 binary successfully restored: $(du -sh ./build/aarch64/fx_lightweight | awk '{print $1}')"
else
    log_fail "Build script failed to restore the file. Checking alternative build caches..."
    # Fallback copy from secondary target arrays if available
    find ./target ./zig-out -name "fx_lightweight" -type f -exec cp {} ./build/aarch64/fx_lightweight \; 2>/dev/null || true
fi

# 2. Non-Destructive Header Inspection
log_status "Reading Program Headers to determine why stripping failed..."
TARGET_BIN="./build/riscv64/fx_lightweight"

if [ -f "$TARGET_BIN" ]; then
    echo -e "\n${BLUE}--- [ELF PROGRAM HEADERS: $TARGET_BIN] ---${NC}"
    if command -v readelf >/dev/null 2>&1; then
        # Look for custom segments or missing symbol sections (.symtab)
        readelf -l "$TARGET_BIN" | grep -A 4 -i "program header" || true
        echo -e "\n${BLUE}--- [SECTION HEADERS] ---${NC}"
        readelf -S "$TARGET_BIN" | grep -E '(symtab|strtab|debug|text)' || true
    else
        log_fail "readelf utility unavailable in this path context."
    fi
else
    log_fail "Target binary $TARGET_BIN missing from workspace storage profiles."
fi

echo -e "\n${BLUE}======================================================================${NC}"
